# -*- coding: utf-8 -*-
# lib_pip.py — 画中画（Picture-in-Picture）核心逻辑
#
# 功能：根据文案中的关键词，从"画中画"文件夹中匹配对应素材视频，
#       按音频时间戳精确替换主视频的对应帧段。

import os, sys, re, json, time, random, subprocess, shutil
from itertools import combinations

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)  # 项目根目录
PIP_DIR  = os.path.join(ROOT_DIR, "pip_videos")
os.makedirs(PIP_DIR, exist_ok=True)

HEYGEM_DIR = os.path.join(ROOT_DIR, "heygem-win-50")
HEYGEM_FFMPEG = os.path.join(HEYGEM_DIR, "py39", "ffmpeg", "bin")
_FFMPEG  = shutil.which("ffmpeg")  or "ffmpeg"
_FFPROBE = shutil.which("ffprobe") or "ffprobe"
_HEYGEM_FFMPEG_EXE = os.path.join(HEYGEM_FFMPEG, "ffmpeg.exe")
_HEYGEM_FFPROBE_EXE = os.path.join(HEYGEM_FFMPEG, "ffprobe.exe")
if os.path.exists(_HEYGEM_FFMPEG_EXE):
    _FFMPEG = _HEYGEM_FFMPEG_EXE
if os.path.exists(_HEYGEM_FFPROBE_EXE):
    _FFPROBE = _HEYGEM_FFPROBE_EXE

OUTPUT_DIR = os.path.join(ROOT_DIR, "unified_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_WIN  = sys.platform == "win32"
_NWIN = subprocess.CREATE_NO_WINDOW if _WIN else 0

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}

# ═══════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════

def _safe_print(msg: str):
    try:
        sys.stdout.write(msg + "\n"); sys.stdout.flush()
    except Exception:
        try:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
        except Exception:
            pass


def get_video_duration(path: str) -> float:
    """用 ffprobe 获取视频时长（秒）"""
    try:
        # 检查文件是否存在
        if not os.path.exists(path):
            _safe_print(f"[PIP] 获取时长失败: 文件不存在 {path}")
            return 0.0

        # 检查 ffprobe 是否存在
        if not os.path.exists(_FFPROBE):
            _safe_print(f"[PIP] ffprobe 不存在: {_FFPROBE}")
            _safe_print(f"[PIP] 当前工作目录: {os.getcwd()}")
            _safe_print(f"[PIP] ROOT_DIR: {ROOT_DIR}")
            return 0.0

        # 打印文件信息
        file_size = os.path.getsize(path)
        _safe_print(f"[PIP] 获取视频时长: {path} (大小: {file_size} 字节)")

        r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_format", str(path)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            creationflags=_NWIN, timeout=15)

        if r.returncode != 0:
            _safe_print(f"[PIP] ffprobe 返回错误码 {r.returncode}")
            if r.stderr:
                _safe_print(f"[PIP] ffprobe 错误: {r.stderr[:200]}")
            return 0.0

        duration = float(json.loads(r.stdout).get("format", {}).get("duration", 0))
        _safe_print(f"[PIP] 视频时长: {duration:.2f}s")
        return duration

    except FileNotFoundError as e:
        _safe_print(f"[PIP] 获取视频时长异常: {e}")
        _safe_print(f"[PIP] ffprobe 路径: {_FFPROBE}")
        _safe_print(f"[PIP] ffprobe 存在: {os.path.exists(_FFPROBE)}")
        return 0.0
    except Exception as e:
        _safe_print(f"[PIP] 获取视频时长异常: {e}")
        import traceback
        _safe_print(f"[PIP] 详细错误: {traceback.format_exc()}")
        return 0.0


def get_video_resolution(path: str):
    """获取视频分辨率 (width, height)"""
    try:
        r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", str(path)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            creationflags=_NWIN, timeout=15)
        streams = json.loads(r.stdout).get("streams", [])
        if streams:
            return int(streams[0].get("width", 1280)), int(streams[0].get("height", 720))
    except Exception:
        pass
    return 1280, 720


# ═══════════════════════════════════════════════
# 文本分句 + 计时
# ═══════════════════════════════════════════════

