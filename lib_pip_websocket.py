"""
画中画 WebSocket 模块 - 通过 TextExtractor 复用连接生成画中画视频
"""

import os
import time
import json
import queue as _queue

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PIP_VIDEO_DIR = os.path.join(BASE_DIR, "pip_videos")
os.makedirs(PIP_VIDEO_DIR, exist_ok=True)


def _safe_print(msg: str):
    try:
        print(msg, flush=True)
    except Exception:
        pass


def _download_video(url: str, output_path: str, max_retries: int = 3) -> bool:
    """下载视频文件到指定路径"""
    import requests as _req
    for attempt in range(1, max_retries + 1):
        try:
            _safe_print(f"[PIP] 下载视频 第{attempt}/{max_retries}次: {url[:80]}...")
            r = _req.get(url, timeout=(15, 300), stream=True)
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                _safe_print(f"[PIP] 视频下载成功，大小: {os.path.getsize(output_path)} 字节")
                return True
            else:
                raise IOError("下载的文件为空或太小")
        except Exception as e:
            _safe_print(f"[PIP] 第{attempt}次下载失败: {e}")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            if attempt < max_retries:
                time.sleep(attempt * 3)
    return False


def generate_pip_via_extractor(prompt: str, extractor, output_path: str = None,
                               progress_cb=None, timeout: float = 300.0) -> str:
    """
    通过 TextExtractor 的连接生成画中画视频
    :param prompt: 视频生成提示词
    :param extractor: TextExtractor 实例
    :param output_path: 输出路径
    :param progress_cb: 进度回调
    :param timeout: 超时时间
    :return: 本地视频文件路径，失败返回空字符串
    """
    def _prog(pct, msg):
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass

    ts = int(time.time() * 1000)
    out_path = output_path or os.path.join(PIP_VIDEO_DIR, f"pip_chatglm_{ts}.mp4")
    request_id = f"pip_{ts}"

    _prog(0.02, "🎬 正在连接画中画服务...")
    _safe_print(f"[PIP] 发送 chatglm_video 请求: {prompt[:60]}...")

    # 获取卡密
    license_key = extractor._get_license_key()
    if not license_key:
        _safe_print("[PIP] 未找到卡密")
        return ""

    # 通过 TextExtractor 发送请求
    request_data = {
        "type": "chatglm_video",
        "key": license_key,
        "content": prompt,
        "request_id": request_id
    }

    _prog(0.08, "🎬 已提交生成请求，等待服务器处理...")

    # 发送请求并等待响应
    success, result = extractor.send_request(
        request_data,
        timeout=timeout,
        response_type="chatglm_video_result",
        request_id=request_id
    )

    if not success:
        _safe_print(f"[PIP] chatglm_video 失败: {result}")
        return ""

    # 解析响应
    video_url = result.get("video_url", "")
    if not video_url:
        _safe_print("[PIP] chatglm_video 未返回 video_url")
        return ""

    # 处理转义的 URL
    video_url = video_url.replace("\\/", "/")
    _safe_print(f"[PIP] 收到视频URL: {video_url[:80]}...")

    # 下载视频
    _prog(0.88, "⬇️ 下载画中画视频...")
    if _download_video(video_url, out_path):
        _prog(1.0, "✅ 画中画视频生成完成")
        return out_path
    else:
        _safe_print("[PIP] 画中画视频下载失败")
        return ""


