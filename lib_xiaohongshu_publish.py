# -*- coding: utf-8 -*-
# lib_xiaohongshu_publish.py - 小红书自动发布模块

import os
import sys
import time
import traceback
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 小红书相关 URL
XIAOHONGSHU_UPLOAD_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"
XIAOHONGSHU_LOGIN_URL = "https://creator.xiaohongshu.com/login"


class XiaohongshuPublisher:
    """小红书自动发布工具 - 完整流程"""

    def __init__(self, user_data_dir=None):
        """
        初始化发布器
        :param user_data_dir: Chrome用户数据目录，用于保持登录状态
        """
        self.driver = None
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.expanduser("~"), "AppData", "Local", "XiaohongshuPublisher"
        )
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    # ------------------------------------------------------------
    #  ChromeDriver 路径
    # ------------------------------------------------------------
    def _get_chromedriver_path(self):
        """获取 ChromeDriver 路径"""
        driver_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"

        # 优先检查 chromedriver 文件夹
        driver_folder_path = os.path.join(self.base_dir, "chromedriver", driver_name)
        if os.path.exists(driver_folder_path):
            print(f"[小红书发布] 使用打包驱动: {driver_folder_path}")
            return driver_folder_path

        # 检查当前目录
        driver_path = os.path.join(self.base_dir, driver_name)
        if os.path.exists(driver_path):
            print(f"[小红书发布] 使用本地驱动: {driver_path}")
            return driver_path

        print("[小红书发布] 未找到本地驱动，尝试使用系统驱动")
        return None

    # ------------------------------------------------------------
    #  初始化浏览器
    # ------------------------------------------------------------
    def _init_driver(self):
        """初始化浏览器驱动"""
        if self.driver:
            return True

        chrome_options = Options()

        # 使用用户数据目录保持登录状态
        chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
        chrome_options.add_argument("--profile-directory=Default")

        # 禁用自动化检测
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # 禁用 GPU 加速
        chrome_options.add_argument("--disable-gpu")

        # 设置窗口大小
        chrome_options.add_argument("--window-size=1280,900")

        # 禁用通知
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "download.default_directory": os.path.expanduser("~\\Downloads"),
        }
        chrome_options.add_experimental_option("prefs", prefs)

        try:
            driver_path = self._get_chromedriver_path()

            if driver_path:
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("[小红书发布] 使用本地 ChromeDriver 初始化浏览器")
            else:
                print("[小红书发布] 尝试使用系统 ChromeDriver...")
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[小红书发布] 使用系统 ChromeDriver 初始化浏览器")

            # 设置隐式等待
            self.driver.implicitly_wait(2)

            # 修改 navigator.webdriver 标志
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            })

            print("[小红书发布] 浏览器初始化成功")
            return True
        except Exception as e:
            print(f"[小红书发布] 浏览器初始化失败: {e}")
            traceback.print_exc()
            return False

    # ------------------------------------------------------------
    #  检查登录状态
    # ------------------------------------------------------------
    def _check_login(self, step_callback=None):
        """
        打开小红书发布页面，检测是否处于登录状态。
        如果跳转到 login 页面说明未登录。
        :return: (is_logged_in, message)
        """
        def _step(name, detail=""):
            print(f"[小红书发布] {name} {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            print("[小红书发布] == 检查登录状态 ==")
            self.driver.get(XIAOHONGSHU_UPLOAD_URL)
            time.sleep(3)

            current_url = self.driver.current_url
            print(f"[小红书发布] 当前页面 URL: {current_url}")

            # 如果跳转到了登录页面
            if "login" in current_url.lower():
                print("[小红书发布] 检测到登录页面，需要用户登录")
                return False, "检测到小红书登录页面，请登录"

            # 如果还在发布页面，说明已登录
            if "publish" in current_url:
                print("[小红书发布] 已在发布页面，已登录")
                return True, "已登录"

            # 兜底判断
            if "creator.xiaohongshu.com" in current_url and "login" not in current_url:
                print("[小红书发布] 停留在创作中心，视为已登录")
                return True, "已登录"

            print("[小红书发布] 未检测到登录态")
            return False, "未登录，需要登录"

        except Exception as e:
            print(f"[小红书发布] 检查登录状态失败: {e}")
            traceback.print_exc()
            return False, f"检查失败: {str(e)}"

    # ------------------------------------------------------------
    #  等待用户登录
    # ------------------------------------------------------------
    def _wait_for_login(self, timeout=300, step_callback=None):
        """
        在登录页面等待用户登录。
        登录成功后页面会自动跳转回发布页面。
        :param timeout: 最长等待时间（秒）
        :param step_callback: 步骤回调
        :return: (success, message)
        """
        def _step(name, detail=""):
            print(f"[小红书发布] {name} {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            _step("请登录小红书", "请在浏览器中完成登录（支持扫码/手机验证码）")
            print("[小红书发布] == 等待用户登录 ==")

            start_time = time.time()
            check_count = 0
            while time.time() - start_time < timeout:
                check_count += 1

                current_url = self.driver.current_url

                # 检测是否已跳转到发布页面（登录成功后自动跳转）
                if "publish" in current_url and "login" not in current_url:
                    print("[小红书发布] [OK] 已跳转到发布页面，登录成功!")
                    _step("登录成功!", "已跳转到视频发布页面")
                    time.sleep(2)
                    return True, "登录成功"

                # 检测URL不再是登录页面
                if "login" not in current_url.lower():
                    if "creator.xiaohongshu.com" in current_url:
                        print("[小红书发布] [OK] 页面已变化，登录成功!")
                        _step("登录成功!", "正在跳转到视频发布页面...")
                        time.sleep(1)
                        # 主动跳转到发布页面
                        self.driver.get(XIAOHONGSHU_UPLOAD_URL)
                        time.sleep(3)
                        return True, "登录成功"

                # 每30秒打印一次提醒
                if check_count % 30 == 0:
                    elapsed = int(time.time() - start_time)
                    remaining = timeout - elapsed
                    _step("等待登录...", f"已等待 {elapsed} 秒，剩余 {remaining} 秒")

                time.sleep(1)

            return False, "登录超时(5分钟内未完成登录)"

        except Exception as e:
            print(f"[小红书发布] 等待登录失败: {e}")
            traceback.print_exc()
            return False, f"等待登录失败: {str(e)}"

    # ------------------------------------------------------------
    #  上传视频文件
    # ------------------------------------------------------------
    def _upload_video(self, video_path, update_progress):
        """
        上传视频文件到小红书
        查找 input.upload-input[type="file"] 并发送文件路径
        小红书的上传input: <input class="upload-input" type="file" accept=".mp4,.mov,.flv,.f4v,.mkv,.rm,.rmvb,.m4v,.mpg,.mpeg,.ts">
        """
        print("[小红书发布] == 上传视频文件 ==")
        update_progress(10, "等待页面加载...")

        try:
            # 确保在发布页面
            current_url = self.driver.current_url
            if "publish" not in current_url:
                print("[小红书发布] 不在发布页面，跳转...")
                self.driver.get(XIAOHONGSHU_UPLOAD_URL)

            # 等待页面完全加载
            print("[小红书发布] 等待页面加载完成（5秒）...")
            time.sleep(5)

            video_abs_path = os.path.abspath(video_path)
            print(f"[小红书发布] 文件路径: {video_abs_path}")

            # 查找文件上传 input
            print("[小红书发布] 查找视频上传 input...")

            file_input = None
            try:
                # 方法1：直接查找 upload-input 类
                file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input.upload-input[type='file']")
                if file_inputs:
                    file_input = file_inputs[0]
                    print(f"[小红书发布] 找到 upload-input 视频上传 input")
            except Exception as e:
                print(f"[小红书发布] 方法1查找失败: {e}")

            if not file_input:
                try:
                    # 方法2：查找带有视频格式accept的file input
                    file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    for inp in file_inputs:
                        accept = inp.get_attribute('accept') or ''
                        if '.mp4' in accept or '.mov' in accept or 'video' in accept:
                            file_input = inp
                            print(f"[小红书发布] 找到视频上传 input, accept={accept[:50]}...")
                            break

                    if not file_input and file_inputs:
                        file_input = file_inputs[0]
                        print(f"[小红书发布] 使用第一个 file input")

                except Exception as e:
                    print(f"[小红书发布] 方法2查找失败: {e}")

            if not file_input:
                # 备用：使用JavaScript查找
                print("[小红书发布] 尝试使用JavaScript查找...")
                try:
                    file_input = self.driver.execute_script('''
                        var inputs = document.querySelectorAll('input[type="file"]');
                        for (var i = 0; i < inputs.length; i++) {
                            var accept = inputs[i].getAttribute('accept') || '';
                            if (accept.indexOf('.mp4') !== -1 || accept.indexOf('.mov') !== -1) {
                                return inputs[i];
                            }
                        }
                        // 查找 upload-input 类
                        var uploadInput = document.querySelector('input.upload-input');
                        if (uploadInput) return uploadInput;
                        return inputs.length > 0 ? inputs[0] : null;
                    ''')
                except Exception as e:
                    print(f"[小红书发布] JavaScript查找失败: {e}")

            if not file_input:
                return False, "未找到视频上传入口"

            # 使文件input可见（有些可能是隐藏的）
            try:
                self.driver.execute_script("""
                    arguments[0].style.display = 'block';
                    arguments[0].style.visibility = 'visible';
                    arguments[0].style.opacity = '1';
                    arguments[0].style.position = 'absolute';
                    arguments[0].style.zIndex = '99999';
                """, file_input)
            except Exception:
                pass

            # 发送文件路径
            file_input.send_keys(video_abs_path)
            print(f"[小红书发布] 文件路径已发送: {video_abs_path}")

            update_progress(15, "正在上传视频文件...")
            return True, "视频文件已发送"

        except Exception as e:
            print(f"[小红书发布] 上传视频失败: {e}")
            traceback.print_exc()
            return False, f"上传失败: {str(e)}"

    # ------------------------------------------------------------
    #  等待视频上传完成
    # ------------------------------------------------------------
    def _wait_upload_complete(self, update_progress, max_wait=600):
        """
        等待视频上传完成。
        检测上传进度条消失或页面状态变化表示上传成功。
        """
        print("[小红书发布] == 等待视频上传完成 ==")
        update_progress(20, "等待视频上传完成...")
        time.sleep(3)

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                page_source = self.driver.page_source

                # 方法1：检测是否有标题输入框出现（上传完成后会显示）
                try:
                    title_inputs = self.driver.find_elements(
                        By.CSS_SELECTOR, "input.d-text[placeholder*='标题']"
                    )
                    if title_inputs and title_inputs[0].is_displayed():
                        print("[小红书发布] [OK] 检测到标题输入框，视频上传完成")
                        update_progress(40, "视频上传完成")
                        return True
                except Exception:
                    pass

                # 方法2：检测上传完成的状态变化
                try:
                    # 检查是否有视频预览或缩略图
                    preview_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, "video, [class*='preview'], [class*='thumbnail']"
                    )
                    if preview_elements:
                        for elem in preview_elements:
                            if elem.is_displayed():
                                # 额外等待确认
                                time.sleep(2)
                                print("[小红书发布] [OK] 检测到预览元素，视频可能已上传完成")
                                update_progress(40, "视频上传完成")
                                return True
                except Exception:
                    pass

                # 方法3：检测是否有进度条
                try:
                    progress_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, "[class*='progress'], [class*='uploading']"
                    )
                    has_progress = False
                    for elem in progress_elements:
                        if elem.is_displayed():
                            has_progress = True
                            break
                    
                    # 如果没有进度条了，可能上传完成
                    if not has_progress:
                        time.sleep(3)
                        # 再次检查标题输入框
                        title_inputs = self.driver.find_elements(
                            By.CSS_SELECTOR, "input.d-text[placeholder*='标题'], input[placeholder*='标题']"
                        )
                        if title_inputs:
                            print("[小红书发布] [OK] 上传完成（进度条消失）")
                            update_progress(40, "视频上传完成")
                            return True
                except Exception:
                    pass

                elapsed = int(time.time() - start_time)
                update_progress(20 + min(elapsed // 15, 15), f"视频上传中...已等待 {elapsed} 秒")

            except Exception as e:
                print(f"[小红书发布] 检查上传状态异常: {e}")

            time.sleep(3)

        print("[小红书发布] 警告：上传状态检测超时，继续执行...")
        return False

    # ------------------------------------------------------------
    #  填写标题
    # ------------------------------------------------------------
    def _fill_title(self, title, update_progress):
        """
        填写视频标题
        小红书标题输入框: <input class="d-text" type="text" placeholder="填写标题会有更多赞哦" value="">
        """
        print("[小红书发布] == 填写标题 ==")
        update_progress(50, "正在填写标题...")

        try:
            safe_title = (title or "精彩视频")[:20]  # 小红书标题限制，通常20字左右

            # 查找标题输入框
            title_input = None
            selectors = [
                "input.d-text[placeholder*='标题']",
                "input[placeholder*='标题']",
                "input.d-text[type='text']",
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        title_input = elements[0]
                        print(f"[小红书发布] 找到标题输入框: {selector}")
                        break
                except Exception:
                    continue

            if not title_input:
                # 备用：使用 XPath
                try:
                    title_input = self.driver.find_element(
                        By.XPATH, "//input[contains(@placeholder, '标题')]"
                    )
                except Exception:
                    pass

            if not title_input:
                print("[小红书发布] [X] 未找到标题输入框")
                return False

            # 点击并清空
            title_input.click()
            time.sleep(0.3)
            title_input.clear()
            time.sleep(0.2)

            # 使用 JS 设值
            self.driver.execute_script("""
                var el = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, arguments[1]);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, title_input, safe_title)

            print(f"[小红书发布] [OK] 标题已填写: {safe_title}")
            update_progress(60, f"标题已填写")
            return True

        except Exception as e:
            print(f"[小红书发布] 填写标题失败: {e}")
            traceback.print_exc()
            return False

    # ------------------------------------------------------------
    #  填写正文描述（话题）
    # ------------------------------------------------------------
    def _fill_description(self, topics, update_progress):
        """
        填写正文描述（话题）
        小红书正文编辑器: <div contenteditable="true" class="tiptap ProseMirror">
            <p data-placeholder="输入正文描述，真诚有价值的分享予人温暖">
        注意：小红书的话题带#，空格分隔
        """
        if not topics:
            print("[小红书发布] 无话题需要填写，跳过")
            return True

        print("[小红书发布] == 填写正文描述（话题） ==")
        update_progress(65, "正在填写正文描述...")

        try:
            # 查找正文编辑器
            desc_editor = None
            selectors = [
                "div.tiptap.ProseMirror[contenteditable='true']",
                "div.ProseMirror[contenteditable='true']",
                "div[contenteditable='true'][role='textbox']",
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        desc_editor = elements[0]
                        print(f"[小红书发布] 找到正文编辑器: {selector}")
                        break
                except Exception:
                    continue

            if not desc_editor:
                # 备用：使用 XPath
                try:
                    desc_editor = self.driver.find_element(
                        By.XPATH, "//div[contains(@class, 'ProseMirror') and @contenteditable='true']"
                    )
                except Exception:
                    pass

            if not desc_editor:
                print("[小红书发布] [X] 未找到正文编辑器，跳过话题填写")
                return True  # 不强制要求

            # 点击编辑器获取焦点
            desc_editor.click()
            time.sleep(0.5)

            # 构建话题文本（小红书话题带#号，空格分隔）
            topics_list = [f"#{t.strip().lstrip('#')}" for t in topics if t.strip()]
            topics_text = " ".join(topics_list)

            # 方法1：使用 JavaScript 直接设置编辑器内容（避免逐字输入导致的位置错乱）
            try:
                self.driver.execute_script("""
                    var editor = arguments[0];
                    var text = arguments[1];
                    
                    // 查找或创建 p 元素
                    var p = editor.querySelector('p');
                    if (!p) {
                        p = document.createElement('p');
                        editor.appendChild(p);
                    }
                    
                    // 设置文本内容
                    p.textContent = text;
                    
                    // 移除 placeholder 类
                    p.classList.remove('is-empty', 'is-editor-empty');
                    
                    // 触发 input 事件
                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                    editor.dispatchEvent(new Event('change', { bubbles: true }));
                """, desc_editor, topics_text)
                print(f"[小红书发布] [OK] 使用JS填写话题: {topics_text}")
                time.sleep(0.5)
            except Exception as js_err:
                print(f"[小红书发布] JS方式失败: {js_err}，尝试备用方式...")
                
                # 方法2：使用 send_keys 一次性输入完整文本
                try:
                    # 先清空编辑器
                    desc_editor.click()
                    time.sleep(0.2)
                    
                    # 全选并删除
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
                    actions.perform()
                    time.sleep(0.1)
                    
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.DELETE)
                    actions.perform()
                    time.sleep(0.2)
                    
                    # 一次性输入完整的话题文本
                    actions = ActionChains(self.driver)
                    actions.send_keys(topics_text)
                    actions.perform()
                    print(f"[小红书发布] [OK] 使用send_keys填写话题: {topics_text}")
                except Exception as sk_err:
                    print(f"[小红书发布] send_keys方式也失败: {sk_err}")

            update_progress(70, f"话题已填写")
            return True

        except Exception as e:
            print(f"[小红书发布] 填写正文描述失败: {e}")
            traceback.print_exc()
            return True  # 不强制要求

    # ------------------------------------------------------------
    #  点击发布按钮
    # ------------------------------------------------------------
    def _click_publish(self, update_progress):
        """
        点击发布按钮
        小红书发布按钮: <button class="d-button ... bg-red">发布</button>
        """
        print("[小红书发布] == 点击发布 ==")
        update_progress(85, "正在发布视频...")

        try:
            publish_btn = None

            # 方法1：查找含有"发布"文字的按钮
            selectors = [
                "button.d-button.bg-red",
                "button[class*='bg-red']",
                "button.d-button",
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if "发布" in elem.text:
                            publish_btn = elem
                            print(f"[小红书发布] 找到发布按钮")
                            break
                    if publish_btn:
                        break
                except Exception:
                    continue

            # 备用：XPath 查找
            if not publish_btn:
                try:
                    publish_btn = self.driver.find_element(
                        By.XPATH, "//button[contains(@class, 'bg-red')]//span[contains(text(), '发布')]/ancestor::button"
                    )
                except Exception:
                    pass

            if not publish_btn:
                try:
                    # 查找任何包含"发布"的按钮
                    publish_btn = self.driver.find_element(
                        By.XPATH, "//button[.//span[contains(text(), '发布')] or contains(text(), '发布')]"
                    )
                except Exception:
                    pass

            if not publish_btn:
                return False, "找不到发布按钮"

            # 滚动到按钮可见位置
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior:'smooth',block:'center'});",
                publish_btn)
            time.sleep(0.5)

            # 点击
            try:
                publish_btn.click()
            except Exception:
                # 如果直接点击失败，使用 JS 点击
                self.driver.execute_script("arguments[0].click();", publish_btn)

            print("[小红书发布] [OK] 已点击发布按钮")
            time.sleep(3)

            update_progress(100, "发布成功！")
            return True, "视频已成功发布到小红书"

        except Exception as e:
            return False, f"点击发布按钮失败: {str(e)}"

    # ------------------------------------------------------------
    #  publish - 完整发布流程（含登录检查）
    # ------------------------------------------------------------
    def publish(self, video_path, title, topics=None, progress_callback=None, step_callback=None):
        """
        完整的发布流程（包含登录检查）

        流程总览：
        +-----------------------------------------------+
        | 步骤1  启动浏览器                              |
        | 步骤2  打开小红书发布页面，检测登录状态         |
        |   |- 已登录 -> 继续                           |
        |   +- 未登录 -> 等待用户登录                   |
        | 步骤3  上传视频文件                            |
        | 步骤4  等待视频上传完成                        |
        | 步骤5  填写标题                                |
        | 步骤6  填写正文描述（话题）                    |
        | 步骤7  点击发布                                |
        +-----------------------------------------------+

        :param video_path: 视频文件路径
        :param title: 视频标题
        :param topics: 话题列表（小红书带#号，空格分隔）
        :param progress_callback: 进度回调 callback(percent, message)
        :param step_callback: 步骤回调 callback(step_name, step_detail)
        :return: (success, message)
        """
        def _step(name, detail=""):
            print(f"[小红书发布] [{name}] {detail}")
            if step_callback:
                step_callback(name, detail)

        def update_progress(pct, msg):
            print(f"[小红书发布] [{pct}%] {msg}")
            if progress_callback:
                progress_callback(pct, msg)

        try:
            if not os.path.exists(video_path):
                return False, f"视频文件不存在: {video_path}"

            if not title or not title.strip():
                return False, "标题不能为空，请填写视频标题后再发布"

            # -- 步骤1：启动浏览器 --
            _step("步骤1：启动浏览器", "正在初始化 Chrome 驱动...")
            if not self._init_driver():
                return False, "浏览器初始化失败，请确保已安装 Chrome 浏览器"
            _step("步骤1：浏览器启动成功", "Chrome 已就绪")

            # -- 步骤2：检查登录状态 --
            _step("步骤2：检查登录状态", "正在访问小红书发布页面...")
            is_logged_in, msg = self._check_login(step_callback=step_callback)

            if not is_logged_in:
                # 需要登录
                _step("步骤2：需要登录", "检测到小红书登录页面，请在浏览器中完成登录")
                success, msg = self._wait_for_login(step_callback=step_callback)
                if not success:
                    return False, msg
                _step("步骤2：登录成功 [OK]", "已成功登录小红书，即将开始上传")
            else:
                _step("步骤2：已登录 [OK]", "检测到已登录状态")

            # -- 步骤3：上传视频文件 --
            _step("步骤3：开始上传视频", "请勿操作浏览器窗口")
            ok, msg = self._upload_video(video_path, update_progress)
            if not ok:
                return False, msg

            # -- 步骤4：等待视频上传完成 --
            _step("步骤4：等待上传完成", "正在上传视频...")
            self._wait_upload_complete(update_progress)
            time.sleep(2)

            # -- 步骤5：填写标题 --
            _step("步骤5：填写标题", "正在填写视频标题...")
            title_ok = self._fill_title(title, update_progress)
            if not title_ok:
                return False, "填写标题失败"

            # -- 步骤6：填写正文描述（话题） --
            _step("步骤6：填写正文描述", "正在填写话题...")
            self._fill_description(topics, update_progress)

            # -- 步骤7：点击发布 --
            _step("步骤7：点击发布", "正在发布...")
            return self._click_publish(update_progress)

        except Exception as e:
            print(f"[小红书发布] 发布流程失败: {e}")
            traceback.print_exc()
            return False, f"发布失败: {str(e)}"
        finally:
            # 不关闭浏览器，保持登录状态
            pass

    # ------------------------------------------------------------
    #  关闭浏览器
    # ------------------------------------------------------------
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                print("[小红书发布] 浏览器已关闭")
            except Exception:
                pass
            self.driver = None


# ==============================================================
#  测试代码
# ==============================================================
if __name__ == "__main__":
    publisher = XiaohongshuPublisher()

    # 测试视频路径
    test_video = r"D:\test_video.mp4"
    test_title = "这是一个测试视频标题"
    test_topics = ["测试", "小红书", "自动化"]

    def progress(pct, msg):
        print(f"进度: {pct}% - {msg}")

    def step(name, detail):
        print(f"\n{'='*50}")
        print(f"  {name}")
        print(f"  {detail}")
        print(f"{'='*50}")

    success, message = publisher.publish(
        test_video,
        test_title,
        test_topics,
        progress_callback=progress,
        step_callback=step
    )

    print(f"\n结果: {'[OK] 成功' if success else '[X] 失败'} - {message}")

    # 等待用户查看结果
    input("按回车键关闭浏览器...")
    publisher.close()
