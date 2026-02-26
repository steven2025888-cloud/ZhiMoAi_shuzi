# -*- coding: utf-8 -*-
"""
lib_subtitle.py — 字幕生成与烧录引擎

支持：
- Whisper 语音识别
- ASS 字幕生成
- 关键词高亮
- ffmpeg 字幕烧录
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Callable, List, Optional, Dict, Any

# ============================================================
# 常量配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "unified_outputs")

# 确保目录存在
os.makedirs(FONTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# FFmpeg 路径配置
_LATENTSYNC_DIR = os.path.join(BASE_DIR, "_internal_sync")
_FFMPEG_DIR = os.path.join(_LATENTSYNC_DIR, "ffmpeg-7.1", "bin")
_FFMPEG = os.path.join(_FFMPEG_DIR, "ffmpeg.exe")
_FFPROBE = os.path.join(_FFMPEG_DIR, "ffprobe.exe")

if not os.path.exists(_FFMPEG):
    _FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
    _FFPROBE = shutil.which("ffprobe") or "ffprobe"

# Windows 无窗口标志
_WIN = sys.platform == "win32"
_NWIN = subprocess.CREATE_NO_WINDOW if _WIN else 0

# 字幕结束标点
SENTENCE_ENDS = {"。", "！", "？", ".", "!", "?", "；", ";", "，", ",", "、"}

# 默认颜色
DEFAULT_TEXT_COLOR = "#FFFFFF"
DEFAULT_HI_COLOR = "#FFD700"
DEFAULT_OUTLINE_COLOR = "#000000"
DEFAULT_BG_COLOR = "#000000"


# ============================================================
# 字体工具
# ============================================================
def get_font_choices() -> List[str]:
    """获取字体选择列表，第一项为系统字体"""
    font_exts = {".ttf", ".otf", ".TTF", ".OTF"}
    try:
        names = [
            os.path.splitext(f)[0]
            for f in sorted(os.listdir(FONTS_DIR))
            if os.path.splitext(f)[1] in font_exts
        ]
    except OSError:
        names = []
    return ["系统字体"] + names


# ============================================================
# 颜色工具
# ============================================================
def normalize_color(raw: str, fallback: str = "#ffffff") -> str:
    """
    确保颜色是 #RRGGBB 格式
    
    Args:
        raw: 原始颜色值
        fallback: 默认颜色
        
    Returns:
        规范化的颜色值 #RRGGBB
    """
    if not raw or not isinstance(raw, str):
        return fallback
    
    raw = raw.strip().lstrip("#")
    
    # 去掉 Gradio 可能追加的 alpha (8位)
    if len(raw) == 8:
        raw = raw[:6]
    
    # 短形式 #RGB -> #RRGGBB
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    
    # 验证是否为合法十六进制
    if len(raw) == 6:
        try:
            int(raw, 16)
            return f"#{raw.upper()}"
        except ValueError:
            pass
    
    return fallback


def _hex2ass(hex_color: str) -> str:
    """将 #RRGGBB 转换为 ASS BGR 格式 &H00BBGGRR&"""
    c = normalize_color(hex_color, DEFAULT_TEXT_COLOR).lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return f"&H00{b:02X}{g:02X}{r:02X}&"


def _hex2ass_alpha(hex_color: str, opacity: int = 0) -> str:
    """
    将 #RRGGBB + 透明度转换为 ASS 格式 &HAABBGGRR&
    
    Args:
        hex_color: 颜色值
        opacity: 不透明度 0=全透明, 100=完全不透明
    """
    c = normalize_color(hex_color, DEFAULT_BG_COLOR).lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    # ASS alpha: 00=不透明, FF=全透明
    alpha = int(255 * (1 - max(0, min(100, opacity)) / 100))
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}&"


# ============================================================
# ASS 时间格式
# ============================================================
def _ass_time(seconds: float) -> str:
    """将秒数转换为 ASS 时间格式 h:mm:ss.cc"""
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = min(99, int(round((s - int(s)) * 100)))
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


