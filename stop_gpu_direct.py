#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接通过 CompShare API 关机（独立脚本）

依赖文件（与本脚本同目录）：
1. gpu_stop_api_template.json  # 从浏览器抓包保存的关机请求模板
2. gpu_storage_state.json      # Playwright 登录态

用法：
  python stop_gpu_direct.py
"""

import asyncio
import json
import os
import sys
import time
from urllib.parse import urlencode

from playwright.async_api import async_playwright


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOP_API_TEMPLATE_FILE = os.path.join(BASE_DIR, "gpu_stop_api_template.json")
STORAGE_STATE_FILE = os.path.join(BASE_DIR, "gpu_storage_state.json")


def load_json(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERR] 读取文件失败: {path}, error={e}")
        return None


def build_payload(template: dict) -> dict:
    body = dict(template.get("body") or {})
    body["Action"] = "StopCompShareInstance"
    body["_timestamp"] = str(int(time.time() * 1000))
    return body


def clean_headers(raw_headers: dict | None) -> dict:
    headers = dict(raw_headers or {})
    for k in list(headers.keys()):
        if k.lower() in ("content-length", "host", "cookie"):
            headers.pop(k, None)
    return headers


async def main() -> int:
    template = load_json(STOP_API_TEMPLATE_FILE)
    if not template:
        print(f"[ERR] 未找到或无法读取模板: {STOP_API_TEMPLATE_FILE}")
        return 1

    if not os.path.exists(STORAGE_STATE_FILE):
        print(f"[ERR] 未找到登录态文件: {STORAGE_STATE_FILE}")
        return 1

    url = template.get("url") or "https://api.compshare.cn/?Action=StopCompShareInstance"
    payload = build_payload(template)
    headers = clean_headers(template.get("headers"))
    data = urlencode(payload)

    print("[INFO] 准备发送关机请求...")
    print(f"[INFO] URL: {url}")
    print(f"[INFO] UHostId: {payload.get('UHostId', 'N/A')}")

    try:
        async with async_playwright() as p:
            request_ctx = await p.request.new_context(
                storage_state=STORAGE_STATE_FILE,
                ignore_https_errors=True,
            )
            resp = await request_ctx.post(url, headers=headers, data=data)
            text = await resp.text()
            print(f"[INFO] HTTP {resp.status}")
            print(text)

            # 尝试解析 RetCode，0 认为成功
            try:
                obj = json.loads(text)
                if int(obj.get("RetCode", -1)) == 0:
                    print("[OK] 关机请求成功")
                    await request_ctx.dispose()
                    return 0
                print(f"[ERR] 关机请求失败, RetCode={obj.get('RetCode')}, Message={obj.get('Message')}")
                await request_ctx.dispose()
                return 2
            except Exception:
                # 非 JSON 时按 HTTP 判断
                await request_ctx.dispose()
                return 0 if 200 <= resp.status < 300 else 2
    except Exception as e:
        print(f"[ERR] 请求异常: {e}")
        return 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

