"""
视频转文字 Worker

流程:
1. 启动 Playwright 浏览器，打开 shuiyinyun.com
2. 连接 Hyperf WebSocket (ws://host:9502/ws?worker=1)
3. 接收带卡密的任务，放入队列串行处理
4. 结果带上卡密发回，服务端只推给对应客户端

启动:
  python ws_worker.py
"""

import asyncio
import json
import os
import sys
import websockets
from playwright.async_api import async_playwright


# ============================================================
#  配置
# ============================================================
WS_URL = "wss://api.zhimengai.xyz/dsp"
TARGET_URL = "https://www.shuiyinyun.com/tools/#/editor/videoToText"
# 浏览器数据目录 (保存登录状态、cookie 等)
BROWSER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_data")
# 复制按钮选择器 (Vue scoped attribute，如果网站更新可能需要修改)
COPY_BUTTON_SELECTOR = ".el-button.start-button.absolute.right-\\[30rpx\\].bottom-\\[30rpx\\].el-button--primary"
# 等待转写完成的超时时间 (秒)
CONVERT_TIMEOUT = 300


class VideoToTextWorker:
    def __init__(self):
        self.ws = None
        self.page = None
        self.browser = None
        self.playwright = None
        self.queue = asyncio.Queue()  # 任务队列: (key, url)

    # ============================================================
    #  浏览器
    # ============================================================

    async def start_browser(self):
        """启动 Playwright 浏览器 (持久化登录状态)"""
        print(f"[Browser] 启动浏览器... 数据目录: {BROWSER_DATA_DIR}")
        self.playwright = await async_playwright().start()
        # 使用持久化上下文，重启后保留 cookie/登录状态
        self.context = await self.playwright.chromium.launch_persistent_context(
            BROWSER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            permissions=["clipboard-read", "clipboard-write"],
            locale="zh-CN",
            viewport=None,  # 让页面内容跟随实际窗口大小变化
            no_viewport=True,  # 禁用固定视口
        )
        # 用已有的页面或新开一个
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        # 导航到目标页面
        await self.page.goto(TARGET_URL, wait_until="networkidle")
        print(f"[Browser] 已打开: {TARGET_URL}")

        # 注入响应式 CSS，让内容随窗口大小变化
        await self.page.add_style_tag(content="""
            .main-content, .editor-container, .video-container, 
            .el-container, .el-main, [class*="container"] {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
            }
        """)
        print("[Browser] 已注入响应式 CSS")

    async def ensure_on_target_page(self):
        """确保在目标页面上"""
        current = self.page.url
        if "shuiyinyun.com" not in current or "videoToText" not in current:
            print("[Browser] 不在目标页面，重新跳转...")
            await self.page.goto(TARGET_URL, wait_until="networkidle")
            await asyncio.sleep(2)

    # ============================================================
    #  视频转文字自动化
    # ============================================================

    async def process_url(self, url: str) -> str:
        """
        处理视频链接，返回转写文字

        流程:
        1. 检查 .chooseFile-line → 点击
        2. 检查 .el-input__inner → 输入链接
        3. 如果没有输入框 → 跳转页面重试
        4. 点击 .start-button
        5. 等待复制按钮出现 → 点击 → 获取内容
        """
        page = self.page
        max_retries = 3

        # === Step 1 & 2: 找到输入框并输入链接 ===
        input_success = False
        for attempt in range(max_retries):
            print(f"[Task] 第 {attempt + 1}/{max_retries} 次尝试...")

            # 检查 .chooseFile-line
            try:
                choose_file = await page.query_selector(".chooseFile-line")
                if choose_file:
                    visible = await choose_file.is_visible()
                    if visible:
                        print("[Task] 找到 .chooseFile-line，点击...")
                        await choose_file.click()
                        await asyncio.sleep(1.5)
            except Exception as e:
                print(f"[Task] chooseFile-line 检查异常: {e}")

            # 检查 .el-input__inner 输入框
            try:
                input_el = await page.query_selector(".el-input__inner")
                if input_el:
                    visible = await input_el.is_visible()
                    if visible:
                        print(f"[Task] 找到输入框，输入链接: {url}")
                        await input_el.click()
                        # 清空并输入
                        await input_el.fill("")
                        await asyncio.sleep(0.3)
                        await input_el.fill(url)
                        await asyncio.sleep(0.5)
                        input_success = True
                        break
            except Exception as e:
                print(f"[Task] 输入框检查异常: {e}")

            # 输入框不存在，跳转到目标页面重试
            print("[Task] 未找到输入框，跳转目标页面...")
            await page.goto(TARGET_URL, wait_until="networkidle")
            await asyncio.sleep(2)

        if not input_success:
            return "错误: 多次尝试后仍未找到输入框"

        # === Step 3: 点击 .start-button ===
        print("[Task] 等待 start-button...")
        try:
            start_btn = await page.wait_for_selector(
                ".start-button", timeout=10000, state="visible"
            )
            if start_btn:
                await start_btn.click()
                print("[Task] 已点击开始按钮")
            else:
                return "错误: 未找到开始按钮"
        except Exception as e:
            return f"错误: 等待开始按钮失败 - {e}"

        # === Step 4: 等待 textarea 出现 ===
        print(f"[Task] 等待转写结果 textarea 出现 (最长 {CONVERT_TIMEOUT}s)...")
        try:
            textarea = await page.wait_for_selector(
                ".el-textarea__inner",
                timeout=CONVERT_TIMEOUT * 1000,
                state="visible",
            )
        except Exception as e:
            return f"错误: 等待转写结果超时 - {e}"

        if not textarea:
            return "错误: 转写结果未出现"

        print("[Task] textarea 已出现，等待内容填充...")

        # === Step 5: 等待 textarea 有内容 ===
        content = ""
        max_wait = CONVERT_TIMEOUT  # 最长等待时间
        check_interval = 2  # 每2秒检查一次
        waited = 0
        
        while waited < max_wait:
            try:
                # 使用 input_value() 获取 textarea 的值，保留换行符
                content = await textarea.input_value()
                
                # 备用方案: 使用 inner_text()
                if not content:
                    content = await textarea.inner_text()
                
                # 再备用: 使用 text_content()
                if not content:
                    content = await textarea.text_content()
                
                # 如果有内容了，跳出循环
                if content and content.strip():
                    print(f"[Task] 内容已填充 ({len(content)} 字)")
                    break
                    
            except Exception as e:
                print(f"[Task] 读取内容异常: {e}")
            
            # 等待后继续检查
            await asyncio.sleep(check_interval)
            waited += check_interval
            print(f"[Task] 等待内容中... ({waited}s/{max_wait}s)")

        if content and content.strip():
            print(f"[Task] 获取内容成功 ({len(content)} 字)")
        else:
            content = "错误: 等待超时，未能获取转写内容"
            print("[Task] 获取内容失败")

        # === Step 6: 点击关闭按钮 ===
        try:
            # 尝试多个可能的选择器
            selectors = [
                ".source-close.el-icon-close",  # 两个类在同一元素
                "[data-v-c643e034][data-v-068f1dba].source-close",  # 带 data 属性
                ".source-close",  # 只用第一个类
            ]
            
            close_btn = None
            for selector in selectors:
                close_btn = await page.query_selector(selector)
                if close_btn:
                    visible = await close_btn.is_visible()
                    if visible:
                        print(f"[Task] 找到关闭按钮: {selector}")
                        break
                    else:
                        close_btn = None
            
            if close_btn:
                await close_btn.click()
                print("[Task] 已点击关闭按钮")
                await asyncio.sleep(0.5)
            else:
                print("[Task] 未找到可见的关闭按钮")
                
        except Exception as e:
            print(f"[Task] 关闭按钮点击异常: {e}")

        # === Step 7: 刷新页面 ===
        try:
            await page.reload(wait_until="networkidle")
            print("[Task] 已刷新页面")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[Task] 刷新页面异常: {e}")

        return content

    # ============================================================
    #  WebSocket 通信
    # ============================================================

    # ============================================================
    #  队列消费: 串行处理任务
    # ============================================================

    async def queue_consumer(self):
        """从队列取任务，一个个处理"""
        while True:
            key, url = await self.queue.get()
            print(f"\n{'=' * 50}")
            print(f"[Queue] 开始处理: key={key}  url={url}")
            print(f"[Queue] 队列剩余: {self.queue.qsize()}")
            print(f"{'=' * 50}")

            try:
                await self.ensure_on_target_page()
                result = await self.process_url(url)
            except Exception as e:
                print(f"[Queue] 处理异常: {e}")
                result = f"处理失败: {e}"

            # 发回结果，带上 key
            if self.ws:
                try:
                    await self.ws.send(json.dumps({
                        "type": "result",
                        "key": key,
                        "content": result,
                    }, ensure_ascii=False))
                    print(f"[Queue] 结果已发送 → key={key} ({len(result)} 字)")
                except Exception as e:
                    print(f"[Queue] 发送失败: {e}")

            self.queue.task_done()

    # ============================================================
    #  WebSocket 通信
    # ============================================================

    async def ws_loop(self):
        """WebSocket 消息循环，自动重连"""
        while True:
            try:
                print(f"\n[WS] 连接: {WS_URL}")
                async with websockets.connect(
                    WS_URL,
                    ping_interval=30,
                    ping_timeout=10,
                    max_size=10 * 1024 * 1024,
                ) as ws:
                    self.ws = ws
                    print("[WS] 已连接")

                    # 注册为 worker
                    await ws.send(json.dumps({"type": "register", "role": "worker"}))
                    print("[WS] 已发送注册")

                    # 启动心跳
                    heartbeat = asyncio.create_task(self._heartbeat(ws))

                    try:
                        async for raw in ws:
                            print(f"[WS] 收到原始消息: {raw[:200]}")
                            try:
                                data = json.loads(raw)
                                msg_type = data.get("type", "")

                                if msg_type == "connected":
                                    print(f"[WS] 服务端: {data.get('role', '')}")

                                elif msg_type == "pong":
                                    pass

                                elif msg_type == "url":
                                    key = data.get("key", "")
                                    url = data.get("url", "")
                                    self.queue.put_nowait((key, url))
                                    print(f"[WS] 任务入队: key={key}  队列: {self.queue.qsize()}")

                                else:
                                    print(f"[WS] 消息: {msg_type}")

                            except json.JSONDecodeError:
                                print(f"[WS] 无效 JSON: {raw[:100]}")
                    finally:
                        heartbeat.cancel()
                        self.ws = None

            except (
                websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError,
                OSError,
            ) as e:
                print(f"[WS] 连接断开: {e}")
            except Exception as e:
                print(f"[WS] 异常: {e}")

            print("[WS] 5 秒后重连...")
            await asyncio.sleep(5)

    async def _heartbeat(self, ws):
        """心跳保活"""
        while True:
            try:
                await asyncio.sleep(25)
                await ws.send(json.dumps({"type": "ping"}))
            except Exception:
                break

    # ============================================================
    #  主入口
    # ============================================================

    async def run(self):
        print("=" * 50)
        print("  视频转文字 Worker")
        print(f"  WS:     {WS_URL}")
        print(f"  目标:   {TARGET_URL}")
        print("=" * 50 + "\n")

        await self.start_browser()
        # 同时跑: WS 收消息 + 队列消费
        await asyncio.gather(
            self.ws_loop(),
            self.queue_consumer(),
        )

    async def cleanup(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()


if __name__ == "__main__":
    # 支持自定义 WS 地址: python ws_worker.py ws://192.168.1.100:9502/ws?worker=1
    if len(sys.argv) > 1:
        WS_URL = sys.argv[1]

    worker = VideoToTextWorker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("\n[Worker] 已停止")
