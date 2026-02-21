# -*- coding: utf-8 -*-
# lib_license.py — 卡密验证模块

import os, json, time, hashlib, platform, subprocess, uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSE_FILE = os.path.join(BASE_DIR, ".license")
API_URL = "https://api.zhimengai.xyz/api/dsp/login"


def _get_machine_code():
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
    # 3. Windows: 用 wmic 获取主板序列号
    if platform.system() == "Windows":
        try:
            r = subprocess.run(
                ["wmic", "baseboard", "get", "SerialNumber"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for line in r.stdout.strip().splitlines():
                line = line.strip()
                if line and line != "SerialNumber":
                    parts.append(line)
                    break
        except Exception:
            pass
        # 4. CPU ID
        try:
            r = subprocess.run(
                ["wmic", "cpu", "get", "ProcessorId"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for line in r.stdout.strip().splitlines():
                line = line.strip()
                if line and line != "ProcessorId":
                    parts.append(line)
                    break
        except Exception:
            pass

    raw = "|".join(parts) if parts else str(uuid.getnode())
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def _load_local():
    """读取本地保存的卡密信息"""
    if not os.path.exists(LICENSE_FILE):
        return None
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data  # {"license_key": "xxx", "expire_time": "2025-12-31 23:59:59", "login_time": ...}
    except Exception:
        return None


def _save_local(license_key, expire_time):
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
    except Exception as e:
        print(f"[LICENSE] save fail: {e}")


def _clear_local():
    """清除本地卡密"""
    try:
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)
    except Exception:
        pass


def _is_expired(expire_time):
    """检查是否过期"""
    if not expire_time:
        return False  # 无过期时间 = 永久
    try:
        from datetime import datetime
        exp = datetime.strptime(expire_time, "%Y-%m-%d %H:%M:%S")
        return datetime.now() > exp
    except Exception:
        return False


def call_login_api(license_key):
    """调用远程 API 验证卡密, 返回 (success, msg, expire_time)"""
    machine_code = _get_machine_code()
    try:
        import urllib.request
        import urllib.parse
        data = urllib.parse.urlencode({
            "license_key": license_key,
            "machine_code": machine_code,
        }).encode("utf-8")
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
        else:
            return False, msg, None
    except Exception as e:
        return False, f"network error: {e}", None


def check_saved_license():
    """检查本地保存的卡密状态
    返回: (status, info)
      status: "valid" | "expired" | "none"
      info: dict with license_key, expire_time etc.
    """
    local = _load_local()
    if not local or not local.get("license_key"):
        return "none", {}
    if _is_expired(local.get("expire_time")):
        _clear_local()
        return "expired", local
    return "valid", local


def validate_online(license_key):
    """在线验证并保存
    返回: (success: bool, message: str)
    """
    ok, msg, expire = call_login_api(license_key)
    if ok:
        return True, msg
    else:
        _clear_local()
        return False, msg


def get_machine_code():
    """公开接口：获取机器码"""
    return _get_machine_code()
