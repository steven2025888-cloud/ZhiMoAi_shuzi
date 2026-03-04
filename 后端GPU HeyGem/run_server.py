#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HeyGem Linux 在线合成服务
=========================
功能：
  1. 多并发队列（最大并发数可配置，默认3，超出排队）
  2. 客户端上传视频+音频 -> 服务端合成（支持 hash 去重，相同文件不重复上传）
  3. 超过1天的上传/输出文件自动清理
  4. 合成进度实时回传客户端

启动方式：
  python run_server.py
  python run_server.py --host 0.0.0.0 --port 8383
"""

import argparse
import configparser
import gc
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Optional

# Keep process CWD stable for both main process and spawn children.
# Some binary modules read config/config.ini by relative path at import time.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_BASE_DIR)
_CFG_PATH = os.path.join(_BASE_DIR, "config", "config.ini")
if not os.path.exists(_CFG_PATH):
    raise FileNotFoundError(f"config.ini not found: {_CFG_PATH}")

_cfg_check = configparser.ConfigParser()
_cfg_check.read(_CFG_PATH, encoding="utf-8")
if not _cfg_check.has_section("log"):
    raise RuntimeError(f"config.ini missing [log] section: {_CFG_PATH}")

# ── 可选：禁用 GFPGAN 面部超分以大幅加速合成（必须在 import engine 之前） ──
_ENABLE_GFPGAN = _cfg_check.get("digital", "enable_gfpgan", fallback="1").strip()
if _ENABLE_GFPGAN == "0":
    import numpy as _np
    class _DummyGFPGAN:
        """GFPGAN 占位：返回原图（格式兼容），跳过 ONNX 推理。
        真实 GFPGAN.forward():
            Input:  cv2 BGR image, uint8, 0-255, any size
            Output: BGR numpy array, float32, 0-1, 512x512x3
        """
        def __init__(self, *a, **kw):
            self.input_size = (512, 512)
        def forward(self, face_image):
            import cv2 as _cv2
            img = _cv2.resize(face_image, self.input_size, interpolation=_cv2.INTER_LINEAR)
            return img.astype(_np.float32) / 255.0
        def __getattr__(self, name):
            def _noop(*a, **kw):
                if a:
                    return a[0]
                return None
            return _noop
    try:
        import face_lib.face_restore
        import face_lib.face_restore.gfpgan_onnx.gfpgan_onnx_api as _gfpgan_mod
        _gfpgan_mod.GFPGAN = _DummyGFPGAN
        face_lib.face_restore.GFPGAN = _DummyGFPGAN
        print("[Server] GFPGAN 面部超分已禁用（enable_gfpgan=0）")
    except Exception as _e:
        print(f"[Server] 禁用 GFPGAN 失败: {_e}")

import cv2
from flask import Flask, request, jsonify, send_file

import service.trans_dh_service
from h_utils.custom import CustomError
from y_utils.config import GlobalConfig
from y_utils.logger import logger

# WebSocket 客户端（连接到 API 端）
try:
    from ws_client import GpuWebSocketClient
    WS_CLIENT_AVAILABLE = True
except ImportError:
    logger.warning("[Server] ws_client 未安装，WebSocket 功能不可用")
    WS_CLIENT_AVAILABLE = False

# ============================================================
#  配置加载
# ============================================================
_cfg = configparser.ConfigParser()
_cfg.read(_CFG_PATH, encoding="utf-8")

MAX_CONCURRENT = int(_cfg.get("server", "max_concurrent", fallback="3"))
UPLOAD_DIR = _cfg.get("server", "upload_dir", fallback="./uploads")
OUTPUT_DIR = _cfg.get("server", "output_dir", fallback="./outputs")
FILE_TTL = int(_cfg.get("server", "file_ttl_seconds", fallback="86400"))
CLEANUP_INTERVAL = int(_cfg.get("server", "cleanup_interval_seconds", fallback="3600"))
API_SECRET = _cfg.get("server", "api_secret", fallback="").strip()

# WebSocket 配置
WS_API_URL = _cfg.get("server", "ws_api_url", fallback="").strip()  # 例如: ws://api.example.com:9501/dsp
WS_ENABLED = bool(WS_API_URL and WS_CLIENT_AVAILABLE)

def _abs_path(p: str) -> str:
    if not p:
        return os.path.abspath(os.path.dirname(__file__))
    if os.path.isabs(p):
        return os.path.abspath(p)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), p))


UPLOAD_DIR = _abs_path(UPLOAD_DIR)
OUTPUT_DIR = _abs_path(OUTPUT_DIR)

# 文件池目录：按 md5 hash 存储，实现去重
FILE_POOL_DIR = os.path.join(UPLOAD_DIR, "pool")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FILE_POOL_DIR, exist_ok=True)

# 资产目录：音色和数字人文件（30天保留）
ASSET_DIR = os.path.join(UPLOAD_DIR, "assets")
ASSET_TTL = int(_cfg.get("server", "asset_ttl_seconds", fallback=str(30 * 86400)))  # 30天
os.makedirs(ASSET_DIR, exist_ok=True)

# SQLite 数据库：资产元数据
_DB_PATH = os.path.join(os.path.dirname(__file__), "assets.db")
_db_lock = threading.Lock()


def _get_db():
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db():
    conn = _get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_key TEXT NOT NULL,
        asset_type TEXT NOT NULL,          -- 'voice' | 'avatar'
        name TEXT NOT NULL,
        file_hash TEXT NOT NULL,
        file_ext TEXT NOT NULL DEFAULT '',
        file_path TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_assets_key_type ON assets(license_key, asset_type);
    CREATE INDEX IF NOT EXISTS idx_assets_expires ON assets(expires_at);
    """)
    conn.close()
    logger.info(f"[DB] 资产数据库初始化完成: {_DB_PATH}")


_init_db()


def _pool_path(file_hash, ext):
    """根据 hash 和扩展名，返回文件池中的路径"""
    return os.path.join(FILE_POOL_DIR, f"{file_hash}{ext}")


def _file_exists_in_pool(file_hash, ext):
    """检查文件池中是否已存在该 hash 的文件"""
    p = _pool_path(file_hash, ext)
    return os.path.exists(p) and os.path.getsize(p) > 0


def _resolve_to_pool(file_hash: str, ext: str) -> str:
    """确保文件存在于文件池中，不在则从资产目录自动恢复。

    返回文件池路径（如果找到），否则返回空字符串。
    """
    pool_p = _pool_path(file_hash, ext)
    if os.path.exists(pool_p) and os.path.getsize(pool_p) > 0:
        return pool_p

    # 文件池中不存在，尝试从资产目录恢复
    with _db_lock:
        conn = _get_db()
        row = conn.execute(
            "SELECT file_path FROM assets WHERE file_hash=? AND file_ext=? AND expires_at>? "
            "ORDER BY created_at DESC LIMIT 1",
            (file_hash, ext, time.time()),
        ).fetchone()
        conn.close()

    if row and row["file_path"] and os.path.exists(row["file_path"]):
        try:
            shutil.copy2(row["file_path"], pool_p)
            logger.info(f"[Pool] 从资产目录恢复到文件池: {file_hash}{ext}")
            return pool_p
        except Exception as e:
            logger.warning(f"[Pool] 恢复文件失败: {e}")

    return ""


