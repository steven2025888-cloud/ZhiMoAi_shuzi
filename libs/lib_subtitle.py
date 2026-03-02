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
# 工具函数
# ============================================================
def _safe_print(msg: str):
    """安全打印，避免 GBK 编码错误"""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            # 移除无法编码的字符
            safe_msg = msg.encode('gbk', errors='replace').decode('gbk')
            print(safe_msg)
        except Exception:
            # 最后的备选方案：只打印 ASCII 字符
            print(msg.encode('ascii', errors='replace').decode('ascii'))

# ============================================================
# 常量配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "unified_outputs")

# 确保目录存在
os.makedirs(FONTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# FFmpeg 路径配置
_HEYGEM_DIR = os.path.join(PROJECT_DIR, "heygem-win-50")
_HEYGEM_FFMPEG_DIR = os.path.join(_HEYGEM_DIR, "py39", "ffmpeg", "bin")

_FFMPEG = None
_FFPROBE = None

_CANDIDATE_FFMPEG = [
    os.path.join(_HEYGEM_FFMPEG_DIR, "ffmpeg.exe"),
    os.path.join(PROJECT_DIR, "ffmpeg_bin", "ffmpeg.exe"),
    os.path.join(PROJECT_DIR, "ffmpeg", "ffmpeg.exe"),
]
_CANDIDATE_FFPROBE = [
    os.path.join(_HEYGEM_FFMPEG_DIR, "ffprobe.exe"),
    os.path.join(PROJECT_DIR, "ffmpeg_bin", "ffprobe.exe"),
    os.path.join(PROJECT_DIR, "ffmpeg", "ffprobe.exe"),
]

# imageio_ffmpeg 自带 ffmpeg 二进制，作为兜底
try:
    import imageio_ffmpeg as _ioff
    _io_ffmpeg_path = _ioff.get_ffmpeg_exe()
    if _io_ffmpeg_path and os.path.exists(_io_ffmpeg_path):
        _CANDIDATE_FFMPEG.append(_io_ffmpeg_path)
        # ffprobe 可能在同目录下
        _io_ffprobe = os.path.join(os.path.dirname(_io_ffmpeg_path), "ffprobe.exe")
        if not os.path.exists(_io_ffprobe):
            _io_ffprobe = os.path.join(os.path.dirname(_io_ffmpeg_path), "ffprobe")
        if os.path.exists(_io_ffprobe):
            _CANDIDATE_FFPROBE.append(_io_ffprobe)
except Exception:
    pass

for _p in _CANDIDATE_FFMPEG:
    if os.path.exists(_p):
        _FFMPEG = _p
        break
if not _FFMPEG:
    _FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

for _p in _CANDIDATE_FFPROBE:
    if os.path.exists(_p):
        _FFPROBE = _p
        break
if not _FFPROBE:
    # ffprobe 可能在 ffmpeg 同目录
    if _FFMPEG and os.path.exists(_FFMPEG):
        _maybe_probe = os.path.join(os.path.dirname(_FFMPEG), "ffprobe" + (".exe" if sys.platform == "win32" else ""))
        if os.path.exists(_maybe_probe):
            _FFPROBE = _maybe_probe
if not _FFPROBE:
    _FFPROBE = shutil.which("ffprobe") or "ffprobe"

# 打印ffmpeg路径用于调试
try:
    print(f"[SUBTITLE] FFmpeg路径: {_FFMPEG}", flush=True)
    print(f"[SUBTITLE] FFprobe路径: {_FFPROBE}", flush=True)
    if not os.path.exists(_FFMPEG):
        print(f"[SUBTITLE] 警告: FFmpeg不存在于 {_FFMPEG}", flush=True)
        print(f"[SUBTITLE] 尝试的路径:", flush=True)
        for _p in _CANDIDATE_FFMPEG:
            print(f"  - {_p} (存在: {os.path.exists(_p)})", flush=True)
    if not os.path.exists(_FFPROBE):
        print(f"[SUBTITLE] 警告: FFprobe不存在于 {_FFPROBE}", flush=True)
        print(f"[SUBTITLE] 尝试的路径:", flush=True)
        for _p in _CANDIDATE_FFPROBE:
            print(f"  - {_p} (存在: {os.path.exists(_p)})", flush=True)
except Exception as e:
    print(f"[SUBTITLE] 打印路径信息失败: {e}", flush=True)

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
FONTS_MERGED_PATH = os.path.join(BASE_DIR, "fonts_merged.json")
FONT_CACHE_DIR = os.path.join(BASE_DIR, "font_cache")
FONT_USAGE_PATH = os.path.join(BASE_DIR, "font_usage.json")

def _load_fonts_merged() -> dict:
    """加载 fonts_merged.json"""
    try:
        with open(FONTS_MERGED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"fonts": [], "categories": {}}

def _load_font_usage() -> dict:
    """加载用户字体使用记录 {font_name: count}"""
    try:
        with open(FONT_USAGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def record_font_usage(font_name: str):
    """记录用户使用了某个字体（生成字幕时调用）"""
    if not font_name or font_name in ("系统字体", "默认字体"):
        return
    usage = _load_font_usage()
    usage[font_name] = usage.get(font_name, 0) + 1
    try:
        with open(FONT_USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(usage, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_font_choices() -> List[str]:
    """获取字体选择列表，第一项为系统字体（兼容旧逻辑）"""
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

def get_font_choices_grouped() -> list:
    """从 fonts_merged.json 读取字体列表，按分组返回扁平 choices
    
    排序规则：
    0. 系统字体（Windows 内置）→ 始终置顶
    1. 用户使用过的字体 → 置顶（按使用次数降序），标记【最近使用】
    2. 每个分组内按 popular 降序排列
    """
    data = _load_fonts_merged()
    fonts = data.get("fonts", [])
    
    if not fonts:
        return [("🖥️ 系统字体（默认）", "系统字体"), ("【中文简体】思源黑体 Bold", "SourceHanSansCN-Bold")]
    
    usage = _load_font_usage()
    
    # 按 category 分组
    groups: Dict[str, List[tuple]] = {}
    cat_labels: Dict[str, str] = {}
    used_fonts = []  # 用户使用过的字体
    
    for f in fonts:
        cat = f.get("category", "other")
        label = f.get("category_label", cat)
        cat_labels[cat] = label
        if cat not in groups:
            groups[cat] = []
        display = f.get("display_name") or f.get("name", "")
        value = f.get("name", "")
        pop = f.get("popular", 0)
        use_count = usage.get(value, 0)
        if display and value:
            if use_count > 0:
                used_fonts.append((f"⭐ {display}", value, use_count))
            groups[cat].append((f"【{label}】{display}", value, pop))
    
    # 用户使用过的按次数降序
    used_fonts.sort(key=lambda x: -x[2])
    used_names = {v for _, v, _ in used_fonts}
    
    # 每个分组内按 popular 降序
    for cat in groups:
        groups[cat].sort(key=lambda x: -x[2])
    
    result = []
    
    # 系统字体始终在最前面
    result.append(("🖥️ 系统字体（默认）", "系统字体"))
    
    # 再放用户常用字体
    if used_fonts:
        result.extend((d, v) for d, v, _ in used_fonts)
    
    # 再按分组放其余字体（跳过已在常用中的）
    order = ["zh_cn", "zh_tw", "en"]
    for cat in order:
        if cat in groups:
            result.extend((d, v) for d, v, _ in groups[cat] if v not in used_names)
    for cat, items in groups.items():
        if cat not in order:
            result.extend((d, v) for d, v, _ in items if v not in used_names)
    
    return result

def get_font_info(font_name: str) -> Optional[dict]:
    """根据字体 name 获取完整信息"""
    data = _load_fonts_merged()
    for f in data.get("fonts", []):
        if f.get("name") == font_name:
            return f
    return None

def get_font_preview_path(font_name: str) -> str:
    """获取字体的 cache_font 路径（用于预览）"""
    info = get_font_info(font_name)
    if not info:
        return ""
    cache_path = info.get("cache_font", "")
    if cache_path:
        full = os.path.join(BASE_DIR, cache_path)
        if os.path.exists(full):
            return full
    return ""


def ensure_font_downloaded(font_name: str, progress_cb=None) -> str:
    """确保字体文件存在于 fonts/ 目录，不存在则下载（参考 BGM 直连下载方式）

    返回字体文件的完整路径，失败返回空字符串
    """
    if not font_name or font_name in ("系统字体", "默认字体"):
        return ""

    info = get_font_info(font_name)
    if not info:
        print(f"[FONT] 未找到字体信息: {font_name}")
        return ""

    filename = info.get("filename", "")
    if not filename:
        return ""

    # 检查 fonts/ 目录是否已有（完整版）
    target = os.path.join(FONTS_DIR, filename)
    expected_size = info.get("size", 0)
    if os.path.exists(target):
        actual_size = os.path.getsize(target)
        if expected_size > 0 and actual_size >= expected_size * 0.5:
            print(f"[FONT] 字体已存在(完整版): {target} ({actual_size} bytes)")
            return target
        elif expected_size == 0 and actual_size > 100000:
            print(f"[FONT] 字体已存在: {target} ({actual_size} bytes)")
            return target
        else:
            print(f"[FONT] 字体文件太小({actual_size} vs 预期{expected_size})，需要下载完整版")
            try: os.remove(target)
            except Exception: pass

    # 需要下载
    url = info.get("download_url", "")
    if not url:
        print(f"[FONT] 无下载链接: {font_name}")
        return ""

    display = info.get("display_name", font_name)
    print(f"[FONT] 开始下载字体: {font_name} from {url}")
    if progress_cb:
        try: progress_cb(0.1, f"⬇️ 下载字体: {display}...")
        except Exception: pass

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }

    tmp_path = target + ".tmp"

    def _looks_like_html(p):
        """检查文件是否为 HTML 错误页面"""
        try:
            with open(p, "rb") as f:
                head = f.read(256).lstrip()
            if not head:
                return True
            low = head[:64].lower()
            return low.startswith(b"<!doctype") or low.startswith(b"<html") or low.startswith(b"<head")
        except Exception:
            return False

    def _file_valid(p):
        return os.path.exists(p) and os.path.getsize(p) > 10000 and not _looks_like_html(p)

    def _do_stream_write(resp_iter, total):
        """通用流式写入 + 进度回调"""
        downloaded = 0
        with open(tmp_path, "wb") as f:
            for chunk in resp_iter:
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total > 0:
                        pct = 0.1 + 0.85 * (downloaded / total)
                        try: progress_cb(min(pct, 0.95), f"⬇️ 下载字体: {display} ({downloaded//1024}KB)")
                        except Exception: pass
        return downloaded

    # ---- 方法1: requests 默认（和 BGM 下载完全一致） ----
    def _dl_requests():
        try:
            import requests as _req
        except ImportError:
            return False
        last_err = None
        for _attempt in range(3):
            try:
                if os.path.exists(tmp_path):
                    try: os.remove(tmp_path)
                    except Exception: pass
                with _req.get(url, headers=headers, stream=True,
                              allow_redirects=True, timeout=(15, 120)) as r:
                    total = int(r.headers.get("content-length", 0))
                    _do_stream_write(r.iter_content(chunk_size=262144), total)
                if _file_valid(tmp_path):
                    return True
                last_err = Exception("invalid file")
            except Exception as e:
                last_err = e
                print(f"[FONT] requests 第{_attempt+1}次失败: {e}")
            time.sleep(0.5)
        return False

    # ---- 方法2: requests 直连（禁用系统代理） ----
    def _dl_requests_noproxy():
        try:
            import requests as _req
        except ImportError:
            return False
        try:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass
            sess = _req.Session()
            sess.trust_env = False
            with sess.get(url, headers=headers, stream=True,
                          allow_redirects=True, timeout=(15, 120)) as r:
                total = int(r.headers.get("content-length", 0))
                _do_stream_write(r.iter_content(chunk_size=262144), total)
            sess.close()
            return _file_valid(tmp_path)
        except Exception as e:
            print(f"[FONT] requests(noproxy) 失败: {e}")
            return False

    # ---- 方法3: urllib 直连 ----
    def _dl_urllib():
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = resp.read(262144)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb and total > 0:
                            pct = 0.1 + 0.85 * (downloaded / total)
                            try: progress_cb(min(pct, 0.95), f"⬇️ 下载字体: {display} ({downloaded//1024}KB)")
                            except Exception: pass
            return _file_valid(tmp_path)
        except Exception as e:
            print(f"[FONT] urllib 失败: {e}")
            return False

    # ---- 方法4: PowerShell 兜底（走系统网络栈，和浏览器最接近） ----
    def _dl_powershell():
        try:
            u = url.replace("'", "''")
            p = tmp_path.replace("'", "''")
            cmd = (
                "$ProgressPreference='SilentlyContinue';"
                "try { "
                f"Invoke-WebRequest -UseBasicParsing -Uri '{u}' -OutFile '{p}' "
                f"-Headers @{{'User-Agent'='{headers['User-Agent']}'}}; "
                "exit 0 } catch { exit 1 }"
            )
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                capture_output=True, text=True,
                creationflags=_NWIN, timeout=120)
            return r.returncode == 0 and _file_valid(tmp_path)
        except Exception as e:
            print(f"[FONT] powershell 失败: {e}")
            return False

    try:
        ok = False
        methods = [
            ("requests", _dl_requests),
            ("requests-noproxy", _dl_requests_noproxy),
            ("urllib", _dl_urllib),
            ("powershell", _dl_powershell),
        ]
        for method_name, method in methods:
            print(f"[FONT] 尝试 {method_name} 下载...")
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass
            if method():
                print(f"[FONT] {method_name} 下载成功")
                ok = True
                break
            else:
                print(f"[FONT] {method_name} 失败，尝试下一个方法")

        if ok and _file_valid(tmp_path):
            shutil.move(tmp_path, target)
            print(f"[FONT] 下载完成: {target} ({os.path.getsize(target)} bytes)")
            if progress_cb:
                try: progress_cb(1.0, "✅ 字体下载完成")
                except Exception: pass
            return target
        else:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass
            print(f"[FONT] 所有下载方式均失败")
            return ""
    except Exception as e:
        print(f"[FONT] 下载异常: {e}")
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        return ""




def get_font_family_name(font_name: str) -> str:
    """读取字体文件内部的 family name（ASS/libass 需要用内部名称匹配）
    
    优先从 fonts/ 目录读取，其次从 font_cache/ 读取。
    返回内部 family name，失败则返回原始 font_name。
    """
    if not font_name or font_name in ("系统字体", "默认字体"):
        return "Source Han Sans CN Bold"
    
    info = get_font_info(font_name)
    if not info:
        return font_name
    
    filename = info.get("filename", "")
    
    # 查找可用的字体文件路径
    font_path = ""
    if filename:
        p = os.path.join(FONTS_DIR, filename)
        if os.path.exists(p):
            font_path = p
    if not font_path:
        cache = info.get("cache_font", "")
        if cache:
            p = os.path.join(BASE_DIR, cache)
            if os.path.exists(p):
                font_path = p
    
    if not font_path:
        return font_name
    
    try:
        from PIL import ImageFont
        pil_font = ImageFont.truetype(font_path, 20)
        family, style = pil_font.getname()
        if family:
            print(f"[FONT] '{font_name}' -> internal family: '{family}'")
            return family
    except Exception as e:
        print(f"[FONT] 读取字体内部名称失败: {e}")
    
    return font_name


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

    fn = get_font_family_name(font_name) if font_name and font_name not in ("默认字体", "系统字体") else "Source Han Sans CN Bold"
    print(f"[SUBTITLE] font_name='{font_name}' -> ASS Fontname='{fn}'")

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

    # ── 标题样式（两行不同样式） ──
    title_style_line = ""
    title_event = ""
    if title_text and title_text.strip():
        title_display = title_text.strip()

        # 支持两行：\n 或 \N 或 ｜ 分隔
        tmp = title_display.replace("\\N", "\n")
        if "｜" in tmp:
            tmp = tmp.replace("｜", "\n")
        parts = [p.strip() for p in tmp.split("\n") if p.strip()]
        line1 = (parts[0] if parts else "")
        line2 = (parts[1] if len(parts) > 1 else "")

        # 样式固定：
        # 第一行：橙色字 + 黑描边
        # 第二行：黑字 + 白描边
        t1_tc = _hex2ass("#FFA500")
        t1_oc = _hex2ass("#000000")
        t2_tc = _hex2ass("#000000")
        t2_oc = _hex2ass("#FFFFFF")

        t_fs  = max(12, min(96, int(title_font_size or 68)))
        t_mv  = max(10, min(400, int(title_margin_top or 200)))
        t_dur = max(1, int(title_duration or 5))

        # 标题换行：根据字体大小和视频宽度计算（每行单独裁切）
        # 修复：使用更准确的字符宽度计算（中文字符约为字号的1.1倍）
        _title_margin = 80
        _title_usable = (play_res_x - _title_margin * 2)
        _title_char_w = t_fs * 1.1  # 中文字符宽度约为字号的1.1倍
        _title_max_chars = max(10, int(_title_usable / _title_char_w))  # 至少显示10个字
        if len(line1) > _title_max_chars:
            line1 = line1[:_title_max_chars]
        if len(line2) > _title_max_chars:
            line2 = line2[:_title_max_chars]

        # 两套样式（同位置对齐方式，但 MarginV 由事件用 \pos 控制）
        title_style_line = (
            f"Style: Title1,{fn},{t_fs},"
            f"{t1_tc},&H000000FF&,{t1_oc},&H00000000&,"
            f"1,0,0,0,100,100,0,0,{border_style},{osz},0,"
            f"8,{_title_margin},{_title_margin},{t_mv},1\n"
            f"Style: Title2,{fn},{t_fs},"
            f"{t2_tc},&H000000FF&,{t2_oc},&H00000000&,"
            f"1,0,0,0,100,100,0,0,{border_style},{osz},0,"
            f"8,{_title_margin},{_title_margin},{t_mv},1\n"
        )

        t_ts = _ass_time(0)
        t_te = _ass_time(t_dur)
        # 使用 \pos 做垂直偏移：第二行下移一行高度
        cx = play_res_x // 2
        y1 = t_mv
        y2 = t_mv + int(t_fs * 1.15)
        if line1:
            title_event += f"Dialogue: 2,{t_ts},{t_te},Title1,,0,0,0,,{{\\pos({cx},{y1})\\an8\\c{t1_tc}\\3c{t1_oc}}}{line1}\n"
        if line2:
            title_event += f"Dialogue: 2,{t_ts},{t_te},Title2,,0,0,0,,{{\\pos({cx},{y2})\\an8\\c{t2_tc}\\3c{t2_oc}}}{line2}\n"

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
# 片头生成：人物抠图 + 白色描边 + 标题
# ═══════════════════════════════════════════════
def _extract_first_frame(video_path: str, out_path: str) -> bool:
    """从视频提取第一帧"""
    try:
        subprocess.run(
            [_FFMPEG, "-y", "-i", str(video_path),
             "-vframes", "1", "-q:v", "2", out_path],
            capture_output=True, creationflags=_NWIN, timeout=30)
        return os.path.exists(out_path)
    except Exception as e:
        print(f"[INTRO] 提取首帧失败: {e}")
        return False


def _remove_bg(img_path: str) -> "Image.Image":
    """用 rembg 抠图，返回 RGBA 图片"""
    from rembg import remove
    from PIL import Image
    inp = Image.open(img_path).convert("RGBA")
    out = remove(inp)
    return out


def _add_white_outline(rgba_img: "Image.Image", thickness: int = 18, gap: int = 10) -> "Image.Image":
    """给抠出的人物添加白色粗描边效果，描边与人物之间有间距"""
    from PIL import Image, ImageFilter
    
    # 提取 alpha 通道
    alpha = rgba_img.split()[3]
    
    # 先膨胀出间距（gap）
    gap_alpha = alpha
    for _ in range(gap):
        gap_alpha = gap_alpha.filter(ImageFilter.MaxFilter(3))
    
    # 再膨胀出描边厚度（thickness）
    expanded = gap_alpha
    for _ in range(thickness):
        expanded = expanded.filter(ImageFilter.MaxFilter(3))
    
    # 创建白色描边层
    w, h = rgba_img.size
    outline_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # 白色填充膨胀区域
    white = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    outline_layer.paste(white, mask=expanded)
    
    # 挖掉间距区域（让描边和人物之间透明）
    transparent = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    outline_layer.paste(transparent, mask=gap_alpha)
    
    # 把原图贴回去
    outline_layer.paste(rgba_img, mask=alpha)
    
    return outline_layer


def _get_video_resolution(video_path: str) -> tuple:
    """获取视频分辨率"""
    try:
        r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", str(video_path)],
            capture_output=True, text=True, creationflags=_NWIN, timeout=10)
        streams = json.loads(r.stdout).get("streams", [])
        if streams:
            return int(streams[0].get("width", 1280)), int(streams[0].get("height", 720))
    except Exception:
        pass
    return 1280, 720


def _get_video_fps(video_path: str) -> float:
    """获取视频帧率"""
    try:
        r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", str(video_path)],
            capture_output=True, text=True, creationflags=_NWIN, timeout=10)
        streams = json.loads(r.stdout).get("streams", [])
        if streams:
            fps_str = streams[0].get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
    except Exception:
        pass
    return 30.0


