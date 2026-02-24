# -*- coding: utf-8 -*-
# lib_shipinhao_publish.py - 视频号自动发布模块

import os
import sys
import time
import traceback
import platform
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 尝试导入 pyautogui（用于处理原生文件对话框）
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[视频号发布] 警告: pyautogui 未安装，将无法处理原生文件对话框")

# 视频号可能的发布页面 URL
SHIPINHAO_CREATE_URL = "https://channels.weixin.qq.com/platform/post/create"
SHIPINHAO_CREATE_URL_ALT = "https://channels.weixin.qq.com/post/create"  # 备用 URL
SHIPINHAO_LOGIN_URL = "https://channels.weixin.qq.com/login.html"


class ShipinhaoPublisher:
    """视频号自动发布工具 - 完整流程"""

    # Shadow DOM 穿透辅助 JavaScript
    SHADOW_DOM_JS = '''
    // 递归搜索 Shadow DOM 中的元素
    function searchInShadowDom(root, selector) {
        var results = [];
        // 先在当前节点查找
        var found = root.querySelectorAll(selector);
        results = results.concat(Array.from(found));
        
        // 遍历所有子元素
        var allElements = root.querySelectorAll("*");
        for (var i = 0; i < allElements.length; i++) {
            var el = allElements[i];
            if (el.shadowRoot) {
                var shadowResults = searchInShadowDom(el.shadowRoot, selector);
                results = results.concat(shadowResults);
            }
        }
        return results;
    }
    
    // 搜索包含指定文本的元素
    function findElementByTextInShadowDom(root, tagName, text) {
        var elements = searchInShadowDom(root, tagName);
        for (var i = 0; i < elements.length; i++) {
            if (elements[i].textContent && elements[i].textContent.trim().includes(text)) {
                return elements[i];
            }
        }
        return null;
    }
    '''

    def __init__(self, user_data_dir=None):
        """
        初始化发布器
        :param user_data_dir: Chrome用户数据目录，用于保持登录状态
        """
        self.driver = None
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.expanduser("~"), "AppData", "Local", "ShipinhaoPublisher"
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
            print(f"[视频号发布] 使用打包驱动: {driver_folder_path}")
            return driver_folder_path

        # 检查当前目录
        driver_path = os.path.join(self.base_dir, driver_name)
        if os.path.exists(driver_path):
            print(f"[视频号发布] 使用本地驱动: {driver_path}")
            return driver_path

        print("[视频号发布] 未找到本地驱动，尝试使用系统驱动")
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
        chrome_options.add_argument("--window-size=1280,800")

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
                print("[视频号发布] 使用本地 ChromeDriver 初始化浏览器")
            else:
                print("[视频号发布] 尝试使用系统 ChromeDriver...")
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[视频号发布] 使用系统 ChromeDriver 初始化浏览器")

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

            print("[视频号发布] 浏览器初始化成功")
            return True
        except Exception as e:
            print(f"[视频号发布] 浏览器初始化失败: {e}")
            traceback.print_exc()
            return False

    # ------------------------------------------------------------
    #  检查登录状态
    # ------------------------------------------------------------
    def _check_login(self, step_callback=None):
        """
        打开视频号发布页面，检测是否处于登录状态。
        如果跳转到 login.html 说明未登录。
        :return: (is_logged_in, message)
        """
        def _step(name, detail=""):
            print(f"[视频号发布] {name} {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            print("[视频号发布] == 检查登录状态 ==")
            self.driver.get(SHIPINHAO_CREATE_URL)
            time.sleep(3)

            current_url = self.driver.current_url
            print(f"[视频号发布] 当前页面 URL: {current_url}")

            # 如果跳转到了登录页面
            if "login" in current_url.lower():
                print("[视频号发布] 检测到登录页面，需要用户扫码登录")
                return False, "检测到视频号登录页面，请扫码登录"

            # 如果还在 create 页面，说明已登录
            if "post/create" in current_url:
                print("[视频号发布] 已在发布页面，已登录")
                return True, "已登录"

            # 兜底判断
            if "channels.weixin.qq.com" in current_url and "login" not in current_url:
                print("[视频号发布] 停留在视频号平台，视为已登录")
                return True, "已登录"

            print("[视频号发布] 未检测到登录态")
            return False, "未登录，需要扫码登录"

        except Exception as e:
            print(f"[视频号发布] 检查登录状态失败: {e}")
            traceback.print_exc()
            return False, f"检查失败: {str(e)}"

    # ------------------------------------------------------------
    #  等待用户扫码登录
    # ------------------------------------------------------------
    def _wait_for_login(self, timeout=300, step_callback=None):
        """
        在登录页面等待用户扫码登录。
        登录成功后页面会自动跳转回 create 页面。
        :param timeout: 最长等待时间（秒）
        :param step_callback: 步骤回调
        :return: (success, message)
        """
        def _step(name, detail=""):
            print(f"[视频号发布] {name} {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            _step("请扫码登录", "请在浏览器中使用微信扫描二维码完成登录")
            print("[视频号发布] == 等待扫码登录 ==")

            start_time = time.time()
            check_count = 0
            while time.time() - start_time < timeout:
                check_count += 1

                current_url = self.driver.current_url

                # 检测是否已跳转回发布页面（登录成功后自动跳转）
                if "post/create" in current_url:
                    print("[视频号发布] [OK] 已跳转到发布页面，登录成功!")
                    _step("扫码登录成功!", "已跳转到视频发布页面")
                    time.sleep(2)
                    return True, "登录成功"

                # 检测URL不再是登录页面
                if "login" not in current_url.lower() and "channels.weixin.qq.com" in current_url:
                    print("[视频号发布] [OK] 页面已变化，登录成功!")
                    _step("扫码登录成功!", "正在跳转到视频发布页面...")
                    time.sleep(1)
                    # 主动跳转到发布页面
                    self.driver.get(SHIPINHAO_CREATE_URL)
                    time.sleep(3)
                    return True, "登录成功"

                # 每30秒打印一次提醒
                if check_count % 30 == 0:
                    elapsed = int(time.time() - start_time)
                    remaining = timeout - elapsed
                    _step("等待扫码登录...", f"已等待 {elapsed} 秒，剩余 {remaining} 秒")

                time.sleep(1)

            return False, "登录超时(5分钟内未完成扫码)"

        except Exception as e:
            print(f"[视频号发布] 等待登录失败: {e}")
            traceback.print_exc()
            return False, f"等待登录失败: {str(e)}"

    # ------------------------------------------------------------
    #  上传视频文件
    # ------------------------------------------------------------
    def _upload_video(self, video_path, update_progress):
        """
        上传视频文件到视频号
        等待页面加载完成后，直接查找 input[type="file"] 并发送文件路径
        """
        print("[视频号发布] == 上传视频文件 ==")
        update_progress(10, "等待页面加载...")

        try:
            # 确保在发布页面
            current_url = self.driver.current_url
            if "post/create" not in current_url and "/create" not in current_url:
                print("[视频号发布] 不在发布页面，跳转...")
                self.driver.get(SHIPINHAO_CREATE_URL)
            
            # 等待5秒让页面完全加载（包括上传组件）
            print("[视频号发布] 等待页面加载完成（5秒）...")
            time.sleep(5)
            
            # 确保在主文档（不在iframe中）
            self.driver.switch_to.default_content()
            
            # 使用JavaScript查找并操作隐藏的 input[type="file"]
            # 视频号助手使用 wujie 微前端框架，子应用渲染在 Shadow DOM 中
            # 所以 document.querySelectorAll 无法直接找到 Shadow DOM 内的元素
            # 需要遍历 Shadow DOM 来查找 input[type="file"]
            print("[视频号发布] 使用JavaScript查找并操作 input[type='file']（含Shadow DOM遍历）...")
            
            video_abs_path = os.path.abspath(video_path)
            print(f"[视频号发布] 文件路径: {video_abs_path}")
            
            # 策略说明：
            # 视频号助手使用 wujie 微前端框架，子应用渲染在 Shadow DOM 中
            # Selenium 的 WebDriver 协议无法稳定引用 Shadow DOM 内的元素
            # （无论是 execute_script 返回、shadow_root.find_element 都会 StaleElementReference）
            # 最终方案：使用 Chrome DevTools Protocol (CDP) 直接操作：
            #   1. 用 CDP Runtime.evaluate 在 JS 中找到 Shadow DOM 内的 file input（返回 RemoteObject）
            #   2. 用 CDP DOM.describeNode 获取 backendNodeId
            #   3. 用 CDP DOM.setFileInputFiles 直接设置文件，完全绕过 Selenium 元素引用
            
            # 先尝试 CDP 方案（适用于 Shadow DOM）
            print("[视频号发布] 使用 CDP 方案查找 file input（穿透 Shadow DOM）...")
            
            try:
                cdp_success = False
                
                # 用 CDP Runtime.evaluate 在 JS 中查找 file input（包括 Shadow DOM 内的）
                # 返回的是 CDP RemoteObject，不经过 WebDriver 协议，不会 StaleElement
                cdp_result = self.driver.execute_cdp_cmd('Runtime.evaluate', {
                    'expression': '''
                        (function() {
                            function findFileInput(root) {
                                var inputs = root.querySelectorAll('input[type="file"]');
                                for (var i = 0; i < inputs.length; i++) {
                                    if ((inputs[i].getAttribute('accept') || '').indexOf('video') !== -1) {
                                        return inputs[i];
                                    }
                                }
                                if (inputs.length > 0) return inputs[0];
                                var all = root.querySelectorAll('*');
                                for (var j = 0; j < all.length; j++) {
                                    if (all[j].shadowRoot) {
                                        var found = findFileInput(all[j].shadowRoot);
                                        if (found) return found;
                                    }
                                }
                                return null;
                            }
                            return findFileInput(document);
                        })()
                    ''',
                    'returnByValue': False
                })
                
                print(f"[视频号发布] CDP Runtime.evaluate 结果: type={cdp_result.get('result', {}).get('type')}, "
                      f"subtype={cdp_result.get('result', {}).get('subtype')}, "
                      f"className={cdp_result.get('result', {}).get('className')}")
                
                remote_object = cdp_result.get('result', {})
                object_id = remote_object.get('objectId')
                
                if object_id and remote_object.get('type') != 'undefined' and remote_object.get('subtype') != 'null':
                    # 找到了 file input 的 RemoteObject
                    # 用 DOM.describeNode 获取 backendNodeId
                    node_info = self.driver.execute_cdp_cmd('DOM.describeNode', {
                        'objectId': object_id
                    })
                    backend_node_id = node_info['node']['backendNodeId']
                    print(f"[视频号发布] 获取到 backendNodeId: {backend_node_id}")
                    
                    # 用 CDP DOM.setFileInputFiles 直接设置文件
                    self.driver.execute_cdp_cmd('DOM.setFileInputFiles', {
                        'files': [video_abs_path],
                        'backendNodeId': backend_node_id
                    })
                    print("[视频号发布] CDP DOM.setFileInputFiles 成功")
                    cdp_success = True
                else:
                    print("[视频号发布] CDP 未找到 file input (RemoteObject 为空/null)")
                
            except Exception as cdp_err:
                print(f"[视频号发布] CDP 方案异常: {cdp_err}")
                traceback.print_exc()
                cdp_success = False
            
            if not cdp_success:
                # CDP 失败，回退到常规 Selenium 方式（仅适用于主文档中的 file input）
                print("[视频号发布] CDP 方案失败，回退到常规 Selenium 查找...")
                try:
                    file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    file_input = None
                    for inp in file_inputs:
                        accept = inp.get_attribute('accept') or ''
                        if 'video' in accept:
                            file_input = inp
                            break
                    if not file_input and file_inputs:
                        file_input = file_inputs[0]
                    if not file_input:
                        return False, "未找到 file input（CDP 和常规方式均失败）"
                    
                    self.driver.execute_script("""
                        arguments[0].style.display = 'block';
                        arguments[0].style.visibility = 'visible';
                        arguments[0].style.opacity = '1';
                        arguments[0].style.position = 'absolute';
                        arguments[0].style.zIndex = '99999';
                    """, file_input)
                    print(f"[视频号发布] 回退方式：找到主文档中的 file input (共{len(file_inputs)}个)")
                    file_input.send_keys(video_abs_path)
                    print("[视频号发布] 文件路径已发送（回退方式）")
                except Exception as fallback_err:
                    return False, f"所有上传方式均失败。CDP: {cdp_err}, 常规: {fallback_err}"
            
            print(f"[视频号发布] 文件上传操作完成: {video_abs_path}")
            
            update_progress(15, "正在上传视频文件...")
            return True, "视频文件已发送"
            
        except Exception as e:
            print(f"[视频号发布] 上传视频失败: {e}")
            traceback.print_exc()
            return False, f"上传失败: {str(e)}"

    # ------------------------------------------------------------
    #  等待视频上传完成
    # ------------------------------------------------------------
    def _wait_upload_complete(self, update_progress, max_wait=300):
        """
        等待视频上传完成。
        检测 <video id="fullScreenVideo"> 出现表示上传成功。
        """
        print("[视频号发布] == 等待视频上传完成 ==")
        update_progress(20, "等待视频上传完成...")
        time.sleep(3)

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # 方法1: 通过 ID 检测 fullScreenVideo
                videos = self.driver.find_elements(By.ID, "fullScreenVideo")
                if videos:
                    print("[视频号发布] [OK] 检测到 fullScreenVideo (By.ID)，视频上传完成")
                    update_progress(40, "视频上传完成")
                    return True

                # 方法2: 通过 CSS 选择器检测带 blob src 的 video
                video_elements = self.driver.find_elements(By.CSS_SELECTOR, "video[src^='blob:']")
                if video_elements:
                    print("[视频号发布] [OK] 检测到 blob video，视频上传完成")
                    update_progress(40, "视频上传完成")
                    return True

                # 方法3: 使用 JavaScript 穿透 Shadow DOM 检测
                video_check = self.driver.execute_script('''
                    // 递归搜索 Shadow DOM 中的元素
                    function searchInShadowDom(root, selector) {
                        // 先在当前节点查找
                        var found = root.querySelectorAll(selector);
                        if (found.length > 0) return Array.from(found);
                        
                        var results = [];
                        // 遍历所有子元素
                        var allElements = root.querySelectorAll("*");
                        for (var i = 0; i < allElements.length; i++) {
                            var el = allElements[i];
                            // 如果有 shadowRoot，递归搜索
                            if (el.shadowRoot) {
                                var shadowResults = searchInShadowDom(el.shadowRoot, selector);
                                results = results.concat(shadowResults);
                            }
                        }
                        return results;
                    }
                    
                    // 搜索所有 video 元素（包括 Shadow DOM 内部）
                    var videos = searchInShadowDom(document, "video");
                    
                    for (var i = 0; i < videos.length; i++) {
                        var v = videos[i];
                        var src = v.src || v.getAttribute("src") || "";
                        if (v.id === "fullScreenVideo" || src.startsWith("blob:")) {
                            return {found: true, method: "shadowDom", src: src, id: v.id || ""};
                        }
                    }
                    
                    // 也搜索“封面预览”文字作为备用检测
                    function searchTextInShadowDom(root, text) {
                        if (root.textContent && root.textContent.includes(text)) {
                            return true;
                        }
                        var allElements = root.querySelectorAll("*");
                        for (var i = 0; i < allElements.length; i++) {
                            var el = allElements[i];
                            if (el.shadowRoot) {
                                if (searchTextInShadowDom(el.shadowRoot, text)) {
                                    return true;
                                }
                            }
                        }
                        return false;
                    }
                    
                    var hasCoverPreview = searchTextInShadowDom(document, "封面预览");
                    
                    return {found: false, videoCount: videos.length, hasCoverPreview: hasCoverPreview};
                ''')
                
                if video_check and video_check.get('found'):
                    print(f"[视频号发布] [OK] JS检测到视频上传完成 - 方法: {video_check.get('method')}, id: {video_check.get('id', '')}, src前缀: {video_check.get('src', '')[:50]}")
                    update_progress(40, "视频上传完成")
                    return True
                
                # 备用检测：如果检测到"封面预览"文字，说明视频已上传完成
                if video_check and video_check.get('hasCoverPreview'):
                    print("[视频号发布] [OK] 检测到'封面预览'文字，视频上传完成")
                    update_progress(40, "视频上传完成")
                    return True

                elapsed = int(time.time() - start_time)
                # 每10秒打印一次调试信息
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"[视频号发布] 调试: video数量={video_check.get('videoCount', 0) if video_check else 'N/A'}, 封面预览={video_check.get('hasCoverPreview', False) if video_check else 'N/A'}")
                
                update_progress(20 + min(elapsed // 10, 15), f"视频上传中...已等待 {elapsed} 秒")

            except Exception as e:
                print(f"[视频号发布] 检查上传状态异常: {e}")

            time.sleep(2)

        print("[视频号发布] 警告：上传状态检测超时，继续执行...")
        return False

    # ------------------------------------------------------------
    #  填写标题和话题 (Shadow DOM 版本)
    # ------------------------------------------------------------
    def _fill_title_and_topics(self, title, topics, update_progress):
        """
        在 Shadow DOM 内的编辑器中填写标题和话题。
        """
        print("[视频号发布] == 填写标题和话题 ==")
        update_progress(50, "正在填写标题和话题...")

        try:
            # 使用 JavaScript 在 Shadow DOM 中查找并操作编辑器
            safe_title = (title or "精彩视频")[:30]
            
            result = self.driver.execute_script(self.SHADOW_DOM_JS + '''
                // 查找描述编辑器
                // 注意: contenteditable 属性可能是空字符串或"true"，都表示可编辑
                var editors = searchInShadowDom(document, "div.input-editor[contenteditable]");
                if (editors.length === 0) {
                    editors = searchInShadowDom(document, "div[contenteditable][data-placeholder='添加描述']");
                }
                if (editors.length === 0) {
                    editors = searchInShadowDom(document, "div.input-editor");
                }
                if (editors.length === 0) {
                    editors = searchInShadowDom(document, "div[contenteditable]");
                }
                
                if (editors.length === 0) {
                    return {success: false, error: "未找到描述编辑器"};
                }
                
                var editor = editors[0];
                // 点击获取焦点
                editor.click();
                editor.focus();
                
                return {success: true, found: true};
            ''')
            
            if not result or not result.get('success'):
                print(f"[视频号发布] [X] {result.get('error', '未找到编辑器')}")
                return False
            
            time.sleep(0.5)
            
            # 使用 ActionChains 输入标题
            actions = ActionChains(self.driver)
            # 先清空现有内容
            actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
            actions.perform()
            time.sleep(0.2)
            
            actions = ActionChains(self.driver)
            actions.send_keys(safe_title)
            actions.perform()
            time.sleep(0.3)
            
            print(f"[视频号发布] [OK] 标题已填写: {safe_title}")

            # 输入话题（所有话题在同一行，用空格分隔）
            if topics:
                for topic in topics:
                    topic = topic.strip().lstrip('#')
                    if not topic:
                        continue

                    # 输入空格分隔（第一个话题前也加空格与标题分开）
                    actions = ActionChains(self.driver)
                    actions.send_keys(" ")
                    actions.perform()
                    time.sleep(0.2)

                    # 输入 # + 话题
                    actions = ActionChains(self.driver)
                    actions.send_keys(f"#{topic}")
                    actions.perform()
                    time.sleep(1)

                    # 尝试在 Shadow DOM 中查找话题联想
                    try:
                        suggestion_found = self.driver.execute_script(self.SHADOW_DOM_JS + '''
                            var suggestions = searchInShadowDom(document, "div[class*='topic-item'], div[class*='mention-item'], li[class*='option']");
                            if (suggestions.length > 0) {
                                suggestions[0].click();
                                return true;
                            }
                            return false;
                        ''')
                        
                        if suggestion_found:
                            print(f"[视频号发布] [OK] 选中话题联想: #{topic}")
                            time.sleep(0.5)
                        else:
                            # 没有联想，按空格结束话题输入
                            actions = ActionChains(self.driver)
                            actions.send_keys(" ")
                            actions.perform()
                            print(f"[视频号发布] 无联想，直接输入话题: #{topic}")
                    except Exception:
                        actions = ActionChains(self.driver)
                        actions.send_keys(" ")
                        actions.perform()

                print(f"[视频号发布] [OK] 话题已填写: {topics}")

            update_progress(70, "标题和话题已填写")
            return True

        except Exception as e:
            print(f"[视频号发布] 填写标题和话题失败: {e}")
            traceback.print_exc()
            return False

    # ------------------------------------------------------------
    #  点击发表按钮 (Shadow DOM 版本)
    # ------------------------------------------------------------
    def _click_publish(self, update_progress):
        """
        在 Shadow DOM 中查找并点击发表按钮
        """
        print("[视频号发布] == 点击发表 ==")
        update_progress(85, "正在发布视频...")

        try:
            # 使用 JavaScript 在 Shadow DOM 中查找并点击发表按钮
            # 优先通过文字内容精确匹配"发表"按钮
            result = self.driver.execute_script(self.SHADOW_DOM_JS + '''
                // 查找所有按钮
                var allButtons = searchInShadowDom(document, "button");
                var publishBtn = null;
                
                // 优先查找文字内容为"发表"的按钮
                for (var i = 0; i < allButtons.length; i++) {
                    var text = (allButtons[i].textContent || allButtons[i].innerText || "").trim();
                    if (text === "发表") {
                        publishBtn = allButtons[i];
                        break;
                    }
                }
                
                // 备用：通过 class 查找 primary 按钮
                if (!publishBtn) {
                    var primaryButtons = searchInShadowDom(document, "button.weui-desktop-btn_primary");
                    for (var i = 0; i < primaryButtons.length; i++) {
                        var text = (primaryButtons[i].textContent || primaryButtons[i].innerText || "").trim();
                        if (text === "发表") {
                            publishBtn = primaryButtons[i];
                            break;
                        }
                    }
                }
                
                if (!publishBtn) {
                    return {success: false, error: "找不到发表按钮"};
                }
                
                // 滚动到可见位置
                publishBtn.scrollIntoView({behavior: "smooth", block: "center"});
                
                return {success: true, ready: true};
            ''')
            
            if not result or not result.get('success'):
                return False, result.get('error', '找不到发表按钮')
            
            time.sleep(0.5)
            
            # 点击按钮 - 精确匹配文字为"发表"的按钮
            click_result = self.driver.execute_script(self.SHADOW_DOM_JS + '''
                var allButtons = searchInShadowDom(document, "button");
                var publishBtn = null;
                
                for (var i = 0; i < allButtons.length; i++) {
                    var text = (allButtons[i].textContent || allButtons[i].innerText || "").trim();
                    if (text === "发表") {
                        publishBtn = allButtons[i];
                        break;
                    }
                }
                
                if (publishBtn) {
                    publishBtn.click();
                    return {success: true};
                }
                return {success: false};
            ''')
            
            if click_result and click_result.get('success'):
                print("[视频号发布] [OK] 已点击发表按钮")
                time.sleep(3)
                update_progress(100, "发布成功！")
                return True, "视频已成功发布到视频号"
            else:
                return False, "点击发表按钮失败"

        except Exception as e:
            return False, f"点击发表按钮失败: {str(e)}"

    # ------------------------------------------------------------
    #  publish - 完整发布流程（含登录检查）
    # ------------------------------------------------------------
    def publish(self, video_path, title, topics=None, progress_callback=None, step_callback=None):
        """
        完整的发布流程（包含登录检查）

        流程总览：
        +-----------------------------------------------+
        | 步骤1  启动浏览器                              |
        | 步骤2  打开视频号发布页面，检测登录状态        |
        |   |- 已登录 -> 继续                             |
        |   +- 未登录 -> 等待扫码登录                     |
        | 步骤3  上传视频文件                            |
        | 步骤4  等待视频上传完成                        |
        | 步骤5  填写标题和话题                          |
        | 步骤6  点击发表                                |
        +-----------------------------------------------+

        :param video_path: 视频文件路径
        :param title: 视频标题
        :param topics: 话题列表
        :param progress_callback: 进度回调 callback(percent, message)
        :param step_callback: 步骤回调 callback(step_name, step_detail)
        :return: (success, message)
        """
        def _step(name, detail=""):
            print(f"[视频号发布] [{name}] {detail}")
            if step_callback:
                step_callback(name, detail)

        def update_progress(pct, msg):
            print(f"[视频号发布] [{pct}%] {msg}")
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
            _step("步骤2：检查登录状态", "正在访问视频号发布页面...")
            is_logged_in, msg = self._check_login(step_callback=step_callback)

            if not is_logged_in:
                # 需要扫码登录
                _step("步骤2：需要扫码登录", "检测到视频号登录页面，请使用微信扫描屏幕上的二维码")
                success, msg = self._wait_for_login(step_callback=step_callback)
                if not success:
                    return False, msg
                _step("步骤2：登录成功 [OK]", "已成功登录视频号平台，即将开始上传")
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

            # -- 步骤5：填写标题和话题 --
            _step("步骤5：填写标题和话题", "正在填写发布信息...")
            title_ok = self._fill_title_and_topics(title, topics, update_progress)
            if not title_ok:
                return False, "填写标题和话题失败"

            # -- 步骤6：点击发表 --
            _step("步骤6：点击发表", "正在发布...")
            return self._click_publish(update_progress)

        except Exception as e:
            print(f"[视频号发布] 发布流程失败: {e}")
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
                print("[视频号发布] 浏览器已关闭")
            except Exception:
                pass
            self.driver = None
