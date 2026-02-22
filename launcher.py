# -*- coding: utf-8 -*-
"""
织梦AI - 启动器程序
功能：
  - 合并 启动应用.bat 和 启动应用.vbs 的功能
  - 自动清理超大日志文件
  - 记录运行日志
  - 无窗口启动
"""
import os
import sys
import subprocess
import time
import logging
from datetime import datetime
import traceback

# 获取正确的BASE_DIR（支持PyInstaller打包）
if getattr(sys, 'frozen', False):
    # 如果是PyInstaller打包的exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 如果是Python脚本
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置日志
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 配置日志格式
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
        ]
    )
    logger = logging.getLogger(__name__)
except Exception as e:
    # 如果日志配置失败，使用基本的print
    print(f"日志配置失败: {e}")
    logger = None


def log_info(msg):
    """记录日志"""
    if logger:
        logger.info(msg)
    else:
        print(f"[INFO] {msg}")


def log_error(msg):
    """记录错误"""
    if logger:
        logger.error(msg)
    else:
        print(f"[ERROR] {msg}")


def log_warning(msg):
    """记录警告"""
    if logger:
        logger.warning(msg)
    else:
        print(f"[WARNING] {msg}")


def clean_logs():
    """清理超大日志文件"""
    try:
        log_cleaner = os.path.join(BASE_DIR, "log_cleaner.py")
        log_cleaner_pyc = os.path.join(BASE_DIR, "log_cleaner.pyc")
        
        # 优先使用pyc
        if os.path.exists(log_cleaner_pyc):
            log_cleaner = log_cleaner_pyc
        elif not os.path.exists(log_cleaner):
            return
        
        # 尝试多个可能的Python路径
        python_paths = [
            os.path.join(BASE_DIR, "_internal_tts", "installer_files", "env", "python.exe"),
            os.path.join(BASE_DIR, "IndexTTS2-SonicVale", "installer_files", "env", "python.exe"),
            "python.exe"
        ]
        
        python_exe = None
        for path in python_paths:
            if os.path.exists(path):
                python_exe = path
                break
        
        if python_exe:
            subprocess.run([python_exe, log_cleaner], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    except Exception as e:
        log_warning(f"日志清理失败: {e}")


def start_app():
    """启动应用"""
    try:
        log_info("=" * 80)
        log_info(f"织梦AI大模型 v2.0 启动器")
        log_info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_info(f"工作目录: {BASE_DIR}")
        log_info("=" * 80)
        
        # 1. 清理日志
        log_info("[1/3] 清理超大日志文件...")
        clean_logs()
        
        # 2. 检查环境
        log_info("[2/3] 检查运行环境...")
        
        # 尝试多个可能的Python路径
        python_paths = [
            os.path.join(BASE_DIR, "_internal_tts", "installer_files", "env", "python.exe"),
            os.path.join(BASE_DIR, "IndexTTS2-SonicVale", "installer_files", "env", "python.exe"),
            "python.exe"  # 系统Python
        ]
        
        python_exe = None
        for path in python_paths:
            if os.path.isabs(path):
                exists = os.path.exists(path)
            else:
                exists = True  # 系统Python，假设存在
            
            if exists:
                python_exe = path
                log_info(f"  找到Python: {path}")
                break
            else:
                log_info(f"  未找到: {path}")
        
        if not python_exe:
            log_error("Python 解释器未找到")
            log_error("尝试的路径:")
            for path in python_paths:
                log_error(f"  - {path}")
            log_error("请确保已正确安装引擎文件")
            return False
        
        # 检查主程序（支持.py和.pyc）
        app_backend = os.path.join(BASE_DIR, "app_backend.py")
        app_backend_pyc = os.path.join(BASE_DIR, "app_backend.pyc")
        
        if os.path.exists(app_backend_pyc):
            app_backend = app_backend_pyc
            log_info(f"  使用加密版本: {app_backend}")
        elif os.path.exists(app_backend):
            log_info(f"  使用源代码版本: {app_backend}")
        else:
            log_error(f"主程序未找到: {app_backend}")
            return False
        
        # 3. 启动应用
        log_info("[3/3] 启动应用...")
        log_info(f"Python: {python_exe}")
        log_info(f"主程序: {app_backend}")
        
        # 使用 pythonw.exe 无窗口启动
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw_exe):
            pythonw_exe = python_exe
            log_info(f"  使用python.exe (pythonw.exe不存在)")
        else:
            log_info(f"  使用pythonw.exe")
        
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        process = subprocess.Popen(
            [pythonw_exe, app_backend],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags
        )
        
        log_info(f"应用已启动 (PID: {process.pid})")
        log_info("=" * 80)
        return True
        
    except Exception as e:
        log_error(f"启动失败: {e}")
        log_error(traceback.format_exc())
        return False


if __name__ == "__main__":
    try:
        success = start_app()
        sys.exit(0 if success else 1)
    except Exception as e:
        log_error(f"启动器异常: {e}")
        log_error(traceback.format_exc())
        sys.exit(1)