def _md5_of_file(path):
    """计算文件的 MD5"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ============================================================
#  自定义 write_video（与 app.py / run_api.py 一致）
# ============================================================
def _write_video_server(
    output_imgs_queue, temp_dir, result_dir, work_id, audio_path,
    result_queue, width, height, fps,
    watermark_switch=0, digital_auth=0, temp_queue=None,
):
    output_mp4 = os.path.join(temp_dir, f"{work_id}-t.mp4")
    result_path = os.path.join(result_dir, f"{work_id}-r.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_write = cv2.VideoWriter(output_mp4, fourcc, fps, (width, height))
    logger.info(f"[Server] VideoWriter init: {work_id}")

    frame_count = 0
    # 进度文件：子进程写入帧数，主进程读取（跨进程 IPC）
    _progress_file = os.path.join(temp_dir, f".progress_{work_id}")
    _last_progress_write = 0  # 上次写进度文件的时间戳（节流，避免频繁 IO 拖慢合成）

    try:
        while True:
            state, reason, value_ = output_imgs_queue.get()
            if isinstance(state, bool) and state is True:
                logger.info(f"[Server] VideoWriter [{work_id}] 帧队列结束")
                video_write.release()
                break
            elif isinstance(state, bool) and state is False:
                logger.error(f"[Server] VideoWriter [{work_id}] 异常: {reason}")
                raise CustomError(reason)
            else:
                for img in value_:
                    video_write.write(img)
                    frame_count += 1
                # 写进度文件供主进程读取，节流：每 5 秒最多写一次
                _now = time.time()
                if _now - _last_progress_write >= 5:
                    _last_progress_write = _now
                    try:
                        with open(_progress_file, "w") as _pf:
                            _pf.write(f"{frame_count}\n")
                    except Exception:
                        pass

        if video_write is not None:
            video_write.release()

        # 诊断：检查音频文件是否存在
        if not os.path.exists(audio_path):
            logger.warning(f"[Server] 音频文件不存在: {audio_path}, 尝试在 temp_dir 查找")
            # 引擎可能传的是相对路径，尝试在 temp_dir 中寻找格式化后的音频
            _alt = os.path.join(temp_dir, f"{work_id}_format.wav")
            if os.path.exists(_alt):
                audio_path = _alt
                logger.info(f"[Server] 使用备选音频: {audio_path}")
            else:
                logger.error(f"[Server] 备选音频也不存在: {_alt}")

        logger.info(f"[Server] ffmpeg merge: audio={audio_path} (exists={os.path.exists(audio_path)}, "
                     f"size={os.path.getsize(audio_path) if os.path.exists(audio_path) else 0}), "
                     f"video={output_mp4}")

        command = (
            f'ffmpeg -loglevel warning -y -i {audio_path} -i {output_mp4} '
            f'-map 0:a -map 1:v '
            f'-c:a aac -c:v libx264 -profile:v baseline -level 3.1 '
            f'-pix_fmt yuv420p -crf 15 '
            f'-movflags +faststart -strict -2 {result_path}'
        )
        logger.info(f"[Server] ffmpeg: {command}")
        rc = subprocess.call(command, shell=True)
        if rc != 0:
            logger.warning(f"[Server] ffmpeg 退出码非零: {rc}")
        logger.info(f"[Server] 视频生成完成: {result_path}")
        result_queue.put([True, result_path])
    except Exception as e:
        logger.error(f"[Server] VideoWriter [{work_id}] 异常: {e}")
        # 写错误文件供主进程读取（与进度文件同目录）
        try:
            _err_file = os.path.join(temp_dir, f".error_{work_id}")
            with open(_err_file, "w") as _ef:
                _ef.write(str(e))
        except Exception:
            pass
        result_queue.put([False, f"[{work_id}] 异常: {e}"])
    logger.info(f"[Server] VideoWriter [{work_id}] 线程结束")


service.trans_dh_service.write_video = _write_video_server

# ============================================================
#  全局状态
# ============================================================
app = Flask(__name__)

# ── CORS 支持（手机端 H5 跨域访问视频/接口） ──
@app.after_request
def _add_cors_headers(response):
    try:
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, Range'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range, Accept-Ranges, Content-Disposition'
        # iOS/Safari 对 Range/流式播放更友好
        if (response.mimetype or '').startswith('video/'):
            response.headers['Accept-Ranges'] = 'bytes'
    except Exception:
        pass
    return response

_task_instance = None
_task_instance_lock = threading.Lock()

_semaphore = threading.Semaphore(MAX_CONCURRENT)
_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT + 4)

_tasks = OrderedDict()
_tasks_lock = threading.Lock()

# WebSocket 客户端实例
_ws_client: Optional[GpuWebSocketClient] = None


class TaskStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    SYNTHESIZING = "synthesizing"
    ENCODING = "encoding"
    DONE = "done"
    ERROR = "error"


def _new_task(task_id, audio_name, video_name):
    return {
        "task_id": task_id,
        "status": TaskStatus.QUEUED,
        "progress": 0,
        "total_frames": 0,
        "current_frame": 0,
        "message": "排队中...",
        "audio_name": audio_name,
        "video_name": video_name,
        "result_path": "",
        "error": "",
        "created_at": time.time(),
        "started_at": 0,
        "finished_at": 0,
        "_license_key": "",    # 客户端 license_key，用于 WS 进度推送路由
        "_sender_fd": 0,       # 客户端 WS fd，用于精确推送
    }


def _update_task(task_id, **kwargs):
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id].update(kwargs)


_last_ws_notify_time = 0  # 上次通知 gpu_power_manager 的时间戳

def _notify_gpu_task_active(task_id: str = "", task_type: str = "heygem_task"):
    """节流通知 gpu_power_manager 有活跃任务（每 30 秒最多一次）"""
    global _last_ws_notify_time
    now = time.time()
    if now - _last_ws_notify_time < 30:
        return
    _last_ws_notify_time = now
    if _ws_client:
        _ws_client.notify_task_active(task_id=task_id, task_type=task_type)


_last_progress_push_time = {}  # task_id -> last push timestamp（节流 WS 推送）

def _push_progress(task_id: str):
    """通过 WS 推送任务进度给客户端（节流：每 2 秒最多推一次帧进度）"""
    if not _ws_client:
        return
    with _tasks_lock:
        task = _tasks.get(task_id)
        if not task:
            return
        key = task.get("_license_key", "")
        sender_fd = task.get("_sender_fd", 0)
        status = task.get("status", "")
        progress = task.get("progress", 0)
        message = task.get("message", "")
        total_frames = task.get("total_frames", 0)
        current_frame = task.get("current_frame", 0)

    if not key:
        return  # 没有 license_key（旧版客户端/PC直连），不推送

    # 帧进度节流：synthesizing 状态每 2 秒最多推一次
    now = time.time()
    if status in (TaskStatus.SYNTHESIZING, TaskStatus.PROCESSING):
        last = _last_progress_push_time.get(task_id, 0)
        if now - last < 2:
            return
    _last_progress_push_time[task_id] = now

    _ws_client.send_progress(
        task_id=task_id,
        key=key,
        sender_fd=sender_fd,
        status=status,
        progress=progress,
        message=message,
        total_frames=total_frames,
        current_frame=current_frame,
    )


def _update_task_progress(work_id, stage, frame_count):
    task_id = ""
    with _tasks_lock:
        for t in _tasks.values():
            if t.get("_work_id") == work_id:
                total = t.get("total_frames", 0) or 1
                pct = min(95, int(frame_count / total * 90) + 5)
                t["status"] = stage
                t["current_frame"] = frame_count
                t["progress"] = pct
                t["message"] = f"合成中 {frame_count}/{total} 帧 ({pct}%)"
                task_id = t.get("task_id", "")
                break
    # 每 30 秒通知 gpu_power_manager 有活跃任务，防止误判空闲关机
    _notify_gpu_task_active(task_id=task_id, task_type="heygem_synthesizing")
    # WS 推送进度给客户端
    if task_id:
        _push_progress(task_id)


def _get_queue_info():
    with _tasks_lock:
        total = len(_tasks)
        processing = sum(1 for t in _tasks.values()
                         if t["status"] in (TaskStatus.PROCESSING, TaskStatus.SYNTHESIZING, TaskStatus.ENCODING))
        queued = sum(1 for t in _tasks.values() if t["status"] == TaskStatus.QUEUED)
    return {
        "total_tasks": total,
        "processing": processing,
        "queued": queued,
        "max_concurrent": MAX_CONCURRENT,
    }


# ============================================================
#  API 鉴权
# ============================================================
def _check_auth():
    if not API_SECRET:
        return None
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if token != API_SECRET:
        return jsonify({"code": 401, "msg": "鉴权失败"}), 401
    return None


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        err = _check_auth()
        if err:
            return err
        return f(*args, **kwargs)
    return decorated


# ============================================================
#  核心：任务执行
# ============================================================
def _run_task(task_id, audio_path, video_path):
    _update_task(task_id, status=TaskStatus.QUEUED, message="等待可用 GPU 槽位...")
    _semaphore.acquire()
    try:
        # 通知 gpu_power_manager 有任务开始处理（立即通知，不受节流限制）
        global _last_ws_notify_time
        _last_ws_notify_time = 0  # 强制立即发送
        _notify_gpu_task_active(task_id=task_id, task_type="heygem_processing")

        _update_task(task_id, status=TaskStatus.PROCESSING, message="开始处理...",
                     started_at=time.time())
        _push_progress(task_id)  # 推送 processing 状态

        # 检查 ffmpeg 是否可用
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            raise RuntimeError("ffmpeg 未安装！请执行: sudo apt install -y ffmpeg")
        except Exception:
            pass

        # 检查输入文件
        if not os.path.exists(audio_path):
            raise RuntimeError(f"音频文件不存在: {audio_path}")
        if not os.path.exists(video_path):
            raise RuntimeError(f"视频文件不存在: {video_path}")

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()

        if total_frames <= 0 or width <= 0 or height <= 0:
            raise RuntimeError(f"视频文件无效: frames={total_frames}, size={width}x{height}")

        _update_task(task_id, total_frames=total_frames,
                     message=f"视频信息: {width}x{height} {fps:.1f}fps {total_frames}帧")

        work_id = str(uuid.uuid1())
        _update_task(task_id, _work_id=work_id)

        def _transcode_video_for_engine(src_video: str, out_video: str) -> None:
            """Force video to a conservative format accepted by engine preprocess."""
            cmd = [
                "ffmpeg", "-y", "-loglevel", "warning",
                "-i", src_video,
                "-an",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(int(fps)) if fps and fps > 0 else "25",
                out_video,
            ]
            logger.info(f"[Server] 转码兜底命令: {' '.join(cmd)}")
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(f"视频兜底转码失败: rc={p.returncode}, stderr={p.stderr[-800:]}")
            if not os.path.exists(out_video) or os.path.getsize(out_video) <= 0:
                raise RuntimeError("视频兜底转码失败: 输出文件不存在或为空")

        def _engine_entry_is_error(entry) -> bool:
            try:
                if isinstance(entry, (list, tuple)) and len(entry) >= 1:
                    s0 = entry[0]
                    if getattr(s0, "name", "").lower() == "error":
                        return True
                    if str(s0).lower().endswith("status.error"):
                        return True
                    if getattr(s0, "value", None) == 3:
                        return True
                return False
            except Exception:
                return False

        def _engine_entry_message(entry) -> str:
            try:
                if isinstance(entry, (list, tuple)):
                    # 常见结构: (Status, progress, result_path, message)
                    if len(entry) >= 4 and isinstance(entry[3], str):
                        return entry[3]
                    if len(entry) >= 2 and isinstance(entry[-1], str):
                        return entry[-1]
                return str(entry)
            except Exception:
                return ""

        _task_instance.task_dic[work_id] = ""
        try:
            _task_instance.work(audio_path, video_path, work_id, 0, 0, 0, 0)
        except Exception as work_err:
            # work() 可能抛异常，也可能仅写 task_dic 的 Status.error
            logger.warning(f"[Server] 推理引擎 work() 抛异常: {work_err}")

        # 读取引擎输出（即使没有异常也要检查 Status）
        result_entry = _task_instance.task_dic.get(work_id, "")
        err_msg = _engine_entry_message(result_entry)

        # 仅在格式错误时兜底重试一次，避免无意义重跑
        if _engine_entry_is_error(result_entry) and ("format video error" in (err_msg or "").lower()):
            logger.warning(f"[Server] 命中 format video error，准备兜底重试: {err_msg}")
            work_dir = os.path.join(UPLOAD_DIR, "work")
            os.makedirs(work_dir, exist_ok=True)
            fallback_video = os.path.join(work_dir, f"{task_id}_fallback.mp4")
            _transcode_video_for_engine(video_path, fallback_video)
            _task_instance.task_dic[work_id] = ""
            try:
                _task_instance.work(audio_path, fallback_video, work_id, 0, 0, 0, 0)
            except Exception as retry_err:
                raise RuntimeError(f"推理引擎错误(重试后仍失败): {retry_err}")
            result_entry = _task_instance.task_dic.get(work_id, "")

        if isinstance(result_entry, (list, tuple)) and len(result_entry) > 2:
            raw_result = result_entry[2]
        else:
            raw_result = str(result_entry)

        task_output_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_output_dir, exist_ok=True)

        # 引擎返回的路径可能不含目录前缀，先尝试在 temp/result 下查找
        _base = os.path.dirname(os.path.abspath(__file__))
        _temp = _cfg.get("temp", "temp_dir", fallback="./temp")
        _result = _cfg.get("result", "result_dir", fallback="./result")
        _temp = os.path.join(_base, _temp) if not os.path.isabs(_temp) else _temp
        _result = os.path.join(_base, _result) if not os.path.isabs(_result) else _result

        if raw_result and not os.path.exists(raw_result):
            # 引擎经常返回错误路径（如 /{work_id}-r.mp4），尝试在 temp/result 目录修正
            _basename = os.path.basename(raw_result)
            for _try_dir in [_temp, _result, "."]:
                _try_path = os.path.join(_try_dir, _basename)
                if os.path.exists(_try_path):
                    logger.info(f"[Server] 修正引擎路径: {raw_result} -> {_try_path}")
                    raw_result = _try_path
                    break

        if raw_result and os.path.exists(raw_result):
            dest = os.path.join(task_output_dir, f"{task_id}.mp4")
            shutil.move(raw_result, dest)
            result_path = os.path.realpath(dest)
        else:
            # 搜索可能的结果文件：优先 -r.mp4（含音频的合并结果），排除 _format.mp4（预处理输入）
            possible_results = []
            for d in [".", _temp, _result, os.path.dirname(video_path), "/tmp"]:
                if os.path.isdir(d):
                    for fn in os.listdir(d):
                        if work_id not in fn or not fn.endswith(".mp4"):
                            continue
                        # 排除预处理文件（没有音频）
                        if "_format.mp4" in fn or "_fallback.mp4" in fn:
                            continue
                        possible_results.append(os.path.join(d, fn))
            # 优先选择 -r.mp4（ffmpeg 合并后的含音频结果）
            possible_results.sort(key=lambda p: (0 if p.endswith("-r.mp4") else 1))
            if possible_results:
                src = possible_results[0]
                dest = os.path.join(task_output_dir, f"{task_id}.mp4")
                shutil.move(src, dest)
                result_path = os.path.realpath(dest)
                logger.info(f"[Server] 找到备选结果: {src}")
            else:
                raise RuntimeError(
                    f"推理未产出结果文件 (task_dic={repr(result_entry)[:200]}). "
                    f"请检查: 1) ffmpeg 是否安装 2) 磁盘空间 3) GPU 状态"
                )

        _update_task(task_id, status=TaskStatus.DONE, progress=100,
                     message="合成完成", result_path=result_path,
                     finished_at=time.time())
        _push_progress(task_id)  # 推送 done 状态
        _last_progress_push_time.pop(task_id, None)  # 清理节流记录

        # ── 写缓存：复制结果到缓存目录，下次相同 audio+video 可直接返回 ──
        with _tasks_lock:
            _ck = _tasks.get(task_id, {}).get("_cache_key", "")
        if _ck and result_path and os.path.exists(result_path):
            try:
                _cache_dir = os.path.join(OUTPUT_DIR, f"cache_{_ck}")
                os.makedirs(_cache_dir, exist_ok=True)
                _cache_file = os.path.join(_cache_dir, f"cache_{_ck}.mp4")
                shutil.copy2(result_path, _cache_file)
                logger.info(f"[Server] 缓存写入: {_cache_file}")
            except Exception as ce:
                logger.warning(f"[Server] 缓存写入失败: {ce}")

        # 清理进度文件和错误文件
        try:
            _wid = ""
            with _tasks_lock:
                _wid = _tasks.get(task_id, {}).get("_work_id", "")
            if _wid:
                _base = os.path.dirname(os.path.abspath(__file__))
                _temp = _cfg.get("temp", "temp_dir", fallback="./temp")
                _temp = os.path.join(_base, _temp) if not os.path.isabs(_temp) else _temp
                for _fn in [f".progress_{_wid}", f".error_{_wid}"]:
                    _fp = os.path.join(_temp, _fn)
                    if os.path.exists(_fp):
                        os.remove(_fp)
        except Exception:
            pass

        logger.info(f"[Server] 任务完成: {task_id} -> {result_path}")

    except Exception as e:
        logger.error(f"[Server] 任务失败: {task_id}\n{traceback.format_exc()}")
        _update_task(task_id, status=TaskStatus.ERROR, progress=0,
                     message=f"合成失败: {e}", error=str(e),
                     finished_at=time.time())
        _push_progress(task_id)  # 推送 error 状态
        _last_progress_push_time.pop(task_id, None)
    finally:
        _semaphore.release()
        gc.collect()


# ============================================================
#  Flask 路由
# ============================================================

@app.route("/api/heygem/check_files", methods=["POST"])
@auth_required
def check_files():
    """
    检查文件是否已存在于服务器文件池（通过 MD5 hash 比对）

    请求体 JSON:
      {"files": [{"hash": "md5hex", "ext": ".wav"}, {"hash": "md5hex", "ext": ".mp4"}]}

    返回:
      {"code": 0, "data": {"md5hex": true, "md5hex2": false}}
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"code": 400, "msg": "请求体必须是合法的JSON"}), 400

    files = data.get("files", [])
    result = {}
    for item in files:
        h = item.get("hash", "").strip()
        ext = item.get("ext", "").strip()
        if h:
            exists = _file_exists_in_pool(h, ext)
            if exists:
                # 刷新 mtime 避免被清理
                p = _pool_path(h, ext)
                try:
                    os.utime(p, None)
                except Exception:
                    pass
            result[h] = exists
    return jsonify({"code": 0, "data": result})