# ============================================================
# 关键词工具
# ============================================================
def parse_keywords(kw_str: str) -> List[str]:
    """把分隔符分隔的关键词字符串解析成列表"""
    if not kw_str or not kw_str.strip():
        return []
    # 支持中英文逗号、顿号、空格
    parts = re.split(r"[,，、\s]+", kw_str.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_keyword(word: str, keywords: List[str]) -> bool:
    """判断词是否包含关键词（子串匹配）"""
    word = word.strip()
    return any(kw and kw in word for kw in keywords)


# ═══════════════════════════════════════════════
# 生成 ASS 字幕
# ═══════════════════════════════════════════════
def build_ass(words, font_name, font_size,
              text_color, hi_color, outline_color, outline_size,
              position, pos_offset=0,
              kw_enable=False, keywords=None, hi_scale=1.5,
              bg_color="#000000", bg_opacity=0,
              title_text="", title_duration=5, title_color="#FFD700",
              title_outline_color="#000000", title_margin_top=30,
              title_font_size=48,
              video_width=0, video_height=0):
    """
    words      : [{"word":str, "start":float, "end":float}, ...]
    position   : "上"|"中"|"下"  →  水平居中（Alignment 8/5/2）
    pos_offset : 垂直偏移 px（正数向上，负数向下），用户自定义偏移
    kw_enable  : 是否启用关键词高亮
    keywords   : 关键词列表 ["便宜","优质",...]
    hi_scale   : 关键词字号倍数（相对于 font_size）
    bg_color   : 背景颜色 #RRGGBB
    bg_opacity : 背景透明度 0=全透明 100=不透明
    title_text : 标题文本（空则不显示标题）
    title_duration : 标题显示时长（秒）
    title_color : 标题字幕颜色 #RRGGBB
    title_outline_color : 标题描边颜色 #RRGGBB
    title_margin_top : 标题距顶部距离 px
    title_font_size : 标题字体大小 px
    video_width : 实际视频宽度（用于计算换行，0=使用默认1280）
    video_height: 实际视频高度
    """
    align_map   = {"上": 8, "中": 5, "下": 2, "⬆上": 8, "⬛中": 5, "⬇下": 2}
    # 调整"下"的位置，基础值往上移动（从30改为60），再加上默认偏移50px，再加上用户自定义偏移
    marginv_map = {"上": 50, "中": 0,  "下": 60, "⬆上": 50, "⬛中": 0, "⬇下": 60}
    align   = align_map.get(position, 2)
    base_marginv = marginv_map.get(position, 60)
    # 默认偏移50px + 用户自定义偏移（正数向上，所以是加法）
    marginv = base_marginv + 50 + int(pos_offset or 0)

    # PlayRes 使用实际视频分辨率（避免缩放导致字幕溢出）
    play_res_x = int(video_width) if video_width and int(video_width) > 0 else 1280
    play_res_y = int(video_height) if video_height and int(video_height) > 0 else 720

    tc  = _hex2ass(text_color)
    hc  = _hex2ass(hi_color)
    oc  = _hex2ass(outline_color)
    osz = max(0, min(10, int(outline_size or 0)))
    fs  = int(font_size or 32)
    hi_fs = max(fs + 4, int(fs * max(1.0, float(hi_scale))))

    kws = (keywords or []) if kw_enable else []
    
    # 调试日志
    print(f"[SUBTITLE] kw_enable={kw_enable}, keywords={keywords}, kws={kws}")

    fn = font_name if font_name and font_name not in ("默认字体", "系统字体") else "Microsoft YaHei"

    # 背景色处理 - 使用\an标签和box方式
    bg_op = max(0, min(100, int(bg_opacity or 0)))
    has_bg = bg_op > 0

    # 文字样式: 始终 BorderStyle=1（仅描边）
    border_style = 1
    shadow_size = 0

    # 背景样式: 使用BorderStyle=4（box背景）
    bg_style_line = ""
    if has_bg:
        bg_c = _hex2ass_alpha(bg_color or "#000000", bg_op)
        # BorderStyle=4 表示使用box背景，Outline参数控制padding
        bg_pad = 12  # 固定padding
        bg_style_line = (
            f"Style: SubBG,{fn},{fs},"
            f"{tc},{tc},{bg_c},{bg_c},"
            f"0,0,0,0,100,100,0,0,4,{bg_pad},0,"
            f"{align},20,20,{marginv},1\n"
        )

    # ── 标题样式 ──
    title_style_line = ""
    title_event = ""
    if title_text and title_text.strip():
        title_display = title_text.strip()
        
        _raw_title_color = title_color
        t_tc  = _hex2ass(normalize_color(title_color, "#FFD700"))
        t_oc  = _hex2ass(normalize_color(title_outline_color, "#000000"))
        # 使用用户设置的标题字体大小，限制范围12-96
        t_fs  = max(12, min(96, int(title_font_size or 48)))
        # 标题距顶部距离
        t_mv  = max(10, min(200, int(title_margin_top or 30)))
        t_dur = max(1, int(title_duration or 5))
        
        print(f"[SUBTITLE] title_color raw='{_raw_title_color}' -> normalized='{normalize_color(title_color, '#FFD700')}' -> ass='{t_tc}', t_fs={t_fs}")
        
        # 标题换行：根据字体大小和视频宽度计算
        _title_margin = 80
        _title_usable = (play_res_x - _title_margin * 2) * 0.90
        _title_char_w = t_fs  # 1个中文字符 ≈ font_size px
        _title_max_chars = max(4, int(_title_usable / _title_char_w))
        
        if len(title_display) > _title_max_chars:
            # 按字符数切分并插入 \N
            lines = [title_display[i:i + _title_max_chars]
                     for i in range(0, len(title_display), _title_max_chars)]
            title_display = "\\N".join(lines)
        
        title_style_line = (
            f"Style: Title,{fn},{t_fs},"
            f"{t_tc},&H000000FF&,{t_oc},&H00000000&,"
            f"1,0,0,0,100,100,0,0,{border_style},{osz},0,"
            f"8,{_title_margin},{_title_margin},{t_mv},1\n"
        )
        t_ts = _ass_time(0)
        t_te = _ass_time(t_dur)
        # 内联颜色标签确保颜色生效
        title_event = f"Dialogue: 2,{t_ts},{t_te},Title,,0,0,0,,{{\\c{t_tc}\\3c{t_oc}}}{title_display}\n"

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {play_res_x}\nPlayResY: {play_res_y}\nTimer: 100.0000\n"
        "WrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{fn},{fs},"
        f"{tc},&H000000FF&,{oc},&H00000000&,"
        f"0,0,0,0,100,100,0,0,{border_style},{osz},{shadow_size},"
        f"{align},60,60,{marginv},1\n"
        f"{title_style_line}"
        f"{bg_style_line}\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    # ── 句子结束标点 ──
    sentence_ends = {'。', '！', '？', '.', '!', '?', '；', ';', '，', ',', '、'}
    # 根据字体大小和视频实际宽度计算可用宽度
    # MarginL=MarginR=60, 再留10%余量
    _margin = 60
    _usable_width = (play_res_x - _margin * 2) * 0.90
    _char_width = max(fs, 12)  # 1个中文字符 ≈ font_size px

    def _strip_punct(text):
        for p in sentence_ends:
            text = text.replace(p, '')
        return text

    def _highlight_text(text, kws_list, hc_val, hi_fs_val):
        """对文本做关键词高亮，返回带ASS标签的字符串"""
        if not kws_list or not text:
            return text
        result_parts = []
        remaining = text
        while remaining:
            earliest_pos = len(remaining)
            earliest_kw = None
            for kw in kws_list:
                if kw and len(kw) >= 1:
                    pos = remaining.find(kw)
                    if pos != -1 and pos < earliest_pos:
                        earliest_pos = pos
                        earliest_kw = kw
            if earliest_kw is None:
                result_parts.append(remaining)
                break
            else:
                if earliest_pos > 0:
                    result_parts.append(remaining[:earliest_pos])
                # 高亮词前后加窄空格，让高亮词和普通文字有间距
                result_parts.append(
                    f" {{\\c{hc_val}\\fs{hi_fs_val}\\b1}}{earliest_kw}{{\\r}} "
                )
                remaining = remaining[earliest_pos + len(earliest_kw):]
        return "".join(result_parts)

    def _calc_pixel_width(text, kws_list, normal_fs, highlight_fs):
        """估算一行文本的像素宽度（考虑高亮关键词放大）"""
        if not text:
            return 0
        char_w = normal_fs
        hi_char_w = highlight_fs
        
        if not kws_list:
            return len(text) * char_w
        
        total = 0.0
        remaining = text
        while remaining:
            earliest_pos = len(remaining)
            earliest_kw = None
            for kw in kws_list:
                if kw and len(kw) >= 1:
                    pos = remaining.find(kw)
                    if pos != -1 and pos < earliest_pos:
                        earliest_pos = pos
                        earliest_kw = kw
            if earliest_kw is None:
                total += len(remaining) * char_w
                break
            else:
                total += earliest_pos * char_w
                total += len(earliest_kw) * hi_char_w
                remaining = remaining[earliest_pos + len(earliest_kw):]
        return total

    def _build_line(text, kws_list, hc_val, hi_fs_val, normal_fs, usable_w):
        """去标点 → 按像素宽度换行 → 高亮，返回最终 ASS 文本"""
        plain = _strip_punct(text)
        if not plain:
            return ""
        
        # 估算总像素宽度
        total_px = _calc_pixel_width(plain, kws_list, normal_fs, hi_fs_val)
        
        if total_px <= usable_w:
            # 一行放得下，直接高亮返回
            return _highlight_text(plain, kws_list, hc_val, hi_fs_val)
        
        # 需要换行：逐字累加像素宽度，超出时插入换行
        char_w = normal_fs
        hi_char_w = hi_fs_val
        
        # 先标记每个字符是否属于高亮关键词
        char_is_highlight = [False] * len(plain)
        if kws_list:
            tmp = plain
            offset = 0
            while tmp:
                earliest_pos = len(tmp)
                earliest_kw = None
                for kw in kws_list:
                    if kw and len(kw) >= 1:
                        pos = tmp.find(kw)
                        if pos != -1 and pos < earliest_pos:
                            earliest_pos = pos
                            earliest_kw = kw
                if earliest_kw is None:
                    break
                for j in range(len(earliest_kw)):
                    char_is_highlight[offset + earliest_pos + j] = True
                tmp = tmp[earliest_pos + len(earliest_kw):]
                offset += earliest_pos + len(earliest_kw)
        
        # 按像素宽度切分成多行
        lines = []
        cur_line = ""
        cur_px = 0.0
        for idx, ch in enumerate(plain):
            w = hi_char_w if char_is_highlight[idx] else char_w
            if cur_px + w > usable_w and cur_line:
                lines.append(cur_line)
                cur_line = ""
                cur_px = 0.0
            cur_line += ch
            cur_px += w
        if cur_line:
            lines.append(cur_line)
        
        # 对每行做高亮，用 \N 连接
        return "\\N".join(
            _highlight_text(l, kws_list, hc_val, hi_fs_val) for l in lines
        )

    # ── 第一步：统一合并成句子 ──
    # 无论输入是逐字（_text_to_words）还是已合并（_merge_words_to_sentences），
    # 都在这里按标点重新分句，保证每条 Dialogue 是一个完整句子。
    merged_sentences = []   # [{"text": str, "start": float, "end": float}, ...]
    cur_text = ""
    cur_start = None
    cur_end = None

    for w in words:
        wt = w["word"].strip()
        if not wt:
            continue
        if cur_start is None:
            cur_start = w["start"]
        cur_text += wt
        cur_end = w["end"]

        # 检查末尾是否有句子结束标点
        if wt[-1] in sentence_ends:
            merged_sentences.append({
                "text": cur_text, "start": cur_start, "end": cur_end
            })
            cur_text = ""
            cur_start = None
            cur_end = None

    # 剩余部分
    if cur_text.strip():
        merged_sentences.append({
            "text": cur_text, "start": cur_start or 0, "end": cur_end or 0
        })

    # 后处理：合并过短的句子（纯文字<=2字 → 并入前一句）
    if len(merged_sentences) > 1:
        tmp = [merged_sentences[0]]
        for s in merged_sentences[1:]:
            pure = _strip_punct(s["text"])
            if len(pure) <= 2 and tmp:
                tmp[-1]["text"] += s["text"]
                tmp[-1]["end"] = s["end"]
            else:
                tmp.append(s)
        merged_sentences = tmp

    # ── 第二步：为每个句子生成 Dialogue ──
    events = ""
    for sent in merged_sentences:
        text = sent["text"]
        t_start = sent["start"]
        t_end = sent["end"]

        # 保证最短显示时长
        if t_end - t_start < 0.8:
            t_end = t_start + 0.8
        if t_end <= t_start:
            t_end = t_start + 1.0

        line_text = _build_line(text, kws, hc, hi_fs, fs, _usable_width)
        if not line_text:
            continue

        ts = _ass_time(t_start)
        te = _ass_time(max(float(t_end), float(t_start) + 0.05))

        # 背景层
        if has_bg:
            plain = _strip_punct(text).strip()
            if plain:
                # 背景层也按像素宽度换行（用普通字体大小）
                _bg_max = max(6, int(_usable_width / _char_width))
                if len(plain) > _bg_max:
                    bg_lines = [plain[i:i + _bg_max]
                                for i in range(0, len(plain), _bg_max)]
                    plain = "\\N".join(bg_lines)
                events += f"Dialogue: 0,{ts},{te},SubBG,,0,0,0,,{plain}\n"

        events += f"Dialogue: 1,{ts},{te},Default,,0,0,0,,{line_text}\n"

    print(f"[SUBTITLE] Generated {events.count('Dialogue:')} events, "
          f"kws={kws}, input_words={len(words)}, sentences={len(merged_sentences)}")

    return header + title_event + events


# ═══════════════════════════════════════════════
# Whisper 转录
# ═══════════════════════════════════════════════
def _merge_words_to_sentences(words):
    """将逐字合并为按句子显示（按标点符号分句）
    
    确保不会出现单个字单独显示的情况：
    - 如果一个句子只有1-2个字，合并到前一个句子
    """
    if not words:
        return []
    
    # 句子结束标点（包括逗号）
    sentence_end_marks = set('。！？，、.!?,;；：:')
    
    sentences = []
    current_text = ""
    current_start = words[0]["start"]
    current_end = words[0]["end"]
    
    for i, word_info in enumerate(words):
        word = word_info["word"].strip()
        if not word:
            continue
        
        # 添加到当前句子
        current_text += word
        current_end = word_info["end"]
        
        # 如果还没有设置start（第一个词）
        if not current_text.strip():
            current_start = word_info["start"]
        
        # 检查是否是句子结束（最后一个字符是标点）
        is_end = word[-1] in sentence_end_marks
        is_last = (i == len(words) - 1)
        
        if is_end or is_last:
            text = current_text.strip()
            if text:
                sentences.append({
                    "word": text,
                    "start": current_start,
                    "end": current_end
                })
            # 重置
            current_text = ""
            if i + 1 < len(words):
                current_start = words[i + 1]["start"]
                current_end = words[i + 1]["end"]
    
    # 后处理：合并过短的句子（1-2个字的句子合并到前一个）
    if len(sentences) > 1:
        merged = [sentences[0]]
        for s in sentences[1:]:
            # 去掉标点后的纯文字长度
            pure_text = s["word"]
            for p in sentence_end_marks:
                pure_text = pure_text.replace(p, '')
            
            if len(pure_text) <= 2 and merged:
                # 太短了，合并到前一个句子
                merged[-1]["word"] += s["word"]
                merged[-1]["end"] = s["end"]
            else:
                merged.append(s)
        sentences = merged
    
    return sentences


def transcribe(audio_path: str):
    if not audio_path or not os.path.exists(str(audio_path)):
        return []

    try:
        import whisper as _w
        model = _w.load_model("base")
        res   = model.transcribe(str(audio_path), word_timestamps=True, language="zh")
        out   = []
        for seg in res.get("segments", []):
            for w in seg.get("words", []):
                out.append({"word": w["word"],
                            "start": float(w["start"]),
                            "end":   float(w["end"])})
        if out:
            # 合并为句子
            return _merge_words_to_sentences(out)
    except Exception:
        pass

    try:
        from faster_whisper import WhisperModel
        m = WhisperModel("base", device="cpu", compute_type="int8")
        segs, _ = m.transcribe(str(audio_path), word_timestamps=True, language="zh")
        out = []
        for seg in segs:
            for w in (getattr(seg, "words", None) or []):
                out.append({"word": w.word,
                            "start": float(w.start),
                            "end":   float(w.end)})
        if out:
            # 合并为句子
            return _merge_words_to_sentences(out)
    except Exception:
        pass

    return []


def _text_to_words(text: str, duration: float) -> list:
    """文本均匀分配到时间轴（中文按字，英文按词）"""
    tokens = []
    for part in re.split(r"(\s+)", text.strip()):
        part = part.strip()
        if not part:
            continue
        if any("\u4e00" <= c <= "\u9fff" for c in part):
            tokens.extend(list(part))
        else:
            tokens.append(part)
    if not tokens:
        tokens = ["字幕"]
    dt = duration / len(tokens)
    return [{"word": t, "start": i * dt, "end": (i + 1) * dt}
            for i, t in enumerate(tokens)]


def _get_duration(video_path: str) -> float:
    try:
        r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_format", str(video_path)],
            capture_output=True, text=True,
            creationflags=_NWIN, timeout=15)
        return float(json.loads(r.stdout).get("format", {}).get("duration", 10.0))
    except Exception:
        return 10.0