def _split_into_sentences(words):
    """
    将 word-level timestamp 列表按标点分句。
    words: [{"word": str, "start": float, "end": float}, ...]
    返回: [(sentence_text, start_sec, end_sec), ...]
    """
    sentence_ends = {'。', '！', '？', '.', '!', '?', '；', ';', '，', ',', '、'}
    sentences = []
    current = []

    for i, w in enumerate(words):
        word_text = w["word"].strip()
        if not word_text:
            continue
        current.append(w)

        has_punct = any(p in word_text for p in sentence_ends)
        is_last = (i == len(words) - 1)
        is_long = len(current) >= 20

        if has_punct or is_last or is_long:
            if current:
                text = "".join(ww["word"].strip() for ww in current)
                start = current[0]["start"]
                end   = current[-1]["end"]
                sentences.append((text, float(start), float(end)))
                current = []

    if current:
        text = "".join(ww["word"].strip() for ww in current)
        start = current[0]["start"]
        end   = current[-1]["end"]
        sentences.append((text, float(start), float(end)))

    return sentences


def find_keyword_time_in_words(words, keyword):
    """
    在 word-level 时间戳中精确定位关键词的所有出现位置。
    不依赖分句，直接在拼接后的完整文本中查找关键词，
    并映射回对应 word 的时间戳。

    words:   [{"word": str, "start": float, "end": float}, ...]
    keyword: 要查找的关键词字符串

    返回: [(kw_start_time, kw_end_time), ...]  按时间顺序
    """
    if not words or not keyword:
        return []

    # 拼接所有 word 文本，记录每个字符对应的 word 索引
    full_text = ""
    char_to_word = []
    for wi, w in enumerate(words):
        wt = w.get("word", "").strip()
        for c in wt:
            char_to_word.append(wi)
            full_text += c

    if not full_text:
        return []

    results = []
    search_from = 0
    while True:
        pos = full_text.find(keyword, search_from)
        if pos == -1:
            break
        end_pos = pos + len(keyword) - 1
        if end_pos < len(char_to_word):
            start_wi = char_to_word[pos]
            end_wi   = char_to_word[end_pos]
            results.append((float(words[start_wi]["start"]),
                            float(words[end_wi]["end"])))
        search_from = pos + 1

    return results


# ═══════════════════════════════════════════════
# 关键词匹配
# ═══════════════════════════════════════════════

def scan_pip_keywords():
    """扫描画中画文件夹下的所有子文件夹名，返回 {关键词: 文件夹路径}"""
    result = {}
    if not os.path.exists(PIP_DIR):
        return result
    for name in os.listdir(PIP_DIR):
        full = os.path.join(PIP_DIR, name)
        if os.path.isdir(full) and name.strip():
            result[name.strip()] = full
    return result


def scan_pip_videos(folder_path: str):
    """扫描文件夹中的所有视频文件，返回 [(path, duration_sec), ...]"""
    videos = []
    if not os.path.exists(folder_path):
        return videos
    for f in os.listdir(folder_path):
        ext = os.path.splitext(f)[1].lower()
        if ext in VIDEO_EXTS:
            full = os.path.join(folder_path, f)
            dur = get_video_duration(full)
            if dur > 0:
                videos.append((full, dur))
    return videos


def match_keywords_to_sentences(sentences, keywords_map):
    """
    对每个句子匹配关键词。
    sentences:    [(text, start, end), ...]
    keywords_map: {keyword: folder_path, ...}
    返回: [(keyword, folder_path, start, end, text), ...]
      → 每个匹配条目包含：关键词、文件夹路径、合并后的起止时间、合并文本
    """
    matches = []

    for kw, folder in keywords_map.items():
        # 找出包含此关键词的所有句子索引
        matched_indices = []
        for i, (text, start, end) in enumerate(sentences):
            if kw in text:
                matched_indices.append(i)

        if not matched_indices:
            continue

        # 对连续匹配的句子进行分组
        groups = []
        current_group = [matched_indices[0]]
        for idx in matched_indices[1:]:
            if idx == current_group[-1] + 1:
                current_group.append(idx)
            else:
                groups.append(current_group)
                current_group = [idx]
        groups.append(current_group)

        # 不再做"最小3秒"向前扩展，直接返回原始句子时间范围
        # 画中画窗口时长由素材视频时长决定，在 apply_pip 中计算
        for group in groups:
            g_start = sentences[group[0]][1]
            g_end   = sentences[group[-1]][2]
            g_text  = "".join(sentences[i][0] for i in group)
            matches.append((kw, folder, g_start, g_end, g_text))

    # 按起始时间排序并合并重叠区间
    matches.sort(key=lambda x: x[2])
    merged = []
    for m in matches:
        if merged and m[2] < merged[-1][3]:
            # 重叠 → 取较长的那个
            prev = merged[-1]
            if (m[3] - m[2]) > (prev[3] - prev[2]):
                merged[-1] = m
        else:
            merged.append(m)

    return merged


