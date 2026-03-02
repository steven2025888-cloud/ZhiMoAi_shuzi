"""Verify Python environment has all required native extensions."""
import sys

checks = [
    ('PIL',         'from PIL import Image, ImageTk, ImageDraw'),
    ('orjson',      'import orjson'),
    ('pydantic_core','import pydantic_core'),
    ('numpy',       'import numpy'),
    ('cv2',         'import cv2'),
    ('gradio',      'import gradio'),
    ('webview',     'import webview'),
    ('cryptography','import cryptography'),
    ('cffi',        'import cffi'),
    ('fastapi',     'import fastapi'),
    ('uvicorn',     'import uvicorn'),
    ('pystray',     'import pystray'),
    ('websockets',  'import websockets'),
    ('aiohttp',     'import aiohttp'),
    ('httptools',   'import httptools'),
    ('pydub',       'import pydub'),
]

failed = []
for name, stmt in checks:
    try:
        exec(stmt)
    except Exception as e:
        failed.append((name, str(e)[:100]))

if failed:
    print(f'  [ERROR] {len(failed)} broken modules:')
    for name, err in failed:
        print(f'    - {name}: {err}')
    sys.exit(1)

print(f'  [OK] All {len(checks)} critical modules verified')
sys.exit(0)
