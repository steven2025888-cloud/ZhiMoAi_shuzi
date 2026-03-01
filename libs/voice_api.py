# -*- coding: utf-8 -*-
"""
voice_api.py - API客户端模块

提供授权验证和语音服务的API调用。
"""

import hashlib
import platform
import uuid
from typing import Any, Dict, List, Optional

import requests

# ============================================================
# 统一API配置
# ============================================================
API_BASE_URL = "https://api.zhimengai.xyz"
DEFAULT_TIMEOUT = 15


# ============================================================
# 设备码获取
# ============================================================
try:
    from lib_license import get_machine_code
except ImportError:
    def get_machine_code() -> str:
        """备用的设备码生成方法"""
        parts = [str(uuid.getnode()), platform.node()]
        raw = "|".join(parts)
        return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()



# ============================================================
# 工具函数
# ============================================================
def safe_json(response: requests.Response) -> Dict[str, Any]:
    """
    安全解析JSON响应
    
    Args:
        response: requests响应对象
        
    Returns:
        解析后的JSON字典
        
    Raises:
        RuntimeError: 当响应不是有效JSON时
    """
    try:
        return response.json()
    except ValueError:
        raise RuntimeError(
            f"接口返回非JSON: status={response.status_code}, "
            f"content-type={response.headers.get('Content-Type')}, "
            f"body={response.text[:500]}"
        )


# ============================================================
# 授权API客户端
# ============================================================
class LicenseApi:
    """授权验证API客户端"""
    
    MAX_RETRIES = 2
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or API_BASE_URL).rstrip("/")

    def login(self, license_key: str, timeout: int = 10) -> Dict[str, Any]:
        """
        登录验证
        
        Args:
            license_key: 授权密钥
            timeout: 请求超时时间
            
        Returns:
            API响应字典
        """
        url = f"{self.base_url}/api/dsp/license/login"
        payload = {
            "license_key": license_key,
            "machine_code": get_machine_code()
        }

        last_error: Optional[Exception] = None
        for _ in range(self.MAX_RETRIES):
            try:
                response = requests.post(url, json=payload, timeout=timeout)
                return response.json()
            except (requests.RequestException, ValueError) as e:
                last_error = e

        raise RuntimeError(f"授权服务器连接失败: {last_error}")

# ============================================================
# 语音服务API客户端
# ============================================================
class VoiceApiClient:
    """语音服务API客户端"""
    
    def __init__(self, base_url: Optional[str] = None, license_key: str = ""):
        """
        初始化客户端
        
        Args:
            base_url: API基础URL
            license_key: 授权密钥
        """
        self.base_url = (base_url or API_BASE_URL).rstrip("/")
        self.license_key = license_key
        self.machine_code = get_machine_code()

    def _headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.license_key}",
            "X-Machine-Code": self.machine_code
        }

    def upload_model(self, wav_path: str, name: str, describe: str = "") -> Dict[str, Any]:
        """
        上传声纹模型
        
        Args:
            wav_path: WAV文件路径
            name: 模型名称
            describe: 模型描述
            
        Returns:
            API响应
        """
        url = f"{self.base_url}/api/dsp/voice/model/upload"
        with open(wav_path, "rb") as f:
            files = {"file": ("model.wav", f, "audio/wav")}
            data = {"name": name, "describe": describe}
            response = requests.post(
                url, 
                headers=self._headers(), 
                files=files, 
                data=data, 
                timeout=60
            )
        return safe_json(response)

    def list_models(self) -> Dict[str, Any]:
        """获取模型列表"""
        url = f"{self.base_url}/api/dsp/voice/model/list"
        response = requests.get(url, headers=self._headers(), timeout=DEFAULT_TIMEOUT)
        return safe_json(response)

    def delete_model(self, model_id: int) -> Dict[str, Any]:
        """
        删除模型
        
        Args:
            model_id: 模型ID
        """
        url = f"{self.base_url}/api/dsp/voice/model/delete"
        response = requests.post(
            url, 
            headers=self._headers(), 
            json={"model_id": model_id}, 
            timeout=DEFAULT_TIMEOUT
        )
        return safe_json(response)

    def tts(self, model_id: int, text: str) -> Dict[str, Any]:
        """
        创建TTS任务
        
        Args:
            model_id: 模型ID
            text: 要合成的文本
            
        Returns:
            包含任务ID的响应
        """
        url = f"{self.base_url}/api/dsp/voice/tts"
        response = requests.post(
            url, 
            headers=self._headers(), 
            json={"model_id": model_id, "text": text}, 
            timeout=300
        )
        return safe_json(response)

    def tts_result(self, task_id: str) -> Dict[str, Any]:
        """
        查询TTS任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态和结果
        """
        url = f"{self.base_url}/api/dsp/voice/tts/result"
        response = requests.get(
            url, 
            headers=self._headers(), 
            params={"taskId": task_id}, 
            timeout=60
        )
        return safe_json(response)
