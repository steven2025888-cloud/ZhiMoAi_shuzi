# -*- coding: utf-8 -*-
"""
测试更新下载功能
"""
import os
import sys
import time
import json

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入更新相关函数
try:
    import urllib.request
    import urllib.error
except ImportError:
    print("urllib模块未加载")
    exit(1)

# 模拟更新信息
MOCK_UPDATE_INFO = {
    "version": "1.1.0",
    "build": 105,
    "url": "https://zhimengai-oss.oss-cn-hangzhou.aliyuncs.com/updates/ZhiMoAI_v1.1.0_Setup.exe",
    "force": False,
    "desc": "1. 增加自动更新功能\n2. 优化登录界面\n3. 添加版本号显示\n4. 修复已知问题"
}

def test_update_dialog():
    """测试更新对话框"""
    print("=" * 60)
    print("测试更新对话框")
    print("=" * 60)
    print()
    
    print("模拟更新信息:")
    print(json.dumps(MOCK_UPDATE_INFO, indent=2, ensure_ascii=False))
    print()
    
    # 导入必要的模块
    from app_backend import show_update_dialog, CURRENT_VERSION, CURRENT_BUILD
    
    print(f"当前版本: {CURRENT_VERSION} (Build {CURRENT_BUILD})")
    print(f"远程版本: {MOCK_UPDATE_INFO['version']} (Build {MOCK_UPDATE_INFO['build']})")
    print()
    
    print("显示更新对话框...")
    print("功能测试:")
    print("  1. 点击'下载更新'按钮")
    print("  2. 观察下载进度")
    print("  3. 下载完成后点击'安装更新'")
    print("  4. 程序应该自动退出并启动安装程序")
    print()
    
    # 显示对话框
    action = show_update_dialog(MOCK_UPDATE_INFO, is_force=False)
    
    print()
    print(f"用户操作: {action}")
    
    if action == "install":
        print("✓ 用户选择安装更新")
        print("✓ 安装程序已启动")
        print("✓ 当前程序将退出")
    elif action == "later":
        print("用户选择稍后更新")
    elif action == "exit":
        print("用户选择退出")
    else:
        print("用户取消操作")
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_update_dialog()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