@app.route("/api/heygem/upload_file", methods=["POST"])
@auth_required
def upload_single_file():
    """
    上传单个文件到文件池

    请求方式: multipart/form-data
      - file: 文件
      - hash: 文件的 MD5 hash
      - ext: 文件扩展名（如 .wav, .mp4）

    返回:
      {"code": 0, "data": {"hash": "...", "server_path": "..."}}
    """
    uploaded = request.files.get("file")
    file_hash = request.form.get("hash", "").strip()
    ext = request.form.get("ext", "").strip()

    if not uploaded:
        return jsonify({"code": 400, "msg": "缺少 file 字段"}), 400
    if not file_hash:
        return jsonify({"code": 400, "msg": "缺少 hash 字段"}), 400
    if not ext:
        ext = os.path.splitext(uploaded.filename or "")[1] or ".bin"

    dest = _pool_path(file_hash, ext)

    # 如果已存在，跳过写入，只刷新 mtime
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        os.utime(dest, None)
        logger.info(f"[Upload] 文件已存在，跳过: {file_hash}{ext}")
    else:
        uploaded.save(dest)
        # 校验 hash
        actual_hash = _md5_of_file(dest)
        if actual_hash != file_hash:
            logger.warning(f"[Upload] hash 不匹配: 期望={file_hash}, 实际={actual_hash}")
            # 仍然保留文件，用实际 hash 重命名
            real_dest = _pool_path(actual_hash, ext)
            if dest != real_dest:
                shutil.move(dest, real_dest)
            dest = real_dest
            file_hash = actual_hash
        logger.info(f"[Upload] 文件保存: {file_hash}{ext} ({os.path.getsize(dest)} bytes)")

    return jsonify({
        "code": 0,
        "data": {"hash": file_hash, "server_path": os.path.realpath(dest)}
    })


