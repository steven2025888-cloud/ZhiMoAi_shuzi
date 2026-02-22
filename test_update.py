# -*- coding: utf-8 -*-
"""
测试更新检查功能
"""
import json
import os
import tempfile
try:
    import urllib.request
    import urllib.error
except ImportError:
    print("urllib模块未加载")
    exit(1)

UPDATE_CHECK_URL = "https://api.zhimengai.xyz/api/update/Dspcheck"
CURRENT_VERSION = "1.0.9"
CURRENT_BUILD = 103

def test_update_check():
    """测试更新检查"""
    print("=" * 60)
    print("测试更新检查功能")
    print("=" * 60)
    print()
    
    print(f"当前版本: {CURRENT_VERSION} (Build {CURRENT_BUILD})")
    print(f"检查地址: {UPDATE_CHECK_URL}")
    print()
    
    try:
        print("正在连接服务器...")
        req = urllib.request.Request(
            UPDATE_CHECK_URL,
            headers={'User-Agent': 'ZhiMoAI/1.0'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"HTTP状态码: {response.status}")
            data = json.loads(response.read().decode('utf-8'))
        
        print()
        print("服务器返回数据:")
        print("-" * 60)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("-" * 60)
        print()
        
        # 解析数据
        remote_version = data.get("version", "")
        remote_build = int(data.get("build", 0))
        download_url = data.get("url", "")
        force_update = data.get("force", False)
        description = data.get("desc", "")
        
        print("解析结果:")
        print(f"  远程版本: {remote_version} (Build {remote_build})")
        print(f"  下载地址: {download_url}")
        print(f"  强制更新: {'是' if force_update else '否'}")
        print(f"  更新说明: {description}")
        print()
        
        # 比较版本
        if remote_build > CURRENT_BUILD:
            print("✓ 发现新版本！")
            if force_update:
                print("⚠ 这是强制更新")
        elif remote_build == CURRENT_BUILD:
            print("⚠ build 号相同，不会触发更新！请检查服务端 build 号是否已增加")
        else:
            print("⚠ 当前版本比服务器版本新")
        
        # 测试下载链接是否支持 Range 请求（断点续传）
        print()
        print("-" * 60)
        print("测试下载链接是否支持断点续传...")
        try:
            range_req = urllib.request.Request(
                download_url,
                headers={'User-Agent': 'ZhiMoAI/1.0', 'Range': 'bytes=0-0'},
                method='GET'
            )
            range_resp = urllib.request.urlopen(range_req, timeout=10)
            if range_resp.status == 206:
                print("✓ 服务器支持断点续传 (HTTP 206)")
                content_range = range_resp.headers.get('Content-Range', '')
                if content_range:
                    total = content_range.split('/')[-1]
                    print(f"  文件总大小: {total} 字节")
            elif range_resp.status == 200:
                print("⚠ 服务器不支持 Range 请求，断点续传不可用")
            range_resp.close()
        except Exception as e:
            print(f"✗ 断点续传测试失败: {e}")
        
        print()
        print("=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except urllib.error.URLError as e:
        print(f"✗ 网络连接失败: {e}")
    except json.JSONDecodeError as e:
        print(f"✗ 数据解析失败: {e}")
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_update_check()
