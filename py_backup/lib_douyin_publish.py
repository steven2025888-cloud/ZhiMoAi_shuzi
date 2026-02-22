# -*- coding: utf-8 -*-
# lib_douyin_publish.py — 抖音自动发布模块

import os
import sys
import time
import traceback
import requests
import zipfile
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

DOUYIN_UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"
DOUYIN_HOME_URL = "https://creator.douyin.com/"

# ChromeDriver 下载地址
CHROMEDRIVER_BASE_URL = "https://chromedriver.storage.googleapis.com"
CHROMEDRIVER_LATEST_URL = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"


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
    """抖音自动发布工具"""
    
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
            # 获取 ChromeDriver 路径
            driver_path = self._get_chromedriver_path()
            
            if driver_path:
                # 使用本地 ChromeDriver
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("[抖音发布] 使用本地 ChromeDriver 初始化浏览器")
            else:
                # 尝试使用系统 PATH 中的驱动
                print("[抖音发布] 尝试使用系统 ChromeDriver...")
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[抖音发布] 使用系统 ChromeDriver 初始化浏览器")
            
            # 设置隐式等待
            self.driver.implicitly_wait(10)
            
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
    
    def check_login_status(self, timeout=5):
        """
        检查登录状态
        :param timeout: 等待跳转的超时时间（秒）
        :return: (is_logged_in, message)
        """
        try:
            print("[抖音发布] 检查登录状态...")
            
            # 访问上传页面
            self.driver.get(DOUYIN_UPLOAD_URL)
            time.sleep(2)
            
            # 记录初始 URL
            initial_url = self.driver.current_url
            print(f"[抖音发布] 初始 URL: {initial_url}")
            
            # 等待指定时间，看是否发生跳转
            start_time = time.time()
            while time.time() - start_time < timeout:
                current_url = self.driver.current_url
                
                # 如果跳转到登录页面，说明未登录
                if "login" in current_url.lower() or "passport" in current_url.lower():
                    print("[抖音发布] 检测到跳转到登录页面，未登录")
                    return False, "未登录，需要扫码登录"
                
                # 如果 URL 包含 upload，说明已登录
                if "upload" in current_url:
                    print("[抖音发布] 已登录，停留在上传页面")
                    return True, "已登录"
                
                time.sleep(0.5)
            
            # 超时后检查最终 URL
            final_url = self.driver.current_url
            if "upload" in final_url:
                print("[抖音发布] 已登录")
                return True, "已登录"
            else:
                print(f"[抖音发布] 未登录，当前 URL: {final_url}")
                return False, "未登录"
                
        except Exception as e:
            print(f"[抖音发布] 检查登录状态失败: {e}")
            traceback.print_exc()
            return False, f"检查失败: {str(e)}"
    
    def wait_for_login(self, timeout=300):
        """
        等待用户登录
        :param timeout: 最长等待时间（秒）
        :return: (success, message)
        """
        try:
            print("[抖音发布] 等待用户登录...")
            print("[抖音发布] 请在浏览器中扫码登录抖音创作者平台")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                current_url = self.driver.current_url
                
                # 如果跳转到上传页面或创作者首页，说明登录成功
                if "upload" in current_url or "creator-micro/home" in current_url:
                    print("[抖音发布] 登录成功！")
                    # 跳转到上传页面
                    if "upload" not in current_url:
                        self.driver.get(DOUYIN_UPLOAD_URL)
                        time.sleep(2)
                    return True, "登录成功"
                
                time.sleep(1)
            
            return False, "登录超时"
            
        except Exception as e:
            print(f"[抖音发布] 等待登录失败: {e}")
            traceback.print_exc()
            return False, f"等待登录失败: {str(e)}"
    
    def upload_video(self, video_path, title, topics=None, progress_callback=None):
        """
        上传视频并发布
        :param video_path: 视频文件路径
        :param title: 视频标题
        :param topics: 话题列表，如 ["美食", "探店"]
        :param progress_callback: 进度回调函数 callback(percent, message)
        :return: (success, message)
        """
        try:
            if not os.path.exists(video_path):
                return False, f"视频文件不存在: {video_path}"
            
            def update_progress(pct, msg):
                print(f"[抖音发布] [{pct}%] {msg}")
                if progress_callback:
                    progress_callback(pct, msg)
            
            update_progress(0, "开始上传流程...")
            
            # 1. 点击上传按钮
            update_progress(10, "查找上传按钮...")
            try:
                # 尝试多种选择器
                upload_btn = None
                selectors = [
                    "//button[contains(@class, 'semi-button-primary') and contains(@class, 'container-drag-btn')]",
                    "//button[contains(@class, 'container-drag-btn')]",
                    "//input[@type='file']",
                ]
                
                for selector in selectors:
                    try:
                        if selector.startswith("//"):
                            elements = self.driver.find_elements(By.XPATH, selector)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        if elements:
                            upload_btn = elements[0]
                            print(f"[抖音发布] 找到上传元素: {selector}")
                            break
                    except:
                        continue
                
                if not upload_btn:
                    return False, "找不到上传按钮"
                
                # 如果是 input 元素，直接发送文件路径
                if upload_btn.tag_name == "input":
                    update_progress(20, "上传视频文件...")
                    upload_btn.send_keys(os.path.abspath(video_path))
                else:
                    # 如果是按钮，查找关联的 input
                    file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    update_progress(20, "上传视频文件...")
                    file_input.send_keys(os.path.abspath(video_path))
                
            except Exception as e:
                return False, f"上传视频失败: {str(e)}"
            
            # 2. 等待视频上传完成
            update_progress(30, "等待视频上传...")
            time.sleep(5)  # 等待上传开始
            
            # 等待上传完成（检测上传状态变化）
            max_wait = 300  # 最多等待5分钟
            start_time = time.time()
            upload_completed = False
            
            while time.time() - start_time < max_wait:
                try:
                    # 检查是否还在上传中
                    uploading_elements = self.driver.find_elements(By.CLASS_NAME, "uploading-container-kBnKYA")
                    
                    # 检查是否上传完成（出现手机预览界面）
                    completed_elements = self.driver.find_elements(By.CLASS_NAME, "phone-screen-iP9oLo")
                    
                    if completed_elements and not uploading_elements:
                        print("[抖音发布] 视频上传完成")
                        upload_completed = True
                        break
                    
                    # 显示进度
                    if uploading_elements:
                        print("[抖音发布] 视频上传中...")
                    
                except Exception as e:
                    print(f"[抖音发布] 检查上传状态异常: {e}")
                
                time.sleep(2)
            
            if not upload_completed:
                print("[抖音发布] 警告：上传状态检测超时，继续执行...")
            
            update_progress(50, "视频上传完成，填写信息...")
            time.sleep(2)
            
            # 3. 填写标题
            update_progress(55, "填写标题...")
            try:
                # 查找标题输入框
                title_selectors = [
                    "//div[contains(@class, 'notranslate')][@contenteditable='true']",
                    "//div[@contenteditable='true']",
                    "//textarea[@placeholder='填写作品标题']",
                ]
                
                title_input = None
                for selector in title_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            title_input = elements[0]
                            break
                    except:
                        continue
                
                if title_input:
                    # 清空并输入标题
                    title_input.click()
                    time.sleep(0.5)
                    title_input.clear()
                    
                    # 使用 JavaScript 设置内容（更可靠）
                    self.driver.execute_script(
                        "arguments[0].innerText = arguments[1];", 
                        title_input, 
                        title[:30]  # 限制30字
                    )
                    print(f"[抖音发布] 标题已填写: {title[:30]}")
                else:
                    print("[抖音发布] 警告：未找到标题输入框")
                    
            except Exception as e:
                print(f"[抖音发布] 填写标题失败: {e}")
            
            # 4. 添加话题（如果提供）
            if topics:
                update_progress(60, "添加话题...")
                try:
                    for topic in topics[:3]:  # 最多3个话题
                        # 在标题后添加话题
                        topic_text = f" #{topic}"
                        self.driver.execute_script(
                            "arguments[0].innerText += arguments[1];",
                            title_input,
                            topic_text
                        )
                        time.sleep(0.5)
                    print(f"[抖音发布] 话题已添加: {topics}")
                except Exception as e:
                    print(f"[抖音发布] 添加话题失败: {e}")
            
            # 5. 设置封面
            update_progress(70, "设置封面...")
            try:
                # 点击封面设置按钮
                cover_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "coverControl-CjlzqC"))
                )
                cover_btn.click()
                print("[抖音发布] 已点击封面设置按钮")
                time.sleep(1)
                
                # 等待并点击第一个"设置封面"按钮
                first_set_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 
                        "button.semi-button.semi-button-primary.semi-button-light.primary-RstHX_"))
                )
                first_set_btn.click()
                print("[抖音发布] 已点击第一个设置封面按钮")
                
                # 等待并点击第二个"完成"按钮（等待它出现）
                second_complete_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 
                        "button.semi-button.semi-button-primary.semi-button-light.primary-RstHX_"))
                )
                second_complete_btn.click()
                print("[抖音发布] 已点击完成按钮")
                time.sleep(1)
                
                print("[抖音发布] 封面已设置")
                    
            except Exception as e:
                print(f"[抖音发布] 设置封面失败（可能不影响发布）: {e}")
            
            # 6. 点击发布按钮
            update_progress(90, "发布视频...")
            try:
                # 查找发布按钮
                publish_selectors = [
                    "//button[contains(@class, 'button-dhlUZE') and contains(@class, 'primary-cECiOJ')]",
                    "//button[contains(@class, 'primary-cECiOJ')]",
                    "//button[contains(text(), '发布')]",
                ]
                
                publish_btn = None
                for selector in publish_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            publish_btn = elements[0]
                            break
                    except:
                        continue
                
                if not publish_btn:
                    return False, "找不到发布按钮"
                
                # 点击发布
                publish_btn.click()
                print("[抖音发布] 已点击发布按钮")
                time.sleep(3)
                
                update_progress(100, "发布成功！")
                return True, "视频已成功发布到抖音"
                
            except Exception as e:
                return False, f"点击发布按钮失败: {str(e)}"
            
        except Exception as e:
            print(f"[抖音发布] 上传失败: {e}")
            traceback.print_exc()
            return False, f"上传失败: {str(e)}"
    
    def publish(self, video_path, title, topics=None, progress_callback=None):
        """
        完整的发布流程（包含登录检查）
        :param video_path: 视频文件路径
        :param title: 视频标题
        :param topics: 话题列表
        :param progress_callback: 进度回调
        :return: (success, message)
        """
        try:
            # 初始化浏览器
            if not self._init_driver():
                return False, "浏览器初始化失败"
            
            # 检查登录状态
            is_logged_in, msg = self.check_login_status()
            
            if not is_logged_in:
                # 等待用户登录
                success, msg = self.wait_for_login()
                if not success:
                    return False, msg
            
            # 上传视频
            return self.upload_video(video_path, title, topics, progress_callback)
            
        except Exception as e:
            print(f"[抖音发布] 发布流程失败: {e}")
            traceback.print_exc()
            return False, f"发布失败: {str(e)}"
        finally:
            # 不关闭浏览器，保持登录状态
            pass
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                print("[抖音发布] 浏览器已关闭")
            except:
                pass
            self.driver = None


# 测试代码
if __name__ == "__main__":
    publisher = DouyinPublisher()
    
    # 测试视频路径
    test_video = r"D:\test_video.mp4"
    test_title = "这是一个测试视频标题，用于测试自动发布功能"
    test_topics = ["测试", "自动化"]
    
    def progress(pct, msg):
        print(f"进度: {pct}% - {msg}")
    
    success, message = publisher.publish(
        test_video,
        test_title,
        test_topics,
        progress_callback=progress
    )
    
    print(f"结果: {message}")
    
    # 等待用户查看结果
    input("按回车键关闭浏览器...")
    publisher.close()