@app.route("/api/heygem/submit", methods=["POST"])
@auth_required
def submit_task():
    """
    通过文件 hash 提交合成任务（文件已在文件池中）

    请求体 JSON:
      {
        "audio_hash": "md5hex",
        "audio_ext": ".wav",
        "video_hash": "md5hex",
        "video_ext": ".mp4"
      }

    返回:
      {"code": 0, "data": {"task_id": "...", "queue": {...}}}
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"code": 400, "msg": "请求体必须是合法的JSON"}), 400

    audio_hash = data.get("audio_hash", "").strip()
    audio_ext = data.get("audio_ext", ".wav").strip()
    video_hash = data.get("video_hash", "").strip()
    video_ext = data.get("video_ext", ".mp4").strip()
    license_key = data.get("license_key", "").strip()  # 客户端卡密，用于 WS 进度推送
    sender_fd = int(data.get("sender_fd", 0))           # WS fd（从 Dsp.php 转发时携带）

    if not audio_hash or not video_hash:
        return jsonify({"code": 400, "msg": "audio_hash 和 video_hash 不能为空"}), 400

    audio_path = _resolve_to_pool(audio_hash, audio_ext)
    video_path = _resolve_to_pool(video_hash, video_ext)

    if not audio_path:
        return jsonify({"code": 404, "msg": f"音频文件不存在: {audio_hash}{audio_ext}，请先上传"}), 404
    if not video_path:
        return jsonify({"code": 404, "msg": f"视频文件不存在: {video_hash}{video_ext}，请先上传"}), 404

    # ── 缓存命中：相同 audio+video 组合已合成过且结果文件仍在，直接返回 ──
    cache_key = hashlib.md5(f"{audio_hash}_{video_hash}".encode()).hexdigest()[:16]
    cache_result_dir = os.path.join(OUTPUT_DIR, f"cache_{cache_key}")
    cache_result_file = os.path.join(cache_result_dir, f"cache_{cache_key}.mp4")
    if os.path.exists(cache_result_file) and os.path.getsize(cache_result_file) > 0:
        # 刷新 mtime 避免被清理
        try:
            os.utime(cache_result_file, None)
            os.utime(cache_result_dir, None)
        except Exception:
            pass
        # 创建一个已完成的任务记录
        task_id = cache_key
        task_info = _new_task(task_id, f"{audio_hash}{audio_ext}", f"{video_hash}{video_ext}")
        task_info.update({
            "status": TaskStatus.DONE,
            "progress": 100,
            "message": "合成完成（缓存命中）",
            "result_path": os.path.realpath(cache_result_file),
            "finished_at": time.time(),
            "started_at": time.time(),
        })
        with _tasks_lock:
            _tasks[task_id] = task_info
        logger.info(f"[Server] 缓存命中: cache_key={cache_key}, audio={audio_hash}, video={video_hash}")
        return jsonify({
            "code": 0,
            "msg": "缓存命中，直接返回",
            "data": {"task_id": task_id, "cached": True, "queue": _get_queue_info()}
        })

    task_id = str(uuid.uuid4()).replace("-", "")[:16]
    task_info = _new_task(task_id, f"{audio_hash}{audio_ext}", f"{video_hash}{video_ext}")
    task_info["_cache_key"] = cache_key  # 任务完成后用于写缓存
    task_info["_license_key"] = license_key  # WS 进度推送路由
    task_info["_sender_fd"] = sender_fd
    with _tasks_lock:
        _tasks[task_id] = task_info

    _executor.submit(_run_task, task_id, audio_path, video_path)

    # 通知 WS 服务器有活跃任务（gpu_power_manager 据此延长空闲计时，防止误关机）
    if _ws_client:
        _ws_client.notify_task_active(task_id=task_id, task_type="heygem_submit")

    logger.info(f"[Server] 任务已提交(hash): task={task_id}, audio={audio_hash}, video={video_hash}, cache_key={cache_key}")
    return jsonify({
        "code": 0,
        "msg": "任务已提交",
        "data": {"task_id": task_id, "queue": _get_queue_info()}
    })


@app.route("/api/heygem/upload", methods=["POST"])
@auth_required
def upload_and_submit():
    """
    上传音频+视频并提交合成任务（兼容旧接口）

    请求方式: multipart/form-data
      - audio: 音频文件
      - video: 视频文件
    """
    audio_file = request.files.get("audio")
    video_file = request.files.get("video")

    if not audio_file or not video_file:
        return jsonify({"code": 400, "msg": "请上传 audio 和 video 文件"}), 400

    task_id = str(uuid.uuid4()).replace("-", "")[:16]
    task_dir = os.path.join(UPLOAD_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    audio_ext = os.path.splitext(audio_file.filename or "audio.wav")[1] or ".wav"
    video_ext = os.path.splitext(video_file.filename or "video.mp4")[1] or ".mp4"
    audio_path = os.path.join(task_dir, f"audio{audio_ext}")
    video_path = os.path.join(task_dir, f"video{video_ext}")

    audio_file.save(audio_path)
    video_file.save(video_path)
    logger.info(f"[Server] 上传完成: task={task_id}, audio={os.path.getsize(audio_path)}B, video={os.path.getsize(video_path)}B")

    task_info = _new_task(task_id, audio_file.filename, video_file.filename)
    with _tasks_lock:
        _tasks[task_id] = task_info

    _executor.submit(_run_task, task_id, audio_path, video_path)

    return jsonify({
        "code": 0,
        "msg": "任务已提交",
        "data": {"task_id": task_id, "queue": _get_queue_info()}
    })


@app.route("/api/heygem/progress", methods=["GET"])
@auth_required
def query_progress():
    """查询任务进度"""
    task_id = request.args.get("task_id", "").strip()
    if not task_id:
        return jsonify({"code": 400, "msg": "缺少 task_id"}), 400

    with _tasks_lock:
        task = _tasks.get(task_id)

    if not task:
        return jsonify({"code": 404, "msg": f"任务 {task_id} 不存在"}), 404

    queue_pos = 0
    if task["status"] == TaskStatus.QUEUED:
        with _tasks_lock:
            for t in _tasks.values():
                if t["status"] == TaskStatus.QUEUED:
                    queue_pos += 1
                if t["task_id"] == task_id:
                    break

    # ── 跨进程进度同步：从子进程写的进度文件读取真实帧数 ──
    progress = task["progress"]
    current_frame = task["current_frame"]
    message = task["message"]
    status = task["status"]
    total_frames = task["total_frames"]

    if status in (TaskStatus.PROCESSING, TaskStatus.QUEUED) and progress < 95:
        work_id = task.get("_work_id", "")
        _real_frame = 0
        _sub_error = ""
        if work_id:
            _base = os.path.dirname(os.path.abspath(__file__))
            _temp = _cfg.get("temp", "temp_dir", fallback="./temp")
            _temp = os.path.join(_base, _temp) if not os.path.isabs(_temp) else _temp
            # 检查子进程错误文件
            _ef = os.path.join(_temp, f".error_{work_id}")
            try:
                if os.path.exists(_ef):
                    with open(_ef, "r") as f:
                        _sub_error = f.read().strip()
            except Exception:
                pass
            # 读取进度文件
            _pf = os.path.join(_temp, f".progress_{work_id}")
            try:
                if os.path.exists(_pf):
                    with open(_pf, "r") as f:
                        _real_frame = int(f.read().strip())
            except Exception:
                pass
        # 子进程报错 → 立即返回错误状态
        if _sub_error:
            status = TaskStatus.ERROR
            progress = 0
            message = f"合成失败: {_sub_error}"
            # 同步更新 _tasks（主进程可能还没收到引擎的错误传递）
            _update_task(task_id, status=TaskStatus.ERROR, progress=0,
                         message=message, error=_sub_error, finished_at=time.time())
        elif _real_frame > 0 and total_frames > 0:
            # 从子进程文件获取到真实进度
            current_frame = _real_frame
            pct = min(95, int(_real_frame / total_frames * 90) + 5)
            progress = pct
            status = TaskStatus.SYNTHESIZING
            message = f"合成中 {_real_frame}/{total_frames} 帧 ({pct}%)"
        elif total_frames > 0 and task.get("started_at", 0) > 0:
            # 估算进度（fallback）：基于已消耗时间和经验速率
            elapsed = time.time() - task["started_at"]
            # 预处理约 10s，之后约每秒 1 帧（含 chaofen）
            est_frame = max(0, int((elapsed - 10) * 1.0))
            est_frame = min(est_frame, total_frames - 1)
            if est_frame > current_frame:
                current_frame = est_frame
                pct = min(90, int(est_frame / total_frames * 85) + 5)
                progress = pct
                status = TaskStatus.SYNTHESIZING
                message = f"合成中... 预计进度 {pct}%"
        elif total_frames == 0 and task.get("started_at", 0) > 0:
            # 预处理阶段（视频帧数尚未确定），展示基于时间的假进度（5%~20%）
            elapsed = time.time() - task["started_at"]
            pct = min(20, 5 + int(elapsed / 2))
            if pct > progress:
                progress = pct
                status = TaskStatus.PROCESSING
                message = f"预处理中... ({int(elapsed)}s)"
        elif status == TaskStatus.QUEUED and task.get("created_at", 0) > 0:
            # 排队中也展示假进度（1%~5%），避免客户端看到 0%
            elapsed = time.time() - task["created_at"]
            pct = min(5, 1 + int(elapsed / 10))
            if pct > progress:
                progress = pct
                message = f"排队等待中... (第{queue_pos}位)"

    return jsonify({
        "code": 0,
        "data": {
            "task_id": task["task_id"],
            "status": status,
            "progress": progress,
            "message": message,
            "total_frames": total_frames,
            "current_frame": current_frame,
            "queue_position": queue_pos,
            "queue": _get_queue_info(),
            "created_at": task["created_at"],
            "started_at": task["started_at"],
            "finished_at": task["finished_at"],
            "error": task["error"],
        }
    })


@app.route("/api/heygem/download", methods=["GET"])
@auth_required
def download_result():
    """下载合成结果视频"""
    task_id = request.args.get("task_id", "").strip()
    if not task_id:
        return jsonify({"code": 400, "msg": "缺少 task_id"}), 400

    with _tasks_lock:
        task = _tasks.get(task_id)

    if not task:
        return jsonify({"code": 404, "msg": f"任务 {task_id} 不存在"}), 404

    if task["status"] != TaskStatus.DONE:
        return jsonify({"code": 400, "msg": f"任务尚未完成 (当前状态: {task['status']})"}), 400

    result_path = task.get("result_path", "")
    if not result_path or not os.path.exists(result_path):
        return jsonify({"code": 404, "msg": "结果文件不存在"}), 404

    return send_file(result_path, mimetype="video/mp4", as_attachment=False,
                     download_name=f"{task_id}.mp4")


@app.route("/api/heygem/queue", methods=["GET"])
@auth_required
def queue_status():
    """查询队列整体状态"""
    info = _get_queue_info()
    with _tasks_lock:
        task_list = []
        for t in _tasks.values():
            task_list.append({
                "task_id": t["task_id"],
                "status": t["status"],
                "progress": t["progress"],
                "created_at": t["created_at"],
            })
    info["tasks"] = task_list
    return jsonify({"code": 0, "data": info})


@app.route("/api/heygem/health", methods=["GET"])
def health_check():
    """健康检查"""
    return jsonify({
        "code": 0,
        "msg": "ok",
        "initialized": _task_instance is not None,
        "queue": _get_queue_info(),
    })


# ============================================================
#  资产管理 API（音色 / 数字人）
# ============================================================

@app.route("/api/asset/upload", methods=["POST"])
@auth_required
def upload_asset():
    """
    上传音色或数字人文件

    multipart/form-data:
      - file: 文件（音频.wav/.mp3 或 视频.mp4）
      - license_key: 卡密
      - asset_type: 'voice' | 'avatar'
      - name: 资产名称
    """
    uploaded = request.files.get("file")
    license_key = request.form.get("license_key", "").strip()
    asset_type = request.form.get("asset_type", "").strip()
    name = request.form.get("name", "").strip()

    if not uploaded:
        return jsonify({"code": 400, "msg": "缺少 file"}), 400
    if not license_key:
        return jsonify({"code": 400, "msg": "缺少 license_key"}), 400
    if asset_type not in ("voice", "avatar"):
        return jsonify({"code": 400, "msg": "asset_type 必须为 voice 或 avatar"}), 400
    if not name:
        name = os.path.splitext(uploaded.filename or "unnamed")[0]

    ext = os.path.splitext(uploaded.filename or "")[1] or (".wav" if asset_type == "voice" else ".mp4")

    # 保存到资产目录（先落临时文件，再计算 hash 做去重）
    asset_subdir = os.path.join(ASSET_DIR, license_key, asset_type)
    os.makedirs(asset_subdir, exist_ok=True)
    tmp_id = str(uuid.uuid4()).replace("-", "")[:12]
    tmp_path = os.path.join(asset_subdir, f"_tmp_{tmp_id}{ext}")
    uploaded.save(tmp_path)

    file_hash = _md5_of_file(tmp_path)
    file_size = os.path.getsize(tmp_path)
    now = time.time()

    # DB 去重：同一 license + type + hash + ext 若未过期，直接复用
    with _db_lock:
        conn = _get_db()
        existed = conn.execute(
            "SELECT id, name, file_size, file_hash, file_ext FROM assets "
            "WHERE license_key=? AND asset_type=? AND file_hash=? AND file_ext=? AND expires_at>? "
            "ORDER BY created_at DESC LIMIT 1",
            (license_key, asset_type, file_hash, ext, now),
        ).fetchone()

        if existed:
            conn.close()
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

            # 刷新文件池 mtime，避免被清理
            pool_dest = _pool_path(file_hash, ext)
            if os.path.exists(pool_dest):
                try:
                    os.utime(pool_dest, None)
                except Exception:
                    pass

            logger.info(f"[Asset] 去重命中: id={existed['id']} type={asset_type} key={license_key} hash={file_hash}")
            return jsonify({
                "code": 0,
                "data": {
                    "id": existed["id"],
                    "name": name or existed["name"],
                    "asset_type": asset_type,
                    "file_hash": existed["file_hash"],
                    "file_ext": existed["file_ext"],
                    "file_size": existed["file_size"],
                }
            })

        # 文件落盘：用 hash 命名，避免同内容重复文件
        dest_path = os.path.join(asset_subdir, f"{file_hash}{ext}")
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
            shutil.move(tmp_path, dest_path)
        else:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        # 同时复制到文件池（供合成使用）
        pool_dest = _pool_path(file_hash, ext)
        if not os.path.exists(pool_dest):
            shutil.copy2(dest_path, pool_dest)
        else:
            try:
                os.utime(pool_dest, None)
            except Exception:
                pass

        # 写入 DB
        conn.execute(
            "INSERT INTO assets (license_key, asset_type, name, file_hash, file_ext, file_path, file_size, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (license_key, asset_type, name, file_hash, ext, dest_path, file_size, now, now + ASSET_TTL)
        )
        conn.commit()
        asset_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

    logger.info(f"[Asset] 上传: id={asset_id} type={asset_type} name={name} key={license_key} hash={file_hash} size={file_size}")

    return jsonify({
        "code": 0,
        "data": {
            "id": asset_id,
            "name": name,
            "asset_type": asset_type,
            "file_hash": file_hash,
            "file_ext": ext,
            "file_size": file_size,
        }
    })


@app.route("/api/asset/list", methods=["GET"])
@auth_required
def list_assets():
    """
    查询资产列表

    GET /api/asset/list?license_key=xxx&asset_type=voice
    """
    license_key = request.args.get("license_key", "").strip()
    asset_type = request.args.get("asset_type", "").strip()

    if not license_key:
        return jsonify({"code": 400, "msg": "缺少 license_key"}), 400

    now = time.time()
    with _db_lock:
        conn = _get_db()
        if asset_type:
            rows = conn.execute(
                "SELECT id, asset_type, name, file_hash, file_ext, file_size, created_at, expires_at "
                "FROM assets WHERE license_key=? AND asset_type=? AND expires_at>? ORDER BY created_at DESC",
                (license_key, asset_type, now)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, asset_type, name, file_hash, file_ext, file_size, created_at, expires_at "
                "FROM assets WHERE license_key=? AND expires_at>? ORDER BY created_at DESC",
                (license_key, now)
            ).fetchall()
        conn.close()

    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "asset_type": r["asset_type"],
            "name": r["name"],
            "file_hash": r["file_hash"],
            "file_ext": r["file_ext"],
            "file_size": r["file_size"],
            "created_at": r["created_at"],
            "days_left": max(0, int((r["expires_at"] - now) / 86400)),
        })

    return jsonify({"code": 0, "data": items})


@app.route("/api/asset/delete", methods=["POST"])
@auth_required
def delete_asset():
    """删除资产"""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"code": 400, "msg": "请求体必须是合法JSON"}), 400

    asset_id = data.get("id", 0)
    license_key = data.get("license_key", "").strip()

    if not asset_id or not license_key:
        return jsonify({"code": 400, "msg": "缺少 id 或 license_key"}), 400

    with _db_lock:
        conn = _get_db()
        row = conn.execute(
            "SELECT file_path FROM assets WHERE id=? AND license_key=?",
            (asset_id, license_key)
        ).fetchone()
        if row:
            # 删除文件
            try:
                if os.path.exists(row["file_path"]):
                    os.remove(row["file_path"])
            except Exception:
                pass
            conn.execute("DELETE FROM assets WHERE id=? AND license_key=?", (asset_id, license_key))
            conn.commit()
        conn.close()

    return jsonify({"code": 0, "msg": "已删除"})


# ============================================================
#  WebSocket 任务处理
# ============================================================

def _handle_ws_task(task_msg: dict):
    """
    处理来自 WebSocket 的任务

    支持的任务类型：
    - delete_asset: 删除资产
    - upload_asset: 上传资产（从 API 服务器下载文件并保存）
    - heygem_submit: HeyGem 视频合成（未来扩展）
    """
    global _ws_client

    task_type = task_msg.get("task_type", task_msg.get("type", ""))
    request_id = task_msg.get("request_id", "")
    key = task_msg.get("key", "")
    sender_fd = task_msg.get("sender_fd", 0)
    payload = task_msg.get("payload", {})

    logger.info(f"[WS Task] 处理任务: type={task_type} request_id={request_id}")

    try:
        if task_type == "delete_asset":
            # 删除资产
            asset_id = payload.get("id", 0)
            license_key = payload.get("license_key", "")

            if not asset_id or not license_key:
                raise ValueError("缺少 id 或 license_key")

            with _db_lock:
                conn = _get_db()
                row = conn.execute(
                    "SELECT file_path FROM assets WHERE id=? AND license_key=?",
                    (asset_id, license_key)
                ).fetchone()
                if row:
                    # 删除文件
                    try:
                        if os.path.exists(row["file_path"]):
                            os.remove(row["file_path"])
                            logger.info(f"[WS Task] 删除文件: {row['file_path']}")
                    except Exception as e:
                        logger.warning(f"[WS Task] 删除文件失败: {e}")
                    conn.execute("DELETE FROM assets WHERE id=? AND license_key=?", (asset_id, license_key))
                    conn.commit()
                    logger.info(f"[WS Task] 删除资产成功: id={asset_id}")
                else:
                    logger.warning(f"[WS Task] 资产不存在: id={asset_id}")
                conn.close()

            # 发送成功结果
            if _ws_client:
                _ws_client.send_result(
                    request_id=request_id,
                    task_type=task_type,
                    key=key,
                    sender_fd=sender_fd,
                    result={"id": asset_id, "msg": "删除成功"},
                    error=False,
                )

        elif task_type == "upload_asset":
            # 上传资产（从 API 服务器下载文件并保存）
            file_path = payload.get("file_path", "")
            asset_type = payload.get("asset_type", "")
            name = payload.get("name", "")
            license_key = payload.get("license_key", "")
            original_filename = payload.get("original_filename", "")

            if not file_path or not asset_type or not name or not license_key:
                raise ValueError("缺少必要参数")

            # 读取文件内容
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 计算文件 hash
            file_hash = _md5_of_file(file_path)
            file_ext = os.path.splitext(original_filename)[1] or os.path.splitext(file_path)[1]
            file_size = os.path.getsize(file_path)

            # 保存到资产目录
            asset_file_path = os.path.join(ASSET_DIR, f"{file_hash}{file_ext}")
            shutil.copy2(file_path, asset_file_path)

            # 保存到数据库
            now = time.time()
            expires_at = now + ASSET_TTL

            with _db_lock:
                conn = _get_db()
                conn.execute(
                    """INSERT INTO assets (license_key, asset_type, name, file_hash, file_ext,
                       file_path, file_size, created_at, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (license_key, asset_type, name, file_hash, file_ext,
                     asset_file_path, file_size, now, expires_at)
                )
                asset_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.commit()
                conn.close()

            # 删除临时文件
            try:
                os.remove(file_path)
            except Exception:
                pass

            logger.info(f"[WS Task] 上传资产成功: id={asset_id} name={name}")

            # 发送成功结果
            if _ws_client:
                _ws_client.send_result(
                    request_id=request_id,
                    task_type=task_type,
                    key=key,
                    sender_fd=sender_fd,
                    result={"id": asset_id, "name": name, "msg": "上传成功"},
                    error=False,
                )

        elif task_type == "heygem_submit":
            # HeyGem 视频合成（通过 WS 代理提交）
            audio_hash = payload.get("audio_hash", "").strip()
            audio_ext = payload.get("audio_ext", ".wav").strip()
            video_hash = payload.get("video_hash", "").strip()
            video_ext = payload.get("video_ext", ".mp4").strip()

            if not audio_hash or not video_hash:
                raise ValueError("缺少 audio_hash 或 video_hash")

            audio_path = _resolve_to_pool(audio_hash, audio_ext)
            video_path = _resolve_to_pool(video_hash, video_ext)

            if not audio_path:
                raise FileNotFoundError(f"音频文件不存在: {audio_hash}{audio_ext}")
            if not video_path:
                raise FileNotFoundError(f"视频文件不存在: {video_hash}{video_ext}")

            # 创建任务并提交到执行器
            task_id = request_id or str(uuid.uuid4()).replace("-", "")[:16]
            cache_key = hashlib.md5(f"{audio_hash}_{video_hash}".encode()).hexdigest()[:16]

            # 缓存命中检查
            cache_result_dir = os.path.join(OUTPUT_DIR, f"cache_{cache_key}")
            cache_result_file = os.path.join(cache_result_dir, f"cache_{cache_key}.mp4")
            if os.path.exists(cache_result_file) and os.path.getsize(cache_result_file) > 0:
                try:
                    os.utime(cache_result_file, None)
                except Exception:
                    pass
                task_id = cache_key
                task_info = _new_task(task_id, f"{audio_hash}{audio_ext}", f"{video_hash}{video_ext}")
                task_info.update({
                    "status": TaskStatus.DONE, "progress": 100,
                    "message": "合成完成（缓存命中）",
                    "result_path": os.path.realpath(cache_result_file),
                    "finished_at": time.time(), "started_at": time.time(),
                })
                with _tasks_lock:
                    _tasks[task_id] = task_info
                logger.info(f"[WS Task] 缓存命中: cache_key={cache_key}")
            else:
                task_info = _new_task(task_id, f"{audio_hash}{audio_ext}", f"{video_hash}{video_ext}")
                task_info["_cache_key"] = cache_key
                with _tasks_lock:
                    _tasks[task_id] = task_info
                _executor.submit(_run_task, task_id, audio_path, video_path)
                logger.info(f"[WS Task] 合成任务已提交: task={task_id} audio={audio_hash} video={video_hash}")

            if _ws_client:
                _ws_client.send_result(
                    request_id=request_id,
                    task_type=task_type,
                    key=key,
                    sender_fd=sender_fd,
                    result={"task_id": task_id, "queue": _get_queue_info()},
                    error=False,
                )

        else:
            logger.warning(f"[WS Task] 未知任务类型: {task_type}")
            if _ws_client:
                _ws_client.send_result(
                    request_id=request_id,
                    task_type=task_type,
                    key=key,
                    sender_fd=sender_fd,
                    error=True,
                    error_msg=f"未知任务类型: {task_type}",
                )

    except Exception as e:
        logger.error(f"[WS Task] 任务执行失败: {e}", exc_info=True)
        if _ws_client:
            _ws_client.send_result(
                request_id=request_id,
                task_type=task_type,
                key=key,
                sender_fd=sender_fd,
                error=True,
                error_msg=str(e),
            )


