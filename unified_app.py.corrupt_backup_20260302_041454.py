# -*- coding: utf-8 -*-
import os, sys, time, subprocess, traceback, shutil, re, json, queue as _queue, threading
import asyncio
import base64
import ctypes
import ctypes.wintypes

# 鈹€鈹€ 鍔犺浇 .env 閰嶇疆 鈹€鈹€
def load_env_file():
    """鍔犺浇.env鏂囦欢鍒扮幆澧冨彉閲?""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

            if not os.getenv("LIPVOICE_SIGN"):
                enc = (os.getenv("LIPVOICE_SIGN_ENC") or "").strip()
                if enc:
                    try:
                        os.environ["LIPVOICE_SIGN"] = _dpapi_decrypt_text(enc)
                    except Exception as _e:
                        print(f"[WARN] LIPVOICE_SIGN_ENC 瑙ｅ瘑澶辫触: {_e}")
        except Exception as e:
            print(f"[WARN] 鍔犺浇.env鏂囦欢澶辫触: {e}")


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _dpapi_decrypt_text(b64_text: str) -> str:
    if sys.platform != "win32":
        raise RuntimeError("DPAPI only supported on Windows")
    raw = base64.b64decode(b64_text.encode("utf-8"))
    in_blob = _DATA_BLOB()
    in_blob.cbData = len(raw)
    in_blob.pbData = ctypes.cast(ctypes.create_string_buffer(raw, len(raw)), ctypes.POINTER(ctypes.c_byte))
    out_blob = _DATA_BLOB()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if not crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        out = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return out.decode("utf-8")
    finally:
        kernel32.LocalFree(out_blob.pbData)


def dpapi_encrypt_text_to_b64(plain_text: str) -> str:
    if sys.platform != "win32":
        raise RuntimeError("DPAPI only supported on Windows")
    if plain_text is None:
        plain_text = ""
    raw = plain_text.encode("utf-8")
    in_blob = _DATA_BLOB()
    in_blob.cbData = len(raw)
    in_blob.pbData = ctypes.cast(ctypes.create_string_buffer(raw, len(raw)), ctypes.POINTER(ctypes.c_byte))
    out_blob = _DATA_BLOB()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        out = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return base64.b64encode(out).decode("utf-8")
    finally:
        kernel32.LocalFree(out_blob.pbData)

load_env_file()

# 鈹€鈹€ WebSocket 妯″潡锛堢敤浜庢彁鍙栨枃妗堝姛鑳斤級鈹€鈹€
try:
    import websockets
    _WS_OK = True
except ImportError:
    _WS_OK = False
    print("[WARN] websockets 妯″潡鏈畨瑁咃紝鎻愬彇鏂囨鍔熻兘灏嗕笉鍙敤")

# 鈹€鈹€ 灏?libs/ 鍔犲叆妯″潡鎼滅储璺緞 鈹€鈹€
_LIBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
if _LIBS_DIR not in sys.path:
    sys.path.insert(0, _LIBS_DIR)

# 鈹€鈹€ 鏂板姛鑳芥ā鍧楋紙鏁板瓧浜?/ 闊宠壊 / 瀛楀箷锛夆攢鈹€
try:
    import lib_avatar as _av
    import lib_voice  as _vc
    import lib_subtitle as _sub
    import lib_pip     as _pip
    import lib_pip_websocket as _pip_ws  # WebSocket 鐢讳腑鐢绘ā鍧?
    _LIBS_OK = True
except Exception as _libs_err:
    _LIBS_OK = False
    import warnings
    warnings.warn(f"[鎵╁睍妯″潡鍔犺浇澶辫触] {_libs_err}")
    # 鍒涘缓瀹夊叏瀛樻牴锛岄伩鍏嶆ā鍧楁湭鍔犺浇鏃?NameError
    class _StubLib:
        def get_choices(self): return ["锛堟ā鍧楁湭鍔犺浇锛?]
        def get_path(self, n): return None
        def render_gallery(self, *a, **kw): return '<div style="color:#dc2626;padding:12px;">鈿?鎵╁睍妯″潡鍔犺浇澶辫触锛岃妫€鏌?lib_avatar/lib_voice/lib_subtitle.py</div>'
        def add_avatar(self, *a): return False, "妯″潡鏈姞杞?
        def del_avatar(self, *a): return False, "妯″潡鏈姞杞?
        def add_voice(self, *a): return False, "妯″潡鏈姞杞?
        def del_voice(self, *a): return False, "妯″潡鏈姞杞?
        def get_font_choices(self): return ["榛樿瀛椾綋"]
        def burn_subtitles(self, *a, **kw): raise RuntimeError("瀛楀箷妯″潡鏈姞杞?)
    _av  = _StubLib()
    _vc  = _StubLib()
    _sub = _StubLib()
    _pip = type('_StubPip', (), {
        'apply_pip_online': staticmethod(lambda *a, **kw: ""),
        'apply_pip_online_smart': staticmethod(lambda *a, **kw: ""),
        'apply_pip_local':  staticmethod(lambda *a, **kw: ""),
    })()
    _pip_ws = type('_StubPipWs', (), {
        'generate_pip_via_extractor': staticmethod(lambda *a, **kw: ""),
        'generate_and_compose_pips': staticmethod(lambda *a, **kw: ""),
    })()

# 鈹€鈹€ 娓呴櫎浠ｇ悊 鈹€鈹€
for _k in ('http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','all_proxy'):
    os.environ.pop(_k, None)
    os.environ[_k] = ''
os.environ['no_proxy'] = '127.0.0.1,localhost'
os.environ['NO_PROXY'] = '127.0.0.1,localhost'

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
PLATFORM_AGREEMENT_FILE = os.path.join(BASE_DIR, "platform_ai_usage_agreement.txt")
LEGACY_AGREEMENT_FILE = os.path.join(BASE_DIR, "platform_publish_agreement.txt")
DOUYIN_AGREEMENT_FILE = os.path.join(BASE_DIR, "docs", "user_agreement.md")  # 鍏煎鏃х増鏈?
INDEXTTS_DIR   = os.path.join(BASE_DIR, "_internal_tts")
HEYGEM_DIR     = os.path.join(BASE_DIR, "heygem-win-50")
OUTPUT_DIR     = os.path.join(BASE_DIR, "unified_outputs")
WORKSPACE_RECORDS_FILE = os.path.join(OUTPUT_DIR, "workspace_records.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MUSIC_DATABASE_FILE = os.path.join(BASE_DIR, "data", "music_database.json")
BGM_CACHE_DIR = os.path.join(BASE_DIR, "bgm_cache")  # 鐙珛鐨凚GM缂撳瓨鐩綍
os.makedirs(BGM_CACHE_DIR, exist_ok=True)

HF_CACHE_DIR = os.path.abspath(os.path.join(INDEXTTS_DIR, "checkpoints", "hf_cache"))
os.makedirs(HF_CACHE_DIR, exist_ok=True)
for _e, _v in [
    ('HF_HUB_CACHE', HF_CACHE_DIR), ('HF_HOME', HF_CACHE_DIR),
    ('HUGGINGFACE_HUB_CACHE', HF_CACHE_DIR), ('TRANSFORMERS_CACHE', HF_CACHE_DIR),
    ('TRANSFORMERS_OFFLINE', '1'), ('HF_HUB_OFFLINE', '1'),
]:
    os.environ[_e] = _v

HEYGEM_PYTHON = os.path.join(HEYGEM_DIR, "py39", "python.exe")
HEYGEM_FFMPEG = os.path.join(HEYGEM_DIR, "py39", "ffmpeg", "bin")


def _resolve_ffmpeg_exe():
    p = os.path.join(HEYGEM_FFMPEG, "ffmpeg.exe")
    if os.path.exists(p):
        return p
    return shutil.which("ffmpeg") or "ffmpeg"


def _resolve_ffprobe_exe():
    p = os.path.join(HEYGEM_FFMPEG, "ffprobe.exe")
    if os.path.exists(p):
        return p
    return shutil.which("ffprobe") or "ffprobe"

# 鈹€鈹€ 瑙嗛鍚堟垚璐ㄩ噺棰勮 鈹€鈹€
QUALITY_PRESETS = {
    "鈿?鏋佸揩":   {"inference_steps": 6,  "guidance_scale": 1.0},
    "馃殌 蹇€?:   {"inference_steps": 8,  "guidance_scale": 1.0},
    "鈿栵笍 鏍囧噯":   {"inference_steps": 12, "guidance_scale": 1.2},
    "鉁?楂樿川閲?: {"inference_steps": 20, "guidance_scale": 1.5},
}

# 鈹€鈹€ TTS 鍚堟垚閫熷害棰勮锛堜富瑕佹帶鍒?num_beams 鍜?max_mel_tokens锛夆攢鈹€
TTS_SPEED_PRESETS = {
    "鈿?鏋佸揩":   {"num_beams": 1, "max_mel_tokens": 1200},
    "馃殌 蹇€?:   {"num_beams": 1, "max_mel_tokens": 1500},
    "鈿栵笍 鏍囧噯":   {"num_beams": 2, "max_mel_tokens": 2000},
    "鉁?楂樿川閲?: {"num_beams": 4, "max_mel_tokens": 2500},
}

sys.path.insert(0, INDEXTTS_DIR)
sys.path.insert(0, os.path.join(INDEXTTS_DIR, "indextts"))

import warnings; warnings.filterwarnings("ignore")
import gradio as gr
import logging
logging.getLogger("h11").setLevel(logging.CRITICAL)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

import random

tts = None
APP_NAME = "缁囨ⅵAI澶фā鍨?
APP_SUB  = "AI璇煶鍏嬮殕 路 鏅鸿兘瑙嗛鍚堟垚 路 涓撲笟绾цВ鍐虫柟妗?


def safe_print(msg: str):
    try:
        sys.stdout.write(msg + "\n"); sys.stdout.flush()
    except Exception:
        try:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
        except Exception:
            pass


def _simple_progress_html(stage: str, pct: int, elapsed_s: int = 0) -> str:
    try:
        pct = int(pct)
    except Exception:
        pct = 0
    pct = max(0, min(100, pct))
    bar = max(2, pct)
    stage = (stage or "澶勭悊涓?).strip()
    sub = f"鐢ㄦ椂 {int(elapsed_s)}s" if elapsed_s else ""
    return (
        '<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
        'border:1.5px solid #6366f1;border-radius:12px;'
        'padding:14px 16px 12px;margin:0 0 10px;'
        'font-family:Microsoft YaHei,system-ui,sans-serif;'
        'box-shadow:0 4px 16px rgba(99,102,241,.18);">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<span style="font-size:13px;font-weight:800;color:#e2e8f0;">{stage}</span>'
        f'<span style="margin-left:auto;font-size:14px;font-weight:900;color:#6366f1;">{pct}%</span>'
        '</div>'
        '<div style="background:rgba(99,102,241,.15);border-radius:6px;height:8px;overflow:hidden;">'
        f'<div style="height:100%;width:{bar}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:6px;transition:width .25s;"></div>'
        '</div>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:8px;">{sub}</div>'
        '</div>'
    )


def _dual_progress_html(stage: str, total_pct: int, step_label: str, step_pct: int, elapsed_s: int = 0) -> str:
    """Dual progress bar HTML: total progress + current step progress."""
    total_pct = max(0, min(100, int(total_pct or 0)))
    step_pct = max(0, min(100, int(step_pct or 0)))
    total_bar = max(2, total_pct)
    step_bar = max(2, step_pct)
    stage = (stage or "澶勭悊涓?).strip()
    step_label = (step_label or "").strip()
    sub = f"鐢ㄦ椂 {int(elapsed_s)}s" if elapsed_s else ""
    return (
        '<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
        'border:1.5px solid #6366f1;border-radius:12px;'
        'padding:14px 16px 12px;margin:0 0 10px;'
        'font-family:Microsoft YaHei,system-ui,sans-serif;'
        'box-shadow:0 4px 16px rgba(99,102,241,.18);">'
        # 鎬昏繘搴?
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
        f'<span style="font-size:13px;font-weight:800;color:#e2e8f0;">馃搳 鎬昏繘搴?/span>'
        f'<span style="margin-left:auto;font-size:14px;font-weight:900;color:#6366f1;">{total_pct}%</span>'
        '</div>'
        '<div style="background:rgba(99,102,241,.15);border-radius:6px;height:8px;overflow:hidden;margin-bottom:12px;">'
        f'<div style="height:100%;width:{total_bar}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:6px;transition:width .25s;"></div>'
        '</div>'
        # 姝ラ杩涘害
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
        f'<span style="font-size:12px;font-weight:700;color:#94a3b8;">鈿欙笍 {stage}{(" 路 " + step_label) if step_label else ""}</span>'
        f'<span style="margin-left:auto;font-size:12px;font-weight:800;color:#22d3ee;">{step_pct}%</span>'
        '</div>'
        '<div style="background:rgba(34,211,238,.12);border-radius:6px;height:6px;overflow:hidden;">'
        f'<div style="height:100%;width:{step_bar}%;background:linear-gradient(90deg,#22d3ee,#06b6d4);border-radius:6px;transition:width .25s;"></div>'
        '</div>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:8px;">{sub}</div>'
        '</div>'
    )


# 浠?env鏂囦欢璇诲彇鐗堟湰淇℃伅
def _load_version_from_env():
    """浠?env鏂囦欢璇诲彇鐗堟湰鍙峰拰 build 鍙?""
    env_file = os.path.join(BASE_DIR, ".env")
    version = "1.0.0"  # 榛樿鐗堟湰鍙?
    build = 100
    try:
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 娉ㄦ剰锛欰PP_VERSION_NUMBER 鏄増鏈彿锛堝 "1.0.0"锛?
                    # TTS_MODE 鏄?TTS 妯″紡閫夋嫨锛坙ocal / online锛夛紝涓嶈娣锋穯
                    if line.startswith('APP_VERSION_NUMBER='):
                        version = line.split('=', 1)[1].strip()
                    elif line.startswith('APP_BUILD='):
                        build = int(line.split('=', 1)[1].strip())
    except Exception as e:
        print(f"[WARNING] 璇诲彇.env鐗堟湰淇℃伅澶辫触: {e}")
    return version, build

APP_VERSION, APP_BUILD = _load_version_from_env()


_heygem_warmup_started = False


def _warmup_heygem():
    global _heygem_warmup_started
    if _heygem_warmup_started:
        return
    _heygem_warmup_started = True

    def _run():
        try:
            if not os.path.exists(HEYGEM_PYTHON):
                safe_print("[HEYGEM] python not found, skip warmup")
                return
            env = _build_heygem_env()
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            code = "import cy_app; cy_app.VideoProcessor(); print('HEYGEM_WARMUP_DONE', flush=True)"
            p = subprocess.Popen([HEYGEM_PYTHON, "-c", code], cwd=HEYGEM_DIR, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace",
                                 creationflags=flags)
            if p.stdout:
                for _ in range(200):
                    line = p.stdout.readline()
                    if not line:
                        if p.poll() is not None:
                            break
                        continue
                    line = line.strip()
                    if line:
                        safe_print("[HEYGEM-WARMUP] " + line)
            try:
                p.wait(timeout=60)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        except Exception as e:
            safe_print("[HEYGEM] warmup fail: " + str(e))

    threading.Thread(target=_run, daemon=True).start()


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  JS锛氭敞鍏ュ叏灞€閫昏緫锛堝湪 Gradio js= 鍙傛暟涓繍琛岋紝椤甸潰鍔犺浇鍚庣珛鍗虫墽琛岋級
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
# 浠庡閮ㄦ枃浠跺姞杞絁S锛屽苟娉ㄥ叆鐗堟湰鍙?
try:
    with open(os.path.join(BASE_DIR, "ui", "ui_init.js"), "r", encoding="utf-8") as f:
        INIT_JS = f.read()
        # 鏇挎崲鐗堟湰鍙峰崰浣嶇
        INIT_JS = INIT_JS.replace('{{APP_VERSION}}', APP_VERSION)
        INIT_JS = INIT_JS.replace('{{APP_BUILD}}', str(APP_BUILD))
except Exception as e:
    print(f"[WARNING] 鏃犳硶鍔犺浇 ui/ui_init.js: {e}")
    INIT_JS = "() => { console.log('[缁囨ⅵAI] JS鍔犺浇澶辫触'); }"

# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  CSS
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
# 浠庡閮ㄦ枃浠跺姞杞紺SS
try:
    with open(os.path.join(BASE_DIR, "ui", "ui_style.css"), "r", encoding="utf-8") as f:
        CUSTOM_CSS = f.read()
except Exception as e:
    print(f"[WARNING] 鏃犳硶鍔犺浇 ui/ui_style.css: {e}")
    CUSTOM_CSS = ""



# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
def auto_load_model():
    """鏍规嵁 TTS 妯″紡閫夋嫨鍐冲畾鏄惁鍔犺浇 IndexTTS2 妯″瀷"""
    global tts
    
    # 閲嶆柊鍔犺浇.env鏂囦欢锛岀‘淇濊幏鍙栨渶鏂扮殑TTS_MODE
    load_env_file()
    
    # 璇诲彇 TTS 妯″紡閫夋嫨锛坙ocal 鎴?online锛?
    tts_mode = os.getenv('TTS_MODE', 'local')
    safe_print(f"[MODEL] TTS 妯″紡: {tts_mode}")
    
    # 濡傛灉鏄湪绾跨増锛岃烦杩囨ā鍨嬪姞杞?
    if tts_mode == 'online':
        safe_print("[MODEL] 褰撳墠涓哄湪绾跨増锛岃烦杩?IndexTTS2 妯″瀷鍔犺浇")
        tts = None
        return
    
    # 鏈湴鐗堟墠鍔犺浇妯″瀷
    safe_print("[MODEL] 褰撳墠涓烘湰鍦扮増锛屽紑濮嬪姞杞?IndexTTS2 妯″瀷...")
    
    model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
    if not os.path.exists(model_dir):
        safe_print("[ERR] model dir not found"); return
    original_cwd = os.getcwd()
    os.chdir(INDEXTTS_DIR)
    try:
        safe_print("[MODEL] 姝ｅ湪鍔犺浇 IndexTTS2 澹板妯″瀷...")
        
        # 妫€鏌UDA鏄惁鍙敤
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        safe_print(f"[MODEL] PyTorch CUDA鍙敤: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            safe_print(f"[MODEL] GPU璁惧: {torch.cuda.get_device_name(0)}")
            safe_print(f"[MODEL] CUDA鐗堟湰: {torch.version.cuda}")
        else:
            safe_print("[MODEL] 璀﹀憡锛氭湭妫€娴嬪埌CUDA锛屽皢浣跨敤CPU锛堥€熷害浼氬緢鎱級")
        
        from indextts.infer_v2 import IndexTTS2
        tts = IndexTTS2(model_dir=model_dir,
                        cfg_path=os.path.join(model_dir, "config.yaml"), use_fp16=True)
        safe_print("[MODEL] 妯″瀷鍔犺浇瀹屾垚锛屾鍦ㄩ鐑紩鎿?..")
        # 棰勭儹锛氳Е鍙戜竴娆℃帹鐞嗗唴閮ㄥ垵濮嬪寲锛圕UDA鍥?JIT缂栬瘧绛夛級锛岄伩鍏嶉娆″悎鎴愬崱椤?
        try:
            import tempfile, numpy as np
            _dummy_wav = os.path.join(OUTPUT_DIR, "_warmup.wav")
            # 鎵句换鎰忎竴涓凡鏈夐煶鑹蹭綔涓?prompt 杩涜棰勭儹
            _voice_meta = os.path.join(BASE_DIR, "voices", "meta.json")
            _prompt = None
            if os.path.exists(_voice_meta):
                import json as _json
                _vm = _json.load(open(_voice_meta, encoding='utf-8'))
                if _vm and os.path.exists(_vm[0].get("path","")):
                    _prompt = _vm[0]["path"]
            if _prompt:
                tts.infer(spk_audio_prompt=_prompt, text="浣犲ソ銆?,
                          output_path=_dummy_wav,
                          do_sample=True, top_p=0.8, top_k=30,
                          temperature=0.8, length_penalty=0.0,
                          num_beams=1, repetition_penalty=10.0,
                          max_mel_tokens=200,
                          emo_audio_prompt=None, emo_alpha=0.5,
                          emo_vector=None, use_emo_text=False,
                          emo_text=None, use_random=False)
                try: os.remove(_dummy_wav)
                except Exception: pass
                safe_print("[MODEL] 寮曟搸棰勭儹瀹屾垚锛岄娆″悎鎴愬皢鐩存帴杈撳嚭")
        except Exception as _we:
            safe_print("[MODEL] 棰勭儹璺宠繃锛堟棤闊宠壊鏂囦欢鎴栭鐑け璐ワ級: " + str(_we))
        safe_print("[MODEL] OK")
    except Exception as e:
        safe_print("[MODEL] FAIL: " + str(e)); traceback.print_exc()
    finally:
        os.chdir(original_cwd)

# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  TTS GPU 鏄惧瓨绠＄悊锛堣棰戝悎鎴愬墠鍚庤嚜鍔ㄩ噴鏀?鎭㈠ GPU 鍗犵敤锛?
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
_tts_on_gpu = True  # 杩借釜 TTS 妯″瀷褰撳墠鏄惁鍦?GPU 涓?

def _release_tts_gpu():
    """瀹屽叏鍗歌浇 TTS 妯″瀷锛屽悓鏃堕噴鏀?GPU 鏄惧瓨鍜岀郴缁熷唴瀛?""
    global tts, _tts_on_gpu
    if tts is None:
        return
    try:
        import torch, gc
        del tts
        tts = None
        _tts_on_gpu = False
        gc.collect()
        torch.cuda.empty_cache()
        safe_print("[GPU] TTS 妯″瀷宸插畬鍏ㄥ嵏杞斤紙GPU + RAM 鍧囧凡閲婃斁锛?)
    except Exception as e:
        safe_print(f"[GPU] 閲婃斁 TTS 澶辫触: {e}")


def _restore_tts_gpu():
    """纭繚 TTS 妯″瀷宸插姞杞藉埌 GPU锛堝宸插嵏杞藉垯浠庣鐩橀噸鏂板姞杞斤級"""
    global tts, _tts_on_gpu
    
    # 濡傛灉鏄湪绾跨増锛屼笉闇€瑕佹仮澶峊TS妯″瀷
    tts_mode = os.getenv('TTS_MODE', 'local')
    if tts_mode == 'online':
        safe_print("[GPU] 鍦ㄧ嚎鐗堟ā寮忥紝璺宠繃 TTS 妯″瀷鎭㈠")
        return
    
    if tts is not None and _tts_on_gpu:
        return
    # tts 宸茶鍗歌浇锛岄渶瑕佷粠纾佺洏閲嶆柊鍔犺浇
    if tts is None:
        try:
            safe_print("[GPU] TTS 妯″瀷宸插嵏杞斤紝姝ｅ湪閲嶆柊鍔犺浇...")
            model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
            if not os.path.exists(model_dir):
                safe_print("[GPU] 妯″瀷鐩綍涓嶅瓨鍦紝鏃犳硶閲嶆柊鍔犺浇")
                return
            original_cwd = os.getcwd()
            os.chdir(INDEXTTS_DIR)
            try:
                from indextts.infer_v2 import IndexTTS2
                tts = IndexTTS2(model_dir=model_dir,
                                cfg_path=os.path.join(model_dir, "config.yaml"), use_fp16=True)
                _tts_on_gpu = True
                safe_print("[GPU] TTS 妯″瀷閲嶆柊鍔犺浇瀹屾垚")
            finally:
                os.chdir(original_cwd)
        except Exception as e:
            safe_print(f"[GPU] 閲嶆柊鍔犺浇 TTS 澶辫触: {e}")
        return
    # tts 鍦ㄥ唴瀛樹腑浣嗗湪 CPU 涓婏紙鍏煎鏃ч€昏緫锛?
    try:
        import torch
        device = tts.device
        if not device or device == "cpu":
            _tts_on_gpu = True
            return
        for name in ('gpt', 'semantic_model', 'semantic_codec', 's2mel',
                      'campplus_model', 'bigvgan'):
            model = getattr(tts, name, None)
            if model is not None and isinstance(model, torch.nn.Module):
                model.to(device)
        qwen = getattr(tts, 'qwen_emo', None)
        if qwen is not None:
            inner = getattr(qwen, 'model', None)
            if inner is not None and isinstance(inner, torch.nn.Module):
                inner.to(device)
        for name in ('semantic_mean', 'semantic_std'):
            t = getattr(tts, name, None)
            if t is not None and isinstance(t, torch.Tensor) and not t.is_cuda:
                setattr(tts, name, t.to(device))
        for name in ('emo_matrix', 'spk_matrix'):
            obj = getattr(tts, name, None)
            if obj is not None and isinstance(obj, (list, tuple)):
                setattr(tts, name, tuple(t.to(device) if isinstance(t, torch.Tensor) and not t.is_cuda else t for t in obj))
        _tts_on_gpu = True
        safe_print("[GPU] TTS 妯″瀷宸叉仮澶嶅埌 GPU")
    except Exception as e:
        safe_print(f"[GPU] 鎭㈠ TTS 鍒?GPU 澶辫触: {e}")


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  璇煶鍚堟垚锛堟敮鎸佹湰鍦扮増鍜屽湪绾跨増锛?
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
def download_voice_from_proxy(play_url: str, output_path: str, max_retries: int = 5, extra_headers=None) -> str:
    """閫氳繃浠ｇ悊URL涓嬭浇闊抽鏂囦欢鍒版寚瀹氳矾寰勶紙鑷姩閲嶈瘯 + 娴佸紡涓嬭浇锛?""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import time as _time
    import http.client as _http_client

    session = requests.Session()
    try:
        # urllib3 灞傝嚜鍔ㄩ噸璇曪紙浠呴拡瀵硅繛鎺ョ骇閿欒锛?
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=2,
                backoff_factor=1,
                status_forcelist=[502, 503, 504],
                allowed_methods=["GET"],
            )
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        headers = {
            "User-Agent": "ZhiMoAi-Client/1.0",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Accept-Encoding": "identity",
        }
        if extra_headers and isinstance(extra_headers, dict):
            headers.update({k: v for k, v in extra_headers.items() if v is not None})

        def _looks_like_audio(path: str, content_type: str) -> (bool, str):
            try:
                if not os.path.exists(path):
                    return False, "鏂囦欢涓嶅瓨鍦?
                size = os.path.getsize(path)
                if size < 2048:
                    return False, f"鏂囦欢杩囧皬({size}瀛楄妭)"

                ct = (content_type or "").lower()
                # 鍏佽鐨?content-type
                if ct and ("json" in ct or "text" in ct or "html" in ct):
                    return False, f"Content-Type 寮傚父: {content_type}"

                with open(path, 'rb') as f:
                    head = f.read(64)

                # WAV: RIFF....WAVE
                if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WAVE":
                    return True, "wav"
                # MP3: ID3 or frame sync
                if len(head) >= 3 and head[0:3] == b"ID3":
                    return True, "mp3"
                if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
                    return True, "mp3"
                # OGG: OggS
                if len(head) >= 4 and head[0:4] == b"OggS":
                    return True, "ogg"

                # 濡傛灉 content-type 鏄庣‘鏄煶棰戯紝涔熸斁琛岋紙鏌愪簺 wav 鍙兘鏃?RIFF 澶达紝鏋佸皯瑙侊級
                if ct.startswith("audio/"):
                    return True, f"audio/{ct}"
                return False, "鏂囦欢澶翠笉绗﹀悎甯歌闊抽鏍煎紡"
            except Exception as e:
                return False, f"鏍￠獙澶辫触: {e}"

        last_err = None
        for attempt in range(1, max_retries + 1):
            r = None
            try:
                print(f"[涓嬭浇] 绗?{attempt}/{max_retries} 娆″皾璇曚笅杞介煶棰?..")

                r = session.get(
                    play_url,
                    headers=headers,
                    timeout=(30, 600),
                    stream=True,
                )
                r.raise_for_status()

                expected = int(r.headers.get('Content-Length', 0) or 0)
                content_type = r.headers.get('Content-Type', '')

                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)

                file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                if file_size > 0 and (expected == 0 or file_size >= expected):
                    ok_audio, why = _looks_like_audio(output_path, content_type)
                    if ok_audio:
                        print(f"[涓嬭浇] 闊抽涓嬭浇鎴愬姛锛屽ぇ灏? {file_size} 瀛楄妭")
                        return output_path
                    # 棰勮涓€涓嬪搷搴斿唴瀹癸紝甯姪瀹氫綅鏈嶅姟绔繑鍥炵殑鏄粈涔?
                    try:
                        with open(output_path, 'rb') as _f:
                            preview = _f.read(256)
                        try:
                            preview_text = preview.decode('utf-8', errors='replace')
                        except Exception:
                            preview_text = str(preview)
                    except Exception:
                        preview_text = "(鏃犳硶璇诲彇棰勮)"
                    # 濡傛灉鏈嶅姟绔繑鍥炵殑鏄壌鏉?鍗″瘑鐩稿叧 JSON锛岀户缁噸璇曟病鏈夋剰涔?
                    if '"code":7' in preview_text and (
                        ("缂哄皯 Authorization" in preview_text) or ("鍗″瘑宸茶繃鏈? in preview_text)
                    ):
                        raise RuntimeError(f"[AUTH]{preview_text}")

                    raise IOError(
                        f"涓嬭浇鍐呭涓嶆槸鏈夋晥闊抽: {why}; Content-Type={content_type}; 棰勮={preview_text}"
                    )

                raise IOError(f"鏂囦欢涓嶅畬鏁? 宸蹭笅杞?{file_size} / 棰勬湡 {expected} 瀛楄妭")

            except (_http_client.IncompleteRead, requests.exceptions.ChunkedEncodingError) as e:
                last_err = e
                print(f"[涓嬭浇] 鏂祦/鍗婂寘(IncompleteRead)锛岀 {attempt} 娆″け璐? {e}")
            except RuntimeError as e:
                last_err = e
                # 閴存潈/鍗″瘑閿欒涓嶉噸璇?
                if str(e).startswith("[AUTH]"):
                    raise
                print(f"[涓嬭浇] 绗?{attempt} 娆′笅杞藉け璐? {e}")
            except Exception as e:
                last_err = e
                print(f"[涓嬭浇] 绗?{attempt} 娆′笅杞藉け璐? {e}")
            finally:
                if r is not None:
                    try:
                        r.close()
                    except Exception:
                        pass

            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass

            if attempt < max_retries:
                wait = min(attempt * 5, 30)
                print(f"[涓嬭浇] 绛夊緟 {wait} 绉掑悗閲嶈瘯...")
                _time.sleep(wait)
            else:
                raise last_err
    finally:
        try:
            session.close()
        except Exception:
            pass


def download_voice_from_lipvoice_direct(voice_url: str, output_path: str, sign: str, max_retries: int = 3) -> str:
    import requests
    import time as _time
    import http.client as _http_client

    headers = {
        "User-Agent": "ZhiMoAi-Client/1.0",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Accept-Encoding": "identity",
        "sign": sign,
    }

    last_err = None
    for attempt in range(1, max_retries + 1):
        r = None
        try:
            print(f"[鐩磋繛涓嬭浇] 绗?{attempt}/{max_retries} 娆″皾璇?..")
            r = requests.get(voice_url, headers=headers, timeout=(30, 600), stream=True)
            r.raise_for_status()
            content_type = r.headers.get('Content-Type', '')

            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

            ok_audio = os.path.exists(output_path) and os.path.getsize(output_path) >= 2048
            if not ok_audio:
                # 缁欏嚭棰勮
                preview_text = ""
                try:
                    with open(output_path, 'rb') as _f:
                        preview = _f.read(256)
                    preview_text = preview.decode('utf-8', errors='replace')
                except Exception:
                    preview_text = "(鏃犳硶璇诲彇棰勮)"
                raise IOError(f"鐩磋繛涓嬭浇鍐呭寮傚父: Content-Type={content_type}; 棰勮={preview_text}")

            return output_path

        except (_http_client.IncompleteRead, requests.exceptions.ChunkedEncodingError) as e:
            last_err = e
            print(f"[鐩磋繛涓嬭浇] 鏂祦/鍗婂寘锛岀 {attempt} 娆″け璐? {e}")
        except Exception as e:
            last_err = e
            print(f"[鐩磋繛涓嬭浇] 绗?{attempt} 娆″け璐? {e}")
        finally:
            if r is not None:
                try:
                    r.close()
                except Exception:
                    pass

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass

        if attempt < max_retries:
            _time.sleep(attempt * 2)

    raise last_err


def _pip_force_chinese_person(prompt: str) -> str:
    p = (prompt or "").strip()
    if not p:
        return p
    p_low = p.lower()
    if "涓浗" in p or "chinese" in p_low:
        return p
    human_keywords = [
        "浜?, "浜虹墿", "鐪熶汉", "妯＄壒", "鐢蜂汉", "濂充汉", "鐢峰", "濂冲", "灏戝勾", "灏戝コ", "澶у彅", "闃垮Ж",
        "person", "people", "man", "woman", "boy", "girl", "male", "female", "human",
    ]
    if any(k in p for k in human_keywords) or any(k in p_low for k in human_keywords):
        return p + "锛屼腑鍥戒汉"
    return p


def split_text_by_sentences(text, max_chars=100):
    """灏嗘枃鏈寜鍙ュ瓙鍒嗗壊锛屾瘡娈典笉瓒呰繃max_chars瀛楃

    Args:
        text: 瑕佸垎鍓茬殑鏂囨湰
        max_chars: 姣忔鏈€澶у瓧绗︽暟

    Returns:
        list: 鍒嗗壊鍚庣殑鏂囨湰娈靛垪琛?
    """
    import re

    # 鎸夊彞瀛愬垎鍓诧紙涓枃鍙ュ彿銆侀棶鍙枫€佹劅鍙瑰彿銆佽嫳鏂囧彞鍙风瓑锛?
    sentences = re.split(r'([銆傦紒锛??锛?])', text)

    # 閲嶆柊缁勫悎鍙ュ瓙鍜屾爣鐐?
    full_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            full_sentences.append(sentences[i] + sentences[i + 1])
        else:
            full_sentences.append(sentences[i])
    if len(sentences) % 2 == 1:
        full_sentences.append(sentences[-1])

    # 鍚堝苟鐭彞锛岀‘淇濇瘡娈典笉瓒呰繃max_chars
    chunks = []
    current_chunk = ""

    for sentence in full_sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # 濡傛灉褰撳墠鍙ュ瓙鏈韩灏辫秴杩噈ax_chars锛屽崟鐙綔涓轰竴娈?
        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            chunks.append(sentence)
        # 濡傛灉鍔犱笂褰撳墠鍙ュ瓙浼氳秴杩噈ax_chars锛屽厛淇濆瓨褰撳墠chunk
        elif len(current_chunk) + len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
        # 鍚﹀垯缁х画绱姞
        else:
            current_chunk += sentence

    # 娣诲姞鏈€鍚庝竴娈?
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def generate_speech_online_concurrent(text, voice_name, progress=gr.Progress()):
    """鍦ㄧ嚎鐗?TTS锛氬苟鍙戣皟鐢ㄤ簯绔?API 鍚堟垚璇煶锛堜紭鍖栫増锛?

    灏嗛暱鏂囨湰鍒嗗壊鎴愬涓?00瀛椾互鍐呯殑娈佃惤锛屽苟鍙戣姹傦紝鍏ㄩ儴瀹屾垚鍚庡悎鎴?
    """
    if not text.strip():
        raise gr.Error("璇疯緭鍏ヨ鍚堟垚鐨勬枃鏈唴瀹?)

    try:
        from voice_api import VoiceApiClient, API_BASE_URL, get_machine_code
        from lib_license import check_saved_license
        import lib_voice as _vc
        import time as _time
        import concurrent.futures
        from pydub import AudioSegment

        # 妫€鏌ュ崱瀵?
        status, info = check_saved_license()
        if status != "valid":
            raise gr.Error("璇峰厛鐧诲綍鍗″瘑鍚庡啀浣跨敤鍦ㄧ嚎鐗?TTS")

        if not isinstance(info, dict):
            raise gr.Error("鍗″瘑淇℃伅璇诲彇澶辫触锛岃閲嶆柊鐧诲綍")

        license_key = info.get("license_key", "")
        if not license_key:
            raise gr.Error("鍗″瘑鏃犳晥锛岃閲嶆柊鐧诲綍")

        # 鑾峰彇 model_id
        model_id = _vc.get_online_model_id(voice_name)
        if not model_id:
            raise gr.Error(f"鏈壘鍒板湪绾块煶鑹层€寋voice_name}銆嶇殑妯″瀷 ID")

        # 鍒嗗壊鏂囨湰
        text_chunks = split_text_by_sentences(text, max_chars=100)
        chunk_count = len(text_chunks)

        print(f"[TTS鍦ㄧ嚎鐗?骞跺彂] 鏂囨湰鎬婚暱搴? {len(text)}, 鍒嗗壊涓?{chunk_count} 娈?)
        for i, chunk in enumerate(text_chunks):
            print(f"[TTS鍦ㄧ嚎鐗?骞跺彂] 娈佃惤{i+1}: {len(chunk)}瀛?- {chunk[:30]}...")

        progress(0.05, desc=f"[鍦ㄧ嚎] 鍑嗗骞跺彂璇锋眰 {chunk_count} 涓换鍔?..")

        client = VoiceApiClient(API_BASE_URL, license_key)

        # 鎻愪氦鎵€鏈変换鍔?
        task_ids = []
        for i, chunk in enumerate(text_chunks):
            try:
                result = client.tts(model_id, chunk)
                if result.get("code") != 0:
                    raise gr.Error(f"娈佃惤{i+1}鎻愪氦澶辫触锛歿result.get('msg', '鏈煡閿欒')}")

                data = result.get("data", {})
                task_id = data.get("task_id") or data.get("taskId") or data.get("id")
                if not task_id:
                    raise gr.Error(f"娈佃惤{i+1}鏈繑鍥炰换鍔D")

                task_ids.append((i, task_id, chunk))
                print(f"[TTS鍦ㄧ嚎鐗?骞跺彂] 娈佃惤{i+1}宸叉彁浜わ紝浠诲姟ID: {task_id}")
            except Exception as e:
                raise gr.Error(f"娈佃惤{i+1}鎻愪氦澶辫触锛歿e}")

        progress(0.15, desc=f"[鍦ㄧ嚎] 宸叉彁浜?{chunk_count} 涓换鍔★紝绛夊緟澶勭悊...")

        # 骞跺彂杞鎵€鏈変换鍔?
        def poll_task(task_info):
            idx, task_id, chunk_text = task_info
            start_time = _time.time()

            while True:
                try:
                    result = client.tts_result(task_id)

                    if not isinstance(result, dict):
                        return (idx, None, f"杞缁撴灉寮傚父")

                    data = result.get("data", {})
                    task_status = data.get("status", "")

                    is_completed = (
                        task_status in ["completed", "success", "done"] or
                        task_status == 2 or
                        (isinstance(task_status, int) and task_status >= 2)
                    )

                    is_failed = (
                        task_status in ["failed", "error"] or
                        task_status == -1 or
                        (isinstance(task_status, int) and task_status < 0)
                    )

                    if result.get("code") == 0 and is_completed:
                        voice_url = (
                            data.get("audio_url") or
                            data.get("audioUrl") or
                            data.get("voiceUrl") or
                            data.get("voice_url") or
                            data.get("url")
                        )

                        if voice_url:
                            print(f"[TTS鍦ㄧ嚎鐗?骞跺彂] 娈佃惤{idx+1}宸插畬鎴? {voice_url}")
                            return (idx, voice_url, None)
                        else:
                            return (idx, None, "鏈繑鍥為煶棰慤RL")

                    elif is_failed:
                        error_msg = data.get("message") or data.get("msg") or data.get("error") or "鏈煡閿欒"
                        return (idx, None, error_msg)

                    # 瓒呮椂妫€鏌ワ紙姣忎釜浠诲姟鏈€澶氱瓑寰?鍒嗛挓锛?
                    if _time.time() - start_time > 300:
                        return (idx, None, "浠诲姟瓒呮椂")

                    _time.sleep(2)

                except Exception as e:
                    return (idx, None, str(e))

        # 浣跨敤绾跨▼姹犲苟鍙戣疆璇?
        audio_urls = [None] * chunk_count
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(chunk_count, 10)) as executor:
            futures = [executor.submit(poll_task, task_info) for task_info in task_ids]

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                idx, url, error = future.result()
                completed += 1

                if error:
                    raise gr.Error(f"娈佃惤{idx+1}澶勭悊澶辫触锛歿error}")

                audio_urls[idx] = url
                progress(0.15 + 0.6 * completed / chunk_count,
                        desc=f"[鍦ㄧ嚎] 宸插畬鎴?{completed}/{chunk_count} 涓换鍔?..")

        progress(0.75, desc="[鍦ㄧ嚎] 涓嬭浇闊抽鏂囦欢...")

        # 涓嬭浇鎵€鏈夐煶棰戞枃浠?
        audio_files = []
        sign = os.getenv("LIPVOICE_SIGN", "").strip()

        for i, voice_url in enumerate(audio_urls):
            try:
                ts = int(_time.time())
                local_file = os.path.join(OUTPUT_DIR, f"tts_online_chunk_{ts}_{i}.wav")

                if sign:
                    download_voice_from_lipvoice_direct(voice_url, local_file, sign)
                else:
                    from urllib.parse import quote
                    proxy_url = f"{API_BASE_URL}/api/dsp/voice/tts/download?voice_url={quote(voice_url)}"
                    download_voice_from_proxy(
                        proxy_url,
                        local_file,
                        extra_headers={
                            "Authorization": f"Bearer {license_key}",
                            "X-Machine-Code": get_machine_code(),
                        },
                    )

                audio_files.append(local_file)
                print(f"[TTS鍦ㄧ嚎鐗?骞跺彂] 娈佃惤{i+1}宸蹭笅杞? {local_file}")

            except Exception as e:
                raise gr.Error(f"娈佃惤{i+1}涓嬭浇澶辫触锛歿e}")

        progress(0.90, desc="[鍦ㄧ嚎] 鍚堟垚闊抽...")

        # 鍚堟垚鎵€鏈夐煶棰?
        if len(audio_files) == 1:
            final_file = audio_files[0]
        else:
            combined = AudioSegment.from_wav(audio_files[0])
            for audio_file in audio_files[1:]:
                segment = AudioSegment.from_wav(audio_file)
                combined += segment

            ts = int(_time.time())
            final_file = os.path.join(OUTPUT_DIR, f"tts_online_{ts}.wav")
            combined.export(final_file, format="wav")

            # 娓呯悊涓存椂鏂囦欢
            for audio_file in audio_files:
                try:
                    os.remove(audio_file)
                except Exception:
                    pass

        progress(1.0, desc="[OK] 鍚堟垚瀹屾垚")
        print(f"[TTS鍦ㄧ嚎鐗?骞跺彂] 鍚堟垚鎴愬姛: {final_file}")

        return final_file, "[OK] 鍦ㄧ嚎璇煶鍚堟垚瀹屾垚", final_file

    except gr.Error:
        raise
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"鍦ㄧ嚎 TTS 澶辫触锛歿e}")


def generate_speech_online(text, voice_name, progress=gr.Progress()):
    """鍦ㄧ嚎鐗?TTS锛氳皟鐢ㄤ簯绔?API 鍚堟垚璇煶"""
    if not text.strip():
        raise gr.Error("璇疯緭鍏ヨ鍚堟垚鐨勬枃鏈唴瀹?)
    
    try:
        from voice_api import VoiceApiClient
        from lib_license import check_saved_license
        import lib_voice as _vc
        
        # 妫€鏌ュ崱瀵?
        status, info = check_saved_license()
        if status != "valid":
            raise gr.Error("璇峰厛鐧诲綍鍗″瘑鍚庡啀浣跨敤鍦ㄧ嚎鐗?TTS")

        if not isinstance(info, dict):
            raise gr.Error("鍗″瘑淇℃伅璇诲彇澶辫触锛岃閲嶆柊鐧诲綍")

        license_key = info.get("license_key", "")
        if not license_key:
            raise gr.Error("鍗″瘑鏃犳晥锛岃閲嶆柊鐧诲綍")
        
        # 鑾峰彇 model_id
        model_id = _vc.get_online_model_id(voice_name)
        if not model_id:
            raise gr.Error(f"鏈壘鍒板湪绾块煶鑹层€寋voice_name}銆嶇殑妯″瀷 ID")
        
        progress(0.1, desc="[鍦ㄧ嚎] 姝ｅ湪璋冪敤浜戠 TTS 鏈嶅姟...")
        
        # 璋冪敤 API
        from voice_api import API_BASE_URL
        client = VoiceApiClient(API_BASE_URL, license_key)
        
        result = client.tts(model_id, text)
        print(f"[TTS鍦ㄧ嚎鐗圿 鏈嶅姟鍣ㄨ繑鍥? {result}")

        if not isinstance(result, dict):
            raise gr.Error(f"鍦ㄧ嚎 TTS 澶辫触锛氭湇鍔″櫒杩斿洖寮傚父锛堥潪JSON瀵硅薄锛夛細{result}")
        
        if result.get("code") != 0:
            raise gr.Error(f"鍚堟垚澶辫触锛歿result.get('msg', '鏈煡閿欒')}")
        
        data = result.get("data", {})
        if data is None:
            data = {}
        # 鍏煎涓嶅悓鐨勫瓧娈靛悕锛歵ask_id, taskId, id
        task_id = data.get("task_id") or data.get("taskId") or data.get("id")
        
        if not task_id:
            print(f"[TTS鍦ㄧ嚎鐗圿 閿欒锛氭湭鎵惧埌浠诲姟ID锛宒ata={data}")
            raise gr.Error(f"鏈嶅姟鍣ㄨ繑鍥炵殑浠诲姟 ID 鏃犳晥锛岃繑鍥炴暟鎹? {data}")
        
        progress(0.3, desc="[鍦ㄧ嚎] 浜戠姝ｅ湪澶勭悊涓?..")
        
        # 杞缁撴灉锛堜笉璁捐秴鏃讹紝鍥犱负闀挎枃妗堝悎鎴愬彲鑳介渶瑕佹暟鍒嗛挓锛?
        import time as _time
        start_time = _time.time()
        while True:
            result = client.tts_result(task_id)
            print(f"[TTS鍦ㄧ嚎鐗圿 杞缁撴灉: {result}")

            if not isinstance(result, dict):
                raise gr.Error(f"鍦ㄧ嚎 TTS 澶辫触锛氳疆璇㈢粨鏋滆繑鍥炲紓甯革紙闈濲SON瀵硅薄锛夛細{result}")
            
            status_code = result.get("code")
            data = result.get("data", {})
            if data is None:
                data = {}
            task_status = data.get("status", "")
            
            # 鍏煎涓嶅悓鐨勭姸鎬佽〃绀猴細
            # - 瀛楃涓? "completed", "success", "done"
            # - 鏁板瓧: 2 (瀹屾垚), 1 (澶勭悊涓?, 0 (绛夊緟), -1 (澶辫触)
            is_completed = (
                task_status in ["completed", "success", "done"] or
                task_status == 2 or
                (isinstance(task_status, int) and task_status >= 2)
            )
            
            is_failed = (
                task_status in ["failed", "error"] or
                task_status == -1 or
                (isinstance(task_status, int) and task_status < 0)
            )
            
            if status_code == 0 and is_completed:
                # 鍏煎澶氱闊抽URL瀛楁鍚?
                voice_url = (
                    data.get("audio_url") or 
                    data.get("audioUrl") or 
                    data.get("voiceUrl") or 
                    data.get("voice_url") or 
                    data.get("url")
                )
                
                if voice_url:
                    progress(0.9, desc="[鍦ㄧ嚎] 涓嬭浇闊抽鏂囦欢...")
                    from urllib.parse import quote
                    from voice_api import API_BASE_URL
                    from voice_api import get_machine_code
                    
                    try:
                        print(f"[TTS鍦ㄧ嚎鐗圿 涓嬭浇闊抽: {voice_url}")
                        
                        # 鐢熸垚鏈湴淇濆瓨璺緞锛堝拰鏈湴鐗堜竴鏍蜂繚瀛樺埌 unified_outputs锛?
                        ts = int(_time.time())
                        local_file = os.path.join(OUTPUT_DIR, f"tts_online_{ts}.wav")
                        
                        sign = os.getenv("LIPVOICE_SIGN", "").strip()
                        if sign:
                            print("[TTS鍦ㄧ嚎鐗圿 浣跨敤鐩磋繛涓嬭浇闊抽...")
                            download_voice_from_lipvoice_direct(voice_url, local_file, sign)
                        else:
                            # 鏈厤缃?LIPVOICE_SIGN 鏃跺洖閫€璧版湇鍔＄浠ｇ悊涓嬭浇
                            proxy_url = f"{API_BASE_URL}/api/dsp/voice/tts/download?voice_url={quote(voice_url)}"
                            download_voice_from_proxy(
                                proxy_url,
                                local_file,
                                extra_headers={
                                    "Authorization": f"Bearer {license_key}",
                                    "X-Machine-Code": get_machine_code(),
                                },
                            )
                        
                        progress(1.0, desc="[OK] 鍚堟垚瀹屾垚")
                        print(f"[TTS鍦ㄧ嚎鐗圿 鍚堟垚鎴愬姛: {local_file}")
                        
                        # 杩斿洖鏈湴鏂囦欢璺緞
                        return local_file, "[OK] 鍦ㄧ嚎璇煶鍚堟垚瀹屾垚", local_file
                    except Exception as e:
                        raise gr.Error(f"涓嬭浇闊抽澶辫触锛歿e}")
                else:
                    print(f"[TTS鍦ㄧ嚎鐗圿 閿欒锛氭湭鎵惧埌闊抽URL锛宒ata={data}")
                    raise gr.Error(f"鏈嶅姟鍣ㄨ繑鍥炵殑闊抽 URL 鏃犳晥锛岃繑鍥炴暟鎹? {data}")
            elif is_failed:
                error_msg = data.get("message") or data.get("msg") or data.get("error") or "鏈煡閿欒"
                raise gr.Error(f"鍚堟垚澶辫触锛歿error_msg}")
            
            # 鏇存柊杩涘害
            elapsed = int(_time.time() - start_time)
            progress(min(0.3 + elapsed / 600 * 0.5, 0.8), desc=f"[鍦ㄧ嚎] 浜戠澶勭悊涓?..宸茬瓑寰?{elapsed} 绉?)
            _time.sleep(2)
        
    except gr.Error:
        raise
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"鍦ㄧ嚎 TTS 澶辫触锛歿e}")


def generate_speech_local(text, prompt_audio, top_p, top_k, temperature, num_beams,
                          repetition_penalty, max_mel_tokens, emo_mode, emo_audio, emo_weight,
                          emo_text, vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                          progress=gr.Progress()):
    """鏈湴鐗?TTS锛氫娇鐢ㄦ湰鏈?GPU 鍚堟垚璇煶"""
    global tts
    if not text.strip():     raise gr.Error("璇疯緭鍏ヨ鍚堟垚鐨勬枃鏈唴瀹?)
    if prompt_audio is None: raise gr.Error("璇蜂笂浼犲弬鑰冮煶棰戞枃浠?)

    # 纭繚 TTS 妯″瀷宸插姞杞戒笖鍦?GPU 涓婏紙瑙嗛鍚堟垚鍚庢ā鍨嬪凡鍗歌浇锛岄渶閲嶆柊鍔犺浇锛?
    _restore_tts_gpu()
    if tts is None:          raise gr.Error("妯″瀷鏈姞杞斤紝璇风瓑寰呭垵濮嬪寲瀹屾垚")

    ts  = int(time.time())
    out = os.path.join(OUTPUT_DIR, f"tts_{ts}.wav")
    cwd = os.getcwd(); os.chdir(INDEXTTS_DIR)
    try:
        progress(0.25, desc="馃幆 閰嶇疆鐢熸垚鍙傛暟...")
        kw = dict(
            do_sample=True, top_p=float(top_p), top_k=int(top_k),
            temperature=float(temperature), length_penalty=0.0,
            num_beams=int(num_beams), repetition_penalty=float(repetition_penalty),
            max_mel_tokens=int(max_mel_tokens)
        )
        emo_ref_path, vec, use_emo_text = None, None, False
        if emo_mode == "浣跨敤鎯呮劅鍙傝€冮煶棰?:
            emo_ref_path = emo_audio
            progress(0.30, desc="馃幁 鍔犺浇鎯呮劅鍙傝€?..")
        elif emo_mode == "浣跨敤鎯呮劅鍚戦噺鎺у埗":
            vec = tts.normalize_emo_vec([vec1,vec2,vec3,vec4,vec5,vec6,vec7,vec8], apply_bias=True)
            progress(0.30, desc="馃幁 搴旂敤鎯呮劅鍚戦噺...")
        elif emo_mode == "浣跨敤鎯呮劅鎻忚堪鏂囨湰鎺у埗":
            use_emo_text = True
            progress(0.30, desc="馃幁 瑙ｆ瀽鎯呮劅鎻忚堪...")

        progress(0.35, desc="馃殌 寮€濮嬬敓鎴愰煶棰戯紙璇疯€愬績绛夊緟锛?..")
        final_emo_text = None
        if emo_text and isinstance(emo_text, str) and emo_text.strip():
            final_emo_text = emo_text.strip()

        tts.infer(
            spk_audio_prompt=prompt_audio, text=text, output_path=out,
            emo_audio_prompt=emo_ref_path, emo_alpha=float(emo_weight),
            emo_vector=vec, use_emo_text=use_emo_text, emo_text=final_emo_text,
            use_random=False, **kw
        )
        os.chdir(cwd)
        progress(0.90, desc="馃捑 淇濆瓨闊抽鏂囦欢...")
        progress(1.0, desc="鉁?鍚堟垚瀹屾垚")
        return out, "鉁?璇煶鍚堟垚瀹屾垚", out
    except Exception as e:
        os.chdir(cwd); traceback.print_exc()
        raise gr.Error("TTS 澶辫触: " + str(e))


def generate_speech(text, prompt_audio, voice_name, top_p, top_k, temperature, num_beams,
                    repetition_penalty, max_mel_tokens, emo_mode, emo_audio, emo_weight,
                    emo_text, vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                    progress=gr.Progress()):
    """璇煶鍚堟垚鍏ュ彛锛氫互褰撳墠 TTS_MODE 涓哄噯閫夋嫨鏈湴/鍦ㄧ嚎銆?

    璇存槑锛氫箣鍓嶄粎鏍规嵁 voice_name 鏄惁涓哄湪绾块煶鑹叉潵鍐冲畾璧板湪绾垮悎鎴愶紝
    浼氬鑷淬€岀櫥褰曟椂閫夊湪绾跨増 鈫?UI 鍒囧埌鏈湴鐗堛€嶅悗浠嶇劧璇蛋鍦ㄧ嚎鍚堟垚锛堣〃鐜颁负闈炲父鎱級銆?
    """
    tts_mode = os.getenv('TTS_MODE', 'local')
    if tts_mode == 'online':
        # 浣跨敤骞跺彂浼樺寲鐗堟湰
        return generate_speech_online_concurrent(text, voice_name, progress)
    return generate_speech_local(text, prompt_audio, top_p, top_k, temperature, num_beams,
                                 repetition_penalty, max_mel_tokens, emo_mode, emo_audio, emo_weight,
                                 emo_text, vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                                 progress)


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  瑙嗛鏍煎紡杞崲
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
def convert_video_for_browser(video_path, progress=gr.Progress()):
    if not video_path or not os.path.exists(video_path): return None
    ffmpeg = _resolve_ffmpeg_exe()
    if not ffmpeg: return video_path
    ts  = int(time.time())
    out = os.path.join(OUTPUT_DIR, f"converted_{ts}.mp4")
    progress(0.3, desc="杞崲瑙嗛鏍煎紡...")
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        p = subprocess.Popen(
            [ffmpeg, "-i", video_path, "-c:v", "libx264", "-preset", "ultrafast",
             "-crf", "23", "-c:a", "aac", "-b:a", "128k",
             "-movflags", "+faststart", "-pix_fmt", "yuv420p", "-y", out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        p.communicate(timeout=120)
        progress(1.0, desc="杞崲瀹屾垚")
        return out if p.returncode == 0 and os.path.exists(out) else video_path
    except Exception:
        return video_path


def _load_music_database():
    if not os.path.exists(MUSIC_DATABASE_FILE):
        return {}
    try:
        with open(MUSIC_DATABASE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _pick_random_bgm(selected_types):
    db = _load_music_database()
    if not selected_types:
        selected_types = list(db.keys())
    if not selected_types:
        raise gr.Error("鑳屾櫙闊充箰搴撲负绌?)
    pool = []
    for t in selected_types:
        items = db.get(t) or []
        if isinstance(items, list):
            pool.extend([it for it in items if isinstance(it, dict) and it.get("url") and it.get("filename")])
    if not pool:
        raise gr.Error("鎵€閫夌被鍨嬩笅娌℃湁鍙敤闊充箰")
    return random.choice(pool)


def _safe_bgm_cache_path(filename: str) -> str:
    name = (filename or "").strip()
    if not name:
        name = f"bgm_{int(time.time())}.mp3"
    name = os.path.basename(name)
    name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\-_. ()]", "_", name)
    return os.path.join(BGM_CACHE_DIR, name)


def download_bgm_if_needed(url: str, filename: str, progress=gr.Progress()):
    path = _safe_bgm_cache_path(filename)
    if os.path.exists(path) and os.path.getsize(path) > 1024:
        return path

    progress(0.1, desc="馃幍 AI姝ｅ湪鍖归厤鏈€浣抽煶涔?..")
    try:
        import requests  # type: ignore
    except ImportError:
        requests = None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }

    def _looks_like_html(file_path: str) -> bool:
        try:
            with open(file_path, "rb") as f:
                head = f.read(256).lstrip()
            if not head:
                return True
            low = head[:64].lower()
            return low.startswith(b"<!doctype") or low.startswith(b"<html") or low.startswith(b"<head")
        except Exception:
            return False

    def _download_via_requests():
        if requests is None:
            return False
        last_err = None
        for _attempt in range(3):
            try:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                with requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=(15, 60)) as r:
                    # 鏈変簺璧勬簮绔欎細杩斿洖闈炴爣鍑嗙姸鎬佺爜锛堝567锛夛紝娴忚鍣ㄤ粛鍙笅杞?
                    # 杩欓噷涓嶄娇鐢?raise_for_status锛岃€屾槸浠モ€滄渶缁堟枃浠舵槸鍚︽湁鏁堚€濅綔涓烘垚鍔熸爣鍑?
                    with open(path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                f.write(chunk)
                if os.path.exists(path) and os.path.getsize(path) > 1024 and (not _looks_like_html(path)):
                    return True
                last_err = Exception(f"http_status={getattr(r, 'status_code', 'unknown')}, invalid_file")
            except Exception as e:
                last_err = e
            time.sleep(0.6)
        if last_err:
            raise last_err
        return False

    def _download_via_urllib():
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(path, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        f.write(chunk)
            return os.path.exists(path) and os.path.getsize(path) > 1024 and (not _looks_like_html(path))
        except Exception:
            return False

    def _download_via_powershell():
        # Windows 鍏滃簳锛氳蛋绯荤粺缃戠粶鏍堬紝琛屼负鏇存帴杩戞祻瑙堝櫒
        try:
            if sys.platform != "win32":
                return False
            u = url.replace("'", "''")
            p = path.replace("'", "''")
            cmd = (
                "$ProgressPreference='SilentlyContinue';"
                "try { "
                f"Invoke-WebRequest -UseBasicParsing -Uri '{u}' -OutFile '{p}' -Headers @{{'User-Agent'='{headers['User-Agent']}'}}; "
                "exit 0 } catch { exit 1 }"
            )
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            r = subprocess.run([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd
            ], capture_output=True, text=True, creationflags=flags, timeout=120)
            if r.returncode != 0:
                return False
            return os.path.exists(path) and os.path.getsize(path) > 1024 and (not _looks_like_html(path))
        except Exception:
            return False

    if requests is not None:
        try:
            _download_via_requests()
        except Exception:
            # ignore, fallback below
            pass

    if os.path.exists(path) and os.path.getsize(path) > 1024 and (not _looks_like_html(path)):
        return path

    progress(0.2, desc="馃幍 AI鏅鸿兘闊充箰鍔犺浇涓?..")
    if _download_via_urllib():
        return path
    if _download_via_powershell():
        return path

    raise gr.Error(f"闊充箰璧勬簮鍔犺浇澶辫触: {url}")


def prepare_random_bgm_and_download(types_val, progress=gr.Progress(), max_tries=6):
    """浠庢墍閫夌被鍨嬩腑闅忔満鎸戦€夊彲鐢ㄩ煶涔愬苟涓嬭浇銆備笅杞藉け璐ヨ嚜鍔ㄦ崲鏇查噸璇曘€?""
    tried = set()
    last_err = None
    max_tries = int(max_tries or 6)
    for i in range(max_tries):
        item = _pick_random_bgm(types_val)
        url = item.get("url") or ""
        title = item.get("title") or ""
        filename = item.get("filename") or (title + ".mp3")

        key = url + "|" + filename
        if key in tried:
            continue
        tried.add(key)

        try:
            progress(0.05 + (i / max(1, max_tries)) * 0.25, desc=f"鍑嗗BGM锛歿title[:18]}...")
            local_path = download_bgm_if_needed(url, filename, progress=progress)
            shown = (title or os.path.basename(local_path)).strip()
            return item, local_path, shown
        except Exception as e:
            last_err = e
            continue

    raise gr.Error(f"鍑嗗鑳屾櫙闊充箰澶辫触锛堝凡灏濊瘯{len(tried)}棣栵級: {last_err}")


def mix_bgm_into_video(video_path: str, bgm_path: str, bgm_volume: float, progress=gr.Progress()):
    if not video_path or not os.path.exists(video_path):
        raise gr.Error("璇峰厛鐢熸垚瑙嗛锛堟楠?鎴栨楠?锛?)
    if not bgm_path or not os.path.exists(bgm_path):
        raise gr.Error("璇峰厛閫夋嫨鑳屾櫙闊充箰")

    ffmpeg_bin = _resolve_ffmpeg_exe()

    vol = float(bgm_volume or 1.0)
    vol = max(0.0, min(3.0, vol))

    ts = int(time.time())
    out = os.path.join(OUTPUT_DIR, f"video_bgm_{ts}.mp4")

    progress(0.2, desc="鍚堟垚鑳屾櫙闊充箰...")
    filter_complex = f"[1:a]volume={vol}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", video_path,
        "-stream_loop", "-1",
        "-i", bgm_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        out
    ]

    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=flags, timeout=600)
        if p.returncode != 0:
            err = (p.stderr or p.stdout or "").strip()
            raise gr.Error("鑳屾櫙闊充箰鍚堟垚澶辫触: " + (err[:400] if err else "ffmpeg error"))
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(f"鑳屾櫙闊充箰鍚堟垚澶辫触: {e}")

    if not os.path.exists(out) or os.path.getsize(out) < 1024:
        raise gr.Error("鑳屾櫙闊充箰鍚堟垚澶辫触锛氳緭鍑烘枃浠朵笉瀛樺湪")
    progress(1.0, desc="瀹屾垚")
    return out


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  杩涘害璇︽儏 HTML 鏋勫缓锛堢敤浜庢楠?/ 甯у弻琛屾樉绀猴級
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
def _make_detail_html(f_pct, f_cur, f_total, s_pct, s_cur, s_total, prog):
    bar_f = max(2, f_pct)
    bar_s = max(2, s_pct)
    return (
        f'''<div style="background:linear-gradient(135deg,#1e293b,#0f172a);
            border:1.5px solid #6366f1;border-radius:12px;
            padding:14px 16px 12px;margin:0 0 10px;
            font-family:Microsoft YaHei,system-ui,sans-serif;
            box-shadow:0 4px 16px rgba(99,102,241,.18);">
          <!-- 甯ц繘搴?-->
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:11px;color:#94a3b8;width:32px;flex-shrink:0;">甯?/span>
            <div style="flex:1;background:rgba(99,102,241,.15);border-radius:4px;height:7px;overflow:hidden;">
              <div style="height:100%;width:{bar_f}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);
                border-radius:4px;transition:width .35s;"></div>
            </div>
            <span style="font-size:12px;font-weight:700;color:#6366f1;width:48px;text-align:right;flex-shrink:0;">{f_pct}%</span>
            <span style="font-size:11px;color:#64748b;flex-shrink:0;">{f_cur}/{f_total}</span>
          </div>
          <!-- 姝ラ杩涘害 -->
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:11px;color:#94a3b8;width:32px;flex-shrink:0;">姝ラ</span>
            <div style="flex:1;background:rgba(139,92,246,.15);border-radius:4px;height:7px;overflow:hidden;">
              <div style="height:100%;width:{bar_s}%;background:linear-gradient(90deg,#8b5cf6,#a78bfa);
                border-radius:4px;transition:width .35s;"></div>
            </div>
            <span style="font-size:12px;font-weight:700;color:#8b5cf6;width:48px;text-align:right;flex-shrink:0;">{s_pct}%</span>
            <span style="font-size:11px;color:#64748b;flex-shrink:0;">{s_cur}/{s_total}</span>
          </div>
          <!-- 鎬昏繘搴?-->
          <div style="font-size:11px;color:#64748b;text-align:right;">鎬昏繘搴?{prog*100:.1f}%</div>
        </div>'''
    )

def _build_heygem_env():
    """鏋勫缓 HeyGem 瀛愯繘绋嬫墍闇€鐨勭幆澧冨彉閲忥紙鍙傝€?heygem-win-50/寮€濮?bat锛夈€?""
    env = os.environ.copy()
    py_path = os.path.join(HEYGEM_DIR, "py39")
    scripts_path = os.path.join(py_path, "Scripts")
    cu_path = os.path.join(py_path, "Lib", "site-packages", "torch", "lib")
    cuda_path = os.path.join(py_path, "Library", "bin")
    ffmpeg_path = HEYGEM_FFMPEG

    # 杩欎簺鍙橀噺鍦?bat 閲屼細娓呯┖锛岄伩鍏嶆薄鏌撶郴缁?Python
    env["PYTHONHOME"] = ""
    env["PYTHONPATH"] = ""

    # 鍏抽敭锛氳 heygem 鍐呯疆 ffmpeg 鍙敤
    env["PATH"] = ";".join([
        py_path,
        scripts_path,
        ffmpeg_path,
        cu_path,
        cuda_path,
        env.get("PATH", "")
    ])

    # gradio 涓存椂鐩綍
    env["GRADIO_TEMP_DIR"] = os.path.join(HEYGEM_DIR, "tmp")

    # huggingface 闀滃儚/缂撳瓨锛坆at 閲屾湁锛屼繚鐣欎竴鑷达級
    env.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    env.setdefault("HF_HOME", os.path.join(HEYGEM_DIR, "hf_download"))
    env.setdefault("TRANSFORMERS_CACHE", os.path.join(HEYGEM_DIR, "tf_download"))
    env.setdefault("XFORMERS_FORCE_DISABLE_TRITON", "1")
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:512")

    # 璁╁瓙杩涚▼/澶氳繘绋嬭兘 import 鍒扮紪璇戞ā鍧?
    env["PYTHONPATH"] = ";".join([
        HEYGEM_DIR,
        os.path.join(HEYGEM_DIR, "service"),
        env.get("PYTHONPATH", "")
    ])
    return env


def run_heygem(video_path, audio_path, progress=gr.Progress(), detail_cb=None,
               output_path_override=None, steps=12, if_gfpgan=False):
    """浣跨敤 heygem-win-50 鐢熸垚鍙ｅ瀷瑙嗛銆?

    閫氳繃 HeyGem 鍐呯疆 python 鍦ㄥ瓙杩涚▼涓皟鐢?cy_app.VideoProcessor.process_video锛岄伩鍏嶄緷璧栧綋鍓嶄富杩涚▼鐜銆?
    """
    if not video_path:
        raise gr.Error("璇蜂笂浼犱汉鐗╄棰?)
    if not audio_path:
        raise gr.Error("璇峰厛鍦ㄦ楠?鍑嗗闊抽锛堟枃瀛楄浆璇煶 鎴?鐩存帴涓婁紶闊抽鏂囦欢锛?)
    if not os.path.exists(str(video_path)):
        raise gr.Error("瑙嗛鏂囦欢涓嶅瓨鍦紝璇烽噸鏂颁笂浼?)
    if not os.path.exists(str(audio_path)):
        raise gr.Error("闊抽鏂囦欢涓嶅瓨鍦紝璇烽噸鏂伴€夋嫨")
    if not os.path.exists(HEYGEM_PYTHON):
        raise gr.Error("HeyGem 鐜鏈壘鍒帮細heygem-win-50/py39/python.exe")

    ts = int(time.time())
    sv = os.path.join(OUTPUT_DIR, f"in_v_{ts}{os.path.splitext(str(video_path))[1]}")
    sa = os.path.join(OUTPUT_DIR, f"in_a_{ts}{os.path.splitext(str(audio_path))[1]}")
    out = output_path_override if output_path_override else os.path.join(OUTPUT_DIR, f"lipsync_{ts}.mp4")
    try:
        shutil.copy2(str(video_path), sv)
        shutil.copy2(str(audio_path), sa)
    except Exception as e:
        raise gr.Error("澶嶅埗鏂囦欢澶辫触: " + str(e))

    progress(0.05, desc="鍒濆鍖栦腑...")
    _release_tts_gpu()

    env = _build_heygem_env()
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    # 瀛愯繘绋嬭剼鏈細璋冪敤 heygem 鐨?VideoProcessor锛屽苟鎶?yield 鐨勫唴瀹规墦鍗板嚭鏉ワ紙渚夸簬璋冭瘯/杩借釜锛?
    py_code = (
        "import os,sys\n"
        "os.chdir(r'''" + HEYGEM_DIR.replace("'", "''") + "''')\n"
        "import cy_app\n"
        "vp=cy_app.VideoProcessor()\n"
        "gen=vp.process_video(1, r'''" + sa.replace("'", "''") + "''', r'''" + sv.replace("'", "''") + "''', " + str(int(steps or 12)) + ", " + ("True" if if_gfpgan else "False") + ", output_filename=r'''" + out.replace("'", "''") + "''')\n"
        "last=None\n"
        "try:\n"
        "  for x in gen:\n"
        "    last=x\n"
        "    try: print(x, flush=True)\n"
        "    except Exception: pass\n"
        "except Exception as e:\n"
        "  print('HEYGEM_ERROR:'+repr(e), flush=True)\n"
        "  raise\n"
        "print('HEYGEM_DONE', last, flush=True)\n"
    )

    try:
        proc = subprocess.Popen(
            [HEYGEM_PYTHON, "-c", py_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=HEYGEM_DIR,
            env=env,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
            bufsize=1,
        )
    except Exception as e:
        _restore_tts_gpu()
        raise gr.Error("鍚姩 HeyGem 澶辫触: " + str(e))

    progress(0.08, desc="姝ｅ湪鐢熸垚瑙嗛...")
    last_line = ""
    prog = 0.08
    stage = "鍑嗗涓?
    stage_pct = 8
    t0 = time.time()
    # HeyGem 鍙岃繘搴﹁拷韪細鎬昏繘搴?+ 姝ラ杩涘害
    step_total = 0
    step_pct = 0       # 褰撳墠姝ラ鐧惧垎姣?0~100
    step_label = ""    # 褰撳墠姝ラ鎻忚堪

    if detail_cb:
        try:
            detail_cb(_dual_progress_html(stage, stage_pct, "", 0, 0))
        except Exception:
            pass
    while True:
        line = proc.stdout.readline() if proc.stdout else ""
        if not line and proc.poll() is not None:
            break
        if not line:
            continue
        line = line.strip()
        if not line:
            continue
        last_line = line
        safe_print("[HEYGEM] " + line)
        low = line.lower()

        # 鈹€鈹€ 瑙ｆ瀽 HeyGem 鍚勯樁娈碉紙鍙湪鍖归厤鏃舵洿鏂?stage锛岄伩鍏嶈烦鍔級鈹€鈹€

        # 1) 棰勫鐞?
        if "鏂囦欢涓嬭浇鑰楁椂" in line or ("涓嬭浇" in line and "鑰楁椂" in line):
            stage = "鍑嗗绱犳潗"
            stage_pct = max(stage_pct, 5)
            prog = max(prog, 0.05)
            step_label = "涓嬭浇鏂囦欢"
            step_pct = 100
        elif "format" in low and ("video" in low or "audio" in low or "甯х巼" in line or "fps" in low):
            stage = "鍒嗘瀽闊宠棰?
            stage_pct = max(stage_pct, 8)
            prog = max(prog, 0.08)
            step_label = "鏍煎紡杞崲"
            step_pct = 100
        elif "batch_size" in low or "batch size" in low:
            stage = "鍒濆鍖栨帹鐞?
            stage_pct = max(stage_pct, 10)
            prog = max(prog, 0.10)
            step_label = "鍔犺浇妯″瀷"
            step_pct = 0

        # 2) 鏁版嵁鍑嗗杩涘害锛歞rivered_video_pn >>> progress: 12/108
        elif "drivered_video_pn" in line:
            stage = "鍑嗗鏁版嵁"
            dp = re.search(r'progress:\s*(\d+)/(\d+)', line)
            if dp:
                cur, total = int(dp.group(1)), int(dp.group(2))
                step_total = max(step_total, total)
                if total > 0:
                    frac = cur / total
                    stage_pct = max(stage_pct, int(10 + frac * 20))
                    prog = max(prog, 0.10 + frac * 0.20)
                    step_label = f"甯ф暟鎹?{cur}/{total}"
                    step_pct = int(frac * 100)

        # 3) 鎺ㄧ悊杩涘害锛歛udio_transfer >>> frameId:24
        elif "audio_transfer" in line and "frameid" in low:
            stage = "鐢熸垚鍙ｅ瀷"
            ap = re.search(r'frameId[:\s]*(\d+)', line, re.IGNORECASE)
            if ap:
                step_cur = int(ap.group(1))
                if step_total > 0:
                    frac = min(1.0, step_cur / step_total)
                    stage_pct = max(stage_pct, int(30 + frac * 55))
                    prog = max(prog, 0.30 + frac * 0.55)
                    step_label = f"鎺ㄧ悊甯?{step_cur}/{step_total}"
                    step_pct = int(frac * 100)
                else:
                    stage_pct = max(stage_pct, min(80, stage_pct + 3))
                    prog = max(prog, min(0.80, prog + 0.03))
                    step_label = f"鎺ㄧ悊甯?{step_cur}"
                    step_pct = min(step_pct + 5, 95)

        # 4) 鍚堟垚杈撳嚭
        elif "executing ffmpeg command" in low or ("ffmpeg" in low and "command" in low):
            stage = "鍚堟垚杈撳嚭"
            stage_pct = max(stage_pct, 88)
            prog = max(prog, 0.88)
            step_label = "ffmpeg 鍚堝苟"
            step_pct = 50
        elif "video result saved" in low:
            stage = "瀹屾垚"
            stage_pct = max(stage_pct, 95)
            prog = max(prog, 0.95)
            step_label = "淇濆瓨鏂囦欢"
            step_pct = 100

        # 杈撳嚭鍙岃繘搴︽潯鍗＄墖
        if detail_cb:
            try:
                el = int(time.time() - t0)
                detail_cb(_dual_progress_html(stage, stage_pct, step_label, step_pct, el))
            except Exception:
                pass

        # 鎺ㄨ繘 Gradio progress bar
        try:
            prog = min(0.96, prog + 0.002)
            progress(prog, desc=f"{stage}... {int(stage_pct)}%")
        except Exception:
            pass

    rc = proc.wait()
    _restore_tts_gpu()

    if rc != 0:
        raise gr.Error("瑙嗛鍚堟垚澶辫触锛圚eyGem锛? " + (last_line or "unknown error"))
    if not os.path.exists(out):
        raise gr.Error("杈撳嚭瑙嗛鏂囦欢鏈壘鍒帮紝璇烽噸璇?)

    if detail_cb:
        try:
            el = int(time.time() - t0)
            detail_cb(_dual_progress_html("瀹屾垚", 100, "鍏ㄩ儴瀹屾垚", 100, el))
        except Exception:
            pass
    progress(1.0, desc="鉁?瀹屾垚")
    for f in (sv, sa):
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    return out, "鉁?瑙嗛鍚堟垚瀹屾垚"


def _md5_of_local_file(path):
    """璁＄畻鏈湴鏂囦欢鐨?MD5 hash"""
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_heygem_online(video_path, audio_path, progress=gr.Progress(), detail_cb=None,
                      output_path_override=None, **_kw):
    """浣跨敤 Linux HeyGem 鏈嶅姟鍣ㄥ湪绾垮悎鎴愬彛鍨嬭棰戙€?

    娴佺▼锛?
    1. 閫氳繃 WebSocket 鏌ヨ GPU 鐘舵€?
    2. 濡傛灉 GPU 绂荤嚎锛岄€氳繃 WebSocket 鎻愪氦浠诲姟锛堣Е鍙戝紑鏈猴級
    3. 绛夊緟 GPU 涓婄嚎閫氱煡
    4. GPU 涓婄嚎鍚庯紝鐩存帴 HTTP 涓婁紶鏂囦欢鍜屾彁浜や换鍔?
    """
    safe_print(f"[HEYGEM-ONLINE] 寮€濮嬪湪绾垮悎鎴愭祦绋?)

    import requests as _req

    server_url = os.getenv("HEYGEM_SERVER_URL", "").strip().rstrip("/")
    api_secret = os.getenv("HEYGEM_API_SECRET", "").strip()

    if not server_url:
        raise gr.Error("HEYGEM_SERVER_URL 鏈厤缃紝璇峰湪 .env 涓缃?Linux HeyGem 鏈嶅姟鍣ㄥ湴鍧€\n"
                       "鏍煎紡绀轰緥: http://192.168.1.100:8383")

    # 鑷姩琛ュ叏 http:// 鍓嶇紑
    if not server_url.startswith("http://") and not server_url.startswith("https://"):
        server_url = "http://" + server_url
    # 鑷姩琛ュ叏绔彛
    from urllib.parse import urlparse
    parsed = urlparse(server_url)
    if not parsed.port:
        server_url = server_url.rstrip("/") + ":8383"

    if not video_path or not os.path.exists(str(video_path)):
        raise gr.Error("瑙嗛鏂囦欢涓嶅瓨鍦紝璇烽噸鏂颁笂浼?)
    if not audio_path or not os.path.exists(str(audio_path)):
        raise gr.Error("闊抽鏂囦欢涓嶅瓨鍦紝璇烽噸鏂伴€夋嫨")

    headers = {}
    if api_secret:
        headers["Authorization"] = f"Bearer {api_secret}"

    ts = int(time.time())
    out = output_path_override or os.path.join(OUTPUT_DIR, f"lipsync_online_{ts}.mp4")
    t0 = time.time()

    video_path = str(video_path)
    audio_path = str(audio_path)
    video_ext = os.path.splitext(video_path)[1] or ".mp4"
    audio_ext = os.path.splitext(audio_path)[1] or ".wav"

    # 鈹€鈹€ 姝ラ 1: 閫氳繃 WebSocket 鎻愪氦浠诲姟骞剁瓑寰?GPU 涓婄嚎 鈹€鈹€
    safe_print(f"[HEYGEM-ONLINE] 姝ラ1: 閫氳繃 WebSocket 鎻愪氦浠诲姟")
    progress(0.01, desc="鎻愪氦浠诲姟锛屾鏌?GPU 鐘舵€?..")

    # 鑾峰彇鍏ㄥ眬 TextExtractor 瀹炰緥
    global _text_extractor
    if not _text_extractor:
        safe_print(f"[DEBUG] 鍒涘缓 TextExtractor 瀹炰緥")
        _text_extractor = TextExtractor()
        _text_extractor.start()
        # 绛夊緟杩炴帴鍜屾敞鍐屽畬鎴?
        import time as _wait_time
        for i in range(30):  # 鏈€澶氱瓑寰?15 绉?
            if _text_extractor._connected and _text_extractor._registered:
                safe_print(f"[DEBUG] WebSocket 宸茶繛鎺ュ苟娉ㄥ唽 (鑰楁椂 {i*0.5}s)")
                break
            _wait_time.sleep(0.5)
        else:
            safe_print(f"[DEBUG] WebSocket 杩炴帴鎴栨敞鍐岃秴鏃?)
    else:
        # 濡傛灉瀹炰緥宸插瓨鍦紝涔熻绛夊緟娉ㄥ唽瀹屾垚
        import time as _wait_time
        for i in range(30):
            if _text_extractor._connected and _text_extractor._registered:
                safe_print(f"[DEBUG] WebSocket 宸插氨缁?(鑰楁椂 {i*0.5}s)")
                break
            _wait_time.sleep(0.5)
        else:
            safe_print(f"[DEBUG] WebSocket 鏈氨缁?)

    safe_print(f"[DEBUG] TextExtractor 鐘舵€? connected={_text_extractor._connected}, registered={_text_extractor._registered}")

    if not _text_extractor or not _text_extractor._connected or not _text_extractor._registered:
        safe_print(f"[HEYGEM-ONLINE] WebSocket 鏈氨缁?(connected={_text_extractor._connected if _text_extractor else False}, registered={_text_extractor._registered if _text_extractor else False})")
        raise gr.Error("WebSocket 鏈氨缁紝鏃犳硶鎻愪氦浠诲姟銆傝妫€鏌ョ綉缁滆繛鎺ュ拰鍗″瘑閰嶇疆銆?)

    # 閫氳繃 WebSocket 鎻愪氦浠诲姟
    safe_print(f"[HEYGEM-ONLINE] 閫氳繃 WebSocket 鎻愪氦浠诲姟锛堣Е鍙?GPU 寮€鏈猴級")
    progress(0.01, desc="璁＄畻鏂囦欢鎸囩汗...")

    # 璁＄畻鏂囦欢 hash
    video_hash = _md5_of_local_file(video_path)
    audio_hash = _md5_of_local_file(audio_path)
    safe_print(f"[HEYGEM-ONLINE] video hash={video_hash}, audio hash={audio_hash}")

    # 鍙戦€佷换鍔℃彁浜ゆ秷鎭?
    submit_request = {
        "type": "gpu.job.submit",
        "task_type": "heygem_submit",
        "request_id": f"heygem_{ts}",
        "payload": {
            "video_hash": video_hash,
            "audio_hash": audio_hash,
            "video_ext": video_ext,
            "audio_ext": audio_ext,
        }
    }

    safe_print(f"[DEBUG] 鍑嗗鍙戦€佽姹? {submit_request}")

    try:
        # 浣跨敤 TextExtractor 鐨勬柟娉曞彂閫佽姹?
        safe_print(f"[DEBUG] 璋冪敤 _send_ws_request...")
        success, response = _text_extractor._send_ws_request(
            submit_request,
            timeout=1800,  # 30 鍒嗛挓瓒呮椂
            response_type=None  # 涓嶆寚瀹氱壒瀹氬搷搴旂被鍨嬶紝璁╁畠澶勭悊 gpu.power.offline/online
        )
        safe_print(f"[DEBUG] _send_ws_request 杩斿洖: success={success}, response={response}")

        if not success:
            # 鏀跺埌 gpu.power.offline锛岃鏄?GPU 绂荤嚎锛屼换鍔″凡鍏ラ槦
            safe_print(f"[HEYGEM-ONLINE] GPU 绂荤嚎锛屼换鍔″凡鍏ラ槦: {response}")
            progress(0.02, desc="GPU 绂荤嚎锛岀瓑寰呰嚜鍔ㄥ紑鏈?..")

            # 绛夊緟 GPU 涓婄嚎閫氱煡
            safe_print(f"[HEYGEM-ONLINE] 绛夊緟 GPU 涓婄嚎...")
            start_wait = time.time()
            max_wait = 1800  # 鏈€澶氱瓑寰?30 鍒嗛挓

            while time.time() - start_wait < max_wait:
                try:
                    # 浠庨槦鍒椾腑鑾峰彇娑堟伅
                    message = _text_extractor._response_queue.get(timeout=5)
                    data = json.loads(message)
                    msg_type = data.get("type", "")

                    if msg_type == "gpu.power.online":
                        safe_print(f"[HEYGEM-ONLINE] 鉁?GPU 宸蹭笂绾?)
                        break

                    # 鍏朵粬娑堟伅鏀惧洖闃熷垪
                    _text_extractor._response_queue.put(message)

                except _queue.Empty:
                    elapsed = int(time.time() - start_wait)
                    if elapsed % 10 == 0:
                        safe_print(f"[HEYGEM-ONLINE] 绛夊緟 GPU 涓婄嚎... ({elapsed}s)")
                        progress(0.02 + (elapsed / max_wait) * 0.08, desc=f"绛夊緟 GPU 涓婄嚎... ({elapsed}s)")
                    continue

            # 妫€鏌ユ槸鍚﹁秴鏃?
            if time.time() - start_wait >= max_wait:
                raise gr.Error(f"绛夊緟 GPU 涓婄嚎瓒呮椂锛?0鍒嗛挓锛夛紝璇锋鏌?GPU 鏈嶅姟鍣ㄧ姸鎬?)

        else:
            # GPU 鍦ㄧ嚎锛屼换鍔″凡鎻愪氦
            safe_print(f"[HEYGEM-ONLINE] GPU 鍦ㄧ嚎锛屼换鍔″凡鎻愪氦")

    except Exception as e:
        safe_print(f"[HEYGEM-ONLINE] WebSocket 閫氫俊澶辫触: {e}")
        import traceback
        traceback.print_exc()
        raise gr.Error(f"WebSocket 閫氫俊澶辫触: {e}")

    # 鈹€鈹€ 姝ラ 2: GPU 宸蹭笂绾匡紝寮€濮嬩笂浼犳枃浠跺拰鎻愪氦浠诲姟 鈹€鈹€
    safe_print(f"[HEYGEM-ONLINE] 姝ラ2: GPU 宸蹭笂绾匡紝寮€濮嬩笂浼犳枃浠?)
    progress(0.1, desc="GPU 宸蹭笂绾匡紝鍑嗗涓婁紶鏂囦欢...")

    # hash 宸插湪姝ラ1涓绠楋紝鐩存帴浣跨敤
    safe_print(f"[HEYGEM-ONLINE] video hash={video_hash}, audio hash={audio_hash}")

    # 鈹€鈹€ 2) 妫€鏌ユ湇鍔″櫒鏄惁宸叉湁杩欎簺鏂囦欢 鈹€鈹€
    progress(0.03, desc="妫€鏌ユ湇鍔″櫒鏂囦欢...")
    if detail_cb:
        try: detail_cb(_dual_progress_html("妫€鏌ユ枃浠?, 3, "姣斿鏈嶅姟鍣?, 0, 0))
        except Exception: pass

    try:
        resp = _req.post(
            f"{server_url}/api/heygem/check_files",
            json={"files": [
                {"hash": video_hash, "ext": video_ext},
                {"hash": audio_hash, "ext": audio_ext},
            ]},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        check_data = resp.json().get("data", {})
    except Exception as e:
        safe_print(f"[HEYGEM-ONLINE] check_files 澶辫触锛屽皢鍏ㄩ噺涓婁紶: {e}")
        check_data = {}

    video_exists = check_data.get(video_hash, False)
    audio_exists = check_data.get(audio_hash, False)

    # 鈹€鈹€ 3) 浠呬笂浼犵己澶辩殑鏂囦欢 鈹€鈹€
    upload_items = []
    if not video_exists:
        upload_items.append(("video", video_path, video_hash, video_ext))
    else:
        safe_print(f"[HEYGEM-ONLINE] 瑙嗛鏂囦欢宸插湪鏈嶅姟鍣紝璺宠繃涓婁紶")
    if not audio_exists:
        upload_items.append(("audio", audio_path, audio_hash, audio_ext))
    else:
        safe_print(f"[HEYGEM-ONLINE] 闊抽鏂囦欢宸插湪鏈嶅姟鍣紝璺宠繃涓婁紶")

    for i, (ftype, fpath, fhash, fext) in enumerate(upload_items):
        pct = 4 + i * 3
        progress(pct / 100, desc=f"涓婁紶{ftype}鍒版湇鍔″櫒...")
        if detail_cb:
            try:
                sz = os.path.getsize(fpath)
                detail_cb(_dual_progress_html("涓婁紶鏂囦欢", pct, f"{ftype} ({sz//1024}KB)", int(i / max(len(upload_items), 1) * 100), int(time.time() - t0)))
            except Exception: pass

        try:
            with open(fpath, "rb") as f:
                resp = _req.post(
                    f"{server_url}/api/heygem/upload_file",
                    files={"file": (os.path.basename(fpath), f)},
                    data={"hash": fhash, "ext": fext},
                    headers=headers,
                    timeout=(30, 600),
                )
            resp.raise_for_status()
            udata = resp.json()
            if udata.get("code") != 0:
                raise RuntimeError(udata.get("msg", "涓婁紶澶辫触"))
            safe_print(f"[HEYGEM-ONLINE] 涓婁紶瀹屾垚: {ftype} -> {udata.get('data', {}).get('hash')}")
        except _req.exceptions.RequestException as e:
            raise gr.Error(f"涓婁紶{ftype}鍒版湇鍔″櫒澶辫触: {e}")

    # 鈹€鈹€ 4) 閫氳繃 hash 鎻愪氦鍚堟垚浠诲姟 鈹€鈹€
    progress(0.10, desc="鎻愪氦鍚堟垚浠诲姟...")
    if detail_cb:
        try: detail_cb(_dual_progress_html("鎻愪氦浠诲姟", 10, "鍙戦€佽姹?, 0, int(time.time() - t0)))
        except Exception: pass

    try:
        resp = _req.post(
            f"{server_url}/api/heygem/submit",
            json={
                "audio_hash": audio_hash,
                "audio_ext": audio_ext,
                "video_hash": video_hash,
                "video_ext": video_ext,
            },
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("msg", "鎻愪氦澶辫触"))
        task_id = data["data"]["task_id"]
        queue_info = data["data"].get("queue", {})
        safe_print(f"[HEYGEM-ONLINE] 浠诲姟宸叉彁浜? {task_id}, 闃熷垪: {queue_info}")
    except _req.exceptions.RequestException as e:
        raise gr.Error(f"鎻愪氦鍚堟垚浠诲姟澶辫触: {e}")
    except Exception as e:
        raise gr.Error(f"鎻愪氦鍚堟垚浠诲姟澶辫触: {e}")

    # 鈹€鈹€ 5) 杞杩涘害 鈹€鈹€
    progress(0.12, desc="绛夊緟鏈嶅姟鍣ㄥ鐞?..")
    poll_interval = 2
    max_wait = 1800

    while True:
        elapsed = time.time() - t0
        if elapsed > max_wait:
            raise gr.Error(f"鍚堟垚瓒呮椂 ({int(elapsed)}s)锛岃妫€鏌ユ湇鍔″櫒鐘舵€?)

        try:
            resp = _req.get(
                f"{server_url}/api/heygem/progress",
                params={"task_id": task_id},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            pdata = resp.json().get("data", {})
        except Exception as e:
            safe_print(f"[HEYGEM-ONLINE] 杞寮傚父: {e}")
            time.sleep(poll_interval)
            continue

        status = pdata.get("status", "")
        pct = pdata.get("progress", 0)
        msg = pdata.get("message", "")
        queue_pos = pdata.get("queue_position", 0)
        el = int(elapsed)

        if status == "queued":
            desc = f"鎺掗槦涓?(绗瑊queue_pos}浣?..."
            progress(0.12, desc=desc)
            if detail_cb:
                try: detail_cb(_dual_progress_html("鎺掗槦绛夊緟", 12, f"闃熷垪浣嶇疆 {queue_pos}", 0, el))
                except Exception: pass

        elif status in ("processing", "synthesizing", "encoding"):
            safe_pct = max(12, min(95, pct))
            grad_pct = 0.12 + (safe_pct - 12) * 0.01
            progress(min(0.95, grad_pct), desc=f"{msg} ({safe_pct}%)")
            if detail_cb:
                try:
                    cur_frame = pdata.get("current_frame", 0)
                    total_frame = pdata.get("total_frames", 0)
                    step_label = f"{cur_frame}/{total_frame} 甯? if total_frame else msg
                    detail_cb(_dual_progress_html("鍦ㄧ嚎鍚堟垚", safe_pct, step_label, safe_pct, el))
                except Exception: pass

        elif status == "done":
            safe_print(f"[HEYGEM-ONLINE] 鍚堟垚瀹屾垚锛屽紑濮嬩笅杞界粨鏋?..")
            progress(0.95, desc="涓嬭浇鍚堟垚缁撴灉...")
            if detail_cb:
                try: detail_cb(_dual_progress_html("涓嬭浇缁撴灉", 95, "姝ｅ湪涓嬭浇", 50, el))
                except Exception: pass
            break

        elif status == "error":
            err = pdata.get("error", "鏈煡閿欒")
            raise gr.Error(f"鏈嶅姟鍣ㄥ悎鎴愬け璐? {err}")

        time.sleep(poll_interval)

    # 鈹€鈹€ 6) 涓嬭浇缁撴灉 鈹€鈹€
    try:
        resp = _req.get(
            f"{server_url}/api/heygem/download",
            params={"task_id": task_id},
            headers=headers,
            timeout=(15, 600),
            stream=True,
        )
        resp.raise_for_status()

        with open(out, "wb") as f:
            for chunk in resp.iter_content(chunk_size=256 * 1024):
                if chunk:
                    f.write(chunk)

        if not os.path.exists(out) or os.path.getsize(out) < 1024:
            raise RuntimeError("涓嬭浇鐨勭粨鏋滄枃浠跺紓甯?)

        safe_print(f"[HEYGEM-ONLINE] 涓嬭浇瀹屾垚: {out} ({os.path.getsize(out)} bytes)")
    except _req.exceptions.RequestException as e:
        raise gr.Error(f"涓嬭浇鍚堟垚缁撴灉澶辫触: {e}")

    el = int(time.time() - t0)
    if detail_cb:
        try: detail_cb(_dual_progress_html("瀹屾垚", 100, "鍏ㄩ儴瀹屾垚", 100, el))
        except Exception: pass
    progress(1.0, desc="鉁?瀹屾垚")
    return out, "鉁?鍦ㄧ嚎瑙嗛鍚堟垚瀹屾垚"


def run_heygem_auto(video_path, audio_path, progress=gr.Progress(), detail_cb=None,
                    output_path_override=None, steps=12, if_gfpgan=False,
                    heygem_mode=None):
    """鏍规嵁 heygem_mode 鍙傛暟鎴?HEYGEM_MODE 鐜鍙橀噺閫夋嫨鏈湴鎴栧湪绾垮悎鎴?""
    if heygem_mode is None:
        mode = os.getenv("HEYGEM_MODE", "local").strip().lower()
    else:
        mode = str(heygem_mode).strip().lower()
        # UI 浼犲叆鐨勫彲鑳芥槸涓枃
        if "鍦ㄧ嚎" in mode or "online" in mode:
            mode = "online"
        else:
            mode = "local"
    if mode == "online":
        return run_heygem_online(video_path, audio_path, progress, detail_cb,
                                output_path_override)
    return run_heygem(video_path, audio_path, progress, detail_cb,
                      output_path_override, steps, if_gfpgan)


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  鎵归噺浠诲姟杈呭姪鍑芥暟
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
def generate_speech_batch(text, prompt_audio, out_path,
                          top_p=0.8, top_k=30, temperature=0.8,
                          num_beams=3, repetition_penalty=10.0, max_mel_tokens=1500):
    global tts
    if not text.strip(): raise RuntimeError("鏂囨湰涓虹┖")
    if not prompt_audio: raise RuntimeError("缂哄皯鍙傝€冮煶棰?)
    # 纭繚 TTS 妯″瀷宸插姞杞戒笖鍦?GPU 涓婏紙瑙嗛鍚堟垚鍚庢ā鍨嬪凡鍗歌浇锛岄渶閲嶆柊鍔犺浇锛?
    _restore_tts_gpu()
    if tts is None: raise RuntimeError("妯″瀷鏈姞杞?)
    cwd = os.getcwd(); os.chdir(INDEXTTS_DIR)
    try:
        kw = dict(do_sample=True, top_p=float(top_p), top_k=int(top_k),
                  temperature=float(temperature), length_penalty=0.0,
                  num_beams=int(num_beams), repetition_penalty=float(repetition_penalty),
                  max_mel_tokens=int(max_mel_tokens))
        tts.infer(spk_audio_prompt=prompt_audio, text=text, output_path=out_path,
                  emo_audio_prompt=None, emo_alpha=0.5,
                  emo_vector=None, use_emo_text=False, emo_text=None, use_random=False, **kw)
        return out_path
    finally:
        os.chdir(cwd)


def _render_task_list(tasks):
    if not tasks:
        return ('<div style="text-align:center;padding:28px 16px;color:#94a3b8;'
                'font-family:Microsoft YaHei,sans-serif;background:#f8fafc;'
                'border-radius:10px;border:2px dashed #e2e8f0;">'
                '<div style="font-size:24px;margin-bottom:8px;">馃搵</div>'
                '<div style="font-size:13px;">鏆傛棤浠诲姟 鈥?鍦ㄥ乏渚у～鍐欎俊鎭悗鐐瑰嚮銆屽姞鍏ラ槦鍒椼€?/div></div>')
    status_cfg = {
        "绛夊緟涓?:  ("#f1f5f9","#64748b","鈴?),
        "杩涜涓?:  ("#ede9fe","#6d28d9","鈿欙笍"),
        "鉁?瀹屾垚": ("#f0fdf4","#15803d","鉁?),
        "鉂?澶辫触": ("#fff1f2","#be123c","鉂?),
    }
    rows = ""
    for i, t in enumerate(tasks):
        idx = i + 1
        status = t.get("status", "绛夊緟涓?)
        sbg, sc, si = status_cfg.get(status, ("#f1f5f9","#64748b","鈴?))
        ab = ('<span class="bt-badge bt-badge-tts">馃帣 鏂囧瓧鍚堟垚</span>'
              if t.get("audio_mode") == "tts" else
              '<span class="bt-badge bt-badge-audio">馃幍 涓婁紶闊抽</span>')
        vb = ('<span class="bt-badge bt-badge-shared">馃幀 鍏叡瑙嗛</span>'
              if t.get("video_mode") == "shared" else
              '<span class="bt-badge bt-badge-own">馃幀 涓撳睘瑙嗛</span>')
        chip = (f'<span style="background:{sbg};color:{sc};border-radius:20px;'
                f'padding:2px 9px;font-size:11px;font-weight:700;">{si} {status}</span>')
        if status not in ("杩涜涓?, "鉁?瀹屾垚"):
            js_code = ("var el=document.querySelector('#bt-del-trigger textarea');"
                       "if(el){el.value='" + str(idx) + "';"
                       "el.dispatchEvent(new Event('input',{bubbles:true}));}")
            del_btn = (
                '<button onclick="' + js_code + '" '
                'style="background:none;border:none;cursor:pointer;color:#cbd5e1;'
                'font-size:15px;padding:3px 6px;border-radius:6px;line-height:1;" '
                'onmouseover="this.style.background=\'#fee2e2\';this.style.color=\'#dc2626\'" '
                'onmouseout="this.style.background=\'none\';this.style.color=\'#cbd5e1\'"'
                '>鉁?/button>'
            )
        else:
            del_btn = ""
        row_bg = ("#f0fdf4" if "瀹屾垚" in status else
                  ("#fff1f2" if "澶辫触" in status else
                   ("#f5f3ff" if status == "杩涜涓? else "transparent")))
        rows += (
            f'<tr style="border-bottom:1px solid #f1f5f9;background:{row_bg};">'
            f'<td style="padding:10px 8px;font-weight:800;color:#6366f1;font-size:13px;text-align:center;width:40px;">#{idx}</td>'
            f'<td style="padding:10px 8px;font-size:13px;color:#0f172a;font-weight:600;">{t.get("name","浠诲姟"+str(idx))}</td>'
            f'<td style="padding:10px 8px;">{ab}</td>'
            f'<td style="padding:10px 8px;">{vb}</td>'
            f'<td style="padding:10px 8px;">{chip}</td>'
            f'<td style="padding:10px 6px;text-align:center;width:36px;">{del_btn}</td>'
            f'</tr>'
        )
    cnt = len(tasks)
    return (
        f'<div style="border-radius:10px;overflow:hidden;border:1px solid #e2e8f0;">'
        f'<div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:9px 14px;'
        f'display:flex;align-items:center;justify-content:space-between;">'
        f'<span style="font-size:12px;font-weight:700;color:#fff;">鍏?{cnt} 涓换鍔?/span>'
        f'<span style="font-size:11px;color:rgba(255,255,255,.75);">鐐瑰嚮琛屾湯 鉁?鍙垹闄?/span></div>'
        f'<table style="width:100%;border-collapse:collapse;font-family:Microsoft YaHei,sans-serif;">'
        f'<thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">'
        f'<th style="padding:8px;text-align:center;font-size:11px;color:#64748b;width:40px;">搴?/th>'
        f'<th style="padding:8px;text-align:left;font-size:11px;color:#64748b;">浠诲姟鍚嶇О</th>'
        f'<th style="padding:8px;text-align:left;font-size:11px;color:#64748b;">闊抽</th>'
        f'<th style="padding:8px;text-align:left;font-size:11px;color:#64748b;">瑙嗛</th>'
        f'<th style="padding:8px;text-align:left;font-size:11px;color:#64748b;">鐘舵€?/th>'
        f'<th style="padding:8px;width:36px;"></th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def _hint(kind, msg):
    """鐢熸垚鎻愮ず HTML 灏忔潯"""
    if kind == "ok":
        bg, ic, tc = "#f0fdf4", "鉁?, "#15803d"
    elif kind == "warning":
        bg, ic, tc = "#fff7ed", "鈿狅笍", "#92400e"
    else:
        bg, ic, tc = "#fff1f2", "鉂?, "#be123c"
    return (f'<div style="background:{bg};border-radius:8px;padding:8px 12px;'
            f'font-size:12px;color:{tc};font-weight:600;'
            f'font-family:Microsoft YaHei,sans-serif;margin-top:4px;">'
            f'{ic} {msg}</div>')


def _render_batch_prog(done, total, cur_name, status, msg, out_folder=""):
    pct = int(done / total * 100) if total else 0
    sc = {"杩愯涓?: "#6366f1", "宸插畬鎴?: "#16a34a", "澶辫触": "#dc2626"}.get(status, "#64748b")
    folder_hint = f'<div style="font-size:11px;color:#64748b;margin-top:8px;">' + '\U0001f4c1' + f' 杈撳嚭鐩綍锛歿out_folder}</div>' if out_folder else ""
    return f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1.5px solid #6366f1;border-radius:12px;padding:14px 16px;font-family:Microsoft YaHei,sans-serif;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;"><span style="width:10px;height:10px;border-radius:50%;background:{sc};flex-shrink:0;"></span><span style="font-size:13px;font-weight:700;color:#e2e8f0;">{status}</span><span style="margin-left:auto;font-size:13px;font-weight:800;color:#6366f1;">{done}/{total}</span></div><div style="background:rgba(99,102,241,.15);border-radius:6px;height:8px;overflow:hidden;margin-bottom:8px;"><div style="height:100%;width:{pct}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:6px;"></div></div><div style="font-size:12px;color:#94a3b8;">{msg}</div>{folder_hint}</div>'


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  WebSocket 鏂囨鎻愬彇鍣紙鍏ㄥ眬鍗曚緥锛屼繚鎸侀暱杩炴帴锛?
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
class TextExtractor:
    """WebSocket 鏂囨鎻愬彇鍣紝淇濇寔闀胯繛鎺?""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._ws = None
        self._connected = False
        self._registered = False
        self._loop = None
        self._thread = None
        self._response_queue = _queue.Queue()
        self._ws_url = "wss://api.zhimengai.xyz/dsp"
        
    def _get_license_key(self):
        """浠庢湰鍦拌幏鍙栧崱瀵?""
        license_file = os.path.join(BASE_DIR, ".license")
        if os.path.exists(license_file):
            try:
                with open(license_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("license_key", "")
            except Exception:
                pass
        return ""
    
    async def _connect_and_register(self):
        """杩炴帴WebSocket骞舵敞鍐?""
        if not _WS_OK:
            safe_print("[TextExtractor] websockets 妯″潡鏈畨瑁?)
            return False

        try:
            license_key = self._get_license_key()
            if not license_key:
                safe_print("[TextExtractor] 鏈壘鍒板崱瀵?)
                return False

            safe_print(f"[DEBUG] 寮€濮嬭繛鎺?WebSocket...")
            safe_print(f"[DEBUG] License key: {license_key[:20]}...{license_key[-10:] if len(license_key) > 30 else ''}")
            self._ws = await websockets.connect(
                self._ws_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            self._connected = True
            safe_print("[TextExtractor] WebSocket 杩炴帴鎴愬姛")

            # 鍙戦€佹敞鍐屾秷鎭?
            register_msg = json.dumps({"type": "register", "key": license_key})
            await self._ws.send(register_msg)
            safe_print(f"[DEBUG] 宸插彂閫佹敞鍐屾秷鎭? {register_msg[:100]}...")

            # 绛夊緟娉ㄥ唽鍝嶅簲
            try:
                response = await asyncio.wait_for(self._ws.recv(), timeout=10)
                safe_print(f"[DEBUG] 鏀跺埌娉ㄥ唽鍝嶅簲: {response}")
                # 灏嗘敞鍐屽搷搴斾篃鏀惧叆闃熷垪锛屼緵鍏朵粬浠ｇ爜浣跨敤
                self._response_queue.put(response)
                self._registered = True
                safe_print(f"[DEBUG] 娉ㄥ唽鎴愬姛锛宺egistered={self._registered}")
            except asyncio.TimeoutError:
                safe_print("[TextExtractor] 娉ㄥ唽鍝嶅簲瓒呮椂锛岀户缁繍琛?)
                self._registered = True  # 鍗充娇瓒呮椂涔熺户缁?
                safe_print(f"[DEBUG] 瓒呮椂鍚庤缃?registered={self._registered}")

            return True
        except Exception as e:
            safe_print(f"[TextExtractor] 杩炴帴澶辫触: {e}")
            import traceback
            traceback.print_exc()
            self._connected = False
            self._registered = False
            return False
    
    async def _listen_loop(self):
        """鐩戝惉WebSocket娑堟伅"""
        while self._connected and self._ws:
            try:
                message = await self._ws.recv()
                # safe_print(f"[TextExtractor] 鏀跺埌娑堟伅: {message[:200]}..." if len(message) > 200 else f"[TextExtractor] 鏀跺埌娑堟伅: {message}")  # 绉婚櫎鏃ュ織
                self._response_queue.put(message)
            except websockets.exceptions.ConnectionClosed:
                safe_print("[TextExtractor] 杩炴帴宸插叧闂紝灏濊瘯閲嶈繛...")
                self._connected = False
                # 灏濊瘯閲嶈繛
                await asyncio.sleep(2)
                await self._connect_and_register()
            except Exception as e:
                safe_print(f"[TextExtractor] 鐩戝惉閿欒: {e}")
                break
    
    def _run_event_loop(self):
        """鍦ㄥ悗鍙扮嚎绋嬭繍琛屼簨浠跺惊鐜?""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # 杩炴帴骞舵敞鍐?
        self._loop.run_until_complete(self._connect_and_register())
        
        # 寮€濮嬬洃鍚?
        if self._connected:
            try:
                self._loop.run_until_complete(self._listen_loop())
            except Exception as e:
                safe_print(f"[TextExtractor] 浜嬩欢寰幆閿欒: {e}")
    
    def start(self):
        """鍚姩WebSocket杩炴帴锛堝悗鍙扮嚎绋嬶級"""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._thread.start()
            safe_print("[TextExtractor] 鍚庡彴绾跨▼宸插惎鍔?)
    
    def send_request(self, request_data: dict, timeout: float = 30.0,
                    response_type: str = None, request_id: str = None) -> tuple:
        """
        鍙戦€侀€氱敤WebSocket璇锋眰
        :param request_data: 璇锋眰鏁版嵁瀛楀吀
        :param timeout: 瓒呮椂鏃堕棿锛堢锛?
        :param response_type: 鏈熸湜鐨勫搷搴旂被鍨嬶紙濡?"chatglm_video_result"锛?
        :param request_id: 璇锋眰ID锛岀敤浜庡尮閰嶅搷搴?
        :return: (success, data_or_error)
        """
        if not _WS_OK:
            return False, "websockets 妯″潡鏈畨瑁?

        if not self._connected or not self._ws:
            self.start()
            time.sleep(2)

        if not self._connected:
            return False, "WebSocket 鏈繛鎺?

        try:
            # 鍦ㄤ簨浠跺惊鐜腑鍙戦€佹秷鎭?
            async def send_msg():
                await self._ws.send(json.dumps(request_data))

            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(send_msg(), self._loop)
                future.result(timeout=5)
            else:
                return False, "浜嬩欢寰幆鏈繍琛?

            # 绛夊緟鍝嶅簲
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = self._response_queue.get(timeout=1)
                    data = json.loads(response)

                    # 濡傛灉鎸囧畾浜?request_id锛屾鏌ユ槸鍚﹀尮閰?
                    if request_id and data.get("request_id") != request_id:
                        # 涓嶅尮閰嶏紝鏀惧洖闃熷垪
                        self._response_queue.put(response)
                        continue

                    # 濡傛灉鎸囧畾浜?response_type锛屾鏌ョ被鍨?
                    if response_type and data.get("type") == response_type:
                        return True, data

                    # 澶勭悊閫氱敤鍝嶅簲绫诲瀷
                    msg_type = data.get("type", "")
                    if msg_type == "ack":
                        continue  # 璺宠繃 ack锛岀户缁瓑寰呮渶缁堢粨鏋?
                    elif msg_type == "gpu_offline" or msg_type == "gpu.power.offline":
                        return False, data.get("msg", "GPU鏈嶅姟鍣ㄦ湭涓婄嚎锛屼换鍔″凡鎺掗槦锛屾湇鍔″櫒鍚姩鍚庤嚜鍔ㄦ墽琛岋紙绾?鍒嗛挓锛?)
                    elif msg_type == "gpu.power.online":
                        # 寮€鏈哄湪绾垮箍鎾紝涓嶆槸鏈姹傛渶缁堢粨鏋滐紝缁х画绛夊緟涓氬姟缁撴灉
                        continue
                    elif msg_type == "error":
                        return False, data.get("message", "璇锋眰澶辫触")
                    elif msg_type == "kicked":
                        return False, "杩炴帴琚湇鍔″櫒韪㈠嚭"
                    elif not response_type:
                        # 濡傛灉娌℃湁鎸囧畾鍝嶅簲绫诲瀷锛岃繑鍥炰换浣曢潪 ack 鐨勫搷搴?
                        return True, data

                except _queue.Empty:
                    continue
                except json.JSONDecodeError:
                    continue

            return False, "璇锋眰瓒呮椂"

        except Exception as e:
            return False, f"鍙戦€佽姹傚け璐? {e}"

    def _send_ws_request(self, request_data: dict, timeout: float = 30.0,
                        response_type: str = None) -> tuple:
        """
        Send a WebSocket request for GPU power/task coordination.
        Returns (False, data) for offline/error and (True, data) for accepted/expected response.
        """
        safe_print(f"[DEBUG] _send_ws_request start: request_type={request_data.get('type')}")

        if not _WS_OK:
            safe_print("[DEBUG] websockets not installed")
            return False, "websockets not installed"

        if not self._connected or not self._ws:
            safe_print("[DEBUG] WebSocket not connected, trying to start...")
            self.start()
            time.sleep(2)

        if not self._connected:
            safe_print("[DEBUG] WebSocket connect failed")
            return False, "WebSocket not connected"

        deferred_messages = []
        request_id = str(request_data.get("request_id") or "")

        try:
            async def send_msg():
                msg_str = json.dumps(request_data)
                safe_print(f"[DEBUG] send ws: {msg_str[:200]}...")
                await self._ws.send(msg_str)

            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(send_msg(), self._loop)
                future.result(timeout=5)
            else:
                return False, "event loop not running"

            start_time = time.time()
            response_count = 0
            while time.time() - start_time < timeout:
                try:
                    response = self._response_queue.get(timeout=1)
                    response_count += 1
                    safe_print(f"[DEBUG] recv #{response_count}: {response[:200]}...")

                    data = json.loads(response)
                    msg_type = str(data.get("type") or "")
                    msg_request_id = str(data.get("request_id") or "")

                    if msg_type in ["registered", "connected", "pong"]:
                        continue

                    # keep non-current responses for later consumers
                    if request_id and msg_request_id and msg_request_id != request_id:
                        deferred_messages.append(response)
                        continue

                    if response_type and msg_type == response_type:
                        return True, data

                    if msg_type in ["gpu_offline", "gpu.power.offline"]:
                        return False, data
                    if msg_type == "ack":
                        return True, data
                    if msg_type == "error":
                        return False, data

                    # unrelated/broadcast messages are kept and restored
                    deferred_messages.append(response)

                except _queue.Empty:
                    continue
                except json.JSONDecodeError:
                    continue

            return False, "request timeout"

        except Exception as e:
            safe_print(f"[DEBUG] ws request exception: {e}")
            import traceback
            traceback.print_exc()
            return False, f"send request failed: {e}"
        finally:
            for msg in deferred_messages:
                try:
                    self._response_queue.put_nowait(msg)
                except Exception:
                    try:
                        self._response_queue.put(msg)
                    except Exception:
                        pass

    def extract_text(self, url_or_content: str, timeout: float = 30.0) -> tuple:
        """
        鎻愬彇鏂囨
        :param url_or_content: URL鎴栧唴瀹?
        :param timeout: 瓒呮椂鏃堕棿锛堢锛?
        :return: (success, content_or_error)
        """
        if not _WS_OK:
            return False, "websockets 妯″潡鏈畨瑁咃紝璇疯繍琛? pip install websockets"

        if not self._connected or not self._ws:
            # 灏濊瘯鍚姩杩炴帴
            self.start()
            time.sleep(2)  # 绛夊緟杩炴帴寤虹珛

        if not self._connected:
            return False, "WebSocket 鏈繛鎺ワ紝璇锋鏌ョ綉缁?

        # 娓呯┖闃熷垪涓殑鏃ф秷鎭?
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except _queue.Empty:
                break

        # 鍙戦€佹彁鍙栬姹?
        try:
            extract_msg = json.dumps({"type": "url", "url": url_or_content})

            # 鍦ㄤ簨浠跺惊鐜腑鍙戦€佹秷鎭?
            async def send_msg():
                await self._ws.send(extract_msg)

            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(send_msg(), self._loop)
                future.result(timeout=5)
            else:
                return False, "浜嬩欢寰幆鏈繍琛?

            safe_print(f"[TextExtractor] 宸插彂閫佹彁鍙栬姹? {url_or_content[:50]}...")

            # 绛夊緟鍝嶅簲
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = self._response_queue.get(timeout=1)
                    data = json.loads(response)

                    if data.get("type") == "result":
                        content = data.get("content", "")
                        is_error = data.get("error", False)

                        if is_error:
                            # 閿欒鎯呭喌锛氳繑鍥炲け璐ュ拰閿欒淇℃伅
                            return False, content
                        elif content:
                            # 鎴愬姛鎯呭喌锛氳繑鍥炴垚鍔熷拰鍐呭
                            return True, content
                        else:
                            return False, "杩斿洖鍐呭涓虹┖"
                    elif data.get("type") == "error":
                        return False, data.get("message", "鎻愬彇澶辫触")
                except _queue.Empty:
                    continue
                except json.JSONDecodeError:
                    continue

            return False, "璇锋眰瓒呮椂锛岃閲嶈瘯"

        except Exception as e:
            return False, f"鍙戦€佽姹傚け璐? {e}"


# 鍏ㄥ眬鏂囨鎻愬彇鍣ㄥ疄渚?
_text_extractor = None

def get_text_extractor():
    """鑾峰彇鍏ㄥ眬鏂囨鎻愬彇鍣ㄥ疄渚?""
    global _text_extractor
    if _text_extractor is None:
        _text_extractor = TextExtractor()
    return _text_extractor

# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  鏋勫缓 UI
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
def build_ui():

    with gr.Blocks(
        title=APP_NAME,
        css=CUSTOM_CSS,
        js=INIT_JS,
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.indigo,
            secondary_hue=gr.themes.colors.purple,
            font=[gr.themes.GoogleFont("Noto Sans SC"), "Microsoft YaHei", "system-ui"],
        ),
    ) as app:

        # 鈹€鈹€ 杩涘害鎻愮ず妯箙锛堣棰戝悎鎴愭椂鏄剧ず锛夆攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
        progress_banner = gr.HTML(
            value='',
            elem_id="zdai-progress-banner",
            visible=False,
        )

        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲 椤跺眰 Tabs 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
        with gr.Tabs():

            # 鈹€鈹€ Tab 1锛氬伐浣滃彴 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
            with gr.Tab("馃幀  宸ヤ綔鍙?):
                # 鈺愨晲 椤堕儴宸ヤ綔鍙拌褰曠鐞嗗尯 鈺愨晲
                with gr.Group(elem_classes="panel", elem_id="workspace-record-panel"):
                    gr.HTML('<div style="font-size:14px;font-weight:700;color:#334155;margin-bottom:12px;">馃捑 宸ヤ綔鍙拌褰?/div>')
                    
                    with gr.Row():
                        # 宸︿晶锛氫笅鎷夋
                        workspace_record_dropdown = gr.Dropdown(
                            label="閫夋嫨璁板綍",
                            choices=[],
                            value=None,
                            interactive=True,
                            scale=2,
                            elem_id="workspace-record-dropdown"
                        )
                        
                        # 鍙充晶锛?涓寜閽紝涓ゆ帓涓ゅ垪
                        with gr.Column(scale=1, elem_id="workspace-record-buttons"):
                            with gr.Row():
                                workspace_restore_btn = gr.Button("馃攧 鎭㈠", variant="primary", scale=1, size="sm")
                                workspace_delete_btn = gr.Button("馃棏 鍒犻櫎", variant="secondary", scale=1, size="sm", elem_classes="danger-btn")
                            with gr.Row():
                                workspace_refresh_btn = gr.Button("馃攧 鍒锋柊鍒楄〃", variant="secondary", scale=1, size="sm")
                                workspace_clear_btn = gr.Button("馃棏 娓呯┖鎵€鏈夎褰?, variant="secondary", scale=1, size="sm", elem_classes="danger-btn")
                    
                    workspace_record_hint = gr.HTML(value="")
                
                with gr.Row(elem_classes="workspace"):

                    # 鈺愨晲鈺?姝ラ 1锛氭枃妗堟彁鍙?+ 姝ラ 2锛氶煶棰戝悎鎴?鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
                    with gr.Column(scale=1):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">1</div>'
                            '<span class="step-title">鏂囨鎻愬彇</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            # 鈹€鈹€ 鏂囨鎻愬彇鍔熻兘鍖?鈹€鈹€
                            with gr.Group(elem_classes="extract-panel"):
                                gr.HTML(
                                    '<div class="extract-header">'
                                    '<span class="extract-icon">馃敆</span>'
                                    '<span class="extract-title">鏅鸿兘鏂囨鎻愬彇</span>'
                                    '<span class="extract-badge">AI</span>'
                                    '</div>'
                                )
                                extract_input = gr.Textbox(
                                    label="",
                                    placeholder="绮樿创鎶栭煶/灏忕孩涔?鍏紬鍙风瓑閾炬帴锛屾垨鐩存帴杈撳叆鍐呭...",
                                    lines=2,
                                    elem_classes="extract-input"
                                )
                                gr.HTML(
                                    '<div class="extract-tip">'
                                    '鏀寔涓绘祦骞冲彴閾炬帴锛屼竴閿彁鍙栨枃妗堝唴瀹?
                                    '</div>'
                                )
                                extract_btn = gr.Button(
                                    "鉁?鎻愬彇鏂囨",
                                    variant="primary",
                                    size="sm",
                                    elem_classes="extract-btn"
                                )
                                extract_hint = gr.HTML(value="", elem_classes="extract-hint")
                                
                                # 鈹€鈹€ AI鏀瑰啓鍔熻兘锛堟斁鍦ㄦ彁鍙栨鍐咃級 鈹€鈹€
                                gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:4px 8px;margin-top:12px;margin-bottom:8px;">AI鏅鸿兘鏀瑰啓鏂囨锛屽悓鏃剁敓鎴愭爣棰樺拰璇濋鏍囩</div>')
                                rewrite_btn = gr.Button("鉁?AI鏀瑰啓 + 鏍囬鏍囩", variant="secondary", size="sm")
                            
                            input_text = gr.TextArea(
                                label="鏂囨鍐呭",
                                placeholder="鍦ㄦ杈撳叆鎴栫矘璐存枃妗堝唴瀹癸紝鎴栦娇鐢ㄤ笂鏂规彁鍙栧姛鑳?..",
                                lines=6)

                        # 鈺愨晲鈺?姝ラ 2锛氶煶棰戝悎鎴?鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">2</div>'
                            '<span class="step-title">闊抽鍚堟垚</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            audio_mode = gr.Radio(
                                label="閫夋嫨闊抽鏉ユ簮",
                                choices=["鏂囧瓧杞闊?, "鐩存帴涓婁紶闊抽"],
                                value="鏂囧瓧杞闊?,
                                elem_classes="audio-mode-radio")

                            # 鈹€鈹€ 妯″紡A: 鏂囧瓧杞闊?鈹€鈹€
                            with gr.Group(visible=True) as tts_mode_group:
                                # 鈹€鈹€ TTS 妯″紡鍒囨崲 鈹€鈹€
                                # 閲嶆柊璇诲彇.env纭繚鑾峰彇鏈€鏂板€?
                                load_env_file()
                                current_tts_mode = os.getenv('TTS_MODE', 'local')
                                tts_mode_switch = gr.Radio(
                                    label="TTS 妯″紡",
                                    choices=["馃捇 鏈湴鐗?, "鈽侊笍 鍦ㄧ嚎鐗?],
                                    value="馃捇 鏈湴鐗? if current_tts_mode == 'local' else "鈽侊笍 鍦ㄧ嚎鐗?,
                                    elem_classes="voice-style-radio")
                                gr.HTML(
                                    '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                    '馃捇 <b>鏈湴鐗?/b>锛氫娇鐢ㄦ湰鏈?GPU 澶勭悊锛岄渶瑕佽緝楂橀厤缃?br>'
                                    '鈽侊笍 <b>鍦ㄧ嚎鐗?/b>锛氫娇鐢ㄤ簯绔湇鍔″櫒澶勭悊锛屾棤闇€楂橀厤缃樉鍗?/div>'
                                )
                                
                                gr.HTML('<div class="section-label">馃帣 闊宠壊閫夋嫨</div>')
                                with gr.Row():
                                    # 鏍规嵁褰撳墠TTS妯″紡杩囨护闊宠壊鍒楄〃
                                    voice_select = gr.Dropdown(
                                        label="浠庨煶鑹插簱閫夋嫨",
                                        choices=_vc.get_choices(current_tts_mode) if _LIBS_OK else [],
                                        value=None, interactive=True, scale=4)
                                    voice_refresh_btn = gr.Button("鉄?, scale=1, min_width=40,
                                                                  variant="secondary")
                                voice_preview = gr.Audio(label="馃攰 璇曞惉鎵€閫夐煶鑹?, interactive=False,
                                                         visible=False)
                                
                                # 闅愯棌鐨?prompt_audio 缁勪欢锛堢敤浜庡唴閮ㄩ€昏緫锛屼笉鏄剧ず缁欑敤鎴凤級
                                prompt_audio = gr.Audio(visible=False, type="filepath")

                                # 鈹€鈹€ 璇煶椋庢牸棰勮锛堜粎鏈湴鐗堝彲瑙侊級鈹€鈹€
                                _is_local_tts = (current_tts_mode == 'local')
                                with gr.Group(visible=_is_local_tts) as local_only_settings_group:
                                    voice_style = gr.Radio(
                                        label="璇煶椋庢牸",
                                        choices=["鏍囧噯", "绋冲畾鎾姤", "娲绘臣鐢熷姩", "鎱㈤€熸湕璇?, "涓撲笟妯″紡"],
                                        value="鏍囧噯",
                                        elem_classes="voice-style-radio")
                                    # 鈹€鈹€ 鍚堟垚閫熷害棰勮 鈹€鈹€
                                    tts_speed_preset = gr.Radio(
                                        label="鍚堟垚閫熷害",
                                        choices=list(TTS_SPEED_PRESETS.keys()),
                                        value="馃殌 蹇€?,
                                        elem_classes="voice-style-radio")
                                    gr.HTML(
                                        '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                        '鈿℃瀬蹇細鏈€蹇€熷害锛岄€傚悎棰勮璇曞惉<br>'
                                        '馃殌蹇€燂細閫熷害浼樺厛锛岄粯璁ゆ帹鑽愶紙FP16锛?br>'
                                        '鈿栵笍鏍囧噯锛氶€熷害涓庤川閲忓吋椤?br>'
                                        '鉁ㄩ珮璐ㄩ噺锛氭渶浣宠闊宠川閲忥紝閫熷害杈冩參</div>'
                                    )

                                    voice_speed = gr.Slider(
                                        label="璇€熻皟鑺?,
                                        info="鈫?鎱? |  蹇?鈫?,
                                        minimum=0.5, maximum=1.5, value=1.0, step=0.05)

                                with gr.Group(visible=False) as pro_mode_group:
                                    with gr.Row():
                                        top_p = gr.Slider(label="璇嶈澶氭牱鎬?, info="瓒婇珮瓒婇殢鏈?0.7~0.9", minimum=0.1, maximum=1.0, value=0.8, step=0.05)
                                        top_k = gr.Slider(label="鍊欓€夎瘝鏁伴噺", info="瓒婂皬瓒婁繚瀹?20~50", minimum=1, maximum=100, value=30, step=1)
                                    with gr.Row():
                                        temperature = gr.Slider(label="璇皵娲昏穬搴?, info="瓒婇珮瓒婃湁鍙樺寲", minimum=0.1, maximum=2.0, value=0.7, step=0.1)
                                        num_beams   = gr.Slider(label="鎼滅储绮惧害", info="瓒婇珮瓒婃參浣嗘洿鍑?, minimum=1, maximum=10, value=1, step=1)
                                    with gr.Row():
                                        repetition_penalty = gr.Slider(label="閬垮厤閲嶅", info="瓒婇珮瓒婁笉閲嶅", minimum=1.0, maximum=20.0, value=8.0, step=0.5)
                                        max_mel_tokens     = gr.Slider(label="鏈€澶ч暱搴?, info="闀挎枃鏈渶鍔犲ぇ", minimum=500, maximum=3000, value=1500, step=100)
                                    gr.HTML('<div class="divider"></div>')
                                    gr.Markdown("### 馃幁 鎯呮劅鎺у埗")
                                    emo_mode = gr.Radio(
                                        label="鎯呮劅鎺у埗妯″紡",
                                        choices=["涓庨煶鑹插弬鑰冮煶棰戠浉鍚?,"浣跨敤鎯呮劅鍙傝€冮煶棰?,"浣跨敤鎯呮劅鍚戦噺鎺у埗","浣跨敤鎯呮劅鎻忚堪鏂囨湰鎺у埗"],
                                        value="涓庨煶鑹插弬鑰冮煶棰戠浉鍚?)
                                    with gr.Group(visible=False) as emo_audio_group:
                                        emo_audio  = gr.Audio(label="鎯呮劅鍙傝€冮煶棰?, sources=["upload"], type="filepath")
                                        emo_weight = gr.Slider(label="鎯呮劅寮哄害", info="0=涓嶆贩鍚堟儏鎰燂紝1=瀹屽叏浣跨敤鎯呮劅鍙傝€?, minimum=0.0, maximum=1.0, value=0.6, step=0.1)
                                    with gr.Group(visible=False) as emo_vec_group:
                                        gr.Markdown("璋冩暣8涓儏鎰熷悜閲忕淮搴︼紙-1.0 鍒?1.0锛?)
                                        with gr.Row():
                                            vec1 = gr.Slider(label="鍚戦噺1", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                            vec2 = gr.Slider(label="鍚戦噺2", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                        with gr.Row():
                                            vec3 = gr.Slider(label="鍚戦噺3", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                            vec4 = gr.Slider(label="鍚戦噺4", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                        with gr.Row():
                                            vec5 = gr.Slider(label="鍚戦噺5", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                            vec6 = gr.Slider(label="鍚戦噺6", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                        with gr.Row():
                                            vec7 = gr.Slider(label="鍚戦噺7", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                            vec8 = gr.Slider(label="鍚戦噺8", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                    with gr.Group(visible=False) as emo_text_group:
                                        emo_text = gr.Textbox(
                                            label="鎯呮劅鎻忚堪鏂囨湰",
                                            placeholder="渚嬪锛氬紑蹇冦€佹偛浼ゃ€佹劋鎬?..",
                                            lines=2)
                                    def update_emo_visibility(mode):
                                        return (
                                            gr.update(visible=(mode=="浣跨敤鎯呮劅鍙傝€冮煶棰?)),
                                            gr.update(visible=(mode=="浣跨敤鎯呮劅鍚戦噺鎺у埗")),
                                            gr.update(visible=(mode=="浣跨敤鎯呮劅鎻忚堪鏂囨湰鎺у埗")))
                                    emo_mode.change(update_emo_visibility,
                                                    inputs=[emo_mode],
                                                    outputs=[emo_audio_group, emo_vec_group, emo_text_group])
                                gen_btn      = gr.Button("馃幍  寮€濮嬭闊冲悎鎴?, variant="primary", size="lg")
                                tts_hint = gr.HTML(value="")
                                output_audio = gr.Audio(label="鍚堟垚缁撴灉", interactive=False)

                            # 鈹€鈹€ 妯″紡B: 鐩存帴涓婁紶闊抽 鈹€鈹€
                            with gr.Group(visible=False) as upload_mode_group:
                                gr.HTML(
                                    '<div style="background:#f0f9ff;border:1.5px solid #bae6fd;'
                                    'border-radius:12px;padding:12px 14px;margin-bottom:12px;">'
                                    '<div style="font-size:13px;font-weight:700;color:#0c4a6e;margin-bottom:4px;">馃搧 鐩存帴涓婁紶闊抽鏂囦欢</div>'
                                    '<div style="font-size:11px;color:#0369a1;line-height:1.6;">'
                                    '涓婁紶宸叉湁鐨勯煶棰戞枃浠讹紝璺宠繃璇煶鍚堟垚姝ラ锛岀洿鎺ョ敤浜庤棰戝悎鎴愩€?br>'
                                    '鏀寔 WAV銆丮P3 绛夊父瑙佹牸寮忋€?/div></div>'
                                )
                                direct_audio_upload = gr.Audio(
                                    label="涓婁紶闊抽鏂囦欢锛圵AV / MP3锛?,
                                    sources=["upload"], type="filepath")

                    # 鈺愨晲鈺?姝ラ 3锛氳棰戝悎鎴?鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
                    with gr.Column(scale=2):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">3</div>'
                            '<span class="step-title">瑙嗛鍚堟垚</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            # 鈹€鈹€ 鏁板瓧浜洪€夋嫨 鈹€鈹€
                            gr.HTML('<div class="section-label">馃幁 鏁板瓧浜洪€夋嫨</div>')
                            with gr.Row():
                                avatar_select = gr.Dropdown(
                                    label="浠庢暟瀛椾汉搴撻€夋嫨",
                                    choices=_av.get_choices() if _LIBS_OK else [],
                                    value=None, interactive=True, scale=4)
                                avatar_refresh_btn = gr.Button("鉄?, scale=1, min_width=40,
                                                               variant="secondary")
                            avatar_preview = gr.Video(
                                label="棰勮", height=190, interactive=False, visible=False)
                            avatar_preview_title = gr.HTML(value="", visible=False)

                            # 鈹€鈹€ 鍚堟垚闊抽 鈹€鈹€
                            gr.HTML('<div class="section-label">馃攰 闊抽锛堣嚜鍔ㄥ紩鐢ㄦ楠?鐨勭粨鏋滐紝涔熷彲鎵嬪姩涓婁紶锛?/div>')
                            audio_for_ls = gr.Audio(
                                label="鐢ㄤ簬瑙嗛鍚堟垚鐨勯煶棰?,
                                type="filepath", interactive=True)

                            # 鈹€鈹€ 鍚堟垚妯″紡閫夋嫨锛堟湰鍦扮増/鍦ㄧ嚎鐗堬級鈹€鈹€
                            _default_heygem = os.getenv("HEYGEM_MODE", "local").strip().lower()
                            _heygem_default_label = "馃寪 鍦ㄧ嚎鐗堬紙鏈嶅姟鍣級" if _default_heygem == "online" else "馃捇 鏈湴鐗?
                            gr.HTML('<div class="section-label">馃枼锔?鍚堟垚妯″紡</div>')
                            heygem_mode_radio = gr.Radio(
                                label="閫夋嫨鍚堟垚鏂瑰紡",
                                choices=["馃捇 鏈湴鐗?, "馃寪 鍦ㄧ嚎鐗堬紙鏈嶅姟鍣級"],
                                value=_heygem_default_label,
                                elem_classes="voice-style-radio")
                            gr.HTML(
                                '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                '馃捇鏈湴鐗堬細浣跨敤鏈満GPU鍚堟垚锛岄渶瑕?heygem-win-50<br>'
                                '馃寪鍦ㄧ嚎鐗堬細涓婁紶鍒癓inux鏈嶅姟鍣ㄥ悎鎴愶紝闇€閰嶇疆 HEYGEM_SERVER_URL</div>'
                            )

                            # 鈹€鈹€ 鐢熸垚璐ㄩ噺閫夋嫨锛堜粎鏈湴鐗堝彲瑙侊級鈹€鈹€
                            _show_quality = (_default_heygem != "online")
                            with gr.Group(visible=_show_quality) as quality_group:
                                gr.HTML('<div class="section-label">鈿欙笍 鐢熸垚璐ㄩ噺</div>')
                                quality_preset = gr.Radio(
                                    label="閫熷害 鈫?璐ㄩ噺",
                                    choices=list(QUALITY_PRESETS.keys()),
                                    value="鈿栵笍 鏍囧噯",
                                    elem_classes="voice-style-radio")
                                gr.HTML(
                                    '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                    '鈿℃瀬蹇細6姝ワ紝閫熷害鏈€蹇紝閫傚悎棰勮<br>'
                                    '馃殌蹇€燂細8姝ワ紝閫熷害涓庤川閲忓吋椤?br>'
                                    '鈿栵笍鏍囧噯锛?2姝ワ紝榛樿鎺ㄨ崘<br>'
                                    '鉁ㄩ珮璐ㄩ噺锛?0姝ワ紝鏁堟灉鏈€浣充絾杈冩參</div>'
                                )

                            ls_btn = gr.Button("馃殌  寮€濮嬪悎鎴?, variant="primary", size="lg")
                            
                            # 鈹€鈹€ 鍚堟垚瑙嗛鏄剧ず鍖猴紙鍦ㄦ楠?鍐呴儴锛夆攢鈹€
                            ls_detail_html = gr.HTML(value="", visible=False, elem_id="ls-detail-box")
                            output_video = gr.Video(
                                label="鉁?鍚堟垚瑙嗛",
                                height=400, elem_id="output-video", interactive=False)

                    # 鈺愨晲鈺?姝ラ 4锛氬瓧骞曞悎鎴愪笌鐢讳腑鐢?鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
                    with gr.Column(scale=2):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">4</div>'
                            '<span class="step-title">瀛楀箷鍚堟垚涓庣敾涓敾</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            # 鈺愨晲 鐢讳腑鐢昏缃?鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
                            with gr.Group(elem_classes="pip-panel"):
                                gr.HTML(
                                    '<div class="subtitle-panel-head">'
                                    '<div class="subtitle-panel-icon">馃柤</div>'
                                    '<span class="subtitle-panel-title">鐢讳腑鐢昏缃?/span>'
                                    '</div>'
                                )
                                pip_enable = gr.Checkbox(
                                    label="馃柤 鍚敤鐢讳腑鐢?,
                                    value=False,
                                    elem_classes="kw-checkbox")
                                with gr.Group(visible=False) as pip_settings_group:
                                    pip_mode = gr.Radio(
                                        choices=["馃寪 鍦ㄧ嚎鐢熸垚", "馃搧 鏈湴涓婁紶"],
                                        value="馃寪 鍦ㄧ嚎鐢熸垚",
                                        label="鐢讳腑鐢绘ā寮?,
                                        elem_classes="audio-mode-radio")
                                    # 鍦ㄧ嚎妯″紡锛氭彁绀鸿瘝
                                    with gr.Group() as pip_online_group:
                                        pip_prompt = gr.TextArea(
                                            label="馃幀 鐢讳腑鐢绘彁绀鸿瘝",
                                            placeholder="鎻忚堪浣犳兂瑕佺殑瀹炴櫙鐢婚潰锛屽锛氱幇浠ｅ鍐呰淇柦宸ュ満鏅紝鐢婚潰骞插噣楂樼骇...\n锛圓I鏀瑰啓鏃朵細鑷姩鐢熸垚锛?,
                                            lines=3, max_lines=5)
                                        gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:2px 8px;">'
                                                '鎻愮ず璇嶈秺璇︾粏锛岀敓鎴愮殑鐢婚潰瓒婄簿鍑嗐€傜偣鍑汇€孉I鏀瑰啓+鏍囬鏍囩銆嶅彲鑷姩鐢熸垚銆?/div>')
                                    # 鏈湴涓婁紶妯″紡
                                    with gr.Group(visible=False) as pip_local_group:
                                        pip_local_files = gr.File(
                                            label="馃搧 涓婁紶鐢讳腑鐢昏棰戠礌鏉?,
                                            file_types=["video"],
                                            file_count="multiple")
                                        gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:2px 8px;">'
                                                '涓婁紶1-3涓棰戠墖娈碉紝灏嗛潤闊冲悗绌挎彃鍒板悎鎴愯棰戜腑銆?/div>')
                                    # 閫氱敤璁剧疆锛圓I鑷姩鍐冲畾绌挎彃浣嶇疆鍜屾椂闀匡紝闅愯棌鎵嬪姩鎺у埗锛?
                                    with gr.Row(visible=False):
                                        pip_interval = gr.Slider(
                                            minimum=8, maximum=30, value=15, step=1,
                                            label="绌挎彃闂撮殧(绉?")
                                        pip_clip_dur = gr.Slider(
                                            minimum=3, maximum=8, value=5, step=1,
                                            label="姣忔鏃堕暱(绉?")
                                    pip_btn = gr.Button("馃幀 鐢熸垚鐢讳腑鐢昏棰?, variant="primary", size="lg")
                                    pip_hint = gr.HTML(value="")
                            
                            # 鈺愨晲 瀛楀箷闈㈡澘 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
                            with gr.Group(elem_classes="subtitle-panel", elem_id="subtitle-panel-main"):
                                gr.HTML(
                                    '<div class="subtitle-panel-head">'
                                    '<div class="subtitle-panel-icon">鉁忥笍</div>'
                                    '<span class="subtitle-panel-title">鏅鸿兘瀛楀箷</span>'
                                    '<span class="subtitle-panel-tip">鉁?鏀寔鍏抽敭璇嶉珮浜?/span>'
                                    '</div>'
                                )
                                # 鍩烘湰璁剧疆锛氬瓧浣?瀛楀彿 浣嶇疆锛堝缁堝彲瑙侊級
                                with gr.Row():
                                    _font_grouped = _sub.get_font_choices_grouped() if _LIBS_OK else [("馃枼锔?绯荤粺瀛椾綋锛堥粯璁わ級", "绯荤粺瀛椾綋"), ("銆愪腑鏂囩畝浣撱€戞€濇簮榛戜綋 Bold", "SourceHanSansCN-Bold")]
                                    sub_font = gr.Dropdown(
                                        label="瀛椾綋",
                                        choices=_font_grouped,
                                        value="绯荤粺瀛椾綋",
                                        interactive=True, scale=3)
                                    sub_size = gr.Slider(label="瀛楀彿 px", minimum=16, maximum=72,
                                                         value=44, step=2, scale=3)
                                    sub_pos = gr.Radio(label="浣嶇疆", choices=["涓?,"涓?,"涓?],
                                                       value="涓?, scale=2,
                                                       elem_classes="sub-pos-radio")
                                # 瀛椾綋棰勮鍖哄煙
                                sub_font_preview = gr.HTML(value="", visible=False, elem_id="sub-font-preview")
                                # 鈹€鈹€ 楂樼骇璁剧疆鎸夐挳锛堝脊绐楀叆鍙ｏ級鈹€鈹€
                                sub_settings_open_btn = gr.Button(
                                    "鈿欙笍 楂樼骇璁剧疆", variant="secondary", size="sm",
                                    elem_classes="sub-settings-btn")

                            # 鈹€鈹€ 瀛楀箷楂樼骇璁剧疆寮圭獥锛堢嫭绔嬩簬瀛楀箷闈㈡澘锛夆攢鈹€
                            with gr.Group(visible=False, elem_id="sub-settings-modal") as sub_settings_modal:
                                gr.HTML(
                                    '<div style="text-align:center;margin-bottom:16px;">'
                                    '<div style="width:44px;height:44px;border-radius:12px;'
                                    'background:linear-gradient(135deg,#0ea5e9,#0284c7);'
                                    'display:flex;align-items:center;justify-content:center;'
                                    'margin:0 auto 12px;font-size:20px;'
                                    'box-shadow:0 4px 12px rgba(14,165,233,.3);">鈿欙笍</div>'
                                    '<div style="font-size:17px;font-weight:800;color:#0f172a;">瀛楀箷楂樼骇璁剧疆</div>'
                                    '</div>'
                                )
                                with gr.Row(elem_classes="sub-modal-columns"):
                                    # 鈺愨晲 宸︿晶锛氶鑹蹭笌鏍峰紡 + 鍏抽敭璇嶉珮浜?鈺愨晲
                                    with gr.Column(scale=1, min_width=260):
                                        gr.HTML('<div class="sub-modal-section">馃帹 棰滆壊涓庢牱寮?/div>')
                                        sub_color_txt = gr.ColorPicker(
                                            label="瀛楀箷棰滆壊", value="#FFFFFF")
                                        sub_hi_txt = gr.ColorPicker(
                                            label="楂樹寒棰滆壊", value="#FFD700")
                                        sub_outline_txt = gr.ColorPicker(
                                            label="鎻忚竟棰滆壊", value="#000000",
                                            elem_id="sub-outline-color")
                                        sub_outline_size = gr.Slider(
                                            label="鎻忚竟瀹藉害 px", minimum=0, maximum=10,
                                            value=6, step=1)
                                        # 鑳屾櫙棰滆壊闅愯棌锛堜笉鍐嶄娇鐢級
                                        sub_bg_color = gr.ColorPicker(
                                            value="#000000", visible=False)
                                        sub_bg_opacity = gr.Slider(
                                            value=0, visible=False)
                                        gr.HTML('<div class="sub-modal-section" style="margin-top:14px;">馃専 鍏抽敭璇嶉珮浜?/div>')
                                        with gr.Row():
                                            sub_kw_enable = gr.Checkbox(
                                                label="馃専 鍚敤鍏抽敭璇嶆斁澶ч珮浜?, value=False,
                                                scale=2, elem_classes="kw-checkbox")
                                            sub_hi_scale = gr.Slider(
                                                label="鏀惧ぇ鍊嶆暟", minimum=1.1, maximum=2.5,
                                                value=1.5, step=0.1, scale=2, visible=False)
                                        with gr.Row(visible=False) as sub_kw_row:
                                            sub_kw_text = gr.Textbox(
                                                label="鍏抽敭璇嶏紙閫楀彿鍒嗛殧锛?,
                                                placeholder="濡傦細渚垮疁,浼樿川,鎺ㄨ崘,闄愭椂  鈥?澶氫釜璇嶇敤閫楀彿闅斿紑",
                                                max_lines=1, scale=1)
                                        
                                        gr.HTML('<div class="sub-modal-section" style="margin-top:14px;">馃搷 浣嶇疆寰皟</div>')
                                        sub_pos_offset = gr.Slider(
                                            label="鍨傜洿鍋忕Щ px锛堟鏁板悜涓婏紝璐熸暟鍚戜笅锛?,
                                            minimum=-200, maximum=200,
                                            value=0, step=5,
                                            info="鍦ㄥ熀纭€浣嶇疆涓婂井璋?
                                        )
                                    # 鈺愨晲 鍙充晶锛欰I浼樺寲 + 鏍囬璁剧疆 + 瀛楀箷鍐呭 鈺愨晲
                                    with gr.Column(scale=1, min_width=260):
                                        gr.HTML('<div class="sub-modal-section">鉁?AI浼樺寲瀛楀箷</div>')
                                        gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:4px 8px;margin-bottom:8px;">AI鏅鸿兘浼樺寲瀛楀箷鏍囬鍜屽叧閿瘝楂樹寒</div>')
                                        subtitle_ai_optimize_btn = gr.Button("鉁?AI浼樺寲瀛楀箷", variant="secondary", size="sm")
                                        
                                        gr.HTML('<div class="sub-modal-section" style="margin-top:14px;">馃搶 鏍囬璁剧疆</div>')
                                        sub_title_text = gr.Textbox(
                                            label="鏍囬绗竴琛?,
                                            placeholder="杈撳叆绗竴琛屾爣棰樻枃瀛楋紝鐣欑┖鍒欎笉鏄剧ず鏍囬",
                                            max_lines=1)
                                        sub_title_text2 = gr.Textbox(
                                            label="鏍囬绗簩琛?,
                                            placeholder="杈撳叆绗簩琛屾爣棰樻枃瀛楋紙鍙€夛級",
                                            max_lines=1)
                                        with gr.Row():
                                            sub_title_font_size = gr.Slider(
                                                label="鏍囬瀛楀彿", minimum=12, maximum=96,
                                                value=68, step=1, scale=2)
                                            sub_title_duration = gr.Slider(
                                                label="鏄剧ず鏃堕暱(绉?", minimum=1, maximum=30,
                                                value=5, step=1, scale=2)
                                        with gr.Row():
                                            sub_title_margin_top = gr.Slider(
                                                label="璺濋《閮ㄨ窛绂?px", minimum=0, maximum=400,
                                                value=200, step=5, scale=2)
                                        with gr.Row():
                                            sub_title_color = gr.ColorPicker(
                                                label="鏍囬棰滆壊", value="#FFD700", scale=1)
                                            sub_title_outline_color = gr.ColorPicker(
                                                label="鏍囬鎻忚竟棰滆壊", value="#000000", scale=1)
                                        sub_text_modal = gr.Textbox(
                                            label="瀛楀箷鍐呭",
                                            value="",
                                            visible=False,
                                            lines=1)
                                # 鈹€鈹€ 搴曢儴鎸夐挳锛堝叏瀹斤級鈹€鈹€
                                with gr.Row():
                                    sub_settings_cancel_btn = gr.Button(
                                        "鍙栨秷", variant="secondary", size="lg",
                                        elem_classes="sub-modal-close-btn")
                                    sub_settings_close_btn = gr.Button(
                                        "鉁?纭畾", variant="primary", size="lg",
                                        elem_classes="sub-modal-close-btn")

                            with gr.Group(elem_classes="subtitle-panel", elem_id="subtitle-panel-tail"):
                                # 鈹€鈹€ 瀛楀箷鏂囨湰 + 鎸夐挳锛堝缁堝彲瑙侊級鈹€鈹€
                                sub_text = gr.Textbox(
                                    label="瀛楀箷鍐呭锛堣闊冲悎鎴愬悗鑷姩濉叆锛?,
                                    placeholder="瀹屾垚姝ラ1璇煶鍚堟垚鍚庝細鑷姩濉叆鏂囧瓧锛屼篃鍙墜鍔ㄧ紪杈?..",
                                    lines=2,
                                    visible=False)
                                sub_btn = gr.Button("鉁? 鐢熸垚甯﹀瓧骞曡棰?, variant="primary", size="lg")
                                sub_hint = gr.HTML(value="")
                        
                        # 瀛楀箷瑙嗛鏄剧ず鍖猴紙鐙珛鐨刾anel锛岀揣璺熷湪瀛楀箷闈㈡澘鍚庨潰锛?
                        with gr.Column(elem_classes="panel", visible=False, elem_id="sub-video-panel") as sub_video_panel:
                            sub_video = gr.Video(label="馃幀 瀛楀箷鐗堣棰?, height=280,
                                                 interactive=False)

                        # 姝ラ5锛欱GM鑳屾櫙闊充箰
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">5</div>'
                            '<span class="step-title">BGM鑳屾櫙闊充箰</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            bgm_enable = gr.Checkbox(label="馃幍 鍚敤鑳屾櫙闊充箰", value=False, elem_classes="kw-checkbox")
                            
                            bgm_types = gr.CheckboxGroup(
                                label="鑳屾櫙闊充箰绫诲瀷",
                                choices=list(_load_music_database().keys()),
                                value=[],
                            )
                            bgm_volume = gr.Slider(
                                label="鑳屾櫙闊充箰闊抽噺",
                                minimum=0.0, maximum=2.0, value=0.3, step=0.05
                            )
                            with gr.Row():
                                bgm_change_btn = gr.Button("馃攧 鏇存崲BGM", variant="secondary", size="sm")
                                bgm_mix_btn = gr.Button("馃幀 AI閫夋嫨BGM", variant="primary", size="sm")
                                bgm_custom_btn = gr.UploadButton("馃搧 涓婁紶鑷畾涔塀GM", file_types=["audio"], variant="secondary", size="sm")
                            # 闅愯棌鐨勮嚜瀹氫箟BGM缁勪欢锛堢敤浜庡唴閮ㄩ€昏緫锛?
                            bgm_custom_upload = gr.Audio(visible=False, type="filepath")
                            bgm_selected = gr.Textbox(visible=False, value="")
                            bgm_audio_preview = gr.Audio(label="璇曞惉BGM", interactive=False, visible=False)
                            bgm_hint = gr.HTML(value="")
                            bgm_path_hidden = gr.Textbox(visible=False, value="")
                            bgm_state = gr.State(value={"path": "", "title": ""})
                            bgm_video = gr.Video(label="馃幀 甯GM瑙嗛", height=280, interactive=False)

                        # 姝ラ6锛氬彂甯冨钩鍙帮紙涓嬫柟锛?
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">6</div>'
                            '<span class="step-title">鍙戝竷骞冲彴</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            gr.HTML('<div style="font-size:13px;color:#64748b;margin-bottom:12px;">浼樺厛鍙戝竷甯GM瑙嗛锛屽叾娆″瓧骞曡棰戯紝濡傛棤瀛楀箷鍒欏彂甯冨悎鎴愯棰?/div>')
                            
                            publish_platforms = gr.CheckboxGroup(
                                label="閫夋嫨鍙戝竷骞冲彴",
                                choices=["鎶栭煶", "瑙嗛鍙?, "鍝斿摡鍝斿摡", "灏忕孩涔?, "蹇墜"],
                                value=["鎶栭煶"],
                                elem_classes="publish-platform-checkbox"
                            )
                            
                            douyin_title = gr.Textbox(
                                label="瑙嗛鏍囬",
                                placeholder="鑷姩浣跨敤璇煶鏂囧瓧鍓?0瀛楋紝涔熷彲鎵嬪姩淇敼...",
                                max_lines=2)
                            
                            douyin_topics = gr.Textbox(
                                label="璇濋鏍囩锛堥€楀彿鍒嗛殧锛?,
                                placeholder="濡傦細缇庨,鎺㈠簵,鎺ㄨ崘",
                                max_lines=1)
                            
                            gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:4px 8px;margin-bottom:8px;">浣跨敤AI鏅鸿兘浼樺寲鏍囬骞剁敓鎴?涓瘽棰樻爣绛?/div>')
                            optimize_btn = gr.Button("鉁?AI浼樺寲", variant="secondary", size="sm")
                            
                            douyin_btn = gr.Button("馃殌 鍙戝竷鍒伴€変腑骞冲彴", variant="primary", size="lg")
                            douyin_hint = gr.HTML(value="")
                    
            # 鈹€鈹€ Tab 2锛氭暟瀛椾汉绠＄悊 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
            with gr.Tab("馃幁  鏁板瓧浜?):
                with gr.Row(elem_classes="workspace"):

                    # 宸﹀垪锛氫笂浼?
                    with gr.Column(scale=1):
                        # 鏍囬鍦ㄥ闈紝鏈夌嫭绔嬭儗鏅?
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);">锛?/div>'
                            '<span class="step-title">娣诲姞鏁板瓧浜?/span>'
                            '</div>'
                        )
                        # 鍐呭鍦ㄧ櫧鑹瞤anel閲?
                        with gr.Column(elem_classes="panel"):
                            av_upload = gr.File(
                                label="涓婁紶瑙嗛锛圡P4 / AVI / MOV / WMV锛?,
                                file_types=["video"], type="filepath")
                            av_upload_preview = gr.Video(
                                label="棰勮", height=150, interactive=False, visible=False)
                            av_name = gr.Textbox(
                                label="鏁板瓧浜哄悕绉?,
                                placeholder="涓烘鏁板瓧浜鸿捣涓€涓悕瀛?..", max_lines=1)
                            av_save_btn  = gr.Button("馃捑  淇濆瓨", variant="primary", size="lg")
                            av_save_hint = gr.HTML(value="")
                            gr.HTML(
                                '<div style="font-size:11px;color:#94a3b8;line-height:2;margin-top:10px;">'
                                '馃挕 淇濆瓨鍚庡彲鍦ㄥ伐浣滃彴鐩存帴閫夌敤<br>'
                                '馃搧 瀛樺偍浜?<b>avatars/</b> 鐩綍</div>'
                            )
                            # 闅愯棌鐨勫垹闄ゆ帶浠讹紙鐢卞垪琛ㄦ寜閽Е鍙戯級
                            av_del_dd   = gr.Textbox(visible=False, value="")
                            av_del_btn  = gr.Button("鍒犻櫎", visible=False)
                            av_del_hint = gr.HTML(value="")

                    # 鍙冲垪锛氱敾寤婏紙琛屽唴馃棏锛? JS妗ユ帴闅愯棌杈撳叆 + 棰勮
                    with gr.Column(scale=2):
                        # 鏍囬鍦ㄥ闈紝鏈夌嫭绔嬭儗鏅?
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">馃搵</div>'
                            '<span class="step-title">鏁板瓧浜哄簱</span>'
                            '</div>'
                        )
                        # 鍐呭鍦ㄧ櫧鑹瞤anel閲?
                        with gr.Column(elem_classes="panel"):
                            av_gallery = gr.HTML(
                                value=_av.render_gallery("av-del-input", "av-prev-trigger") if _LIBS_OK else "")
                            # JS妗ユ帴锛氬崱鐗囦笂鐨勷煑戞寜閽啓鍏ユ闅愯棌textbox瑙﹀彂鍒犻櫎
                            with gr.Row(elem_id="av-del-input-row"):
                                av_del_js_input = gr.Textbox(
                                elem_id="av-del-input", value="", interactive=True)
                        # JS妗ユ帴锛氬崱鐗囩偣鍑诲啓鍏ユ闅愯棌textbox瑙﹀彂棰勮
                        with gr.Row(elem_id="av-prev-trigger-row"):
                            av_prev_js_input = gr.Textbox(
                                elem_id="av-prev-trigger", value="", interactive=True)
                        av_del_real_hint = gr.HTML(value="")
                        gr.HTML('<div class="divider"></div>')
                        gr.HTML('<div class="section-label">馃攳 棰勮锛堢偣鍑讳笂鏂瑰崱鐗囷級</div>')
                        av_prev_video = gr.Video(label="", height=240, interactive=False)
                        av_prev_title = gr.HTML(value="")

            # 鈹€鈹€ Tab 4锛氶煶鑹叉ā鍨?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
            with gr.Tab("馃帣  闊宠壊妯″瀷"):
                with gr.Row(elem_classes="workspace"):

                    # 宸﹀垪锛氫笂浼?
                    with gr.Column(scale=1):
                        # 鏍囬鍦ㄥ闈紝鏈夌嫭绔嬭儗鏅?
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#0ea5e9,#0284c7);">锛?/div>'
                            '<span class="step-title">娣诲姞闊宠壊</span>'
                            '</div>'
                        )
                        # 鍐呭鍦ㄧ櫧鑹瞤anel閲?
                        with gr.Column(elem_classes="panel"):
                            # 鈹€鈹€ 鐗堟湰閫夋嫨 鈹€鈹€
                            vc_source = gr.Radio(
                                label="闊宠壊鐗堟湰",
                                choices=["馃捇 鏈湴鐗堬紙鏈満澶勭悊锛?, "鈽侊笍 鍦ㄧ嚎鐗堬紙浜戠澶勭悊锛?],
                                value="馃捇 鏈湴鐗堬紙鏈満澶勭悊锛?,
                                elem_classes="voice-style-radio")
                            gr.HTML(
                                '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                '馃捇 <b>鏈湴鐗?/b>锛氫娇鐢ㄦ湰鏈?GPU 澶勭悊锛岄渶瑕佽緝楂橀厤缃?br>'
                                '鈽侊笍 <b>鍦ㄧ嚎鐗?/b>锛氫娇鐢ㄤ簯绔湇鍔″櫒澶勭悊锛屾棤闇€楂橀厤缃樉鍗?/div>'
                            )
                            vc_upload = gr.Audio(
                                label="涓婁紶鍙傝€冮煶棰戯紙3-10绉?WAV/MP3锛?,
                                sources=["upload"], type="filepath")
                            vc_name = gr.Textbox(
                                label="闊宠壊鍚嶇О",
                                placeholder="涓烘闊宠壊璧蜂竴涓悕瀛?..", max_lines=1)
                            vc_save_btn  = gr.Button("馃捑  淇濆瓨", variant="primary", size="lg")
                            vc_save_hint = gr.HTML(value="")
                            gr.HTML(
                                '<div style="font-size:11px;color:#94a3b8;line-height:2;margin-top:10px;">'
                                '馃挕 淇濆瓨鍚庡彲鍦ㄥ伐浣滃彴鐩存帴閫夌敤<br>'
                                '馃捇 鏈湴鐗堝瓨鍌ㄤ簬 <b>voices/</b> 鐩綍<br>'
                                '鈽侊笍 鍦ㄧ嚎鐗堝瓨鍌ㄥ湪浜戠鏈嶅姟鍣?/div>'
                            )
                            # 鈹€鈹€ 鍚屾鍦ㄧ嚎闊宠壊鎸夐挳 鈹€鈹€
                            vc_sync_btn = gr.Button("馃攧 鍚屾鍦ㄧ嚎闊宠壊", variant="secondary", size="sm")
                            vc_del_dd   = gr.Textbox(visible=False, value="")
                            vc_del_btn  = gr.Button("鍒犻櫎", visible=False)
                            vc_del_hint = gr.HTML(value="")

                    # 鍙冲垪锛氱敾寤婏紙琛屽唴馃棏锛? JS妗ユ帴 + 璇曞惉
                    with gr.Column(scale=2):
                        # 鏍囬鍦ㄥ闈紝鏈夌嫭绔嬭儗鏅?
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#0ea5e9,#0284c7);">馃搵</div>'
                            '<span class="step-title">闊宠壊搴?/span>'
                            '</div>'
                        )
                        # 鍐呭鍦ㄧ櫧鑹瞤anel閲?
                        with gr.Column(elem_classes="panel"):
                            vc_gallery = gr.HTML(
                                value=_vc.render_gallery("vc-del-input", "vc-prev-trigger") if _LIBS_OK else "")
                            with gr.Row(elem_id="vc-del-input-row"):
                                vc_del_js_input = gr.Textbox(
                                    elem_id="vc-del-input", value="", interactive=True)
                            # JS妗ユ帴锛氬崱鐗囩偣鍑诲啓鍏ユ闅愯棌textbox瑙﹀彂璇曞惉
                            with gr.Row(elem_id="vc-prev-trigger-row"):
                                vc_prev_js_input = gr.Textbox(
                                    elem_id="vc-prev-trigger", value="", interactive=True)
                            vc_del_real_hint = gr.HTML(value="")
                            gr.HTML('<div class="divider"></div>')
                            gr.HTML('<div class="section-label">馃攰 璇曞惉锛堢偣鍑讳笂鏂瑰崱鐗囷級</div>')
                            vc_prev_audio = gr.Audio(label="", interactive=False)

            # 鈹€鈹€ Tab 5锛氭壒閲忎换鍔?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
            with gr.Tab("鈿? 鎵归噺浠诲姟"):
                with gr.Row(elem_classes="workspace"):

                    # 鈺愨晲 宸﹀垪锛氭柊寤轰换鍔¤〃鍗?鈺愨晲
                    with gr.Column(scale=1, elem_classes="panel bt-form"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">锛?/span>鏂板缓浠诲姟</div>')

                        bt_name = gr.Textbox(label="浠诲姟鍚嶇О",
                            placeholder="鐣欑┖鑷姩缂栧彿锛堜换鍔?銆佷换鍔?鈥︼級", max_lines=1)

                        # 鈹€鈹€ 姝ラ 1锛氶煶棰?鈹€鈹€
                        gr.HTML('<div class="bt-step-row"><span class="step-chip" style="width:20px;height:20px;font-size:11px;">1</span><span class="bt-step-label">閫夋嫨闊抽鏉ユ簮</span></div>')
                        bt_audio_mode = gr.Radio(
                            choices=["鏂囧瓧鍚堟垚璇煶", "涓婁紶闊抽鏂囦欢"],
                            value="鏂囧瓧鍚堟垚璇煶", label="", elem_classes="bt-radio")

                        with gr.Group(visible=True) as bt_tts_group:
                            bt_text = gr.Textbox(label="鍚堟垚鏂囧瓧鍐呭",
                                placeholder="杈撳叆瑕佽浆鎹负璇煶鐨勬枃瀛?..", lines=3)
                            bt_ref_audio = gr.Audio(label="鍙傝€冮煶鑹诧紙3~10 绉掞級",
                                sources=["upload"], type="filepath")

                        with gr.Group(visible=False) as bt_custom_audio_group:
                            bt_custom_audio = gr.Audio(label="涓婁紶闊抽锛圵AV / MP3锛?,
                                sources=["upload"], type="filepath")

                        # 鈹€鈹€ 姝ラ 2锛氳棰?鈹€鈹€
                        gr.HTML('<div class="bt-step-row"><span class="step-chip" style="width:20px;height:20px;font-size:11px;">2</span><span class="bt-step-label">閫夋嫨瑙嗛鏉ユ簮</span></div>')
                        bt_video_mode = gr.Radio(
                            choices=["浣跨敤鍏叡瑙嗛", "涓婁紶涓撳睘瑙嗛"],
                            value="浣跨敤鍏叡瑙嗛", label="", elem_classes="bt-radio")

                        with gr.Group(visible=False) as bt_own_video_group:
                            bt_own_video = gr.File(label="涓撳睘瑙嗛锛堜粎姝や换鍔★級",
                                file_types=["video"], type="filepath")

                        # 鈹€鈹€ 姝ラ 3锛氭坊鍔?鈹€鈹€
                        gr.HTML('<div class="bt-step-row"><span class="step-chip" style="width:20px;height:20px;font-size:11px;">3</span><span class="bt-step-label">鍔犲叆浠诲姟闃熷垪</span></div>')
                        bt_add_hint = gr.HTML(value="")
                        bt_add_btn  = gr.Button("鉃? 鍔犲叆闃熷垪", variant="primary", size="lg")

                    # 鈺愨晲 鍙冲垪锛氬叕鍏辫棰?+ 鎵规璁剧疆 + 闃熷垪 鈺愨晲
                    with gr.Column(scale=2, elem_classes="panel bt-queue"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">馃搵</span>浠诲姟闃熷垪涓庤缃?/div>')

                        # 椤堕儴锛氬叕鍏辫棰?+ 鎵规鍚嶇О 妯帓
                        with gr.Row():
                            with gr.Column(scale=1):
                                gr.HTML('<div class="bt-section-title">馃幀 鍏叡瑙嗛</div>')
                                bt_shared_video = gr.File(label="鎵€鏈変换鍔″叡浜浜虹墿瑙嗛",
                                    file_types=["video"], type="filepath")
                            with gr.Column(scale=1):
                                gr.HTML('<div class="bt-section-title">馃搧 鎵规鍚嶇О</div>')
                                bt_batch_name = gr.Textbox(label="杈撳嚭鏂囦欢澶瑰悕",
                                    placeholder="鐣欑┖鍒欎娇鐢ㄦ椂闂存埑", max_lines=1)
                                gr.HTML('<div style="font-size:11px;color:#94a3b8;margin-top:2px;">杈撳嚭鐩綍锛歶nified_outputs / <b>鏃堕棿鎴砡鎵规鍚?/b></div>')

                        gr.HTML('<div class="divider"></div>')

                        # 浠诲姟鍒楄〃锛圝S 涓殑鍙夊彿浼氭妸 index 鍐欏叆闅愯棌 textbox锛?
                        bt_task_list_html = gr.HTML(
                            value=_render_task_list([]), elem_id="bt-task-list")

                        # 闅愯棌瑙﹀彂鍣細JS 鍐欏叆搴忓彿 鈫?Python 鍒犻櫎
                        bt_del_trigger = gr.Textbox(value="", visible=False,
                            elem_id="bt-del-trigger")

                        gr.HTML('<div class="divider"></div>')
                        with gr.Row():
                            bt_start_btn = gr.Button("馃殌  寮€濮嬫壒閲忕敓鎴?, variant="primary", scale=3)
                            bt_clear_btn = gr.Button("馃棏 娓呯┖闃熷垪", variant="stop", scale=1)

                        bt_progress_html = gr.HTML(value="", visible=False, elem_id="bt-progress-box")

                bt_tasks_state = gr.State([])

                # 鈹€鈹€ AI浼樺寲鐘舵€佽窡韪?鈹€鈹€
                ai_rewrite_done = gr.State(False)

                # 鈹€鈹€ 浜嬩欢锛氬垏鎹㈤煶棰戞潵婧?鈹€鈹€
                bt_audio_mode.change(
                    lambda m: (gr.update(visible=(m=="鏂囧瓧鍚堟垚璇煶")),
                               gr.update(visible=(m=="涓婁紶闊抽鏂囦欢"))),
                    inputs=[bt_audio_mode], outputs=[bt_tts_group, bt_custom_audio_group])

                # 鈹€鈹€ 浜嬩欢锛氬垏鎹㈣棰戞潵婧?鈹€鈹€
                bt_video_mode.change(
                    lambda m: gr.update(visible=(m=="涓婁紶涓撳睘瑙嗛")),
                    inputs=[bt_video_mode], outputs=[bt_own_video_group])

                # 鈹€鈹€ 浜嬩欢锛氭坊鍔犱换鍔?鈹€鈹€
                def _bt_add(tasks, name, am, text, ref, cust, vm, ov):
                    idx = len(tasks) + 1
                    tn  = name.strip() if name.strip() else f"浠诲姟{idx}"
                    if am == "鏂囧瓧鍚堟垚璇煶":
                        if not text.strip():
                            return tasks, _render_task_list(tasks), _hint("warning","璇峰～鍐欏悎鎴愭枃瀛楀唴瀹?)
                        if not ref:
                            return tasks, _render_task_list(tasks), _hint("warning","璇蜂笂浼犲弬鑰冮煶鑹?)
                    else:
                        if not cust:
                            return tasks, _render_task_list(tasks), _hint("warning","璇蜂笂浼犻煶棰戞枃浠?)
                    if vm == "涓婁紶涓撳睘瑙嗛" and not ov:
                        return tasks, _render_task_list(tasks), _hint("warning","璇蜂笂浼犱笓灞炶棰戞垨鍒囨崲涓哄叕鍏辫棰?)
                    task = {"id":idx,"name":tn,
                            "audio_mode":"tts" if am=="鏂囧瓧鍚堟垚璇煶" else "custom",
                            "text":text,"ref_audio":ref,"audio_path":cust,
                            "video_mode":"shared" if vm=="浣跨敤鍏叡瑙嗛" else "own",
                            "video_path":ov,"status":"绛夊緟涓?}
                    nt = tasks + [task]
                    # 濡傛灉鐢ㄤ簡鍏叡瑙嗛锛岄澶栨彁绀?
                    hint_msg = f"宸叉坊鍔犮€寋tn}銆嶏紝鍏?{len(nt)} 涓换鍔?
                    if task["video_mode"] == "shared":
                        hint_msg += " 锝?鈿狅笍 璇风‘淇濆凡鍦ㄥ彸渚т笂浼犲叕鍏辫棰?
                    return nt, _render_task_list(nt), _hint("ok", hint_msg)

                bt_add_btn.click(_bt_add,
                    inputs=[bt_tasks_state, bt_name, bt_audio_mode, bt_text,
                            bt_ref_audio, bt_custom_audio, bt_video_mode, bt_own_video],
                    outputs=[bt_tasks_state, bt_task_list_html, bt_add_hint])

                # 鈹€鈹€ 浜嬩欢锛氳鍐呭弶鍙峰垹闄わ紙JS 瑙﹀彂闅愯棌 textbox锛夆攢鈹€
                def _bt_del_by_trigger(tasks, trigger_val):
                    if not trigger_val or not trigger_val.strip():
                        return tasks, _render_task_list(tasks)
                    try:
                        di = int(trigger_val.strip()) - 1
                    except ValueError:
                        return tasks, _render_task_list(tasks)
                    if di < 0 or di >= len(tasks):
                        return tasks, _render_task_list(tasks)
                    nt = [t for j,t in enumerate(tasks) if j != di]
                    for k,t in enumerate(nt):
                        t["id"] = k+1
                    return nt, _render_task_list(nt)

                bt_del_trigger.change(_bt_del_by_trigger,
                    inputs=[bt_tasks_state, bt_del_trigger],
                    outputs=[bt_tasks_state, bt_task_list_html])

                # 鈹€鈹€ 浜嬩欢锛氭竻绌洪槦鍒?鈹€鈹€
                bt_clear_btn.click(
                    lambda: ([], _render_task_list([]), "", gr.update(visible=False)),
                    outputs=[bt_tasks_state, bt_task_list_html, bt_add_hint, bt_progress_html])

                # 鈹€鈹€ 浜嬩欢锛氬紑濮嬫壒閲忕敓鎴?鈹€鈹€
                def _bt_run(tasks, shared_video, batch_name, progress=gr.Progress()):
                    if not tasks:
                        yield (gr.update(visible=True, value=_hint("warning","璇峰厛娣诲姞鑷冲皯涓€涓换鍔?)),
                               gr.update(), gr.update()); return

                    # 鈹€鈹€ 鍓嶇疆鏍￠獙锛氭湁浠诲姟鐢ㄥ叕鍏辫棰戜絾鏈笂浼?鈹€鈹€
                    needs_shared = any(t.get("video_mode") == "shared" for t in tasks)
                    if needs_shared and (not shared_video or not os.path.exists(str(shared_video))):
                        sc = sum(1 for t in tasks if t.get("video_mode") == "shared")
                        yield (gr.update(visible=True, value=_hint("error",
                               f"鏈?{sc} 涓换鍔¤缃负銆屼娇鐢ㄥ叕鍏辫棰戙€嶏紝璇峰厛鍦ㄥ彸涓婅涓婁紶鍏叡浜虹墿瑙嗛锛?)),
                               gr.update(), gr.update()); return

                    ts_str = time.strftime("%Y%m%d_%H%M%S")
                    safe_nm = re.sub(r'[\\/:*?"<>|]', '', batch_name.strip()) if batch_name.strip() else ""
                    folder_name = f"{ts_str}_{safe_nm}" if safe_nm else ts_str
                    batch_dir   = os.path.join(OUTPUT_DIR, folder_name)
                    os.makedirs(batch_dir, exist_ok=True)
                    import copy
                    rt    = copy.deepcopy(tasks)
                    total = len(rt)

                    def _y(done, status, msg):
                        return (gr.update(visible=True, value=_render_batch_prog(done,total,"",status,msg,batch_dir)),
                                gr.update(visible=True, value=_render_task_list(rt)),
                                gr.update())

                    yield _y(0,"杩愯涓?,"鍑嗗寮€濮嬶紝鍔犺浇璧勬簮涓?..")
                    for i,task in enumerate(rt):
                        idx = i+1; tn = task.get("name",f"浠诲姟{idx}")
                        rt[i]["status"] = "杩涜涓?
                        yield _y(i,"杩愯涓?,f"鈻?姝ｅ湪澶勭悊 {tn}锛坽idx}/{total}锛?)
                        try:
                            if task.get("audio_mode") == "tts":
                                ao = os.path.join(batch_dir, f"闊抽_{idx}.wav")
                                progress(0.1, desc=f"[{idx}/{total}] {tn} 鈥?鍚堟垚璇煶...")
                                generate_speech_batch(task["text"], task["ref_audio"], ao)
                                ap = ao
                            else:
                                ap = task.get("audio_path")
                                if not ap or not os.path.exists(ap):
                                    raise RuntimeError("闊抽鏂囦欢涓嶅瓨鍦?)
                                ext = os.path.splitext(ap)[1]
                                dst = os.path.join(batch_dir, f"闊抽_{idx}{ext}")
                                shutil.copy2(ap, dst); ap = dst
                            if task.get("video_mode") == "shared":
                                if not shared_video or not os.path.exists(shared_video):
                                    raise RuntimeError("鍏叡瑙嗛鏈笂浼?)
                                vp = shared_video
                            else:
                                vp = task.get("video_path")
                                if not vp or not os.path.exists(vp):
                                    raise RuntimeError("涓撳睘瑙嗛涓嶅瓨鍦?)
                            op = os.path.join(batch_dir, f"浠诲姟{idx}.mp4")
                            progress(0.3, desc=f"[{idx}/{total}] {tn} 鈥?瑙嗛鍚堟垚...")
                            run_heygem_auto(vp, ap, output_path_override=op, steps=12, if_gfpgan=False)
                            rt[i]["status"] = "鉁?瀹屾垚"
                            yield _y(idx,"杩愯涓?,f"鉁?{tn} 瀹屾垚 鈫?浠诲姟{idx}.mp4")
                        except Exception as e:
                            rt[i]["status"] = "鉂?澶辫触"
                            yield _y(i,"杩愯涓?,f"鉂?{tn} 澶辫触锛歿str(e)[:80]}")

                    dc = sum(1 for t in rt if t["status"]=="鉁?瀹屾垚")
                    fc = total-dc
                    fm = f"鍏ㄩ儴瀹屾垚锛佹垚鍔?{dc} 涓? + (f"锛屽け璐?{fc} 涓? if fc else "")
                    yield (gr.update(visible=True, value=_render_batch_prog(total,total,"","宸插畬鎴?,fm,batch_dir)),
                           gr.update(visible=True, value=_render_task_list(rt)),
                           gr.update(value=[]))

                bt_start_btn.click(_bt_run,
                    inputs=[bt_tasks_state, bt_shared_video, bt_batch_name],
                    outputs=[bt_progress_html, bt_task_list_html, bt_tasks_state])


        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲 浜嬩欢缁戝畾 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲

        def _hint_html(kind, msg):
            cfg = {
                "ok":      ("#f0fdf4","鉁?,"#15803d"),
                "warning": ("#fff7ed","鈿狅笍","#92400e"),
                "error":   ("#fff1f2","鉂?,"#be123c"),
            }
            bg, ic, tc = cfg.get(kind, cfg["error"])
            return (f'<div style="background:{bg};border-radius:8px;padding:8px 12px;'
                    f'font-size:12px;color:{tc};font-weight:600;'
                    f'font-family:Microsoft YaHei,sans-serif;margin-top:4px;">'
                    f'{ic} {msg}</div>')

        def _make_progress_banner(stage: str, pct: int, cur: int, total: int) -> str:
            """鐢熸垚甯х敾闈㈣繘搴︽í骞?HTML"""
            bar_w = max(2, pct)
            return (
                f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
                f'border:1.5px solid #6366f1;border-radius:12px;'
                f'padding:14px 20px;margin:0 0 12px;'
                f'box-shadow:0 4px 16px rgba(99,102,241,.2);">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                f'<div style="width:10px;height:10px;border-radius:50%;background:#6366f1;'
                f'animation:zdai-pulse 1.2s infinite;flex-shrink:0;"></div>'
                f'<span style="font-size:13px;font-weight:700;color:#e2e8f0;font-family:Microsoft YaHei,sans-serif;">'
                f'{stage}</span>'
                f'<span style="margin-left:auto;font-size:14px;font-weight:800;color:#6366f1;">{pct}%</span>'
                f'</div>'
                f'<div style="background:rgba(99,102,241,.15);border-radius:6px;height:8px;overflow:hidden;">'
                f'<div style="height:100%;width:{bar_w}%;border-radius:6px;'
                f'background:linear-gradient(90deg,#6366f1,#8b5cf6);transition:width .3s;"></div></div>'
                f'<div style="font-size:11px;color:#64748b;margin-top:6px;font-family:Microsoft YaHei,sans-serif;">'
                f'宸插鐞?{cur} / {total} 甯?/div>'
                f'<style>@keyframes zdai-pulse{{0%,100%{{opacity:1;transform:scale(1)}}'
                f'50%{{opacity:.5;transform:scale(.8)}}}}</style>'
                f'</div>'
            )

        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
        #  宸ヤ綔鍙拌褰曚繚瀛樹笌鎭㈠
        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
        def _load_workspace_records():
            """鍔犺浇鎵€鏈夊伐浣滃彴璁板綍"""
            if not os.path.exists(WORKSPACE_RECORDS_FILE):
                return []
            try:
                with open(WORKSPACE_RECORDS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []

        def _save_workspace_record(record):
            """淇濆瓨涓€鏉″伐浣滃彴璁板綍"""
            try:
                records = _load_workspace_records()
                records.insert(0, record)
                records = records[:100]  # 鏈€澶氫繚鐣?00鏉?
                with open(WORKSPACE_RECORDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                print(f"[ERROR] 淇濆瓨宸ヤ綔鍙拌褰曞け璐? {e}")
                return False

        def _get_workspace_record_choices():
            """鑾峰彇宸ヤ綔鍙拌褰曠殑涓嬫媺妗嗛€夐」"""
            records = _load_workspace_records()
            if not records:
                return []
            
            choices = []
            for i, rec in enumerate(records):
                record_name = rec.get("record_name", "")
                if not record_name:
                    text = rec.get("input_text", "")
                    if text and text.strip():
                        record_name = text[:10]
                    else:
                        record_name = rec.get("time", "鏈煡鏃堕棿")
                
                time_str = rec.get("time", "")
                # 鏍煎紡锛氬悕绉?(鏃堕棿)锛屽€间负绱㈠紩
                choice_label = f"{record_name} ({time_str})"
                choices.append((choice_label, str(i)))
            
            return choices


        def _delete_workspace_record_by_dropdown(selected_value):
            """閫氳繃涓嬫媺妗嗛€夋嫨鍒犻櫎宸ヤ綔鍙拌褰?""
            try:
                if not selected_value:
                    return gr.update(), _hint_html("warning", "璇峰厛閫夋嫨瑕佸垹闄ょ殑璁板綍")
                
                record_idx = int(selected_value)
                records = _load_workspace_records()
                
                if record_idx < 0 or record_idx >= len(records):
                    return gr.update(), _hint_html("error", "璁板綍涓嶅瓨鍦ㄦ垨宸茶鍒犻櫎")
                
                rec = records.pop(record_idx)
                with open(WORKSPACE_RECORDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                
                rec_name = rec.get("record_name") or rec.get("time", "璇ヨ褰?)
                new_choices = _get_workspace_record_choices()
                return gr.update(choices=new_choices, value=None), _hint_html("ok", f"宸插垹闄よ褰曪細{rec_name}")
            except Exception as e:
                return gr.update(), _hint_html("error", f"鍒犻櫎澶辫触: {e}")
        
        def _clear_workspace_records():
            """娓呯┖鎵€鏈夊伐浣滃彴璁板綍"""
            try:
                if os.path.exists(WORKSPACE_RECORDS_FILE):
                    os.remove(WORKSPACE_RECORDS_FILE)
                return gr.update(choices=[], value=None), _hint_html("ok", "宸叉竻绌烘墍鏈夊伐浣滃彴璁板綍")
            except Exception as e:
                return gr.update(), _hint_html("error", f"娓呯┖澶辫触: {e}")

        def _auto_save_workspace(input_text, prompt_audio, voice_select_val, audio_mode_val,
                                direct_audio, avatar_select_val, audio_for_ls_val,
                                output_audio_val, output_video_val,
                                sub_text_val, sub_video_val,
                                # 瀛楀箷鍙傛暟
                                sub_font_val, sub_size_val, sub_pos_val, sub_pos_offset_val,
                                sub_color_val, sub_hi_val, sub_outline_val, sub_outline_size_val,
                                sub_bg_color_val, sub_bg_opacity_val,
                                sub_kw_enable_val, sub_hi_scale_val, sub_kw_text_val,
                                # 鍙戝竷鍙傛暟
                                douyin_title_val="", douyin_topics_val="",
                                # 瀛楀箷鏍囬鍙傛暟
                                sub_title_text_val="",
                                sub_title_text2_val="",
                                # 鐗囧ご鍙傛暟
                                intro_enable_val=None,
                                # 鐢讳腑鐢诲弬鏁?
                                pip_enable_val=None,
                                pip_mode_val=None,
                                pip_prompt_val=None,
                                pip_interval_val=None,
                                pip_clip_dur_val=None,
                                # 鍙€夛細鐢ㄤ簬 AI 鏀瑰啓鍦烘櫙锛屾寜鍘熸枃鏌ユ壘宸叉湁璁板綍骞舵浛鎹?
                                search_key=None):
            """鑷姩淇濆瓨褰撳墠宸ヤ綔鍙扮姸鎬?- 鐩稿悓鏂囨湰鍒欐洿鏂帮紝涓嶅悓鏂囨湰鍒欐柊寤?
            褰?search_key 涓嶄负 None 鏃讹紝鐢?search_key 鏌ユ壘宸叉湁璁板綍锛堢敤浜?AI 鏀瑰啓鍦烘櫙锛氭寜鍘熸枃鏌ユ壘骞剁敤鏀瑰啓鍚庣殑鏂囨鏇挎崲锛?
            """
            try:
                # 寮哄埗杈撳嚭鍒版枃浠朵互渚胯皟璇?
                debug_file = os.path.join(OUTPUT_DIR, "debug_save.txt")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] _auto_save_workspace 琚皟鐢╘n")
                    f.write(f"  output_audio_val type: {type(output_audio_val)}, value: {output_audio_val}\n")
                    f.write(f"  audio_for_ls_val type: {type(audio_for_ls_val)}, value: {audio_for_ls_val}\n")
                    f.write(f"  output_video_val type: {type(output_video_val)}, value: {output_video_val}\n")
                    f.write(f"  sub_text_val: {sub_text_val}\n")
                    f.write(f"  sub_title_text_val: {sub_title_text_val}\n")
                    f.write(f"  sub_kw_enable_val: {sub_kw_enable_val}\n")
                    f.write(f"  sub_kw_text_val: {sub_kw_text_val}\n")
                
                # 杈呭姪鍑芥暟锛氫粠 Gradio Audio 缁勪欢鍊间腑鎻愬彇鏂囦欢璺緞
                def extract_audio_path(val):
                    """
                    Gradio Audio 缁勪欢鍙兘杩斿洖锛?
                    1. 瀛楃涓茶矾寰?
                    2. 鍏冪粍 (sample_rate, numpy_array) - 杩欑鎯呭喌鏃犳硶鎭㈠鍘熷璺緞
                    3. 瀛楀吀 {'name': 'path', ...}
                    """
                    if val is None:
                        return ""
                    if isinstance(val, str):
                        return val.strip()
                    if isinstance(val, dict) and 'name' in val:
                        return val['name'].strip() if isinstance(val['name'], str) else str(val['name']).strip()
                    # 濡傛灉鏄厓缁?(sample_rate, array)锛岃鏄庨煶棰戣鍔犺浇鍒板唴瀛樹簡
                    # 杩欑鎯呭喌鎴戜滑鏃犳硶鑾峰彇鍘熷鏂囦欢璺緞锛屽彧鑳借繑鍥炵┖
                    if isinstance(val, tuple):
                        with open(debug_file, "a", encoding="utf-8") as f:
                            f.write(f"  [WARNING] Audio 缁勪欢杩斿洖浜嗗厓缁勬牸寮忥紝鏃犳硶鑾峰彇鏂囦欢璺緞\n")
                        return ""
                    return ""
                
                # 杈呭姪鍑芥暟锛氬皢浠讳綍鍊艰浆鎹负JSON鍙簭鍒楀寲鐨勭被鍨?
                def to_json_safe(val):
                    """灏嗗€艰浆鎹负JSON鍙簭鍒楀寲鐨勭被鍨?""
                    if val is None:
                        return ""
                    # 澶勭悊 numpy 鏁扮粍
                    if hasattr(val, 'tolist'):
                        return val.tolist()
                    # 澶勭悊瀛楃涓诧紙鍘婚櫎涓ょ绌烘牸锛?
                    if isinstance(val, str):
                        return val.strip()
                    # 澶勭悊鍏朵粬鍩烘湰绫诲瀷
                    if isinstance(val, (int, float, bool)):
                        return val
                    # 灏濊瘯杞崲涓哄瓧绗︿覆
                    return str(val).strip()
                
                # 鐢熸垚璁板綍鍚嶇О锛氫娇鐢ㄦ枃鏈墠10涓瓧锛屽鏋滄病鏈夊垯浣跨敤鏃堕棿
                text = (input_text or "").strip()
                if text:
                    record_name = text[:10]
                else:
                    record_name = time.strftime("%H:%M:%S")
                
                # 鎻愬彇闊抽璺緞锛堝鐞?Gradio Audio 缁勪欢鐨勪笉鍚岃繑鍥炴牸寮忥級
                output_audio_path = extract_audio_path(output_audio_val)
                audio_for_ls_path = extract_audio_path(audio_for_ls_val)
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  鎻愬彇鐨勮矾寰?\n")
                    f.write(f"    output_audio_path: {output_audio_path}\n")
                    f.write(f"    audio_for_ls_path: {audio_for_ls_path}\n")
                
                record = {
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "record_name": record_name,
                    "input_text": to_json_safe(input_text),
                    "prompt_audio": to_json_safe(prompt_audio),
                    "voice_select": to_json_safe(voice_select_val),
                    "audio_mode": to_json_safe(audio_mode_val) or "鏂囧瓧杞闊?,
                    "direct_audio": to_json_safe(direct_audio),
                    "avatar_select": to_json_safe(avatar_select_val),
                    "audio_for_ls": audio_for_ls_path,  # 浣跨敤 audio_for_ls 鐨勮矾寰?
                    "output_audio": output_audio_path,  # 浣跨敤 output_audio 鐨勮矾寰?
                    "output_video": to_json_safe(output_video_val),
                    "sub_text": to_json_safe(sub_text_val),
                    "sub_video": to_json_safe(sub_video_val),
                    # 瀛楀箷鍙傛暟
                    "sub_font": to_json_safe(sub_font_val),
                    "sub_size": to_json_safe(sub_size_val) or 38,
                    "sub_pos": to_json_safe(sub_pos_val) or "涓?,
                    "sub_pos_offset": to_json_safe(sub_pos_offset_val) or 0,
                    "sub_color": to_json_safe(sub_color_val) or "#FFFFFF",
                    "sub_hi_color": to_json_safe(sub_hi_val) or "#FFD700",
                    "sub_outline_color": to_json_safe(sub_outline_val) or "#000000",
                    "sub_outline_size": to_json_safe(sub_outline_size_val) or 6,
                    "sub_bg_color": to_json_safe(sub_bg_color_val) or "#000000",
                    "sub_bg_opacity": to_json_safe(sub_bg_opacity_val) or 0,
                    "sub_kw_enable": bool(sub_kw_enable_val) if sub_kw_enable_val is not None else False,
                    "sub_hi_scale": to_json_safe(sub_hi_scale_val) or 1.5,
                    "sub_kw_text": to_json_safe(sub_kw_text_val),
                    # 瀛楀箷鏍囬
                    "sub_title_text": to_json_safe(sub_title_text_val),
                    "sub_title_text2": to_json_safe(sub_title_text2_val),
                    # 鐗囧ご鍙傛暟
                    "intro_enable": bool(intro_enable_val) if intro_enable_val is not None else False,
                    # 鍙戝竷鍙傛暟
                    "douyin_title": to_json_safe(douyin_title_val),
                    "douyin_topics": to_json_safe(douyin_topics_val),
                    # 鐢讳腑鐢诲弬鏁?
                    "pip_enable": bool(pip_enable_val) if pip_enable_val is not None else False,
                    "pip_mode": to_json_safe(pip_mode_val) if pip_mode_val is not None else "馃寪 鍦ㄧ嚎鐢熸垚",
                    "pip_prompt": to_json_safe(pip_prompt_val) if pip_prompt_val is not None else "",
                    "pip_interval": to_json_safe(pip_interval_val) if pip_interval_val is not None else 15.0,
                    "pip_clip_dur": to_json_safe(pip_clip_dur_val) if pip_clip_dur_val is not None else 5.0,
                }
                
                # 璇诲彇鐜版湁璁板綍
                records = _load_workspace_records()
                
                # 鏌ユ壘鏄惁鏈夌浉鍚屾枃鏈殑璁板綍锛堝彧姣旇緝鏂囨湰鍐呭锛?
                # 濡傛灉鎻愪緵浜?search_key锛岀敤 search_key 鏌ユ壘锛圓I鏀瑰啓鍦烘櫙锛氭寜鍘熸枃鏌ユ壘锛?
                match_text = (search_key or "").strip() if search_key is not None else text
                existing_idx = -1
                for i, rec in enumerate(records):
                    if rec.get("input_text", "").strip() == match_text:
                        existing_idx = i
                        break
                
                # 濡傛灉 input_text 涓虹┖涓旀病鏈夋壘鍒板尮閰嶈褰曪紝灏濊瘯鏇存柊鏈€杩戜竴鏉¤褰?
                # 锛堢敤鎴峰湪鏈緭鍏ユ枃妗堢殑鎯呭喌涓嬬紪杈戞爣棰?璇濋锛屽簲鏇存柊鏈€鏂拌褰曡€岄潪鏂板缓锛?
                if existing_idx < 0 and not text and records:
                    # 妫€鏌ユ渶杩戜竴鏉¤褰曠殑 input_text 鏄惁涔熶负绌?
                    if not records[0].get("input_text", "").strip():
                        existing_idx = 0
                
                if existing_idx >= 0:
                    # 鏇存柊鐜版湁璁板綍 - 鐢讳腑鐢诲弬鏁颁负绌烘椂淇濈暀鏃у€?
                    old_record = records[existing_idx]
                    if pip_enable_val is None and old_record.get("pip_enable") is not None:
                        record["pip_enable"] = old_record["pip_enable"]
                    if pip_mode_val is None and old_record.get("pip_mode"):
                        record["pip_mode"] = old_record["pip_mode"]
                    if pip_prompt_val is None and old_record.get("pip_prompt"):
                        record["pip_prompt"] = old_record["pip_prompt"]
                    if pip_interval_val is None and old_record.get("pip_interval") is not None:
                        record["pip_interval"] = old_record["pip_interval"]
                    if pip_clip_dur_val is None and old_record.get("pip_clip_dur") is not None:
                        record["pip_clip_dur"] = old_record["pip_clip_dur"]
                    records[existing_idx] = record
                    msg = f"宸叉洿鏂帮細{record_name}"
                else:
                    # 鏂板缓璁板綍
                    records.insert(0, record)
                    records = records[:100]  # 鏈€澶氫繚鐣?00鏉?
                    msg = f"宸蹭繚瀛橈細{record_name}"
                
                # 淇濆瓨鍒版枃浠?
                with open(WORKSPACE_RECORDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                
                return _hint_html("ok", msg), gr.update(choices=_get_workspace_record_choices())
            except Exception as e:
                import traceback
                traceback.print_exc()
                return _hint_html("error", f"淇濆瓨澶辫触: {str(e)}"), gr.update()

        def _restore_workspace(record_idx_str):
            """鎭㈠閫変腑鐨勫伐浣滃彴璁板綍"""
            try:
                if not record_idx_str:
                    # 鏈€夋嫨璁板綍,鍙洿鏂版彁绀?鍏朵粬缁勪欢涓嶅姩
                    return [gr.update()] * 34 + [_hint_html("warning", "璇峰厛閫夋嫨涓€鏉¤褰?)]

                try:
                    record_idx = int(record_idx_str)
                except (ValueError, TypeError):
                    return [gr.update()] * 34 + [_hint_html("error", "鏃犳晥鐨勮褰曠储寮?)]

                records = _load_workspace_records()

                if record_idx < 0 or record_idx >= len(records):
                    return [gr.update()] * 34 + [_hint_html("error", "璁板綍涓嶅瓨鍦?)]
                
                rec = records[record_idx]
                
                # 寮哄埗杈撳嚭鍒版枃浠朵互渚胯皟璇?
                debug_file = os.path.join(OUTPUT_DIR, "debug_restore.txt")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] _restore_workspace 琚皟鐢╘n")
                    f.write(f"  output_audio: {rec.get('output_audio', '')}\n")
                    f.write(f"  audio_for_ls: {rec.get('audio_for_ls', '')}\n")
                    f.write(f"  sub_text: {rec.get('sub_text', '')}\n")
                
                # 杈呭姪鍑芥暟锛氬畨鍏ㄨ幏鍙栨枃浠惰矾寰勫€?
                def safe_file_value(path):
                    """鍙湁褰撹矾寰勫瓨鍦ㄤ笖鏄枃浠舵椂鎵嶈繑鍥烇紝鍚﹀垯杩斿洖 None"""
                    if not path or not isinstance(path, str):
                        return None
                    path = path.strip()
                    if not path:
                        return None
                    # 妫€鏌ユ枃浠舵槸鍚﹀瓨鍦?
                    exists = os.path.exists(path) and os.path.isfile(path)
                    with open(debug_file, "a", encoding="utf-8") as f:
                        f.write(f"  safe_file_value: {path} -> exists={exists}\n")
                    if exists:
                        return path
                    return None
                
                # 杈呭姪鍑芥暟锛氬畨鍏ㄨ幏鍙栦笅鎷夋閫夋嫨鍊?
                def safe_dropdown_value(value, choices_func):
                    """妫€鏌ュ€兼槸鍚﹀湪閫夐」鍒楄〃涓紝濡傛灉涓嶅湪鍒欒繑鍥?None"""
                    if not value:
                        return None
                    try:
                        choices = choices_func() if callable(choices_func) else []
                        if value in choices:
                            return value
                        else:
                            # 濡傛灉鍊间笉鍦ㄥ垪琛ㄤ腑锛岃褰曟棩蹇椾絾杩斿洖None锛堜笉鎶ラ敊锛?
                            with open(debug_file, "a", encoding="utf-8") as f:
                                f.write(f"  璀﹀憡: 闊宠壊 '{value}' 涓嶅湪褰撳墠鍒楄〃涓紝鍙兘鏄疶TS妯″紡涓嶅尮閰峔n")
                            return None
                    except Exception as e:
                        with open(debug_file, "a", encoding="utf-8") as f:
                            f.write(f"  safe_dropdown_value 寮傚父: {e}\n")
                        return None
                
                # 鑾峰彇闊抽鏂囦欢璺緞锛堝嵆浣挎枃浠朵笉瀛樺湪涔熸仮澶嶈矾寰勶紝璁╃敤鎴风煡閬撲箣鍓嶇殑鏂囦欢锛?
                output_audio_path = rec.get("output_audio", "")
                audio_for_ls_path = rec.get("audio_for_ls", "")
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  浠庤褰曡鍙栫殑璺緞:\n")
                    f.write(f"    output_audio_path: {output_audio_path}\n")
                    f.write(f"    audio_for_ls_path: {audio_for_ls_path}\n")
                
                # 濡傛灉 output_audio 瀛樺湪锛屼紭鍏堜娇鐢ㄥ畠
                # 濡傛灉涓嶅瓨鍦ㄤ絾鏈夎矾寰勮褰曪紝涔熸樉绀鸿矾寰勶紙铏界劧鏂囦欢鍙兘宸茶鍒犻櫎锛?
                output_audio_value = safe_file_value(output_audio_path)
                if not output_audio_value and output_audio_path:
                    # 鏂囦欢涓嶅瓨鍦ㄤ絾鏈夎矾寰勮褰曪紝浠嶇劧灏濊瘯鎭㈠锛圙radio浼氭樉绀洪敊璇絾淇濈暀璺緞锛?
                    output_audio_value = output_audio_path
                
                audio_for_ls_value = safe_file_value(audio_for_ls_path)
                if not audio_for_ls_value and audio_for_ls_path:
                    audio_for_ls_value = audio_for_ls_path
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  鏈€缁堟仮澶嶇殑鍊?\n")
                    f.write(f"    output_audio_value: {output_audio_value}\n")
                    f.write(f"    audio_for_ls_value: {audio_for_ls_value}\n")
                    f.write(f"    sub_text: {rec.get('sub_text', '')}\n")
                    f.write(f"    sub_title_text: {rec.get('sub_title_text', '')}\n")
                    f.write(f"    sub_kw_enable: {rec.get('sub_kw_enable', False)}\n")
                    f.write(f"    sub_kw_text: {rec.get('sub_kw_text', '')}\n")
                
                # 鑾峰彇瀛楀箷瑙嗛璺緞
                sub_video_path = rec.get("sub_video", "")
                if sub_video_path and os.path.exists(sub_video_path):
                    sub_video_update = gr.update(value=sub_video_path, visible=True, show_download_button=True)
                else:
                    sub_video_update = gr.update(visible=False)
                
                # 杩斿洖鎵€鏈夐渶瑕佹洿鏂扮殑缁勪欢鍊?
                # 鑾峰彇褰撳墠TTS妯″紡锛岀敤浜庤繃婊ら煶鑹插垪琛?
                current_tts_mode = os.getenv('TTS_MODE', 'local')
                
                result = [
                    gr.update(value=rec.get("input_text", "")),           # input_text
                    gr.update(value=safe_file_value(rec.get("prompt_audio"))),  # prompt_audio
                    gr.update(value=safe_dropdown_value(rec.get("voice_select"), lambda: _vc.get_choices(current_tts_mode) if _LIBS_OK else [])),  # voice_select - 浣跨敤褰撳墠妯″紡杩囨护
                    gr.update(value=rec.get("audio_mode", "鏂囧瓧杞闊?)), # audio_mode
                    gr.update(value=safe_file_value(rec.get("direct_audio"))),  # direct_audio
                    gr.update(value=safe_dropdown_value(rec.get("avatar_select"), lambda: _av.get_choices() if _LIBS_OK else [])),  # avatar_select
                    gr.update(value=audio_for_ls_value) if audio_for_ls_value else gr.update(),  # audio_for_ls
                    gr.update(value=output_audio_value) if output_audio_value else gr.update(),  # output_audio
                    gr.update(value=safe_file_value(rec.get("output_video"))),  # output_video
                    gr.update(value=rec.get("sub_text", "")),             # sub_text - 鐩存帴鎭㈠鏂囨湰
                    sub_video_update,                                      # sub_video - 甯?visible 鎺у埗
                    # 瀛楀箷鍙傛暟
                    gr.update(value=rec.get("sub_font", "")),             # sub_font
                    gr.update(value=rec.get("sub_size", 38)),             # sub_size
                    gr.update(value=rec.get("sub_pos", "涓?)),            # sub_pos
                    gr.update(value=rec.get("sub_pos_offset", 0)),        # sub_pos_offset
                    gr.update(value=rec.get("sub_color", "#FFFFFF")),     # sub_color_txt
                    gr.update(value=rec.get("sub_hi_color", "#FFD700")),  # sub_hi_txt
                    gr.update(value=rec.get("sub_outline_color", "#000000")), # sub_outline_txt
                    gr.update(value=rec.get("sub_outline_size", 6)),      # sub_outline_size
                    gr.update(value=rec.get("sub_bg_color", "#000000")),  # sub_bg_color
                    gr.update(value=rec.get("sub_bg_opacity", 0)),        # sub_bg_opacity
                    gr.update(value=rec.get("sub_kw_enable", False)),     # sub_kw_enable
                    gr.update(value=rec.get("sub_hi_scale", 1.5)),        # sub_hi_scale
                    gr.update(value=rec.get("sub_kw_text", "")),          # sub_kw_text
                    # 瀛楀箷鏍囬
                    gr.update(value=rec.get("sub_title_text", "")),        # sub_title_text
                    gr.update(value=rec.get("sub_title_text2", "")),       # sub_title_text2
                    # 鍙戝竷鍙傛暟
                    gr.update(value=rec.get("douyin_title", "")),           # douyin_title
                    gr.update(value=rec.get("douyin_topics", "")),          # douyin_topics
                    # 鐢讳腑鐢诲弬鏁?
                    gr.update(value=rec.get("pip_enable", False)),          # pip_enable
                    gr.update(value=rec.get("pip_mode", "馃寪 鍦ㄧ嚎鐢熸垚")),     # pip_mode
                    gr.update(value=rec.get("pip_prompt", "")),             # pip_prompt
                    gr.update(value=rec.get("pip_interval", 15.0)),         # pip_interval
                    gr.update(value=rec.get("pip_clip_dur", 5.0)),          # pip_clip_dur
                    _hint_html("ok", f"宸叉仮澶嶈褰曪細{rec.get('record_name', rec.get('time', '鏈煡'))}")
                ]
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  杩斿洖鐨?audio_for_ls 鏇存柊: {result[6]}\n")
                
                return result
            except Exception as e:
                return [gr.update()] * 34 + [_hint_html("error", f"鎭㈠澶辫触: {str(e)}")]

        # TTS 鈥?鍚庡彴绾跨▼鎵ц锛屾祦寮忚繑鍥炶繘搴︼紝UI 涓嶅崱
        def tts_wrap(text, pa, voice_name, spd, tp, tk, temp, nb, rp, mmt,
                     emo_m, emo_a, emo_w, emo_t,
                     v1, v2, v3, v4, v5, v6, v7, v8,
                     progress=gr.Progress()):
            # 鍙傛暟楠岃瘉
            if not text or not text.strip():
                raise gr.Error("璇峰湪鏂囨鍐呭涓緭鍏ユ枃鏈?)
            
            # 鍦ㄧ嚎/鏈湴浠ュ綋鍓?TTS_MODE 涓哄噯
            tts_mode = os.getenv('TTS_MODE', 'local')
            is_online = (tts_mode == 'online')

            # 鍦ㄧ嚎鐗堜笉闇€瑕?prompt_audio锛屾湰鍦扮増闇€瑕?
            if not is_online and pa is None:
                raise gr.Error("璇峰厛閫夋嫨闊宠壊鎴栦笂浼犲弬鑰冮煶棰?)
            
            try:
                progress(0.05, desc="姝ｅ湪鍚堟垚璇煶...")
                
                r = generate_speech(text, pa, voice_name, tp, tk, temp, nb, rp, mmt,
                                    emo_m, emo_a, emo_w, emo_t,
                                    v1, v2, v3, v4, v5, v6, v7, v8,
                                    progress=progress)
                out_path = r[0]
                
                # 璇€熻皟鏁达紙ffmpeg atempo锛?
                speed = float(spd or 1.0)
                if abs(speed - 1.0) > 0.02 and out_path and os.path.exists(out_path):
                    progress(0.92, desc="璋冩暣璇€?..")
                    try:
                        tmp_path = out_path + ".speed.wav"
                        # atempo 鑼冨洿 0.5~2.0, 閾惧紡澶勭悊瓒呭嚭鑼冨洿
                        atempo_val = max(0.5, min(2.0, speed))
                        ffmpeg_bin = _resolve_ffmpeg_exe()
                        cmd = [ffmpeg_bin, "-y", "-i", out_path,
                               "-filter:a", f"atempo={atempo_val}", tmp_path]
                        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                        subprocess.run(cmd, capture_output=True, text=True,
                                       encoding="utf-8", errors="replace",
                                       creationflags=flags)
                        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100:
                            os.replace(tmp_path, out_path)
                    except Exception as e:
                        print(f"[TTS] speed adjust fail: {e}")
                
                progress(1.0, desc="瀹屾垚")
                
                # Windows Toast
                try:
                    ps = (
                        "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
                        "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom,ContentType=WindowsRuntime]|Out-Null;"
                        "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(2);"
                        "$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('缁囨ⅵAI 鈥?璇煶鍚堟垚瀹屾垚'))|Out-Null;"
                        "$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('闊抽宸茬敓鎴愶紝鍙互杩涜瑙嗛鍚堟垚銆?))|Out-Null;"
                        "$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
                        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('缁囨ⅵAI').Show($n);"
                    )
                    subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                                     creationflags=subprocess.CREATE_NO_WINDOW,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
                return out_path, out_path
            except gr.Error:
                raise
            except Exception as e:
                raise gr.Error("鍚堟垚澶辫触: " + str(e))

        # TTS 鎸夐挳鐐瑰嚮 - 鐩存帴鍦ㄥ畬鎴愬悗淇濆瓨
        def tts_and_save(text, pa, voice_sel, spd, tp, tk, temp, nb, rp, mmt,
                        emo_m, emo_a, emo_w, emo_t,
                        v1, v2, v3, v4, v5, v6, v7, v8,
                        # 淇濆瓨闇€瑕佺殑鍏朵粬鍙傛暟
                        audio_mode_val, direct_aud, avatar_sel,
                        out_vid, sub_vid,
                        sub_font_val, sub_size_val, sub_pos_val, sub_pos_offset_val,
                        sub_color_val, sub_hi_val, sub_outline_val, sub_outline_size_val,
                        sub_bg_color_val, sub_bg_opacity_val,
                        sub_kw_enable_val, sub_hi_scale_val, sub_kw_text_val,
                        sub_title_text_val, sub_title_text2_val,
                        douyin_title_val, douyin_topics_val,
                        progress=gr.Progress()):
            """鍚堟垚骞惰嚜鍔ㄤ繚瀛樺伐浣滃彴鐘舵€?""
            # 鍏堟墽琛孴TS锛寁oice_sel 鍦ㄧ涓変釜浣嶇疆
            audio_path, audio_for_ls_path = tts_wrap(
                text, pa, voice_sel, spd, tp, tk, temp, nb, rp, mmt,
                emo_m, emo_a, emo_w, emo_t,
                v1, v2, v3, v4, v5, v6, v7, v8,
                progress=progress
            )
            
            # 鍚屾鏂囨湰鍒板瓧骞?
            sub_text_val = text
            
            # 淇濆瓨宸ヤ綔鍙扮姸鎬?
            hint_msg, dropdown_update = _auto_save_workspace(
                text, pa, voice_sel, audio_mode_val, direct_aud, avatar_sel,
                audio_for_ls_path, audio_path, out_vid,
                sub_text_val, sub_vid,
                sub_font_val, sub_size_val, sub_pos_val, sub_pos_offset_val,
                sub_color_val, sub_hi_val, sub_outline_val, sub_outline_size_val,
                sub_bg_color_val, sub_bg_opacity_val,
                sub_kw_enable_val, sub_hi_scale_val, sub_kw_text_val,
                douyin_title_val=douyin_title_val, douyin_topics_val=douyin_topics_val,
                sub_title_text_val=sub_title_text_val,
                sub_title_text2_val=sub_title_text2_val
            )
            
            # 杩斿洖鎵€鏈夐渶瑕佹洿鏂扮殑缁勪欢
            debug_file = os.path.join(OUTPUT_DIR, "debug_tts.txt")
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] tts_and_save 杩斿洖鍊?\n")
                f.write(f"  audio_path (output_audio): {audio_path}\n")
                f.write(f"  audio_for_ls_path: {audio_for_ls_path}\n")
                f.write(f"  sub_text_val: {sub_text_val}\n")
            
            return audio_path, audio_for_ls_path, sub_text_val, hint_msg, dropdown_update
        
        gen_btn.click(
            tts_and_save,
            inputs=[
                input_text, prompt_audio, voice_select, voice_speed, top_p, top_k, temperature,
                num_beams, repetition_penalty, max_mel_tokens,
                emo_mode, emo_audio, emo_weight, emo_text,
                vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                # 淇濆瓨闇€瑕佺殑鍙傛暟
                audio_mode, direct_audio_upload, avatar_select,
                output_video, sub_video,
                sub_font, sub_size, sub_pos, sub_pos_offset,
                sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                sub_bg_color, sub_bg_opacity,
                sub_kw_enable, sub_hi_scale, sub_kw_text,
                sub_title_text, sub_title_text2,
                douyin_title, douyin_topics
            ],
            outputs=[output_audio, audio_for_ls, sub_text,
                    workspace_record_hint, workspace_record_dropdown])

        # 鈹€鈹€ 闊抽妯″紡鍒囨崲 鈹€鈹€
        def _toggle_audio_mode(mode):
            return (
                gr.update(visible=(mode == "鏂囧瓧杞闊?)),
                gr.update(visible=(mode == "鐩存帴涓婁紶闊抽")),
            )
        audio_mode.change(_toggle_audio_mode,
            inputs=[audio_mode],
            outputs=[tts_mode_group, upload_mode_group])

        # 鈹€鈹€ 鐢讳腑鐢诲閫夋鍒囨崲 鈹€鈹€
        pip_enable.change(
            lambda v: gr.update(visible=v),
            inputs=[pip_enable],
            outputs=[pip_settings_group])

        # 鈹€鈹€ 鐢讳腑鐢绘ā寮忓垏鎹紙鍦ㄧ嚎/鏈湴锛夆攢鈹€
        def _pip_mode_switch(mode_val):
            is_online = ("鍦ㄧ嚎" in str(mode_val))
            return gr.update(visible=is_online), gr.update(visible=not is_online)
        pip_mode.change(
            _pip_mode_switch,
            inputs=[pip_mode],
            outputs=[pip_online_group, pip_local_group])

        # 鈹€鈹€ 鐢讳腑鐢荤敓鎴愭寜閽?鈹€鈹€
        def generate_pip_video(current_video, pip_mode_val, pip_prompt_val,
                               pip_local_val, pip_interval_val, pip_clip_dur_val,
                               progress=gr.Progress()):
            """鐢讳腑鐢昏棰戠敓鎴愶細鍦ㄧ嚎妯″紡閫氳繃 WebSocket chatglm_video 鐢熸垚锛屾湰鍦版ā寮忕敤鐢ㄦ埛涓婁紶鐨勭礌鏉?""
            if not current_video:
                return gr.update(), _hint_html("error", "璇峰厛鍦ㄦ楠?鐢熸垚瑙嗛")
            if not os.path.exists(str(current_video)):
                return gr.update(), _hint_html("error", "瑙嗛鏂囦欢涓嶅瓨鍦紝璇烽噸鏂扮敓鎴?)

            is_online = ("鍦ㄧ嚎" in str(pip_mode_val))

            try:
                if is_online:
                    if not pip_prompt_val or not pip_prompt_val.strip():
                        return gr.update(), _hint_html("warning", "璇疯緭鍏ョ敾涓敾鎻愮ず璇嶏紙鎴栫偣鍑汇€孉I鏀瑰啓+鏍囬鏍囩銆嶈嚜鍔ㄧ敓鎴愶級")
                    progress(0.02, desc="馃幀 鍦ㄧ嚎鐢熸垚鐢讳腑鐢?..")
                    # 鎸夋崲琛屾媶鍒嗕负澶氫釜鎻愮ず璇?
                    prompts_list = [_pip_force_chinese_person(p.strip()) for p in pip_prompt_val.strip().split('\n') if p.strip()]
                    if not prompts_list:
                        prompts_list = [_pip_force_chinese_person(pip_prompt_val.strip())]

                    # 浣跨敤 TextExtractor 杩炴帴鐢熸垚鐢讳腑鐢?
                    extractor = get_text_extractor()
                    if len(prompts_list) == 1:
                        # 鍗曚釜鎻愮ず璇?- 鏆備笉鏀寔鍚堟垚锛屽彧鐢熸垚
                        pip_result = _pip_ws.generate_pip_via_extractor(
                            prompts_list[0],
                            extractor,
                            progress_cb=lambda pct, msg: progress(pct, desc=f"馃柤 {msg}")
                        )
                    else:
                        # 澶氫釜鎻愮ず璇嶏紝鎵归噺鐢熸垚骞跺悎鎴?
                        pip_result = _pip_ws.generate_and_compose_pips(
                            str(current_video),
                            prompts_list,
                            extractor,
                            clip_duration=5.0,
                            progress_cb=lambda pct, msg: progress(pct, desc=f"馃柤 {msg}")
                        )
                else:
                    # 鏈湴涓婁紶妯″紡
                    if not pip_local_val:
                        return gr.update(), _hint_html("warning", "璇蜂笂浼犵敾涓敾瑙嗛绱犳潗")
                    # Gradio File 缁勪欢杩斿洖鐨勬槸 NamedString / tempfile 璺緞鍒楄〃
                    local_paths = []
                    if isinstance(pip_local_val, list):
                        for f in pip_local_val:
                            p = f.name if hasattr(f, 'name') else str(f)
                            if p and os.path.exists(p):
                                local_paths.append(p)
                    elif hasattr(pip_local_val, 'name'):
                        local_paths.append(pip_local_val.name)
                    elif isinstance(pip_local_val, str) and os.path.exists(pip_local_val):
                        local_paths.append(pip_local_val)

                    if not local_paths:
                        return gr.update(), _hint_html("warning", "涓婁紶鐨勬枃浠舵棤鏁堬紝璇烽噸鏂伴€夋嫨")

                    progress(0.05, desc="馃柤 鏈湴鐢讳腑鐢诲鐞?..")
                    pip_result = _pip.apply_pip_local(
                        str(current_video),
                        local_paths,
                        interval=float(pip_interval_val),
                        clip_duration=float(pip_clip_dur_val),
                        progress_cb=lambda pct, msg: progress(pct, desc=f"馃柤 {msg}")
                    )

                if pip_result and os.path.exists(pip_result):
                    safe_print(f"[PIP] 鐢讳腑鐢诲鐞嗗畬鎴? {pip_result}")
                    progress(1.0, desc="鉁?鐢讳腑鐢荤敓鎴愬畬鎴?)
                    return pip_result, _hint_html("ok", "鐢讳腑鐢昏棰戠敓鎴愬畬鎴?)
                else:
                    return gr.update(), _hint_html("error", "鐢讳腑鐢诲鐞嗗け璐ワ紝璇锋煡鐪嬫帶鍒跺彴鏃ュ織")

            except Exception as e:
                safe_print(f"[PIP] 鐢讳腑鐢诲鐞嗗け璐? {e}")
                traceback.print_exc()
                return gr.update(), _hint_html("error", f"鐢讳腑鐢荤敓鎴愬け璐? {str(e)}")

        pip_btn.click(
            generate_pip_video,
            inputs=[output_video, pip_mode, pip_prompt, pip_local_files,
                    pip_interval, pip_clip_dur],
            outputs=[output_video, pip_hint])

        # 鈹€鈹€ AI浼樺寲瀛楀箷鍑芥暟锛堟牴鎹槸鍚﹀凡AI鏀瑰啓锛屾墽琛屼笉鍚屼紭鍖栬寖鍥达級鈹€鈹€
        def _optimize_subtitle_with_deepseek(video_text, already_optimized=False):
            """
            浣跨敤DeepSeek AI浼樺寲瀛楀箷銆?
            - 濡傛灉鏈紭鍖栬繃(already_optimized=False)锛氬叧閿瘝+瀛楀箷鏍囬+瑙嗛鏍囬+璇濋+鐢讳腑鐢绘彁绀鸿瘝
            - 濡傛灉宸蹭紭鍖栬繃(already_optimized=True)锛氬彧浼樺寲鍏抽敭璇?瀛楀箷鏍囬
            """

            def _two_line_title(t: str) -> str:
                s = (t or "").strip()
                if not s:
                    return ""
                # 甯歌鍒嗛殧绗︼細| / 锝?鎹㈣
                for sep in ("\n", "锝?, "|", "/"):
                    if sep in s:
                        parts = [p.strip() for p in s.split(sep) if p.strip()]
                        if parts:
                            s1 = parts[0][:10]
                            s2 = (parts[1] if len(parts) > 1 else "")[:10]
                            if not s2 and len(parts) > 2:
                                s2 = parts[2][:10]
                            if not s2 and len(s1) < len(parts[0]):
                                # parts[0] 澶暱琚埅鏂紝缁欑浜岃琛ラ綈
                                s2 = parts[0][10:20]
                            if not s2 and len(s) > 10:
                                s2 = s[10:20]
                            return (s1 + "\n" + s2).strip()
                # 鏃犲垎闅旂锛氭寜闀垮害纭垏涓よ
                s1 = s[:10]
                s2 = s[10:20]
                return (s1 + ("\n" + s2 if s2 else "")).strip()
            if not video_text or not video_text.strip():
                if not already_optimized:
                    return "", "", "", "", "", False, _hint_html("warning", "璇峰厛杈撳叆瑙嗛鏂囨湰鍐呭")
                else:
                    return "", "", False, _hint_html("warning", "璇峰厛杈撳叆瑙嗛鏂囨湰鍐呭")
            
            if not already_optimized:
                # 鍏ㄩ噺浼樺寲锛氬叧閿瘝+瀛楀箷鏍囬+瑙嗛鏍囬+璇濋+澶氫釜鐢讳腑鐢绘彁绀鸿瘝
                prompt = f"""璇锋牴鎹互涓嬭棰戞枃鏈唴瀹癸紝瀹屾垚浜斾釜浠诲姟锛?

浠诲姟涓€锛氱敓鎴愪袱琛屽瓧骞曟爣棰橈紙姣忚8-10涓瓧锛屽敖閲忔帴杩?0涓瓧锛夈€傛爣棰樿鍙ｈ鍖栥€佹湁鍐插嚮鍔涖€侀€傚悎鐭棰戝皝闈€?
        杈撳嚭鏃惰鐢?锝?鍒嗛殧涓よ锛屼緥濡傦細绗竴琛岋綔绗簩琛岋紙姣忚8-10瀛楋級銆?
浠诲姟浜岋細浠庢枃鏈腑鎻愬彇灏藉彲鑳藉鐨勫叧閿瘝锛堢敤浜庡瓧骞曢珮浜樉绀猴級锛屽寘鎷牳蹇冨悕璇嶃€佸姩璇嶃€佸舰瀹硅瘝绛夐噸瑕佽瘝璇紝涓嶉檺鏁伴噺锛岀敤閫楀彿鍒嗛殧
浠诲姟涓夛細鐢熸垚涓€涓惛寮曚汉鐨勭煭瑙嗛鏍囬锛堜笉瓒呰繃30瀛楋紝鍚稿紩鐪肩悆銆佸紩鍙戝ソ濂囷級
浠诲姟鍥涳細鐢熸垚5涓浉鍏崇殑鐑棬璇濋鏍囩锛岀敤閫楀彿鍒嗛殧
浠诲姟浜旓細涓虹敾涓敾瑙嗛鐢熸垚澶氫釜鎻愮ず璇嶃€傛瘡涓彁绀鸿瘝鎻忚堪涓€涓笉鍚岀殑鐪熷疄鍦烘櫙鐢婚潰锛岀敤浜嶢I鐢熸垚瀹炴櫙B-roll瑙嗛绱犳潗銆?
鐢熸垚1涓彁绀鸿瘝锛堜緥濡?0绉掓枃妗堢敓鎴?涓紝60绉掓枃妗堢敓鎴?涓紝90绉掓枃妗堢敓鎴?涓級銆傛瘡涓彁绀鸿瘝鎻忚堪涓€涓€傚悎鍙ｆ挱鎺ㄥ箍鐨勭湡瀹炲満鏅敾闈紝鐢ㄤ簬AI鐢熸垚瀹炴櫙B-roll瑙嗛绱犳潗銆?
瑕佹眰锛氭牴鎹枃妗堟湕璇绘椂闀夸及绠楋紙绾︽瘡绉?-4涓瓧锛夛紝鎸夋瘡30绉?涓彁绀鸿瘝鐨勮鍒欑敓鎴愬搴旀暟閲忋€傛瘡涓笉瓒呰繃80瀛椼€?
鍦烘櫙瑕佹眰锛氬疄鐗╁満鏅紝閫傚悎鐭棰戝彛鎾敾涓敾绱犳潗锛屼富瑕佺敤浜庡睍绀哄巶瀹躲€佸晢鍝併€佸伐浣滃満鏅垨鏈嶅姟鐜銆傜敾闈㈠共鍑€楂樼骇锛岀┖闂撮€氶€忥紝涓讳綋鏄庣‘锛屾瀯鍥剧畝娲侊紝鍏锋湁鐭棰態-roll璐ㄦ劅锛岀伅鍏夋煍鍜岋紝鐪熷疄缁嗚妭涓板瘜锛屾暣浣撻珮绾ф劅寮猴紝鐢熸椿鍖栦絾涓嶆潅涔憋紝瓒呮竻鍐欏疄椋庢牸銆傚満鏅繀椤讳笉鍚屻€?

瑙嗛鏂囨湰鍐呭锛?
{video_text[:500]}

璇蜂弗鏍兼寜鐓т互涓嬫牸寮忚緭鍑猴紝涓嶈娣诲姞鍏朵粬鍐呭锛?
瀛楀箷鏍囬锛歔浣犵殑瀛楀箷鏍囬]
鍏抽敭璇嶏細[鍏抽敭璇?,鍏抽敭璇?,鍏抽敭璇?,...]
瑙嗛鏍囬锛歔浣犵殑瑙嗛鏍囬]
璇濋锛歔璇濋1,璇濋2,璇濋3,璇濋4,璇濋5]
鎻愮ず璇?锛歔绗竴澶勭敾涓敾鍦烘櫙鎻忚堪]
鎻愮ず璇?锛歔绗簩澶勭敾涓敾鍦烘櫙鎻忚堪]
..."""
                
                result, error = _call_deepseek_api(prompt)
                if error:
                    return "", "", "", "", "", False, _hint_html("error", error)
                
                if result:
                    lines = result.strip().split('\n')
                    sub_title = ""
                    new_keywords = ""
                    video_title = ""
                    new_topics = ""
                    pip_prompts_list = []
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith("瀛楀箷鏍囬锛?) or line.startswith("瀛楀箷鏍囬:"):
                            sub_title = line.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                        elif line.startswith("鍏抽敭璇嶏細") or line.startswith("鍏抽敭璇?"):
                            new_keywords = line.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                        elif line.startswith("瑙嗛鏍囬锛?) or line.startswith("瑙嗛鏍囬:"):
                            video_title = line.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                        elif line.startswith("璇濋锛?) or line.startswith("璇濋:"):
                            new_topics = line.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                        elif re.match(r'鎻愮ず璇峔d*[锛?]', line):
                            pip_line = re.sub(r'^鎻愮ず璇峔d*[锛?]\s*', '', line).strip()
                            if pip_line:
                                pip_prompts_list.append(pip_line)
                    
                    kw_enable = bool(new_keywords.strip())
                    new_pip_prompt = "\n".join(pip_prompts_list) if pip_prompts_list else ""
                    pip_count = len(pip_prompts_list)
                    sub_title = _two_line_title(sub_title)
                    return sub_title, new_keywords, video_title, new_topics, new_pip_prompt, kw_enable, _hint_html("ok", f"AI浼樺寲瀹屾垚锛佸凡鐢熸垚瀛楀箷鏍囬銆佸叧閿瘝銆佽棰戞爣棰樸€佽瘽棰樺拰{pip_count}涓敾涓敾鎻愮ず璇?)
                else:
                    return "", "", "", "", "", False, _hint_html("error", "AI浼樺寲澶辫触锛屾湭杩斿洖鍐呭")
            else:
                # 绮剧畝浼樺寲锛氬彧浼樺寲鍏抽敭璇?瀛楀箷鏍囬
                prompt = f"""璇锋牴鎹互涓嬭棰戞枃鏈唴瀹癸紝瀹屾垚涓や釜浠诲姟锛?

浠诲姟涓€锛氱敓鎴愪袱琛屽瓧骞曟爣棰橈紙姣忚8-10涓瓧锛屽敖閲忔帴杩?0涓瓧锛夈€傝緭鍑虹敤"锝?鍒嗛殧涓よ锛屼緥濡傦細绗竴琛岋綔绗簩琛屻€?
浠诲姟浜岋細浠庢枃鏈腑鎻愬彇灏藉彲鑳藉鐨勫叧閿瘝锛堢敤浜庡瓧骞曢珮浜樉绀猴級锛屽寘鎷牳蹇冨悕璇嶃€佸姩璇嶃€佸舰瀹硅瘝绛夐噸瑕佽瘝璇紝涓嶉檺鏁伴噺锛岀敤閫楀彿鍒嗛殧

瑙嗛鏂囨湰鍐呭锛?
{video_text[:300]}

璇蜂弗鏍兼寜鐓т互涓嬫牸寮忚緭鍑猴紝涓嶈娣诲姞鍏朵粬鍐呭锛?
鏍囬锛歔浣犵殑鏍囬]
鍏抽敭璇嶏細[鍏抽敭璇?,鍏抽敭璇?,鍏抽敭璇?,...]"""
                
                result, error = _call_deepseek_api(prompt)
                if error:
                    return "", "", False, _hint_html("error", error)
                
                if result:
                    lines = result.strip().split('\n')
                    new_title = ""
                    new_keywords = ""
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith("鏍囬锛?) or line.startswith("鏍囬:"):
                            new_title = line.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                        elif line.startswith("鍏抽敭璇嶏細") or line.startswith("鍏抽敭璇?"):
                            new_keywords = line.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                    
                    kw_enable = bool(new_keywords.strip())
                    new_title = _two_line_title(new_title)
                    return new_title, new_keywords, kw_enable, _hint_html("ok", "AI浼樺寲瀹屾垚锛佸凡鐢熸垚瀛楀箷鏍囬鍜屽叧閿瘝")
                else:
                    return "", "", False, _hint_html("error", "AI浼樺寲澶辫触锛屾湭杩斿洖鍐呭")

        # 鈹€鈹€ 瀛楀箷楂樼骇璁剧疆寮圭獥 鈹€鈹€
        sub_settings_open_btn.click(
            lambda txt: (gr.update(visible=True), gr.update(value=txt or "")),
            inputs=[input_text],
            outputs=[sub_settings_modal, sub_text_modal])
        
        def _close_sub_settings_and_save(sub_text_modal_val,
                                         inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                                         avatar_sel, aud_for_ls, out_aud, out_vid,
                                         sub_vid,
                                         sub_fnt, sub_sz, sub_ps, sub_ps_off,
                                         sub_col, sub_hi, sub_out, sub_out_sz,
                                         sub_bg_col, sub_bg_op,
                                         sub_kw_en, sub_hi_sc, sub_kw_txt,
                                         sub_title_txt, sub_title_txt2,
                                         douyin_title_val, douyin_topics_val):
            """鍏抽棴楂樼骇璁剧疆寮圭獥骞朵繚瀛樺埌宸ヤ綔鍙?""
            try:
                save_hint, dropdown_update = _auto_save_workspace(
                    inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                    avatar_sel, aud_for_ls, out_aud, out_vid,
                    inp_txt, sub_vid,
                    sub_fnt, sub_sz, sub_ps, sub_ps_off,
                    sub_col, sub_hi, sub_out, sub_out_sz,
                    sub_bg_col, sub_bg_op,
                    sub_kw_en, sub_hi_sc, sub_kw_txt,
                    douyin_title_val=douyin_title_val, douyin_topics_val=douyin_topics_val,
                    sub_title_text_val=sub_title_txt,
                    sub_title_text2_val=sub_title_txt2
                )
            except Exception as e:
                save_hint = _hint_html("error", f"淇濆瓨澶辫触: {e}")
                dropdown_update = gr.update()
            return gr.update(visible=False), gr.update(value=inp_txt or ""), save_hint, dropdown_update
        
        sub_settings_close_btn.click(
            _close_sub_settings_and_save,
            inputs=[sub_text_modal,
                    input_text, prompt_audio, voice_select, audio_mode, direct_audio_upload,
                    avatar_select, audio_for_ls, output_audio, output_video,
                    sub_video,
                    sub_font, sub_size, sub_pos, sub_pos_offset,
                    sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                    sub_bg_color, sub_bg_opacity,
                    sub_kw_enable, sub_hi_scale, sub_kw_text,
                    sub_title_text, sub_title_text2,
                    douyin_title, douyin_topics],
            outputs=[sub_settings_modal, sub_text,
                    workspace_record_hint, workspace_record_dropdown])
        sub_settings_cancel_btn.click(
            lambda: gr.update(visible=False),
            outputs=[sub_settings_modal])
        
        # 鈹€鈹€ AI浼樺寲瀛楀箷鎸夐挳锛堟牴鎹槸鍚﹀凡AI鏀瑰啓锛屾墽琛屼笉鍚岃寖鍥翠紭鍖栵紝骞朵繚瀛樺埌宸ヤ綔鍙帮級鈹€鈹€
        def _split_title_lines(title_text):
            """灏嗘爣棰樺垎鎴愪袱琛岋紝姣忚鏈€澶?0涓瓧"""
            if not title_text or not title_text.strip():
                return "", ""

            # 鏀寔澶氱鍒嗛殧绗?
            title = title_text.strip()
            for sep in ("\n", "锝?, "|", "\\"):
                if sep in title:
                    parts = [p.strip() for p in title.split(sep) if p.strip()]
                    line1 = parts[0][:10] if parts else ""  # 闄愬埗绗竴琛屾渶澶?0瀛?
                    line2 = parts[1][:10] if len(parts) > 1 else ""  # 闄愬埗绗簩琛屾渶澶?0瀛?
                    return line1, line2

            # 濡傛灉娌℃湁鍒嗛殧绗︼紝涓旀爣棰樿秴杩?0涓瓧锛岃嚜鍔ㄥ垎鎴愪袱琛?
            if len(title) > 10:
                line1 = title[:10]
                line2 = title[10:20]  # 绗簩琛屼篃鏈€澶?0瀛?
                return line1, line2

            # 鏍囬涓嶈秴杩?0瀛楋紝杩斿洖绗竴琛岋紝绗簩琛屼负绌?
            return title, ""

        def _subtitle_ai_optimize_and_save(video_text, ai_rewrite_done_val,
                                           prmt_aud, voice_sel, audio_mode_val, direct_aud,
                                           avatar_sel, aud_for_ls, out_aud, out_vid,
                                           sub_txt, sub_vid,
                                           sub_fnt, sub_sz, sub_ps, sub_ps_off,
                                           sub_col, sub_hi, sub_out, sub_out_sz,
                                           sub_bg_col, sub_bg_op,
                                           sub_kw_en, sub_hi_sc, sub_kw_txt,
                                           douyin_title_val, douyin_topics_val):
            already_optimized = bool(ai_rewrite_done_val)

            if not already_optimized:
                # 鍏ㄩ噺浼樺寲锛氬瓧骞曟爣棰?鍏抽敭璇?瑙嗛鏍囬+璇濋+鐢讳腑鐢绘彁绀鸿瘝
                result = _optimize_subtitle_with_deepseek(video_text, already_optimized=False)
                # result: (sub_title, keywords, video_title, topics, pip_prompt, kw_enable, hint)
                if len(result) == 7:
                    sub_title, new_keywords, video_title, new_topics, new_pip_prompt, kw_enable, hint = result
                    # 灏嗘爣棰樺垎鎴愪袱琛?
                    title_line1, title_line2 = _split_title_lines(sub_title)
                else:
                    # 鍑洪敊鏃惰繑鍥炲皯閲忓€?
                    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), True, gr.update(), gr.update()
                try:
                    save_hint, dropdown_update = _auto_save_workspace(
                        video_text, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                        avatar_sel, aud_for_ls, out_aud, out_vid,
                        sub_txt, sub_vid,
                        sub_fnt, sub_sz, sub_ps, sub_ps_off,
                        sub_col, sub_hi, sub_out, sub_out_sz,
                        sub_bg_col, sub_bg_op,
                        kw_enable, sub_hi_sc, new_keywords,
                        douyin_title_val=video_title or douyin_title_val,
                        douyin_topics_val=new_topics or douyin_topics_val,
                        sub_title_text_val=title_line1,
                        sub_title_text2_val=title_line2,
                        pip_prompt_val=new_pip_prompt
                    )
                except Exception as e:
                    save_hint = _hint_html("error", f"淇濆瓨澶辫触: {e}")
                    dropdown_update = gr.update()
                # outputs: sub_title_text, sub_title_text2, sub_kw_text, sub_kw_enable, douyin_title, douyin_topics, pip_prompt, tts_hint, ai_rewrite_done, workspace_hint, workspace_dropdown
                return title_line1, title_line2, new_keywords, kw_enable, video_title, new_topics, new_pip_prompt, hint, True, save_hint, dropdown_update
            else:
                # 绮剧畝浼樺寲锛氬彧浼樺寲鍏抽敭璇?瀛楀箷鏍囬
                result = _optimize_subtitle_with_deepseek(video_text, already_optimized=True)
                # result: (title, keywords, kw_enable, hint)
                if len(result) == 4:
                    new_title, new_keywords, kw_enable, hint = result
                    # 灏嗘爣棰樺垎鎴愪袱琛?
                    title_line1, title_line2 = _split_title_lines(new_title)
                else:
                    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), True, gr.update(), gr.update()
                try:
                    save_hint, dropdown_update = _auto_save_workspace(
                        video_text, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                        avatar_sel, aud_for_ls, out_aud, out_vid,
                        sub_txt, sub_vid,
                        sub_fnt, sub_sz, sub_ps, sub_ps_off,
                        sub_col, sub_hi, sub_out, sub_out_sz,
                        sub_bg_col, sub_bg_op,
                        kw_enable, sub_hi_sc, new_keywords,
                        douyin_title_val=douyin_title_val, douyin_topics_val=douyin_topics_val,
                        sub_title_text_val=title_line1,
                        sub_title_text2_val=title_line2
                    )
                except Exception as e:
                    save_hint = _hint_html("error", f"淇濆瓨澶辫触: {e}")
                    dropdown_update = gr.update()
                # 绮剧畝妯″紡涓嶆洿鏂?douyin_title, douyin_topics, pip_prompt
                return title_line1, title_line2, new_keywords, kw_enable, gr.update(), gr.update(), gr.update(), hint, True, save_hint, dropdown_update

        subtitle_ai_optimize_btn.click(
            _subtitle_ai_optimize_and_save,
            inputs=[input_text, ai_rewrite_done,
                    prompt_audio, voice_select, audio_mode, direct_audio_upload,
                    avatar_select, audio_for_ls, output_audio, output_video,
                    sub_text, sub_video,
                    sub_font, sub_size, sub_pos, sub_pos_offset,
                    sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                    sub_bg_color, sub_bg_opacity,
                    sub_kw_enable, sub_hi_scale, sub_kw_text,
                    douyin_title, douyin_topics],
            outputs=[sub_title_text, sub_title_text2, sub_kw_text, sub_kw_enable,
                    douyin_title, douyin_topics, pip_prompt, tts_hint,
                    ai_rewrite_done,
                    workspace_record_hint, workspace_record_dropdown]
        )

        # 鈹€鈹€ 璇煶椋庢牸棰勮
        _VOICE_PRESETS = {
            "鏍囧噯":     dict(tp=0.8,  tk=30, temp=0.7, rp=8.0,  spd=1.0),
            "绋冲畾鎾姤": dict(tp=0.6,  tk=10, temp=0.2, rp=14.0, spd=0.95),
            "娲绘臣鐢熷姩": dict(tp=0.95, tk=60, temp=1.4, rp=4.0,  spd=1.1),
            "鎱㈤€熸湕璇?: dict(tp=0.6,  tk=10, temp=0.15, rp=14.0, spd=0.9),
        }
        def _on_voice_style(style):
            is_pro = (style == "涓撲笟妯″紡")
            if is_pro:
                return [gr.update(visible=True), gr.update()] + [gr.update()] * 4
            p = _VOICE_PRESETS.get(style, _VOICE_PRESETS["鏍囧噯"])
            return [
                gr.update(visible=False),
                gr.update(value=p["spd"]),
                gr.update(value=p["tp"]),
                gr.update(value=p["tk"]),
                gr.update(value=p["temp"]),
                gr.update(value=p["rp"]),
            ]
        voice_style.change(_on_voice_style,
            inputs=[voice_style],
            outputs=[pro_mode_group, voice_speed, top_p, top_k, temperature, repetition_penalty])

        # 鈹€鈹€ TTS 鍚堟垚閫熷害棰勮 鈹€鈹€
        def _on_tts_speed(preset):
            p = TTS_SPEED_PRESETS.get(preset, TTS_SPEED_PRESETS["馃殌 蹇€?])
            return [
                gr.update(value=p["num_beams"]),
                gr.update(value=p["max_mel_tokens"]),
            ]
        tts_speed_preset.change(_on_tts_speed,
            inputs=[tts_speed_preset],
            outputs=[num_beams, max_mel_tokens])

        # 鐩存帴涓婁紶闊抽鏃惰嚜鍔ㄥ～鍏?audio_for_ls
        def _on_direct_audio(audio_path):
            # 鍙湁褰撴湁瀹為檯闊抽璺緞鏃舵墠杩斿洖锛屽惁鍒欒繑鍥?gr.update() 涓嶆洿鏂?
            if audio_path and isinstance(audio_path, str) and audio_path.strip():
                return audio_path
            return gr.update()  # 涓嶆洿鏂?
        direct_audio_upload.change(_on_direct_audio,
            inputs=[direct_audio_upload],
            outputs=[audio_for_ls])

        # 鈹€鈹€ 鏁板瓧浜烘枃浠朵笂浼犻瑙?鈹€鈹€
        def _av_file_preview(file_path, progress=gr.Progress()):
            if not file_path:
                return gr.update(visible=False, value=None)
            # 杞爜淇濊瘉娴忚鍣ㄥ彲鎾斁
            try:
                converted = convert_video_for_browser(file_path, progress)
                return gr.update(visible=True, value=converted if converted else file_path, show_download_button=True)
            except Exception:
                return gr.update(visible=True, value=file_path, show_download_button=True)

        av_upload.change(_av_file_preview,
            inputs=[av_upload], outputs=[av_upload_preview])

        # 鈹€鈹€ 闊宠壊搴撲簨浠?鈹€鈹€
        def _on_voice_select(name):
            if not name or name.startswith("锛?) or not _LIBS_OK:
                return None, gr.update(visible=False)
            path = _vc.get_path(name)
            if path and os.path.exists(path):
                return path, gr.update(value=path, visible=True)
            return None, gr.update(visible=False)

        voice_select.change(_on_voice_select,
            inputs=[voice_select], outputs=[prompt_audio, voice_preview])

        voice_refresh_btn.click(
            lambda: gr.update(choices=_vc.get_choices() if _LIBS_OK else []),
            outputs=[voice_select])
        
        # 鈹€鈹€ TTS 妯″紡鍒囨崲浜嬩欢 鈹€鈹€
        def _on_tts_mode_switch(mode_choice):
            """鍒囨崲TTS妯″紡锛氭洿鏂扮幆澧冨彉閲忋€侀煶鑹插垪琛紝骞跺湪闇€瑕佹椂鍔犺浇妯″瀷"""
            global tts, _tts_on_gpu
            
            # 瑙ｆ瀽妯″紡
            mode = "local" if "鏈湴鐗? in mode_choice else "online"
            
            # 鏇存柊鐜鍙橀噺
            os.environ['TTS_MODE'] = mode
            
            # 淇濆瓨鍒?env鏂囦欢
            env_path = os.path.join(BASE_DIR, '.env')
            try:
                env_lines = []
                mode_found = False
                
                if os.path.exists(env_path):
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('TTS_MODE='):
                                env_lines.append(f'TTS_MODE={mode}\n')
                                mode_found = True
                            else:
                                env_lines.append(line)
                
                if not mode_found:
                    env_lines.append(f'TTS_MODE={mode}\n')
                
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(env_lines)
                
                safe_print(f"[TTS_MODE] 宸插垏鎹㈠埌: {mode}")
            except Exception as e:
                safe_print(f"[TTS_MODE] 淇濆瓨澶辫触: {e}")
            
            # 濡傛灉鍒囨崲鍒版湰鍦扮増涓旀ā鍨嬫湭鍔犺浇锛屽垯鍔犺浇妯″瀷
            if mode == "local" and tts is None:
                try:
                    safe_print("[TTS_MODE] 妫€娴嬪埌鍒囨崲鍒版湰鍦扮増锛屽紑濮嬪姞杞?IndexTTS2 妯″瀷...")
                    model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
                    if os.path.exists(model_dir):
                        original_cwd = os.getcwd()
                        os.chdir(INDEXTTS_DIR)
                        try:
                            from indextts.infer_v2 import IndexTTS2
                            tts = IndexTTS2(model_dir=model_dir,
                                          cfg_path=os.path.join(model_dir, "config.yaml"), 
                                          use_fp16=True)
                            _tts_on_gpu = True
                            safe_print("[TTS_MODE] IndexTTS2 妯″瀷鍔犺浇瀹屾垚")
                        finally:
                            os.chdir(original_cwd)
                    else:
                        safe_print("[TTS_MODE] 妯″瀷鐩綍涓嶅瓨鍦紝鏃犳硶鍔犺浇")
                except Exception as e:
                    safe_print(f"[TTS_MODE] 妯″瀷鍔犺浇澶辫触: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 鏇存柊闊宠壊鍒楄〃锛堟牴鎹ā寮忚繃婊わ級
            filter_mode = mode  # "local" 鎴?"online"
            new_choices = _vc.get_choices(filter_mode) if _LIBS_OK else []
            
            # 鏈湴鐗堟樉绀鸿闊抽鏍?鍚堟垚閫熷害/璇€燂紝鍦ㄧ嚎鐗堥殣钘?
            is_local = (mode == "local")
            return gr.update(choices=new_choices, value=None), gr.update(visible=is_local)
        
        tts_mode_switch.change(
            _on_tts_mode_switch,
            inputs=[tts_mode_switch],
            outputs=[voice_select, local_only_settings_group]
        )

        # 鈹€鈹€ 鏁板瓧浜哄簱浜嬩欢 鈹€鈹€
        def _on_avatar_select(name):
            if not name or name.startswith("锛?) or not _LIBS_OK:
                return gr.update(visible=False), gr.update(value="", visible=False)
            path = _av.get_path(name)
            if not path or not os.path.exists(path):
                return gr.update(visible=False), gr.update(value="", visible=False)
            return gr.update(value=path, visible=True, show_download_button=True), gr.update(value="", visible=False)

        avatar_select.change(_on_avatar_select,
            inputs=[avatar_select], outputs=[avatar_preview, avatar_preview_title])

        avatar_refresh_btn.click(
            lambda: gr.update(choices=_av.get_choices() if _LIBS_OK else []),
            outputs=[avatar_select])

        # 鈹€鈹€ 鏁板瓧浜?Tab 浜嬩欢 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
        def _av_all_outputs(hint_html):
            """缁熶竴杩斿洖鏍煎紡: hint + gallery + 涓嬫媺鍒锋柊 + 娓呯┖闅愯棌杈撳叆妗?""
            ch = _av.get_choices() if _LIBS_OK else []
            return (hint_html,
                    _av.render_gallery("av-del-input", "av-prev-trigger") if _LIBS_OK else "",
                    gr.update(choices=ch, value=None),
                    gr.update(value=""))  # 娓呯┖闅愯棌杈撳叆妗?

        def _save_avatar_handler(video, name, progress=gr.Progress()):
            if not _LIBS_OK:
                return _av_all_outputs(_hint_html("error","鎵╁睍妯″潡鏈姞杞?))
            if not video:
                return _av_all_outputs(_hint_html("warning","璇峰厛涓婁紶瑙嗛"))
            try:
                converted = convert_video_for_browser(video, progress)
                save_path = converted if (converted and os.path.exists(converted)) else video
            except Exception:
                save_path = video
            ok, msg = _av.add_avatar(save_path, name)
            return _av_all_outputs(_hint_html("ok" if ok else "warning", msg))

        av_save_btn.click(_save_avatar_handler,
            inputs=[av_upload, av_name],
            outputs=[av_save_hint, av_gallery, avatar_select, av_del_js_input])

        def _del_avatar_handler(name):
            print(f"[DEBUG] _del_avatar_handler 琚皟鐢紝name='{name}'")
            if not _LIBS_OK:
                return _av_all_outputs(_hint_html("error","鎵╁睍妯″潡鏈姞杞?))
            if not name or not name.strip() or name.startswith("锛?):
                return _av_all_outputs(_hint_html("warning","璇峰厛閫夋嫨瑕佸垹闄ょ殑鏁板瓧浜?))
            ok, msg = _av.del_avatar(name.strip())
            print(f"[DEBUG] del_avatar 杩斿洖: ok={ok}, msg={msg}")
            return _av_all_outputs(_hint_html("ok" if ok else "warning", msg))

        # 鍗＄墖鍐?馃棏 鎸夐挳 鈫?JS 鍐欏叆闅愯棌 textbox 鈫?change 浜嬩欢瑙﹀彂
        av_del_js_input.change(_del_avatar_handler,
            inputs=[av_del_js_input],
            outputs=[av_del_real_hint, av_gallery, avatar_select, av_del_js_input])

        # 鐐瑰嚮鍗＄墖 鈫?JS 鍐欏叆闅愯棌 textbox 鈫?change 浜嬩欢瑙﹀彂棰勮
        def _preview_avatar(name):
            if not _LIBS_OK or not name or name.startswith("锛?):
                return gr.update(value=None), ""
            path = _av.get_path(name)
            return (gr.update(value=path, show_download_button=True) if path and os.path.exists(path) else gr.update(value=None)), ""

        av_prev_js_input.change(_preview_avatar,
            inputs=[av_prev_js_input], outputs=[av_prev_video, av_prev_title])

        # 鈹€鈹€ 闊宠壊 Tab 浜嬩欢 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
        def _vc_all_outputs(hint_html):
            ch = _vc.get_choices() if _LIBS_OK else []
            return (hint_html,
                    _vc.render_gallery("vc-del-input", "vc-prev-trigger") if _LIBS_OK else "",
                    gr.update(choices=ch, value=None),
                    gr.update(value=""))  # 娓呯┖闅愯棌杈撳叆妗?

        def _save_voice(audio, name, source_choice):
            if not _LIBS_OK:
                return _vc_all_outputs(_hint_html("error","鎵╁睍妯″潡鏈姞杞?))
            # 鏍规嵁閫夋嫨鐨勭増鏈皟鐢ㄤ笉鍚岀殑淇濆瓨鏂规硶
            if "鍦ㄧ嚎鐗? in source_choice:
                ok, msg = _vc.add_online_voice(audio, name)
            else:
                ok, msg = _vc.add_local_voice(audio, name)
            return _vc_all_outputs(_hint_html("ok" if ok else "warning", msg))

        vc_save_btn.click(_save_voice,
            inputs=[vc_upload, vc_name, vc_source],
            outputs=[vc_save_hint, vc_gallery, voice_select, vc_del_js_input])
        
        # 鈹€鈹€ 鍚屾鍦ㄧ嚎闊宠壊鎸夐挳 鈹€鈹€
        def _sync_online_voices():
            if not _LIBS_OK:
                return _vc_all_outputs(_hint_html("error","鎵╁睍妯″潡鏈姞杞?))
            ok, msg = _vc.sync_online_voices()
            return _vc_all_outputs(_hint_html("ok" if ok else "warning", msg))
        
        vc_sync_btn.click(_sync_online_voices,
            outputs=[vc_save_hint, vc_gallery, voice_select, vc_del_js_input])

        def _del_voice_handler(name):
            print(f"[DEBUG] _del_voice_handler 琚皟鐢紝name='{name}'")
            if not _LIBS_OK:
                return _vc_all_outputs(_hint_html("error","鎵╁睍妯″潡鏈姞杞?))
            if not name or not name.strip() or name.startswith("锛?):
                return _vc_all_outputs(_hint_html("warning","璇峰厛閫夋嫨瑕佸垹闄ょ殑闊宠壊"))
            ok, msg = _vc.del_voice(name.strip())
            print(f"[DEBUG] del_voice 杩斿洖: ok={ok}, msg={msg}")
            return _vc_all_outputs(_hint_html("ok" if ok else "warning", msg))

        # 鍗＄墖鍐?馃棏 鎸夐挳 鈫?JS bridge
        vc_del_js_input.change(_del_voice_handler,
            inputs=[vc_del_js_input],
            outputs=[vc_del_real_hint, vc_gallery, voice_select, vc_del_js_input])

        # 鐐瑰嚮鍗＄墖 鈫?JS 鍐欏叆闅愯棌 textbox 鈫?change 浜嬩欢瑙﹀彂璇曞惉
        vc_prev_js_input.change(
            lambda n: (_vc.get_path(n) if (_LIBS_OK and n and not n.startswith("锛?)) else None),
            inputs=[vc_prev_js_input], outputs=[vc_prev_audio])

        # 鈹€鈹€ 鍏抽敭璇嶉珮浜紑鍏?鈹€鈹€
        def _toggle_kw(enabled):
            return gr.update(visible=enabled), gr.update(visible=enabled)
        sub_kw_enable.change(_toggle_kw, inputs=[sub_kw_enable],
                             outputs=[sub_kw_row, sub_hi_scale])

        # 鈹€鈹€ 瀛椾綋閫夋嫨棰勮 鈹€鈹€

        def _render_font_preview(font_path, text, width=580, height=64, font_size=30):
            """鐢?Pillow 娓叉煋瀛椾綋棰勮鍥撅紝杩斿洖 base64 PNG 瀛楃涓?""
            try:
                from PIL import Image, ImageDraw, ImageFont
                import base64, io
                img = Image.new("RGBA", (width, height), (26, 26, 46, 255))
                draw = ImageDraw.Draw(img)
                try:
                    pil_font = ImageFont.truetype(font_path, font_size)
                except Exception:
                    return ""
                bbox = draw.textbbox((0, 0), text, font=pil_font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                x = (width - tw) // 2 - bbox[0]
                y = (height - th) // 2 - bbox[1]
                draw.text((x, y), text, fill=(255, 255, 255, 255), font=pil_font)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return base64.b64encode(buf.getvalue()).decode("ascii")
            except Exception as e:
                print(f"[FONT PREVIEW] render failed: {e}")
                return ""

        def _on_font_select(font_name):
            """瀛椾綋閫夋嫨鍚庣敤 Pillow 娓叉煋棰勮鍥剧墖"""
            if not font_name or font_name in ("绯荤粺瀛椾綋", "榛樿瀛椾綋"):
                return gr.update(value="", visible=False)
            
            if not _LIBS_OK:
                return gr.update(value="", visible=False)
            
            info = _sub.get_font_info(font_name)
            if not info:
                return gr.update(value="", visible=False)
            
            display = info.get("display_name", font_name)
            filename = info.get("filename", "")
            category = info.get("category", "zh_cn")
            in_fonts = os.path.exists(os.path.join(_sub.FONTS_DIR, filename)) if filename else False
            size_mb = info.get("size", 0) / 1024 / 1024
            status = "鉁?宸蹭笅杞? if in_fonts else f"猬囷笍 鐢熸垚鏃惰嚜鍔ㄤ笅杞?({size_mb:.1f}MB)"
            
            # 浼樺厛鐢?font_cache 绮剧畝鐗堬紝鍏舵鐢?fonts/ 瀹屾暣鐗?
            font_file = ""
            cache_font = info.get("cache_font", "")
            if cache_font:
                p = os.path.join(_sub.BASE_DIR, cache_font)
                if os.path.exists(p):
                    font_file = p
            if not font_file and filename:
                p = os.path.join(_sub.FONTS_DIR, filename)
                if os.path.exists(p):
                    font_file = p
            
            # 鏍规嵁鍒嗙被鐢?display_name + 鏁板瓧 浣滀负棰勮鏂囧瓧
            cat_suffix = {"zh_cn": "涓枃瀛楀箷", "zh_tw": "涓枃瀛楀箷", "en": "Subtitle"}
            preview_text = f"{display} {cat_suffix.get(category, '瀛楀箷')} 1234"
            
            img_html = ""
            if font_file:
                b64 = _render_font_preview(font_file, preview_text)
                if b64:
                    img_html = (
                        f'<img src="data:image/png;base64,{b64}" '
                        f'style="width:100%;border-radius:6px;display:block;" />'
                    )
            
            if not img_html:
                img_html = (
                    '<div style="font-size:20px;color:#888;text-align:center;'
                    'padding:12px 0;">棰勮涓嶅彲鐢?/div>'
                )
            
            html = (
                f'<div style="padding:8px;background:#1a1a2e;border-radius:8px;">'
                f'{img_html}'
                f'<div style="color:#aaa;font-size:12px;text-align:center;'
                f'margin-top:6px;padding-bottom:4px;">'
                f'馃敜 {display} &nbsp; {status}</div>'
                f'</div>'
            )
            return gr.update(value=html, visible=True)
        
        sub_font.change(_on_font_select, inputs=[sub_font], outputs=[sub_font_preview])

        # 鈹€鈹€ 瀛楀箷鐢熸垚 鈹€鈹€
        def _do_subtitle(vid, aud, text,
                         font, size, pos, pos_offset,
                         color_txt, hi_txt, outline_txt, outline_size,
                         bg_color, bg_opacity,
                         kw_enable, kw_str, hi_scale,
                         title_text="", title_text2="", title_duration=5,
                         title_color="#FFD700", title_outline_color="#000000",
                         title_margin_top=200, title_font_size=68,
                         progress=gr.Progress()):
            if not _LIBS_OK:
                return "", _hint_html("error","鎵╁睍妯″潡鏈姞杞?)

            # 瑙ｆ瀽瑙嗛璺緞锛坓r.Video 鍦ㄤ笉鍚?Gradio 鐗堟湰杩斿洖鏍煎紡涓嶅悓锛?
            if isinstance(vid, dict):
                vid_path = (vid.get("video") or {}).get("path") or vid.get("path") or ""
            else:
                vid_path = str(vid) if vid else ""
            if not vid_path or not os.path.exists(vid_path):
                return "", _hint_html("warning","璇峰厛瀹屾垚瑙嗛鍚堟垚鍐嶆坊鍔犲瓧骞?)

            aud_path = str(aud) if (aud and isinstance(aud, str)) else None

            # 鍚堝苟涓よ鏍囬
            combined_title = ""
            if title_text and title_text.strip():
                combined_title = title_text.strip()
                if title_text2 and title_text2.strip():
                    combined_title += "锝? + title_text2.strip()
            elif title_text2 and title_text2.strip():
                combined_title = title_text2.strip()

            # 璋冭瘯鏃ュ織
            print(f"[SUBTITLE] _do_subtitle: kw_enable={kw_enable}, kw_str='{kw_str}'")
            print(f"[SUBTITLE] title_text='{title_text}', title_text2='{title_text2}', combined='{combined_title}'")

            def _cb(pct, msg): progress(pct, desc=msg)
            try:
                out = _sub.burn_subtitles(
                    vid_path, aud_path, text or "",
                    font, size,
                    color_txt, hi_txt, outline_txt, int(outline_size or 0),
                    pos, int(pos_offset or 0),
                    kw_enable=bool(kw_enable),
                    kw_str=kw_str or "",
                    hi_scale=float(hi_scale or 1.5),
                    bg_color=bg_color or "#000000",
                    bg_opacity=int(bg_opacity or 0),
                    title_text=combined_title,
                    title_duration=int(title_duration or 5),
                    title_color=title_color or "#FFD700",
                    title_outline_color=title_outline_color or "#000000",
                    title_margin_top=int(title_margin_top or 200),
                    title_font_size=int(title_font_size or 68),
                    intro_enable=False,
                    progress_cb=_cb
                )
                return (out,
                        _hint_html("ok", "瀛楀箷瑙嗛宸茬敓鎴? " + os.path.basename(out)))
            except Exception as e:
                # 瀹夊叏鎵撳嵃寮傚父鍫嗘爤
                try:
                    traceback.print_exc()
                except:
                    print(f"[ERROR] Exception: {repr(e)}")
                # 瀹夊叏澶勭悊寮傚父娑堟伅锛岄伩鍏嶇紪鐮侀敊璇?
                try:
                    error_msg = str(e)[:300]
                except:
                    error_msg = repr(e)[:300]
                return ("",
                        _hint_html("error", f"瀛楀箷鐢熸垚澶辫触: {error_msg}"))

        # 瀛楀箷鎸夐挳鐐瑰嚮 - 鐩存帴鍦ㄥ畬鎴愬悗淇濆瓨
        def subtitle_and_save(out_vid, aud_for_ls, sub_txt, sub_fnt, sub_sz, sub_ps, sub_ps_off,
                             sub_col, sub_hi, sub_out, sub_out_sz,
                             sub_bg_col, sub_bg_op, sub_kw_en, sub_kw_txt, sub_hi_sc,
                             # 鏍囬鍙傛暟
                             title_txt, title_txt2, title_fs, title_dur, title_col, title_out_col, title_mt,
                             # 淇濆瓨闇€瑕佺殑鍏朵粬鍙傛暟
                             inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                             avatar_sel, out_aud,
                             douyin_title_val, douyin_topics_val,
                             progress=gr.Progress()):
            """鐢熸垚瀛楀箷骞惰嚜鍔ㄤ繚瀛樺伐浣滃彴鐘舵€?""
            # 鍏堣繑鍥炲姞杞界姸鎬?
            yield gr.update(), _hint_html("info", "馃幀 姝ｅ湪鐢熸垚瀛楀箷瑙嗛锛岃绋嶅€?.."), gr.update(), gr.update()

            # 瀛楀箷鍐呭鐩存帴浣跨敤鏂囨鍐呭锛堥伩鍏嶇淮鎶や袱浠芥枃鏈級
            sub_txt = inp_txt or ""
            # 鍏堢敓鎴愬瓧骞?
            sub_vid_path, sub_hnt = _do_subtitle(
                out_vid, aud_for_ls, sub_txt, sub_fnt, sub_sz, sub_ps, sub_ps_off,
                sub_col, sub_hi, sub_out, sub_out_sz,
                sub_bg_col, sub_bg_op, sub_kw_en, sub_kw_txt, sub_hi_sc,
                title_text=title_txt or "",
                title_text2=title_txt2 or "",
                title_duration=int(title_dur or 5),
                title_color=title_col or "#FFD700",
                title_outline_color=title_out_col or "#000000",
                title_margin_top=int(title_mt or 200),
                title_font_size=int(title_fs or 68),
                progress=progress
            )

            # 淇濆瓨宸ヤ綔鍙扮姸鎬?
            # 娉ㄦ剰锛氫娇鐢ㄥ疄闄呯殑闊抽鍜岃棰戣矾寰?
            hint_msg, dropdown_update = _auto_save_workspace(
                inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                avatar_sel, aud_for_ls, aud_for_ls, out_vid,
                inp_txt, sub_vid_path,
                sub_fnt, sub_sz, sub_ps, sub_ps_off,
                sub_col, sub_hi, sub_out, sub_out_sz,
                sub_bg_col, sub_bg_op,
                sub_kw_en, sub_hi_sc, sub_kw_txt,
                douyin_title_val=douyin_title_val, douyin_topics_val=douyin_topics_val,
                sub_title_text_val=title_txt,
                sub_title_text2_val=title_txt2,
                intro_enable_val=False
            )

            # 杩斿洖瀛楀箷瑙嗛锛岄渶瑕佽缃?visible=True 鍜?show_download_button=True
            if sub_vid_path:
                sub_vid_update = gr.update(value=sub_vid_path, visible=True, show_download_button=True)
            else:
                sub_vid_update = gr.update(visible=False)

            yield sub_vid_update, sub_hnt, hint_msg, dropdown_update
        
        sub_btn.click(
            subtitle_and_save,
            inputs=[
                output_video, audio_for_ls,
                sub_text, sub_font, sub_size, sub_pos, sub_pos_offset,
                sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                sub_bg_color, sub_bg_opacity,
                sub_kw_enable, sub_kw_text, sub_hi_scale,
                # 鏍囬鍙傛暟
                sub_title_text, sub_title_text2, sub_title_font_size, sub_title_duration, sub_title_color,
                sub_title_outline_color, sub_title_margin_top,
                # 淇濆瓨闇€瑕佺殑鍙傛暟
                input_text, prompt_audio, voice_select, audio_mode, direct_audio_upload,
                avatar_select, output_audio,
                douyin_title, douyin_topics
            ],
            outputs=[sub_video, sub_hint,
                    workspace_record_hint, workspace_record_dropdown]
        ).then(
            lambda v: gr.update(visible=True) if v else gr.update(visible=False),
            inputs=[sub_video],
            outputs=[sub_video_panel]
        )
        
        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
        # DeepSeek API 闆嗘垚
        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
        
        _deepseek_last_call = [0.0]  # 涓婃璋冪敤鏃堕棿鎴筹紙鐢ㄥ垪琛ㄤ互渚块棴鍖呭唴淇敼锛?
        _DEEPSEEK_COOLDOWN = 60     # 鍐峰嵈鏃堕棿锛堢锛?

        def _call_deepseek_api(prompt, system_prompt="浣犳槸涓€涓笓涓氱殑鏂囨鍒涗綔鍔╂墜銆?):
            """
            璋冪敤DeepSeek API锛堥檺娴侊細60绉掑唴鍙厑璁歌皟鐢ㄤ竴娆★級
            :param prompt: 鐢ㄦ埛鎻愮ず璇?
            :param system_prompt: 绯荤粺鎻愮ず璇?
            :return: API杩斿洖鐨勬枃鏈唴瀹?
            """
            now = time.time()
            elapsed = now - _deepseek_last_call[0]
            if elapsed < _DEEPSEEK_COOLDOWN:
                remaining = int(_DEEPSEEK_COOLDOWN - elapsed)
                return None, f"鈴?璇锋眰杩囦簬棰戠箒锛岃 {remaining} 绉掑悗鍐嶈瘯"

            try:
                import requests
                
                # DeepSeek API閰嶇疆
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                if not api_key:
                    # 灏濊瘯浠?env鏂囦欢璇诲彇
                    env_file = os.path.join(BASE_DIR, ".env")
                    if os.path.exists(env_file):
                        with open(env_file, "r", encoding="utf-8") as f:
                            for line in f:
                                if line.startswith("DEEPSEEK_API_KEY="):
                                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                    break
                
                if not api_key:
                    return None, "鉂?鏈厤缃瓺eepSeek API瀵嗛挜\n\n璇峰湪.env鏂囦欢涓坊鍔狅細\nDEEPSEEK_API_KEY=your_api_key"
                
                # 璁板綍鏈璋冪敤鏃堕棿锛堝湪瀹為檯鍙戣姹傚墠璁板綍锛岄槻姝㈠苟鍙戠粫杩囷級
                _deepseek_last_call[0] = time.time()
                
                # 璋冪敤API
                url = "https://ai.zhimengai.xyz/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return content.strip(), None
                else:
                    error_msg = f"API璇锋眰澶辫触 (鐘舵€佺爜: {response.status_code})"
                    try:
                        error_detail = response.json().get("error", {}).get("message", "")
                        if error_detail:
                            error_msg += f"\n{error_detail}"
                    except:
                        pass
                    return None, error_msg
                    
            except requests.exceptions.Timeout:
                return None, "鉂?API璇锋眰瓒呮椂锛岃妫€鏌ョ綉缁滆繛鎺?
            except Exception as e:
                return None, f"鉂?API璋冪敤澶辫触: {str(e)}"
        
        def _rewrite_text_with_deepseek(original_text):
            """浣跨敤DeepSeek AI鏀瑰啓鏂囨,鍚屾椂浼樺寲鏍囬銆佺敓鎴愯瘽棰樻爣绛俱€佸叧閿瘝鍜岀敾涓敾鎻愮ず璇?""
            if not original_text or not original_text.strip():
                return original_text, "", "", "", "", False, _hint_html("warning", "璇峰厛杈撳叆鏂囨湰鍐呭")
            
            prompt = f"""璇峰畬鎴愪互涓嬩簲涓换鍔★細

浠诲姟涓€锛氬皢浠ヤ笅鏂囨鏀瑰啓寰楁洿鍔犵敓鍔ㄣ€佸惛寮曚汉锛屼繚鎸佸師鎰忎絾鎻愬崌琛ㄨ揪鏁堟灉銆?
瑕佹眰锛氬繀椤讳繚鐣欏師鏂囩殑鎵€鏈夋钀藉拰瀹屾暣鍐呭锛屼笉瑕佸垹鍑忋€佸悎骞舵垨缂╃煭锛屼繚鎸佸拰鍘熸枃鐩歌繎鐨勫瓧鏁板拰娈佃惤鏁般€備娇鐢ㄦ洿鐢熷姩鐨勮瘝姹囧拰琛ㄨ揪鏂瑰紡锛岃鏂囨鏇存湁鎰熸煋鍔涘拰鍚稿紩鍔涖€?

浠诲姟浜岋細鏍规嵁鏂囨鍐呭锛岀敓鎴愪竴涓惛寮曚汉鐨勭煭瑙嗛鏍囬锛堜笉瓒呰繃30瀛楋紝鍚稿紩鐪肩悆銆佸紩鍙戝ソ濂囷級銆?

浠诲姟涓夛細鏍规嵁鏂囨鍐呭锛岀敓鎴?涓浉鍏崇殑鐑棬璇濋鏍囩锛岀敤閫楀彿鍒嗛殧銆?

浠诲姟鍥涳細浠庢枃妗堜腑鎻愬彇灏藉彲鑳藉鐨勫叧閿瘝锛堢敤浜庡瓧骞曢珮浜樉绀猴級锛屽寘鎷牳蹇冨悕璇嶃€佸姩璇嶃€佸舰瀹硅瘝绛夐噸瑕佽瘝璇紝涓嶉檺鏁伴噺锛岀敤閫楀彿鍒嗛殧銆?

浠诲姟浜旓細鏍规嵁鏂囨鍐呭锛屼负鐢讳腑鐢昏棰戠敓鎴愭彁绀鸿瘝銆傛瘡30绉掕棰戠敓鎴?涓彁绀鸿瘝锛堜緥濡?0绉掓枃妗?1涓紝60绉掓枃妗?2涓紝90绉掓枃妗?3涓級銆傛牴鎹枃妗堥暱搴︿及绠楁湕璇绘椂闀匡紙绾︽瘡绉?-4涓瓧锛夛紝璁＄畻鎵€闇€鎻愮ず璇嶆暟閲忋€?
瑕佹眰锛?
- 姣忎釜鎻愮ず璇嶅搴旀枃妗堜腑涓€涓€傚悎鎻掑叆鐢讳腑鐢荤殑浣嶇疆锛堝璁茶В鏌愪釜鍏蜂綋鍦烘櫙/鐗╀欢/娲诲姩鏃讹級
- 涓ユ牸鎸夋瘡30绉?涓殑瑙勫垯鐢熸垚瀵瑰簲鏁伴噺鐨勬彁绀鸿瘝
- 姣忎釜鎻愮ず璇嶄笉瓒呰繃80瀛楋紝蹇呴』鍖呭惈鍔ㄦ€佸厓绱犲拰鍔ㄤ綔鎻忚堪锛岀敾闈㈣鏈夎繍鍔ㄦ劅鍜岀敓鍛藉姏
- 鍔ㄦ€佽姹傦細蹇呴』鍖呭惈浜虹墿鍔ㄤ綔銆佺墿浣撶Щ鍔ㄣ€侀暅澶磋繍鍔ㄧ瓑鍔ㄦ€佸厓绱狅紝閬垮厤闈欐€佺敾闈€備緥濡傦細浜虹墿璧板姩銆佹墜閮ㄦ搷浣溿€佺墿鍝佸睍绀恒€侀暅澶存帹鎷夋憞绉荤瓑
- 鐢婚潰椋庢牸锛氳秴娓呭啓瀹為鏍硷紝鏋勫浘绠€娲侊紝鍏夌嚎鏄庝寒鑷劧
- 姣忎釜鎻愮ず璇嶇殑鍦烘櫙蹇呴』涓嶅悓锛屼笌瀵瑰簲鏂囨娈佃惤鍐呭鐩稿叧

鍘熸枃妗堬細
{original_text}

璇蜂弗鏍兼寜鐓т互涓嬫牸寮忚緭鍑猴紝涓嶈娣诲姞鍏朵粬鍐呭锛?
鏂囨锛歔鏀瑰啓鍚庣殑瀹屾暣鏂囨]
鏍囬锛歔浣犵殑鏍囬]
璇濋锛歔璇濋1,璇濋2,璇濋3,璇濋4,璇濋5]
鍏抽敭璇嶏細[鍏抽敭璇?,鍏抽敭璇?,鍏抽敭璇?,...]
鎻愮ず璇?锛歔绗竴澶勭敾涓敾鍦烘櫙鎻忚堪]
鎻愮ず璇?锛歔绗簩澶勭敾涓敾鍦烘櫙鎻忚堪]
..."""
            
            result, error = _call_deepseek_api(prompt)
            
            if error:
                return original_text, "", "", "", "", False, _hint_html("error", error)
            
            if result:
                # 瑙ｆ瀽杩斿洖缁撴灉
                lines = result.strip().split('\n')
                new_text = original_text
                new_title = ""
                new_topics = ""
                new_keywords = ""
                pip_prompts_list = []  # 澶氫釜鐢讳腑鐢绘彁绀鸿瘝
                
                # 瑙ｆ瀽澶氳鏂囨锛氭枃妗堝彲鑳借法瓒婂琛岋紝鐩村埌閬囧埌"鏍囬锛?鎴?璇濋锛?
                in_text_block = False
                text_lines = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("鏂囨锛?) or stripped.startswith("鏂囨:"):
                        first_line = stripped.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                        if first_line:
                            text_lines.append(first_line)
                        in_text_block = True
                    elif stripped.startswith("鏍囬锛?) or stripped.startswith("鏍囬:"):
                        in_text_block = False
                        new_title = stripped.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                    elif stripped.startswith("璇濋锛?) or stripped.startswith("璇濋:"):
                        in_text_block = False
                        new_topics = stripped.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                    elif stripped.startswith("鍏抽敭璇嶏細") or stripped.startswith("鍏抽敭璇?"):
                        in_text_block = False
                        new_keywords = stripped.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                    elif re.match(r'鎻愮ず璇峔d*[锛?]', stripped):
                        in_text_block = False
                        pip_line = re.sub(r'^鎻愮ず璇峔d*[锛?]\s*', '', stripped).strip()
                        if pip_line:
                            pip_prompts_list.append(pip_line)
                    elif in_text_block and stripped:
                        text_lines.append(stripped)
                
                if text_lines:
                    new_text = "\n".join(text_lines)
                
                # 濡傛灉娌¤В鏋愬埌鏂囨锛堝彲鑳紸I娌′弗鏍兼寜鏍煎紡锛夛紝鐢ㄦ暣涓粨鏋滀綔涓烘敼鍐欐枃妗?
                if new_text == original_text and not any(
                    line.strip().startswith(("鏂囨锛?, "鏂囨:")) for line in lines
                ):
                    text_parts = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith(("鏍囬锛?, "鏍囬:", "璇濋锛?, "璇濋:", "鍏抽敭璇嶏細", "鍏抽敭璇?")) or re.match(r'鎻愮ず璇峔d*[锛?]', line):
                            break
                        if line:
                            text_parts.append(line)
                    if text_parts:
                        new_text = "\n".join(text_parts)
                
                # 濡傛灉鏈夊叧閿瘝锛岃嚜鍔ㄥ紑鍚叧閿瘝楂樹寒
                kw_enable = bool(new_keywords.strip())
                
                # 澶氫釜鎻愮ず璇嶇敤鎹㈣鍒嗛殧
                new_pip_prompt = "\n".join(pip_prompts_list) if pip_prompts_list else ""
                
                pip_count = len(pip_prompts_list)
                return new_text, new_title, new_topics, new_keywords, new_pip_prompt, kw_enable, _hint_html("ok", f"AI鏀瑰啓瀹屾垚锛佸凡鐢熸垚鏍囬銆佽瘽棰樸€佸叧閿瘝鍜寋pip_count}涓敾涓敾鎻愮ず璇?)
            else:
                return original_text, "", "", "", "", False, _hint_html("error", "AI鏀瑰啓澶辫触锛屾湭杩斿洖鍐呭")
        
        def _optimize_title_with_deepseek(current_title, current_topics, video_text):
            """浣跨敤DeepSeek AI浼樺寲鏍囬骞剁敓鎴愯瘽棰樻爣绛?""
            if not video_text or not video_text.strip():
                return current_title, current_topics, _hint_html("warning", "璇峰厛杈撳叆瑙嗛鏂囨湰鍐呭")
            
            prompt = f"""璇锋牴鎹互涓嬭棰戞枃鏈唴瀹癸紝鐢熸垚涓€涓惛寮曚汉鐨勬姈闊宠棰戞爣棰樺拰5涓浉鍏宠瘽棰樻爣绛俱€?

瑙嗛鏂囨湰鍐呭锛?
{video_text[:200]}

瑕佹眰锛?
1. 鏍囬锛氫笉瓒呰繃30瀛楋紝瑕佸惛寮曠溂鐞冦€佸紩鍙戝ソ濂?
2. 璇濋鏍囩锛?涓紝鐢ㄩ€楀彿鍒嗛殧锛岃鐑棬涓旂浉鍏?
3. 杈撳嚭鏍煎紡涓ユ牸鎸夌収锛?
鏍囬锛歔浣犵殑鏍囬]
璇濋锛歔璇濋1,璇濋2,璇濋3,璇濋4,璇濋5]

璇风洿鎺ヨ緭鍑猴紝涓嶈娣诲姞鍏朵粬鍐呭銆?""
            
            result, error = _call_deepseek_api(prompt)
            
            if error:
                return current_title, current_topics, _hint_html("error", error)
            
            if result:
                # 瑙ｆ瀽杩斿洖缁撴灉
                lines = result.strip().split('\n')
                new_title = current_title
                new_topics = current_topics
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("鏍囬锛?) or line.startswith("鏍囬:"):
                        new_title = line.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                    elif line.startswith("璇濋锛?) or line.startswith("璇濋:"):
                        new_topics = line.split("锛?, 1)[-1].split(":", 1)[-1].strip()
                
                return new_title, new_topics, _hint_html("ok", "AI浼樺寲瀹屾垚")
            else:
                return current_title, current_topics, _hint_html("error", "AI浼樺寲澶辫触锛屾湭杩斿洖鍐呭")
        
        # 缁戝畾AI鏀瑰啓鎸夐挳锛堜竴娆PI璋冪敤鍚屾椂鏀瑰啓鏂囨+鐢熸垚鏍囬+鐢熸垚鏍囩+鐢讳腑鐢绘彁绀鸿瘝锛?
        def _rewrite_and_save(original_text,
                              # 淇濆瓨闇€瑕佺殑鍙傛暟
                              prmt_aud, voice_sel, audio_mode_val, direct_aud,
                              avatar_sel, aud_for_ls, out_aud, out_vid,
                              sub_vid,
                              sub_fnt, sub_sz, sub_ps, sub_ps_off,
                              sub_col, sub_hi, sub_out, sub_out_sz,
                              sub_bg_col, sub_bg_op,
                              sub_kw_en, sub_hi_sc, sub_kw_txt):
            """鏀瑰啓鏂囨骞跺悓姝ヨ繑鍥炵粰瀛楀箷锛屽悓鏃朵繚瀛樺伐浣滃彴璁板綍"""
            try:
                new_text, title, topics, new_keywords, new_pip_prompt, kw_enable, hint = _rewrite_text_with_deepseek(original_text)
                # 灏嗘爣棰樺垎鎴愪袱琛?
                title_line1, title_line2 = _split_title_lines(title)
            except Exception as e:
                new_text = original_text
                title, topics, new_keywords, new_pip_prompt, kw_enable = "", "", "", "", False
                title_line1, title_line2 = "", ""
                hint = _hint_html("error", f"AI鏀瑰啓寮傚父: {e}")
            
            try:
                save_hint, dropdown_update = _auto_save_workspace(
                    new_text, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                    avatar_sel, aud_for_ls, out_aud, out_vid,
                    new_text, sub_vid,
                    sub_fnt, sub_sz, sub_ps, sub_ps_off,
                    sub_col, sub_hi, sub_out, sub_out_sz,
                    sub_bg_col, sub_bg_op,
                    kw_enable, sub_hi_sc, new_keywords,
                    douyin_title_val=title, douyin_topics_val=topics,
                    sub_title_text_val=title_line1,
                    sub_title_text2_val=title_line2,
                    pip_prompt_val=new_pip_prompt,
                    search_key=original_text
                )
            except Exception as e:
                print(f"[AI鏀瑰啓] 淇濆瓨宸ヤ綔鍙板け璐? {e}")
                traceback.print_exc()
                save_hint = _hint_html("error", f"淇濆瓨宸ヤ綔鍙板け璐? {e}")
                dropdown_update = gr.update()
            
            # outputs: input_text, douyin_title, douyin_topics, sub_kw_text, sub_kw_enable, pip_prompt, tts_hint, sub_text, sub_title_text, sub_title_text2, ai_rewrite_done, workspace_hint, workspace_dropdown
            return new_text, title, topics, new_keywords, kw_enable, new_pip_prompt, hint, new_text, title_line1, title_line2, True, save_hint, dropdown_update
        rewrite_btn.click(
            _rewrite_and_save,
            inputs=[input_text,
                    # 淇濆瓨闇€瑕佺殑鍙傛暟
                    prompt_audio, voice_select, audio_mode, direct_audio_upload,
                    avatar_select, audio_for_ls, output_audio, output_video,
                    sub_video,
                    sub_font, sub_size, sub_pos, sub_pos_offset,
                    sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                    sub_bg_color, sub_bg_opacity,
                    sub_kw_enable, sub_hi_scale, sub_kw_text],
            outputs=[input_text, douyin_title, douyin_topics, sub_kw_text, sub_kw_enable,
                    pip_prompt, tts_hint, sub_text, sub_title_text, sub_title_text2,
                    ai_rewrite_done,
                    workspace_record_hint, workspace_record_dropdown])
        
        
        # 娓呯┖鎻愮ず
        input_text.change(lambda: "", outputs=[tts_hint])
        
        # 缁戝畾AI浼樺寲鎸夐挳锛堜紭鍖栧悗鍚屾椂淇濆瓨宸ヤ綔鍙帮級
        def _optimize_and_save(current_title, current_topics, video_text,
                               # 淇濆瓨闇€瑕佺殑鍙傛暟
                               prmt_aud, voice_sel, audio_mode_val, direct_aud,
                               avatar_sel, aud_for_ls, out_aud, out_vid,
                               sub_txt, sub_vid,
                               sub_fnt, sub_sz, sub_ps, sub_ps_off,
                               sub_col, sub_hi, sub_out, sub_out_sz,
                               sub_bg_col, sub_bg_op,
                               sub_kw_en, sub_hi_sc, sub_kw_txt):
            new_title, new_topics, hint = _optimize_title_with_deepseek(current_title, current_topics, video_text)
            try:
                save_hint, dropdown_update = _auto_save_workspace(
                    video_text, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                    avatar_sel, aud_for_ls, out_aud, out_vid,
                    sub_txt, sub_vid,
                    sub_fnt, sub_sz, sub_ps, sub_ps_off,
                    sub_col, sub_hi, sub_out, sub_out_sz,
                    sub_bg_col, sub_bg_op,
                    sub_kw_en, sub_hi_sc, sub_kw_txt,
                    douyin_title_val=new_title, douyin_topics_val=new_topics,
                    sub_title_text_val="",  # AI浼樺寲鏍囬涓嶅奖鍝嶅瓧骞曟爣棰?
                    sub_title_text2_val=""
                )
            except Exception as e:
                print(f"[AI浼樺寲] 淇濆瓨宸ヤ綔鍙板け璐? {e}")
                save_hint = _hint_html("error", f"淇濆瓨宸ヤ綔鍙板け璐? {e}")
                dropdown_update = gr.update()
            return new_title, new_topics, hint, save_hint, dropdown_update
        optimize_btn.click(
            _optimize_and_save,
            inputs=[douyin_title, douyin_topics, input_text,
                    # 淇濆瓨闇€瑕佺殑鍙傛暟
                    prompt_audio, voice_select, audio_mode, direct_audio_upload,
                    avatar_select, audio_for_ls, output_audio, output_video,
                    sub_text, sub_video,
                    sub_font, sub_size, sub_pos, sub_pos_offset,
                    sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                    sub_bg_color, sub_bg_opacity,
                    sub_kw_enable, sub_hi_scale, sub_kw_text],
            outputs=[douyin_title, douyin_topics, douyin_hint,
                    workspace_record_hint, workspace_record_dropdown])
        
        # 鎵嬪姩缂栬緫瑙嗛鏍囬/璇濋鏃惰嚜鍔ㄤ繚瀛樺伐浣滃彴
        def _on_title_topics_change(title_val, topics_val,
                                    inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                                    avatar_sel, aud_for_ls, out_aud, out_vid,
                                    sub_txt, sub_vid,
                                    sub_fnt, sub_sz, sub_ps, sub_ps_off,
                                    sub_col, sub_hi, sub_out, sub_out_sz,
                                    sub_bg_col, sub_bg_op,
                                    sub_kw_en, sub_hi_sc, sub_kw_txt,
                                    sub_title_txt, sub_title_txt2):
            try:
                # 鍙湁鏍囬鎴栬瘽棰橀潪绌烘椂鎵嶄繚瀛橈紙閬垮厤娓呯┖鏃惰Е鍙戞棤鐢ㄤ繚瀛橈級
                if not (title_val or "").strip() and not (topics_val or "").strip():
                    return gr.update(), gr.update()
                return _auto_save_workspace(
                    inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                    avatar_sel, aud_for_ls, out_aud, out_vid,
                    sub_txt, sub_vid,
                    sub_fnt, sub_sz, sub_ps, sub_ps_off,
                    sub_col, sub_hi, sub_out, sub_out_sz,
                    sub_bg_col, sub_bg_op,
                    sub_kw_en, sub_hi_sc, sub_kw_txt,
                    douyin_title_val=title_val, douyin_topics_val=topics_val,
                    sub_title_text_val=sub_title_txt,
                    sub_title_text2_val=sub_title_txt2
                )
            except Exception as e:
                print(f"[鏍囬璇濋鑷姩淇濆瓨] 澶辫触: {e}")
                traceback.print_exc()
                return gr.update(), gr.update()
        _title_topics_save_inputs = [
            douyin_title, douyin_topics,
            input_text, prompt_audio, voice_select, audio_mode, direct_audio_upload,
            avatar_select, audio_for_ls, output_audio, output_video,
            sub_text, sub_video,
            sub_font, sub_size, sub_pos, sub_pos_offset,
            sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
            sub_bg_color, sub_bg_opacity,
            sub_kw_enable, sub_hi_scale, sub_kw_text,
            sub_title_text, sub_title_text2
        ]
        _title_topics_save_outputs = [workspace_record_hint, workspace_record_dropdown]
        douyin_title.change(_on_title_topics_change,
            inputs=_title_topics_save_inputs, outputs=_title_topics_save_outputs)
        douyin_topics.change(_on_title_topics_change,
            inputs=_title_topics_save_inputs, outputs=_title_topics_save_outputs)
        
        # 鎶栭煶鍙戝竷
        def _publish_overlay_html(step_name, step_detail="", is_done=False, is_error=False):
            """鐢熸垚鍙戝竷杩涘害灞呬腑娴眰 HTML"""
            if is_done:
                return ""  # 瀹屾垚鍚庢竻绌烘诞灞傦紝鐢辨渶缁堢粨鏋滄浛浠?
            if is_error:
                return ""  # 閿欒鏃舵竻绌烘诞灞?
            return (
                f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
                f'border:2px solid #6366f1;border-radius:16px;'
                f'padding:28px 24px;margin:8px 0;'
                f'box-shadow:0 8px 32px rgba(99,102,241,.25);'
                f'text-align:center;">'
                # 鏃嬭浆鍔ㄧ敾
                f'<div style="width:48px;height:48px;border:4px solid rgba(99,102,241,.2);'
                f'border-top-color:#6366f1;border-radius:50%;'
                f'animation:zdai-publish-spin .8s linear infinite;'
                f'margin:0 auto 16px;"></div>'
                # 褰撳墠姝ラ
                f'<div style="font-size:16px;font-weight:800;color:#e2e8f0;'
                f'font-family:Microsoft YaHei,sans-serif;margin-bottom:6px;">'
                f'{step_name}</div>'
                # 姝ラ璇︽儏
                f'<div style="font-size:13px;color:#94a3b8;'
                f'font-family:Microsoft YaHei,sans-serif;margin-bottom:16px;">'
                f'{step_detail}</div>'
                # 璇峰嬁鎿嶄綔璀﹀憡
                f'<div style="display:inline-flex;align-items:center;gap:8px;'
                f'background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.3);'
                f'border-radius:8px;padding:8px 16px;">'
                f'<span style="font-size:16px;">鈿狅笍</span>'
                f'<span style="font-size:12px;color:#fbbf24;font-weight:600;'
                f'font-family:Microsoft YaHei,sans-serif;">'
                f'鍙戝竷杩涜涓紝璇峰嬁鎿嶄綔椤甸潰</span>'
                f'</div>'
                f'<style>@keyframes zdai-publish-spin{{to{{transform:rotate(360deg)}}}}</style>'
                f'</div>'
            )

        def _do_platform_publish(bgm_video, sub_video, output_video, title_text, topics_text, platforms, progress=gr.Progress()):
            """鍙戝竷瑙嗛鍒伴€変腑鐨勫钩鍙?- 浼樺厛浣跨敤瀛楀箷瑙嗛锛堢敓鎴愬櫒锛屽疄鏃舵樉绀鸿繘搴︼級"""
            # 鈹€鈹€ 鍓嶇疆鏍￠獙 鈹€鈹€
            if not platforms:
                yield _hint_html("warning", "璇疯嚦灏戦€夋嫨涓€涓彂甯冨钩鍙?)
                return

            missing_deps = []
            try:
                import selenium
            except ImportError:
                missing_deps.append("selenium")
            try:
                import requests
            except ImportError:
                missing_deps.append("requests")
            if missing_deps:
                deps_str = "銆?.join(missing_deps)
                yield _hint_html("error",
                        f"鉂?缂哄皯渚濊禆锛歿deps_str}<br><br>"
                        "璇疯繍琛屼互涓嬪懡浠ゅ畨瑁咃細<br>"
                        "1. 鍙屽嚮杩愯銆屽畨瑁呮姈闊冲彂甯冧緷璧?bat銆?br>"
                        "鎴?br>"
                        f"2. 鎵嬪姩杩愯锛歱ip install {' '.join(missing_deps)}")
                return

            # 瑙ｆ瀽瑙嗛璺緞锛堜紭鍏堬細甯GM瑙嗛 > 瀛楀箷瑙嗛 > 鍚堟垚瑙嗛锛?
            video_to_use = None
            video_type = ""

            if bgm_video:
                if isinstance(bgm_video, dict):
                    bgm_video_path = (bgm_video.get("video") or {}).get("path") or bgm_video.get("path") or bgm_video.get("value") or ""
                else:
                    bgm_video_path = str(bgm_video) if bgm_video else ""
                if bgm_video_path and os.path.exists(bgm_video_path):
                    video_to_use = bgm_video_path
                    video_type = "甯GM瑙嗛"

            if sub_video:
                if isinstance(sub_video, dict):
                    sub_video_path = (sub_video.get("video") or {}).get("path") or sub_video.get("path") or sub_video.get("value") or ""
                else:
                    sub_video_path = str(sub_video) if sub_video else ""
                if sub_video_path and os.path.exists(sub_video_path):
                    if not video_to_use:
                        video_to_use = sub_video_path
                        video_type = "瀛楀箷瑙嗛"
            if not video_to_use and output_video:
                if isinstance(output_video, dict):
                    output_video_path = (output_video.get("video") or {}).get("path") or output_video.get("path") or output_video.get("value") or ""
                else:
                    output_video_path = str(output_video) if output_video else ""
                if output_video_path and os.path.exists(output_video_path):
                    video_to_use = output_video_path
                    video_type = "鍚堟垚瑙嗛"
            if not video_to_use:
                yield _hint_html("warning", "璇峰厛鐢熸垚瑙嗛锛堝彲浠ユ槸鏈€缁堝悎鎴愯棰戞垨瀛楀箷瑙嗛锛?)
                return

            topics = []
            if topics_text:
                topics = [t.strip() for t in re.split(r'[,锛屻€乗s]+', topics_text.strip()) if t.strip()]

            # 鈹€鈹€ 閫愬钩鍙板彂甯?鈹€鈹€
            all_results = []
            for platform_name in platforms:
                yield _publish_overlay_html(f"鍑嗗鍙戝竷鍒皗platform_name}...", "姝ｅ湪鍒濆鍖栧彂甯冩祦绋?)

                q = _queue.Queue()
                result = {"success": False, "message": ""}

                def _run_publish(pname=platform_name):
                    try:
                        if pname == "鎶栭煶":
                            import lib_douyin_publish as douyin_pub
                            publisher = douyin_pub.DouyinPublisher()
                        elif pname == "瑙嗛鍙?:
                            import lib_shipinhao_publish as sph_pub
                            publisher = sph_pub.ShipinhaoPublisher()
                        elif pname == "鍝斿摡鍝斿摡":
                            import lib_bilibili_publish as bilibili_pub
                            publisher = bilibili_pub.BilibiliPublisher()
                        elif pname == "灏忕孩涔?:
                            import lib_xiaohongshu_publish as xhs_pub
                            publisher = xhs_pub.XiaohongshuPublisher()
                        elif pname == "蹇墜":
                            import lib_kuaishou_publish as ks_pub
                            publisher = ks_pub.KuaishouPublisher()
                        else:
                            result["success"] = False
                            result["message"] = f"{pname} 骞冲彴鏆傛湭鏀寔"
                            q.put(("done",))
                            return

                        def step_cb(name, detail):
                            q.put(("step", name, detail))

                        def progress_cb(pct, msg):
                            q.put(("progress", pct, msg))

                        s, m = publisher.publish(
                            video_to_use,
                            title_text or "绮惧僵瑙嗛",
                            topics,
                            progress_callback=progress_cb,
                            step_callback=step_cb
                        )
                        result["success"] = s
                        result["message"] = m
                    except Exception as e:
                        result["success"] = False
                        result["message"] = str(e)
                    finally:
                        q.put(("done",))

                threading.Thread(target=_run_publish, daemon=True).start()

                current_step = f"鍑嗗鍙戝竷鍒皗platform_name}..."
                current_detail = "姝ｅ湪鍒濆鍖栧彂甯冩祦绋?
                while True:
                    try:
                        item = q.get(timeout=0.5)
                        if item[0] == "done":
                            break
                        elif item[0] == "step":
                            current_step = f"[{platform_name}] {item[1]}"
                            current_detail = item[2]
                            yield _publish_overlay_html(current_step, current_detail)
                        elif item[0] == "progress":
                            pct, msg = item[1], item[2]
                            progress(pct / 100, desc=f"[{platform_name}] {msg}")
                            yield _publish_overlay_html(f"[{platform_name}] {msg}", f"杩涘害 {pct}%")
                    except _queue.Empty:
                        yield _publish_overlay_html(current_step, current_detail)

                all_results.append((platform_name, result["success"], result["message"]))

            # 鈹€鈹€ 姹囨€荤粨鏋?鈹€鈹€
            result_parts = []
            has_error = False
            for pname, success, msg in all_results:
                if success:
                    result_parts.append(f"鉁?{pname}锛歿msg}")
                else:
                    has_error = True
                    if "chromedriver" in msg.lower() or "chrome" in msg.lower():
                        result_parts.append(f"鉂?{pname}锛欳hrome 娴忚鍣ㄩ┍鍔ㄩ棶棰?)
                    else:
                        result_parts.append(f"鉂?{pname}锛歿msg[:150]}")

            result_html = "<br>".join(result_parts)
            if video_type:
                result_html += f"<br><br>鍙戝竷鐨勮棰戯細{video_type}"

            if has_error:
                yield _hint_html("warning", result_html)
            else:
                yield _hint_html("ok", result_html)

        douyin_btn.click(_do_platform_publish,
            inputs=[bgm_video, sub_video, output_video, douyin_title, douyin_topics, publish_platforms],
            outputs=[douyin_hint])

        def _mix_bgm_entry(enable_val, types_val, current_selected_val, bgm_path_val, bgm_state_val, vol_val, sub_vid, out_vid,
                          # 淇濆瓨闇€瑕佺殑鍙傛暟
                          inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                          avatar_sel, aud_for_ls, out_aud,
                          sub_txt,
                          sub_fnt, sub_sz, sub_ps, sub_ps_off,
                          sub_col, sub_hi, sub_out, sub_out_sz,
                          sub_bg_col, sub_bg_op,
                          sub_kw_en, sub_hi_sc, sub_kw_txt,
                          sub_title_txt, sub_title_txt2,
                          douyin_title_val, douyin_topics_val,
                          pip_prompt_val,
                          progress=gr.Progress()):
            if not enable_val:
                raise gr.Error("璇峰厛鍚敤鑳屾櫙闊充箰")

            selected_label = ""
            state_path = ""
            state_title = ""
            if isinstance(bgm_state_val, dict):
                state_path = (bgm_state_val.get("path") or "").strip()
                state_title = (bgm_state_val.get("title") or "").strip()

            # 浼樺厛澶嶇敤 State 涓殑宸查€夐煶涔愶紙閬垮厤閲嶅鐐瑰嚮鏃舵崲姝岋級
            if state_path and os.path.exists(state_path):
                bgm_path_val = state_path
                selected_label = state_title
            else:
                # 鍏舵澶嶇敤 textbox 閲屽凡鏈夌殑鏈湴璺緞
                if isinstance(bgm_path_val, str):
                    bgm_path_val = bgm_path_val.strip()
                else:
                    bgm_path_val = ""

                if bgm_path_val and os.path.exists(bgm_path_val):
                    selected_label = (current_selected_val or "").strip()
                else:
                    _, bgm_path_val, selected_label = prepare_random_bgm_and_download(types_val, progress=progress)

            base_video = None
            if sub_vid and isinstance(sub_vid, str) and os.path.exists(sub_vid):
                base_video = sub_vid
            elif out_vid and isinstance(out_vid, str) and os.path.exists(out_vid):
                base_video = out_vid
            else:
                # 鍏煎 gradio dict
                for v in (sub_vid, out_vid):
                    if isinstance(v, dict):
                        p = (v.get("video") or {}).get("path") or v.get("path") or v.get("value")
                        if p and os.path.exists(p):
                            base_video = p
                            break
            if not base_video:
                raise gr.Error("璇峰厛鐢熸垚瑙嗛锛堟楠?鎴栨楠?锛?)
            out = mix_bgm_into_video(base_video, bgm_path_val, float(vol_val or 1.0), progress=progress)
            hint = _hint_html("ok", "鑳屾櫙闊充箰宸插悎鎴愬埌瑙嗛")
            if selected_label:
                hint = _hint_html("ok", f"宸茶嚜鍔ㄩ€夋嫨骞跺悎鎴怋GM锛歿selected_label}")
            shown = (selected_label or (current_selected_val or "")).strip()
            new_state = {"path": bgm_path_val, "title": shown}

            # 淇濆瓨宸ヤ綔鍙扮姸鎬?
            try:
                save_hint, dropdown_update = _auto_save_workspace(
                    inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                    avatar_sel, aud_for_ls, aud_for_ls, out_vid,
                    sub_txt, sub_vid,
                    sub_fnt, sub_sz, sub_ps, sub_ps_off,
                    sub_col, sub_hi, sub_out, sub_out_sz,
                    sub_bg_col, sub_bg_op,
                    sub_kw_en, sub_hi_sc, sub_kw_txt,
                    douyin_title_val=douyin_title_val, douyin_topics_val=douyin_topics_val,
                    sub_title_text_val=sub_title_txt,
                    sub_title_text2_val=sub_title_txt2,
                    pip_prompt_val=pip_prompt_val
                )
            except Exception as e:
                print(f"[BGM娣烽煶] 淇濆瓨宸ヤ綔鍙板け璐? {e}")
                traceback.print_exc()
                save_hint = _hint_html("error", f"淇濆瓨宸ヤ綔鍙板け璐? {e}")
                dropdown_update = gr.update()

            return (
                out,
                hint,
                gr.update(value=shown),
                gr.update(value=bgm_path_val),
                gr.update(value=bgm_path_val, visible=True),
                new_state,
                save_hint,
                dropdown_update,
            )

        def _change_bgm(types_val, bgm_state_val, progress=gr.Progress()):
            cur_path = ""
            cur_title = ""
            if isinstance(bgm_state_val, dict):
                cur_path = (bgm_state_val.get("path") or "").strip()
                cur_title = (bgm_state_val.get("title") or "").strip()

            # 灏介噺閬垮厤閲嶅閫夊埌鍚屼竴棣?
            last_err = None
            for _ in range(8):
                try:
                    item, local_path, shown = prepare_random_bgm_and_download(types_val, progress=progress)
                    if local_path and cur_path and os.path.exists(cur_path) and os.path.abspath(local_path) == os.path.abspath(cur_path):
                        continue
                    if shown and cur_title and shown.strip() == cur_title.strip():
                        continue
                    new_state = {"path": local_path, "title": shown}
                    return (
                        gr.update(value=shown),
                        gr.update(value=local_path),
                        gr.update(value=local_path, visible=True),
                        _hint_html("ok", f"宸叉洿鎹GM锛歿shown}"),  # 绉婚櫎浜嗏渽锛宊hint_html浼氳嚜鍔ㄦ坊鍔?
                        new_state,
                    )
                except Exception as e:
                    last_err = e
                    continue
            raise gr.Error(f"鏇存崲BGM澶辫触: {last_err}")
        
        def _use_custom_bgm(custom_audio_path):
            """浣跨敤鑷畾涔変笂浼犵殑BGM"""
            if not custom_audio_path or not os.path.exists(custom_audio_path):
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    _hint_html("warning", "璇峰厛涓婁紶鑷畾涔塀GM鏂囦欢"),
                    gr.update()
                )
            
            # 澶嶅埗鍒癇GM缂撳瓨鐩綍
            import shutil
            filename = os.path.basename(custom_audio_path)
            cache_path = _safe_bgm_cache_path(filename)
            
            try:
                shutil.copy2(custom_audio_path, cache_path)
                new_state = {"path": cache_path, "title": f"鑷畾涔夛細{filename}"}
                return (
                    gr.update(value=f"鑷畾涔夛細{filename}"),
                    gr.update(value=cache_path),
                    gr.update(value=cache_path, visible=True),
                    _hint_html("ok", f"宸蹭娇鐢ㄨ嚜瀹氫箟BGM锛歿filename}"),
                    new_state,
                )
            except Exception as e:
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    _hint_html("error", f"澶嶅埗BGM鏂囦欢澶辫触锛歿e}"),
                    gr.update()
                )

        bgm_change_btn.click(
            _change_bgm,
            inputs=[bgm_types, bgm_state],
            outputs=[bgm_selected, bgm_path_hidden, bgm_audio_preview, bgm_hint, bgm_state]
        )
        
        # 鑷畾涔塀GM涓婁紶鎸夐挳
        bgm_custom_btn.upload(
            _use_custom_bgm,
            inputs=[bgm_custom_btn],
            outputs=[bgm_selected, bgm_path_hidden, bgm_audio_preview, bgm_hint, bgm_state]
        )
        
        # BGM鍚敤/绂佺敤锛堜笉鍐嶉渶瑕佹樉绀?闅愯棌鑷畾涔変笂浼狅紝鎸夐挳濮嬬粓鍙锛?

        bgm_mix_btn.click(
            _mix_bgm_entry,
            inputs=[bgm_enable, bgm_types, bgm_selected, bgm_path_hidden, bgm_state, bgm_volume, sub_video, output_video,
                   # 淇濆瓨闇€瑕佺殑鍙傛暟
                   input_text, prompt_audio, voice_select, audio_mode, direct_audio_upload,
                   avatar_select, audio_for_ls, output_audio,
                   sub_text,
                   sub_font, sub_size, sub_pos, sub_pos_offset,
                   sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                   sub_bg_color, sub_bg_opacity,
                   sub_kw_enable, sub_hi_scale, sub_kw_text,
                   sub_title_text, sub_title_text2,
                   douyin_title, douyin_topics,
                   pip_prompt],
            outputs=[bgm_video, bgm_hint, bgm_selected, bgm_path_hidden, bgm_audio_preview, bgm_state,
                    workspace_record_hint, workspace_record_dropdown]
        )

        # 瑙嗛鍚堟垚
        def ls_wrap(avatar_name, auto_a, input_txt, quality_name="鈿栵笍 鏍囧噯",
                    heygem_mode_val="馃捇 鏈湴鐗?, progress=gr.Progress()):
            # 璋冭瘯鏃ュ織
            safe_print(f"[DEBUG] ls_wrap 寮€濮嬫墽琛?)
            safe_print(f"[DEBUG] avatar_name={avatar_name}, auto_a={auto_a}")
            safe_print(f"[DEBUG] heygem_mode_val={heygem_mode_val}")

            # 鎶婃暟瀛椾汉鍚嶈浆鎹㈡垚鏂囦欢璺緞
            video = None
            if _LIBS_OK and avatar_name and not avatar_name.startswith("锛?):
                video = _av.get_path(avatar_name)
            if not video:
                if not avatar_name or avatar_name.startswith("锛?):
                    safe_print(f"[DEBUG] 閿欒锛氭湭閫夋嫨鏁板瓧浜?)
                    raise gr.Error("璇峰厛鍦ㄦ楠?宸︿晶閫夋嫨涓€涓暟瀛椾汉")
                else:
                    safe_print(f"[DEBUG] 閿欒锛氭暟瀛椾汉鏂囦欢涓嶅瓨鍦?)
                    raise gr.Error(f"鏁板瓧浜?'{avatar_name}' 鐨勮棰戞枃浠朵笉瀛樺湪锛岃閲嶆柊娣诲姞璇ユ暟瀛椾汉")
            audio  = auto_a
            if not audio or not os.path.exists(str(audio)):
                safe_print(f"[DEBUG] 閿欒锛氶煶棰戞枃浠朵笉瀛樺湪")
                raise gr.Error("闊抽鏂囦欢涓嶅瓨鍦紝璇峰厛鍦ㄦ楠?鐢熸垚鎴栦笂浼犻煶棰戯紝鍐嶇偣鍑诲悎鎴?)
            preset = QUALITY_PRESETS.get(quality_name, QUALITY_PRESETS["鈿栵笍 鏍囧噯"])
            q      = _queue.Queue()
            result = {"out": None, "err": None}

            def _detail_cb(html):
                q.put(("detail", html))

            def _run():
                try:
                    out, _ = run_heygem_auto(video, audio, progress, detail_cb=_detail_cb,
                                             steps=preset.get("inference_steps", 12),
                                             if_gfpgan=False,
                                             heygem_mode=heygem_mode_val)
                    result["out"] = out
                except Exception as e:
                    result["err"] = e
                finally:
                    q.put(("done",))

            threading.Thread(target=_run, daemon=True).start()

            # 鍒濆灞曠ず锛氱敤鎴峰彲鐞嗚В鐨勯樁娈佃繘搴﹀崱鐗?
            _t0 = time.time()
            _last_detail = _dual_progress_html("鍑嗗涓?, 5, "鍒濆鍖?, 0, 0)
            yield gr.update(), gr.update(value=_last_detail, visible=True)

            while True:
                try:
                    item = q.get(timeout=0.3)
                    if item[0] == "done":
                        break
                    elif item[0] == "detail":
                        _last_detail = item[1]
                        yield gr.update(), gr.update(value=_last_detail, visible=True)
                except _queue.Empty:
                    # 瓒呮椂鏃朵繚鎸佷笂涓€娆＄殑杩涘害鍐呭涓嶅彉锛屼笉瑕嗙洊 detail_cb 鐨勮緭鍑?
                    yield gr.update(), gr.update(value=_last_detail, visible=True)

            if result["err"]:
                yield gr.update(), gr.update(value=_dual_progress_html("鍑洪敊", 0, "澶辫触", 0, int(time.time() - _t0)), visible=True)
                raise gr.Error(str(result["err"]))

            out      = result["out"]
            
            # 璋冭瘯杈撳嚭
            debug_file = os.path.join(OUTPUT_DIR, "debug_ls_wrap.txt")
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ls_wrap 瀹屾垚\n")
                f.write(f"  out type: {type(out)}\n")
                f.write(f"  out value: {out}\n")
            
            try:
                ps = (
                    "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
                    "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom,ContentType=WindowsRuntime]|Out-Null;"
                    "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(2);"
                    "$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('缁囨ⅵAI 鈥?鍚堟垚瀹屾垚'))|Out-Null;"
                    "$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('瑙嗛鍚堟垚宸插畬鎴愶紒'))|Out-Null;"
                    "$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
                    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('缁囨ⅵAI').Show($n);"
                )
                subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                                 creationflags=subprocess.CREATE_NO_WINDOW,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            # 瑙嗛鍚堟垚瀹屾垚鍚庢樉绀烘姈闊冲彂甯冨尯鍩燂紝骞惰嚜鍔ㄥ～鍏呮爣棰?
            # 杩斿洖锛氳棰戣矾寰勶紙瀛楃涓诧級銆佽鎯?
            # 娉ㄦ剰锛氱涓€涓繑鍥炲€兼槸瑙嗛璺緞瀛楃涓诧紝涓嶆槸 gr.update 瀵硅薄
            yield out, gr.update(value=_dual_progress_html("鉁?瀹屾垚", 100, "鍏ㄩ儴瀹屾垚", 100, int(time.time() - _t0)), visible=True)

        # 瑙嗛鍚堟垚鎸夐挳鐐瑰嚮 - 鐩存帴鍦ㄥ畬鎴愬悗淇濆瓨
        def video_and_save(avatar_sel, aud_for_ls, inp_txt, quality_name, heygem_mode_val,
                          pip_enabled, pip_mode_val, pip_prompt_val,
                          pip_local_val, pip_interval_val, pip_clip_dur_val,
                          # 淇濆瓨闇€瑕佺殑鍏朵粬鍙傛暟
                          prmt_aud, voice_sel, audio_mode_val, direct_aud,
                          out_aud, sub_txt, sub_vid,
                          sub_fnt, sub_sz, sub_ps, sub_ps_off,
                          sub_col, sub_hi, sub_out, sub_out_sz,
                          sub_bg_col, sub_bg_op,
                          sub_kw_en, sub_hi_sc, sub_kw_txt,
                          sub_title_txt, sub_title_txt2,
                          douyin_title_val, douyin_topics_val,
                          progress=gr.Progress()):
            """鍚堟垚瑙嗛骞惰嚜鍔ㄤ繚瀛樺伐浣滃彴鐘舵€?""
            # 璋冭瘯鏃ュ織
            safe_print(f"[DEBUG] video_and_save 寮€濮嬫墽琛?)
            safe_print(f"[DEBUG] avatar_sel={avatar_sel}, aud_for_ls={aud_for_ls}")
            safe_print(f"[DEBUG] heygem_mode_val={heygem_mode_val}")

            # 寮€濮嬫椂绂佺敤鎸夐挳锛岄槻姝㈤噸澶嶇偣鍑?
            yield gr.update(), gr.update(), gr.update(), gr.update(), gr.update(interactive=False)

            try:
                final_result = None
                for result in ls_wrap(avatar_sel, aud_for_ls, inp_txt, quality_name=quality_name,
                                     heygem_mode_val=heygem_mode_val, progress=progress):
                    yield result + (gr.update(), gr.update(), gr.update(interactive=False))
                    final_result = result
            
                if final_result:
                    video_path, ls_detail = final_result

                    # 鈹€鈹€ 鐢讳腑鐢诲鐞?鈹€鈹€
                    # 鍙湁鍦ㄥ嬀閫夌敾涓敾涓旀湁鏈夋晥鎻愮ず璇嶆垨绱犳潗鏃舵墠澶勭悊
                    should_process_pip = False
                    if pip_enabled and video_path and os.path.exists(str(video_path)):
                        is_online = ("鍦ㄧ嚎" in str(pip_mode_val))
                        if is_online:
                            # 鍦ㄧ嚎妯″紡锛氶渶瑕佹湁鎻愮ず璇?
                            should_process_pip = pip_prompt_val and pip_prompt_val.strip()
                        else:
                            # 鏈湴妯″紡锛氶渶瑕佹湁涓婁紶鐨勭礌鏉?
                            if isinstance(pip_local_val, list):
                                should_process_pip = any(hasattr(f, 'name') or os.path.exists(str(f)) for f in pip_local_val)
                            elif pip_local_val:
                                should_process_pip = True

                    if should_process_pip:
                        try:
                            # 绛夊緟瑙嗛鏂囦欢瀹屽叏鍐欏叆锛堟渶澶氱瓑寰?绉掞級
                            import time as _wait_time
                            for _ in range(10):
                                if os.path.exists(str(video_path)) and os.path.getsize(str(video_path)) > 1024:
                                    _wait_time.sleep(0.5)  # 鍐嶇瓑寰?.5绉掔‘淇濇枃浠跺畬鍏ㄥ啓鍏?
                                    break
                                _wait_time.sleep(0.5)

                            yield gr.update(), gr.update(
                                value='<div style="display:flex;align-items:center;gap:10px;padding:12px 16px;'
                                      'background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;">'
                                      '<div style="width:18px;height:18px;border:2.5px solid #bae6fd;'
                                      'border-top-color:#0ea5e9;border-radius:50%;'
                                      'animation:zdai-spin .7s linear infinite;flex-shrink:0;"></div>'
                                      '<span style="font-size:13px;color:#0369a1;font-weight:600;">'
                                      '馃柤 姝ｅ湪澶勭悊鐢讳腑鐢绘浛鎹⑩€?/span>'
                                      '<style>@keyframes zdai-spin{to{transform:rotate(360deg)}}</style></div>',
                                visible=True), gr.update(), gr.update(), gr.update(interactive=False)

                            is_online = ("鍦ㄧ嚎" in str(pip_mode_val))
                            pip_result = ""
                            if is_online:
                                if pip_prompt_val and pip_prompt_val.strip():
                                    prompts_list = [_pip_force_chinese_person(p.strip()) for p in pip_prompt_val.strip().split('\n') if p.strip()]
                                    if not prompts_list:
                                        prompts_list = [_pip_force_chinese_person(pip_prompt_val.strip())]

                                    # 浣跨敤 TextExtractor 杩炴帴鐢熸垚鐢讳腑鐢?
                                    extractor = get_text_extractor()
                                    if len(prompts_list) == 1:
                                        # 鍗曚釜鎻愮ず璇?- 鏆備笉鏀寔鍚堟垚
                                        pip_result = _pip_ws.generate_pip_via_extractor(
                                            prompts_list[0],
                                            extractor,
                                            progress_cb=lambda pct, msg: safe_print(f"[PIP] {pct:.0%} {msg}")
                                        )
                                    else:
                                        # 澶氫釜鎻愮ず璇嶏紝鎵归噺鐢熸垚骞跺悎鎴?
                                        pip_result = _pip_ws.generate_and_compose_pips(
                                            str(video_path),
                                            prompts_list,
                                            extractor,
                                            clip_duration=5.0,
                                            progress_cb=lambda pct, msg: safe_print(f"[PIP] {pct:.0%} {msg}")
                                        )
                                else:
                                    safe_print("[PIP] 鍦ㄧ嚎妯″紡浣嗘棤鎻愮ず璇嶏紝璺宠繃鐢讳腑鐢?)
                            else:
                                local_paths = []
                                if isinstance(pip_local_val, list):
                                    for f in pip_local_val:
                                        p = f.name if hasattr(f, 'name') else str(f)
                                        if p and os.path.exists(p):
                                            local_paths.append(p)
                                elif pip_local_val:
                                    p = pip_local_val.name if hasattr(pip_local_val, 'name') else str(pip_local_val)
                                    if p and os.path.exists(p):
                                        local_paths.append(p)
                                if local_paths:
                                    pip_result = _pip.apply_pip_local(
                                        str(video_path), local_paths,
                                        interval=float(pip_interval_val),
                                        clip_duration=float(pip_clip_dur_val),
                                        progress_cb=lambda pct, msg: safe_print(f"[PIP] {pct:.0%} {msg}")
                                    )
                                else:
                                    safe_print("[PIP] 鏈湴妯″紡浣嗘棤鏈夋晥绱犳潗锛岃烦杩囩敾涓敾")

                            if pip_result and os.path.exists(pip_result):
                                safe_print(f"[PIP] 鐢讳腑鐢诲鐞嗗畬鎴? {pip_result}")
                                video_path = pip_result
                            else:
                                safe_print("[PIP] 鐢讳腑鐢诲鐞嗘湭浜у嚭缁撴灉")
                        except Exception as e:
                            safe_print(f"[PIP] 鐢讳腑鐢诲鐞嗗け璐ワ紙涓嶅奖鍝嶈棰戣緭鍑猴級: {e}")
                            traceback.print_exc()

                # 璋冭瘯杈撳嚭
                debug_file = os.path.join(OUTPUT_DIR, "debug_video_save.txt")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] video_and_save 淇濆瓨鍓峔n")
                    f.write(f"  video_path type: {type(video_path)}\n")
                    f.write(f"  video_path value: {video_path}\n")
                
                # 淇濆瓨宸ヤ綔鍙扮姸鎬?
                # 娉ㄦ剰锛氳繖閲屼紶閫掔殑 audio_for_ls 鏄疄闄呬娇鐢ㄧ殑闊抽锛宱utput_audio 涔熷簲璇ユ槸鍚屼竴涓?
                hint_msg, dropdown_update = _auto_save_workspace(
                    inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                    avatar_sel, aud_for_ls, aud_for_ls, video_path,
                    sub_txt, sub_vid,
                    sub_fnt, sub_sz, sub_ps, sub_ps_off,
                    sub_col, sub_hi, sub_out, sub_out_sz,
                    sub_bg_col, sub_bg_op,
                    sub_kw_en, sub_hi_sc, sub_kw_txt,
                    douyin_title_val=douyin_title_val, douyin_topics_val=douyin_topics_val,
                    sub_title_text_val=sub_title_txt,
                    sub_title_text2_val=sub_title_txt2,
                    pip_prompt_val=pip_prompt_val
                )
                
                # 鏈€鍚庝竴娆?yield锛屽寘鍚繚瀛樼粨鏋滃苟閲嶆柊鍚敤鎸夐挳
                # 娉ㄦ剰锛氱涓€涓€奸渶瑕佹槸瑙嗛璺緞锛孏radio 浼氳嚜鍔ㄥ鐞?
                yield video_path, ls_detail, hint_msg, dropdown_update, gr.update(interactive=True)
            except Exception as e:
                # 寮傚父鏃朵篃瑕侀噸鏂板惎鐢ㄦ寜閽紙鍚﹀垯浼氬崱姝伙級
                err_hint = _hint_html("error", f"鍚堟垚澶辫触锛歿e}")
                yield gr.update(), gr.update(), gr.update(value=err_hint, visible=True), gr.update(), gr.update(interactive=True)
                return
        
        ls_btn.click(
            video_and_save,
            inputs=[
                avatar_select, audio_for_ls, input_text, quality_preset, heygem_mode_radio,
                pip_enable, pip_mode, pip_prompt, pip_local_files,
                pip_interval, pip_clip_dur,
                # 淇濆瓨闇€瑕佺殑鍙傛暟
                prompt_audio, voice_select, audio_mode, direct_audio_upload,
                output_audio, sub_text, sub_video,
                sub_font, sub_size, sub_pos, sub_pos_offset,
                sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                sub_bg_color, sub_bg_opacity,
                sub_kw_enable, sub_hi_scale, sub_kw_text,
                sub_title_text, sub_title_text2,
                douyin_title, douyin_topics
            ],
            outputs=[output_video, ls_detail_html,
                    workspace_record_hint, workspace_record_dropdown, ls_btn])

        # 鍚堟垚妯″紡鍒囨崲锛氬湪绾跨増闅愯棌璐ㄩ噺閫夐」
        heygem_mode_radio.change(
            lambda m: gr.update(visible=("鏈湴" in m)),
            inputs=[heygem_mode_radio],
            outputs=[quality_group])

        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
        #  宸ヤ綔鍙拌褰曚簨浠剁粦瀹?
        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
        
        # 鍒锋柊宸ヤ綔鍙拌褰曞垪琛?
        workspace_refresh_btn.click(
            lambda: gr.update(choices=_get_workspace_record_choices()),
            outputs=[workspace_record_dropdown])
        
        # 娓呯┖鎵€鏈夊伐浣滃彴璁板綍
        workspace_clear_btn.click(
            _clear_workspace_records,
            outputs=[workspace_record_dropdown, workspace_record_hint])
        
        # 鎭㈠宸ヤ綔鍙拌褰曪紙閫氳繃涓嬫媺妗嗛€夋嫨锛?
        workspace_restore_btn.click(
            _restore_workspace,
            inputs=[workspace_record_dropdown],
            outputs=[
                input_text, prompt_audio, voice_select, audio_mode, direct_audio_upload,
                avatar_select, audio_for_ls, output_audio, output_video,
                sub_text, sub_video,
                sub_font, sub_size, sub_pos, sub_pos_offset,
                sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                sub_bg_color, sub_bg_opacity,
                sub_kw_enable, sub_hi_scale, sub_kw_text,
                sub_title_text, sub_title_text2,
                douyin_title, douyin_topics,
                pip_enable, pip_mode, pip_prompt, pip_interval, pip_clip_dur,
                workspace_record_hint
            ])
        
        # 鍒犻櫎宸ヤ綔鍙拌褰曪紙閫氳繃涓嬫媺妗嗛€夋嫨锛?
        workspace_delete_btn.click(
            _delete_workspace_record_by_dropdown,
            inputs=[workspace_record_dropdown],
            outputs=[workspace_record_dropdown, workspace_record_hint])

        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
        #  鏂囨鎻愬彇浜嬩欢缁戝畾
        # 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
        
        def _do_extract_text(url_or_content, progress=gr.Progress()):
            """鎻愬彇鏂囨澶勭悊鍑芥暟"""
            if not url_or_content or not url_or_content.strip():
                return gr.update(), _hint_html("warning", "璇疯緭鍏ラ摼鎺ユ垨鍐呭")
            
            progress(0.2, desc="姝ｅ湪鎻愬彇鏂囨...")
            
            # 鑾峰彇鏂囨鎻愬彇鍣ㄥ疄渚?
            extractor = get_text_extractor()
            
            # 鍚姩WebSocket杩炴帴锛堝鏋滆繕娌″惎鍔級
            extractor.start()
            
            progress(0.4, desc="姝ｅ湪鍙戦€佽姹?..")
            
            # 鎻愬彇鏂囨
            success, result = extractor.extract_text(url_or_content.strip(), timeout=30)
            
            progress(1.0, desc="瀹屾垚")
            
            if success:
                # 鎻愬彇鎴愬姛锛岃繑鍥炲唴瀹瑰埌鍚堟垚鏂囨湰妗?
                return gr.update(value=result), '<div class="hint-ok">鉁?鏂囨鎻愬彇鎴愬姛锛?/div>'
            else:
                # 鎻愬彇澶辫触
                return gr.update(), f'<div class="hint-err">鉂?{result}</div>'
        
        extract_btn.click(
            _do_extract_text,
            inputs=[extract_input],
            outputs=[input_text, extract_hint]
        )

        # 椤甸潰鍔犺浇鏃惰嚜鍔ㄥ埛鏂板伐浣滃彴璁板綍鍒楄〃锛屽苟鍒濆鍖朩ebSocket杩炴帴
        def _init_load():
            # 鍚庡彴鍒濆鍖栨枃妗堟彁鍙栧櫒鐨刉ebSocket杩炴帴
            try:
                extractor = get_text_extractor()
                extractor.start()
                safe_print("[TextExtractor] WebSocket 杩炴帴宸插湪鍚庡彴鍒濆鍖?)
            except Exception as e:
                safe_print(f"[TextExtractor] 鍒濆鍖栧け璐? {e}")
            
            return gr.update(choices=_get_workspace_record_choices())
        
        app.load(_init_load, outputs=[workspace_record_dropdown])

        return app


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  鍗″瘑楠岃瘉 (Gradio 鍚姩鍓嶏紝鐢?tkinter 寮圭獥)
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
def _license_gate():
    """鍗″瘑楠岃瘉闂ㄦ帶銆傝繑鍥?True=閫氳繃, False=閫€鍑?""
    try:
        import lib_license as lic
    except ImportError:
        return True  # 娌℃湁 lib_license 妯″潡 鈫?璺宠繃楠岃瘉

    # 1) 妫€鏌ユ湰鍦板凡淇濆瓨鐨勫崱瀵?
    status, info = lic.check_saved_license()
    if status == "valid":
        ok, msg = lic.validate_online(info.get("license_key", ""))
        if ok:
            safe_print("[LICENSE] OK")
            return True
        safe_print(f"[LICENSE] online verify fail: {msg}")

    # 2) 闇€瑕佺櫥褰?鈥?寮瑰嚭 tkinter 瀵硅瘽妗?
    try:
        import tkinter as tk
        from PIL import Image, ImageTk, ImageDraw
    except ImportError:
        safe_print("[LICENSE] tkinter not available, skip")
        return True

    result = {"passed": False}
    root = tk.Tk()
    root.title("杞欢婵€娲?)
    root.resizable(False, False)
    root.configure(bg="#eef2ff")

    # 鏇村ぇ鐨勭獥鍙ｏ紝閬垮厤浠讳綍鎺т欢鎸ゅ帇
    w, h = 520, 560
    sx = (root.winfo_screenwidth() - w) // 2
    sy = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{sx}+{sy}")

    # 澶栧眰瀹瑰櫒锛堟ā鎷熷晢涓氬寲鍗＄墖闃村奖鏁堟灉锛?
    page = tk.Frame(root, bg="#eef2ff")
    page.pack(fill="both", expand=True, padx=18, pady=18)

    card_shadow = tk.Frame(page, bg="#dbe4ff")
    card_shadow.pack(fill="both", expand=True, padx=2, pady=2)

    card = tk.Frame(card_shadow, bg="#ffffff", relief="flat", bd=0)
    card.pack(fill="both", expand=True, padx=(0, 2), pady=(0, 2))

    # 椤堕儴鍝佺墝鍖?
    top = tk.Frame(card, bg="#ffffff")
    top.pack(fill="x", padx=20, pady=(18, 10))

    badge = tk.Label(
        top,
        text="PRO",
        font=("Segoe UI", 9, "bold"),
        bg="#eef2ff",
        fg="#4338ca",
        padx=10,
        pady=3
    )
    badge.pack(anchor="w")

    tk.Label(
        top,
        text="杞欢婵€娲荤櫥褰?,
        font=("Microsoft YaHei", 18, "bold"),
        bg="#ffffff",
        fg="#0f172a"
    ).pack(anchor="w", pady=(10, 4))

    tk.Label(
        top,
        text="璇疯緭鍏ユ湁鏁堝崱瀵嗗畬鎴愭縺娲汇€傞娆′娇鐢ㄥ墠闇€闃呰骞跺嬀閫夌敤鎴峰崗璁€?,
        font=("Microsoft YaHei", 9),
        bg="#ffffff",
        fg="#64748b",
        justify="left"
    ).pack(anchor="w")

    # 鍒嗛殧绾?
    tk.Frame(card, bg="#e5e7eb", height=1).pack(fill="x", padx=20, pady=(4, 12))

    body = tk.Frame(card, bg="#ffffff")
    body.pack(fill="both", expand=True, padx=20, pady=(0, 14))

    # 杈撳叆鍗＄墖
    input_card = tk.Frame(body, bg="#f8fafc", relief="solid", bd=1)
    input_card.pack(fill="x", pady=(0, 12))

    tk.Label(input_card, text="婵€娲诲崱瀵?, font=("Microsoft YaHei", 10, "bold"),
             bg="#f8fafc", fg="#1f2937").pack(anchor="w", padx=12, pady=(10, 6))
    tk.Label(input_card, text="寤鸿绮樿创瀹屾暣鍗″瘑锛岀郴缁熷皢杩涜鍦ㄧ嚎鏍￠獙銆?, font=("Microsoft YaHei", 8),
             bg="#f8fafc", fg="#94a3b8").pack(anchor="w", padx=12, pady=(0, 8))

    key_entry = tk.Entry(
        input_card,
        font=("Consolas", 12),
        relief="solid",
        bd=1,
        highlightthickness=1,
        highlightbackground="#d1d5db",
        highlightcolor="#4f46e5",
        bg="#ffffff",
        fg="#111827",
        insertbackground="#111827"
    )
    key_entry.pack(fill="x", padx=12, pady=(0, 12), ipady=10)
    if info.get("license_key"):
        key_entry.insert(0, info["license_key"])

    # 鍗忚鍖哄煙锛堟洿瑙勬暣锛?
    agreement_var = tk.BooleanVar(value=False)
    agreement_box = tk.Frame(body, bg="#fff7ed", relief="solid", bd=1)
    agreement_box.pack(fill="x", pady=(0, 12))

    tk.Label(
        agreement_box,
        text="鈿?浣跨敤鍓嶈鍏堥槄璇诲苟鍚屾剰銆婄敤鎴峰崗璁€嬩笌銆婇殣绉佸崗璁€?,
        font=("Microsoft YaHei", 9, "bold"),
        bg="#fff7ed",
        fg="#c2410c",
        anchor="w"
    ).pack(fill="x", padx=12, pady=(10, 6))

    tk.Label(
        agreement_box,
        text="鏈蒋浠朵粎鎻愪緵鎶€鏈緟鍔╄兘鍔涳紝涓嶅鍐呭鍚堣銆丄I鐢熸垚缁撴灉鍑嗙‘鎬с€佸钩鍙板鏍哥粨鏋溿€佽处鍙风姸鎬佸強缁忚惀缁撴灉浣滀换浣曚繚璇併€?,
        font=("Microsoft YaHei", 8),
        bg="#fff7ed",
        fg="#9a3412",
        justify="left",
        wraplength=450,
        anchor="w"
    ).pack(fill="x", padx=12, pady=(0, 8))

    agree_row = tk.Frame(agreement_box, bg="#fff7ed")
    agree_row.pack(fill="x", padx=10, pady=(0, 10))

    # 鑷畾涔夊嬀閫夋锛堥伩鍏嶇郴缁熼粯璁ゆ牱寮忚繃涓戯級
    def _toggle_agreement(*_):
        agreement_var.set(not bool(agreement_var.get()))

    chk_wrap = tk.Frame(agree_row, bg="#fff7ed")
    chk_wrap.pack(side="left", padx=(0, 8))

    chk_canvas = tk.Canvas(chk_wrap, width=18, height=18, bg="#fff7ed", highlightthickness=0, bd=0, cursor="hand2")
    chk_canvas.pack()

    def _draw_custom_checkbox(*_):
        chk_canvas.delete("all")
        checked = bool(agreement_var.get())
        border = "#4f46e5" if checked else "#cbd5e1"
        fill = "#4f46e5" if checked else "#ffffff"
        chk_canvas.create_rectangle(1, 1, 17, 17, outline=border, fill=fill, width=1)
        if checked:
            chk_canvas.create_line(4, 9, 8, 13, 14, 5, fill="#ffffff", width=2, capstyle="round", joinstyle="round")

    chk_canvas.bind("<Button-1>", _toggle_agreement)

    agree_text_label = tk.Label(agree_row, text="鎴戝凡闃呰骞跺悓鎰?, font=("Microsoft YaHei", 9), bg="#fff7ed", fg="#374151", cursor="hand2")
    agree_text_label.pack(side="left")
    agree_text_label.bind("<Button-1>", _toggle_agreement)

    def _render_md_to_tk(text_widget, md_text):
        """灏?Markdown 娓叉煋鍒?tkinter Text widget锛堝甫鏍煎紡鏍囩锛?""
        import re
        tw = text_widget
        tw.tag_configure("h1", font=("Microsoft YaHei", 16, "bold"), foreground="#0f172a",
                         spacing1=14, spacing3=6)
        tw.tag_configure("h2", font=("Microsoft YaHei", 13, "bold"), foreground="#1e293b",
                         spacing1=12, spacing3=4)
        tw.tag_configure("h3", font=("Microsoft YaHei", 11, "bold"), foreground="#334155",
                         spacing1=8, spacing3=3)
        tw.tag_configure("body", font=("Microsoft YaHei", 9), foreground="#475569",
                         spacing1=1, spacing3=1, lmargin1=8, lmargin2=8)
        tw.tag_configure("bold", font=("Microsoft YaHei", 9, "bold"), foreground="#1e293b")
        tw.tag_configure("li", font=("Microsoft YaHei", 9), foreground="#475569",
                         lmargin1=24, lmargin2=36, spacing1=1, spacing3=1)
        tw.tag_configure("hr", font=("Microsoft YaHei", 6), foreground="#cbd5e1",
                         spacing1=6, spacing3=6, justify="center")
        tw.tag_configure("sub_li", font=("Microsoft YaHei", 9), foreground="#64748b",
                         lmargin1=44, lmargin2=56, spacing1=1, spacing3=1)

        def _strip_inline(s):
            segments = []
            pos = 0
            for m in re.finditer(r'\*{2,3}(.+?)\*{2,3}', s):
                if m.start() > pos:
                    segments.append((s[pos:m.start()], False))
                segments.append((m.group(1), True))
                pos = m.end()
            if pos < len(s):
                segments.append((s[pos:], False))
            if not segments:
                segments = [(s, False)]
            return segments

        for line in md_text.splitlines():
            if re.match(r'^\s*[\*\-_]{3,}\s*$', line):
                tw.insert("end", "鈹? * 60 + "\n", "hr")
                continue
            m = re.match(r'^(#{1,6})\s+(.*)', line)
            if m:
                level = len(m.group(1))
                title = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', m.group(2).strip())
                tag = "h1" if level == 1 else ("h2" if level == 2 else "h3")
                tw.insert("end", title + "\n", tag)
                continue
            if not line.strip():
                tw.insert("end", "\n")
                continue
            li_m = re.match(r'^(\s*)([\*\-]|\d+[\.\)])\s+(.*)', line)
            if li_m:
                indent = len(li_m.group(1))
                content = li_m.group(3)
                tag = "sub_li" if indent >= 4 else "li"
                prefix = "  鈥?" if not li_m.group(2)[0].isdigit() else f"  {li_m.group(2)} "
                segs = _strip_inline(content)
                tw.insert("end", prefix)
                for txt, is_bold in segs:
                    tw.insert("end", txt, (tag, "bold") if is_bold else tag)
                tw.insert("end", "\n")
                continue
            segs = _strip_inline(line)
            for txt, is_bold in segs:
                tw.insert("end", txt, ("body", "bold") if is_bold else "body")
            tw.insert("end", "\n")

    def _load_agreement_text():
        default_text = "鐢ㄦ埛鍗忚鏂囦欢缂哄け锛岃灏?user_agreement.md 鏀惧湪绋嬪簭鍚岀洰褰曚笅銆?
        try:
            candidates = [
                os.path.join(BASE_DIR, "docs", "user_agreement.md"),
                os.path.join(BASE_DIR, "platform_ai_usage_agreement.txt"),
            ]
            for p in candidates:
                if p and os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            return content
        except Exception as e:
            return default_text + "\n\n璇诲彇閿欒锛?s" % (e,)
        return default_text

    def _load_privacy_text():
        default_text = "闅愮鍗忚鏂囦欢缂哄け锛岃灏?privacy_policy_total.md 鎴?privacy_policy.md 鏀惧湪绋嬪簭鍚岀洰褰曚笅銆?
        try:
            candidates = [
                os.path.join(BASE_DIR, "docs", "privacy_policy_total.md"),
                os.path.join(BASE_DIR, "docs", "privacy_policy.md"),
            ]
            for p in candidates:
                if p and os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            return content
        except Exception as e:
            return default_text + "\n\n璇诲彇閿欒锛?s" % (e,)
        return default_text

    def show_agreement():
        agreement_window = tk.Toplevel(root)
        agreement_window.title("鐢ㄦ埛鍗忚涓庨殣绉佸崗璁?)
        agreement_window.geometry("860x700")
        agreement_window.minsize(760, 620)
        agreement_window.configure(bg="#f1f5f9")
        agreement_window.transient(root)
        agreement_window.grab_set()

        try:
            agreement_window.update_idletasks()
            rw, rh = root.winfo_width(), root.winfo_height()
            rx, ry = root.winfo_x(), root.winfo_y()
            aw, ah = 860, 700
            ax = rx + max((rw - aw) // 2, 0)
            ay = ry + max((rh - ah) // 2, 0)
            agreement_window.geometry(f"{aw}x{ah}+{ax}+{ay}")
        except Exception:
            pass

        shell = tk.Frame(agreement_window, bg="#f1f5f9")
        shell.pack(fill="both", expand=True, padx=16, pady=16)

        header = tk.Frame(shell, bg="#ffffff", relief="solid", bd=1)
        header.pack(fill="x")
        tk.Label(header, text="鐢ㄦ埛鍗忚涓庨殣绉佸崗璁?, font=("Microsoft YaHei", 13, "bold"),
                 bg="#ffffff", fg="#0f172a").pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(header, text="璇峰畬鏁撮槄璇诲悗鍕鹃€夊悓鎰忋€傚缓璁敱瀹為檯杩愯惀璐熻矗浜洪槄璇诲苟纭銆?,
                 font=("Microsoft YaHei", 9), bg="#ffffff", fg="#64748b").pack(anchor="w", padx=14, pady=(0, 12))

        # 鈹€鈹€ Tab 鎸夐挳鏍?鈹€鈹€
        tab_bar = tk.Frame(shell, bg="#f1f5f9")
        tab_bar.pack(fill="x", pady=(10, 0))

        tab_btns = {}
        tab_frames = {}
        current_tab = [0]  # mutable for closure

        def switch_tab(idx):
            current_tab[0] = idx
            for i, (btn, frm) in enumerate(zip(tab_btns.values(), tab_frames.values())):
                if i == idx:
                    btn.config(bg="#4f46e5", fg="#ffffff", relief="flat")
                    frm.pack(fill="both", expand=True)
                else:
                    btn.config(bg="#e2e8f0", fg="#475569", relief="flat")
                    frm.pack_forget()

        tab_btns["user"] = tk.Button(tab_bar, text="馃搫 鐢ㄦ埛鍗忚", font=("Microsoft YaHei", 10, "bold"),
                                     bg="#4f46e5", fg="#ffffff", relief="flat", bd=0, padx=18, pady=6,
                                     cursor="hand2", command=lambda: switch_tab(0))
        tab_btns["user"].pack(side="left", padx=(0, 4))

        tab_btns["privacy"] = tk.Button(tab_bar, text="馃敀 闅愮鍗忚", font=("Microsoft YaHei", 10, "bold"),
                                        bg="#e2e8f0", fg="#475569", relief="flat", bd=0, padx=18, pady=6,
                                        cursor="hand2", command=lambda: switch_tab(1))
        tab_btns["privacy"].pack(side="left")

        # 鈹€鈹€ 鍐呭鍖?鈹€鈹€
        content_area = tk.Frame(shell, bg="#f1f5f9")
        content_area.pack(fill="both", expand=True, pady=8)

        def _make_text_panel(parent, md_content):
            border = tk.Frame(parent, bg="#cbd5e1", padx=1, pady=1)
            border.pack(fill="both", expand=True)
            container = tk.Frame(border, bg="#ffffff")
            container.pack(fill="both", expand=True)
            sb = tk.Scrollbar(container)
            sb.pack(side="right", fill="y")
            tw = tk.Text(container, wrap="word", yscrollcommand=sb.set,
                         font=("Microsoft YaHei", 9), padx=16, pady=14,
                         relief="flat", bd=0, bg="#ffffff", fg="#334155")
            tw.pack(side="left", fill="both", expand=True)
            sb.config(command=tw.yview)
            _render_md_to_tk(tw, md_content)
            tw.config(state="disabled")
            return border

        # 鐢ㄦ埛鍗忚 tab
        tab_frames["user"] = tk.Frame(content_area, bg="#f1f5f9")
        _make_text_panel(tab_frames["user"], _load_agreement_text())

        # 闅愮鍗忚 tab
        tab_frames["privacy"] = tk.Frame(content_area, bg="#f1f5f9")
        _make_text_panel(tab_frames["privacy"], _load_privacy_text())

        # 榛樿鏄剧ず绗竴涓?tab
        switch_tab(0)

        footer = tk.Frame(shell, bg="#f1f5f9")
        footer.pack(fill="x")
        tk.Label(footer, text="鎻愮ず锛氬嬀閫夊崗璁粎琛ㄧず鎮ㄥ凡鐭ユ倝骞舵壙璇哄悎瑙勪娇鐢紝涓嶄唬琛ㄥ钩鍙板鏍搁€氳繃鎴栬处鍙峰畨鍏ㄦ棤椋庨櫓銆?,
                 font=("Microsoft YaHei", 8), bg="#f1f5f9", fg="#64748b", wraplength=760, justify="left").pack(anchor="w", pady=(0, 10))
        tk.Button(
            footer, text="鍚屾剰", command=agreement_window.destroy,
            font=("Microsoft YaHei", 10, "bold"), bg="#4f46e5", fg="white",
            activebackground="#4338ca", activeforeground="white",
            relief="flat", cursor="hand2", bd=0, padx=20, pady=8
        ).pack(side="right")

    link_label = tk.Label(
        agree_row,
        text="銆婄敤鎴峰崗璁€嬩笌銆婇殣绉佸崗璁€?,
        font=("Microsoft YaHei", 9, "underline"),
        bg="#fff7ed",
        fg="#4338ca",
        cursor="hand2"
    )
    link_label.pack(side="left")
    link_label.bind("<Button-1>", lambda e: show_agreement())

    # 鐘舵€佹彁绀哄尯锛堝浐瀹氶珮搴﹀鍣紝閬垮厤鎸ゅ帇涓绘寜閽級
    msg_wrap = tk.Frame(body, bg="#ffffff", height=46)
    msg_wrap.pack(fill="x")
    msg_wrap.pack_propagate(False)
    msg_label = tk.Label(
        msg_wrap,
        text="",
        font=("Microsoft YaHei", 9),
        bg="#ffffff",
        fg="#ef4444",
        anchor="w",
        justify="left",
        wraplength=460
    )
    msg_label.pack(fill="x", pady=(6, 0))

    # 搴曢儴涓绘搷浣滃尯锛堟寜閽浐瀹氬ぇ楂樺害锛?
    action_box = tk.Frame(card, bg="#ffffff")
    action_box.pack(fill="x", padx=20, pady=(0, 18))
    tk.Frame(action_box, bg="#e5e7eb", height=1).pack(fill="x", pady=(0, 12))

    # 鑷畾涔変富鎸夐挳锛堜娇鐢≒IL鍒涘缓鍦嗚娓愬彉鎸夐挳锛?
    btn_state = {"enabled": False}
    
    # 鎸夐挳灏哄
    btn_width = 460
    btn_height = 56
    corner_radius = 10
    
    def create_rounded_gradient_button(width, height, radius, color1, color2, shadow=False):
        """鍒涘缓鍦嗚娓愬彉鎸夐挳鍥剧墖"""
        img_height = height + 6 if shadow else height
        img = Image.new('RGBA', (width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if shadow:
            # 缁樺埗闃村奖
            shadow_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_img)
            shadow_draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=(0, 0, 0, 30))
            img.paste(shadow_img, (2, 5), shadow_img)
        
        # 缁樺埗娓愬彉鑳屾櫙
        gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        for y in range(height):
            ratio = y / height
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            gradient_draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
        # 鍒涘缓鍦嗚钂欑増
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=255)
        
        # 搴旂敤鍦嗚钂欑増
        gradient.putalpha(mask)
        img.paste(gradient, (0, 0), gradient)
        
        return img
    
    # 绂佺敤鐘舵€侀鑹?(娣＄传鑹?
    disabled_color1 = (165, 180, 252)  # #a5b4fc
    disabled_color2 = (196, 181, 253)  # #c4b5fd
    
    # 鍚敤鐘舵€侀鑹?(绱壊娓愬彉)
    normal_color1 = (99, 102, 241)   # #6366f1
    normal_color2 = (124, 58, 237)   # #7c3aed
    
    # 鎮仠鐘舵€侀鑹?(鏇翠寒鐨勭传鑹?
    hover_color1 = (129, 140, 248)   # #818cf8
    hover_color2 = (139, 92, 246)    # #8b5cf6
    
    # 鐐瑰嚮鐘舵€侀鑹?(鏇存繁鐨勭传鑹?
    active_color1 = (79, 70, 229)    # #4f46e5
    active_color2 = (109, 40, 217)   # #6d28d9
    
    # 鍒涘缓鎸夐挳鍥剧墖
    btn_disabled_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, disabled_color1, disabled_color2, shadow=False)
    btn_normal_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, normal_color1, normal_color2, shadow=True)
    btn_hover_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, hover_color1, hover_color2, shadow=True)
    btn_active_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, active_color1, active_color2, shadow=False)
    
    # 杞崲涓篢kinter鍥剧墖
    btn_disabled_tk = ImageTk.PhotoImage(btn_disabled_img)
    btn_normal_tk = ImageTk.PhotoImage(btn_normal_img)
    btn_hover_tk = ImageTk.PhotoImage(btn_hover_img)
    btn_active_tk = ImageTk.PhotoImage(btn_active_img)
    
    # 鎸夐挳瀹瑰櫒
    btn_container = tk.Frame(action_box, bg="#ffffff", height=70)
    btn_container.pack(fill="x")
    btn_container.pack_propagate(False)
    
    btn_canvas = tk.Canvas(btn_container, bg="#ffffff", highlightthickness=0, height=70, width=btn_width)
    btn_canvas.pack()
    
    # 淇濇寔寮曠敤闃叉琚瀮鍦惧洖鏀?
    btn_canvas.btn_images = [btn_disabled_tk, btn_normal_tk, btn_hover_tk, btn_active_tk]
    
    # 鍦–anvas涓婄粯鍒舵寜閽儗鏅?
    btn_x, btn_y = 0, 5
    btn_bg_id = btn_canvas.create_image(btn_x, btn_y, image=btn_disabled_tk, anchor="nw", tags="btn_bg")
    
    # 缁樺埗鎸夐挳鏂囧瓧
    text_id = btn_canvas.create_text(
        btn_x + btn_width // 2,
        btn_y + btn_height // 2,
        text="馃殌  鐧诲綍鍚姩",
        font=("Microsoft YaHei", 15, "bold"),
        fill="#eef2ff",
        tags="btn_text"
    )
    
    # 鍒涘缓閫忔槑鐨勭偣鍑诲尯鍩?
    click_area = btn_canvas.create_rectangle(
        btn_x, btn_y, btn_x + btn_width, btn_y + btn_height,
        fill="", outline="", tags="click_area"
    )
    
    is_pressed = [False]
    
    def _btn_click(_e=None):
        if btn_state["enabled"]:
            _do_login()

    # 缁戝畾鐐瑰嚮浜嬩欢
    def _on_btn_enter(e):
        if btn_state["enabled"] and not is_pressed[0]:
            btn_canvas.itemconfig(btn_bg_id, image=btn_hover_tk)
        btn_canvas.config(cursor="hand2" if btn_state["enabled"] else "arrow")
    
    def _on_btn_leave(e):
        if btn_state["enabled"]:
            btn_canvas.itemconfig(btn_bg_id, image=btn_normal_tk)
        else:
            btn_canvas.itemconfig(btn_bg_id, image=btn_disabled_tk)
        btn_canvas.config(cursor="")
        is_pressed[0] = False
    
    def _on_btn_press(e):
        if btn_state["enabled"]:
            is_pressed[0] = True
            btn_canvas.itemconfig(btn_bg_id, image=btn_active_tk)
            btn_canvas.move(text_id, 0, 2)
    
    def _on_btn_release(e):
        if btn_state["enabled"]:
            is_pressed[0] = False
            btn_canvas.itemconfig(btn_bg_id, image=btn_hover_tk)
            btn_canvas.coords(text_id, btn_x + btn_width // 2, btn_y + btn_height // 2)
            _btn_click()
    
    # 缁戝畾浜嬩欢鍒扮偣鍑诲尯鍩熷拰鏂囧瓧
    for tag in ("click_area", "btn_text"):
        btn_canvas.tag_bind(tag, "<Enter>", _on_btn_enter)
        btn_canvas.tag_bind(tag, "<Leave>", _on_btn_leave)
        btn_canvas.tag_bind(tag, "<ButtonPress-1>", _on_btn_press)
        btn_canvas.tag_bind(tag, "<ButtonRelease-1>", _on_btn_release)
    
    subline = tk.Label(
        action_box,
        text="婵€娲诲嵆琛ㄧず鎮ㄧ悊瑙ｏ細杞欢鎻愪緵鎶€鏈兘鍔涳紝涓嶅骞冲彴瑙勫垯鍙樺寲銆佸鏍哥粨鏋溿€佸皝绂併€佺粡钀ユ崯澶辩瓑璐熻矗銆?,
        font=("Microsoft YaHei", 8),
        bg="#ffffff",
        fg="#94a3b8",
        wraplength=470,
        justify="left"
    )
    subline.pack(anchor="w", pady=(8, 0))

    def _set_btn_enabled(enabled: bool):
        btn_state["enabled"] = bool(enabled)
        if enabled:
            btn_canvas.itemconfig(btn_bg_id, image=btn_normal_tk)
            btn_canvas.itemconfig(text_id, fill="#ffffff")
        else:
            btn_canvas.itemconfig(btn_bg_id, image=btn_disabled_tk)
            btn_canvas.itemconfig(text_id, fill="#eef2ff")

    def _sync_login_btn(*_):
        try:
            _draw_custom_checkbox()
        except Exception:
            pass
        _set_btn_enabled(bool(agreement_var.get()))

    def _do_login():
        key = key_entry.get().strip()
        if not key:
            msg_label.config(text="璇疯緭鍏ュ崱瀵?, fg="#ef4444")
            return
        if not agreement_var.get():
            msg_label.config(text="璇峰厛闃呰骞跺嬀閫夈€婄敤鎴峰崗璁€嬩笌銆婇殣绉佸崗璁€?, fg="#ef4444")
            return

        msg_label.config(text="姝ｅ湪楠岃瘉鍗″瘑锛岃绋嶅€?..", fg="#4f46e5")
        root.update_idletasks()
        ok, msg = lic.validate_online(key)
        if ok:
            msg_label.config(text="婵€娲绘垚鍔燂紝姝ｅ湪杩涘叆绯荤粺...", fg="#16a34a")
            result["passed"] = True
            try:
                agreement_flag_file = os.path.join(BASE_DIR, ".platform_ai_agreement")
                with open(agreement_flag_file, "w", encoding="utf-8") as f:
                    f.write("agreed")
            except Exception:
                pass
            root.after(600, root.destroy)
        else:
            msg_label.config(text=str(msg), fg="#ef4444")

    def _entry_focus_in(e):
        try:
            key_entry.configure(highlightbackground="#4f46e5")
        except Exception:
            pass

    def _entry_focus_out(e):
        try:
            key_entry.configure(highlightbackground="#d1d5db")
        except Exception:
            pass

    key_entry.bind("<FocusIn>", _entry_focus_in)
    key_entry.bind("<FocusOut>", _entry_focus_out)

    try:
        _draw_custom_checkbox()
    except Exception:
        pass
    agreement_var.trace_add("write", _sync_login_btn)
    _set_btn_enabled(False)

    key_entry.bind("<Return>", lambda e: _do_login() if agreement_var.get() else msg_label.config(text="璇峰厛鍕鹃€夊苟鍚屾剰銆婄敤鎴峰崗璁€嬩笌銆婇殣绉佸崗璁€?, fg="#ef4444"))

    def _on_close():
        result["passed"] = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()
    return result["passed"]


# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
#  鍏ュ彛
# 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲
if __name__ == "__main__":
    # ========== 鍗曞疄渚嬫鏌?==========
    # 浣跨敤浜掓枼閿佺‘淇濆彧鏈変竴涓疄渚嬭繍琛岋紝绗簩娆″惎鍔ㄦ椂婵€娲荤涓€涓獥鍙?
    import ctypes
    import ctypes.wintypes

    # 鍒涘缓涓€涓敮涓€鐨勪簰鏂ラ攣鍚嶇О
    MUTEX_NAME = "Global\\ZhiMoAi_Shuzi_Unified_App_Mutex"
    WINDOW_TITLE_PATTERN = "鏅哄ⅷAI鏁板瓧浜?  # 绐楀彛鏍囬鍏抽敭璇?

    # Windows API 鍑芥暟
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32 = ctypes.WinDLL('user32', use_last_error=True)

    CreateMutexW = kernel32.CreateMutexW
    CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.wintypes.BOOL, ctypes.wintypes.LPCWSTR]
    CreateMutexW.restype = ctypes.wintypes.HANDLE

    GetLastError = kernel32.GetLastError
    GetLastError.restype = ctypes.wintypes.DWORD

    ERROR_ALREADY_EXISTS = 183

    # 灏濊瘯鍒涘缓浜掓枼閿?
    mutex_handle = CreateMutexW(None, False, MUTEX_NAME)

    if GetLastError() == ERROR_ALREADY_EXISTS:
        # 浜掓枼閿佸凡瀛樺湪锛岃鏄庣▼搴忓凡缁忓湪杩愯
        print("[INFO] 妫€娴嬪埌绋嬪簭宸插湪杩愯锛屾鍦ㄦ縺娲荤幇鏈夌獥鍙?..")

        # 灏濊瘯鏌ユ壘骞舵縺娲荤幇鏈夌獥鍙?
        try:
            # 瀹氫箟鍥炶皟鍑芥暟绫诲瀷
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                ctypes.wintypes.BOOL,
                ctypes.wintypes.HWND,
                ctypes.wintypes.LPARAM
            )

            # 瀛樺偍鎵惧埌鐨勭獥鍙ｅ彞鏌?
            found_hwnd = []

            def enum_windows_callback(hwnd, lParam):
                # 鑾峰彇绐楀彛鏍囬
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value

                    # 妫€鏌ユ槸鍚︽槸鎴戜滑鐨勭獥鍙ｏ紙鍖呭惈鍏抽敭璇嶆垨 Gradio 榛樿鏍囬锛?
                    if WINDOW_TITLE_PATTERN in title or "Gradio" in title:
                        # 妫€鏌ョ獥鍙ｆ槸鍚﹀彲瑙?
                        if user32.IsWindowVisible(hwnd):
                            print(f"[DEBUG] 鎵惧埌绐楀彛: {title}")
                            found_hwnd.append(hwnd)
                            return False  # 鍋滄鏋氫妇
                return True  # 缁х画鏋氫妇

            # 鏋氫妇鎵€鏈夐《灞傜獥鍙?
            callback = EnumWindowsProc(enum_windows_callback)
            user32.EnumWindows(callback, 0)

            if found_hwnd:
                hwnd = found_hwnd[0]

                # 濡傛灉绐楀彛鏈€灏忓寲锛屽厛鎭㈠
                SW_RESTORE = 9
                SW_SHOW = 5
                user32.ShowWindow(hwnd, SW_RESTORE)
                time.sleep(0.1)  # 绛夊緟绐楀彛鎭㈠
                user32.ShowWindow(hwnd, SW_SHOW)

                # 婵€娲荤獥鍙ｏ紙浣跨敤澶氱鏂规硶纭繚鎴愬姛锛?
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.SetActiveWindow(hwnd)

                print("[INFO] 鉁?宸叉縺娲荤幇鏈夌獥鍙?)
            else:
                print("[WARN] 鏈壘鍒扮幇鏈夌獥鍙ｏ紝浣嗙▼搴忓凡鍦ㄨ繍琛?)
                print("[INFO] 璇峰湪浠诲姟鏍忔垨绯荤粺鎵樼洏涓煡鎵剧▼搴忕獥鍙?)

        except Exception as e:
            print(f"[WARN] 婵€娲荤獥鍙ｅけ璐? {e}")
            import traceback
            traceback.print_exc()

        # 閫€鍑虹浜屼釜瀹炰緥
        sys.exit(0)

    # 绋嬪簭閫€鍑烘椂浼氳嚜鍔ㄩ噴鏀句簰鏂ラ攣
    # ========== 鍗曞疄渚嬫鏌ョ粨鏉?==========

    # 鍗″瘑楠岃瘉宸插湪 app_backend.py 涓畬鎴愶紝杩欓噷涓嶅啀閲嶅楠岃瘉
    # if not _license_gate():
    #     safe_print("[LICENSE] denied, exit")
    #     sys.exit(0)

    auto_load_model()
    try:
        # 鍦ㄧ嚎鐗堟棤闇€棰勭儹 HeyGem锛堣妭鐪佸惎鍔ㄦ椂闂?璧勬簮锛?
        if os.getenv('TTS_MODE', 'local') != 'online':
            _warmup_heygem()
    except Exception:
        pass
    app = build_ui()
    app.queue()
    for port in [7870, 7871, 7872, 7873, 7874]:
        try:
            app.launch(
                server_name="127.0.0.1",
                server_port=port,
                inbrowser=False,
                quiet=True,
                show_error=True,
                share=False,
                show_api=False,
                # 鈽?鍏抽敭锛氬厑璁?Gradio 闈欐€佹湇鍔¤闂?BASE_DIR锛坙ogo.jpg / 杞崲瑙嗛绛夛級
                allowed_paths=[BASE_DIR, OUTPUT_DIR,
                              os.path.join(BASE_DIR,"avatars"),
                              os.path.join(BASE_DIR,"voices"),
                              os.path.join(BASE_DIR,"fonts"),
                              os.path.join(BASE_DIR,"font_cache")],
            )
            break
        except OSError:
            continue

