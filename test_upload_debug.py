# -*- coding: utf-8 -*-
"""测试视频号上传功能 - 调试版本"""

import time
import pyautogui
from lib_shipinhao_publish import ShipinhaoPublisher

# 设置 pyautogui 的安全延迟
pyautogui.PAUSE = 0.5
pyautogui.FAILSAFE = True

print("=" * 60)
print("测试视频号上传功能")
print("=" * 60)

# 创建发布器
pub = ShipinhaoPublisher()

# 初始化浏览器
print("\n[1] 初始化浏览器...")
if not pub._init_driver():
    print("❌ 浏览器初始化失败")
    exit(1)

print("✓ 浏览器初始化成功")

# 检查登录状态
print("\n[2] 检查登录状态...")
is_logged_in, msg = pub._check_login()
print(f"登录状态: {is_logged_in}, {msg}")

if not is_logged_in:
    print("❌ 未登录，请先登录")
    exit(1)

print("✓ 已登录")

# 等待页面加载
print("\n[3] 等待页面加载...")
time.sleep(3)

# 打印调试信息
print("\n[4] 收集页面调试信息...")
try:
    debug_info = pub.driver.execute_script("""
        var result = {
            iframes: [],
            inputs: [],
            uploadElements: [],
            buttons: []
        };
        
        // 收集 iframe 信息
        var iframes = document.querySelectorAll('iframe');
        for (var i = 0; i < iframes.length; i++) {
            var iframe = iframes[i];
            result.iframes.push({
                name: iframe.name || '',
                src: iframe.src || '',
                display: window.getComputedStyle(iframe).display
            });
        }
        
        // 收集所有 input
        var inputs = document.querySelectorAll('input');
        for (var i = 0; i < inputs.length; i++) {
            var input = inputs[i];
            result.inputs.push({
                type: input.type,
                accept: input.accept || '',
                display: window.getComputedStyle(input).display,
                className: input.className
            });
        }
        
        // 收集上传相关元素
        var uploadKeywords = ['上传', '选择', '拖拽', 'upload', 'select', 'drag'];
        var allElements = document.querySelectorAll('*');
        for (var i = 0; i < allElements.length; i++) {
            var el = allElements[i];
            var text = el.innerText || '';
            var className = el.className || '';
            
            for (var j = 0; j < uploadKeywords.length; j++) {
                if ((text.indexOf(uploadKeywords[j]) !== -1 && text.length < 50) ||
                    className.indexOf(uploadKeywords[j]) !== -1) {
                    result.uploadElements.push({
                        tag: el.tagName,
                        text: text.substring(0, 30),
                        className: className.substring(0, 60)
                    });
                    break;
                }
            }
        }
        
        // 收集按钮
        var buttons = document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            result.buttons.push({
                text: btn.innerText || '',
                className: btn.className
            });
        }
        
        return result;
    """)
    
    print(f"\n📊 页面信息:")
    print(f"  - iframe 数量: {len(debug_info['iframes'])}")
    for i, iframe in enumerate(debug_info['iframes'][:3]):
        print(f"    [{i}] name={iframe['name']}, src={iframe['src'][:50]}..., display={iframe['display']}")
    
    print(f"\n  - input 数量: {len(debug_info['inputs'])}")
    for i, inp in enumerate(debug_info['inputs'][:5]):
        print(f"    [{i}] type={inp['type']}, accept={inp['accept']}, display={inp['display']}")
    
    print(f"\n  - 上传相关元素: {len(debug_info['uploadElements'])}")
    for i, el in enumerate(debug_info['uploadElements'][:10]):
        print(f"    [{i}] {el['tag']}: text='{el['text']}', class='{el['className']}'")
    
    print(f"\n  - 按钮数量: {len(debug_info['buttons'])}")
    for i, btn in enumerate(debug_info['buttons'][:10]):
        if btn['text']:
            print(f"    [{i}] '{btn['text'][:30]}'")

except Exception as e:
    print(f"❌ 调试信息收集失败: {e}")

print("\n" + "=" * 60)
print("测试完成，浏览器将保持打开状态")
print("请检查页面，查看是否有文件选择对话框")
print("按 Ctrl+C 退出")
print("=" * 60)

# 保持浏览器打开
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\n程序退出")
