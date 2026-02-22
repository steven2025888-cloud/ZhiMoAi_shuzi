# -*- coding: utf-8 -*-
"""
织梦AI - 简单启动器
直接调用启动应用.bat或启动Python应用
"""
import os
import subprocess
import sys

if __name__ == "__main__":
    try:
        # 获取当前目录
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 启动bat文件
        bat_file = os.path.join(base_dir, "启动应用.bat")
        
        if os.path.exists(bat_file):
            # 使用start命令启动，这样启动器可以立即退出
            # 使用DETACHED_PROCESS标志，让子进程完全独立
            subprocess.Popen(
                bat_file,
                shell=True,
                cwd=base_dir,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            # 如果bat不存在，直接启动Python
            pythonw = os.path.join(base_dir, "_internal_tts", "installer_files", "env", "pythonw.exe")
            
            # 检查主程序（优先使用.py，如果不存在则使用.pyc）
            app_py = os.path.join(base_dir, "app_backend.py")
            app_pyc = os.path.join(base_dir, "app_backend.pyc")
            
            if os.path.exists(app_py):
                app_file = app_py
            elif os.path.exists(app_pyc):
                app_file = app_pyc
            else:
                app_file = None
            
            if os.path.exists(pythonw) and app_file:
                subprocess.Popen(
                    [pythonw, app_file],
                    cwd=base_dir,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
        
        # 立即退出，释放内存
        sys.exit(0)
    except Exception as e:
        sys.exit(1)
