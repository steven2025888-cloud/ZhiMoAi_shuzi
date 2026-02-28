"""
画中画 WebSocket 模块 - 通过 TextExtractor 复用连接生成画中画视频
"""

import os
import time
import json
import queue as _queue
import subprocess
import math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PIP_VIDEO_DIR = os.path.join(BASE_DIR, "pip_videos")
os.makedirs(PIP_VIDEO_DIR, exist_ok=True)
OUTPUT_DIR = os.path.join(BASE_DIR, "unified_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_NWIN = 0x08000000  # CREATE_NO_WINDOW


def _find_exe(name):
    """查找 ffmpeg/ffprobe 可执行文件"""
    heygem_bin = os.path.join(BASE_DIR, "heygem-win-50", "py39", "ffmpeg", "bin", f"{name}.exe")
    if os.path.exists(heygem_bin):
        return heygem_bin

    candidates = [
        os.path.join(BASE_DIR, "ffmpeg_bin", f"{name}.exe"),
        os.path.join(BASE_DIR, "ffmpeg", f"{name}.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p

    import shutil
    return shutil.which(name) or name


_FFMPEG = _find_exe("ffmpeg")
_FFPROBE = _find_exe("ffprobe")


def _safe_print(msg: str):
    try:
        print(msg, flush=True)
    except Exception:
        pass


def get_video_duration(path: str) -> float:
    """获取视频时长（秒）"""
    try:
        r = subprocess.run(
            [_FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, creationflags=_NWIN, timeout=15, errors="replace")
        if r.returncode == 0 and (r.stdout or "").strip():
            return float((r.stdout or "0").strip())
        return 0.0
    except Exception:
        return 0.0


def get_video_resolution(path: str) -> tuple:
    """获取视频分辨率"""
    try:
        r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", str(path)],
            capture_output=True, text=True, creationflags=_NWIN, timeout=15, errors="replace")
        s = json.loads(r.stdout).get("streams", [{}])[0]
        return int(s.get("width", 1280)), int(s.get("height", 720))
    except Exception:
        return 1280, 720


def get_video_fps(path: str) -> float:
    """获取视频帧率"""
    try:
        r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", str(path)],
            capture_output=True, text=True, creationflags=_NWIN, timeout=15, errors="replace")
        s = json.loads(r.stdout).get("streams", [{}])[0]
        fps_str = s.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            n, d = fps_str.split("/")
            return float(n) / float(d) if float(d) else 30.0
        return float(fps_str)
    except Exception:
        return 30.0


def interleave_pip_clips(main_video: str, pip_clips: list, clip_duration: float = 5.0,
                        progress_cb=None) -> str:
    """
    将画中画片段穿插到主视频中
    :param main_video: 主视频路径
    :param pip_clips: 画中画片段路径列表
    :param clip_duration: 每段画中画显示时长（秒）
    :param progress_cb: 进度回调
    :return: 输出视频路径，失败返回空字符串
    """
    def _prog(pct, msg):
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass

    if not main_video or not os.path.exists(main_video):
        return ""
    if not pip_clips:
        return ""

    main_dur = get_video_duration(main_video)
    if main_dur < 5:
        _safe_print("[PIP] 主视频太短，跳过画中画")
        return ""

    main_w, main_h = get_video_resolution(main_video)
    main_fps = get_video_fps(main_video)

    _prog(0.70, "🖼 准备画中画片段...")

    # 计算插入时间点（均匀分布）
    num_clips = len(pip_clips)
    usable_start = 5.0
    usable_end = main_dur - 5.0 - clip_duration
    if usable_end <= usable_start:
        usable_start = 2.0
        usable_end = main_dur - 2.0 - clip_duration

    if num_clips == 1:
        insert_times = [usable_start + (usable_end - usable_start) / 2]
    else:
        gap = (usable_end - usable_start) / (num_clips - 1) if num_clips > 1 else 0
        insert_times = [usable_start + i * gap for i in range(num_clips)]

    _safe_print(f"[PIP] 将在 {len(insert_times)} 个位置插入画中画")
    _prog(0.75, f"🎬 将插入 {len(insert_times)} 段画中画...")

    # 构建 ffmpeg 复杂滤镜
    ts = int(time.time())
    out_path = os.path.join(OUTPUT_DIR, f"pip_final_{ts}.mp4")

    # 构建输入和滤镜
    inputs = ["-i", str(main_video)]
    for i, (start, clip_path) in enumerate(zip(insert_times, pip_clips)):
        inputs.extend(["-itsoffset", f"{start:.2f}", "-i", str(clip_path)])

    # 构建滤镜链
    filter_parts = []
    prev = "[0:v]"
    for i, (start, clip_path) in enumerate(zip(insert_times, pip_clips)):
        inp_idx = i + 1
        end = start + clip_duration
        # 缩放 pip 片段到主视频尺寸
        filter_parts.append(
            f"[{inp_idx}:v]scale={main_w}:{main_h}:force_original_aspect_ratio=decrease,"
            f"pad={main_w}:{main_h}:(ow-iw)/2:(oh-ih)/2:black,fps={main_fps}[pip{i}]"
        )
        out_label = f"[v{i}]"
        filter_parts.append(
            f"{prev}[pip{i}]overlay=0:0:enable='between(t,{start:.2f},{end:.2f})':eof_action=pass{out_label}"
        )
        prev = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        _FFMPEG, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", prev,
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        out_path
    ]

    _prog(0.80, "🎬 合成画中画视频...")

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=_NWIN, text=True, errors="replace")
        _, stderr = proc.communicate(timeout=600)

        if proc.returncode != 0:
            _safe_print(f"[PIP] ffmpeg 合成失败: {stderr[-500:]}")
            return ""

        if not os.path.exists(out_path):
            return ""

        _prog(0.95, "✅ 画中画合成完成")
        return out_path

    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        _safe_print("[PIP] 画中画合成超时")
        return ""
    except Exception as e:
        _safe_print(f"[PIP] 画中画合成异常: {e}")
        import traceback
        traceback.print_exc()
        return ""


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


