# -*- coding: utf-8 -*-
"""
织梦AI - 调试启动器（有控制台窗口，可以看到所有报错信息）
用法：双击运行此文件，或在 CMD 中执行 python launcher_debug.py
"""
import os
import sys
import subprocess
import time

# 获取正确的BASE_DIR（支持PyInstaller打包）
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print("  织梦AI 调试启动器")
print("=" * 60)
print(f"  工作目录: {BASE_DIR}")
print(f"  Python:   {sys.executable}")
print()

# 搜索 Python 解释器
python_paths = [
    os.path.join(BASE_DIR, "FunCosyVoice3", "python310", "python.exe"),
]

print("[1] 搜索 Python 解释器...")
python_exe = None
for p in python_paths:
    exists = os.path.exists(p)
    status = "✓ 找到" if exists else "✗ 不存在"
    print(f"  {status}: {p}")
    if exists and python_exe is None:
        python_exe = p

if not python_exe:
    print()
    print("!!! 错误: 未找到 Python 解释器 !!!")
    print("请确保 FunCosyVoice3 文件夹已正确安装")
    input("\n按回车键退出...")
    sys.exit(1)

print(f"\n  使用: {python_exe}")

# 搜索主程序
print("\n[2] 搜索主程序...")
script_candidates = [
    os.path.join(BASE_DIR, "app_backend.py"),
    os.path.join(BASE_DIR, "app_backend.pyc"),
]

app_backend = None
for p in script_candidates:
    exists = os.path.exists(p)
    status = "✓ 找到" if exists else "✗ 不存在"
    print(f"  {status}: {p}")
    if exists and app_backend is None:
        app_backend = p

if not app_backend:
    print()
    print("!!! 错误: 未找到 app_backend !!!")
    input("\n按回车键退出...")
    sys.exit(1)

print(f"\n  使用: {app_backend}")

# 检查 .env / config.dat
print("\n[3] 检查配置文件...")
env_file = os.path.join(BASE_DIR, ".env")
config_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ZhiMoAI')
config_file = os.path.join(config_dir, 'config.dat')

print(f"  .env:       {'✓ 存在' if os.path.exists(env_file) else '✗ 不存在'} ({env_file})")
print(f"  config.dat: {'✓ 存在' if os.path.exists(config_file) else '✗ 不存在'} ({config_file})")

# 检查关键目录
print("\n[4] 检查关键目录...")
for name, path in [
    ("FunCosyVoice3", os.path.join(BASE_DIR, "FunCosyVoice3")),
    ("heygem-win-50", os.path.join(BASE_DIR, "heygem-win-50")),
    ("libs", os.path.join(BASE_DIR, "libs")),
    ("logs", os.path.join(BASE_DIR, "logs")),
    ("ui", os.path.join(BASE_DIR, "ui")),
    ("docs", os.path.join(BASE_DIR, "docs")),
]:
    print(f"  {'✓' if os.path.exists(path) else '✗'} {name}: {path}")

# 启动（有控制台窗口，直接显示 stdout/stderr）
print("\n" + "=" * 60)
print("  启动 app_backend（控制台模式，所有输出可见）")
print("=" * 60)
print()

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

try:
    # 用 python.exe（不是 pythonw.exe）启动，不隐藏窗口
    process = subprocess.Popen(
        [python_exe, "-u", app_backend],
        cwd=BASE_DIR,
    )
    print(f"[OK] app_backend 已启动 (PID: {process.pid})")
    print(f"[OK] 此窗口会持续显示，关闭此窗口会结束程序")
    print()
    
    # 等待子进程结束
    rc = process.wait()
    print()
    print(f"[END] app_backend 已退出，退出码: {rc}")
    
except KeyboardInterrupt:
    print("\n[STOP] 用户中断")
    process.terminate()
except Exception as e:
    print(f"\n[ERROR] 启动失败: {e}")
    import traceback
    traceback.print_exc()

input("\n按回车键退出...")
