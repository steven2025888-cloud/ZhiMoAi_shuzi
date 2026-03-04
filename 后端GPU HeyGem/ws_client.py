#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 服务器 WebSocket 客户端
连接到 API 端的 WebSocket 网关，接收任务并回传结果
"""

import json
import logging
import threading
import time
from typing import Callable, Optional

try:
    import websocket
except ImportError:
    print("请安装 websocket-client: pip install websocket-client")
    raise

logger = logging.getLogger(__name__)


class GpuWebSocketClient:
    """GPU 服务器 WebSocket 客户端"""

    def __init__(
        self,
        ws_url: str,
        on_task_callback: Callable[[dict], None],
        reconnect_interval: int = 5,
        max_reconnect_interval: int = 30,
    ):
        """
        初始化 WebSocket 客户端

        Args:
            ws_url: WebSocket 服务器地址，例如 ws://api.example.com/dsp
            on_task_callback: 收到任务时的回调函数，参数为任务消息字典
            reconnect_interval: 初始重连间隔（秒）
            max_reconnect_interval: 最大重连间隔（秒）
        """
        self.ws_url = ws_url
        self.on_task_callback = on_task_callback
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_interval = max_reconnect_interval

        self.ws: Optional[websocket.WebSocketApp] = None
        self.running = False
        self.connected = False
        self.thread: Optional[threading.Thread] = None
        self._current_reconnect_interval = reconnect_interval

        # 已处理的 request_id 集合（防止重复处理）
        self._processed_requests = {}
        self._processed_lock = threading.Lock()

    def start(self):
        """启动 WebSocket 客户端（后台线程）"""
        if self.running:
            logger.warning("[WS Client] 已经在运行中")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_forever, daemon=True)
        self.thread.start()
        logger.info(f"[WS Client] 启动成功，连接到 {self.ws_url}")

    def stop(self):
        """停止 WebSocket 客户端"""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("[WS Client] 已停止")

    def send_result(
        self,
        request_id: str,
        task_type: str,
        key: str = "",
        sender_fd: int = 0,
        result: Optional[dict] = None,
        error: bool = False,
        error_msg: str = "",
    ):
        """
        发送任务结果给 API 端

        Args:
            request_id: 请求ID
            task_type: 任务类型
            key: license_key
            sender_fd: 原始发送者的 WebSocket fd
            result: 结果数据（成功时）
            error: 是否错误
            error_msg: 错误信息（失败时）
        """
        if not self.connected or not self.ws:
            logger.error(f"[WS Client] 未连接，无法发送结果: request_id={request_id}")
            return

        msg = {
            "type": "gpu.job.result",
            "task_type": task_type,
            "request_id": request_id,
            "key": key,
            "sender_fd": sender_fd,
            "error": error,
        }

        if error:
            msg["error_msg"] = error_msg
        else:
            msg["result"] = result or {}

        try:
            self.ws.send(json.dumps(msg, ensure_ascii=False))
            logger.info(
                f"[WS Client] 发送结果: request_id={request_id} task_type={task_type} error={error}"
            )
        except Exception as e:
            logger.error(f"[WS Client] 发送结果失败: {e}")

    def send_progress(
        self,
        task_id: str,
        key: str = "",
        sender_fd: int = 0,
        status: str = "",
        progress: int = 0,
        message: str = "",
        total_frames: int = 0,
        current_frame: int = 0,
    ):
        """
        推送任务进度给客户端（经 Dsp.php 路由到指定 license_key 的客户端）

        Args:
            task_id: 任务ID
            key: license_key，用于路由到正确客户端
            sender_fd: 原始提交者的 WS fd（精确回传用）
            status: 任务状态 (queued/processing/synthesizing/done/error)
            progress: 进度百分比 0-100
            message: 进度描述文字
            total_frames: 总帧数
            current_frame: 当前已处理帧数
        """
        if not self.connected or not self.ws:
            return
        msg = {
            "type": "gpu.task.progress",
            "task_id": task_id,
            "key": key,
            "sender_fd": sender_fd,
            "status": status,
            "progress": progress,
            "message": message,
            "total_frames": total_frames,
            "current_frame": current_frame,
            "ts": int(time.time()),
        }
        try:
            self.ws.send(json.dumps(msg, ensure_ascii=False))
        except Exception as e:
            logger.debug(f"[WS Client] send_progress 失败: {e}")

    def notify_task_active(self, task_id: str = "", task_type: str = ""):
        """通知 WS 服务器当前有活跃任务（gpu_power_manager 据此延长空闲计时）"""
        if not self.connected or not self.ws:
            return
        try:
            self.ws.send(json.dumps({
                "type": "gpu.task.active",
                "task_id": task_id,
                "task_type": task_type,
                "ts": int(time.time()),
            }))
        except Exception as e:
            logger.debug(f"[WS Client] notify_task_active 失败: {e}")

    def _run_forever(self):
        """后台线程：持续运行 WebSocket 连接"""
        while self.running:
            try:
                self._connect()
            except Exception as e:
                logger.error(f"[WS Client] 连接异常: {e}")

            if self.running:
                logger.info(
                    f"[WS Client] {self._current_reconnect_interval}秒后重连..."
                )
                time.sleep(self._current_reconnect_interval)
                # 指数退避
                self._current_reconnect_interval = min(
                    self._current_reconnect_interval * 2, self.max_reconnect_interval
                )

    def _connect(self):
        """建立 WebSocket 连接"""
        logger.info(f"[WS Client] 正在连接 {self.ws_url}...")

        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self.ws.run_forever()

    def _on_open(self, ws):
        """WebSocket 连接成功"""
        self.connected = True
        self._current_reconnect_interval = self.reconnect_interval
        logger.info("[WS Client] 连接成功")

        # 注册为 worker 并通知 GPU 上线
        register_msg = {
            "type": "register",
            "role": "worker",
            "version": "1.0",
            "ts": int(time.time()),
        }
        ws.send(json.dumps(register_msg))
        logger.info("[WS Client] 已发送注册消息")

        # 发送 GPU 上线通知（类型必须是 gpu.power.online，Dsp.php 才能识别并广播）
        online_msg = {
            "type": "gpu.power.online",
            "status": "running",
            "msg": "GPU服务器已启动",
            "ts": int(time.time()),
        }
        ws.send(json.dumps(online_msg))
        logger.info("[WS Client] 已发送 gpu.power.online 上线通知")

    def _on_message(self, ws, message):
        """收到 WebSocket 消息"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            logger.debug(f"[WS Client] 收到消息: type={msg_type}")

            # 注册确认
            if msg_type == "registered":
                logger.info("[WS Client] 注册成功，等待任务...")
                return

            # ping/pong
            if msg_type == "ping":
                ws.send(json.dumps({"type": "pong"}))
                return

            # 单个任务
            if msg_type == "gpu.job.submit" or msg_type == "gpu_task":
                self._handle_task(data)
                return

            # 批量任务（GPU 上线后下发）
            if msg_type == "gpu.job.dispatch.batch":
                jobs = data.get("data", {}).get("jobs", [])
                logger.info(f"[WS Client] 收到批量任务: {len(jobs)} 个")
                for job in jobs:
                    self._handle_task(job)
                return

            # 旧协议兼容
            if msg_type in ("url", "chatglm_video"):
                self._handle_task(data)
                return

        except json.JSONDecodeError:
            logger.error(f"[WS Client] 消息解析失败: {message[:200]}")
        except Exception as e:
            logger.error(f"[WS Client] 处理消息异常: {e}", exc_info=True)

    def _handle_task(self, task_msg: dict):
        """处理任务消息"""
        request_id = task_msg.get("request_id", "")
        task_type = task_msg.get("task_type", task_msg.get("type", ""))

        # 幂等性检查
        with self._processed_lock:
            if request_id and request_id in self._processed_requests:
                logger.warning(
                    f"[WS Client] 任务已处理，跳过: request_id={request_id}"
                )
                return
            if request_id:
                self._processed_requests[request_id] = time.time()

        logger.info(
            f"[WS Client] 处理任务: request_id={request_id} task_type={task_type}"
        )

        # 调用回调函数（在新线程中执行，避免阻塞 WebSocket）
        threading.Thread(
            target=self._execute_task, args=(task_msg,), daemon=True
        ).start()

    def _execute_task(self, task_msg: dict):
        """在独立线程中执行任务"""
        try:
            self.on_task_callback(task_msg)
        except Exception as e:
            logger.error(f"[WS Client] 任务执行异常: {e}", exc_info=True)
            # 发送错误结果
            self.send_result(
                request_id=task_msg.get("request_id", ""),
                task_type=task_msg.get("task_type", ""),
                key=task_msg.get("key", ""),
                sender_fd=task_msg.get("sender_fd", 0),
                error=True,
                error_msg=str(e),
            )

    def _on_error(self, ws, error):
        """WebSocket 错误"""
        logger.error(f"[WS Client] 错误: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket 连接关闭"""
        self.connected = False
        logger.warning(
            f"[WS Client] 连接关闭: code={close_status_code} msg={close_msg}"
        )

    def cleanup_processed_cache(self, ttl: int = 3600):
        """清理过期的已处理记录（定期调用）"""
        now = time.time()
        with self._processed_lock:
            expired = [
                rid for rid, ts in self._processed_requests.items() if now - ts > ttl
            ]
            for rid in expired:
                del self._processed_requests[rid]
            if expired:
                logger.info(f"[WS Client] 清理过期记录: {len(expired)} 条")


# 示例用法
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    def on_task(task_msg):
        print(f"收到任务: {task_msg}")
        # 模拟处理
        time.sleep(2)
        # 发送结果（需要在实际代码中调用 client.send_result）

    client = GpuWebSocketClient(
        ws_url="ws://localhost:9501/dsp", on_task_callback=on_task
    )

    client.start()

    try:
        while True:
            time.sleep(10)
            client.cleanup_processed_cache()
    except KeyboardInterrupt:
        client.stop()