# ═══════════════════════════════════════════════
# 主入口：烧录字幕
# ═══════════════════════════════════════════════
def burn_subtitles(video_path, audio_path, text_hint,
                   font_name, font_size,
                   text_color, hi_color, outline_color, outline_size,
                   position, pos_offset=0,
                   kw_enable=False, kw_str="", hi_scale=1.5,
                   bg_color="#000000", bg_opacity=0,
                   title_text="", title_duration=5, title_color="#FFD700",
                   title_outline_color="#000000", title_margin_top=30,
                   title_font_size=48,
                   progress_cb=None):
    def _prog(pct, msg):
        if progress_cb:
            try: progress_cb(pct, msg)
            except Exception: pass

    if not video_path or not os.path.exists(str(video_path)):
        raise RuntimeError("请先完成视频合成")

    # 规范化颜色（防 Gradio ColorPicker 传奇怪格式）
    text_color    = normalize_color(text_color,    "#FFFFFF")
    hi_color      = normalize_color(hi_color,      "#FFD700")
    outline_color = normalize_color(outline_color, "#000000")
    bg_color      = normalize_color(bg_color,      "#000000")

    _prog(0.05, "🎙 识别音频文字...")
    src_audio = str(audio_path) if (audio_path and os.path.exists(str(audio_path))) else str(video_path)
    words     = transcribe(src_audio)

    if not words:
        _prog(0.2, "⚠️ Whisper 不可用，按输入文字生成字幕...")
        dur   = _get_duration(str(video_path))
        hint  = (text_hint or "").strip() or "字幕内容"
        words = _text_to_words(hint, dur)

    _prog(0.4, "📝 生成字幕文件...")
    keywords = parse_keywords(kw_str) if kw_enable else []
    
    # 调试日志
    print(f"[SUBTITLE] burn_subtitles: kw_enable={kw_enable}, kw_str='{kw_str}', keywords={keywords}")

    # 获取视频实际分辨率（用于字幕换行计算）
    _vid_w, _vid_h = 1280, 720
    try:
        _r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", str(video_path)],
            capture_output=True, text=True,
            creationflags=_NWIN, timeout=10)
        _streams = json.loads(_r.stdout).get("streams", [])
        if _streams:
            _vid_w = int(_streams[0].get("width", 1280))
            _vid_h = int(_streams[0].get("height", 720))
    except Exception:
        pass
    print(f"[SUBTITLE] video resolution: {_vid_w}x{_vid_h}")

    # 规范化标题颜色
    title_color         = normalize_color(title_color,         "#FFD700")
    title_outline_color = normalize_color(title_outline_color, "#000000")

    ass_content = build_ass(
        words,
        font_name, font_size,
        text_color, hi_color, outline_color, outline_size,
        position, int(pos_offset or 0),
        kw_enable=kw_enable,
        keywords=keywords,
        hi_scale=float(hi_scale or 1.5),
        bg_color=bg_color,
        bg_opacity=int(bg_opacity or 0),
        title_text=title_text or "",
        title_duration=int(title_duration or 5),
        title_color=title_color,
        title_outline_color=title_outline_color,
        title_margin_top=int(title_margin_top or 30),
        title_font_size=int(title_font_size or 48),
        video_width=_vid_w,
        video_height=_vid_h,
    )

    ts       = int(time.time())
    ass_path = os.path.join(OUTPUT_DIR, f"sub_{ts}.ass")
    out_path = os.path.join(OUTPUT_DIR, f"subtitled_{ts}.mp4")

    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_content)

    _prog(0.65, "🎬 烧录字幕...")

    def _esc(p):
        return str(p).replace("\\", "/").replace(":", "\\:")

    vf = f"ass='{_esc(ass_path)}'"
    font_files = [f for f in os.listdir(FONTS_DIR)
                  if f.endswith((".ttf",".otf",".TTF",".OTF"))]
    if font_files:
        vf = f"ass='{_esc(ass_path)}':fontsdir='{_esc(FONTS_DIR)}'"

    cmd = [
        _FFMPEG, "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_path
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=_NWIN,
            text=True, errors="replace")
        _, stderr = proc.communicate(timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 失败 (code={proc.returncode}):\n{stderr[-600:]}")
    except subprocess.TimeoutExpired:
        try: proc.kill()
        except Exception: pass
        raise RuntimeError("字幕烧录超时（>5分钟）")

    if not os.path.exists(out_path):
        raise RuntimeError("输出文件未生成，请检查 ffmpeg")

    # 保留一份ASS文件用于调试
    try:
        debug_ass = os.path.join(OUTPUT_DIR, "debug_last_subtitle.ass")
        import shutil
        shutil.copy2(ass_path, debug_ass)
        print(f"[SUBTITLE] ASS debug copy saved to: {debug_ass}")
    except Exception as e:
        print(f"[SUBTITLE] Failed to save debug ASS: {e}")

    try:
        os.remove(ass_path)
    except Exception:
        pass

    _prog(1.0, "✅ 完成")
    return out_path