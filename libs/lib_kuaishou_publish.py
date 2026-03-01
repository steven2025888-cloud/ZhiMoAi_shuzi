# -*- coding: utf-8 -*-
# lib_kuaishou_publish.py - 快手自动发布模块

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

# 快手相关 URL
KUAISHOU_UPLOAD_URL = "https://cp.kuaishou.com/article/publish/video?origin=www.kuaishou.com&source=NewReco"
KUAISHOU_HOME_URL = "https://cp.kuaishou.com/"


class KuaishouPublisher:
    """快手自动发布工具 - 完整流程"""

    def __init__(self, user_data_dir=None):
        """
        初始化发布器
        :param user_data_dir: Chrome用户数据目录，用于保持登录状态
        """
        self.driver = None
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.expanduser("~"), "AppData", "Local", "KuaishouPublisher"
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
            print(f"[快手发布] 使用打包驱动: {driver_folder_path}")
            return driver_folder_path

        # 检查当前目录
        driver_path = os.path.join(self.base_dir, driver_name)
        if os.path.exists(driver_path):
            print(f"[快手发布] 使用本地驱动: {driver_path}")
            return driver_path

        print("[快手发布] 未找到本地驱动，尝试使用系统驱动")
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
                print("[快手发布] 使用本地 ChromeDriver 初始化浏览器")
            else:
                print("[快手发布] 尝试使用系统 ChromeDriver...")
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[快手发布] 使用系统 ChromeDriver 初始化浏览器")

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

            print("[快手发布] 浏览器初始化成功")
            return True
        except Exception as e:
            print(f"[快手发布] 浏览器初始化失败: {e}")
            traceback.print_exc()
            return False

    # ------------------------------------------------------------
    #  检查登录状态
    # ------------------------------------------------------------
    def _check_login(self, step_callback=None):
        """
        打开快手创作者平台发布页面，检测是否处于登录状态。
        快手未登录时页面上会显示"立即登录"按钮。
        :return: (is_logged_in, message)
        """
        def _step(name, detail=""):
            print(f"[快手发布] {name} {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            print("[快手发布] == 检查登录状态 ==")
            self.driver.get(KUAISHOU_UPLOAD_URL)
            time.sleep(3)

            current_url = self.driver.current_url
            print(f"[快手发布] 当前页面 URL: {current_url}")

            # 检测页面是否有"立即登录"按钮
            try:
                page_source = self.driver.page_source
                if "立即登录" in page_source:
                    print("[快手发布] 检测到页面含'立即登录'，需要用户登录")
                    return False, "检测到快手登录页面，请登录"
            except Exception:
                pass

            # 如果 URL 包含 login 相关关键词
            if "login" in current_url.lower() or "passport" in current_url.lower():
                print("[快手发布] 检测到登录页面(URL)，需要用户登录")
                return False, "检测到快手登录页面，请登录"

            # 检测是否存在上传区域（已登录的标志）
            try:
                # 快手的上传 input 元素
                upload_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[type='file'][accept*='video']"
                )
                if upload_input:
                    print("[快手发布] 找到上传入口，已登录")
                    return True, "已登录"
            except NoSuchElementException:
                pass

            # 检测作品描述编辑区（已登录标志）
            try:
                desc_editor = self.driver.find_element(By.ID, "work-description-edit")
                if desc_editor:
                    print("[快手发布] 找到作品描述编辑器，已登录")
                    return True, "已登录"
            except NoSuchElementException:
                pass

            # 兜底判断：如果停留在创作者平台域名
            if "cp.kuaishou.com" in current_url and "login" not in current_url:
                print("[快手发布] 停留在创作中心，视为已登录")
                return True, "已登录"

            print("[快手发布] 未检测到登录态")
            return False, "未登录，需要登录"

        except Exception as e:
            print(f"[快手发布] 检查登录状态失败: {e}")
            traceback.print_exc()
            return False, f"检查失败: {str(e)}"

    # ------------------------------------------------------------
    #  等待用户登录
    # ------------------------------------------------------------
    def _wait_for_login(self, timeout=300, step_callback=None):
        """
        在登录页面等待用户登录。
        监听页面变化，当"立即登录"消失或出现上传区域时，视为登录成功。
        :param timeout: 最长等待时间（秒）
        :param step_callback: 步骤回调
        :return: (success, message)
        """
        def _step(name, detail=""):
            print(f"[快手发布] {name} {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            _step("请登录快手", "请在浏览器中完成登录（支持扫码/手机验证码）")
            print("[快手发布] == 等待用户登录 ==")

            # 降低隐式等待避免卡顿
            self.driver.implicitly_wait(0.3)

            start_time = time.time()
            check_count = 0
            while time.time() - start_time < timeout:
                check_count += 1

                # 方式1：检测页面是否还有"立即登录"
                try:
                    page_source = self.driver.page_source
                    if "立即登录" not in page_source:
                        # "立即登录"消失了，可能已登录
                        # 再检查是否有上传区域
                        try:
                            upload_input = self.driver.find_element(
                                By.CSS_SELECTOR, "input[type='file'][accept*='video']"
                            )
                            if upload_input:
                                print("[快手发布] [OK] 检测到上传区域，登录成功!")
                                _step("登录成功!", "已检测到上传入口")
                                self.driver.implicitly_wait(2)
                                time.sleep(2)
                                return True, "登录成功"
                        except NoSuchElementException:
                            pass

                        # 检测作品描述编辑器
                        try:
                            desc_editor = self.driver.find_element(By.ID, "work-description-edit")
                            if desc_editor:
                                print("[快手发布] [OK] 检测到作品描述编辑器，登录成功!")
                                _step("登录成功!", "已检测到编辑区域")
                                self.driver.implicitly_wait(2)
                                time.sleep(2)
                                return True, "登录成功"
                        except NoSuchElementException:
                            pass
                except Exception:
                    pass

                # 方式2：检测URL变化
                current_url = self.driver.current_url
                if "publish/video" in current_url and "login" not in current_url.lower():
                    # 仍在发布页面，再次检查登录状态
                    try:
                        upload_input = self.driver.find_element(
                            By.CSS_SELECTOR, "input[type='file'][accept*='video']"
                        )
                        if upload_input:
                            print("[快手发布] [OK] URL在发布页且找到上传入口，登录成功!")
                            _step("登录成功!", "已就绪")
                            self.driver.implicitly_wait(2)
                            time.sleep(2)
                            return True, "登录成功"
                    except NoSuchElementException:
                        pass

                # 每30秒打印一次提醒
                if check_count % 30 == 0:
                    elapsed = int(time.time() - start_time)
                    remaining = timeout - elapsed
                    _step("等待登录...", f"已等待 {elapsed} 秒，剩余 {remaining} 秒")

                time.sleep(1)

            self.driver.implicitly_wait(2)
            return False, "登录超时(5分钟内未完成登录)"

        except Exception as e:
            print(f"[快手发布] 等待登录失败: {e}")
            traceback.print_exc()
            return False, f"等待登录失败: {str(e)}"

    # ------------------------------------------------------------
    #  上传视频文件
    # ------------------------------------------------------------
    def _upload_video(self, video_path, update_progress):
        """
        上传视频文件
        快手的上传 input: <input type="file" accept="video/*,.mp4,.mov,.flv,...">
        """
        print("[快手发布] == 上传视频文件 ==")
        update_progress(10, "查找上传入口...")

        try:
            # 查找视频上传 input
            upload_input = None
            selectors = [
                "input[type='file'][accept*='video']",
                "input[type='file'][accept*='.mp4']",
                "input[type='file']",
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        upload_input = elements[0]
                        print(f"[快手发布] 找到上传 input: {selector}")
                        break
                except Exception:
                    continue

            if not upload_input:
                return False, "找不到视频上传入口"

            update_progress(15, "正在上传视频文件...")
            upload_input.send_keys(os.path.abspath(video_path))

            print(f"[快手发布] 视频文件已发送: {video_path}")
            return True, "视频文件已发送"

        except Exception as e:
            return False, f"上传视频失败: {str(e)}"

    # ------------------------------------------------------------
    #  等待视频上传完成
    # ------------------------------------------------------------
    def _wait_video_upload(self, update_progress, max_wait=300):
        """
        等待视频上传完成
        """
        print("[快手发布] == 等待视频上传完成 ==")
        update_progress(20, "等待视频上传完成...")
        time.sleep(5)  # 等待上传开始

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # 检测上传进度或完成状态
                # 快手可能有不同的进度指示器，这里用通用方式检测
                
                # 检测是否有上传进度条
                progress_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "[class*='progress'], [class*='upload']"
                )
                
                # 检测描述编辑器是否可编辑（上传完成的标志之一）
                try:
                    desc_editor = self.driver.find_element(By.ID, "work-description-edit")
                    # 检查编辑器是否可用
                    if desc_editor.get_attribute("contenteditable") == "true":
                        # 再等待一下确保完全就绪
                        time.sleep(3)
                        print("[快手发布] [OK] 视频上传完成")
                        update_progress(40, "视频上传完成")
                        return True
                except NoSuchElementException:
                    pass

                elapsed = int(time.time() - start_time)
                update_progress(20 + min(elapsed // 10, 15), f"视频上传中...已等待 {elapsed} 秒")

            except Exception as e:
                print(f"[快手发布] 检查上传状态异常: {e}")

            time.sleep(2)

        print("[快手发布] 警告：上传状态检测超时，继续执行...")
        return False

    # ------------------------------------------------------------
    #  填写标题和话题
    # ------------------------------------------------------------
    def _fill_title_and_topics(self, title, topics, update_progress):
        """
        填写标题和话题
        快手的标题和话题都在同一个编辑器中：
        <div class="_description_17g9x_24" id="work-description-edit" 
             placeholder="作品描述不会写？试试智能文案" contenteditable="true"></div>
        """
        print("[快手发布] == 填写标题和话题 ==")
        update_progress(50, "正在填写标题和话题...")

        try:
            # 查找作品描述编辑器
            desc_editor = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "work-description-edit"))
            )

            # 点击编辑器获取焦点
            desc_editor.click()
            time.sleep(0.5)

            # 构建内容：标题 + 话题
            content_parts = []
            
            # 添加标题
            if title and title.strip():
                content_parts.append(title.strip())
            
            # 添加话题（快手话题也是 #话题 格式）
            if topics:
                topics_text = " ".join([f"#{t.strip().lstrip('#')}" for t in topics if t.strip()])
                if topics_text:
                    content_parts.append(topics_text)

            full_content = " ".join(content_parts)

            # 方法1：使用 JavaScript 设置内容
            try:
                self.driver.execute_script("""
                    var editor = arguments[0];
                    var text = arguments[1];
                    
                    // 清空编辑器
                    editor.innerHTML = '';
                    
                    // 设置文本内容
                    editor.textContent = text;
                    
                    // 触发 input 事件
                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                    editor.dispatchEvent(new Event('change', { bubbles: true }));
                    editor.dispatchEvent(new Event('blur', { bubbles: true }));
                """, desc_editor, full_content)
                print(f"[快手发布] [OK] 使用JS填写内容: {full_content[:50]}...")
                time.sleep(0.5)
            except Exception as js_err:
                print(f"[快手发布] JS方式失败: {js_err}，尝试备用方式...")

                # 方法2：使用 ActionChains 输入
                try:
                    desc_editor.click()
                    time.sleep(0.3)
                    
                    # 全选并删除
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
                    actions.perform()
                    time.sleep(0.1)
                    
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.DELETE)
                    actions.perform()
                    time.sleep(0.2)
                    
                    # 输入内容
                    actions = ActionChains(self.driver)
                    actions.send_keys(full_content)
                    actions.perform()
                    print(f"[快手发布] [OK] 使用send_keys填写内容")
                except Exception as sk_err:
                    print(f"[快手发布] send_keys方式也失败: {sk_err}")

            update_progress(70, "标题和话题已填写")
            return True

        except TimeoutException:
            print("[快手发布] [X] 未找到作品描述编辑器")
            return False
        except Exception as e:
            print(f"[快手发布] 填写标题和话题失败: {e}")
            traceback.print_exc()
            return False

    # ------------------------------------------------------------
    #  点击发布按钮
    # ------------------------------------------------------------
    def _click_publish(self, update_progress):
        """
        点击发布按钮
        快手发布按钮: <div class="_button_3a3lq_1 _button-primary_3a3lq_60" style="width: 96px; height: 36px;"><div>发布</div></div>
        """
        print("[快手发布] == 点击发布 ==")
        update_progress(85, "正在发布视频...")

        try:
            publish_btn = None

            # 方法1：通过类名和文字查找
            try:
                # 查找包含"发布"文字的按钮
                buttons = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[class*='_button-primary']"
                )
                for btn in buttons:
                    if "发布" in btn.text:
                        publish_btn = btn
                        print("[快手发布] 找到发布按钮(class含_button-primary)")
                        break
            except Exception:
                pass

            # 方法2：XPath 查找含"发布"文字的 div
            if not publish_btn:
                try:
                    publish_btn = self.driver.find_element(
                        By.XPATH, "//div[contains(@class, '_button')][.//div[text()='发布']]"
                    )
                    print("[快手发布] 找到发布按钮(XPath)")
                except Exception:
                    pass

            # 方法3：查找任何含"发布"文字的可点击元素
            if not publish_btn:
                try:
                    elements = self.driver.find_elements(
                        By.XPATH, "//*[contains(text(), '发布')]"
                    )
                    for elem in elements:
                        # 优先选择按钮样式的元素
                        if "_button" in (elem.get_attribute("class") or ""):
                            publish_btn = elem
                            break
                    if not publish_btn and elements:
                        # 兜底：选择第一个
                        publish_btn = elements[-1]  # 通常发布按钮在后面
                    print("[快手发布] 找到发布按钮(文字匹配)")
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

            print("[快手发布] [OK] 已点击发布按钮")
            time.sleep(3)

            update_progress(100, "发布成功！")
            return True, "视频已成功发布到快手"

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
        | 步骤2  打开快手发布页面，检测登录状态           |
        |   |- 已登录 -> 继续                           |
        |   +- 未登录 -> 等待用户登录                   |
        | 步骤3  上传视频文件                            |
        | 步骤4  等待视频上传完成                        |
        | 步骤5  填写标题和话题                          |
        | 步骤6  点击发布                                |
        +-----------------------------------------------+

        :param video_path: 视频文件路径
        :param title: 视频标题
        :param topics: 话题列表（快手带#号）
        :param progress_callback: 进度回调 callback(percent, message)
        :param step_callback: 步骤回调 callback(step_name, step_detail)
        :return: (success, message)
        """
        def _step(name, detail=""):
            print(f"[快手发布] [{name}] {detail}")
            if step_callback:
                step_callback(name, detail)

        def update_progress(pct, msg):
            print(f"[快手发布] [{pct}%] {msg}")
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
            _step("步骤2：检查登录状态", "正在访问快手创作者平台...")
            is_logged_in, msg = self._check_login(step_callback)

            if not is_logged_in:
                # 需要登录
                _step("步骤2：需要登录", "检测到快手登录页面，请在浏览器中完成登录")
                success, msg = self._wait_for_login(step_callback=step_callback)
                if not success:
                    return False, msg
                _step("步骤2：登录成功 [OK]", "已成功登录快手创作者平台")
            else:
                _step("步骤2：已登录 [OK]", "检测到已登录状态")

            # -- 步骤3：上传视频 --
            _step("步骤3：开始上传视频", "请勿操作浏览器窗口")
            ok, msg = self._upload_video(video_path, update_progress)
            if not ok:
                return False, msg

            # -- 步骤4：等待视频上传完成 --
            _step("步骤4：等待上传完成", "视频正在处理中...")
            self._wait_video_upload(update_progress)
            time.sleep(2)

            # -- 步骤5：填写标题和话题 --
            _step("步骤5：填写标题和话题", "正在填写作品信息")
            self._fill_title_and_topics(title, topics, update_progress)

            # -- 步骤6：点击发布 --
            _step("步骤6：点击发布", "正在发布视频")
            return self._click_publish(update_progress)

        except Exception as e:
            print(f"[快手发布] 发布流程失败: {e}")
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
                print("[快手发布] 浏览器已关闭")
            except Exception:
                pass
            self.driver = None


# ==============================================================
#  测试代码
# ==============================================================
if __name__ == "__main__":
    publisher = KuaishouPublisher()

    # 测试视频路径
    test_video = r"D:\test_video.mp4"
    test_title = "这是一个测试视频标题，用于测试自动发布功能"
    test_topics = ["测试", "自动化"]

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
