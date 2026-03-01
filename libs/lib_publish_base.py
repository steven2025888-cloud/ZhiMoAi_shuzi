# -*- coding: utf-8 -*-
"""
lib_publish_base.py - 社交平台自动发布基类

提供各平台发布器的公共功能：
- Chrome浏览器驱动管理
- 通用的初始化和关闭逻辑
- 统一的日志和回调处理
"""

import os
import platform
import time
import traceback
from abc import ABC, abstractmethod
from typing import Callable, Optional, Tuple, List

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


class PublishBase(ABC):
    """社交平台自动发布基类"""
    
    # 子类需要重写的属性
    PLATFORM_NAME: str = "未知平台"
    DEFAULT_USER_DATA_DIR_NAME: str = "PublisherData"
    WINDOW_SIZE: Tuple[int, int] = (1280, 800)
    
    def __init__(self, user_data_dir: Optional[str] = None):
        """
        初始化发布器
        
        Args:
            user_data_dir: Chrome用户数据目录，用于保持登录状态
        """
        self.driver: Optional[webdriver.Chrome] = None
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.expanduser("~"), "AppData", "Local", self.DEFAULT_USER_DATA_DIR_NAME
        )
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """
        统一日志输出
        
        Args:
            message: 日志内容
            level: 日志级别
        """
        print(f"[{self.PLATFORM_NAME}发布] {message}")
    
    def _step_callback(
        self, 
        step_callback: Optional[Callable[[str, str], None]], 
        name: str, 
        detail: str = ""
    ) -> None:
        """
        执行步骤回调
        
        Args:
            step_callback: 步骤回调函数
            name: 步骤名称
            detail: 步骤详情
        """
        self._log(f"{name} {detail}")
        if step_callback:
            step_callback(name, detail)
    
    def _progress_callback(
        self,
        progress_callback: Optional[Callable[[int, str], None]],
        percent: int,
        message: str
    ) -> None:
        """
        执行进度回调
        
        Args:
            progress_callback: 进度回调函数
            percent: 进度百分比
            message: 进度消息
        """
        self._log(f"[{percent}%] {message}")
        if progress_callback:
            progress_callback(percent, message)
    
    def _get_chromedriver_path(self) -> Optional[str]:
        """
        获取 ChromeDriver 路径
        
        Returns:
            ChromeDriver路径，如果未找到返回None
        """
        driver_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
        
        # 优先检查 chromedriver 文件夹
        driver_folder_path = os.path.join(self.base_dir, "chromedriver", driver_name)
        if os.path.exists(driver_folder_path):
            self._log(f"使用打包驱动: {driver_folder_path}")
            return driver_folder_path
        
        # 检查当前目录
        driver_path = os.path.join(self.base_dir, driver_name)
        if os.path.exists(driver_path):
            self._log(f"使用本地驱动: {driver_path}")
            return driver_path
        
        self._log("未找到本地驱动，尝试使用系统驱动")
        return None
    
    def _create_chrome_options(self) -> Options:
        """
        创建Chrome选项
        
        Returns:
            配置好的Chrome选项
        """
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
        width, height = self.WINDOW_SIZE
        chrome_options.add_argument(f"--window-size={width},{height}")
        
        # 禁用通知
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "download.default_directory": os.path.expanduser("~\\Downloads"),
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        return chrome_options
    
    def _init_driver(self) -> bool:
        """
        初始化浏览器驱动
        
        Returns:
            初始化是否成功
        """
        if self.driver:
            return True
        
        try:
            chrome_options = self._create_chrome_options()
            driver_path = self._get_chromedriver_path()
            
            if driver_path:
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self._log("使用本地 ChromeDriver 初始化浏览器")
            else:
                self._log("尝试使用系统 ChromeDriver...")
                self.driver = webdriver.Chrome(options=chrome_options)
                self._log("使用系统 ChromeDriver 初始化浏览器")
            
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
            
            self._log("浏览器初始化成功")
            return True
            
        except Exception as e:
            self._log(f"浏览器初始化失败: {e}")
            traceback.print_exc()
            return False
    
    def _wait_for_login_generic(
        self,
        check_logged_in: Callable[[], bool],
        redirect_url: str,
        timeout: int = 300,
        step_callback: Optional[Callable[[str, str], None]] = None,
        login_prompt: str = "请登录"
    ) -> Tuple[bool, str]:
        """
        通用的等待登录逻辑
        
        Args:
            check_logged_in: 检查是否已登录的函数
            redirect_url: 登录成功后跳转的URL
            timeout: 超时时间（秒）
            step_callback: 步骤回调函数
            login_prompt: 登录提示文字
            
        Returns:
            (是否成功, 消息)
        """
        self._step_callback(step_callback, login_prompt, "请在浏览器中完成登录")
        self._log("== 等待用户登录 ==")
        
        try:
            start_time = time.time()
            check_count = 0
            
            while time.time() - start_time < timeout:
                check_count += 1
                
                if check_logged_in():
                    self._log("[OK] 登录成功!")
                    self._step_callback(step_callback, "登录成功!", "正在跳转...")
                    time.sleep(1)
                    self.driver.get(redirect_url)
                    time.sleep(3)
                    return True, "登录成功"
                
                # 每30秒打印一次提醒
                if check_count % 30 == 0:
                    elapsed = int(time.time() - start_time)
                    remaining = timeout - elapsed
                    self._step_callback(
                        step_callback, 
                        "等待登录...", 
                        f"已等待 {elapsed} 秒，剩余 {remaining} 秒"
                    )
                
                time.sleep(1)
            
            return False, f"登录超时({timeout // 60}分钟内未完成登录)"
            
        except Exception as e:
            self._log(f"等待登录失败: {e}")
            traceback.print_exc()
            return False, f"等待登录失败: {str(e)}"
    
    def close(self) -> None:
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                self._log("浏览器已关闭")
            except Exception:
                pass
            self.driver = None
    
    @abstractmethod
    def publish(
        self,
        video_path: str,
        title: str,
        topics: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        step_callback: Optional[Callable[[str, str], None]] = None
    ) -> Tuple[bool, str]:
        """
        发布视频
        
        Args:
            video_path: 视频文件路径
            title: 视频标题
            topics: 话题列表
            progress_callback: 进度回调函数
            step_callback: 步骤回调函数
            
        Returns:
            (是否成功, 消息)
        """
        pass
    
    def _validate_inputs(self, video_path: str, title: str) -> Tuple[bool, str]:
        """
        验证输入参数
        
        Args:
            video_path: 视频文件路径
            title: 视频标题
            
        Returns:
            (是否有效, 错误消息)
        """
        if not os.path.exists(video_path):
            return False, f"视频文件不存在: {video_path}"
        
        if not title or not title.strip():
            return False, "标题不能为空，请填写视频标题后再发布"
        
        return True, ""
