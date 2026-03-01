#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 服务器自动开关机管理器

流程:
1. 启动 Playwright 浏览器，打开 GPU 控制台
2. 连接 Hyperf WebSocket (wss://api.zhimengai.xyz/dsp)
3. 注册为 gpu_monitor，接收任务通知
4. 有任务时自动开机，30分钟无任务自动关机

启动:
  python gpu_power_manager.py
"""

import asyncio
import json
import os
import time
from urllib.parse import parse_qsl, urlencode
from datetime import datetime
import websockets
from playwright.async_api import async_playwright


# ============================================================
#  配置
# ============================================================
WS_URL = "wss://api.zhimengai.xyz/dsp"
CONSOLE_URL = "https://console.compshare.cn/light-gpu/console/resources"
# 浏览器数据目录 (保存登录状态、cookie 等)
BROWSER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpu_browser_data")
# 登录状态文件
STORAGE_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpu_storage_state.json")
START_API_TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpu_start_api_template.json")
STOP_API_TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpu_stop_api_template.json")
# 检查间隔 (秒)
CHECK_INTERVAL = 10
# 空闲超时 (秒) - 30分钟
IDLE_TIMEOUT = 1800
# 视口同步间隔（秒）：让页面内容跟随浏览器窗口变化
VIEWPORT_SYNC_INTERVAL = 1


class GPUPowerManager:
    def __init__(self):
        self.ws = None
        self.page = None
        self.browser = None
        self.playwright = None
        self.context = None

        self.last_task_time = None  # 最后一次任务时间
        self.gpu_status = "unknown"  # unknown, starting, running, stopping, stopped
        self.has_pending_task = False  # 是否有待处理任务

        self.check_task = None  # 定期检查任务
        self.gpu_start_task = None  # 后台开机任务
        self.gpu_op_lock = asyncio.Lock()  # 避免并发开/关机
        self.viewport_sync_task = None  # 视口同步任务
        self.start_api_template = None  # 兼容：旧模板文件
        self.stop_api_template = None  # 兼容：旧模板文件

        # ── 从 DescribeCompShareInstance 拦截到的动态参数 ──
        self._api_params = {
            "headers": {},       # 请求头 (含 u-csrf-token 等)
            "base_body": {},     # 公共 body 参数 (ProjectId, _user 等)
            "instance": {},      # 完整实例信息 (UHostId, Zone, Region, State ...)
            "ready": False,      # 是否已拦截到有效参数
        }

    # ============================================================
    #  浏览器
    # ============================================================

    async def start_browser(self, data_dir: str | None = None):
        """启动 Playwright 浏览器 (持久化登录状态)"""
        data_dir = data_dir or BROWSER_DATA_DIR

        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        print(f"[Browser] 启动浏览器... 数据目录: {data_dir}")

        self.playwright = await async_playwright().start()

        # 检查是否有保存的登录状态
        has_saved_state = os.path.exists(STORAGE_STATE_FILE)
        if has_saved_state:
            print(f"[Browser] 发现保存的登录状态: {STORAGE_STATE_FILE}")

        # 启动浏览器（不使用 persistent context，改用普通 context + storage_state）
        browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--disable-web-security",
                "--disable-site-isolation-trials",
            ],
        )

        # 创建上下文，如果有保存的状态则加载
        context_options = {
            "locale": "zh-CN",
            "viewport": None,
            "accept_downloads": True,
            "ignore_https_errors": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        if has_saved_state:
            try:
                context_options["storage_state"] = STORAGE_STATE_FILE
                print("[Browser] 正在加载保存的登录状态...")
            except Exception as e:
                print(f"[Browser] 加载登录状态失败: {e}")

        self.context = await browser.new_context(**context_options)
        self.browser = browser

        # 创建页面
        self.page = await self.context.new_page()
        self._load_api_templates()
        self._bind_network_listeners()

        # 导航到控制台页面
        print(f"[Browser] 正在打开控制台...")
        await self.page.goto(CONSOLE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)  # 等待页面完全加载

        print(f"[Browser] 已打开: {CONSOLE_URL}")

        # 检查是否需要登录
        current_url = self.page.url
        print(f"[Browser] 当前 URL: {current_url}")

        if "login" in current_url.lower():
            print("[Browser] ⚠️  需要登录，请手动登录...")
            print("[Browser] 登录后状态会自动保存")
            print("[Browser] 等待登录完成...")
            # 等待 URL 变化（登录成功）
            try:
                await self.page.wait_for_url(
                    lambda url: "login" not in url.lower(),
                    timeout=300000  # 5分钟
                )
                print("[Browser] ✓ 登录成功")
                await asyncio.sleep(3)

                # 保存登录状态
                print(f"[Browser] 正在保存登录状态到: {STORAGE_STATE_FILE}")
                await self.context.storage_state(path=STORAGE_STATE_FILE)
                print("[Browser] ✓ 登录状态已保存")

                # 再次导航到控制台确保在正确页面
                await self.page.goto(CONSOLE_URL, wait_until="networkidle")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"[Browser] 登录超时: {e}")
                raise
        else:
            print("[Browser] ✓ 已登录（使用保存的状态）")
            # 即使已登录，也保存一次状态以更新 cookies
            try:
                await self.context.storage_state(path=STORAGE_STATE_FILE)
                print("[Browser] ✓ 已更新登录状态")
            except Exception as e:
                print(f"[Browser] 更新登录状态失败: {e}")

    def _load_api_templates(self):
        """加载已保存的启动/关机 API 模板"""
        for key, path, desc in (
            ("start_api_template", START_API_TEMPLATE_FILE, "启动"),
            ("stop_api_template", STOP_API_TEMPLATE_FILE, "关机"),
        ):
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    setattr(self, key, json.load(f))
                print(f"[API] 已加载{desc}模板: {path}")
            except Exception as e:
                print(f"[API] 加载{desc}模板失败: {e}")

    def _save_api_template(self, template: dict | None, path: str, desc: str):
        """保存 API 模板"""
        if not template:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            print(f"[API] 已保存{desc}模板: {path}")
        except Exception as e:
            print(f"[API] 保存{desc}模板失败: {e}")

    def _bind_network_listeners(self):
        """监听网络请求/响应，从 DescribeCompShareInstance 拦截认证参数和 GPU 状态"""
        if not self.page:
            return

        async def _on_request(request):
            """拦截 DescribeCompShareInstance 请求，获取认证头和公共 body 参数"""
            try:
                url = request.url
                post_data = request.post_data or ""
                if "DescribeCompShareInstance" not in url and "DescribeCompShareInstance" not in post_data:
                    return

                headers = dict(request.headers or {})
                body_pairs = parse_qsl(post_data, keep_blank_values=True)
                body = {k: v for k, v in body_pairs}

                # 保存认证头（u-csrf-token 是关键）
                self._api_params["headers"] = {
                    k: v for k, v in headers.items()
                    if k.lower() not in ("content-length", "host", "cookie")
                }
                # 保存公共 body 参数（ProjectId, _user 等后续 Start/Stop 也需要）
                self._api_params["base_body"] = {
                    k: v for k, v in body.items()
                    if k in ("ProjectId", "_user")
                }
                print(f"[API] ✓ 已拦截 DescribeCompShareInstance 请求参数")

            except Exception as e:
                print(f"[API] 拦截请求参数失败: {e}")

        async def _on_response(response):
            """拦截 DescribeCompShareInstance 响应，获取实例信息和 GPU 状态"""
            try:
                url = response.url
                if "DescribeCompShareInstance" not in url:
                    return

                data = await response.json()
                if data.get("RetCode") != 0:
                    print(f"[API] DescribeCompShareInstance 返回错误: RetCode={data.get('RetCode')}")
                    return

                hosts = data.get("UHostSet", [])
                if not hosts:
                    print("[API] DescribeCompShareInstance 无实例")
                    return

                inst = hosts[0]
                self._api_params["instance"] = inst
                self._api_params["ready"] = True

                state = inst.get("State", "unknown")
                state_map = {
                    "Running": "running",
                    "Stopped": "stopped",
                    "Starting": "starting",
                    "Initializing": "starting",
                    "Stopping": "stopping",
                }
                self.gpu_status = state_map.get(state, "unknown")

                print(f"[API] ✓ 已拦截实例信息: UHostId={inst.get('UHostId')}, State={state} → gpu_status={self.gpu_status}")

            except Exception as e:
                print(f"[API] 拦截响应失败: {e}")

        self.page.on("request", lambda req: asyncio.create_task(_on_request(req)))
        self.page.on("response", lambda resp: asyncio.create_task(_on_response(resp)))

    async def _call_compshare_api(self, action: str, extra_body: dict | None = None) -> dict | None:
        """通用 CompShare API 调用，使用从 DescribeCompShareInstance 拦截到的认证参数。
        返回响应 JSON dict，失败返回 None。
        """
        if not self.context:
            print(f"[API] 浏览器上下文未就绪，跳过 {action}")
            return None

        # 构造请求体
        inst = self._api_params.get("instance") or {}
        body = {
            "Action": action,
            "_timestamp": str(int(time.time() * 1000)),
        }
        # 公共参数（ProjectId, _user 来自拦截的请求 body）
        body.update(self._api_params.get("base_body") or {})
        # 实例参数（UHostId, Zone, Region 来自拦截的响应）
        if inst.get("UHostId"):
            body["UHostId"] = inst["UHostId"]
        if inst.get("Zone"):
            body["Zone"] = inst["Zone"]
        if inst.get("Region"):
            body["Region"] = inst["Region"]
        # StopCompShareInstance 需要 BasicImageId
        if action == "StopCompShareInstance" and inst.get("BasicImageId"):
            body["BasicImageId"] = inst["BasicImageId"]
        # 额外参数
        if extra_body:
            body.update(extra_body)

        # 如果拦截参数未就绪，回退到旧模板文件
        if not self._api_params.get("ready"):
            tpl = self.start_api_template if "Start" in action else self.stop_api_template
            if tpl and tpl.get("body"):
                body = dict(tpl["body"])
                body["Action"] = action
                body["_timestamp"] = str(int(time.time() * 1000))
                print(f"[API] 使用旧模板文件参数: {action}")

        headers = dict(self._api_params.get("headers") or {})
        # 回退：如果拦截的 headers 为空，从旧模板文件读
        if not headers.get("u-csrf-token"):
            tpl = self.start_api_template or self.stop_api_template
            if tpl and tpl.get("headers"):
                headers = {k: v for k, v in tpl["headers"].items()
                           if k.lower() not in ("content-length", "host", "cookie")}

        url = f"https://api.compshare.cn/?Action={action}"

        try:
            data = urlencode(body)
            resp = await self.context.request.post(url, headers=headers, data=data)
            text = await resp.text()
            print(f"[API] {action} HTTP {resp.status}: {text[:300]}")

            if resp.status >= 400:
                return None
            result = json.loads(text)
            if result.get("RetCode") != 0:
                print(f"[API] {action} 失败: RetCode={result.get('RetCode')}")
                return None
            return result
        except Exception as e:
            print(f"[API] {action} 异常: {e}")
            return None

    async def check_gpu_status_via_api(self) -> str:
        """通过 DescribeCompShareInstance API 直接查询 GPU 状态（不刷新页面）"""
        result = await self._call_compshare_api("DescribeCompShareInstance")
        if not result:
            return "unknown"
        hosts = result.get("UHostSet", [])
        if not hosts:
            return "unknown"

        inst = hosts[0]
        # 顺便更新缓存的实例信息
        self._api_params["instance"] = inst
        self._api_params["ready"] = True

        state = inst.get("State", "unknown")
        state_map = {
            "Running": "running",
            "Stopped": "stopped",
            "Starting": "starting",
            "Initializing": "starting",
            "Stopping": "stopping",
        }
        status = state_map.get(state, "unknown")
        self.gpu_status = status
        return status

    async def _start_gpu_via_api(self) -> bool:
        """通过 API 启动 GPU"""
        result = await self._call_compshare_api("StartCompShareInstance")
        return result is not None

    async def _stop_gpu_via_api(self) -> bool:
        """通过 API 关闭 GPU"""
        result = await self._call_compshare_api("StopCompShareInstance")
        return result is not None

    async def ensure_on_console_page(self):
        """确保在控制台页面上"""
        current = self.page.url
        if CONSOLE_URL not in current:
            print("[Browser] 不在控制台页面，重新跳转...")
            await self.page.goto(CONSOLE_URL, wait_until="networkidle")
            await asyncio.sleep(2)

    async def viewport_sync_loop(self):
        """将页面 viewport 与浏览器窗口大小保持同步"""
        print("[Browser] 视口同步循环启动")
        while True:
            try:
                await asyncio.sleep(VIEWPORT_SYNC_INTERVAL)
                if not self.page:
                    continue

                size = await self.page.evaluate(
                    """
                    () => ({
                        outerWidth: window.outerWidth || 0,
                        outerHeight: window.outerHeight || 0,
                        innerWidth: window.innerWidth || 0,
                        innerHeight: window.innerHeight || 0
                    })
                    """
                )

                # 估算浏览器边框与工具栏占用
                target_w = max(800, int(size["outerWidth"]) - 16)
                target_h = max(600, int(size["outerHeight"]) - 96)

                # inner 尺寸与目标差异较大时，主动同步 viewport
                if abs(int(size["innerWidth"]) - target_w) > 8 or abs(int(size["innerHeight"]) - target_h) > 8:
                    await self.page.set_viewport_size({"width": target_w, "height": target_h})
            except asyncio.CancelledError:
                break
            except Exception:
                # 这里不刷错误，避免干扰主流程日志
                pass

    # ============================================================
    #  GPU 状态检查和操作
    # ============================================================

    async def check_gpu_status(self) -> str:
        """检查 GPU 状态（优先 API，回退页面刷新）"""
        try:
            status = await self.check_gpu_status_via_api()
            if status != "unknown":
                label = {"running": "运行中", "stopped": "已关机", "starting": "启动中", "stopping": "关闭中"}.get(status, status)
                print(f"[GPU] 状态(API): {label}")
                return status
        except Exception as e:
            print(f"[GPU] API 查询状态失败: {e}")

        # API 失败时回退到页面刷新
        try:
            await self.page.reload(wait_until="networkidle")
            await asyncio.sleep(2)
            # 页面刷新会触发 DescribeCompShareInstance → 响应拦截器自动更新 gpu_status
            status = self.gpu_status
            label = {"running": "运行中", "stopped": "已关机", "starting": "启动中", "stopping": "关闭中"}.get(status, status)
            print(f"[GPU] 状态(页面): {label}")
            return status
        except Exception as e:
            print(f"[GPU] 检查状态失败: {e}")
            return "unknown"

    async def _find_start_button(self):
        """
        在操作区精确定位“启动”按钮。
        优先定位 data-urc-action_list-id=2 内可见按钮，避免命中隐藏模板节点。
        """
        selectors = [
            "div[data-urc-action_list-id='2'] button.uc-fe-button:has-text('启动')",
            "button.uc-fe-button:has-text('启动')",
        ]
        for selector in selectors:
            try:
                buttons = await self.page.query_selector_all(selector)
                if not buttons:
                    continue

                visible_buttons = []
                for btn in buttons:
                    try:
                        if await btn.is_visible():
                            visible_buttons.append(btn)
                    except Exception:
                        continue

                if not visible_buttons:
                    continue

                # 优先选择“可见且可启用”的按钮
                for btn in visible_buttons:
                    try:
                        if await btn.is_enabled():
                            return btn
                    except Exception:
                        continue

                # 退化：返回第一个可见按钮（后续走 force/js click）
                return visible_buttons[0]
            except Exception:
                continue
        return None

    async def start_gpu(self) -> bool:
        """启动 GPU（优先 API，回退页面点击）"""
        try:
            print("[GPU] 开始启动...")

            # 优先走 API 启动
            api_started = await self._start_gpu_via_api()
            if api_started:
                print("[GPU] ✓ 已通过 API 发起启动，进入状态轮询...")
            else:
                print("[GPU] API 启动失败，回退到页面点击...")

            if not api_started:
                # 查找启动按钮
                print("[GPU] 查找启动按钮...")
                start_button = await self._find_start_button()

                if not start_button:
                    print("[GPU] ✗ 未找到启动按钮，GPU 可能已经在运行")
                    return False

                # 检查按钮是否可见
                is_visible = await start_button.is_visible()
                print(f"[GPU] 启动按钮可见: {is_visible}")

                if not is_visible:
                    print("[GPU] ✗ 启动按钮不可见，GPU 可能已经在运行")
                    return False

                # 检查按钮是否启用（有些页面会误报 disabled，后续仍尝试点击）
                is_enabled = await start_button.is_enabled()
                print(f"[GPU] 启动按钮启用: {is_enabled}")
                if not is_enabled:
                    print("[GPU] ⚠️  启动按钮显示为禁用，先等待其变为可用...")
                    for _ in range(10):
                        await asyncio.sleep(1)
                        try:
                            start_button = await self._find_start_button()
                            if start_button and await start_button.is_enabled():
                                is_enabled = True
                                print("[GPU] ✓ 启动按钮已变为可用")
                                break
                        except Exception:
                            pass
                    if not is_enabled:
                        print("[GPU] ⚠️  启动按钮仍显示禁用，继续尝试强制点击方案...")

                # 点击启动按钮（普通点击 -> 强制点击 -> JS 点击）
                print("[GPU] 点击启动按钮...")
                clicked = False

                try:
                    await start_button.scroll_into_view_if_needed()
                except Exception:
                    pass

                # 1) 普通点击
                try:
                    await start_button.click(timeout=5000)
                    clicked = True
                    print("[GPU] ✓ 普通点击成功")
                except Exception as e:
                    print(f"[GPU] 普通点击失败: {e}")

                # 2) 强制点击
                if not clicked:
                    try:
                        await start_button.click(force=True, timeout=5000)
                        clicked = True
                        print("[GPU] ✓ 强制点击成功")
                    except Exception as e:
                        print(f"[GPU] 强制点击失败: {e}")

                # 3) JS 直接触发点击
                if not clicked:
                    try:
                        js_clicked = await self.page.evaluate(
                            """
                            () => {
                                const scope =
                                  document.querySelector("div[data-urc-action_list-id='2']") || document;
                                const buttons = Array.from(scope.querySelectorAll('button.uc-fe-button'));
                                const target = buttons.find(btn =>
                                  (btn.innerText || '').includes('启动') &&
                                  btn.offsetParent !== null
                                );
                                if (!target) return false;
                                target.click();
                                return true;
                            }
                            """
                        )
                        if js_clicked:
                            clicked = True
                            print("[GPU] ✓ JS 点击成功")
                    except Exception as e:
                        print(f"[GPU] JS 点击失败: {e}")

                if not clicked:
                    print("[GPU] ✗ 启动按钮点击失败，可能页面有遮罩或状态异常")
                    return False

                # 有些页面点击“启动”后会弹确认框，这里自动确认
                try:
                    confirm_selector = (
                        "button.uc-fe-button-styletype-primary:has-text('确定'), "
                        "button.uc-fe-button-styletype-primary:has-text('确认'), "
                        "button.uc-fe-button-styletype-primary:has-text('启动')"
                    )
                    confirm_btn = await self.page.query_selector(confirm_selector)
                    if confirm_btn and await confirm_btn.is_visible():
                        await confirm_btn.click()
                        print("[GPU] ✓ 已点击启动确认按钮")
                except Exception:
                    pass

                print("[GPU] ✓ 已点击启动按钮")
            self.gpu_status = "starting"
            await asyncio.sleep(5)

            # 等待启动完成（最多等待5分钟）
            print("[GPU] 等待 GPU 启动...")
            for i in range(60):
                await asyncio.sleep(5)
                status = await self.check_gpu_status()
                if status == "running":
                    print("[GPU] ✓ GPU 启动成功")
                    return True
                elapsed = (i + 1) * 5
                print(f"[GPU] 等待启动... ({elapsed}s)")

            print("[GPU] ⚠️  启动超时（5分钟）")
            return False

        except Exception as e:
            print(f"[GPU] 启动失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def stop_gpu(self) -> bool:
        """关闭 GPU"""
        try:
            print("[GPU] 开始关闭...")

            # 确保在控制台页面
            await self.ensure_on_console_page()

            # 优先走 API 关机（使用监听抓到的真实签名请求）
            api_stopped = await self._stop_gpu_via_api()
            if api_stopped:
                print("[GPU] 已通过 API 发起关机，进入状态轮询...")
                self.gpu_status = "stopping"
                for i in range(36):
                    await asyncio.sleep(5)
                    status = await self.check_gpu_status()
                    if status == "stopped":
                        print("[GPU] ✓ 关闭成功(API)")
                        return True
                    print(f"[GPU] 等待关机... ({(i + 1) * 5}s)")
                print("[GPU] ⚠️  API 关机后状态确认超时，回退页面点击...")

            # 尝试查找并点击操作按钮（可能需要先打开菜单）
            try:
                # 查找所有可能的操作按钮
                action_buttons = await self.page.query_selector_all(
                    "button.uc-fe-button, div[class*='action'], div[class*='more']"
                )
                for btn in action_buttons:
                    try:
                        if await btn.is_visible():
                            await btn.click()
                            print("[GPU] 已点击操作按钮")
                            await asyncio.sleep(1)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"[GPU] 未找到操作按钮，直接查找关闭选项: {e}")

            # 查找并点击关闭按钮
            close_button = await self.page.wait_for_selector(
                "div.uc-fe-menu-item:has-text('关闭')",
                timeout=10000
            )

            if close_button and await close_button.is_visible():
                await close_button.click()
                print("[GPU] 已点击关闭按钮")
                await asyncio.sleep(2)
            else:
                print("[GPU] 未找到关闭按钮")
                return False

            # 勾选同意复选框
            try:
                # 先尝试点击复选框图标
                checkbox_icon = await self.page.wait_for_selector(
                    "span.uc-fe-checkbox-icon-wrap",
                    timeout=10000
                )
                if checkbox_icon:
                    await checkbox_icon.click()
                    print("[GPU] 已勾选同意（图标）")
            except:
                # 如果失败，尝试点击整个复选框容器
                checkbox = await self.page.wait_for_selector(
                    "span.uc-fe-checkbox",
                    timeout=10000
                )
                if checkbox:
                    await checkbox.click()
                    print("[GPU] 已勾选同意（容器）")

            await asyncio.sleep(1)

            # 点击确定按钮（等待按钮变为可用状态）
            confirm_button = await self.page.wait_for_selector(
                "button.uc-fe-button-styletype-primary:has-text('确定'):not(.uc-fe-button-disabled)",
                timeout=10000
            )

            if confirm_button:
                await confirm_button.click()
                print("[GPU] 已点击确定按钮")
                self.gpu_status = "stopping"
                await asyncio.sleep(5)

                # 刷新页面确认关闭
                await self.page.reload(wait_until="networkidle")
                await asyncio.sleep(3)

                status = await self.check_gpu_status()
                if status == "stopped":
                    print("[GPU] ✓ 关闭成功")
                    return True

                print("[GPU] ⚠️  关闭状态未确认")
                return False
            else:
                print("[GPU] 未找到确定按钮")
                return False

        except Exception as e:
            print(f"[GPU] 关闭失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ============================================================
    #  WebSocket 通信
    # ============================================================

    async def _send_ws_message(self, payload: dict) -> bool:
        """发送 WS 消息（失败不抛异常）"""
        if not self.ws:
            return False
        try:
            await self.ws.send(json.dumps(payload, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"[WS] 发送消息失败: {e}, payload={payload}")
            return False

    def _schedule_gpu_start(self, trigger: str, request_id: str | None = None):
        """异步调度开机，避免阻塞 WS 消息循环"""
        self.has_pending_task = True
        self.last_task_time = datetime.now()

        if self.gpu_start_task and not self.gpu_start_task.done():
            print(f"[GPU] 开机任务已在进行中，忽略重复触发: trigger={trigger}")
            return

        self.gpu_start_task = asyncio.create_task(self._start_gpu_worker(trigger, request_id))

    async def _start_gpu_worker(self, trigger: str, request_id: str | None = None):
        """后台开机执行器（带锁，防重复开机）"""
        async with self.gpu_op_lock:
            try:
                status = await self.check_gpu_status()
                if status == "running":
                    self.has_pending_task = False
                    self.last_task_time = datetime.now()
                    print(f"[GPU] 已在运行中，无需开机: trigger={trigger}")
                    # 即使已在运行，也广播一次在线状态给所有客户端
                    await self._broadcast_gpu_online(request_id=request_id)
                    return

                print(f"[GPU] 收到开机触发，开始开机: trigger={trigger}, request_id={request_id}")
                success = await self.start_gpu()
                if success:
                    self.has_pending_task = False
                    self.last_task_time = datetime.now()
                    print("[GPU] 后台开机成功")
                    # 广播 gpu.power.online 给所有客户端
                    await self._broadcast_gpu_online(request_id=request_id)
                else:
                    print("[GPU] 后台开机失败")
                    if request_id:
                        await self._send_ws_message({
                            "type": "gpu.power.boot.result",
                            "request_id": request_id,
                            "success": False,
                            "status": "failed",
                            "msg": "GPU 开机失败",
                        })
            except Exception as e:
                print(f"[GPU] 后台开机异常: {e}")
                if request_id:
                    await self._send_ws_message({
                        "type": "gpu.power.boot.result",
                        "request_id": request_id,
                        "success": False,
                        "status": "error",
                        "msg": f"GPU 开机异常: {e}",
                    })

    async def _broadcast_gpu_online(self, request_id: str | None = None):
        """通过 WS 广播 GPU 已上线消息给所有客户端（由 Dsp.php 中继转发）"""
        payload = {
            "type": "gpu.power.online",
            "status": "running",
            "msg": "GPU 服务器已上线",
            "source": "gpu_monitor",
        }
        if request_id:
            payload["request_id"] = request_id
        sent = await self._send_ws_message(payload)
        if sent:
            print("[WS] ✓ 已广播 gpu.power.online")
        else:
            print("[WS] ✗ 广播 gpu.power.online 失败（WS 未连接）")

    async def _refresh_and_report_status(self, request_id: str):
        """后台刷新 GPU 精确状态并通过 WS 上报"""
        try:
            status = await self.check_gpu_status_via_api()
            if status != "unknown":
                await self._send_ws_message({
                    "type": "gpu.status.response",
                    "status": status,
                    "request_id": request_id,
                    "source": "gpu_monitor",
                    "fresh": True,
                })
        except Exception as e:
            print(f"[WS] 刷新状态上报失败: {e}")

    def _is_start_in_progress(self) -> bool:
        """是否已有开机流程在执行"""
        return bool(self.gpu_start_task and not self.gpu_start_task.done())

    async def ws_loop(self):
        """WebSocket 消息循环，自动重连"""
        while True:
            try:
                print(f"\n[WS] 连接: {WS_URL}")
                async with websockets.connect(
                    WS_URL,
                    # 关闭 websockets 库内置 ping，避免与业务心跳冲突
                    ping_interval=None,
                    ping_timeout=None,
                    max_size=10 * 1024 * 1024,
                ) as ws:
                    self.ws = ws
                    print("[WS] 已连接")

                    # 注册为 gpu_monitor
                    await ws.send(json.dumps({"type": "register", "role": "gpu_monitor"}))
                    print("[WS] 已发送注册 (gpu_monitor)")

                    # 启动心跳
                    heartbeat = asyncio.create_task(self._heartbeat(ws))

                    try:
                        async for raw in ws:
                            # 打印完整的消息内容（用于调试）
                            print(f"[WS] 收到完整消息: {raw}")
                            try:
                                data = json.loads(raw)
                                msg_type = data.get("type", "")

                                if msg_type == "registered":
                                    print(f"[WS] ✓ 服务端确认注册: {data.get('role', '')}")

                                elif msg_type == "pong":
                                    # 心跳消息，不打印
                                    pass

                                # 监听所有 GPU 任务类型
                                elif msg_type in ["url", "chatglm_video", "gpu.job.submit", "gpu_task"]:
                                    # 收到任务，标记有待处理任务
                                    self._schedule_gpu_start(trigger=msg_type)
                                    print(f"[WS] ✓✓✓ 检测到 GPU 任务: {msg_type} ✓✓✓")
                                    print(f"[WS] 任务详情: {data}")
                                    print(f"[WS] 已设置 has_pending_task=True, last_task_time={self.last_task_time}")

                                # 监听 GPU 开机请求
                                elif msg_type == "gpu.power.boot":
                                    print(f"[WS] ✓✓✓ 收到 GPU 开机请求: {data} ✓✓✓")
                                    self._schedule_gpu_start(
                                        trigger=msg_type,
                                        request_id=data.get("request_id"),
                                    )

                                # 监听 GPU 任务活跃通知（run_server.py 有任务在处理）
                                elif msg_type == "gpu.task.active":
                                    self.has_pending_task = True
                                    self.last_task_time = datetime.now()
                                    print(f"[WS] ✓ GPU 有活跃任务: task_id={data.get('task_id','')}, task_type={data.get('task_type','')}")

                                # 监听 GPU 状态查询请求
                                elif msg_type == "gpu.status.query":
                                    print(f"[WS] 收到 GPU 状态查询: {data}")
                                    # 快速返回缓存状态，同时异步刷新
                                    cached = self.gpu_status
                                    await self._send_ws_message({
                                        "type": "gpu.status.response",
                                        "status": cached,
                                        "request_id": data.get("request_id", ""),
                                        "source": "gpu_monitor",
                                    })
                                    # 后台刷新一次精确状态
                                    asyncio.create_task(self._refresh_and_report_status(
                                        data.get("request_id", "")))

                                else:
                                    print(f"[WS] 其他消息类型: {msg_type}, 完整数据: {data}")

                            except json.JSONDecodeError:
                                print(f"[WS] 无效 JSON: {raw}")
                    finally:
                        heartbeat.cancel()
                        try:
                            await heartbeat
                        except asyncio.CancelledError:
                            pass
                        self.ws = None

            except (
                websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError,
                OSError,
            ) as e:
                print(f"[WS] 连接断开: {e}")
            except Exception as e:
                print(f"[WS] 异常: {e}")
                import traceback
                traceback.print_exc()

            print("[WS] 5 秒后重连...")
            await asyncio.sleep(5)

    async def _heartbeat(self, ws):
        """心跳保活"""
        while True:
            try:
                await asyncio.sleep(25)
                await ws.send(json.dumps({"type": "ping"}))
            except asyncio.CancelledError:
                break
            except Exception:
                break

    # ============================================================
    #  定期检查 GPU 状态
    # ============================================================

    async def check_loop(self):
        """定期检查 GPU 状态和任务情况"""
        print("[Check] GPU 状态检查循环启动")

        while True:
            try:
                await asyncio.sleep(CHECK_INTERVAL)
                await self._check_and_manage_gpu()

            except Exception as e:
                print(f"[Check] 检查循环异常: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(CHECK_INTERVAL)

    async def _check_and_manage_gpu(self):
        """检查并管理 GPU 状态"""
        try:
            # 检查 GPU 状态
            status = await self.check_gpu_status()

            # 检查是否有待处理任务
            has_task = self.has_pending_task

            # 记录当前状态
            idle_time_str = "N/A"
            if self.last_task_time:
                idle_time = (datetime.now() - self.last_task_time).total_seconds()
                idle_time_str = f"{idle_time:.0f}s"

            print(f"[Check] GPU={status}, 有任务={has_task}, 最后任务时间={self.last_task_time}, 空闲={idle_time_str}")

            if has_task and status == "stopped":
                if self._is_start_in_progress():
                    print("[Check] 开机流程进行中，跳过重复启动")
                    return
                # 有任务且 GPU 已关机，启动 GPU
                print("[Check] ✓✓✓ 检测到 GPU 任务，准备启动 GPU ✓✓✓")
                success = await self.start_gpu()
                if success:
                    # 重置任务标记和时间
                    self.has_pending_task = False
                    self.last_task_time = datetime.now()
                    print(f"[Check] ✓ GPU 启动成功，开始计时")
                else:
                    print(f"[Check] ✗ GPU 启动失败")

            elif status == "running":
                # GPU 运行中，检查空闲时间
                if has_task:
                    # 有新任务，更新最后任务时间
                    self.last_task_time = datetime.now()
                    self.has_pending_task = False
                    print("[Check] ✓ 检测到新任务，更新最后任务时间")
                elif self.last_task_time:
                    # 无新任务，检查空闲时间
                    idle_time = (datetime.now() - self.last_task_time).total_seconds()
                    remaining = IDLE_TIMEOUT - idle_time
                    print(f"[Check] GPU 空闲时间: {idle_time:.0f}s / {IDLE_TIMEOUT}s (还剩 {remaining:.0f}s)")

                    if idle_time >= IDLE_TIMEOUT:
                        print(f"[Check] ⚠️  GPU 空闲超过 {IDLE_TIMEOUT}s (30分钟)，准备关机")
                        success = await self.stop_gpu()
                        if success:
                            self.last_task_time = None
                            print(f"[Check] ✓ GPU 已关机")
                        else:
                            print(f"[Check] ✗ GPU 关机失败")
                else:
                    # 首次检测到 GPU 运行且无任务，记录时间
                    self.last_task_time = datetime.now()
                    print("[Check] 首次检测到 GPU 运行，开始计时空闲时间")

            elif status == "stopped":
                # GPU 已关机且无任务，什么都不做
                if not has_task:
                    print("[Check] GPU 已关机，等待任务...")

        except Exception as e:
            print(f"[Check] GPU 管理异常: {e}")
            import traceback
            traceback.print_exc()

    # ============================================================
    #  主入口
    # ============================================================

    async def run(self):
        print("=" * 50)
        print("  GPU 电源管理器")
        print(f"  WS:       {WS_URL}")
        print(f"  控制台:   {CONSOLE_URL}")
        print(f"  检查间隔: {CHECK_INTERVAL}s")
        print(f"  空闲超时: {IDLE_TIMEOUT}s (30分钟)")
        print("=" * 50 + "\n")

        await self.start_browser()

        # 启动视口同步任务
        self.viewport_sync_task = asyncio.create_task(self.viewport_sync_loop())

        # 同时跑: WS 收消息 + 定期检查
        await asyncio.gather(
            self.ws_loop(),
            self.check_loop(),
        )

    async def cleanup(self):
        if self.check_task:
            self.check_task.cancel()
        if self.viewport_sync_task:
            self.viewport_sync_task.cancel()
        page = getattr(self, "page", None)
        if page:
            await page.close()
        context = getattr(self, "context", None)
        if context:
            await context.close()
        browser = getattr(self, "browser", None)
        if browser:
            await browser.close()
        playwright = getattr(self, "playwright", None)
        if playwright:
            await playwright.stop()


if __name__ == "__main__":
    manager = GPUPowerManager()
    try:
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        print("\n[Manager] 已停止")