# ============================================================
#  视频编辑 API（字幕 / 画中画 / BGM）
# ============================================================

@app.route("/api/video/edit", methods=["POST"])
@auth_required
def video_edit():
    """
    视频后期编辑（通过 ffmpeg）

    multipart/form-data:
      - video: 主视频文件（或 video_hash + video_ext 引用文件池）
      - edit_type: 'subtitle' | 'pip' | 'bgm' | 'multi'
      - subtitle_text: 字幕文本（edit_type=subtitle 时）
      - subtitle_style: 字幕样式 JSON（可选）
      - pip_video: 画中画视频文件（edit_type=pip 时）
      - pip_position: 画中画位置 'top-left'|'top-right'|'bottom-left'|'bottom-right'（默认 bottom-right）
      - pip_scale: 画中画缩放比例（默认 0.3）
      - bgm_audio: BGM音频文件（edit_type=bgm 时）
      - bgm_volume: BGM音量 0.0~1.0（默认 0.15）
    """
    edit_type = request.form.get("edit_type", "").strip()
    if not edit_type:
        return jsonify({"code": 400, "msg": "缺少 edit_type"}), 400

    # 获取主视频
    video_file = request.files.get("video")
    video_hash = request.form.get("video_hash", "").strip()
    video_ext = request.form.get("video_ext", ".mp4").strip()

    task_id = str(uuid.uuid4()).replace("-", "")[:16]
    work_dir = os.path.join(OUTPUT_DIR, f"edit_{task_id}")
    os.makedirs(work_dir, exist_ok=True)

    if video_file:
        video_path = os.path.join(work_dir, f"input{video_ext}")
        video_file.save(video_path)
    elif video_hash:
        video_path = _pool_path(video_hash, video_ext)
        if not os.path.exists(video_path):
            return jsonify({"code": 404, "msg": "视频文件不存在，请先上传"}), 404
    else:
        return jsonify({"code": 400, "msg": "缺少 video 文件或 video_hash"}), 400

    output_path = os.path.join(work_dir, f"output_{task_id}.mp4")

    try:
        if edit_type == "subtitle":
            _edit_subtitle(video_path, output_path, work_dir)
        elif edit_type == "pip":
            _edit_pip(video_path, output_path, work_dir)
        elif edit_type == "bgm":
            _edit_bgm(video_path, output_path, work_dir)
        elif edit_type == "multi":
            # 多步骤：先字幕，再画中画，再BGM
            step1 = os.path.join(work_dir, "step1.mp4")
            step2 = os.path.join(work_dir, "step2.mp4")
            has_sub = request.form.get("subtitle_text", "").strip()
            has_pip = request.files.get("pip_video")
            has_bgm = request.files.get("bgm_audio")

            current = video_path
            if has_sub:
                _edit_subtitle(current, step1, work_dir)
                current = step1
            if has_pip:
                _edit_pip(current, step2, work_dir)
                current = step2
            if has_bgm:
                _edit_bgm(current, output_path, work_dir)
            elif current != video_path:
                shutil.copy2(current, output_path)
            else:
                shutil.copy2(video_path, output_path)
        else:
            return jsonify({"code": 400, "msg": f"不支持的 edit_type: {edit_type}"}), 400

        if not os.path.exists(output_path):
            raise RuntimeError("ffmpeg 未生成输出文件")

        # 将结果存入文件池
        result_hash = _md5_of_file(output_path)
        pool_result = _pool_path(result_hash, ".mp4")
        if not os.path.exists(pool_result):
            shutil.copy2(output_path, pool_result)

        logger.info(f"[VideoEdit] 完成: task={task_id} type={edit_type} result_hash={result_hash}")

        return jsonify({
            "code": 0,
            "data": {
                "task_id": task_id,
                "result_hash": result_hash,
                "download_url": f"/api/video/edit/download?task_id={task_id}",
            }
        })

    except Exception as e:
        logger.error(f"[VideoEdit] 失败: {task_id}\n{traceback.format_exc()}")
        return jsonify({"code": 500, "msg": f"编辑失败: {e}"}), 500