# ═══════════════════════════════════════════════
# PIP 素材选取算法
# ═══════════════════════════════════════════════

def select_pip_clips(available_videos, target_duration, tolerance=0.3):
    """
    从 available_videos 中选取视频片段，使总时长恰好等于 target_duration。

    available_videos: [(path, duration), ...]
    target_duration:  目标总时长（秒）
    tolerance:        精确匹配容差（秒）

    返回: [(path, use_duration), ...]  其中 use_duration 可能截断最后一个
    """
    if not available_videos or target_duration <= 0:
        return []

    durations = [(p, d) for p, d in available_videos if d > 0]
    if not durations:
        return []

    target = target_duration

    # 策略1：尝试精确组合（子集和 ≈ target）
    # 限制组合搜索规模：最多尝试 3 个视频的组合
    best_combo = None
    best_diff  = float("inf")

    for r in range(1, min(len(durations) + 1, 4)):
        for combo in combinations(range(len(durations)), r):
            total = sum(durations[i][1] for i in combo)
            diff  = abs(total - target)
            if diff < best_diff:
                best_diff  = diff
                best_combo = combo
            if diff <= tolerance:
                break
        if best_diff <= tolerance:
            break

    # 策略1 命中：精确匹配
    if best_combo is not None and best_diff <= tolerance:
        clips = [durations[i] for i in best_combo]
        random.shuffle(clips)
        result = []
        remaining = target
        for i, (p, d) in enumerate(clips):
            if i == len(clips) - 1:
                result.append((p, remaining))
            else:
                use = min(d, remaining)
                result.append((p, use))
                remaining -= use
        return result

    # 策略2：选取总时长 >= target 的最小组合，截断最后一个
    best_combo2 = None
    best_total2 = float("inf")

    for r in range(1, min(len(durations) + 1, 4)):
        for combo in combinations(range(len(durations)), r):
            total = sum(durations[i][1] for i in combo)
            if total >= target and total < best_total2:
                best_total2 = total
                best_combo2 = combo

    if best_combo2 is not None:
        clips = [durations[i] for i in best_combo2]
        random.shuffle(clips)
        result = []
        remaining = target
        for i, (p, d) in enumerate(clips):
            use = min(d, remaining)
            result.append((p, use))
            remaining -= use
            if remaining <= 0:
                break
        return result

    # 策略3：只有一个视频也比目标短 → 直接截断到 target 或用完整视频
    if durations:
        # 选最长的那个截断
        longest = max(durations, key=lambda x: x[1])
        return [(longest[0], min(longest[1], target))]

    return []


# ═══════════════════════════════════════════════
# PIP 视频拼接与叠加
# ═══════════════════════════════════════════════

