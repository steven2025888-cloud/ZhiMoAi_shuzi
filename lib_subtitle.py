# -*- coding: utf-8 -*-
# lib_subtitle.py — 字幕生成与烧录引擎（关键词高亮版）

import os, sys, re, json, time, subprocess, shutil

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

LATENTSYNC_DIR = os.path.join(BASE_DIR, "_internal_sync")
_FFMPEG_DIR = os.path.join(LATENTSYNC_DIR, "ffmpeg-7.1", "bin")
_FFMPEG  = os.path.join(_FFMPEG_DIR, "ffmpeg.exe")
_FFPROBE = os.path.join(_FFMPEG_DIR, "ffprobe.exe")
if not os.path.exists(_FFMPEG):
    _FFMPEG  = shutil.which("ffmpeg")  or "ffmpeg"
    _FFPROBE = shutil.which("ffprobe") or "ffprobe"

OUTPUT_DIR = os.path.join(BASE_DIR, "unified_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_WIN  = sys.platform == "win32"
_NWIN = subprocess.CREATE_NO_WINDOW if _WIN else 0


# ═══════════════════════════════════════════════
# 字体工具
# ═══════════════════════════════════════════════
def get_font_choices():
    """获取字体选择列表，第一项为系统字体"""
    exts = {".ttf", ".otf", ".TTF", ".OTF"}
    try:
        names = [os.path.splitext(f)[0]
                 for f in sorted(os.listdir(FONTS_DIR))
                 if os.path.splitext(f)[1] in exts]
    except Exception:
        names = []
    
    # 第一项始终是系统字体
    result = ["系统字体"]
    if names:
        result.extend(names)
    return result


# ═══════════════════════════════════════════════
# 颜色工具
# ═══════════════════════════════════════════════
def normalize_color(raw: str, fallback: str = "#ffffff") -> str:
    """确保颜色是 #RRGGBB 格式，兼容各种输入"""
    if not raw or not isinstance(raw, str):
        return fallback
    raw = raw.strip().lstrip("#")
    # 去掉 Gradio 可能追加的 alpha 信息 (8位)
    if len(raw) == 8:
        raw = raw[:6]
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) == 6:
        try:
            int(raw, 16)   # 验证是合法16进制
            return "#" + raw.upper()
        except ValueError:
            pass
    return fallback


def _hex2ass(hex_color: str) -> str:
    """#RRGGBB  →  &H00BBGGRR&（ASS BGR 字节序）"""
    c = normalize_color(hex_color, "#ffffff").lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return f"&H00{b:02X}{g:02X}{r:02X}&"


def _hex2ass_alpha(hex_color: str, opacity: int = 0) -> str:
    """#RRGGBB + opacity(0~100) → &HAABBGGRR&
    opacity: 0=全透明, 100=不透明
    ASS alpha: 00=不透明, FF=全透明 (与直觉相反)
    """
    c = normalize_color(hex_color, "#000000").lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    alpha = int(255 * (1 - max(0, min(100, opacity)) / 100))
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}&"


