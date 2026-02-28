"""
Veo 文本生成视频 API 接口封装
接口地址: https://yunwu.ai/v1/video/create
模型: veo3.1-fast-components

使用示例:
  client = VeoVideo(api_key="your_api_key")
  result = client.generate("一只猫在草地上奔跑", output_path="output.mp4")
"""

import time
import logging
import requests
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

BASE_URL = "https://yunwu.ai"


class Model(str, Enum):
    VEO_3_1_FAST = "veo3.1-fast-components"


class TaskStatus(str, Enum):
    PREPARING = "Preparing"
    QUEUEING = "Queueing"
    PROCESSING = "Processing"
    SUCCESS = "Success"
    FAIL = "Fail"


@dataclass
class TaskResult:
    """视频生成任务结果"""
    task_id: str
    status: TaskStatus = TaskStatus.PREPARING
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    error_message: Optional[str] = None


class VeoVideoError(Exception):
    """Veo 视频 API 异常"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


class VeoVideo:
    """
    Veo 文本生成视频客户端

    Args:
        api_key: API Key
        model: 模型名称，默认 veo3.1-fast-components
        timeout: 请求超时时间（秒）
    """

    def __init__(
        self,
        api_key: str,
        model: Model = Model.VEO_3_1_FAST,
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def create_task(
        self,
        prompt: str,
        duration: int = 6,
        resolution: str = "720P",
    ) -> str:
        """
        创建文本生成视频任务

        Args:
            prompt: 视频描述文本
            duration: 视频时长（秒）
            resolution: 视频分辨率

        Returns:
            task_id: 任务 ID
        """
        payload = {
            "model": self.model.value if isinstance(self.model, Model) else self.model,
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
        }

        resp = self._session.post(
            f"{BASE_URL}/v1/video/create",
            json=payload,
            timeout=self.timeout,
        )
        data = resp.json()
        logger.debug("create_task 响应: %s", data)
        self._check_response(data)

        # 兼容多种响应结构
        task_id = (
            data.get("task_id")
            or data.get("taskId")
            or data.get("id")
            or data.get("data", {}).get("task_id")
            or data.get("data", {}).get("taskId")
            or data.get("data", {}).get("id")
        )
        if not task_id:
            raise VeoVideoError(0, f"响应中未找到 task_id，完整响应: {data}")

        logger.info("Veo 视频生成任务已创建: task_id=%s", task_id)
        return task_id

    def query_task(self, task_id: str) -> TaskResult:
        """查询视频生成任务状态 GET /v1/video/query?id=xxx"""
        resp = self._session.get(
            f"{BASE_URL}/v1/video/query",
            params={"id": task_id},
            timeout=self.timeout,
        )
        data = resp.json()
        logger.debug("query_task 响应: %s", data)

        # 查询接口不走 _check_response，因为 failed 状态会带 error 字段
        # 这属于任务状态，不是 API 调用错误
        result = TaskResult(task_id=task_id)

        # 映射状态
        status_map = {
            "queued": TaskStatus.QUEUEING,
            "processing": TaskStatus.PROCESSING,
            "completed": TaskStatus.SUCCESS,
            "success": TaskStatus.SUCCESS,
            "failed": TaskStatus.FAIL,
            "fail": TaskStatus.FAIL,
        }
        raw_status = data.get("status", "").lower()
        result.status = status_map.get(raw_status, TaskStatus.PREPARING)

        result.file_id = data.get("id")
        result.download_url = data.get("video_url")

        # 保存错误信息供调用方使用
        error = data.get("error")
        if error and isinstance(error, dict):
            result.error_message = error.get("message", "")
        else:
            result.error_message = None

        return result

    def download_video(self, url: str, output_path: str) -> str:
        """下载视频到本地文件"""
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("视频已下载: %s", output_path)
        return output_path

    def generate(
        self,
        prompt: str,
        output_path: str = "output.mp4",
        duration: int = 6,
        resolution: str = "720P",
        poll_interval: int = 10,
        max_wait: int = 600,
    ) -> TaskResult:
        """
        一站式文本生成视频：创建任务 -> 轮询等待 -> 下载视频

        Args:
            prompt: 视频描述文本
            output_path: 输出文件路径
            duration: 视频时长（秒）
            resolution: 视频分辨率
            poll_interval: 轮询间隔（秒）
            max_wait: 最大等待时间（秒）

        Returns:
            TaskResult

        Raises:
            VeoVideoError: API 返回错误
            TimeoutError: 超过最大等待时间
        """
        task_id = self.create_task(
            prompt=prompt,
            duration=duration,
            resolution=resolution,
        )

        elapsed = 0
        while elapsed < max_wait:
            result = self.query_task(task_id)
            logger.info("任务 %s 状态: %s", task_id, result.status.value)

            if result.status == TaskStatus.SUCCESS:
                if result.download_url:
                    self.download_video(result.download_url, output_path)
                return result

            if result.status == TaskStatus.FAIL:
                msg = result.error_message or "未知原因"
                raise VeoVideoError(0, f"视频生成失败: {msg} (task_id={task_id})")

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"视频生成超时（{max_wait}s）: task_id={task_id}")

    @staticmethod
    def _check_response(data: dict):
        """检查 API 响应"""
        # 兼容 base_resp 结构
        base_resp = data.get("base_resp", {})
        code = base_resp.get("status_code", 0)
        if code != 0:
            raise VeoVideoError(code, base_resp.get("status_msg", "unknown error"))

        # 兼容 code/message 结构
        code2 = data.get("code", 0)
        if code2 != 0 and code2 != 200:
            raise VeoVideoError(code2, data.get("message") or data.get("msg") or "unknown error")

        # 兼容 error 结构
        error = data.get("error")
        if error:
            if isinstance(error, dict):
                raise VeoVideoError(error.get("code", 0), error.get("message", "unknown error"))
            raise VeoVideoError(0, str(error))


class GrokVideo3(VeoVideo):
    """
    GrokVideo3 - 支持生成15秒视频的Veo客户端
    继承自VeoVideo，专门用于画中画场景
    """

    def __init__(self, api_key: str, timeout: int = 30):
        super().__init__(api_key=api_key, model=Model.VEO_3_1_FAST, timeout=timeout)


# ---- 使用示例 ----
if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.DEBUG)

    API_KEY = os.getenv("VEO_API_KEY", "sk-2IpEFzOUXNeAYTo4rsJ3N47Ix2sd5ARkre0e1MrsqPio4TEN")

    client = VeoVideo(api_key=API_KEY)

    result = client.generate(
        prompt="现代室内装修施工与完工展示场景，适合短视频口播画中画素材，真实家装环境，画面干净高级，空间通透，主体明确，构图简洁，具有短视频B-roll质感，灯光柔和，真实细节丰富，墙面、地砖、吊顶、柜体、灯带层次分明，整体高级感强，生活化但不杂乱，超清，写实风格",
        output_path="cat_running.mp4",
        duration=6,
    )
    print(f"视频生成完成: task_id={result.task_id}, 下载地址={result.download_url}")
