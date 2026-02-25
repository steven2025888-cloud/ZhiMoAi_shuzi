# -*- coding: utf-8 -*-
"""
lib_license.py — 卡密验证模块

提供本地卡密存储和远程API验证功能。
"""

import hashlib
import json
import os
import platform
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from typing import Dict, Optional, Tuple

# ============================================================
# 常量配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSE_FILE = os.path.join(BASE_DIR, ".license")
API_BASE_URL = "https://api.zhimengai.xyz"
API_URL = f"{API_BASE_URL}/api/dsp/login"

# Windows subprocess 标志
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ============================================================
# 机器码生成
# ============================================================
def _get_wmic_value(wmic_args: list, skip_header: str) -> Optional[str]:
    """执行wmic命令并获取结果值"""
    if platform.system() != "Windows":
        return None
    try:
        result = subprocess.run(
            wmic_args,
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=_CREATE_NO_WINDOW
        )
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line and line != skip_header:
                return line
    except Exception:
        pass
    return None


def _get_machine_code() -> str:
    """生成稳定的机器码（基于硬件信息）"""
    parts = []
    
    # 1. MAC 地址
    try:
        parts.append(str(uuid.getnode()))
    except Exception:
        pass
    
    # 2. 计算机名
    try:
        parts.append(platform.node())
    except Exception:
        pass
    
    # 3. Windows 硬件信息
    if platform.system() == "Windows":
        # 主板序列号
        serial = _get_wmic_value(
            ["wmic", "baseboard", "get", "SerialNumber"],
            "SerialNumber"
        )
        if serial:
            parts.append(serial)
        
        # CPU ID
        cpu_id = _get_wmic_value(
            ["wmic", "cpu", "get", "ProcessorId"],
            "ProcessorId"
        )
        if cpu_id:
            parts.append(cpu_id)
    
    raw = "|".join(parts) if parts else str(uuid.getnode())
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


# ============================================================
# 本地存储操作
# ============================================================
def _load_local() -> Optional[Dict]:
    """读取本地保存的卡密信息"""
    if not os.path.exists(LICENSE_FILE):
        return None
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _save_local(license_key: str, expire_time: str) -> bool:
    """保存卡密到本地"""
    data = {
        "license_key": license_key,
        "expire_time": expire_time,
        "login_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "machine_code": _get_machine_code(),
    }
    try:
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        return True
    except IOError as e:
        print(f"[LICENSE] 保存失败: {e}")
        return False


def _clear_local() -> None:
    """清除本地卡密"""
    try:
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)
    except OSError:
        pass


def _is_expired(expire_time: Optional[str]) -> bool:
    """检查是否过期"""
    if not expire_time:
        return False  # 无过期时间 = 永久
    try:
        exp = datetime.strptime(expire_time, "%Y-%m-%d %H:%M:%S")
        return datetime.now() > exp
    except ValueError:
        return False


# ============================================================
# API 验证
# ============================================================
def call_login_api(license_key: str) -> Tuple[bool, str, Optional[str]]:
    """
    调用远程 API 验证卡密
    
    Args:
        license_key: 卡密
        
    Returns:
        (success, message, expire_time)
    """
    machine_code = _get_machine_code()
    data = urllib.parse.urlencode({
        "license_key": license_key,
        "machine_code": machine_code,
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(API_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("User-Agent", "ZhimengAI-Desktop/2.0")
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        
        code = body.get("code", -1)
        msg = body.get("msg", "unknown")
        
        if code == 0:
            expire_time = body.get("expire_time", "")
            _save_local(license_key, expire_time)
            return True, msg, expire_time
        return False, msg, None
        
    except urllib.error.URLError as e:
        return False, f"网络错误: {e.reason}", None
    except Exception as e:
        return False, f"请求失败: {e}", None


# ============================================================
# 公开接口
# ============================================================
def check_saved_license() -> Tuple[str, Dict]:
    """
    检查本地保存的卡密状态
    
    Returns:
        (status, info)
        status: "valid" | "expired" | "none"
        info: 包含license_key, expire_time等信息的字典
    """
    local = _load_local()
    if not local or not local.get("license_key"):
        return "none", {}
    if _is_expired(local.get("expire_time")):
        _clear_local()
        return "expired", local
    return "valid", local


def validate_online(license_key: str) -> Tuple[bool, str]:
    """
    在线验证卡密并保存
    
    Args:
        license_key: 卡密
        
    Returns:
        (success, message)
    """
    ok, msg, _ = call_login_api(license_key)
    if not ok:
        _clear_local()
    return ok, msg


def get_machine_code() -> str:
    """获取机器码"""
    return _get_machine_code()
