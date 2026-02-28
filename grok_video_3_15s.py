import os
import logging

from veo_video import GrokVideo3


def main():
    logging.basicConfig(level=logging.INFO)

    api_key = os.getenv("VEO_API_KEY", "")

    if not api_key:
        raise RuntimeError("Missing env VEO_API_KEY")

    prompt = os.getenv("VIDEO_PROMPT", "现代室内装修施工与完工展示场景，适合短视频口播画中画素材，真实家装环境，画面干净高级，空间通透，主体明确，构图简洁，具有短视频B-roll质感，灯光柔和，真实细节丰富，墙面、地砖、吊顶、柜体、灯带层次分明，整体高级感强，生活化但不杂乱，超清，写实风格")
    output_path = os.getenv("OUTPUT_PATH", "grok_video_3_15s.mp4")
    duration = int(os.getenv("VIDEO_DURATION", "15"))  # 从环境变量读取duration，默认15秒

    client = GrokVideo3(api_key=api_key)
    result = client.generate(
        prompt=prompt,
        output_path=output_path,
        duration=duration,  # 使用从环境变量读取的duration
        resolution=os.getenv("VIDEO_RESOLUTION", "720P"),
        poll_interval=int(os.getenv("POLL_INTERVAL", "10")),
        max_wait=int(os.getenv("MAX_WAIT", "1200")),
    )

    print(f"done: task_id={result.task_id} status={result.status.value} url={result.download_url}")


if __name__ == "__main__":
    main()
