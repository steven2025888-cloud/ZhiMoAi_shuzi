import requests
import uuid
import hashlib
from typing import List, Dict
import os

# ============================================================
# 统一API配置 - 所有API请求都使用这个base_url
# ============================================================
API_BASE_URL = "https://api.zhimengai.xyz"

# 从lib_license导入设备码获取函数
try:
    from lib_license import get_machine_code
except ImportError:
    # 如果lib_license不可用，使用简单的备用方案
    def get_machine_code():
        """备用的设备码生成方法"""
        import platform
        parts = [str(uuid.getnode()), platform.node()]
        raw = "|".join(parts)
        return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def safe_json(r: requests.Response):
    try:
        return r.json()
    except Exception:
        raise RuntimeError(
            f"接口返回非JSON: status={r.status_code}, "
            f"content-type={r.headers.get('Content-Type')}, body={r.text[:500]}"
        )

class LicenseApi:
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or API_BASE_URL).rstrip("/")

    def login(self, license_key: str, timeout=10) -> dict:
        url = f"{self.base_url}/api/dsp/license/login"
        payload = {
            "license_key": license_key,
            "machine_code": get_machine_code()
        }

        last_err = None
        for _ in range(2):  # 重试2次
            try:
                r = requests.post(url, json=payload, timeout=timeout)
                return r.json()
            except Exception as e:
                last_err = e

        raise RuntimeError(f"授权服务器连接失败：{last_err}")

class VoiceApiClient:
    def __init__(self, base_url: str = None, license_key: str = ""):
        self.base_url = (base_url or API_BASE_URL).rstrip("/")
        self.license_key = license_key
        self.machine_code = get_machine_code()

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.license_key}",
            "X-Machine-Code": self.machine_code
        }

    # 上传声纹模型
    def upload_model(self, wav_path: str, name: str, describe: str = "") -> Dict:
        url = f"{self.base_url}/api/dsp/voice/model/upload"
        files = {
            "file": ("model.wav", open(wav_path, "rb"), "audio/wav")
        }
        data = {
            "name": name,
            "describe": describe
        }
        r = requests.post(url, headers=self._headers(), files=files, data=data, timeout=60)
        return safe_json(r)

    # 获取模型列表
    def list_models(self) -> List[Dict]:
        url = f"{self.base_url}/api/dsp/voice/model/list"
        r = requests.get(url, headers=self._headers(), timeout=15)
        return safe_json(r)


    # 删除模型
    def delete_model(self, model_id: int):
        url = f"{self.base_url}/api/dsp/voice/model/delete"
        r = requests.post(url, headers=self._headers(), json={"model_id": model_id}, timeout=15)
        return safe_json(r)

    # 创建TTS任务
    def tts(self, model_id: int, text: str) -> Dict:
        url = f"{self.base_url}/api/dsp/voice/tts"
        r = requests.post(url, headers=self._headers(), json={
            "model_id": model_id,
            "text": text
        }, timeout=30)
        return safe_json(r)

    # 查询TTS结果（轮询用）
    def tts_result(self, task_id: str) -> Dict:
        url = f"{self.base_url}/api/dsp/voice/tts/result"
        params = {"taskId": task_id}
        r = requests.get(url, headers=self._headers(), params=params, timeout=10)
        return safe_json(r)
