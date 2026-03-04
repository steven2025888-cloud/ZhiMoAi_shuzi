# -*- coding: utf-8 -*-
"""
将 .env 明文配置文件加密为二进制文件。
打包前运行：python build_scripts/generate_env_dat.py

加密方式：AES-256-CBC（PKCS7 填充），密钥由 PBKDF2 派生。
输出路径：_internal_data/_rt_init.bin（伪装为运行时缓存）
运行时由 unified_app.py 的 load_env_file() 自动解密。
"""
import hashlib
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
# 输出到 _internal_data/ 目录，文件名伪装为运行时缓存
OUT_DIR = os.path.join(BASE_DIR, "_internal_data")
OUT_PATH = os.path.join(OUT_DIR, "_rt_init.bin")

# ── 密钥派生参数（与 unified_app.py 保持一致）──
_PASSPHRASE = b"Zm@2025!Rt#Cfg$Init"
_KDF_SALT = b"\xa3\x91\x0e\x7f\x44\xbc\x6d\x12\xee\x53\x01\xd8\x9a\xf7\x2c\x88"
_KDF_ITER = 260000


def _derive_key():
    return hashlib.pbkdf2_hmac("sha256", _PASSPHRASE, _KDF_SALT, _KDF_ITER)


def main():
    if not os.path.exists(ENV_PATH):
        print(f"[错误] .env 文件不存在: {ENV_PATH}")
        return 1

    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
    except ImportError:
        print("[错误] 缺少 pycryptodome，请先安装: pip install pycryptodome")
        return 1

    with open(ENV_PATH, "r", encoding="utf-8") as f:
        raw = f.read()

    key = _derive_key()
    cipher = AES.new(key, AES.MODE_CBC)
    ct = cipher.encrypt(pad(raw.encode("utf-8"), AES.block_size))
    # 格式：IV(16字节) + 密文
    payload = cipher.iv + ct

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        f.write(payload)

    print(f"[OK] 配置已加密: {OUT_PATH}")
    print(f"     源文件: {ENV_PATH} ({len(raw)} 字符)")
    print(f"     加密后: {OUT_PATH} ({len(payload)} 字节, AES-256-CBC)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