def generate_intro(video_path: str, title_text: str,
                   title_font_name: str = "", title_font_size: int = 48,
                   title_color: str = "#FFD700",
                   title_outline_color: str = "#000000",
                   bg_gradient: tuple = ((30, 30, 60), (15, 15, 40)),
                   outline_thickness: int = 18,
                   progress_cb=None) -> str:
    """生成1秒片头视频：人物抠图+白色描边+标题

    返回片头视频路径，失败返回空字符串。
    """
    from PIL import Image, ImageDraw, ImageFont

    def _prog(pct, msg):
        if progress_cb:
            try: progress_cb(pct, msg)
            except Exception: pass

    if not video_path or not os.path.exists(str(video_path)):
        print(f"[INTRO] 视频路径无效: {video_path}")
        return ""

    _safe_print(f"[INTRO] 开始生成片头: video={video_path}, title='{title_text}'")

    ts = int(time.time())
    frame_path = os.path.join(OUTPUT_DIR, f"intro_frame_{ts}.png")
    intro_img_path = os.path.join(OUTPUT_DIR, f"intro_img_{ts}.png")
    intro_vid_path = os.path.join(OUTPUT_DIR, f"intro_{ts}.mp4")

    try:
        # 1. 提取第一帧
        _prog(0.05, "🎬 提取视频首帧...")
        print(f"[INTRO] 提取首帧: {video_path} -> {frame_path}")
        if not _extract_first_frame(video_path, frame_path):
            print("[INTRO] 提取首帧失败")
            return ""

        # 2. 获取视频分辨率和帧率
        vid_w, vid_h = _get_video_resolution(video_path)
        fps = _get_video_fps(video_path)

        # 3. 抠图
        _prog(0.15, "✂️ 人物抠图中...")
        print(f"[INTRO] 开始抠图: {frame_path}")
        person = _remove_bg(frame_path)
        print(f"[INTRO] 抠图完成，图片大小: {person.size}")

        # 4. 添加白色描边
        _prog(0.45, "🖌️ 添加描边效果...")
        person_outlined = _add_white_outline(person, thickness=outline_thickness)
        print(f"[INTRO] 描边完成")

        # 5. 合成片头图片
        _prog(0.55, "🎨 合成片头画面...")

        # 创建渐变背景
        canvas = Image.new("RGBA", (vid_w, vid_h), (0, 0, 0, 255))
        draw = ImageDraw.Draw(canvas)
        c1, c2 = bg_gradient
        for y in range(vid_h):
            ratio = y / vid_h
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            draw.line([(0, y), (vid_w, y)], fill=(r, g, b, 255))

        # 缩放人物到画面高度的 85%，居中偏下
        pw, ph = person_outlined.size
        target_h = int(vid_h * 0.85)
        scale = target_h / ph
        target_w = int(pw * scale)
        person_resized = person_outlined.resize((target_w, target_h), Image.LANCZOS)

        # 人物居中，底部对齐
        px = (vid_w - target_w) // 2
        py = vid_h - target_h
        canvas.paste(person_resized, (px, py), person_resized)

        # 6. 添加标题文字
        if title_text and title_text.strip():
            _prog(0.65, "📝 添加标题文字...")
            # 加载字体
            font = None
            font_sz = int(title_font_size or 48)

            # 尝试加载用户选择的字体
            if title_font_name and title_font_name not in ("系统字体", "默认字体", ""):
                try:
                    font_file = ensure_font_downloaded(title_font_name)
                    if font_file and os.path.exists(font_file):
                        font = ImageFont.truetype(font_file, font_sz)
                except Exception:
                    pass

            # 回退到思源黑体或系统字体
            if font is None:
                for fallback in [
                    os.path.join(FONTS_DIR, "SourceHanSansCN-Bold.ttf"),
                    os.path.join(FONTS_DIR, "SourceHanSansCN-Bold.otf"),
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                ]:
                    if os.path.exists(fallback):
                        try:
                            font = ImageFont.truetype(fallback, font_sz)
                            break
                        except Exception:
                            continue
            if font is None:
                font = ImageFont.load_default()

            # 处理两行标题（支持多种分隔符）
            title = title_text.strip()
            title_lines = []
            for sep in ("\n", "｜", "|", "\\"):
                if sep in title:
                    parts = [p.strip() for p in title.split(sep) if p.strip()]
                    title_lines = parts[:2]  # 最多取两行
                    break
            if not title_lines:
                title_lines = [title]

            # 计算文字位置（顶部居中，距顶 8%）
            oc = tuple(int(title_outline_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            tc = tuple(int(title_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            outline_w = max(2, font_sz // 12)

            # 计算行高和起始Y位置
            line_height = int(font_sz * 1.3)
            total_height = line_height * len(title_lines)
            start_y = int(vid_h * 0.08)

            # 绘制每一行
            for i, line in enumerate(title_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
                tx = (vid_w - tw) // 2
                ty = start_y + i * line_height

                # 画描边（8方向偏移）
                for dx in range(-outline_w, outline_w + 1):
                    for dy in range(-outline_w, outline_w + 1):
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((tx + dx, ty + dy), line, font=font, fill=(*oc, 255))
                # 画正文
                draw.text((tx, ty), line, font=font, fill=(*tc, 255))

        # 保存合成图片
        canvas_rgb = canvas.convert("RGB")
        canvas_rgb.save(intro_img_path, quality=95)

        # 7. 用 ffmpeg 生成1秒视频（匹配原视频帧率）
        _prog(0.75, "🎬 生成片头视频...")
        cmd = [
            _FFMPEG, "-y",
            "-loop", "1",
            "-i", intro_img_path,
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", "1",
            "-r", str(int(fps)),
            "-vf", f"scale={vid_w}:{vid_h}:flags=lanczos",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-shortest",
            intro_vid_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              creationflags=_NWIN, timeout=60, errors="replace")
        if proc.returncode != 0 or not os.path.exists(intro_vid_path):
            print(f"[INTRO] ffmpeg 生成片头失败: {proc.stderr[-500:]}")
            return ""

        # 验证生成的片头视频
        if os.path.getsize(intro_vid_path) < 1024:
            print(f"[INTRO] 片头视频文件太小，可能生成失败")
            return ""

        print(f"[INTRO] 片头视频生成成功: {intro_vid_path} ({os.path.getsize(intro_vid_path)} 字节)")

        _prog(0.90, "片头生成完成")
        return intro_vid_path

    except ImportError as e:
        print(f"[INTRO] 缺少依赖: {e}. 请安装: pip install rembg pillow")
        return ""
    except Exception as e:
        print(f"[INTRO] 片头生成失败: {e}")
        import traceback; traceback.print_exc()
        return ""
    finally:
        # 清理临时文件
        for f in (frame_path, intro_img_path):
            try:
                if os.path.exists(f): os.remove(f)
            except Exception:
                pass


def concat_intro_and_video(intro_path: str, main_path: str, output_path: str) -> bool:
    """用 ffmpeg concat 拼接片头和正片"""
    if not intro_path or not os.path.exists(intro_path):
        print(f"[INTRO] 片头文件不存在: {intro_path}")
        return False
    if not main_path or not os.path.exists(main_path):
        print(f"[INTRO] 主视频文件不存在: {main_path}")
        return False

    # 验证文件大小
    intro_size = os.path.getsize(intro_path)
    main_size = os.path.getsize(main_path)
    print(f"[INTRO] 片头大小: {intro_size} 字节, 主视频大小: {main_size} 字节")

    if intro_size < 1024 or main_size < 1024:
        print(f"[INTRO] 文件太小，可能损坏")
        return False

    concat_list = os.path.join(OUTPUT_DIR, f"concat_{int(time.time())}.txt")
    try:
        with open(concat_list, "w", encoding="utf-8") as f:
            intro_abs = os.path.abspath(intro_path).replace(chr(92), "/")
            main_abs = os.path.abspath(main_path).replace(chr(92), "/")
            f.write(f"file '{intro_abs}'\n")
            f.write(f"file '{main_abs}'\n")

        print(f"[INTRO] 开始拼接: {intro_abs} + {main_abs}")

        # 直接使用重编码方式，确保兼容性
        cmd = [
            _FFMPEG, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              creationflags=_NWIN, timeout=300, errors="replace")
        if proc.returncode != 0:
            print(f"[INTRO] concat 失败: {proc.stderr[-500:]}")
            return False

        success = os.path.exists(output_path) and os.path.getsize(output_path) > 1024
        if success:
            print(f"[INTRO] 拼接成功: {output_path} ({os.path.getsize(output_path)} 字节)")
        else:
            print(f"[INTRO] 拼接失败: 输出文件不存在或太小")
        return success
    except Exception as e:
        print(f"[INTRO] concat 异常: {e}")
        import traceback; traceback.print_exc()
        return False
    finally:
        try:
            if os.path.exists(concat_list): os.remove(concat_list)
        except Exception:
            pass


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
                   intro_enable=False,
                   progress_cb=None):
    def _prog(pct, msg):
        if progress_cb:
            try: progress_cb(pct, msg)
            except Exception: pass

    if not video_path or not os.path.exists(str(video_path)):
        raise RuntimeError("请先完成视频合成")

    print(f"[SUBTITLE] intro_enable={intro_enable}, title_text='{title_text}'")

    # 规范化颜色（防 Gradio ColorPicker 传奇怪格式）
    text_color    = normalize_color(text_color,    "#FFFFFF")
    hi_color      = normalize_color(hi_color,      "#FFD700")
    outline_color = normalize_color(outline_color, "#000000")
    bg_color      = normalize_color(bg_color,      "#000000")

    # 确保字体文件已下载到 fonts/ 目录
    if font_name and font_name not in ("系统字体", "默认字体", ""):
        _prog(0.02, "🔤 检查字体文件...")
        _font_path = ensure_font_downloaded(font_name, progress_cb=_prog)
        if _font_path:
            record_font_usage(font_name)
        else:
            print(f"[SUBTITLE] 字体 '{font_name}' 下载失败，使用系统字体")

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

    # 检查ffmpeg是否存在
    if not os.path.exists(_FFMPEG):
        error_msg = f"FFmpeg不存在于 {_FFMPEG}，请检查安装"
        print(f"[SUBTITLE] 错误: {error_msg}", flush=True)
        print(f"[SUBTITLE] 尝试的路径:", flush=True)
        for _p in _CANDIDATE_FFMPEG:
            print(f"  - {_p} (存在: {os.path.exists(_p)})", flush=True)
        raise RuntimeError(error_msg)

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

    # ── 片头生成与拼接 ──
    if intro_enable:
        _safe_print(f"[INTRO] 开始生成片头，title_text='{title_text}'")
        if not title_text or not title_text.strip():
            _safe_print("[INTRO] 警告: 标题为空，片头可能无标题文字")

        _prog(0.82, "🎬 生成片头...")
        try:
            intro_path = generate_intro(
                video_path, (title_text or "").strip(),
                title_font_name=font_name,
                title_font_size=int(title_font_size or 48),
                title_color=title_color,
                title_outline_color=title_outline_color,
                progress_cb=lambda p, m: _prog(0.82 + p * 0.12, m),
            )
            print(f"[INTRO] generate_intro 返回: {intro_path}")

            if intro_path and os.path.exists(intro_path):
                print(f"[INTRO] 片头生成成功: {intro_path} ({os.path.getsize(intro_path)} 字节)")
                _prog(0.94, "🔗 拼接片头与正片...")
                final_path = os.path.join(OUTPUT_DIR, f"intro_sub_{int(time.time())}.mp4")
                print(f"[INTRO] 开始拼接: {intro_path} + {out_path} -> {final_path}")

                if concat_intro_and_video(intro_path, out_path, final_path):
                    # 清理中间文件
                    try: os.remove(out_path)
                    except Exception: pass
                    try: os.remove(intro_path)
                    except Exception: pass
                    out_path = final_path
                    _safe_print(f"[INTRO] 片头拼接成功: {out_path}")
                else:
                    _safe_print("[INTRO] 片头拼接失败，返回无片头版本")
                    try: os.remove(intro_path)
                    except Exception: pass
            else:
                _safe_print(f"[INTRO] 片头生成失败，intro_path={intro_path}, exists={os.path.exists(intro_path) if intro_path else False}")
        except Exception as e:
            _safe_print(f"[INTRO] 片头处理异常: {e}")
            import traceback; traceback.print_exc()

    _prog(1.0, "完成")
    return out_path