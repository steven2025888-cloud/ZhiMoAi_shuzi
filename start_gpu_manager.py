#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 电源管理器 - 快速启动脚本

检查依赖并启动 GPU 电源管理器
"""

import sys
import subprocess
import os


def check_dependencies():
    """检查依赖"""
    print("检查依赖...")

    missing = []

    # 检查 playwright
    try:
        import playwright
        print("✓ playwright 已安装")
    except ImportError:
        print("✗ playwright 未安装")
        missing.append("playwright")

    # 检查 websockets
    try:
        import websockets
        print("✓ websockets 已安装")
    except ImportError:
        print("✗ websockets 未安装")
        missing.append("websockets")

    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        print("\n安装命令:")
        print(f"  pip install {' '.join(missing)}")

        # 询问是否自动安装
        response = input("\n是否自动安装? (y/n): ")
        if response.lower() == 'y':
            print("\n正在安装...")
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing)

            # 如果安装了 playwright，还需要安装浏览器
            if "playwright" in missing:
                print("\n正在安装 Playwright 浏览器...")
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])

            print("\n✓ 依赖安装完成")
        else:
            print("\n请手动安装依赖后再运行")
            return False

    # 检查 playwright 浏览器
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True,
            text=True
        )
        if "chromium" in result.stdout.lower() and "already installed" not in result.stdout.lower():
            print("\n⚠️  Playwright 浏览器未安装")
            print("安装命令:")
            print("  python -m playwright install chromium")

            response = input("\n是否自动安装? (y/n): ")
            if response.lower() == 'y':
                print("\n正在安装 Playwright 浏览器...")
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
                print("\n✓ 浏览器安装完成")
            else:
                print("\n请手动安装浏览器后再运行")
                return False
        else:
            print("✓ Playwright 浏览器已安装")
    except Exception as e:
        print(f"⚠️  无法检查 Playwright 浏览器: {e}")

    return True


def main():
    print("=" * 50)
    print("  GPU 电源管理器 - 快速启动")
    print("=" * 50 + "\n")

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    print("\n" + "=" * 50)
    print("  启动 GPU 电源管理器")
    print("=" * 50 + "\n")

    # 启动主程序
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "gpu_power_manager.py")

    try:
        subprocess.run([sys.executable, main_script])
    except KeyboardInterrupt:
        print("\n\n程序已停止")
    except Exception as e:
        print(f"\n\n启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