def generate_multiple_pips(prompts: list, extractor, progress_cb=None) -> list:
    """
    批量生成多个画中画视频（复用同一连接，快速提交）
    :param prompts: 提示词列表
    :param extractor: TextExtractor 实例
    :param progress_cb: 进度回调
    :return: 生成的视频路径列表
    """
    def _prog(pct, msg):
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass

    if not prompts:
        return []

    _safe_print(f"[PIP] 开始批量生成 {len(prompts)} 个画中画视频...")
    _prog(0.05, f"🎬 快速提交 {len(prompts)} 个生成请求...")

    # 获取卡密
    license_key = extractor._get_license_key()
    if not license_key:
        _safe_print("[PIP] 未找到卡密")
        return []

    # 准备所有任务
    tasks = []
    for i, prompt in enumerate(prompts):
        ts = int(time.time() * 1000) + i
        out_path = os.path.join(PIP_VIDEO_DIR, f"pip_chatglm_{ts}_{i+1}.mp4")
        request_id = f"pip_{ts}_{i+1}"
        tasks.append((i, prompt, out_path, request_id))

    # 快速提交所有请求
    for i, prompt, out_path, request_id in tasks:
        request_data = {
            "type": "chatglm_video",
            "key": license_key,
            "content": prompt,
            "request_id": request_id
        }

        # 发送请求（不等待响应）
        try:
            async def send_msg():
                await extractor._ws.send(json.dumps(request_data))

            if extractor._loop and extractor._loop.is_running():
                import asyncio
                future = asyncio.run_coroutine_threadsafe(send_msg(), extractor._loop)
                future.result(timeout=5)
                _safe_print(f"[PIP] 已提交请求 {i+1}/{len(tasks)}: {prompt[:50]}...")
                time.sleep(0.2)  # 短暂延迟
        except Exception as e:
            _safe_print(f"[PIP] 提交请求 {i+1} 失败: {e}")

    _safe_print(f"[PIP] 所有请求已提交，等待服务器生成...")
    _prog(0.15, f"⏳ 等待服务器生成 {len(tasks)} 个视频...")

    # 等待所有响应（直接从队列读取）
    results = [None] * len(tasks)
    completed = 0
    timeout = 300.0 * len(tasks)
    start_time = time.time()
    request_id_map = {request_id: (i, out_path) for i, _, out_path, request_id in tasks}

    while completed < len(tasks) and time.time() - start_time < timeout:
        try:
            # 从 TextExtractor 的队列中读取消息
            response = extractor._response_queue.get(timeout=2)

            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                _safe_print(f"[PIP] JSON解析失败: {response[:100]}")
                continue

            msg_type = data.get("type", "")

            # 跳过非结果消息
            if msg_type == "ack":
                _safe_print(f"[PIP] 收到 ack")
                continue
            elif msg_type == "pong":
                continue
            elif msg_type == "error":
                _safe_print(f"[PIP] 收到错误: {data.get('message', '')}")
                continue
            elif msg_type == "kicked":
                _safe_print(f"[PIP] 连接被踢出")
                break
            elif msg_type != "chatglm_video_result":
                # 不是我们要的消息，放回队列
                extractor._response_queue.put(response)
                time.sleep(0.5)
                continue

            # 处理 chatglm_video_result
            _safe_print(f"[PIP] 收到视频结果: {response[:200]}...")

            # 尝试通过 request_id 匹配
            resp_request_id = data.get("request_id", "")
            if resp_request_id and resp_request_id in request_id_map:
                i, out_path = request_id_map[resp_request_id]
            else:
                # 如果没有 request_id 或不匹配，按顺序分配
                _safe_print(f"[PIP] 无法通过 request_id 匹配，按顺序分配")
                # 找到第一个未完成的任务
                i = None
                for idx in range(len(tasks)):
                    if results[idx] is None:
                        i = idx
                        out_path = tasks[idx][2]
                        break

                if i is None:
                    _safe_print(f"[PIP] 所有任务已完成，忽略此响应")
                    continue

            # 下载视频
            video_url = data.get("video_url", "").replace("\\/", "/")
            if video_url:
                _safe_print(f"[PIP] 下载第 {i+1} 个视频: {video_url[:80]}...")
                if _download_video(video_url, out_path):
                    results[i] = out_path
                    completed += 1
                    _safe_print(f"[PIP] 第 {i+1} 个视频完成: {out_path}")
                    pct = 0.15 + (completed / len(tasks)) * 0.50
                    _prog(pct, f"✅ 已完成 {completed}/{len(tasks)} 个视频")
                else:
                    _safe_print(f"[PIP] 第 {i+1} 个视频下载失败")
                    results[i] = ""
                    completed += 1
            else:
                _safe_print(f"[PIP] 第 {i+1} 个视频无 URL")
                results[i] = ""
                completed += 1

        except _queue.Empty:
            elapsed = int(time.time() - start_time)
            if elapsed % 30 == 0:
                _safe_print(f"[PIP] 等待中...已完成 {completed}/{len(tasks)}，已等待 {elapsed} 秒")
            continue
        except Exception as e:
            _safe_print(f"[PIP] 处理响应异常: {e}")
            import traceback
            traceback.print_exc()
            continue

    if completed < len(tasks):
        _safe_print(f"[PIP] 超时或中断，仅完成 {completed}/{len(tasks)} 个视频")

    # 过滤掉失败的
    return [r for r in results if r]
