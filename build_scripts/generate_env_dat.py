# -*- coding: utf-8 -*-
"""
将 .env 明文配置文件转换为 env.dat 混淆文件。
打包前运行：python build_scripts/generate_env_dat.py

混淆方式：XOR + base64，防止用户直接阅读配置内容。
运行时由 unified_app.py 的 load_env_file() 自动解码。
"""
import base64
import os
import sys

# XOR 混淆密钥（与 unified_app.py 中保持一致）
_XOR_KEY = b"ZhiMoAI2025@Cfg"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
DAT_PATH = os.path.join(BASE_DIR, "env.dat")


def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def main():
    if not os.path.exists(ENV_PATH):
        print(f"[错误] .env 文件不存在: {ENV_PATH}")
        return 1

    with open(ENV_PATH, "r", encoding="utf-8") as f:
        raw = f.read()

    encoded = base64.b64encode(xor_bytes(raw.encode("utf-8"), _XOR_KEY)).decode("ascii")

    with open(DAT_PATH, "w", encoding="ascii") as f:
        f.write(encoded)

    print(f"[OK] env.dat 已生成: {DAT_PATH}")
    print(f"     源文件: {ENV_PATH} ({len(raw)} 字符)")
    print(f"     混淆后: {DAT_PATH} ({len(encoded)} 字符)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