def generate_and_compose_pips(main_video: str, prompts: list, extractor,
                             clip_duration: float = 5.0, progress_cb=None) -> str:
    """
    批量生成多个画中画视频并合成到主视频中
    :param main_video: 主视频路径
    :param prompts: 提示词列表
    :param extractor: TextExtractor 实例
    :param clip_duration: 每段画中画显示时长
    :param progress_cb: 进度回调
    :return: 合成后的视频路径，失败返回空字符串
    """
    def _prog(pct, msg):
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass

    if not prompts:
        return ""

    # 获取主视频时长，计算应该生成的画中画数量
    main_dur = get_video_duration(main_video)
    if main_dur < 10:
        _safe_print(f"[PIP] 主视频太短({main_dur:.1f}s)，跳过画中画")
        return ""

    # 每30秒生成1个画中画
    max_pip = max(1, int(math.ceil(main_dur / 30.0)))
    max_pip = min(max_pip, 6)  # 最多6个

    # 取AI给出的提示词数量和最大数量中的较小值
    num_pip = min(len(prompts), max_pip)
    selected_prompts = prompts[:num_pip]

    _safe_print(f"[PIP-SMART] 主视频 {main_dur:.1f}s，最多 {max_pip} 个PiP，AI提供 {len(prompts)} 个提示词，实际使用 {num_pip} 个")
    _prog(0.05, f"🎬 快速提交 {num_pip} 个生成请求...")

    # 获取卡密
    license_key = extractor._get_license_key()
    if not license_key:
        _safe_print("[PIP] 未找到卡密")
        return ""

    # 准备所有任务
    tasks = []
    for i, prompt in enumerate(selected_prompts):
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
    clips = [r for r in results if r]

    if not clips:
        _safe_print("[PIP] 没有成功生成任何画中画片段")
        return ""

    _safe_print(f"[PIP] 成功生成 {len(clips)} 个画中画视频，开始合成...")

    # 合成到主视频
    final_video = interleave_pip_clips(
        main_video,
        clips,
        clip_duration=clip_duration,
        progress_cb=progress_cb
    )

    if final_video:
        _safe_print(f"[PIP] 画中画合成完成: {final_video}")
        _safe_print(f"[PIP] 画中画视频已保留在 {PIP_VIDEO_DIR}")
    else:
        _safe_print("[PIP] 画中画合成失败")

    return final_video