def _concat_clips(clips, target_w, target_h, output_path):
    """
    将多个 PIP 片段拼接成一个连续视频，缩放到目标分辨率。
    clips: [(path, use_duration), ...]
    返回: output_path
    """
    if not clips:
        return None

    # 单个片段：直接裁剪+缩放
    if len(clips) == 1:
        p, dur = clips[0]
        cmd = [
            _FFMPEG, "-y",
            "-i", p,
            "-t", f"{dur:.3f}",
            "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                   f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
            "-an",  # 去掉 PIP 素材的音轨
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  creationflags=_NWIN, timeout=120)
            if proc.returncode == 0 and os.path.exists(output_path):
                return output_path
        except Exception as e:
            _safe_print(f"[PIP] 单片段处理失败: {e}")
        return None

    # 多个片段：先分别裁剪+缩放，再 concat
    ts = int(time.time() * 1000)
    tmp_dir = os.path.join(OUTPUT_DIR, f"_pip_tmp_{ts}")
    os.makedirs(tmp_dir, exist_ok=True)

    segment_files = []
    try:
        for i, (p, dur) in enumerate(clips):
            seg_out = os.path.join(tmp_dir, f"seg_{i}.mp4")
            cmd = [
                _FFMPEG, "-y",
                "-i", p,
                "-t", f"{dur:.3f}",
                "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                       f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
                "-an",
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-pix_fmt", "yuv420p",
                seg_out
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  creationflags=_NWIN, timeout=120)
            if proc.returncode != 0 or not os.path.exists(seg_out):
                _safe_print(f"[PIP] 片段 {i} 处理失败")
                continue
            segment_files.append(seg_out)

        if not segment_files:
            return None

        # 写 concat 列表文件
        concat_list = os.path.join(tmp_dir, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for sf in segment_files:
                # ffmpeg concat 要求路径中的单引号和反斜杠转义
                safe = sf.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{safe}'\n")

        cmd = [
            _FFMPEG, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              creationflags=_NWIN, timeout=120)
        if proc.returncode == 0 and os.path.exists(output_path):
            return output_path
        return None
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def _overlay_pip_segments(main_video, pip_segments, output_path):
    """
    将多个 PIP 片段叠加到主视频上。
    main_video: 主视频路径
    pip_segments: [(pip_video_path, start_sec, end_sec), ...]
      → pip_video_path 已经是拼接好的、时长恰好 == (end-start) 的视频
    output_path: 输出路径

    实现：使用 ffmpeg 的多输入 overlay 滤镜，每个 PIP 片段在对应时间段
    完全覆盖主视频画面（全屏替换，不是小窗口）。
    """
    if not pip_segments:
        shutil.copy2(main_video, output_path)
        return output_path

    # 构建 ffmpeg 命令
    inputs = ["-i", main_video]
    for pip_path, _, _ in pip_segments:
        inputs += ["-i", pip_path]

    # 构建滤镜链
    # [0:v] 是主视频，[1:v], [2:v], ... 是各个 PIP 片段
    filter_parts = []
    current_label = "[0:v]"

    for i, (pip_path, start, end) in enumerate(pip_segments):
        input_idx = i + 1
        out_label = f"[v{i}]" if i < len(pip_segments) - 1 else "[vout]"

        # setpts 让 PIP 视频从 0 开始播放，overlay 在 enable 的时间段内全屏覆盖
        # PIP 素材需要在 start 时刻开始显示，所以用 setpts=PTS+{start}/TB 来偏移
        filter_parts.append(
            f"[{input_idx}:v]setpts=PTS+{start:.3f}/TB[pip{i}];"
            f"{current_label}[pip{i}]overlay=0:0:"
            f"enable='between(t,{start:.3f},{end:.3f})'"
            f"{out_label}"
        )
        current_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [_FFMPEG, "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "0:a?",  # 保留主视频音轨（如果有）
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]

    _safe_print(f"[PIP] 执行 overlay 命令，共 {len(pip_segments)} 个片段")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              creationflags=_NWIN, timeout=600,
                              encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            _safe_print(f"[PIP] overlay 失败: {proc.stderr[-500:]}")
            return None
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        _safe_print(f"[PIP] overlay 异常: {e}")
    return None


# ═══════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════

def apply_pip(main_video, audio_path, text, progress_cb=None):
    """
    画中画主函数。

    main_video:  主视频路径（已合成的数字人视频）
    audio_path:  音频路径（用于 Whisper 转录获取时间戳）
    text:        文案原文
    progress_cb: 可选进度回调 (pct:float, msg:str)

    返回: pip_video_path 或 None（无匹配时返回 None）
    """
    def _prog(pct, msg):
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass
        _safe_print(f"[PIP] {msg}")

    if not main_video or not os.path.exists(main_video):
        _safe_print("[PIP] 主视频不存在")
        return None

    if not text or not text.strip():
        _safe_print("[PIP] 文案为空，跳过画中画")
        return None

    # 1. 扫描画中画关键词文件夹
    _prog(0.05, "扫描画中画素材库...")
    keywords_map = scan_pip_keywords()
    if not keywords_map:
        _safe_print("[PIP] 画中画文件夹为空，跳过")
        return None

    _safe_print(f"[PIP] 发现关键词文件夹: {list(keywords_map.keys())}")

    # 先快速检查文案中是否包含任何关键词
    has_match = any(kw in text for kw in keywords_map)
    if not has_match:
        _safe_print("[PIP] 文案中不包含任何关键词，跳过")
        return None

    # 2. 获取音频时间戳
    _prog(0.15, "识别音频时间戳...")
    try:
        from lib_subtitle import transcribe, _text_to_words, _get_duration
    except Exception as e:
        _safe_print(f"[PIP] 导入 lib_subtitle 失败: {e}")
        return None

    whisper_ok = False
    try:
        src_audio = audio_path if (audio_path and os.path.exists(str(audio_path))) else main_video
        _safe_print(f"[PIP] 音频来源: {src_audio}")
        words = transcribe(str(src_audio))
        if words:
            whisper_ok = True
            _safe_print(f"[PIP] Whisper 转录成功，得到 {len(words)} 个词")
            # 打印前几个词帮助调试
            sample = [w["word"] for w in words[:20]]
            _safe_print(f"[PIP] Whisper 前20词: {''.join(sample)}")
        else:
            _safe_print("[PIP] Whisper 转录返回空结果")
    except Exception as e:
        _safe_print(f"[PIP] Whisper 转录异常（将使用原始文案）: {e}")
        words = None

    # 如果 Whisper 不可用，直接使用原始文案生成均匀时间戳
    if not words:
        _safe_print("[PIP] 使用原始文案生成时间戳")
        try:
            dur = _get_duration(main_video)
            words = _text_to_words(text, dur)
            _safe_print(f"[PIP] 文案生成 {len(words)} 个词，视频时长 {dur:.1f}s")
        except Exception as e:
            _safe_print(f"[PIP] 生成文案时间戳失败: {e}")
            return None

    if not words:
        _safe_print("[PIP] 无法获取时间戳")
        return None

    # 3. 精确定位关键词在音频时间轴中的位置（词级别，不依赖分句）
    _prog(0.30, "定位关键词时间戳...")
    _safe_print(f"[PIP] 待匹配关键词: {list(keywords_map.keys())}")

    full_words_text = "".join(w.get("word", "").strip() for w in words)
    _safe_print(f"[PIP] 音频识别文本: {full_words_text[:80]}...")

    matches = []  # [(kw, folder, kw_end_time, context_text), ...]
    for kw, folder in keywords_map.items():
        positions = find_keyword_time_in_words(words, kw)
        for kw_start_t, kw_end_t in positions:
            pos = full_words_text.find(kw)
            ctx_s = max(0, pos - 5) if pos >= 0 else 0
            ctx_e = min(len(full_words_text), pos + len(kw) + 10) if pos >= 0 else 0
            context = full_words_text[ctx_s:ctx_e] if ctx_e > ctx_s else kw
            matches.append((kw, folder, kw_end_t, context))
            _safe_print(f"[PIP] 定位到关键词「{kw}」: {kw_start_t:.1f}s-{kw_end_t:.1f}s 上下文: ...{context}...")

    # 如果 Whisper 转录文本中未定位到关键词，回退到用原始文案
    if not matches and whisper_ok:
        _safe_print("[PIP] Whisper 文本中未定位到关键词，尝试用原始文案定位...")
        try:
            dur = _get_duration(main_video)
            fallback_words = _text_to_words(text, dur)
            if fallback_words:
                for kw, folder in keywords_map.items():
                    positions = find_keyword_time_in_words(fallback_words, kw)
                    for kw_start_t, kw_end_t in positions:
                        matches.append((kw, folder, kw_end_t, kw))
                        _safe_print(f"[PIP] 原始文案定位到「{kw}」: {kw_start_t:.1f}s-{kw_end_t:.1f}s")
                if matches:
                    _safe_print(f"[PIP] 原始文案回退定位成功")
                else:
                    _safe_print("[PIP] 原始文案回退定位也失败")
        except Exception as e:
            _safe_print(f"[PIP] 原始文案回退定位失败: {e}")
            import traceback; traceback.print_exc()

    if not matches:
        _safe_print("[PIP] 没有定位到任何关键词")
        return None

    # 按时间排序，合并过近的匹配（2秒内视为同一位置）
    matches.sort(key=lambda x: x[2])
    merged_matches = []
    for m in matches:
        if merged_matches and m[2] - merged_matches[-1][2] < 2.0:
            if len(m[0]) > len(merged_matches[-1][0]):
                merged_matches[-1] = m
        else:
            merged_matches.append(m)
    matches = merged_matches

    _safe_print(f"[PIP] 最终定位 {len(matches)} 个画中画位置:")
    for kw, folder, kw_end_t, ctx in matches:
        _safe_print(f"  关键词「{kw}」→ 画中画从 {kw_end_t:.1f}s 开始")

    # 5. 获取主视频分辨率和时长
    target_w, target_h = get_video_resolution(main_video)
    main_dur = get_video_duration(main_video)

    # 6. 为每个匹配构建 PIP 片段
    _prog(0.50, "选取画中画素材...")
    pip_segments = []  # [(pip_concat_video, start, end), ...]
    ts = int(time.time())

    for idx, (kw, folder, kw_end_t, ctx) in enumerate(matches):
        _safe_print(f"[PIP] 处理片段 {idx+1}: 关键词「{kw}」 画中画起点={kw_end_t:.1f}s")

        # 扫描该关键词文件夹中的视频
        videos = scan_pip_videos(folder)
        if not videos:
            _safe_print(f"[PIP] 关键词「{kw}」文件夹内无视频，跳过")
            continue

        _safe_print(f"[PIP] 可用素材: {[(os.path.basename(p), f'{d:.1f}s') for p,d in videos]}")

        # 计算画中画素材总可用时长
        total_pip_avail = sum(d for _, d in videos)

        # 画中画从关键词结束时刻开始，持续时长为素材视频时长
        remaining = main_dur - kw_end_t
        if remaining < 1.0:
            _safe_print(f"[PIP] 关键词「{kw}」后剩余时间不足 ({remaining:.1f}s)，跳过")
            continue

        target_dur = min(total_pip_avail, remaining)
        pip_start = kw_end_t
        pip_end = kw_end_t + target_dur
        _safe_print(f"[PIP] 画中画窗口: {pip_start:.1f}s - {pip_end:.1f}s ({target_dur:.1f}s)")

        # 选取合适的片段组合
        clips = select_pip_clips(videos, target_dur)
        if not clips:
            _safe_print(f"[PIP] 无法为关键词「{kw}」找到合适的素材组合，跳过")
            continue

        total_use = sum(d for _, d in clips)
        _safe_print(f"[PIP] 选取: {[(os.path.basename(p), f'{d:.1f}s') for p,d in clips]}  总时长={total_use:.1f}s")

        # 拼接成一个视频
        concat_out = os.path.join(OUTPUT_DIR, f"_pip_seg_{ts}_{idx}.mp4")
        result = _concat_clips(clips, target_w, target_h, concat_out)
        if result:
            pip_segments.append((result, pip_start, pip_end))
        else:
            _safe_print(f"[PIP] 片段 {idx+1} 拼接失败")

    if not pip_segments:
        _safe_print("[PIP] 所有片段处理失败，跳过画中画")
        return None

    # 7. 叠加到主视频
    pct_base = 0.70
    _prog(pct_base, f"合成画中画视频（{len(pip_segments)} 个片段）...")

    out_path = os.path.join(OUTPUT_DIR, f"pip_{ts}.mp4")
    result = _overlay_pip_segments(main_video, pip_segments, out_path)

    # 清理临时 PIP 片段文件
    for seg_path, _, _ in pip_segments:
        try:
            if os.path.exists(seg_path):
                os.remove(seg_path)
        except Exception:
            pass

    if result and os.path.exists(result):
        _prog(1.0, "✅ 画中画合成完成")
        return result
    else:
        _safe_print("[PIP] 最终合成失败")
        return None


# ═══════════════════════════════════════════════
# 本地素材画中画
# ═══════════════════════════════════════════════

def apply_pip_local(main_video, local_paths, interval=15.0, clip_duration=5.0,
                    progress_cb=None):
    """
    将用户上传的本地视频素材按固定间隔叠加到主视频上。

    main_video:    主视频路径
    local_paths:   本地素材视频路径列表
    interval:      每隔多少秒插入一个画中画（秒）
    clip_duration: 每个画中画片段显示时长（秒）
    progress_cb:   可选进度回调 (pct:float, msg:str)

    返回: 合成后的视频路径，失败返回 None
    """
    def _prog(pct, msg):
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass
        _safe_print(f"[PIP-LOCAL] {msg}")

    if not main_video or not os.path.exists(main_video):
        _safe_print("[PIP-LOCAL] 主视频不存在")
        return None

    if not local_paths:
        _safe_print("[PIP-LOCAL] 无本地素材")
        return None

    # 过滤有效文件
    valid_paths = [p for p in local_paths if p and os.path.exists(p)]
    if not valid_paths:
        _safe_print("[PIP-LOCAL] 无有效本地素材文件")
        return None

    _prog(0.05, "读取视频信息...")
    main_dur = get_video_duration(main_video)
    target_w, target_h = get_video_resolution(main_video)

    if main_dur < 2.0:
        _safe_print(f"[PIP-LOCAL] 主视频太短 ({main_dur:.1f}s)，跳过")
        return None

    # 计算插入时间点
    interval = max(5.0, float(interval))
    clip_duration = max(1.0, float(clip_duration))
    insert_times = []
    t = interval
    while t + clip_duration <= main_dur:
        insert_times.append(t)
        t += interval + clip_duration  # 下一个插入点 = 当前结束 + 间隔

    if not insert_times:
        # 至少在视频中段插入一个
        mid = main_dur / 2
        if mid + clip_duration <= main_dur:
            insert_times = [mid]
        else:
            _safe_print("[PIP-LOCAL] 视频太短，无法插入画中画")
            return None

    _safe_print(f"[PIP-LOCAL] 将在 {len(insert_times)} 个位置插入画中画: "
                f"{[f'{t:.1f}s' for t in insert_times]}")

    # 为每个插入点分配素材（循环使用）
    _prog(0.15, "准备画中画素材...")
    ts = int(time.time())
    pip_segments = []

    for idx, start_t in enumerate(insert_times):
        src = valid_paths[idx % len(valid_paths)]
        src_dur = get_video_duration(src)
        use_dur = min(clip_duration, src_dur) if src_dur > 0 else clip_duration
        end_t = start_t + use_dur

        # 缩放+裁剪素材
        seg_out = os.path.join(OUTPUT_DIR, f"_pip_local_{ts}_{idx}.mp4")
        clips = [(src, use_dur)]
        result = _concat_clips(clips, target_w, target_h, seg_out)
        if result:
            pip_segments.append((result, start_t, end_t))
            _safe_print(f"[PIP-LOCAL] 片段 {idx+1}: {os.path.basename(src)} "
                        f"-> {start_t:.1f}s-{end_t:.1f}s")
        else:
            _safe_print(f"[PIP-LOCAL] 片段 {idx+1} 处理失败，跳过")

        pct = 0.15 + 0.50 * (idx + 1) / len(insert_times)
        _prog(pct, f"处理素材 {idx+1}/{len(insert_times)}...")

    if not pip_segments:
        _safe_print("[PIP-LOCAL] 所有素材处理失败")
        return None

    # 叠加到主视频
    _prog(0.70, f"合成画中画视频（{len(pip_segments)} 个片段）...")
    out_path = os.path.join(OUTPUT_DIR, f"pip_local_{ts}.mp4")
    result = _overlay_pip_segments(main_video, pip_segments, out_path)

    # 清理临时文件
    for seg_path, _, _ in pip_segments:
        try:
            if os.path.exists(seg_path):
                os.remove(seg_path)
        except Exception:
            pass

    if result and os.path.exists(result):
        _prog(1.0, "✅ 本地画中画合成完成")
        return result
    else:
        _safe_print("[PIP-LOCAL] 最终合成失败")
        return None
