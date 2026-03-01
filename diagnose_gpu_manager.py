#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 电源管理器诊断工具

用于排查 GPU Manager 不工作的问题
"""

import asyncio
import json
import websockets
from datetime import datetime

WS_URL = "wss://api.zhimengai.xyz/dsp"


async def check_websocket_connection():
    """检查 WebSocket 连接"""
    print("\n" + "=" * 60)
    print("1. 检查 WebSocket 连接")
    print("=" * 60)

    try:
        async with websockets.connect(WS_URL, timeout=10) as ws:
            print(f"✓ WebSocket 连接成功: {WS_URL}")
            return True
    except Exception as e:
        print(f"✗ WebSocket 连接失败: {e}")
        return False


async def check_gpu_monitor_registration():
    """检查 GPU Monitor 注册"""
    print("\n" + "=" * 60)
    print("2. 检查 GPU Monitor 注册")
    print("=" * 60)

    try:
        async with websockets.connect(WS_URL) as ws:
            # 注册为 GPU Monitor
            await ws.send(json.dumps({"type": "register", "role": "gpu_monitor"}))
            print("已发送注册消息...")

            # 等待响应
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(response)
            print(f"收到响应: {data}")

            if data.get("type") == "registered" and data.get("role") == "gpu_monitor":
                print("✓ GPU Monitor 注册成功")
                return True
            else:
                print(f"✗ GPU Monitor 注册失败: {data}")
                return False

    except Exception as e:
        print(f"✗ 注册失败: {e}")
        return False


async def check_task_notification():
    """检查任务通知是否能到达 GPU Monitor"""
    print("\n" + "=" * 60)
    print("3. 检查任务通知")
    print("=" * 60)

    test_key = f"diag_{datetime.now().timestamp()}"

    try:
        # 创建两个连接
        async with websockets.connect(WS_URL) as client_ws, \
                   websockets.connect(WS_URL) as monitor_ws:

            # 注册客户端
            print(f"注册客户端 (key={test_key})...")
            await client_ws.send(json.dumps({
                "type": "register",
                "key": test_key,
                "device_type": "pc"
            }))
            await client_ws.recv()
            print("✓ 客户端注册成功")

            # 注册 GPU Monitor
            print("注册 GPU Monitor...")
            await monitor_ws.send(json.dumps({
                "type": "register",
                "role": "gpu_monitor"
            }))
            await monitor_ws.recv()
            print("✓ GPU Monitor 注册成功")

            await asyncio.sleep(1)

            # 发送 gpu.job.submit 任务
            print("\n发送 gpu.job.submit 任务...")
            await client_ws.send(json.dumps({
                "type": "gpu.job.submit",
                "task_type": "heygem_submit",
                "request_id": f"diag_{datetime.now().timestamp()}",
                "payload": {"test": True}
            }))
            print("✓ 任务已发送")

            # 等待 GPU Monitor 接收通知
            print("\n等待 GPU Monitor 接收通知...")
            try:
                notification = await asyncio.wait_for(monitor_ws.recv(), timeout=5)
                data = json.loads(notification)
                print(f"收到通知: {data}")

                if data.get("type") == "gpu.job.submit":
                    print("✓ GPU Monitor 成功接收到任务通知")
                    return True
                else:
                    print(f"✗ 收到的不是任务通知: {data.get('type')}")
                    return False

            except asyncio.TimeoutError:
                print("✗ 超时：GPU Monitor 未收到任务通知")
                print("\n可能的原因:")
                print("1. Dsp.php 未添加 _notifyGpuMonitors 调用")
                print("2. Hyperf 服务未重启")
                print("3. 代码修改有误")
                return False

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_gpu_manager_running():
    """检查 GPU Manager 是否在运行"""
    print("\n" + "=" * 60)
    print("4. 检查 GPU Manager 是否在运行")
    print("=" * 60)

    try:
        async with websockets.connect(WS_URL) as ws:
            # 查看是否有 GPU Monitor 在线
            await ws.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(ws.recv(), timeout=3)
            data = json.loads(response)

            if data.get("type") == "pong":
                print("✓ WebSocket 服务正常")
                print("\n⚠️  无法直接检测 GPU Manager 是否在运行")
                print("请检查:")
                print("1. 是否运行了 python gpu_power_manager.py")
                print("2. 查看 GPU Manager 的控制台输出")
                print("3. 确认是否看到 '[WS] 服务端确认: gpu_monitor'")
                return None

    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False


async def diagnose():
    """运行完整诊断"""
    print("=" * 60)
    print("GPU 电源管理器诊断工具")
    print("=" * 60)
    print("\n此工具将检查:")
    print("1. WebSocket 连接")
    print("2. GPU Monitor 注册")
    print("3. 任务通知机制")
    print("4. GPU Manager 运行状态")

    input("\n按 Enter 开始诊断...")

    results = []

    # 检查 1
    result1 = await check_websocket_connection()
    results.append(("WebSocket 连接", result1))

    if not result1:
        print("\n✗ WebSocket 连接失败，无法继续诊断")
        return False

    # 检查 2
    result2 = await check_gpu_monitor_registration()
    results.append(("GPU Monitor 注册", result2))

    # 检查 3
    result3 = await check_task_notification()
    results.append(("任务通知", result3))

    # 检查 4
    result4 = await check_gpu_manager_running()
    if result4 is not None:
        results.append(("GPU Manager 运行", result4))

    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)

    for name, result in results:
        if result is True:
            status = "✓ 正常"
        elif result is False:
            status = "✗ 异常"
        else:
            status = "⚠️  无法确定"
        print(f"{name}: {status}")

    # 给出建议
    print("\n" + "=" * 60)
    print("建议")
    print("=" * 60)

    if not result3:
        print("\n⚠️  任务通知未到达 GPU Monitor")
        print("\n请执行以下步骤:")
        print("1. 确认 Dsp.php 已修改（添加 _notifyGpuMonitors 调用）")
        print("2. 重启 Hyperf 服务:")
        print("   ps aux | grep hyperf")
        print("   kill -9 <pid>")
        print("   php bin/hyperf.php start")
        print("3. 重新运行此诊断工具")
    elif result3:
        print("\n✓ 任务通知机制正常")
        print("\n如果 GPU Manager 仍然不工作，请检查:")
        print("1. GPU Manager 是否正在运行")
        print("2. 查看 GPU Manager 的日志输出")
        print("3. 确认 GPU Manager 收到了任务通知")
        print("   应该看到: [WS] 检测到 GPU 任务: gpu.job.submit")
        print("4. 确认 GPU 状态检测是否正确")
        print("   应该看到: [Check] GPU=stopped, 有任务=True")

    return all(r for r in results if r is not None)


async def main():
    try:
        await diagnose()
    except KeyboardInterrupt:
        print("\n\n诊断中断")
    except Exception as e:
        print(f"\n诊断失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
