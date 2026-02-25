# -*- coding: utf-8 -*-
"""
lib_douyin_publish.py - 抖音自动发布模块

基于 PublishBase 基类实现抖音视频发布功能。
"""

import os
import platform
import time
import traceback
import zipfile
from typing import Callable, List, Optional, Tuple

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 导入基类
try:
    from lib_publish_base import PublishBase
except ImportError:
    # 如果基类不可用，则使用空基类
    class PublishBase:
        pass

# ============================================================
# 常量配置
# ============================================================
DOUYIN_UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"
DOUYIN_HOME_URL = "https://creator.douyin.com/"

# ChromeDriver 下载地址
CHROMEDRIVER_BASE_URL = "https://chromedriver.storage.googleapis.com"
CHROMEDRIVER_LATEST_URL = f"{CHROMEDRIVER_BASE_URL}/LATEST_RELEASE"


def get_chrome_version():
    """获取本地 Chrome 浏览器版本"""
    try:
        if platform.system() == "Windows":
            import winreg
            # 尝试从注册表获取版本
            paths = [
                r"SOFTWARE\Google\Chrome\BLBeacon",
                r"SOFTWARE\Wow6432Node\Google\Chrome\BLBeacon",
            ]
            for path in paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    version, _ = winreg.QueryValueEx(key, "version")
                    winreg.CloseKey(key)
                    return version.split('.')[0]  # 返回主版本号
                except:
                    continue
        
        # 如果注册表方法失败，尝试执行 Chrome 命令
        import subprocess
        result = subprocess.run(
            ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            version = result.stdout.split()[-1]
            return version.split('.')[0]
    except Exception as e:
        print(f"[ChromeDriver] 获取 Chrome 版本失败: {e}")
    
    return None


def download_chromedriver(target_dir="."):
    """
    自动下载 ChromeDriver 到指定目录
    :param target_dir: 目标目录
    :return: ChromeDriver 路径或 None
    """
    try:
        print("[ChromeDriver] 开始下载 ChromeDriver...")
        
        # 获取 Chrome 版本
        chrome_version = get_chrome_version()
        if not chrome_version:
            print("[ChromeDriver] 无法获取 Chrome 版本，使用最新版本")
            chrome_version = None
        else:
            print(f"[ChromeDriver] 检测到 Chrome 版本: {chrome_version}")
        
        # 获取对应的 ChromeDriver 版本
        if chrome_version:
            try:
                version_url = f"{CHROMEDRIVER_BASE_URL}/LATEST_RELEASE_{chrome_version}"
                response = requests.get(version_url, timeout=10)
                driver_version = response.text.strip()
            except:
                # 如果特定版本不存在，使用最新版本
                response = requests.get(CHROMEDRIVER_LATEST_URL, timeout=10)
                driver_version = response.text.strip()
        else:
            response = requests.get(CHROMEDRIVER_LATEST_URL, timeout=10)
            driver_version = response.text.strip()
        
        print(f"[ChromeDriver] 将下载版本: {driver_version}")
        
        # 确定平台
        if platform.system() == "Windows":
            platform_name = "win32"
            driver_filename = "chromedriver.exe"
        elif platform.system() == "Darwin":
            platform_name = "mac64"
            driver_filename = "chromedriver"
        else:
            platform_name = "linux64"
            driver_filename = "chromedriver"
        
        # 下载 URL
        download_url = f"{CHROMEDRIVER_BASE_URL}/{driver_version}/chromedriver_{platform_name}.zip"
        print(f"[ChromeDriver] 下载地址: {download_url}")
        
        # 下载文件
        response = requests.get(download_url, timeout=60)
        if response.status_code != 200:
            print(f"[ChromeDriver] 下载失败，状态码: {response.status_code}")
            return None
        
        # 保存 zip 文件
        zip_path = os.path.join(target_dir, "chromedriver.zip")
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print(f"[ChromeDriver] 下载完成，正在解压...")
        
        # 解压
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        # 删除 zip 文件
        os.remove(zip_path)
        
        driver_path = os.path.join(target_dir, driver_filename)
        
        # Linux/Mac 需要添加执行权限
        if platform.system() != "Windows":
            os.chmod(driver_path, 0o755)
        
        print(f"[ChromeDriver] 安装成功: {driver_path}")
        return driver_path
        
    except Exception as e:
        print(f"[ChromeDriver] 下载失败: {e}")
        traceback.print_exc()
        return None


class DouyinPublisher:
    """抖音自动发布工具 - 完整流程"""

    def __init__(self, user_data_dir=None):
        """
        初始化发布器
        :param user_data_dir: Chrome用户数据目录，用于保持登录状态
        """
        self.driver = None
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.expanduser("~"), "AppData", "Local", "DouyinPublisher"
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
            print(f"[ChromeDriver] 使用打包驱动: {driver_folder_path}")
            return driver_folder_path

        # 检查当前目录
        driver_path = os.path.join(self.base_dir, driver_name)
        if os.path.exists(driver_path):
            print(f"[ChromeDriver] 使用本地驱动: {driver_path}")
            return driver_path

        # 都不存在，返回 None（将尝试使用系统 PATH）
        print("[ChromeDriver] 未找到本地驱动，尝试使用系统驱动")
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

        # 禁用 GPU 加速（避免某些环境下的问题）
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
                print("[抖音发布] 使用本地 ChromeDriver 初始化浏览器")
            else:
                print("[抖音发布] 尝试使用系统 ChromeDriver...")
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[抖音发布] 使用系统 ChromeDriver 初始化浏览器")

            # 设置隐式等待（较短，避免 find_element 卡太久）
            self.driver.implicitly_wait(2)

            # 修改 navigator.webdriver 标志
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            })

            print("[抖音发布] 浏览器初始化成功")
            return True
        except Exception as e:
            print(f"[抖音发布] 浏览器初始化失败: {e}")
            traceback.print_exc()
            return False

    # ------------------------------------------------------------
    #  步骤1：检查登录状态（快速检测）
    # ------------------------------------------------------------
    def check_login_status(self, timeout=3):
        """
        访问抖音创作者平台首页，快速判断是否需要扫码登录。
        判断逻辑：
        - URL 含 login / passport -> 登录页
        - 页面含"我是创作者"文字 -> 登录页
        - 找到 id="header-avatar" -> 已登录
        :return: (is_logged_in, message)
        """
        try:
            print("[抖音发布] == 步骤1：检查登录状态 ==")
            self.driver.get(DOUYIN_HOME_URL)
            time.sleep(2)

            current_url = self.driver.current_url
            print(f"[抖音发布] 当前页面 URL: {current_url}")

            # 判断1：URL 含 login / passport
            if "login" in current_url.lower() or "passport" in current_url.lower():
                print("[抖音发布] 检测到登录页(URL)，需要用户扫码")
                return False, "检测到抖音登录页面，请扫码登录"

            # 判断2：页面含"我是创作者"文字 -> 也是登录页/未登录态
            try:
                page_source = self.driver.page_source
                if "我是创作者" in page_source:
                    print("[抖音发布] 检测到页面含'我是创作者'，判定为登录页")
                    return False, "检测到抖音登录页面，请扫码登录"
            except Exception:
                pass

            # 判断3：快速查找 header-avatar
            try:
                avatar = self.driver.find_element(By.ID, "header-avatar")
                if avatar:
                    print("[抖音发布] 找到 header-avatar，已登录")
                    return True, "已登录"
            except NoSuchElementException:
                pass

            # 兜底：如果停留在创作者平台域名，视为已登录
            if "creator" in self.driver.current_url:
                print("[抖音发布] 停留在创作者平台，视为已登录")
                return True, "已登录"

            print("[抖音发布] 未检测到登录态")
            return False, "未登录，需要扫码登录"

        except Exception as e:
            print(f"[抖音发布] 检查登录状态失败: {e}")
            traceback.print_exc()
            return False, f"检查失败: {str(e)}"

    # ------------------------------------------------------------
    #  步骤2：等待用户扫码登录 - 持续监听 header-avatar
    # ------------------------------------------------------------
    def wait_for_login(self, timeout=300, step_callback=None):
        """
        在登录页面持续监听，直到检测到 id="header-avatar" 出现，
        表示用户扫码登录成功。
        登录成功后自动跳转到上传页面。
        :param timeout: 最长等待时间（秒）
        :param step_callback: 步骤回调
        :return: (success, message)
        """
        def _step(name, detail=""):
            print(f"[抖音发布] {name} {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            _step("请扫码登录", "请在浏览器中使用抖音 APP 扫描二维码完成登录")
            print("[抖音发布] == 步骤2：等待扫码登录 ==")
            print("[抖音发布] 持续监听页面变化，等待 header-avatar 出现...")

            # 临时把隐式等待降到最低，避免每次 find_element 卡 2 秒
            self.driver.implicitly_wait(0.3)

            start_time = time.time()
            check_count = 0
            while time.time() - start_time < timeout:
                check_count += 1

                # 方式1：检测页面是否出现 header-avatar（登录成功标志）
                try:
                    avatar = self.driver.find_element(By.ID, "header-avatar")
                    if avatar:
                        print("[抖音发布] [OK] 检测到 header-avatar，扫码登录成功!")
                        _step("扫码登录成功!", "正在跳转到视频上传页面...")
                        self.driver.implicitly_wait(2)  # 恢复
                        time.sleep(1)
                        print(f"[抖音发布] 自动跳转到上传页面: {DOUYIN_UPLOAD_URL}")
                        self.driver.get(DOUYIN_UPLOAD_URL)
                        time.sleep(3)
                        return True, "登录成功"
                except NoSuchElementException:
                    pass

                # 方式2：检测URL变化 + 页面不再含"我是创作者"
                current_url = self.driver.current_url
                is_still_login = ("login" in current_url.lower()
                                  or "passport" in current_url.lower())
                if not is_still_login:
                    # URL不是登录页了，检查页面内容
                    try:
                        page_src = self.driver.page_source
                        if "我是创作者" not in page_src:
                            # 页面不含"我是创作者"了，说明已登录
                            print("[抖音发布] [OK] 页面已变化(URL非登录页且无'我是创作者')，登录成功!")
                            _step("扫码登录成功!", "正在跳转到视频上传页面...")
                            self.driver.implicitly_wait(2)
                            self.driver.get(DOUYIN_UPLOAD_URL)
                            time.sleep(3)
                            return True, "登录成功"
                    except Exception:
                        pass

                # 每30秒打印一次提醒
                if check_count % 30 == 0:
                    elapsed = int(time.time() - start_time)
                    remaining = timeout - elapsed
                    _step("等待扫码登录...", f"已等待 {elapsed} 秒，剩余 {remaining} 秒")

                time.sleep(1)

            self.driver.implicitly_wait(2)  # 恢复
            return False, "登录超时(5分钟内未完成扫码)"

        except Exception as e:
            print(f"[抖音发布] 等待登录失败: {e}")
            traceback.print_exc()
            return False, f"等待登录失败: {str(e)}"

    # ------------------------------------------------------------
    #  步骤3：上传视频文件
    # ------------------------------------------------------------
    def _upload_video_file(self, video_path, update_progress):
        """
        在上传页面找到 file input 并发送视频文件路径。
        :return: (success, message)
        """
        print("[抖音发布] == 步骤3：上传视频文件 ==")
        update_progress(10, "查找上传入口...")

        try:
            upload_btn = None
            selectors = [
                "//input[@type='file']",
                "//button[contains(@class, 'container-drag-btn')]",
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        upload_btn = elements[0]
                        print(f"[抖音发布] 找到上传元素: {selector}")
                        break
                except Exception:
                    continue

            if not upload_btn:
                return False, "找不到上传按钮"

            # 如果是 input 元素，直接发送文件路径
            if upload_btn.tag_name == "input":
                update_progress(15, "正在上传视频文件...")
                upload_btn.send_keys(os.path.abspath(video_path))
            else:
                file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                update_progress(15, "正在上传视频文件...")
                file_input.send_keys(os.path.abspath(video_path))

            print(f"[抖音发布] 视频文件已发送: {video_path}")
            return True, "视频文件已发送"

        except Exception as e:
            return False, f"上传视频失败: {str(e)}"

    # ------------------------------------------------------------
    #  步骤4：等待视频上传完成
    # ------------------------------------------------------------
    def _wait_video_upload(self, update_progress, max_wait=300):
        """
        等待视频上传完成（检测上传状态变化）
        """
        print("[抖音发布] == 步骤4：等待视频上传完成 ==")
        update_progress(20, "等待视频上传完成...")
        time.sleep(5)  # 等待上传开始

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                uploading_elements = self.driver.find_elements(By.CLASS_NAME, "uploading-container-kBnKYA")
                completed_elements = self.driver.find_elements(By.CLASS_NAME, "phone-screen-iP9oLo")

                if completed_elements and not uploading_elements:
                    print("[抖音发布] [OK] 视频上传完成")
                    update_progress(40, "视频上传完成")
                    return True

                if uploading_elements:
                    elapsed = int(time.time() - start_time)
                    update_progress(20 + min(elapsed // 10, 15), f"视频上传中...已等待 {elapsed} 秒")

            except Exception as e:
                print(f"[抖音发布] 检查上传状态异常: {e}")

            time.sleep(2)

        print("[抖音发布] 警告：上传状态检测超时，继续执行...")
        return False

    # ------------------------------------------------------------
    #  步骤5：设置封面（竖封面 + 横封面）
    # ------------------------------------------------------------
    def _setup_cover(self, update_progress, step_callback=None):
        """
        设置封面流程：
        1. 点击 class="filter-k_CjvJ" 打开设置封面弹窗
        2. 检查封面弹窗 class="container-IaxQlJ" 是否出现
           - 若未出现，提示用户手动设置封面，等待用户操作后继续
        3. 检查 class="recommend-bubble-JPbArG" 是否存在，有则点击
        4. 点击<设置横封面>按钮
        5. 点击<完成>按钮
        """
        print("[抖音发布] == 步骤5：设置封面 ==")
        update_progress(45, "正在设置封面...")

        def _step(name, detail=""):
            print(f"[抖音发布] {name} {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            # -- 5.1 点击 filter-k_CjvJ 打开封面设置 --
            print("[抖音发布] 5.1 查找并点击封面设置按钮 (class=filter-k_CjvJ)...")
            try:
                cover_trigger = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "filter-k_CjvJ"))
                )
                # 使用 JS 点击，确保准确点击到目标元素
                self.driver.execute_script("arguments[0].click();", cover_trigger)
                print("[抖音发布] [OK] 已点击 filter-k_CjvJ，等待封面设置弹窗...")
            except TimeoutException:
                print("[抖音发布] [X] 未找到 filter-k_CjvJ，跳过封面设置")
                return

            # -- 5.2 检查封面弹窗 container-IaxQlJ 是否出现 --
            print("[抖音发布] 5.2 等待封面设置弹窗 (class=container-IaxQlJ)...")
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "container-IaxQlJ"))
                )
                print("[抖音发布] [OK] 封面设置弹窗已出现")
                time.sleep(1)
            except TimeoutException:
                print("[抖音发布] [X] 封面设置弹窗(container-IaxQlJ)未出现")
                _step("请手动设置封面", "未能自动打开封面设置弹窗，请手动设置封面后点击下一步")
                update_progress(50, "请手动设置封面，完成后流程将自动继续...")
                # 等待封面弹窗消失或用户完成操作（最多等120秒）
                for i in range(120):
                    time.sleep(1)
                    # 检查封面弹窗是否已被用户关闭（说明用户完成了手动操作）
                    dialogs = self.driver.find_elements(By.CLASS_NAME, "container-IaxQlJ")
                    if not dialogs:
                        # 弹窗不存在，检查是否回到了编辑页面
                        print(f"[抖音发布] 等待用户手动设置封面中... ({i+1}s)")
                        # 检查发布按钮是否可见，说明用户已经回到编辑页面
                        try:
                            publish_btns = self.driver.find_elements(
                                By.CSS_SELECTOR, "button.button-dhlUZE.primary-cECiOJ")
                            if publish_btns:
                                print("[抖音发布] [OK] 检测到编辑页面，用户已完成手动封面设置")
                                update_progress(60, "封面设置完成（用户手动）")
                                return
                        except Exception:
                            pass
                print("[抖音发布] 手动封面设置等待超时，继续后续流程")
                update_progress(60, "封面设置超时，继续下一步")
                return

            update_progress(50, "封面设置弹窗已打开...")

            # -- 5.3 检查并点击 recommend-bubble-JPbArG（选择推荐封面帧）--
            print("[抖音发布] 5.3 检查推荐气泡 (class=recommend-bubble-JPbArG)...")
            time.sleep(2)  # 等待气泡渲染
            
            # 调试：打印气泡元素信息
            try:
                bubbles = self.driver.find_elements(By.CLASS_NAME, "recommend-bubble-JPbArG")
                print(f"[抖音发布] 找到 {len(bubbles)} 个推荐气泡")
                for i, b in enumerate(bubbles):
                    rect = b.rect
                    print(f"[抖音发布]   气泡[{i}]: x={rect['x']}, y={rect['y']}, width={rect['width']}, height={rect['height']}")
            except Exception as e:
                print(f"[抖音发布] 获取气泡信息失败: {e}")
            
            try:
                bubbles = self.driver.find_elements(By.CLASS_NAME, "recommend-bubble-JPbArG")
                if bubbles:
                    print(f"[抖音发布] 发现 {len(bubbles)} 个推荐气泡，尝试点击...")
                    bubble = bubbles[0]
                    clicked = False
                    
                    # 获取气泡的位置信息
                    bubble_rect = bubble.rect
                    bubble_x = bubble_rect['x']
                    bubble_y = bubble_rect['y']
                    bubble_width = bubble_rect['width']
                    bubble_height = bubble_rect['height']
                    print(f"[抖音发布] 气泡位置: x={bubble_x}, y={bubble_y}, width={bubble_width}, height={bubble_height}")
                    
                    # 方式1：使用 JavaScript 直接点击气泡元素的中心位置
                    try:
                        self.driver.execute_script("""
                            var bubble = arguments[0];
                            var rect = bubble.getBoundingClientRect();
                            var centerX = rect.left + rect.width / 2;
                            var centerY = rect.top + rect.height / 2;
                            console.log('Clicking bubble at:', centerX, centerY);
                            
                            // 创建并触发点击事件
                            var clickEvent = new MouseEvent('click', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: centerX,
                                clientY: centerY
                            });
                            bubble.dispatchEvent(clickEvent);
                        """, bubble)
                        clicked = True
                        print(f"[抖音发布] [OK] 使用 JS dispatchEvent 点击气泡成功")
                    except Exception as e1:
                        print(f"[抖音发布] JS dispatchEvent 点击失败: {e1}")
                    
                    # 方式2：使用 ActionChains 直接移动到气泡中心点击
                    if not clicked:
                        try:
                            actions = ActionChains(self.driver)
                            actions.move_to_element(bubble).click().perform()
                            clicked = True
                            print(f"[抖音发布] [OK] 使用 ActionChains move_to_element 点击成功")
                        except Exception as e2:
                            print(f"[抖音发布] ActionChains 点击失败: {e2}")
                    
                    # 方式3：计算气泡相对于 slider 容器的偏移量并点击
                    if not clicked:
                        try:
                            slider_container = self.driver.find_element(By.CLASS_NAME, "container-AGl0YW")
                            if slider_container:
                                container_rect = slider_container.rect
                                # 计算气泡中心相对于容器左上角的偏移
                                offset_x = int(bubble_x - container_rect['x'] + bubble_width / 2)
                                offset_y = int(bubble_y - container_rect['y'] + bubble_height / 2)
                                print(f"[抖音发布] 计算偏移量: offset_x={offset_x}, offset_y={offset_y}")
                                
                                actions = ActionChains(self.driver)
                                actions.move_to_element_with_offset(slider_container, offset_x, offset_y).click().perform()
                                clicked = True
                                print(f"[抖音发布] [OK] 使用计算偏移量点击成功")
                        except Exception as e3:
                            print(f"[抖音发布] 偏移量点击失败: {e3}")
                    
                    # 方式2：直接点击 preview-frames 区域对应位置的帧
                    if not clicked:
                        try:
                            preview_frames = self.driver.find_elements(By.CLASS_NAME, "preview-frame-rt7Mc1")
                            if preview_frames and len(preview_frames) > 2:
                                # 点击第3个预览帧（通常是推荐位置之一）
                                self.driver.execute_script("arguments[0].click();", preview_frames[2])
                                clicked = True
                                print("[抖音发布] [OK] 点击预览帧成功")
                        except Exception as e2:
                            print(f"[抖音发布] 点击预览帧失败: {e2}")
                    
                    # 方式3：使用 JavaScript 直接移动 slider
                    if not clicked:
                        try:
                            # 获取气泡的 left 值，然后设置 slider 的位置
                            self.driver.execute_script("""
                                var bubble = arguments[0];
                                var slider = document.querySelector('.slider-Tiqx_t');
                                if (slider && bubble) {
                                    var bubbleLeft = bubble.style.left;
                                    slider.style.left = bubbleLeft;
                                    // 触发 slider 的 mousedown/mouseup 事件来选中该帧
                                    var rect = slider.getBoundingClientRect();
                                    var evt = new MouseEvent('mousedown', {
                                        bubbles: true, cancelable: true, view: window,
                                        clientX: rect.left + rect.width/2,
                                        clientY: rect.top + rect.height/2
                                    });
                                    slider.dispatchEvent(evt);
                                    var evtUp = new MouseEvent('mouseup', {
                                        bubbles: true, cancelable: true, view: window,
                                        clientX: rect.left + rect.width/2,
                                        clientY: rect.top + rect.height/2
                                    });
                                    slider.dispatchEvent(evtUp);
                                }
                            """, bubble)
                            clicked = True
                            print("[抖音发布] [OK] 使用 JS 移动 slider 成功")
                        except Exception as e3:
                            print(f"[抖音发布] JS 移动 slider 失败: {e3}")
                    
                    # 方式4：点击推荐气泡预览图（recommend-bubble-preview-kAHq91）
                    if not clicked:
                        try:
                            previews = self.driver.find_elements(By.CLASS_NAME, "recommend-bubble-preview-kAHq91")
                            if previews:
                                # 点击预览图，它比气泡大更容易点中
                                self.driver.execute_script("""
                                    arguments[0].scrollIntoView({block: 'center'});
                                """, previews[0])
                                time.sleep(0.2)
                                actions = ActionChains(self.driver)
                                actions.move_to_element(previews[0]).click().perform()
                                clicked = True
                                print("[抖音发布] [OK] 点击推荐气泡预览图成功")
                        except Exception as e4:
                            print(f"[抖音发布] 点击预览图失败: {e4}")
                    
                    # 方式5：使用坐标直接点击
                    if not clicked:
                        try:
                            # 获取气泡在页面上的绝对坐标
                            location = bubble.location
                            size = bubble.size
                            # 用 pyautogui 或者 ActionChains 点击坐标
                            actions = ActionChains(self.driver)
                            actions.move_to_element(bubble).perform()
                            time.sleep(0.1)
                            actions.click().perform()
                            clicked = True
                            print("[抖音发布] [OK] 使用 move_to_element + click 成功")
                        except Exception as e5:
                            print(f"[抖音发布] 坐标点击失败: {e5}")
                    
                    if clicked:
                        time.sleep(1)
                    else:
                        print("[抖音发布] 所有点击方式均失败，继续下一步")
                else:
                    print("[抖音发布] 未发现推荐气泡，跳过")
            except Exception as e:
                print(f"[抖音发布] 推荐气泡处理异常（不影响流程）: {e}")

            # -- 5.4 点击<设置横封面>按钮 --
            print("[抖音发布] 5.4 查找并点击<设置横封面>按钮...")
            try:
                set_horizontal_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(@class, 'primary-RstHX_')]//span[contains(text(), '设置横封面')]/parent::button"
                    ))
                )
                set_horizontal_btn.click()
                print("[抖音发布] [OK] 已点击<设置横封面>按钮")
                time.sleep(2)
            except TimeoutException:
                print("[抖音发布] [X] 未找到<设置横封面>按钮，尝试备用方式...")
                try:
                    buttons = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "button.semi-button.semi-button-primary.semi-button-light.primary-RstHX_"
                    )
                    for btn in buttons:
                        if "设置横封面" in btn.text:
                            btn.click()
                            print("[抖音发布] [OK] 备用方式点击<设置横封面>成功")
                            time.sleep(2)
                            break
                except Exception as e2:
                    print(f"[抖音发布] 备用方式也失败: {e2}")

            update_progress(55, "正在完成封面设置...")

            # -- 5.5 点击<完成>按钮 --
            print("[抖音发布] 5.5 查找并点击<完成>按钮...")
            try:
                complete_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(@class, 'primary-RstHX_')]//span[contains(text(), '完成')]/parent::button"
                    ))
                )
                complete_btn.click()
                print("[抖音发布] [OK] 已点击<完成>按钮")
                time.sleep(2)
            except TimeoutException:
                print("[抖音发布] [X] 未找到<完成>按钮，尝试备用方式...")
                try:
                    buttons = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "button.semi-button.semi-button-primary.semi-button-light.primary-RstHX_"
                    )
                    for btn in buttons:
                        if "完成" in btn.text:
                            btn.click()
                            print("[抖音发布] [OK] 备用方式点击<完成>成功")
                            time.sleep(2)
                            break
                except Exception as e2:
                    print(f"[抖音发布] 备用方式也失败: {e2}")

            update_progress(60, "封面设置完成")
            print("[抖音发布] [OK] 封面设置流程结束")

        except Exception as e:
            print(f"[抖音发布] 设置封面失败（可能不影响发布）: {e}")
            traceback.print_exc()

    # ------------------------------------------------------------
    #  步骤6：填写标题
    # ------------------------------------------------------------
    def _fill_title(self, title, update_progress):
        """
        在标题输入框 <input class="semi-input" placeholder="填写作品标题..."> 中输入标题
        """
        print("[抖音发布] == 步骤6：填写标题 ==")
        update_progress(65, "正在填写标题...")

        try:
            title_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "input.semi-input[placeholder*='填写作品标题']"
                ))
            )
            title_input.click()
            time.sleep(0.3)
            title_input.clear()
            time.sleep(0.2)

            # 使用 JS 设值并触发 input 事件，确保 React/Vue 等框架能捕获
            safe_title = title[:30]  # 限制30字
            self.driver.execute_script("""
                var el = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, arguments[1]);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, title_input, safe_title)

            print(f"[抖音发布] [OK] 标题已填写: {safe_title}")
            update_progress(70, f"标题已填写: {safe_title}")
            return True

        except TimeoutException:
            print("[抖音发布] [X] 未找到标题输入框 (input.semi-input)")
            # 尝试备用选择器
            try:
                title_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[placeholder*='标题']")
                title_input.click()
                title_input.clear()
                title_input.send_keys(title[:30])
                print(f"[抖音发布] [OK] 备用方式填写标题成功")
                return True
            except Exception:
                print("[抖音发布] [X] 备用方式也失败")
                return False
        except Exception as e:
            print(f"[抖音发布] 填写标题失败: {e}")
            return False

    # ------------------------------------------------------------
    #  步骤7：填写作品简介（话题）
    # ------------------------------------------------------------
    def _fill_description(self, topics, update_progress):
        """
        将话题输入到作品简介的 contenteditable div 中
        （data-placeholder="添加作品简介"）
        """
        if not topics:
            print("[抖音发布] 无话题需要填写，跳过")
            return True

        print("[抖音发布] == 步骤7：填写作品简介（话题） ==")
        update_progress(72, "正在填写作品简介...")

        try:
            # 查找作品简介的 contenteditable 编辑器
            desc_editor = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div[data-placeholder='添加作品简介'][contenteditable='true']"
                ))
            )
            desc_editor.click()
            time.sleep(0.5)

            # 构建话题文本（用于日志显示）
            topics_text = " ".join([f"#{t.strip().lstrip('#')}" for t in topics if t.strip()])

            # 使用键盘逐个输入话题（兼容性更好，能触发抖音的话题联想）
            for topic in topics:
                topic = topic.strip().lstrip('#')  # 去掉话题前已有的 # 号，避免重复
                if not topic:
                    continue

                # 先输入 # 号触发话题联想
                actions = ActionChains(self.driver)
                actions.send_keys("#")
                actions.perform()
                time.sleep(0.5)

                # 再输入话题文字
                actions = ActionChains(self.driver)
                actions.send_keys(topic)
                actions.perform()
                time.sleep(1.5)  # 等待话题联想弹出

                # 尝试选择话题联想
                try:
                    suggestions = self.driver.find_elements(
                        By.CSS_SELECTOR, "div[class*='mention-list'] div[class*='mention-item']")
                    if suggestions:
                        suggestions[0].click()
                        print(f"[抖音发布] [OK] 选中话题联想: #{topic}")
                        time.sleep(0.5)
                    else:
                        # 没有联想，按空格结束当前话题
                        actions = ActionChains(self.driver)
                        actions.send_keys(" ")
                        actions.perform()
                        print(f"[抖音发布] 无联想，直接输入话题: #{topic}")
                except Exception:
                    actions = ActionChains(self.driver)
                    actions.send_keys(" ")
                    actions.perform()

            print(f"[抖音发布] [OK] 话题已填写: {topics}")
            update_progress(78, f"话题已填写: {topics_text}")
            return True

        except TimeoutException:
            print("[抖音发布] [X] 未找到作品简介编辑器")
            # 备用：尝试用其他选择器
            try:
                editors = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[contenteditable='true'][data-slate-editor='true']")
                if len(editors) >= 1:
                    # 通常第一个是标题编辑器（如果有），最后一个是简介
                    editor = editors[-1]
                    editor.click()
                    time.sleep(0.3)
                    topics_text = " ".join([f"#{t.strip()}" for t in topics if t.strip()])
                    self.driver.execute_script(
                        "arguments[0].innerText = arguments[1];",
                        editor, topics_text)
                    print(f"[抖音发布] [OK] 备用方式填写话题成功")
                    return True
            except Exception:
                pass
            return False
        except Exception as e:
            print(f"[抖音发布] 填写作品简介失败: {e}")
            return False

    # ------------------------------------------------------------
    #  步骤8：点击发布按钮
    # ------------------------------------------------------------
    def _click_publish(self, update_progress):
        """
        点击发布按钮 <button class="button-dhlUZE primary-cECiOJ ...">发布</button>
        """
        print("[抖音发布] == 步骤8：点击发布 ==")
        update_progress(85, "正在发布视频...")

        try:
            # 优先精确匹配
            publish_btn = None
            try:
                publish_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((
                        By.CSS_SELECTOR,
                        "button.button-dhlUZE.primary-cECiOJ"
                    ))
                )
            except TimeoutException:
                pass

            # 备用方式
            if not publish_btn:
                selectors = [
                    "//button[contains(@class, 'button-dhlUZE') and contains(@class, 'primary-cECiOJ')]",
                    "//button[contains(@class, 'primary-cECiOJ')]",
                    "//button[contains(text(), '发布')]",
                ]
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            publish_btn = elements[0]
                            break
                    except Exception:
                        continue

            if not publish_btn:
                return False, "找不到发布按钮"

            # 滚动到按钮可见位置
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior:'smooth',block:'center'});",
                publish_btn)
            time.sleep(0.5)

            publish_btn.click()
            print("[抖音发布] [OK] 已点击发布按钮")
            time.sleep(3)

            update_progress(100, "发布成功！")
            return True, "视频已成功发布到抖音"

        except Exception as e:
            return False, f"点击发布按钮失败: {str(e)}"

    # ------------------------------------------------------------
    #  upload_video - 完整的上传 + 填写 + 发布
    # ------------------------------------------------------------
    def upload_video(self, video_path, title, topics=None, progress_callback=None, step_callback=None):
        """
        上传视频并发布（主流程入口）
        :param video_path: 视频文件路径
        :param title: 视频标题
        :param topics: 话题列表，如 ["美食", "探店"]
        :param progress_callback: 进度回调函数 callback(percent, message)
        :param step_callback: 步骤回调 callback(step_name, step_detail)
        :return: (success, message)
        """
        try:
            if not os.path.exists(video_path):
                return False, f"视频文件不存在: {video_path}"

            if not title or not title.strip():
                return False, "标题不能为空，请填写视频标题后再发布"

            def update_progress(pct, msg):
                print(f"[抖音发布] [{pct}%] {msg}")
                if progress_callback:
                    progress_callback(pct, msg)

            update_progress(0, "开始上传流程...")

            # 步骤3：上传视频文件
            ok, msg = self._upload_video_file(video_path, update_progress)
            if not ok:
                return False, msg

            # 步骤4：等待视频上传完成
            self._wait_video_upload(update_progress)
            time.sleep(2)

            # 步骤5：设置封面（竖封面 + 横封面）
            self._setup_cover(update_progress, step_callback=step_callback)

            # 步骤6：填写标题（必须成功才能发布）
            title_ok = self._fill_title(title, update_progress)
            if not title_ok:
                return False, "填写标题失败，无法发布。请确保标题不为空"

            # 步骤7：填写作品简介（话题）
            self._fill_description(topics, update_progress)

            # 步骤8：点击发布
            return self._click_publish(update_progress)

        except Exception as e:
            print(f"[抖音发布] 上传失败: {e}")
            traceback.print_exc()
            return False, f"上传失败: {str(e)}"

    # ------------------------------------------------------------
    #  publish - 完整发布流程（含登录检查）
    # ------------------------------------------------------------
    def publish(self, video_path, title, topics=None, progress_callback=None, step_callback=None):
        """
        完整的发布流程（包含登录检查），带有详细步骤提示：

        流程总览：
        +-----------------------------------------------+
        | 步骤1  启动浏览器，打开抖音创作者平台          |
        | 步骤2  检测登录状态                            |
        |   |- 已登录 -> 跳转上传页面                     |
        |   +- 未登录 -> 提示扫码，监听 header-avatar     |
        |        +- 扫码成功 -> 自动跳转上传页面          |
        | 步骤3  上传视频文件                            |
        | 步骤4  等待视频上传完成                        |
        | 步骤5  设置封面                                |
        |   |- 点击 filter-k_CjvJ 打开弹窗              |
        |   |- 检查 container-IaxQlJ 弹窗是否出现        |
        |   |- 点击 recommend-bubble-JPbArG（如果有）     |
        |   |- 点击<设置横封面>                        |
        |   +- 点击<完成>                              |
        | 步骤6  填写标题                                |
        | 步骤7  填写作品简介（话题）                    |
        | 步骤8  点击发布                                |
        +-----------------------------------------------+

        :param video_path: 视频文件路径
        :param title: 视频标题
        :param topics: 话题列表
        :param progress_callback: 进度回调 callback(percent, message)
        :param step_callback: 步骤回调 callback(step_name, step_detail)，用于前端显示
        :return: (success, message)
        """
        def _step(name, detail=""):
            print(f"[抖音发布] [{name}] {detail}")
            if step_callback:
                step_callback(name, detail)

        try:
            # -- 步骤1：启动浏览器 --
            _step("步骤1：启动浏览器", "正在初始化 Chrome 驱动...")
            if not self._init_driver():
                return False, "浏览器初始化失败，请确保已安装 Chrome 浏览器"
            _step("步骤1：浏览器启动成功", "Chrome 已就绪")

            # -- 步骤2：检查登录状态 --
            _step("步骤2：检查登录状态", "正在访问抖音创作者平台...")
            is_logged_in, msg = self.check_login_status()

            if not is_logged_in:
                # 需要扫码登录
                _step("步骤2：需要扫码登录", "检测到抖音登录页面，请使用抖音 APP 扫描屏幕上的二维码")
                success, msg = self.wait_for_login(step_callback=step_callback)
                if not success:
                    return False, msg
                _step("步骤2：登录成功 [OK]", "已成功登录抖音创作者平台，即将开始上传")
            else:
                _step("步骤2：已登录 [OK]", "检测到已登录状态，即将跳转上传页面")
                # 已登录 -> 直接跳转到上传页面
                self.driver.get(DOUYIN_UPLOAD_URL)
                time.sleep(3)

            # -- 步骤3~8：上传视频 + 填写信息 + 发布 --
            _step("步骤3：开始上传视频", "请勿操作浏览器窗口")
            return self.upload_video(video_path, title, topics, progress_callback, step_callback)

        except Exception as e:
            print(f"[抖音发布] 发布流程失败: {e}")
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
                print("[抖音发布] 浏览器已关闭")
            except Exception:
                pass
            self.driver = None


# ==============================================================
#  测试代码
# ==============================================================
if __name__ == "__main__":
    publisher = DouyinPublisher()

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
