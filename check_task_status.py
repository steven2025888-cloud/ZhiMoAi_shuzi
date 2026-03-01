#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查和清除任务状态

用于诊断和清除卡住的任务状态
"""

import redis
import json
import os
import sys

# Redis 配置
REDIS_HOST = "45.192.97.144"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_USERNAME = os.getenv("REDIS_USERNAME")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "a8469758")

# 你的卡密
LICENSE_KEY = "ZM-2026-01-15-TEST-0002"


def main():
    print("=" * 70)
    print("  检查和清除任务状态")
    print("=" * 70)

    # 连接 Redis
    print(f"\n[1] 连接 Redis: {REDIS_HOST}:{REDIS_PORT}")
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
    except Exception as e:
        print(f"[✗] Redis 连接失败: {e}")
        return

    # 检查任务状态
    print(f"\n[2] 检查卡密 {LICENSE_KEY} 的任务状态")
    status_key = f"dsp:task_status:{LICENSE_KEY}"

    # 获取所有任务状态
    all_tasks = r.hgetall(status_key)

    if not all_tasks:
        print("[✓] 没有进行中的任务")
    else:
        print(f"[!] 发现 {len(all_tasks)} 个任务状态:")
        for task_type, task_data in all_tasks.items():
            if isinstance(task_type, bytes):
                task_type = task_type.decode('utf-8')
            if isinstance(task_data, bytes):
                task_data = task_data.decode('utf-8')

            try:
                task = json.loads(task_data)
                print(f"\n  任务类型: {task_type}")
                print(f"  状态: {task.get('status')}")
                print(f"  请求ID: {task.get('request_id')}")
                print(f"  开始时间: {task.get('start_time')}")

                import time
                elapsed = time.time() - task.get('start_time', 0)
                print(f"  已用时: {int(elapsed)} 秒")

                if elapsed > 600:  # 超过10分钟
                    print(f"  [!] 任务已超时（>10分钟）")
            except:
                print(f"  原始数据: {task_data}")

    # 检查队列
    print(f"\n[3] 检查任务队列")
    queue_key = f"dsp:pending_tasks:{LICENSE_KEY}"
    queue_len = r.llen(queue_key)
    print(f"队列长度: {queue_len}")

    if queue_len > 0:
        print("队列中的任务:")
        tasks = r.lrange(queue_key, 0, -1)
        for i, task_json in enumerate(tasks, 1):
            if isinstance(task_json, bytes):
                task_json = task_json.decode('utf-8')
            try:
                task = json.loads(task_json)
                print(f"  [{i}] 请求ID: {task.get('request_id')}, 类型: {task.get('task_type')}")
            except:
                print(f"  [{i}] {task_json[:100]}...")

    # 询问是否清除
    print(f"\n[4] 清除操作")
    if all_tasks or queue_len > 0:
        response = input("\n是否清除所有任务状态和队列？(y/n): ")
        if response.lower() == 'y':
            # 清除任务状态
            if all_tasks:
                r.delete(status_key)
                print(f"[✓] 已清除任务状态: {status_key}")

            # 清除队列
            if queue_len > 0:
                r.delete(queue_key)
                print(f"[✓] 已清除任务队列: {queue_key}")

            print("\n[✓✓✓] 清除完成！现在可以重新提交任务了")
        else:
            print("\n[取消] 未执行清除操作")
    else:
        print("[✓] 没有需要清除的内容")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[操作取消]")
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
