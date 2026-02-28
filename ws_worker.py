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
import re
import sys
import requests
import websockets
from playwright.async_api import async_playwright


# ============================================================
#  配置
# ============================================================
WS_URL = "wss://api.zhimengai.xyz/dsp"
TARGET_URL = "https://www.shuiyinyun.com/tools/#/editor/videoToText"
CHATGLM_VIDEO_URL = "https://chatglm.cn/video?lang=zh"
# 本地浏览器管理器 API (用于获取已打开窗口的 CDP 地址)
BROWSER_API_URL = "http://localhost:49156/profiles/open?windowId=1"
# 浏览器数据目录 (保存登录状态、cookie 等)
BROWSER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_data")
# 复制按钮选择器 (Vue scoped attribute，如果网站更新可能需要修改)
COPY_BUTTON_SELECTOR = ".el-button.start-button.absolute.right-\\[30rpx\\].bottom-\\[30rpx\\].el-button--primary"
# 等待转写完成的超时时间 (秒)
CONVERT_TIMEOUT = 600

# 等待视频生成的超时时间 (秒)
CHATGLM_VIDEO_TIMEOUT = 600
CHATGLM_CONCURRENCY = 4


class VideoToTextWorker:
    def __init__(self):
        self.ws = None
        self.page = None
        self.chatglm_page = None
        self.browser = None
        self.playwright = None
        self.context = None
        self._cdp_mode = False
        self._cdp_browser = None
        self.video_queue = asyncio.Queue()  # (key, url)
        self.chatglm_queue = asyncio.Queue()  # (key, prompt)

        self.chatglm_pages = []
        self.chatglm_worker_tasks = []
        self.error_monitor_task = None  # 错误监控任务
        self.current_task_key = None  # 当前任务的 key
        self.current_task_type = None  # 当前任务类型
        self.error_sent = False  # 是否已发送错误消息（避免重复）
        self.task_cancelled = False  # 任务是否被取消（用于中断任务）
        self.page_reset_by_monitor = False  # 页面是否已被错误监控器重置

    # ============================================================
    #  浏览器
    # ============================================================

    def get_cdp_ws_url(self, api_url: str | None = None) -> str | None:
        api_url = api_url or BROWSER_API_URL
        try:
            resp = requests.get(api_url, timeout=5)
            if resp.status_code != 200:
                return None
            data = resp.json()
            browser_ws = data.get("browser", {}).get("webSocketDebuggerUrl")
            pages = data.get("pages", [])
            if pages:
                pw = pages[0].get("webSocketDebuggerUrl")
                if pw:
                    return pw
            if browser_ws:
                m = re.search(r":(\d+)/", browser_ws)
                if m:
                    port = m.group(1)
                    lr = requests.get(f"http://127.0.0.1:{port}/json/list", timeout=5)
                    if lr.status_code == 200:
                        pl = lr.json()
                        if pl:
                            return pl[0].get("webSocketDebuggerUrl")
            return browser_ws
        except Exception as e:
            print(f"[CDP] 获取WS URL失败: {e}")
            return None

    async def start_browser_cdp(self, api_url: str | None = None):
        """通过 CDP 接管已打开的浏览器窗口（复用登录态）"""
        ws_url = self.get_cdp_ws_url(api_url)
        if not ws_url:
            raise RuntimeError("无法从 BROWSER_API_URL 获取 CDP WebSocket 地址")

        self.playwright = await async_playwright().start()
        self._cdp_mode = True

        print(f"[CDP] 连接: {ws_url}")
        self._cdp_browser = await self.playwright.chromium.connect_over_cdp(ws_url)
        self.context = self._cdp_browser.contexts[0] if self._cdp_browser.contexts else await self._cdp_browser.new_context(locale="zh-CN")

        # 复用已打开 tab（如果找不到再打开）
        self.page = None
        self.chatglm_page = None
        for p in self.context.pages:
            try:
                u = p.url
            except Exception:
                continue
            if (not self.page) and ("shuiyinyun.com" in u and "videoToText" in u):
                self.page = p
            if (not self.chatglm_page) and ("chatglm.cn" in u and "/video" in u):
                self.chatglm_page = p

        if not self.page:
            self.page = await self.context.new_page()
            await self.page.goto(TARGET_URL, wait_until="networkidle")
        print(f"[Browser] 已就绪: {self.page.url}")

        if not self.chatglm_page:
            self.chatglm_page = await self.context.new_page()
            await self.chatglm_page.goto(CHATGLM_VIDEO_URL, wait_until="networkidle")
        print(f"[Browser] 已就绪: {self.chatglm_page.url}")

        # 准备 ChatGLM 并发页面池
        self.chatglm_pages = [self.chatglm_page]
        while len(self.chatglm_pages) < CHATGLM_CONCURRENCY:
            p = await self.context.new_page()
            await p.goto(CHATGLM_VIDEO_URL, wait_until="networkidle")
            self.chatglm_pages.append(p)

        await self.setup_error_listener()
        self.error_monitor_task = asyncio.create_task(self.error_monitor_loop())
        print("[Browser] 已启动错误监控任务")

    async def start_browser(self, data_dir: str | None = None, cdp_api_url: str | None = None):
        """启动 Playwright 浏览器 (持久化登录状态)"""
        if cdp_api_url is not None:
            return await self.start_browser_cdp(cdp_api_url)

        data_dir = data_dir or BROWSER_DATA_DIR
        print(f"[Browser] 启动浏览器... 数据目录: {data_dir}")
        self.playwright = await async_playwright().start()
        # 使用持久化上下文，重启后保留 cookie/登录状态
        self.context = await self.playwright.chromium.launch_persistent_context(
            data_dir,
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

        # 额外打开 ChatGLM 视频页 (单独 tab，避免影响 shuiyinyun 流程)
        try:
            self.chatglm_page = await self.context.new_page()
            await self.chatglm_page.goto(CHATGLM_VIDEO_URL, wait_until="networkidle")
            print(f"[Browser] 已打开: {CHATGLM_VIDEO_URL}")
        except Exception as e:
            self.chatglm_page = None
            print(f"[Browser] 打开 ChatGLM 页面失败: {e}")

        # 准备 ChatGLM 并发页面池
        self.chatglm_pages = []
        if self.chatglm_page:
            self.chatglm_pages.append(self.chatglm_page)
        while len(self.chatglm_pages) < CHATGLM_CONCURRENCY:
            try:
                p = await self.context.new_page()
                await p.goto(CHATGLM_VIDEO_URL, wait_until="networkidle")
                self.chatglm_pages.append(p)
            except Exception as e:
                print(f"[Browser] 创建 ChatGLM 并发页面失败: {e}")
                break

        # 设置实时错误监听器
        await self.setup_error_listener()

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
        
        # 启动错误监控任务
        self.error_monitor_task = asyncio.create_task(self.error_monitor_loop())
        print("[Browser] 已启动错误监控任务")

    async def ensure_on_target_page(self):
        """确保在目标页面上"""
        current = self.page.url
        if "shuiyinyun.com" not in current or "videoToText" not in current:
            print("[Browser] 不在目标页面，重新跳转...")
            await self.page.goto(TARGET_URL, wait_until="networkidle")
            await asyncio.sleep(2)
            # 重新设置监听器
            await self.setup_error_listener()
        else:
            # 即使在目标页面，也检查监听器是否还在
            try:
                is_installed = await self.page.evaluate("() => window.__error_observer_installed || false")
                if not is_installed:
                    print("[Browser] 监听器丢失，重新设置...")
                    await self.setup_error_listener()
            except Exception:
                pass

    async def ensure_on_chatglm_video_page(self, page=None):
        """确保 ChatGLM 视频页可用"""
        page = page or self.chatglm_page
        if not page:
            page = await self.context.new_page()
        current = page.url
        if "chatglm.cn" not in current or "/video" not in current:
            print("[Browser] 不在 ChatGLM 视频页面，重新跳转...")
            await page.goto(CHATGLM_VIDEO_URL, wait_until="networkidle")
            await asyncio.sleep(1)
        return page

    # ============================================================
    #  错误弹窗检测
    # ============================================================

    async def error_monitor_loop(self):
        """后台持续监控错误弹窗"""
        print("[ErrorMonitor] 启动后台监控...")
        while True:
            try:
                await asyncio.sleep(0.5)  # 每0.5秒检查一次，更快响应
                
                # 只在有任务时才检查
                if not self.current_task_key or self.error_sent:
                    continue

                # 只监控 video_to_text 页面错误，避免影响其它任务（如 chatglm_video）
                if self.current_task_type != "video_to_text":
                    continue
                
                has_error, error_msg = await self.check_error_popup()
                if has_error:
                    print(f"[ErrorMonitor] 发现错误弹窗: {error_msg}")
                    # 发送错误消息给客户端
                    await self.send_result(self.current_task_key, f"错误: {error_msg}", is_error=True)
                    self.error_sent = True
                    self.task_cancelled = True  # 标记任务取消
                    
                    # 立即处理弹窗并回到初始页面
                    print("[ErrorMonitor] 开始处理弹窗并回到初始页面...")
                    try:
                        # 尝试点击确定按钮关闭弹窗
                        confirm_btn = await self.page.query_selector(".el-message-box__btns .el-button--primary")
                        if confirm_btn:
                            print("[ErrorMonitor] 点击确定按钮...")
                            await confirm_btn.click()
                            await asyncio.sleep(0.3)
                        else:
                            print("[ErrorMonitor] 未找到确定按钮")
                        
                        # 回到初始页面
                        print(f"[ErrorMonitor] 跳转到 {TARGET_URL}...")
                        await self.page.goto(TARGET_URL, wait_until="networkidle")
                        print("[ErrorMonitor] 页面加载完成，等待1秒...")
                        await asyncio.sleep(1)
                        print("[ErrorMonitor] 重新设置监听器...")
                        await self.setup_error_listener()
                        print("[ErrorMonitor] 已回到初始页面，准备处理下一个任务")
                        self.page_reset_by_monitor = True  # 标记页面已重置
                    except Exception as e:
                        print(f"[ErrorMonitor] 回到初始页面异常: {e}")
                        import traceback
                        traceback.print_exc()
                        self.page_reset_by_monitor = False  # 标记页面未重置
                    
            except Exception as e:
                print(f"[ErrorMonitor] 监控异常: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(2)

    async def get_error_message(self) -> str:
        """获取错误弹窗的消息内容"""
        try:
            message_el = await self.page.query_selector(".el-message-box__message")
            if message_el:
                message = await message_el.inner_text()
                if message:
                    return message.strip()
        except Exception as e:
            print(f"[Error] 获取错误消息异常: {e}")
        return "未知错误"

    async def check_error_popup(self) -> tuple[bool, str]:
        """检测是否出现错误弹窗，返回 (has_error, error_message)"""
        try:
            # 先检查 JS 标记
            has_flag, flag_msg = await self.check_error_flag()
            if has_flag:
                return True, flag_msg
            
            # 再检查 DOM
            error_box = await self.page.query_selector(".el-message-box__wrapper")
            if error_box:
                visible = await error_box.is_visible()
                if visible:
                    error_msg = await self.get_error_message()
                    print(f"[Error] DOM检测到错误弹窗: {error_msg}")
                    return True, error_msg
        except Exception as e:
            print(f"[Error] 检查弹窗异常: {e}")
        return False, ""

    async def handle_error_popup(self):
        """处理错误弹窗：关闭弹窗并重新进入页面"""
        print("[Error] 处理错误弹窗...")
        try:
            # 尝试点击确定按钮关闭弹窗
            confirm_btn = await self.page.query_selector(".el-message-box__btns .el-button--primary")
            if confirm_btn:
                await confirm_btn.click()
                print("[Error] 已点击确定按钮")
                await asyncio.sleep(0.5)
            
            # 重新进入页面
            await self.page.goto(TARGET_URL, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 重新设置监听器
            await self.setup_error_listener()
            print("[Error] 已重新进入页面")
        except Exception as e:
            print(f"[Error] 处理弹窗异常: {e}")

    async def setup_error_listener(self):
        """设置实时错误弹窗监听器"""
        try:
            await self.page.evaluate("""
                () => {
                    // 避免重复设置
                    if (window.__error_observer_installed) return;
                    window.__error_observer_installed = true;
                    
                    // 存储错误历史
                    window.__error_history = [];
                    
                    // 监听 DOM 变化
                    const observer = new MutationObserver((mutations) => {
                        for (const mutation of mutations) {
                            for (const node of mutation.addedNodes) {
                                if (node.nodeType === 1) {
                                    // 检查是否是弹窗元素
                                    let wrapper = null;
                                    if (node.classList?.contains('el-message-box__wrapper')) {
                                        wrapper = node;
                                    } else if (node.querySelector) {
                                        wrapper = node.querySelector('.el-message-box__wrapper');
                                    }
                                    
                                    if (wrapper) {
                                        // 获取错误消息
                                        const msgEl = wrapper.querySelector('.el-message-box__message');
                                        const msg = msgEl?.innerText || msgEl?.textContent || '未知错误';
                                        
                                        // 记录错误
                                        const error = {
                                            time: Date.now(),
                                            message: msg.trim(),
                                            detected: true
                                        };
                                        
                                        window.__error_history.push(error);
                                        console.log('[ErrorListener] 检测到弹窗:', msg);
                                    }
                                }
                            }
                        }
                    });
                    
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true
                    });
                    
                    console.log('[ErrorListener] 监听器已安装');
                }
            """)
            print("[Browser] 已设置实时错误监听器")
        except Exception as e:
            print(f"[Browser] 设置错误监听器异常: {e}")

    async def check_error_flag(self) -> tuple[bool, str]:
        """检查页面中的错误标记（不清除历史）"""
        try:
            result = await self.page.evaluate("""
                () => {
                    if (!window.__error_history || window.__error_history.length === 0) {
                        return {detected: false, message: ''};
                    }
                    
                    // 获取最新的错误
                    const latest = window.__error_history[window.__error_history.length - 1];
                    
                    // 检查是否是最近5秒内的错误
                    const isRecent = (Date.now() - latest.time) < 5000;
                    
                    return {
                        detected: isRecent,
                        message: latest.message,
                        count: window.__error_history.length
                    };
                }
            """)
            detected = result.get('detected', False)
            message = result.get('message', '')
            if detected:
                print(f"[ErrorFlag] 检测到错误: {message} (历史: {result.get('count', 0)})")
            return detected, message
        except Exception as e:
            print(f"[ErrorFlag] 检查异常: {e}")
            return False, ""

    # ============================================================
    #  WebSocket 发送结果
    # ============================================================

    async def send_result(self, key: str, content: str, is_error: bool = False, result_type: str = "result"):
        """发送结果给客户端
        
        Args:
            key: 客户端标识
            content: 结果内容
            is_error: 是否为错误
            result_type: 消息类型 ("result" 用于视频转文字, "chatglm_video_result" 用于视频生成)
        """
        if self.ws:
            try:
                if result_type == "chatglm_video_result":
                    # chatglm_video 结果格式
                    payload = {
                        "type": "chatglm_video_result",
                        "key": key,
                    }
                    if is_error:
                        payload["error"] = True
                        payload["error_msg"] = content
                    else:
                        payload["video_url"] = content
                        payload["cover_url"] = ""  # 暂无封面
                else:
                    # 视频转文字结果格式
                    payload = {
                        "type": "result",
                        "key": key,
                        "content": content,
                    }
                    if is_error:
                        payload["error"] = True
                
                # 发送 JSON，并将 \/ 还原为 / (避免 URL 被转义)
                json_str = json.dumps(payload, ensure_ascii=False).replace(r'\/', '/')
                await self.ws.send(json_str)
                tag = "错误" if is_error else "结果"
                print(f"[WS→Client] {tag}已发送 → type={result_type} key={key} ({len(content)} 字)")
            except Exception as e:
                print(f"[WS→Client] 发送失败: {e}")

    # ============================================================
    #  视频转文字自动化
    # ============================================================

    async def process_url(self, url: str, key: str) -> str:
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
            # 检查任务是否被取消
            if self.task_cancelled:
                print("[Task] 任务已被取消，停止处理")
                return "错误: 任务已取消"
            
            print(f"[Task] 第 {attempt + 1}/{max_retries} 次尝试...")

            # 检测错误弹窗
            has_error, error_msg = await self.check_error_popup()
            if has_error:
                print(f"[Task] 检测到错误弹窗: {error_msg}")
                if not self.error_sent:
                    await self.send_result(key, f"错误: {error_msg}", is_error=True)
                    self.error_sent = True
                    self.task_cancelled = True
                # 不需要调用 handle_error_popup，错误监控器会处理
                return f"错误: {error_msg}"

            # 检查 .chooseFile-line
            try:
                choose_file = await page.query_selector(".chooseFile-line")
                if choose_file:
                    visible = await choose_file.is_visible()
                    if visible:
                        print("[Task] 找到 .chooseFile-line，点击...")
                        await choose_file.click()
                        await asyncio.sleep(1.5)
                        # 检查任务是否被取消
                        if self.task_cancelled:
                            print("[Task] 任务已被取消，停止处理")
                            return "错误: 任务已取消"
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
                        # 检查任务是否被取消
                        if self.task_cancelled:
                            print("[Task] 任务已被取消，停止处理")
                            return "错误: 任务已取消"
                        await input_el.fill(url)
                        await asyncio.sleep(0.5)
                        # 检查任务是否被取消
                        if self.task_cancelled:
                            print("[Task] 任务已被取消，停止处理")
                            return "错误: 任务已取消"
                        input_success = True
                        break
            except Exception as e:
                print(f"[Task] 输入框检查异常: {e}")

            # 输入框不存在，跳转到目标页面重试
            print("[Task] 未找到输入框，跳转目标页面...")
            await page.goto(TARGET_URL, wait_until="networkidle")
            await asyncio.sleep(2)
            # 检查任务是否被取消
            if self.task_cancelled:
                print("[Task] 任务已被取消，停止处理")
                return "错误: 任务已取消"

        if not input_success:
            error_msg = "错误: 多次尝试后仍未找到输入框"
            return error_msg

        # 检查任务是否被取消
        if self.task_cancelled:
            print("[Task] 任务已被取消，停止处理")
            return "错误: 任务已取消"

        # === Step 3: 点击 .start-button ===
        print("[Task] 等待 start-button...")
        
        # 检测错误弹窗
        has_error, error_msg = await self.check_error_popup()
        if has_error:
            print(f"[Task] 检测到错误弹窗: {error_msg}")
            if not self.error_sent:
                await self.send_result(key, f"错误: {error_msg}", is_error=True)
                self.error_sent = True
                self.task_cancelled = True
            # 不需要调用 handle_error_popup，错误监控器会处理
            return f"错误: {error_msg}"
        
        try:
            # 使用较短的超时时间，循环检查
            start_btn = None
            for _ in range(20):  # 最多等待10秒 (20 * 0.5s)
                if self.task_cancelled:
                    print("[Task] 任务已被取消，停止处理")
                    return "错误: 任务已取消"
                
                start_btn = await page.query_selector(".start-button")
                if start_btn:
                    visible = await start_btn.is_visible()
                    if visible:
                        break
                await asyncio.sleep(0.5)
            
            if start_btn:
                await start_btn.click()
                print("[Task] 已点击开始按钮")
            else:
                error_msg = "错误: 未找到开始按钮"
                return error_msg
        except Exception as e:
            error_msg = f"错误: 等待开始按钮失败 - {e}"
            return error_msg

        # === Step 4: 等待 textarea 出现 ===
        print(f"[Task] 等待转写结果 textarea 出现 (最长 {CONVERT_TIMEOUT}s)...")
        
        # 检查任务是否被取消
        if self.task_cancelled:
            print("[Task] 任务已被取消，停止处理")
            return "错误: 任务已取消"
        
        # 检测错误弹窗
        has_error, error_msg = await self.check_error_popup()
        if has_error:
            print(f"[Task] 检测到错误弹窗: {error_msg}")
            if not self.error_sent:
                await self.send_result(key, f"错误: {error_msg}", is_error=True)
                self.error_sent = True
                self.task_cancelled = True
            # 不需要调用 handle_error_popup，错误监控器会处理
            return f"错误: {error_msg}"
        
        try:
            # 使用较短的超时时间，循环检查
            textarea = None
            max_checks = CONVERT_TIMEOUT * 2  # 每0.5秒检查一次
            for _ in range(max_checks):
                if self.task_cancelled:
                    print("[Task] 任务已被取消，停止处理")
                    return "错误: 任务已取消"
                
                textarea = await page.query_selector(".el-textarea__inner")
                if textarea:
                    visible = await textarea.is_visible()
                    if visible:
                        break
                await asyncio.sleep(0.5)
        except Exception as e:
            error_msg = f"错误: 等待转写结果超时 - {e}"
            return error_msg

        if not textarea:
            error_msg = "错误: 转写结果未出现"
            return error_msg

        print("[Task] textarea 已出现，等待内容填充...")

        # === Step 5: 等待 textarea 有内容 ===
        content = ""
        max_wait = CONVERT_TIMEOUT  # 最长等待时间
        check_interval = 2  # 每2秒检查一次
        waited = 0
        
        while waited < max_wait:
            # 检查任务是否被取消
            if self.task_cancelled:
                print("[Task] 任务已被取消，停止等待")
                return "错误: 任务已取消"
            
            # 检测错误弹窗
            has_error, error_msg = await self.check_error_popup()
            if has_error:
                print(f"[Task] 等待内容时检测到错误: {error_msg}")
                if not self.error_sent:
                    await self.send_result(key, f"错误: {error_msg}", is_error=True)
                    self.error_sent = True
                    self.task_cancelled = True
                # 不需要调用 handle_error_popup，错误监控器会处理
                return f"错误: {error_msg}"
            
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
            # 检查任务是否被取消
            if self.task_cancelled:
                print("[Task] 任务已被取消，停止等待")
                return "错误: 任务已取消"
            waited += check_interval
            print(f"[Task] 等待内容中... ({waited}s/{max_wait}s)")

        if content and content.strip():
            print(f"[Task] 获取内容成功 ({len(content)} 字)")
        else:
            error_msg = "错误: 等待超时，未能获取转写内容"
            print("[Task] 获取内容失败")
            content = error_msg

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

        return content

    # ============================================================
    #  ChatGLM 视频生成自动化
    # ============================================================

    async def process_chatglm_video(self, prompt: str, key: str, page=None) -> str:
        page = page or self.chatglm_page
        if not page:
            return "错误: ChatGLM 页面不可用"

        try:
            page = await self.ensure_on_chatglm_video_page(page)

            snippet = (prompt or "").strip()
            if len(snippet) > 30:
                snippet = snippet[:30]

            prompt_loc = page.locator(".toolbar .prompt")
            matched_cards = page.locator("article.card").filter(has=prompt_loc.filter(has_text=snippet))
            before_count = 0
            try:
                before_count = await matched_cards.count()
            except Exception:
                before_count = 0

            textarea = page.locator("textarea.prompt")
            await textarea.wait_for(state="visible", timeout=30_000)
            await textarea.click()
            await textarea.fill("")
            await asyncio.sleep(0.1)
            await textarea.fill(prompt)

            btn_group_enabled = page.locator("div.btn-group:not(.disabled)")
            await btn_group_enabled.wait_for(state="visible", timeout=60_000)
            await asyncio.sleep(0.2)

            submitted = False
            for _ in range(6):
                try:
                    await btn_group_enabled.scroll_into_view_if_needed()
                except Exception:
                    pass

                try:
                    send_btn = btn_group_enabled.locator("button")
                    if await send_btn.count() > 0:
                        await send_btn.first.click(timeout=5_000)
                    else:
                        await btn_group_enabled.click(timeout=5_000)
                except Exception:
                    pass

                try:
                    await page.keyboard.press("Enter")
                except Exception:
                    pass

                try:
                    await page.wait_for_timeout(800)
                    now_count = await matched_cards.count()
                    if now_count > before_count:
                        submitted = True
                        break
                except Exception:
                    pass

                await asyncio.sleep(0.4)

            if not submitted:
                return "错误: 发送失败（按钮点击未触发提交）"

            deadline = asyncio.get_event_loop().time() + CHATGLM_VIDEO_TIMEOUT
            while asyncio.get_event_loop().time() < deadline:
                try:
                    now_count = await matched_cards.count()
                    if now_count > before_count:
                        target_card = matched_cards.nth(before_count)
                        src_loc = target_card.locator("video.video-container.loaded source[type='video/mp4']")
                        await src_loc.first.wait_for(state="attached", timeout=30_000)
                        src = await src_loc.first.get_attribute("src")
                        if src:
                            return src
                except Exception:
                    pass
                await asyncio.sleep(1)

            return "错误: 等待超时，未获取到对应视频链接"

        except Exception as e:
            return f"错误: ChatGLM 视频生成失败 - {e}"

    # ============================================================
    #  WebSocket 通信
    # ============================================================

    # ============================================================
    #  队列消费: 串行处理任务
    # ============================================================

    async def video_queue_consumer(self):
        """video_to_text 串行处理"""
        while True:
            key, url = await self.video_queue.get()
            print(f"\n{'=' * 50}")
            print(f"[Queue] 开始处理: type=video_to_text  key={key}")
            print(f"[Queue] 队列剩余(video): {self.video_queue.qsize()}")
            print(f"{'=' * 50}")

            # 设置当前任务 key，重置错误标记
            self.current_task_key = key
            self.current_task_type = "video_to_text"
            self.error_sent = False
            self.task_cancelled = False
            self.page_reset_by_monitor = False
            
            result = None
            need_reset_page = False  # 是否需要重置页面
            
            try:
                await self.ensure_on_target_page()
                result = await self.process_url(str(url), key)
                
                # 检查任务是否被取消（错误监控器可能已经发送了错误消息并回到初始页面）
                if self.task_cancelled:
                    print(f"[Queue] 任务已被取消（错误监控器已处理）")
                    # 检查错误监控器是否成功重置了页面
                    if self.page_reset_by_monitor:
                        print(f"[Queue] 页面已被错误监控器重置")
                        need_reset_page = False
                    else:
                        print(f"[Queue] 页面未被错误监控器重置，需要手动重置")
                        need_reset_page = True
                elif result and result.startswith("错误:"):
                    # 如果返回错误消息，检查是否已发送
                    print(f"[Queue] 任务失败: {result}")
                    if not self.error_sent:
                        await self.send_result(key, result, is_error=True)
                        self.error_sent = True
                    need_reset_page = True
                else:
                    # 成功处理，发送结果
                    if not self.error_sent:
                        await self.send_result(key, result, is_error=False)
                    need_reset_page = True
                    
            except Exception as e:
                print(f"[Queue] 处理异常: {e}")
                result = f"处理失败: {e}"
                if not self.error_sent:
                    await self.send_result(key, result, is_error=True)
                    self.error_sent = True
                need_reset_page = True
            
            # 任务完成后，清空当前任务标记
            self.current_task_key = None
            self.current_task_type = None
            self.task_cancelled = False
            self.page_reset_by_monitor = False
            
            # 如果需要，回到初始页面
            if need_reset_page:
                try:
                    print("[Queue] 回到初始页面...")
                    await self.page.goto(TARGET_URL, wait_until="networkidle")
                    await asyncio.sleep(1)
                    await self.setup_error_listener()
                except Exception as e:
                    print(f"[Queue] 回到初始页面失败: {e}")
            
            print(f"[Queue] 任务完成，准备处理下一个任务（队列剩余: {self.video_queue.qsize()}）")

            # 标记队列任务完成
            self.video_queue.task_done()

    async def chatglm_worker_loop(self, worker_id: int, page):
        """chatglm_video 并发 worker"""
        print(f"[ChatGLMWorker-{worker_id}] 启动")
        while True:
            key, prompt = await self.chatglm_queue.get()
            print(f"[ChatGLMWorker-{worker_id}] 开始处理 key={key} prompt={prompt[:50]}...")
            try:
                result = await self.process_chatglm_video(str(prompt), key, page=page)
                print(f"[ChatGLMWorker-{worker_id}] 处理完成 key={key} result={result[:100] if result else 'None'}...")
                if result and result.startswith("错误:"):
                    await self.send_result(key, result, is_error=True, result_type="chatglm_video_result")
                else:
                    await self.send_result(key, result, is_error=False, result_type="chatglm_video_result")
            except Exception as e:
                print(f"[ChatGLMWorker-{worker_id}] 异常 key={key}: {e}")
                await self.send_result(key, f"错误: ChatGLM worker 异常 - {e}", is_error=True, result_type="chatglm_video_result")
            finally:
                self.chatglm_queue.task_done()

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
                                    self.video_queue.put_nowait((key, url))
                                    print(f"[WS] 任务入队: type=video_to_text key={key}  队列(video): {self.video_queue.qsize()}")

                                elif msg_type == "chatglm_video":
                                    key = data.get("key", "")
                                    content = data.get("content", "")
                                    self.chatglm_queue.put_nowait((key, content))
                                    print(f"[WS] 任务入队: type=chatglm_video key={key}  队列(chatglm): {self.chatglm_queue.qsize()}")

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

        # 启动 ChatGLM 并发 worker
        self.chatglm_worker_tasks = []
        for i in range(min(CHATGLM_CONCURRENCY, len(self.chatglm_pages))):
            self.chatglm_worker_tasks.append(asyncio.create_task(self.chatglm_worker_loop(i + 1, self.chatglm_pages[i])))

        # 同时跑: WS 收消息 + video_to_text 串行 + chatglm 并发 worker
        await asyncio.gather(
            self.ws_loop(),
            self.video_queue_consumer(),
            *self.chatglm_worker_tasks,
        )

    async def cleanup(self):
        if self.error_monitor_task:
            self.error_monitor_task.cancel()
        if not getattr(self, "_cdp_mode", False):
            context = getattr(self, "context", None)
            if context:
                await context.close()
        playwright = getattr(self, "playwright", None)
        if playwright:
            await playwright.stop()


if __name__ == "__main__":
    # 支持自定义 WS 地址: python ws_worker.py ws://192.168.1.100:9502/ws?worker=1
    if len(sys.argv) > 1:
        WS_URL = sys.argv[1]

    worker = VideoToTextWorker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("\n[Worker] 已停止")