def _edit_subtitle(video_path, output_path, work_dir):
    """添加字幕（支持 title_text 顶部两行标题 + subtitle_text 底部字幕）"""
    text = request.form.get("subtitle_text", "").strip()
    title_text = request.form.get("title_text", "").strip()
    if not text and not title_text:
        shutil.copy2(video_path, output_path)
        return

    style_json = request.form.get("subtitle_style", "{}").strip()
    try:
        style = json.loads(style_json)
    except Exception:
        style = {}

    fontsize = style.get("fontsize", 24)
    fontcolor = style.get("fontcolor", "white")
    borderw = style.get("borderw", 2)
    y_pos = style.get("y", "h-th-40")

    # 获取视频时长
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True
    )
    try:
        duration = float(probe.stdout.strip())
    except Exception:
        duration = 30.0

    # 构建 ASS 字幕文件（支持标题 + 正文双轨）
    ass_path = os.path.join(work_dir, "sub.ass")
    title_fontsize = style.get("title_fontsize", 36)
    title_duration = float(style.get("title_duration", min(5.0, duration)))

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n")
        f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        # 标题样式：顶部居中，大字
        f.write(f"Style: Title,Arial,{title_fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
                f"1,0,0,0,100,100,0,0,1,3,1,8,20,20,30,1\n")
        # 正文字幕样式：底部居中
        f.write(f"Style: Sub,Arial,{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
                f"0,0,0,0,100,100,0,0,3,{borderw},0,2,20,20,40,1\n")
        f.write("\n[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

        # 写标题（顶部两行，持续 title_duration 秒）
        if title_text:
            # 按标点或长度拆成两行
            title_lines = _split_title_two_lines(title_text)
            title_display = "\\N".join(title_lines)  # ASS 换行符
            f.write(f"Dialogue: 1,{_ass_time(0)},{_ass_time(title_duration)},Title,,0,0,0,,{title_display}\n")

        # 写底部字幕
        if text:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                lines = [text]
            seg_dur = duration / len(lines) if lines else duration
            for i, line in enumerate(lines):
                start = i * seg_dur
                end = min((i + 1) * seg_dur, duration)
                f.write(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Sub,,0,0,0,,{line}\n")

    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
    cmd = (
        f'ffmpeg -y -i "{video_path}" '
        f'-vf "ass=\'{ass_escaped}\'" '
        f'-c:v libx264 -profile:v baseline -level 3.1 -pix_fmt yuv420p -movflags +faststart '
        f'-c:a copy "{output_path}"'
    )
    logger.info(f"[Subtitle] {cmd}")
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        # fallback: 用 SRT + subtitles filter（不支持标题）
        logger.warning(f"[Subtitle] ASS 字幕烧录失败，回退到 SRT")
        srt_path = os.path.join(work_dir, "sub.srt")
        lines = [l.strip() for l in (text or title_text).split("\n") if l.strip()] or [text or title_text]
        seg_dur = duration / len(lines) if lines else duration
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, line in enumerate(lines):
                start = i * seg_dur
                end = min((i + 1) * seg_dur, duration)
                f.write(f"{i+1}\n")
                f.write(f"{_srt_time(start)} --> {_srt_time(end)}\n")
                f.write(f"{line}\n\n")
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        cmd2 = (
            f'ffmpeg -y -i "{video_path}" '
            f'-vf "subtitles=\'{srt_escaped}\':force_style=\'FontSize={fontsize},PrimaryColour=&Hffffff&,'
            f'BorderStyle=3,Outline={borderw}\'" '
            f'-c:v libx264 -profile:v baseline -level 3.1 -pix_fmt yuv420p -movflags +faststart '
            f'-c:a copy "{output_path}"'
        )
        subprocess.call(cmd2, shell=True)


def _split_title_two_lines(title: str) -> list:
    """将标题按标点或中点拆成两行"""
    split_chars = ['·', '|', '—', '，', ',', '：', ':', '、']
    for ch in split_chars:
        if ch in title:
            parts = title.split(ch, 1)
            return [p.strip() for p in parts if p.strip()]
    # 没有标点，按长度对半分
    mid = len(title) // 2
    return [title[:mid].strip(), title[mid:].strip()] if len(title) > 6 else [title]


def _ass_time(seconds):
    """格式化为 ASS 时间 H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _edit_pip(video_path, output_path, work_dir):
    """画中画叠加（支持文件上传或 pip_video_hash 引用文件池）"""
    pip_file = request.files.get("pip_video")
    pip_video_hash = request.form.get("pip_video_hash", "").strip()
    pip_video_ext = request.form.get("pip_video_ext", ".mp4").strip()

    if pip_file:
        pip_path = os.path.join(work_dir, "pip_input.mp4")
        pip_file.save(pip_path)
    elif pip_video_hash:
        pip_path = _resolve_to_pool(pip_video_hash, pip_video_ext)
        if not pip_path:
            # 也试下直接作为 URL 下载
            pip_path = ""
    else:
        shutil.copy2(video_path, output_path)
        return

    if not pip_path or not os.path.exists(pip_path):
        logger.warning(f"[PIP] PIP视频文件不存在: hash={pip_video_hash}")
        shutil.copy2(video_path, output_path)
        return

    position = request.form.get("pip_position", "bottom-right").strip()
    scale = float(request.form.get("pip_scale", "0.3"))

    pos_map = {
        "top-left": "10:10",
        "top-right": "main_w-overlay_w-10:10",
        "bottom-left": "10:main_h-overlay_h-10",
        "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
    }
    xy = pos_map.get(position, pos_map["bottom-right"])

    cmd = (
        f'ffmpeg -y -i "{video_path}" -i "{pip_path}" '
        f'-filter_complex "[1:v]scale=iw*{scale}:ih*{scale}[pip];[0:v][pip]overlay={xy}" '
        f'-c:v libx264 -profile:v baseline -level 3.1 -pix_fmt yuv420p -movflags +faststart '
        f'-c:a copy "{output_path}"'
    )
    logger.info(f"[PIP] {cmd}")
    subprocess.call(cmd, shell=True)


def _edit_bgm(video_path, output_path, work_dir):
    """添加背景音乐"""
    bgm_file = request.files.get("bgm_audio")
    if not bgm_file:
        shutil.copy2(video_path, output_path)
        return

    bgm_path = os.path.join(work_dir, "bgm_input.mp3")
    bgm_file.save(bgm_path)

    volume = float(request.form.get("bgm_volume", "0.15"))

    cmd = (
        f'ffmpeg -y -i "{video_path}" -i "{bgm_path}" '
        f'-filter_complex "[0:a]volume=1.0[a0];[1:a]volume={volume}[a1];'
        f'[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]" '
        f'-map 0:v -map "[aout]" -c:v copy -c:a aac -movflags +faststart "{output_path}"'
    )
    logger.info(f"[BGM] {cmd}")
    subprocess.call(cmd, shell=True)


@app.route("/api/video/edit/download", methods=["GET"])
@auth_required
def download_edit_result():
    """下载编辑后的视频"""
    task_id = request.args.get("task_id", "").strip()
    if not task_id:
        return jsonify({"code": 400, "msg": "缺少 task_id"}), 400

    work_dir = os.path.join(OUTPUT_DIR, f"edit_{task_id}")
    output_path = os.path.join(work_dir, f"output_{task_id}.mp4")

    if not os.path.exists(output_path):
        return jsonify({"code": 404, "msg": "结果文件不存在"}), 404

    return send_file(output_path, mimetype="video/mp4", as_attachment=False,
                     download_name=f"edit_{task_id}.mp4")


# ============================================================
#  自动清理
# ============================================================
def _cleanup_old_files():
    while True:
        try:
            time.sleep(CLEANUP_INTERVAL)
            now = time.time()
            cleaned = 0

            # 不清理的固定子目录（pool/assets 由各自策略管理）
            _protected_dirs = {"pool", "assets", "work"}
            for base_dir in [UPLOAD_DIR, OUTPUT_DIR]:
                if not os.path.isdir(base_dir):
                    continue
                for name in os.listdir(base_dir):
                    if name in _protected_dirs:
                        continue
                    path = os.path.join(base_dir, name)
                    try:
                        mtime = os.path.getmtime(path)
                        if now - mtime > FILE_TTL:
                            if os.path.isdir(path):
                                shutil.rmtree(path, ignore_errors=True)
                            else:
                                os.remove(path)
                            cleaned += 1
                    except Exception as e:
                        logger.warning(f"[Cleanup] 清理失败 {path}: {e}")

            # 清理 pool 目录内过期文件（合成音频保留 1 天）
            if os.path.isdir(FILE_POOL_DIR):
                for name in os.listdir(FILE_POOL_DIR):
                    path = os.path.join(FILE_POOL_DIR, name)
                    try:
                        mtime = os.path.getmtime(path)
                        if now - mtime > FILE_TTL:
                            os.remove(path)
                            cleaned += 1
                    except Exception:
                        pass

            expired_ids = []
            with _tasks_lock:
                for tid, t in _tasks.items():
                    if t["status"] in (TaskStatus.DONE, TaskStatus.ERROR):
                        if now - t.get("finished_at", t["created_at"]) > FILE_TTL:
                            expired_ids.append(tid)
                for tid in expired_ids:
                    del _tasks[tid]

            # 清理过期资产（SQLite + 文件）
            asset_cleaned = 0
            try:
                with _db_lock:
                    conn = _get_db()
                    expired_rows = conn.execute(
                        "SELECT id, file_path FROM assets WHERE expires_at < ?", (now,)
                    ).fetchall()
                    for row in expired_rows:
                        try:
                            if os.path.exists(row["file_path"]):
                                os.remove(row["file_path"])
                        except Exception:
                            pass
                        asset_cleaned += 1
                    if expired_rows:
                        conn.execute("DELETE FROM assets WHERE expires_at < ?", (now,))
                        conn.commit()
                    conn.close()
            except Exception as ae:
                logger.warning(f"[Cleanup] 资产清理异常: {ae}")

            if cleaned or expired_ids or asset_cleaned:
                logger.info(f"[Cleanup] 清理完成: 文件/目录 {cleaned} 个, 任务记录 {len(expired_ids)} 条, 过期资产 {asset_cleaned} 个")
        except Exception as e:
            logger.error(f"[Cleanup] 清理线程异常: {e}")


# ============================================================
#  初始化与启动
# ============================================================
def _init_service():
    global _task_instance
    sys.argv = [sys.argv[0]]

    # 确保 temp/result 目录存在（config.ini 中配置的路径）
    _base = os.path.dirname(os.path.abspath(__file__))
    for _sec, _key in [("temp", "temp_dir"), ("result", "result_dir")]:
        _d = _cfg.get(_sec, _key, fallback="")
        if _d:
            _d = os.path.join(_base, _d) if not os.path.isabs(_d) else _d
            os.makedirs(_d, exist_ok=True)
            logger.info(f"[Server] 目录就绪: [{_sec}] {_d}")

    # CWD 保持在 _BASE_DIR（文件顶部已设置），引擎的 ./temp/ 和 ./result/
    # 都依赖 CWD = /root/HeyGem/，不能再切换，否则 format_video 找不到 ./temp/
    logger.info(f"[Server] CWD 保持在: {os.getcwd()}")

    logger.info("[Server] 正在初始化数字人推理服务...")
    _task_instance = service.trans_dh_service.TransDhTask()
    time.sleep(10)
    logger.info("[Server] 数字人推理服务初始化完成")


def _init_ws_client():
    """初始化 WebSocket 客户端"""
    global _ws_client

    if not WS_ENABLED:
        logger.info("[Server] WebSocket 客户端未启用")
        return

    logger.info(f"[Server] 正在启动 WebSocket 客户端: {WS_API_URL}")
    _ws_client = GpuWebSocketClient(
        ws_url=WS_API_URL,
        on_task_callback=_handle_ws_task,
        reconnect_interval=5,
        max_reconnect_interval=30,
    )
    _ws_client.start()
    logger.info("[Server] WebSocket 客户端已启动")


def get_args():
    parser = argparse.ArgumentParser(
        description="HeyGem Linux 在线合成服务",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8383, help="监听端口")
    parser.add_argument("--max-concurrent", type=int, default=None,
                        help=f"最大并发数 (默认读 config.ini: {MAX_CONCURRENT})")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    if args.max_concurrent is not None:
        MAX_CONCURRENT = args.max_concurrent
        _semaphore = threading.Semaphore(MAX_CONCURRENT)
        logger.info(f"[Server] 命令行指定最大并发: {MAX_CONCURRENT}")

    _init_service()

    # 启动 WebSocket 客户端
    _init_ws_client()

    cleanup_thread = threading.Thread(target=_cleanup_old_files, daemon=True)
    cleanup_thread.start()
    logger.info(f"[Server] 清理线程已启动 (TTL={FILE_TTL}s, 间隔={CLEANUP_INTERVAL}s)")

    logger.info(f"[Server] 启动 API: {args.host}:{args.port} (最大并发={MAX_CONCURRENT})")
    logger.info("[Server] 接口列表:")
    logger.info("  POST /api/heygem/check_files   - 检查文件是否已在服务器(hash去重)")
    logger.info("  POST /api/heygem/upload_file   - 上传单个文件到文件池")
    logger.info("  POST /api/heygem/submit        - 通过hash提交合成任务")
    logger.info("  POST /api/heygem/upload         - 上传音视频并提交合成(兼容)")
    logger.info("  GET  /api/heygem/progress       - 查询任务进度")
    logger.info("  GET  /api/heygem/download       - 下载合成结果")
    logger.info("  GET  /api/heygem/queue          - 查询队列状态")
    logger.info("  GET  /api/heygem/health         - 健康检查")
    logger.info("  POST /api/asset/upload          - 上传音色/数字人")
    logger.info("  GET  /api/asset/list            - 查询音色/数字人列表")
    logger.info("  POST /api/asset/delete          - 删除音色/数字人")
    logger.info("  POST /api/video/edit            - 视频编辑(字幕/画中画/BGM)")
    logger.info("  GET  /api/video/edit/download   - 下载编辑后视频")

    app.run(host=args.host, port=args.port, threaded=True)
