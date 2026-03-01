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
# 检查间隔 (秒)
CHECK_INTERVAL = 60
# 空闲超时 (秒) - 30分钟
IDLE_TIMEOUT = 1800


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

    async def ensure_on_console_page(self):
        """确保在控制台页面上"""
        current = self.page.url
        if CONSOLE_URL not in current:
            print("[Browser] 不在控制台页面，重新跳转...")
            await self.page.goto(CONSOLE_URL, wait_until="networkidle")
            await asyncio.sleep(2)

    # ============================================================
    #  GPU 状态检查和操作
    # ============================================================

    async def check_gpu_status(self) -> str:
        """检查 GPU 状态"""
        try:
            # 刷新页面
            await self.page.reload(wait_until="networkidle")
            await asyncio.sleep(2)

            # 查找启动按钮
            start_button = await self.page.query_selector(
                "button.uc-fe-button:has-text('启动')"
            )

            if start_button and await start_button.is_visible():
                self.gpu_status = "stopped"
                print("[GPU] 状态: 已关机")
                return "stopped"

            # 如果没有启动按钮，说明正在运行
            self.gpu_status = "running"
            print("[GPU] 状态: 运行中")
            return "running"

        except Exception as e:
            print(f"[GPU] 检查状态失败: {e}")
            return "unknown"

    async def start_gpu(self) -> bool:
        """启动 GPU"""
        try:
            print("[GPU] 开始启动...")

            # 确保在控制台页面
            await self.ensure_on_console_page()

            # 刷新页面，确保状态最新
            await self.page.reload(wait_until="networkidle")
            await asyncio.sleep(3)

            # 查找启动按钮
            print("[GPU] 查找启动按钮...")
            start_button = await self.page.query_selector(
                "button.uc-fe-button:has-text('启动')"
            )

            if not start_button:
                print("[GPU] ✗ 未找到启动按钮，GPU 可能已经在运行")
                return False

            # 检查按钮是否可见
            is_visible = await start_button.is_visible()
            print(f"[GPU] 启动按钮可见: {is_visible}")

            if not is_visible:
                print("[GPU] ✗ 启动按钮不可见，GPU 可能已经在运行")
                return False

            # 检查按钮是否启用
            is_enabled = await start_button.is_enabled()
            print(f"[GPU] 启动按钮启用: {is_enabled}")

            if not is_enabled:
                print("[GPU] ⚠️  启动按钮被禁用，等待 5 秒后重试...")
                await asyncio.sleep(5)
                await self.page.reload(wait_until="networkidle")
                await asyncio.sleep(3)

                # 重新查找按钮
                start_button = await self.page.query_selector(
                    "button.uc-fe-button:has-text('启动')"
                )
                if not start_button or not await start_button.is_enabled():
                    print("[GPU] ✗ 启动按钮仍然被禁用，可能需要手动操作")
                    return False

            # 点击启动按钮
            print("[GPU] 点击启动按钮...")
            await start_button.click()
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
                                    self.has_pending_task = True
                                    self.last_task_time = datetime.now()
                                    print(f"[WS] ✓✓✓ 检测到 GPU 任务: {msg_type} ✓✓✓")
                                    print(f"[WS] 任务详情: {data}")
                                    print(f"[WS] 已设置 has_pending_task=True, last_task_time={self.last_task_time}")

                                # 监听 GPU 开机请求
                                elif msg_type == "gpu.power.boot":
                                    print(f"[WS] ✓✓✓ 收到 GPU 开机请求: {data} ✓✓✓")
                                    # 立即尝试启动 GPU
                                    success = await self.start_gpu()
                                    if success:
                                        print("[WS] ✓ GPU 开机成功")
                                        # 重置任务标记
                                        self.has_pending_task = False
                                        self.last_task_time = datetime.now()
                                    else:
                                        print("[WS] ✗ GPU 开机失败")

                                else:
                                    print(f"[WS] 其他消息类型: {msg_type}, 完整数据: {data}")

                            except json.JSONDecodeError:
                                print(f"[WS] 无效 JSON: {raw}")
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

        # 同时跑: WS 收消息 + 定期检查
        await asyncio.gather(
            self.ws_loop(),
            self.check_loop(),
        )

    async def cleanup(self):
        if self.check_task:
            self.check_task.cancel()
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
