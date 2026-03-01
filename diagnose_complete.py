#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整诊断脚本 - 测试 GPU Monitor 通知流程

测试步骤：
1. 检查 Redis 连接
2. 检查 GPU Monitor 是否在线
3. 检查 Hyperf 服务状态
4. 模拟 PC 端调用 API
5. 检查 Redis 队列
6. 等待并观察通知是否发送
"""

import asyncio
import json
import os
import sys
import time
import requests
import websockets
import redis


WS_URL = "wss://api.zhimengai.xyz/dsp"
API_URL = "https://api.zhimengai.xyz/api/heygem/task/submit"
REDIS_HOST = "45.192.97.144"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_USERNAME = os.getenv("REDIS_USERNAME")  # 不设默认值，None 表示不传 username
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "a8469758")


def _to_str(v):
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", errors="replace")
        except Exception:
            return str(v)
    return v


def _to_str_set(values):
    return {_to_str(x) for x in (values or set())}


def _to_str_list(values):
    return [_to_str(x) for x in (values or [])]


def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def main():
    print_section("GPU Monitor 通知流程完整诊断")

    # 1. 检查 Redis
    print_section("1. 检查 Redis 连接")
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            username=REDIS_USERNAME or None,
            password=REDIS_PASSWORD,
        )
        r.ping()
        print("[✓] Redis 连接成功")
    except Exception as exc:
        print(f"[✗] Redis 连接失败: {type(exc).__name__}: {exc!r}")
        import traceback
        traceback.print_exc()
        return

    # 2. 检查 GPU Monitor
    print_section("2. 检查 GPU Monitor 状态")
    monitors = _to_str_set(r.smembers("dsp:gpu_monitors"))
    print(f"在线 GPU Monitor: {len(monitors)} 个")
    if monitors:
        print(f"FD 列表: {monitors}")
    else:
        print("[警告] 没有在线的 GPU Monitor！")
        print("请先启动: python gpu_power_manager.py")

    # 3. 检查 Redis 队列
    print_section("3. 检查 Redis 通知队列")
    notify_key = "dsp:gpu_monitor_notify"
    queue_len = r.llen(notify_key)
    print(f"队列长度: {queue_len}")
    if queue_len > 0:
        print("队列中的消息:")
        messages = _to_str_list(r.lrange(notify_key, 0, -1))
        for i, msg in enumerate(messages, 1):
            print(f"  [{i}] {msg}")

    # 4. 连接 WebSocket 监听消息
    print_section("4. 连接 WebSocket 监听消息")

    received_notification = False

    async def ws_listener():
        nonlocal received_notification
        try:
            async with websockets.connect(WS_URL, ping_interval=30, ping_timeout=10) as ws:
                print("[✓] WebSocket 已连接")

                # 注册为 gpu_monitor
                await ws.send(json.dumps({"type": "register", "role": "gpu_monitor"}))
                print("[✓] 已注册为 gpu_monitor")

                # 监听消息
                print("\n[监听中] 等待接收通知...")
                start_time = time.time()

                while time.time() - start_time < 30:  # 最多等待 30 秒
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(raw)
                        msg_type = data.get("type", "")

                        if msg_type == "registered":
                            print(f"[✓] 服务端确认注册: {data.get('role')}")
                        elif msg_type == "pong":
                            pass  # 忽略心跳
                        elif msg_type == "gpu.job.submit":
                            print(f"\n[✓✓✓] 收到 GPU 任务通知！")
                            print(f"消息内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
                            received_notification = True
                            break
                        else:
                            print(f"[收到消息] type={msg_type}, data={data}")
                    except asyncio.TimeoutError:
                        elapsed = int(time.time() - start_time)
                        print(f"  等待中... ({elapsed}s)")
                        continue

                if not received_notification:
                    print("\n[✗] 30秒内未收到通知")
        except Exception as e:
            print(f"[✗] WebSocket 错误: {e}")
            import traceback
            traceback.print_exc()

    # 启动 WebSocket 监听
    ws_task = asyncio.create_task(ws_listener())

    # 等待 WebSocket 连接建立
    await asyncio.sleep(2)

    # 5. 模拟 PC 端调用 API
    print_section("5. 模拟 PC 端调用 API")

    license_key = os.getenv("LICENSE_KEY", "2RFH-MOFU-XVTZ-N79P")
    machine_code = os.getenv("MACHINE_CODE", "test_machine_" + str(int(time.time())))
    print(f"使用卡密: {license_key}")
    print(f"使用设备码: {machine_code}")

    try:
        headers = {
            "Authorization": f"Bearer {license_key}",
            "X-Machine-Code": machine_code,
            "X-Device-Type": "pc",
            "Content-Type": "application/json",
        }

        payload = {
            "audio_hash": "test_audio_" + str(int(time.time())),
            "audio_ext": ".wav",
            "video_hash": "test_video_" + str(int(time.time())),
            "video_ext": ".mp4",
            "license_key": license_key,
        }

        print(f"请求 URL: {API_URL}")
        print(f"请求头: {headers}")
        print(f"请求体: {json.dumps(payload, ensure_ascii=False)}")

        resp = requests.post(API_URL, json=payload, headers=headers, timeout=10)

        print(f"\n[✓] API 响应状态码: {resp.status_code}")
        print(f"响应内容: {resp.text}")

        if resp.status_code == 200:
            result = resp.json()
            print(f"响应 JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")

    except Exception as e:
        print(f"[✗] API 调用失败: {e}")
        import traceback
        traceback.print_exc()

    # 6. 再次检查 Redis 队列
    print_section("6. 检查 API 调用后的 Redis 队列")
    queue_len = r.llen(notify_key)
    print(f"队列长度: {queue_len}")
    if queue_len > 0:
        print("队列中的消息:")
        messages = _to_str_list(r.lrange(notify_key, 0, -1))
        for i, msg in enumerate(messages, 1):
            print(f"  [{i}] {msg}")
    else:
        print("[警告] 队列为空！API 可能没有正确写入消息")

    # 7. 等待 WebSocket 监听完成
    print_section("7. 等待 WebSocket 接收通知")
    await ws_task

    # 8. 总结
    print_section("诊断总结")

    if received_notification:
        print("[✓✓✓] 测试成功！GPU Monitor 收到了任务通知")
        print("\n整个流程正常工作：")
        print("  1. PC 端调用 API ✓")
        print("  2. API 写入 Redis 队列 ✓")
        print("  3. WebSocket 定时器检查队列 ✓")
        print("  4. GPU Monitor 收到通知 ✓")
    else:
        print("[✗✗✗] 测试失败！GPU Monitor 未收到通知")
        print("\n可能的问题：")

        if queue_len == 0:
            print("  1. [✗] Redis 队列为空")
            print("     - 检查 HeyGemTaskController 是否正确写入队列")
            print("     - 检查 API 调用是否成功（状态码 200）")
            print("     - 检查中间件是否正确验证 license_key")
        else:
            print("  1. [✓] Redis 队列有消息")
            print("  2. [✗] WebSocket 定时器未发送消息")
            print("     - 检查 Hyperf 服务是否重启")
            print("     - 检查定时器是否启动（查看 Hyperf 日志）")
            print("     - 检查 Dsp.php 的 _checkAndSendGpuMonitorNotifications 方法")

        if len(monitors) == 0:
            print("  3. [✗] 没有在线的 GPU Monitor")
            print("     - 启动 gpu_power_manager.py")
        else:
            print("  3. [✓] GPU Monitor 在线")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[诊断中断]")
    except Exception as e:
        print(f"\n[诊断失败] {e}")
        import traceback
        traceback.print_exc()