# ═══════════════════════════════════════════════
# ASS 时间格式
# ═══════════════════════════════════════════════
def _ass_time(s: float) -> str:
    s  = max(0.0, float(s))
    h  = int(s // 3600)
    m  = int((s % 3600) // 60)
    sc = s % 60
    cs = int(round((sc - int(sc)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{int(sc):02d}.{cs:02d}"


# ═══════════════════════════════════════════════
# 关键词工具
# ═══════════════════════════════════════════════
def parse_keywords(kw_str: str) -> list:
    """把逗号/空格分隔的关键词字符串解析成列表"""
    if not kw_str or not kw_str.strip():
        return []
    # 支持中英文逗号、顿号、空格
    parts = re.split(r"[,，、\s]+", kw_str.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_keyword(word: str, keywords: list) -> bool:
    """判断一个 token 是否属于关键词（支持子串匹配）"""
    w = word.strip()
    for kw in keywords:
        if kw and kw in w:
            return True
    return False


# ═══════════════════════════════════════════════
# 生成 ASS 字幕
# ═══════════════════════════════════════════════
def build_ass(words, font_name, font_size,
              text_color, hi_color, outline_color, outline_size,
              position,
              kw_enable=False, keywords=None, hi_scale=1.5,
              bg_color="#000000", bg_opacity=0,
              title_text="", title_duration=5, title_color="#FFFFFF",
              title_outline_color="#000000", title_margin_top=30):
    """
    words      : [{"word":str, "start":float, "end":float}, ...]
    position   : "上"|"中"|"下"  →  水平居中（Alignment 8/5/2）
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
    """
    align_map   = {"上": 8, "中": 5, "下": 2, "⬆上": 8, "⬛中": 5, "⬇下": 2}
    marginv_map = {"上": 50, "中": 0,  "下": 30, "⬆上": 50, "⬛中": 0, "⬇下": 30}
    align   = align_map.get(position, 2)
    marginv = marginv_map.get(position, 30)

    tc  = _hex2ass(text_color)
    hc  = _hex2ass(hi_color)
    oc  = _hex2ass(outline_color)
    osz = max(0, min(10, int(outline_size or 0)))
    fs  = int(font_size or 32)
    hi_fs = max(fs + 4, int(fs * max(1.0, float(hi_scale))))

    kws = (keywords or []) if kw_enable else []

    fn = font_name if font_name and font_name != "默认字体" else "Microsoft YaHei"

    # 背景色处理
    bg_op = max(0, min(100, int(bg_opacity or 0)))
    has_bg = bg_op > 0

    # 文字样式: 始终 BorderStyle=1（仅描边）
    border_style = 1
    shadow_size = 0

    # 背景样式: SubBG = 所有颜色设为背景色 + bord 制造圆角填充
    # bord=字号40% 确保相邻字符的描边充分重叠形成连续圆角矩形
    bg_style_line = ""
    if has_bg:
        bg_c = _hex2ass_alpha(bg_color or "#000000", bg_op)
        bg_pad = max(6, int(fs * 0.4))  # 6~N px, 字号越大 padding 越大
        bg_style_line = (
            f"Style: SubBG,{fn},{fs},"
            f"{bg_c},{bg_c},{bg_c},{bg_c},"
            f"1,0,0,0,100,100,2,0,1,{bg_pad},0,"
            f"{align},20,20,{marginv},1\n"
        )

    # ── 标题样式 ──
    title_style_line = ""
    title_event = ""
    if title_text and title_text.strip():
        t_tc  = _hex2ass(normalize_color(title_color, "#FFFFFF"))
        t_oc  = _hex2ass(normalize_color(title_outline_color, "#000000"))
        t_fs  = max(fs + 8, int(fs * 1.3))  # 标题字号比正文大
        t_mv  = max(0, int(title_margin_top or 30))
        t_dur = max(1, int(title_duration or 5))
        title_style_line = (
            f"Style: Title,{fn},{t_fs},"
            f"{t_tc},&H000000FF&,{t_oc},&H00000000&,"
            f"1,0,0,0,100,100,0,0,{border_style},{osz},0,"
            f"8,20,20,{t_mv},1\n"  # Alignment=8 顶部居中
        )
        t_ts = _ass_time(0)
        t_te = _ass_time(t_dur)
        title_event = f"Dialogue: 2,{t_ts},{t_te},Title,,0,0,0,,{title_text.strip()}\n"

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1280\nPlayResY: 720\nTimer: 100.0000\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{fn},{fs},"
        f"{tc},&H000000FF&,{oc},&H00000000&,"
        f"0,0,0,0,100,100,0,0,{border_style},{osz},{shadow_size},"
        f"{align},20,20,{marginv},1\n"
        f"{title_style_line}"
        f"{bg_style_line}\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    # ── 优化：按标点符号分句，保持完整句子 ──
    events = ""
    
    # 定义句子结束标点
    sentence_ends = {'。', '！', '？', '.', '!', '?', '；', ';', '，', ',', '、'}
    
    current_sentence = []
    sentences = []
    
    # 将词按标点分组成句子
    for i, w in enumerate(words):
        word_text = w["word"].strip()
        if not word_text:
            continue
            
        current_sentence.append(w)
        
        # 检查是否是句子结束（包含标点或达到最大长度）
        has_punctuation = any(p in word_text for p in sentence_ends)
        is_last = (i == len(words) - 1)
        is_long = len(current_sentence) >= 15  # 最多15个词一句
        
        if has_punctuation or is_last or is_long:
            if current_sentence:
                sentences.append(current_sentence[:])
                current_sentence = []
    
    # 如果还有剩余的词
    if current_sentence:
        sentences.append(current_sentence)
    
    # 为每个句子生成字幕
    for sentence in sentences:
        if not sentence:
            continue
            
        t_start = sentence[0]["start"]
        t_end = sentence[-1]["end"]
        
        # 确保字幕有合理的显示时长
        duration = t_end - t_start
        if duration < 0.8:  # 最短显示0.8秒
            t_end = t_start + 0.8
        elif t_end <= t_start:
            t_end = t_start + 1.0
        
        # 构建句子文本，去掉标点符号
        parts = []
        for w in sentence:
            wt = w["word"].strip()
            if not wt:
                continue
            
            # 去掉标点符号
            wt_clean = wt
            for p in sentence_ends:
                wt_clean = wt_clean.replace(p, '')
            
            if not wt_clean:  # 如果去掉标点后为空，跳过
                continue
            
            if kws and _is_keyword(wt_clean, kws):
                # 关键词：换高亮色 + 放大 + 加粗
                parts.append(
                    f"{{\\c{hc}\\fs{hi_fs}\\b1}}{wt_clean}{{\\r}}"
                )
            else:
                parts.append(wt_clean)
        
        if not parts:  # 如果没有有效内容，跳过
            continue
        
        line_text = " ".join(parts)  # 词间用单空格分隔
        ts = _ass_time(t_start)
        te = _ass_time(max(float(t_end), float(t_start) + 0.05))

        # 背景层: SubBG渲染同样文字（文字色=描边色=背景色 + 大bord → 圆角背景）
        if has_bg:
            # 去除标点，去除空格让字符紧密排列（bord会自动扩展成连续圆角矩形）
            plain = "".join(
                w["word"].strip().translate({ord(p): '' for p in sentence_ends})
                for w in sentence
            ).replace(" ", "").strip()
            if plain:
                events += f"Dialogue: 0,{ts},{te},SubBG,,0,0,0,,{plain}\n"

        events += f"Dialogue: 1,{ts},{te},Default,,0,0,0,,{line_text}\n"

    return header + title_event + events


# ═══════════════════════════════════════════════
# Whisper 转录
# ═══════════════════════════════════════════════
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
            return out
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
            return out
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
                   position,
                   kw_enable=False, kw_str="", hi_scale=1.5,
                   bg_color="#000000", bg_opacity=0,
                   title_text="", title_duration=5, title_color="#FFFFFF",
                   title_outline_color="#000000", title_margin_top=30,
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

    # 规范化标题颜色
    title_color         = normalize_color(title_color,         "#FFFFFF")
    title_outline_color = normalize_color(title_outline_color, "#000000")

    ass_content = build_ass(
        words,
        font_name, font_size,
        text_color, hi_color, outline_color, outline_size,
        position,
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

    try:
        os.remove(ass_path)
    except Exception:
        pass

    _prog(1.0, "✅ 完成")
    return out_path