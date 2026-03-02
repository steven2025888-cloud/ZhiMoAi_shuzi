# -*- coding: utf-8 -*-
import os
import sys
import time
import hashlib
import json
import traceback
import uuid
import subprocess
import threading
import queue as _queue
import shutil
import requests as _req
import gradio as gr
import asyncio
import ctypes
import base64
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

# ── 配置文件路径（优先 %LOCALAPPDATA%\ZhiMoAI\config.dat，用户不可见）──
_CONFIG_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ZhiMoAI')
_CONFIG_FILE = os.path.join(_CONFIG_DIR, 'config.dat')


def _read_config_lines(path):
    """读取 key=value 格式配置文件，返回 dict"""
    cfg = {}
    if not os.path.exists(path):
        return cfg
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                cfg[key.strip()] = value.strip()
    except Exception:
        pass
    return cfg


def _write_config(cfg: dict):
    """将 dict 写入 config.dat（%LOCALAPPDATA%\ZhiMoAI\）"""
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(_CONFIG_FILE, 'w', encoding='utf-8') as f:
            for k, v in cfg.items():
                f.write(f"{k}={v}\n")
    except Exception as e:
        print(f"[WARN] 保存配置失败: {e}")


def _update_config_key(key: str, value: str):
    """更新 config.dat 中单个键值"""
    cfg = _read_config_lines(_CONFIG_FILE)
    cfg[key] = value
    _write_config(cfg)


def _migrate_env_to_config():
    """首次运行时：如果旧 .env 文件存在，迁移到 config.dat"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        return
    if os.path.exists(_CONFIG_FILE):
        return  # 已经迁移过
    cfg = _read_config_lines(env_path)
    if cfg:
        _write_config(cfg)
        print(f"[CONFIG] 已将 .env 配置迁移到 {_CONFIG_FILE}")


# ── 加载配置 ──
def load_env_file():
    """加载配置到环境变量（优先 config.dat，兼容旧 .env）"""
    # 首次运行迁移
    _migrate_env_to_config()

    # 1) 读取 config.dat（主配置）
    cfg = _read_config_lines(_CONFIG_FILE)

    # 2) 读取 .env（开发覆盖，优先级更高）
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    dev_cfg = _read_config_lines(env_path)
    cfg.update(dev_cfg)

    # 3) 写入 os.environ
    for k, v in cfg.items():
        os.environ[k] = v

    # DPAPI 解密 LIPVOICE_SIGN
    if not os.getenv("LIPVOICE_SIGN"):
        enc = (os.getenv("LIPVOICE_SIGN_ENC") or "").strip()
        if enc:
            try:
                os.environ["LIPVOICE_SIGN"] = _dpapi_decrypt_text(enc)
            except Exception as _e:
                print(f"[WARN] LIPVOICE_SIGN_ENC 解密失败: {_e}")


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

# ── WebSocket 模块（用于提取文案功能）──
try:
    import websockets
    _WS_OK = True
except ImportError:
    _WS_OK = False
    print("[WARN] websockets 模块未安装，提取文案功能将不可用")

# ── 将 libs/ 加入模块搜索路径 ──
_LIBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
if _LIBS_DIR not in sys.path:
    sys.path.insert(0, _LIBS_DIR)

# ── 新功能模块（数字人 / 音色 / 字幕）──
try:
    import lib_avatar as _av
    import lib_voice  as _vc
    import lib_subtitle as _sub
    import lib_pip     as _pip
    import lib_pip_websocket as _pip_ws  # WebSocket 画中画模块
    _LIBS_OK = True
except Exception as _libs_err:
    _LIBS_OK = False
    import warnings
    warnings.warn(f"[扩展模块加载失败] {_libs_err}")
    # 创建安全存根，避免模块未加载时 NameError
    class _StubLib:
        def get_choices(self): return ["（模块未加载）"]
        def get_path(self, n): return None
        def render_gallery(self, *a, **kw): return '<div style="color:#dc2626;padding:12px;">⚠ 扩展模块加载失败，请检查 lib_avatar/lib_voice/lib_subtitle.py</div>'
        def add_avatar(self, *a): return False, "模块未加载"
        def del_avatar(self, *a): return False, "模块未加载"
        def add_voice(self, *a): return False, "模块未加载"
        def del_voice(self, *a): return False, "模块未加载"
        def get_font_choices(self): return ["默认字体"]
        def burn_subtitles(self, *a, **kw): raise RuntimeError("字幕模块未加载")
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

# ── 清除代理 ──
for _k in ('http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','all_proxy'):
    os.environ.pop(_k, None)
    os.environ[_k] = ''
os.environ['no_proxy'] = '127.0.0.1,localhost'
os.environ['NO_PROXY'] = '127.0.0.1,localhost'

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
PLATFORM_AGREEMENT_FILE = os.path.join(BASE_DIR, "platform_ai_usage_agreement.txt")
LEGACY_AGREEMENT_FILE = os.path.join(BASE_DIR, "platform_publish_agreement.txt")
DOUYIN_AGREEMENT_FILE = os.path.join(BASE_DIR, "docs", "user_agreement.md")  # 兼容旧版本
INDEXTTS_DIR   = os.path.join(BASE_DIR, "_internal_tts")
HEYGEM_DIR     = os.path.join(BASE_DIR, "heygem-win-50")
OUTPUT_DIR     = os.path.join(BASE_DIR, "unified_outputs")
WORKSPACE_RECORDS_FILE = os.path.join(OUTPUT_DIR, "workspace_records.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# BASE_DIR 已就绪，重新读取一次版本信息（允许 .env 开发覆盖）
try:
    APP_VERSION, APP_BUILD = get_app_version(BASE_DIR)
except Exception:
    pass

MUSIC_DATABASE_FILE = os.path.join(BASE_DIR, "data", "music_database.json")
BGM_CACHE_DIR = os.path.join(BASE_DIR, "bgm_cache")  # 独立的BGM缓存目录
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

# ── 视频合成质量预设 ──
QUALITY_PRESETS = {
    "⚡ 极快":   {"inference_steps": 6,  "guidance_scale": 1.0},
    "🚀 快速":   {"inference_steps": 8,  "guidance_scale": 1.0},
    "⚖️ 标准":   {"inference_steps": 12, "guidance_scale": 1.2},
    "✨ 高质量": {"inference_steps": 20, "guidance_scale": 1.5},
}

# ── TTS 合成速度预设（主要控制 num_beams 和 max_mel_tokens）──
TTS_SPEED_PRESETS = {
    "⚡ 极快":   {"num_beams": 1, "max_mel_tokens": 1200},
    "🚀 快速":   {"num_beams": 1, "max_mel_tokens": 1500},
    "⚖️ 标准":   {"num_beams": 2, "max_mel_tokens": 2000},
    "✨ 高质量": {"num_beams": 4, "max_mel_tokens": 2500},
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
APP_NAME = "织梦AI大模型"
APP_SUB  = "AI语音克隆 · 智能视频合成 · 专业级解决方案"


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
    stage = (stage or "处理中").strip()
    sub = f"用时 {int(elapsed_s)}s" if elapsed_s else ""
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
    """双进度条 HTML：总进度 + 当前步骤进度"""
    total_pct = max(0, min(100, int(total_pct or 0)))
    step_pct = max(0, min(100, int(step_pct or 0)))
    total_bar = max(2, total_pct)
    step_bar = max(2, step_pct)
    stage = (stage or "处理中").strip()
    step_label = (step_label or "").strip()
    sub = f"用时 {int(elapsed_s)}s" if elapsed_s else ""
    return (
        '<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
        'border:1.5px solid #6366f1;border-radius:12px;'
        'padding:14px 16px 12px;margin:0 0 10px;'
        'font-family:Microsoft YaHei,system-ui,sans-serif;'
        'box-shadow:0 4px 16px rgba(99,102,241,.18);">'
        # 总进度
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
        f'<span style="font-size:13px;font-weight:800;color:#e2e8f0;">📊 总进度</span>'
        f'<span style="margin-left:auto;font-size:14px;font-weight:900;color:#6366f1;">{total_pct}%</span>'
        '</div>'
        '<div style="background:rgba(99,102,241,.15);border-radius:6px;height:8px;overflow:hidden;margin-bottom:12px;">'
        f'<div style="height:100%;width:{total_bar}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:6px;transition:width .25s;"></div>'
        '</div>'
        # 步骤进度
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
        f'<span style="font-size:12px;font-weight:700;color:#94a3b8;">⚙️ {stage}{(" · " + step_label) if step_label else ""}</span>'
        f'<span style="margin-left:auto;font-size:12px;font-weight:800;color:#22d3ee;">{step_pct}%</span>'
        '</div>'
        '<div style="background:rgba(34,211,238,.12);border-radius:6px;height:6px;overflow:hidden;">'
        f'<div style="height:100%;width:{step_bar}%;background:linear-gradient(90deg,#22d3ee,#06b6d4);border-radius:6px;transition:width .25s;"></div>'
        '</div>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:8px;">{sub}</div>'
        '</div>'
    )


# 从统一接口读取版本信息（注意：BASE_DIR 在后面才赋值，这里先给安全默认值）
try:
    from app_version import get_app_version
    APP_VERSION, APP_BUILD = get_app_version(None)
except Exception as _e:
    APP_VERSION, APP_BUILD = ("2.3.9", 239)


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


# ══════════════════════════════════════════════════════════════
#  JS：注入全局逻辑（在 Gradio js= 参数中运行，页面加载后立即执行）
# ══════════════════════════════════════════════════════════════
# 从外部文件加载JS，并注入版本号
try:
    with open(os.path.join(BASE_DIR, "ui", "ui_init.js"), "r", encoding="utf-8") as f:
        INIT_JS = f.read()
        # 替换版本号占位符
        INIT_JS = INIT_JS.replace('{{APP_VERSION}}', APP_VERSION)
        INIT_JS = INIT_JS.replace('{{APP_BUILD}}', str(APP_BUILD))
except Exception as e:
    print(f"[WARNING] 无法加载 ui/ui_init.js: {e}")
    INIT_JS = "() => { console.log('[织梦AI] JS加载失败'); }"

# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
# 从外部文件加载CSS
try:
    with open(os.path.join(BASE_DIR, "ui", "ui_style.css"), "r", encoding="utf-8") as f:
        CUSTOM_CSS = f.read()
except Exception as e:
    print(f"[WARNING] 无法加载 ui/ui_style.css: {e}")
    CUSTOM_CSS = ""



# ══════════════════════════════════════════════════════════════
def auto_load_model():
    """根据 TTS 模式选择决定是否加载 IndexTTS2 模型"""
    global tts
    
    # 重新加载配置，确保获取最新的TTS_MODE
    load_env_file()
    
    # 读取 TTS 模式选择（local 或 online）
    tts_mode = os.getenv('TTS_MODE', 'local')
    safe_print(f"[MODEL] TTS 模式: {tts_mode}")
    
    # 如果是在线版，跳过模型加载
    if tts_mode == 'online':
        safe_print("[MODEL] 当前为在线版，跳过 IndexTTS2 模型加载")
        tts = None
        return
    
    # 本地版才加载模型
    safe_print("[MODEL] 当前为本地版，开始加载 IndexTTS2 模型...")
    
    model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
    if not os.path.exists(model_dir):
        safe_print("[ERR] model dir not found"); return
    original_cwd = os.getcwd()
    os.chdir(INDEXTTS_DIR)
    try:
        safe_print("[MODEL] 正在加载 IndexTTS2 声学模型...")
        
        # 检查CUDA是否可用
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        safe_print(f"[MODEL] PyTorch CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            safe_print(f"[MODEL] GPU设备: {torch.cuda.get_device_name(0)}")
            safe_print(f"[MODEL] CUDA版本: {torch.version.cuda}")
        else:
            safe_print("[MODEL] 警告：未检测到CUDA，将使用CPU（速度会很慢）")
        
        from indextts.infer_v2 import IndexTTS2
        tts = IndexTTS2(model_dir=model_dir,
                        cfg_path=os.path.join(model_dir, "config.yaml"), use_fp16=True)
        safe_print("[MODEL] 模型加载完成，正在预热引擎...")
        # 预热：触发一次推理内部初始化（CUDA图/JIT编译等），避免首次合成卡顿
        try:
            import tempfile, numpy as np
            _dummy_wav = os.path.join(OUTPUT_DIR, "_warmup.wav")
            # 找任意一个已有音色作为 prompt 进行预热
            _voice_meta = os.path.join(BASE_DIR, "voices", "meta.json")
            _prompt = None
            if os.path.exists(_voice_meta):
                import json as _json
                _vm = _json.load(open(_voice_meta, encoding='utf-8'))
                if _vm and os.path.exists(_vm[0].get("path","")):
                    _prompt = _vm[0]["path"]
            if _prompt:
                tts.infer(spk_audio_prompt=_prompt, text="你好。",
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
                safe_print("[MODEL] 引擎预热完成，首次合成将直接输出")
        except Exception as _we:
            safe_print("[MODEL] 预热跳过（无音色文件或预热失败）: " + str(_we))
        safe_print("[MODEL] OK")
    except Exception as e:
        safe_print("[MODEL] FAIL: " + str(e)); traceback.print_exc()
    finally:
        os.chdir(original_cwd)

# ══════════════════════════════════════════════════════════════
#  TTS GPU 显存管理（视频合成前后自动释放/恢复 GPU 占用）
# ══════════════════════════════════════════════════════════════
_tts_on_gpu = True  # 追踪 TTS 模型当前是否在 GPU 上

def _release_tts_gpu():
    """完全卸载 TTS 模型，同时释放 GPU 显存和系统内存"""
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
        safe_print("[GPU] TTS 模型已完全卸载（GPU + RAM 均已释放）")
    except Exception as e:
        safe_print(f"[GPU] 释放 TTS 失败: {e}")


def _restore_tts_gpu():
    """确保 TTS 模型已加载到 GPU（如已卸载则从磁盘重新加载）"""
    global tts, _tts_on_gpu
    
    # 如果是在线版，不需要恢复TTS模型
    tts_mode = os.getenv('TTS_MODE', 'local')
    if tts_mode == 'online':
        safe_print("[GPU] 在线版模式，跳过 TTS 模型恢复")
        return
    
    if tts is not None and _tts_on_gpu:
        return
    # tts 已被卸载，需要从磁盘重新加载
    if tts is None:
        try:
            safe_print("[GPU] TTS 模型已卸载，正在重新加载...")
            model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
            if not os.path.exists(model_dir):
                safe_print("[GPU] 模型目录不存在，无法重新加载")
                return
            original_cwd = os.getcwd()
            os.chdir(INDEXTTS_DIR)
            try:
                from indextts.infer_v2 import IndexTTS2
                tts = IndexTTS2(model_dir=model_dir,
                                cfg_path=os.path.join(model_dir, "config.yaml"), use_fp16=True)
                _tts_on_gpu = True
                safe_print("[GPU] TTS 模型重新加载完成")
            finally:
                os.chdir(original_cwd)
        except Exception as e:
            safe_print(f"[GPU] 重新加载 TTS 失败: {e}")
        return
    # tts 在内存中但在 CPU 上（兼容旧逻辑）
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
        safe_print("[GPU] TTS 模型已恢复到 GPU")
    except Exception as e:
        safe_print(f"[GPU] 恢复 TTS 到 GPU 失败: {e}")


# ══════════════════════════════════════════════════════════════
#  语音合成（支持本地版和在线版）
# ══════════════════════════════════════════════════════════════
def download_voice_from_proxy(play_url: str, output_path: str, max_retries: int = 5, extra_headers=None) -> str:
    """通过代理URL下载音频文件到指定路径（自动重试 + 流式下载）"""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import time as _time
    import http.client as _http_client

    session = requests.Session()
    try:
        # urllib3 层自动重试（仅针对连接级错误）
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
                    return False, "文件不存在"
                size = os.path.getsize(path)
                if size < 2048:
                    return False, f"文件过小({size}字节)"

                ct = (content_type or "").lower()
                # 允许的 content-type
                if ct and ("json" in ct or "text" in ct or "html" in ct):
                    return False, f"Content-Type 异常: {content_type}"

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

                # 如果 content-type 明确是音频，也放行（某些 wav 可能无 RIFF 头，极少见）
                if ct.startswith("audio/"):
                    return True, f"audio/{ct}"
                return False, "文件头不符合常见音频格式"
            except Exception as e:
                return False, f"校验失败: {e}"

        last_err = None
        for attempt in range(1, max_retries + 1):
            r = None
            try:
                print(f"[下载] 第 {attempt}/{max_retries} 次尝试下载音频...")

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
                        print(f"[下载] 音频下载成功，大小: {file_size} 字节")
                        return output_path
                    # 预览一下响应内容，帮助定位服务端返回的是什么
                    try:
                        with open(output_path, 'rb') as _f:
                            preview = _f.read(256)
                        try:
                            preview_text = preview.decode('utf-8', errors='replace')
                        except Exception:
                            preview_text = str(preview)
                    except Exception:
                        preview_text = "(无法读取预览)"
                    # 如果服务端返回的是鉴权/卡密相关 JSON，继续重试没有意义
                    if '"code":7' in preview_text and (
                        ("缺少 Authorization" in preview_text) or ("卡密已过期" in preview_text)
                    ):
                        raise RuntimeError(f"[AUTH]{preview_text}")

                    raise IOError(
                        f"下载内容不是有效音频: {why}; Content-Type={content_type}; 预览={preview_text}"
                    )

                raise IOError(f"文件不完整: 已下载 {file_size} / 预期 {expected} 字节")

            except (_http_client.IncompleteRead, requests.exceptions.ChunkedEncodingError) as e:
                last_err = e
                print(f"[下载] 断流/半包(IncompleteRead)，第 {attempt} 次失败: {e}")
            except RuntimeError as e:
                last_err = e
                # 鉴权/卡密错误不重试
                if str(e).startswith("[AUTH]"):
                    raise
                print(f"[下载] 第 {attempt} 次下载失败: {e}")
            except Exception as e:
                last_err = e
                print(f"[下载] 第 {attempt} 次下载失败: {e}")
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
                print(f"[下载] 等待 {wait} 秒后重试...")
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
            print(f"[直连下载] 第 {attempt}/{max_retries} 次尝试...")
            r = requests.get(voice_url, headers=headers, timeout=(30, 600), stream=True)
            r.raise_for_status()
            content_type = r.headers.get('Content-Type', '')

            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

            ok_audio = os.path.exists(output_path) and os.path.getsize(output_path) >= 2048
            if not ok_audio:
                # 给出预览
                preview_text = ""
                try:
                    with open(output_path, 'rb') as _f:
                        preview = _f.read(256)
                    preview_text = preview.decode('utf-8', errors='replace')
                except Exception:
                    preview_text = "(无法读取预览)"
                raise IOError(f"直连下载内容异常: Content-Type={content_type}; 预览={preview_text}")

            return output_path

        except (_http_client.IncompleteRead, requests.exceptions.ChunkedEncodingError) as e:
            last_err = e
            print(f"[直连下载] 断流/半包，第 {attempt} 次失败: {e}")
        except Exception as e:
            last_err = e
            print(f"[直连下载] 第 {attempt} 次失败: {e}")
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
    if "中国" in p or "chinese" in p_low:
        return p
    human_keywords = [
        "人", "人物", "真人", "模特", "男人", "女人", "男孩", "女孩", "少年", "少女", "大叔", "阿姨",
        "person", "people", "man", "woman", "boy", "girl", "male", "female", "human",
    ]
    if any(k in p for k in human_keywords) or any(k in p_low for k in human_keywords):
        return p + "，中国人"
    return p


def split_text_by_sentences(text, max_chars=100):
    """将文本按句子分割，每段不超过max_chars字符

    Args:
        text: 要分割的文本
        max_chars: 每段最大字符数

    Returns:
        list: 分割后的文本段列表
    """
    import re

    # 按句子分割（中文句号、问号、感叹号、英文句号等）
    sentences = re.split(r'([。！？!?；;])', text)

    # 重新组合句子和标点
    full_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            full_sentences.append(sentences[i] + sentences[i + 1])
        else:
            full_sentences.append(sentences[i])
    if len(sentences) % 2 == 1:
        full_sentences.append(sentences[-1])

    # 合并短句，确保每段不超过max_chars
    chunks = []
    current_chunk = ""

    for sentence in full_sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # 如果当前句子本身就超过max_chars，单独作为一段
        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            chunks.append(sentence)
        # 如果加上当前句子会超过max_chars，先保存当前chunk
        elif len(current_chunk) + len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
        # 否则继续累加
        else:
            current_chunk += sentence

    # 添加最后一段
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def generate_speech_online_concurrent(text, voice_name, progress=gr.Progress()):
    """在线版 TTS：并发调用云端 API 合成语音（优化版）

    将长文本分割成多个100字以内的段落，并发请求，全部完成后合成
    """
    if not text.strip():
        raise gr.Error("请输入要合成的文本内容")

    try:
        from voice_api import VoiceApiClient, API_BASE_URL, get_machine_code
        from lib_license import check_saved_license
        import lib_voice as _vc
        import time as _time
        import concurrent.futures
        from pydub import AudioSegment

        # 检查卡密
        status, info = check_saved_license()
        if status != "valid":
            raise gr.Error("请先登录卡密后再使用在线版 TTS")

        if not isinstance(info, dict):
            raise gr.Error("卡密信息读取失败，请重新登录")

        license_key = info.get("license_key", "")
        if not license_key:
            raise gr.Error("卡密无效，请重新登录")

        # 获取 model_id
        model_id = _vc.get_online_model_id(voice_name)
        if not model_id:
            raise gr.Error(f"未找到在线音色「{voice_name}」的模型 ID")

        # 分割文本
        text_chunks = split_text_by_sentences(text, max_chars=100)
        chunk_count = len(text_chunks)

        print(f"[TTS在线版-并发] 文本总长度: {len(text)}, 分割为 {chunk_count} 段")
        for i, chunk in enumerate(text_chunks):
            print(f"[TTS在线版-并发] 段落{i+1}: {len(chunk)}字 - {chunk[:30]}...")

        progress(0.05, desc=f"[在线] 准备并发请求 {chunk_count} 个任务...")

        client = VoiceApiClient(API_BASE_URL, license_key)

        # 提交所有任务
        task_ids = []
        for i, chunk in enumerate(text_chunks):
            try:
                result = client.tts(model_id, chunk)
                if result.get("code") != 0:
                    raise gr.Error(f"段落{i+1}提交失败：{result.get('msg', '未知错误')}")

                data = result.get("data", {})
                task_id = data.get("task_id") or data.get("taskId") or data.get("id")
                if not task_id:
                    raise gr.Error(f"段落{i+1}未返回任务ID")

                task_ids.append((i, task_id, chunk))
                print(f"[TTS在线版-并发] 段落{i+1}已提交，任务ID: {task_id}")
            except Exception as e:
                raise gr.Error(f"段落{i+1}提交失败：{e}")

        progress(0.15, desc=f"[在线] 已提交 {chunk_count} 个任务，等待处理...")

        # 并发轮询所有任务
        def poll_task(task_info):
            idx, task_id, chunk_text = task_info
            start_time = _time.time()

            while True:
                try:
                    result = client.tts_result(task_id)

                    if not isinstance(result, dict):
                        return (idx, None, f"轮询结果异常")

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
                            print(f"[TTS在线版-并发] 段落{idx+1}已完成: {voice_url}")
                            return (idx, voice_url, None)
                        else:
                            return (idx, None, "未返回音频URL")

                    elif is_failed:
                        error_msg = data.get("message") or data.get("msg") or data.get("error") or "未知错误"
                        return (idx, None, error_msg)

                    # 超时检查（每个任务最多等待5分钟）
                    if _time.time() - start_time > 300:
                        return (idx, None, "任务超时")

                    _time.sleep(2)

                except Exception as e:
                    return (idx, None, str(e))

        # 使用线程池并发轮询
        audio_urls = [None] * chunk_count
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(chunk_count, 10)) as executor:
            futures = [executor.submit(poll_task, task_info) for task_info in task_ids]

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                idx, url, error = future.result()
                completed += 1

                if error:
                    raise gr.Error(f"段落{idx+1}处理失败：{error}")

                audio_urls[idx] = url
                progress(0.15 + 0.6 * completed / chunk_count,
                        desc=f"[在线] 已完成 {completed}/{chunk_count} 个任务...")

        progress(0.75, desc="[在线] 下载音频文件...")

        # 下载所有音频文件
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
                print(f"[TTS在线版-并发] 段落{i+1}已下载: {local_file}")

            except Exception as e:
                raise gr.Error(f"段落{i+1}下载失败：{e}")

        progress(0.90, desc="[在线] 合成音频...")

        # 合成所有音频
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

            # 清理临时文件
            for audio_file in audio_files:
                try:
                    os.remove(audio_file)
                except Exception:
                    pass

        progress(1.0, desc="[OK] 合成完成")
        print(f"[TTS在线版-并发] 合成成功: {final_file}")

        return final_file, "[OK] 在线语音合成完成", final_file

    except gr.Error:
        raise
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"在线 TTS 失败：{e}")


def generate_speech_online(text, voice_name, progress=gr.Progress()):
    """在线版 TTS：调用云端 API 合成语音"""
    if not text.strip():
        raise gr.Error("请输入要合成的文本内容")
    
    try:
        from voice_api import VoiceApiClient
        from lib_license import check_saved_license
        import lib_voice as _vc
        
        # 检查卡密
        status, info = check_saved_license()
        if status != "valid":
            raise gr.Error("请先登录卡密后再使用在线版 TTS")

        if not isinstance(info, dict):
            raise gr.Error("卡密信息读取失败，请重新登录")

        license_key = info.get("license_key", "")
        if not license_key:
            raise gr.Error("卡密无效，请重新登录")
        
        # 获取 model_id
        model_id = _vc.get_online_model_id(voice_name)
        if not model_id:
            raise gr.Error(f"未找到在线音色「{voice_name}」的模型 ID")
        
        progress(0.1, desc="[在线] 正在调用云端 TTS 服务...")
        
        # 调用 API
        from voice_api import API_BASE_URL
        client = VoiceApiClient(API_BASE_URL, license_key)
        
        result = client.tts(model_id, text)
        print(f"[TTS在线版] 服务器返回: {result}")

        if not isinstance(result, dict):
            raise gr.Error(f"在线 TTS 失败：服务器返回异常（非JSON对象）：{result}")
        
        if result.get("code") != 0:
            raise gr.Error(f"合成失败：{result.get('msg', '未知错误')}")
        
        data = result.get("data", {})
        if data is None:
            data = {}
        # 兼容不同的字段名：task_id, taskId, id
        task_id = data.get("task_id") or data.get("taskId") or data.get("id")
        
        if not task_id:
            print(f"[TTS在线版] 错误：未找到任务ID，data={data}")
            raise gr.Error(f"服务器返回的任务 ID 无效，返回数据: {data}")
        
        progress(0.3, desc="[在线] 云端正在处理中...")
        
        # 轮询结果（不设超时，因为长文案合成可能需要数分钟）
        import time as _time
        start_time = _time.time()
        while True:
            result = client.tts_result(task_id)
            print(f"[TTS在线版] 轮询结果: {result}")

            if not isinstance(result, dict):
                raise gr.Error(f"在线 TTS 失败：轮询结果返回异常（非JSON对象）：{result}")
            
            status_code = result.get("code")
            data = result.get("data", {})
            if data is None:
                data = {}
            task_status = data.get("status", "")
            
            # 兼容不同的状态表示：
            # - 字符串: "completed", "success", "done"
            # - 数字: 2 (完成), 1 (处理中), 0 (等待), -1 (失败)
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
                # 兼容多种音频URL字段名
                voice_url = (
                    data.get("audio_url") or 
                    data.get("audioUrl") or 
                    data.get("voiceUrl") or 
                    data.get("voice_url") or 
                    data.get("url")
                )
                
                if voice_url:
                    progress(0.9, desc="[在线] 下载音频文件...")
                    from urllib.parse import quote
                    from voice_api import API_BASE_URL
                    from voice_api import get_machine_code
                    
                    try:
                        print(f"[TTS在线版] 下载音频: {voice_url}")
                        
                        # 生成本地保存路径（和本地版一样保存到 unified_outputs）
                        ts = int(_time.time())
                        local_file = os.path.join(OUTPUT_DIR, f"tts_online_{ts}.wav")
                        
                        sign = os.getenv("LIPVOICE_SIGN", "").strip()
                        if sign:
                            print("[TTS在线版] 使用直连下载音频...")
                            download_voice_from_lipvoice_direct(voice_url, local_file, sign)
                        else:
                            # 未配置 LIPVOICE_SIGN 时回退走服务端代理下载
                            proxy_url = f"{API_BASE_URL}/api/dsp/voice/tts/download?voice_url={quote(voice_url)}"
                            download_voice_from_proxy(
                                proxy_url,
                                local_file,
                                extra_headers={
                                    "Authorization": f"Bearer {license_key}",
                                    "X-Machine-Code": get_machine_code(),
                                },
                            )
                        
                        progress(1.0, desc="[OK] 合成完成")
                        print(f"[TTS在线版] 合成成功: {local_file}")
                        
                        # 返回本地文件路径
                        return local_file, "[OK] 在线语音合成完成", local_file
                    except Exception as e:
                        raise gr.Error(f"下载音频失败：{e}")
                else:
                    print(f"[TTS在线版] 错误：未找到音频URL，data={data}")
                    raise gr.Error(f"服务器返回的音频 URL 无效，返回数据: {data}")
            elif is_failed:
                error_msg = data.get("message") or data.get("msg") or data.get("error") or "未知错误"
                raise gr.Error(f"合成失败：{error_msg}")
            
            # 更新进度
            elapsed = int(_time.time() - start_time)
            progress(min(0.3 + elapsed / 600 * 0.5, 0.8), desc=f"[在线] 云端处理中...已等待 {elapsed} 秒")
            _time.sleep(2)
        
    except gr.Error:
        raise
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"在线 TTS 失败：{e}")


def generate_speech_local(text, prompt_audio, top_p, top_k, temperature, num_beams,
                          repetition_penalty, max_mel_tokens, emo_mode, emo_audio, emo_weight,
                          emo_text, vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                          progress=gr.Progress()):
    """本地版 TTS：使用本机 GPU 合成语音"""
    global tts
    if not text.strip():     raise gr.Error("请输入要合成的文本内容")
    if prompt_audio is None: raise gr.Error("请上传参考音频文件")

    # 确保 TTS 模型已加载且在 GPU 上（视频合成后模型已卸载，需重新加载）
    _restore_tts_gpu()
    if tts is None:          raise gr.Error("模型未加载，请等待初始化完成")

    ts  = int(time.time())
    out = os.path.join(OUTPUT_DIR, f"tts_{ts}.wav")
    cwd = os.getcwd(); os.chdir(INDEXTTS_DIR)
    try:
        progress(0.25, desc="🎯 配置生成参数...")
        kw = dict(
            do_sample=True, top_p=float(top_p), top_k=int(top_k),
            temperature=float(temperature), length_penalty=0.0,
            num_beams=int(num_beams), repetition_penalty=float(repetition_penalty),
            max_mel_tokens=int(max_mel_tokens)
        )
        emo_ref_path, vec, use_emo_text = None, None, False
        if emo_mode == "使用情感参考音频":
            emo_ref_path = emo_audio
            progress(0.30, desc="🎭 加载情感参考...")
        elif emo_mode == "使用情感向量控制":
            vec = tts.normalize_emo_vec([vec1,vec2,vec3,vec4,vec5,vec6,vec7,vec8], apply_bias=True)
            progress(0.30, desc="🎭 应用情感向量...")
        elif emo_mode == "使用情感描述文本控制":
            use_emo_text = True
            progress(0.30, desc="🎭 解析情感描述...")

        progress(0.35, desc="🚀 开始生成音频（请耐心等待）...")
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
        progress(0.90, desc="💾 保存音频文件...")
        progress(1.0, desc="✅ 合成完成")
        return out, "✅ 语音合成完成", out
    except Exception as e:
        os.chdir(cwd); traceback.print_exc()
        raise gr.Error("TTS 失败: " + str(e))


def generate_speech(text, prompt_audio, voice_name, top_p, top_k, temperature, num_beams,
                    repetition_penalty, max_mel_tokens, emo_mode, emo_audio, emo_weight,
                    emo_text, vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                    progress=gr.Progress()):
    """语音合成入口：以当前 TTS_MODE 为准选择本地/在线。

    说明：之前仅根据 voice_name 是否为在线音色来决定走在线合成，
    会导致「登录时选在线版 → UI 切到本地版」后仍然误走在线合成（表现为非常慢）。
    """
    tts_mode = os.getenv('TTS_MODE', 'local')
    if tts_mode == 'online':
        # 使用并发优化版本
        return generate_speech_online_concurrent(text, voice_name, progress)
    return generate_speech_local(text, prompt_audio, top_p, top_k, temperature, num_beams,
                                 repetition_penalty, max_mel_tokens, emo_mode, emo_audio, emo_weight,
                                 emo_text, vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                                 progress)


# ══════════════════════════════════════════════════════════════
#  视频格式转换
# ══════════════════════════════════════════════════════════════
def convert_video_for_browser(video_path, progress=gr.Progress()):
    if not video_path or not os.path.exists(video_path): return None
    ffmpeg = _resolve_ffmpeg_exe()
    if not ffmpeg: return video_path
    ts  = int(time.time())
    out = os.path.join(OUTPUT_DIR, f"converted_{ts}.mp4")
    progress(0.3, desc="转换视频格式...")
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        p = subprocess.Popen(
            [ffmpeg, "-i", video_path, "-c:v", "libx264", "-preset", "ultrafast",
             "-crf", "23", "-c:a", "aac", "-b:a", "128k",
             "-movflags", "+faststart", "-pix_fmt", "yuv420p", "-y", out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        p.communicate(timeout=120)
        progress(1.0, desc="转换完成")
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
        raise gr.Error("背景音乐库为空")
    pool = []
    for t in selected_types:
        items = db.get(t) or []
        if isinstance(items, list):
            pool.extend([it for it in items if isinstance(it, dict) and it.get("url") and it.get("filename")])
    if not pool:
        raise gr.Error("所选类型下没有可用音乐")
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

    progress(0.1, desc="🎵 AI正在匹配最佳音乐...")
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
                    # 有些资源站会返回非标准状态码（如567），浏览器仍可下载
                    # 这里不使用 raise_for_status，而是以“最终文件是否有效”作为成功标准
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
        # Windows 兜底：走系统网络栈，行为更接近浏览器
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

    progress(0.2, desc="🎵 AI智能音乐加载中...")
    if _download_via_urllib():
        return path
    if _download_via_powershell():
        return path

    raise gr.Error(f"音乐资源加载失败: {url}")


def prepare_random_bgm_and_download(types_val, progress=gr.Progress(), max_tries=6):
    """从所选类型中随机挑选可用音乐并下载。下载失败自动换曲重试。"""
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
            progress(0.05 + (i / max(1, max_tries)) * 0.25, desc=f"准备BGM：{title[:18]}...")
            local_path = download_bgm_if_needed(url, filename, progress=progress)
            shown = (title or os.path.basename(local_path)).strip()
            return item, local_path, shown
        except Exception as e:
            last_err = e
            continue

    raise gr.Error(f"准备背景音乐失败（已尝试{len(tried)}首）: {last_err}")


def mix_bgm_into_video(video_path: str, bgm_path: str, bgm_volume: float, progress=gr.Progress()):
    if not video_path or not os.path.exists(video_path):
        raise gr.Error("请先生成视频（步骤3或步骤4）")
    if not bgm_path or not os.path.exists(bgm_path):
        raise gr.Error("请先选择背景音乐")

    ffmpeg_bin = _resolve_ffmpeg_exe()

    vol = float(bgm_volume or 1.0)
    vol = max(0.0, min(3.0, vol))

    ts = int(time.time())
    out = os.path.join(OUTPUT_DIR, f"video_bgm_{ts}.mp4")

    progress(0.2, desc="合成背景音乐...")
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
            raise gr.Error("背景音乐合成失败: " + (err[:400] if err else "ffmpeg error"))
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(f"背景音乐合成失败: {e}")

    if not os.path.exists(out) or os.path.getsize(out) < 1024:
        raise gr.Error("背景音乐合成失败：输出文件不存在")
    progress(1.0, desc="完成")
    return out


# ══════════════════════════════════════════════════════════════
#  进度详情 HTML 构建（用于步骤 / 帧双行显示）
# ══════════════════════════════════════════════════════════════
def _make_detail_html(f_pct, f_cur, f_total, s_pct, s_cur, s_total, prog):
    bar_f = max(2, f_pct)
    bar_s = max(2, s_pct)
    return (
        f'''<div style="background:linear-gradient(135deg,#1e293b,#0f172a);
            border:1.5px solid #6366f1;border-radius:12px;
            padding:14px 16px 12px;margin:0 0 10px;
            font-family:Microsoft YaHei,system-ui,sans-serif;
            box-shadow:0 4px 16px rgba(99,102,241,.18);">
          <!-- 帧进度 -->
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:11px;color:#94a3b8;width:32px;flex-shrink:0;">帧</span>
            <div style="flex:1;background:rgba(99,102,241,.15);border-radius:4px;height:7px;overflow:hidden;">
              <div style="height:100%;width:{bar_f}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);
                border-radius:4px;transition:width .35s;"></div>
            </div>
            <span style="font-size:12px;font-weight:700;color:#6366f1;width:48px;text-align:right;flex-shrink:0;">{f_pct}%</span>
            <span style="font-size:11px;color:#64748b;flex-shrink:0;">{f_cur}/{f_total}</span>
          </div>
          <!-- 步骤进度 -->
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:11px;color:#94a3b8;width:32px;flex-shrink:0;">步骤</span>
            <div style="flex:1;background:rgba(139,92,246,.15);border-radius:4px;height:7px;overflow:hidden;">
              <div style="height:100%;width:{bar_s}%;background:linear-gradient(90deg,#8b5cf6,#a78bfa);
                border-radius:4px;transition:width .35s;"></div>
            </div>
            <span style="font-size:12px;font-weight:700;color:#8b5cf6;width:48px;text-align:right;flex-shrink:0;">{s_pct}%</span>
            <span style="font-size:11px;color:#64748b;flex-shrink:0;">{s_cur}/{s_total}</span>
          </div>
          <!-- 总进度 -->
          <div style="font-size:11px;color:#64748b;text-align:right;">总进度 {prog*100:.1f}%</div>
        </div>'''
    )

def _build_heygem_env():
    """构建 HeyGem 子进程所需的环境变量（参考 heygem-win-50/开始.bat）。"""
    env = os.environ.copy()
    py_path = os.path.join(HEYGEM_DIR, "py39")
    scripts_path = os.path.join(py_path, "Scripts")
    cu_path = os.path.join(py_path, "Lib", "site-packages", "torch", "lib")
    cuda_path = os.path.join(py_path, "Library", "bin")
    ffmpeg_path = HEYGEM_FFMPEG

    # 这些变量在 bat 里会清空，避免污染系统 Python
    env["PYTHONHOME"] = ""
    env["PYTHONPATH"] = ""

    # 关键：让 heygem 内置 ffmpeg 可用
    env["PATH"] = ";".join([
        py_path,
        scripts_path,
        ffmpeg_path,
        cu_path,
        cuda_path,
        env.get("PATH", "")
    ])

    # gradio 临时目录
    env["GRADIO_TEMP_DIR"] = os.path.join(HEYGEM_DIR, "tmp")

    # huggingface 镜像/缓存（bat 里有，保留一致）
    env.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    env.setdefault("HF_HOME", os.path.join(HEYGEM_DIR, "hf_download"))
    env.setdefault("TRANSFORMERS_CACHE", os.path.join(HEYGEM_DIR, "tf_download"))
    env.setdefault("XFORMERS_FORCE_DISABLE_TRITON", "1")
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:512")

    # 让子进程/多进程能 import 到编译模块
    env["PYTHONPATH"] = ";".join([
        HEYGEM_DIR,
        os.path.join(HEYGEM_DIR, "service"),
        env.get("PYTHONPATH", "")
    ])
    return env


def run_heygem(video_path, audio_path, progress=gr.Progress(), detail_cb=None,
               output_path_override=None, steps=12, if_gfpgan=False):
    """使用 heygem-win-50 生成口型视频。

    通过 HeyGem 内置 python 在子进程中调用 cy_app.VideoProcessor.process_video，避免依赖当前主进程环境。
    """
    if not video_path:
        raise gr.Error("请上传人物视频")
    if not audio_path:
        raise gr.Error("请先在步骤1准备音频（文字转语音 或 直接上传音频文件）")
    if not os.path.exists(str(video_path)):
        raise gr.Error("视频文件不存在，请重新上传")
    if not os.path.exists(str(audio_path)):
        raise gr.Error("音频文件不存在，请重新选择")
    if not os.path.exists(HEYGEM_PYTHON):
        raise gr.Error("HeyGem 环境未找到：heygem-win-50/py39/python.exe")

    ts = int(time.time())
    sv = os.path.join(OUTPUT_DIR, f"in_v_{ts}{os.path.splitext(str(video_path))[1]}")
    sa = os.path.join(OUTPUT_DIR, f"in_a_{ts}{os.path.splitext(str(audio_path))[1]}")
    out = output_path_override if output_path_override else os.path.join(OUTPUT_DIR, f"lipsync_{ts}.mp4")
    try:
        shutil.copy2(str(video_path), sv)
        shutil.copy2(str(audio_path), sa)
    except Exception as e:
        raise gr.Error("复制文件失败: " + str(e))

    progress(0.05, desc="初始化中...")
    _release_tts_gpu()

    env = _build_heygem_env()
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    # 子进程脚本：调用 heygem 的 VideoProcessor，并把 yield 的内容打印出来（便于调试/追踪）
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
        raise gr.Error("启动 HeyGem 失败: " + str(e))

    progress(0.08, desc="正在生成视频...")
    last_line = ""
    prog = 0.08
    stage = "准备中"
    stage_pct = 8
    t0 = time.time()
    # HeyGem 双进度追踪：总进度 + 步骤进度
    step_total = 0
    step_pct = 0       # 当前步骤百分比 0~100
    step_label = ""    # 当前步骤描述

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

        # ── 解析 HeyGem 各阶段（只在匹配时更新 stage，避免跳动）──

        # 1) 预处理
        if "文件下载耗时" in line or ("下载" in line and "耗时" in line):
            stage = "准备素材"
            stage_pct = max(stage_pct, 5)
            prog = max(prog, 0.05)
            step_label = "下载文件"
            step_pct = 100
        elif "format" in low and ("video" in low or "audio" in low or "帧率" in line or "fps" in low):
            stage = "分析音视频"
            stage_pct = max(stage_pct, 8)
            prog = max(prog, 0.08)
            step_label = "格式转换"
            step_pct = 100
        elif "batch_size" in low or "batch size" in low:
            stage = "初始化推理"
            stage_pct = max(stage_pct, 10)
            prog = max(prog, 0.10)
            step_label = "加载模型"
            step_pct = 0

        # 2) 数据准备进度：drivered_video_pn >>> progress: 12/108
        elif "drivered_video_pn" in line:
            stage = "准备数据"
            dp = re.search(r'progress:\s*(\d+)/(\d+)', line)
            if dp:
                cur, total = int(dp.group(1)), int(dp.group(2))
                step_total = max(step_total, total)
                if total > 0:
                    frac = cur / total
                    stage_pct = max(stage_pct, int(10 + frac * 20))
                    prog = max(prog, 0.10 + frac * 0.20)
                    step_label = f"帧数据 {cur}/{total}"
                    step_pct = int(frac * 100)

        # 3) 推理进度：audio_transfer >>> frameId:24
        elif "audio_transfer" in line and "frameid" in low:
            stage = "生成口型"
            ap = re.search(r'frameId[:\s]*(\d+)', line, re.IGNORECASE)
            if ap:
                step_cur = int(ap.group(1))
                if step_total > 0:
                    frac = min(1.0, step_cur / step_total)
                    stage_pct = max(stage_pct, int(30 + frac * 55))
                    prog = max(prog, 0.30 + frac * 0.55)
                    step_label = f"推理帧 {step_cur}/{step_total}"
                    step_pct = int(frac * 100)
                else:
                    stage_pct = max(stage_pct, min(80, stage_pct + 3))
                    prog = max(prog, min(0.80, prog + 0.03))
                    step_label = f"推理帧 {step_cur}"
                    step_pct = min(step_pct + 5, 95)

        # 4) 合成输出
        elif "executing ffmpeg command" in low or ("ffmpeg" in low and "command" in low):
            stage = "合成输出"
            stage_pct = max(stage_pct, 88)
            prog = max(prog, 0.88)
            step_label = "ffmpeg 合并"
            step_pct = 50
        elif "video result saved" in low:
            stage = "完成"
            stage_pct = max(stage_pct, 95)
            prog = max(prog, 0.95)
            step_label = "保存文件"
            step_pct = 100
        if detail_cb:
            try:
                el = int(time.time() - t0)
                detail_cb(_dual_progress_html(stage, stage_pct, step_label, step_pct, el))
            except Exception:
                pass

        # 推进 Gradio progress bar
        try:
            from libs.app_version import get_app_version
            APP_VERSION, APP_BUILD = get_app_version()
            prog = min(0.96, prog + 0.002)
            progress(prog, desc=f"{stage}... {int(stage_pct)}%")
        except Exception:
            pass

    rc = proc.wait()
    _restore_tts_gpu()

    if rc != 0:
        raise gr.Error("视频合成失败（HeyGem）: " + (last_line or "unknown error"))
    if not os.path.exists(out):
        raise gr.Error("输出视频文件未找到，请重试")

    if detail_cb:
        try:
            el = int(time.time() - t0)
            detail_cb(_dual_progress_html("完成", 100, "全部完成", 100, el))
        except Exception:
            pass
    progress(1.0, desc="✅ 完成")
    for f in (sv, sa):
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    return out, "✅ 视频合成完成"


def _md5_of_local_file(path):
    """计算本地文件的 MD5 hash"""
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_heygem_online(video_path, audio_path, progress=gr.Progress(), detail_cb=None,
                      output_path_override=None, **_kw):
    """使用 Linux HeyGem 服务器在线合成口型视频。

    流程：计算hash → 检查服务器是否已有 → 仅上传缺失文件 → 提交任务 → 轮询进度 → 下载结果
    """
    import requests as _req

    server_url = os.getenv("HEYGEM_SERVER_URL", "").strip().rstrip("/")
    api_secret = os.getenv("HEYGEM_API_SECRET", "").strip()

    if not server_url:
        raise gr.Error("HEYGEM_SERVER_URL 未配置，请在设置中配置 Linux HeyGem 服务器地址\n"
                       "格式示例: http://192.168.1.100:8383")
    # 自动补全 http:// 前缀
    if not server_url.startswith("http://") and not server_url.startswith("https://"):
        server_url = "http://" + server_url
    # 自动补全端口
    from urllib.parse import urlparse
    parsed = urlparse(server_url)
    if not parsed.port:
        server_url = server_url.rstrip("/") + ":8383"

    if not video_path or not os.path.exists(str(video_path)):
        raise gr.Error("视频文件不存在，请重新上传")
    if not audio_path or not os.path.exists(str(audio_path)):
        raise gr.Error("音频文件不存在，请重新选择")

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

    # ── 0) 通过 WebSocket 查询 GPU 状态，在线直接提交，离线立即开机 ──
    api_ws_url = os.getenv("API_SERVER_URL", "https://api.zhimengai.xyz").strip().rstrip("/")
    api_ws_url = api_ws_url.replace("https://", "wss://").replace("http://", "ws://") + "/dsp"

    _gpu_ws_status = {"status": "unknown", "online_event": threading.Event()}
    _boot_request_id = str(uuid.uuid4())

    def _ws_query_and_boot():
        """通过 WS 查询 GPU 状态，离线则立即发送开机请求，等待 gpu.power.online"""
        if not _WS_OK:
            safe_print("[WS] websockets 模块不可用，跳过 WS 查询")
            return
        import websockets as _ws_lib

        async def _run():
            try:
                async with _ws_lib.connect(api_ws_url, open_timeout=5, close_timeout=3) as ws:
                    # 注册
                    await ws.send(json.dumps({
                        "type": "register",
                        "key": api_secret or "gradio_client",
                        "device_type": "pc"
                    }))
                    # 查询 GPU 状态
                    await ws.send(json.dumps({
                        "type": "gpu.status.query",
                        "request_id": _boot_request_id,
                    }))
                    safe_print(f"[WS] 已发送 GPU 状态查询")

                    # 等待响应（最多等 600 秒 = 10分钟，足够 GPU 开机）
                    _boot_sent = False
                    _last_ping = time.time()
                    _loop = asyncio.get_event_loop()
                    _deadline = _loop.time() + 600
                    while _loop.time() < _deadline:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=5)
                            data = json.loads(raw)
                            msg_type = data.get("type", "")

                            if msg_type == "pong":
                                continue

                            if msg_type == "gpu.status.response":
                                st = str(data.get("status", "unknown")).strip().lower()
                                state_raw = str(data.get("State", data.get("state", ""))).strip().lower()
                                # 兼容服务端 status 与云厂商 State 字段
                                if st in ("online",):
                                    st = "running"
                                if state_raw == "initializing":
                                    st = "starting"
                                safe_print(f"[WS] GPU 状态: {st} (State={state_raw or 'N/A'})")
                                _gpu_ws_status["status"] = st
                                if st == "running":
                                    _gpu_ws_status["online_event"].set()
                                    return
                                elif st == "stopped" and not _boot_sent:
                                    # GPU 离线，立即发送开机请求
                                    await ws.send(json.dumps({
                                        "type": "gpu.power.boot",
                                        "request_id": _boot_request_id,
                                        "source": "gradio",
                                        "msg": "PC端请求启动GPU服务器"
                                    }))
                                    _boot_sent = True
                                    safe_print("[WS] GPU 离线，已发送开机请求")
                                elif st in ("starting", "stopping", "unknown"):
                                    # 启动中/未知状态先等待下一次状态回报，避免误触发重复开机
                                    pass

                            elif msg_type in ("gpu.power.online", "gpu_online"):
                                safe_print("[WS] ✓ 收到 GPU 上线通知!")
                                _gpu_ws_status["status"] = "running"
                                _gpu_ws_status["online_event"].set()
                                return

                            elif msg_type == "gpu.power.boot.result":
                                if data.get("success"):
                                    safe_print("[WS] ✓ GPU 开机成功")
                                    _gpu_ws_status["status"] = "running"
                                    _gpu_ws_status["online_event"].set()
                                    return
                                else:
                                    safe_print(f"[WS] GPU 开机结果: {data.get('msg', '')}")

                            elif msg_type == "registered":
                                safe_print(f"[WS] 已注册: {data}")

                        except asyncio.TimeoutError:
                            if not _boot_sent:
                                break  # 没发过 boot 且超时，退出让 health check 接管
                        except Exception:
                            continue

                        # 每 25 秒发一次心跳，保持 WS 连接不断
                        if time.time() - _last_ping > 25:
                            try:
                                await ws.send(json.dumps({"type": "ping"}))
                                _last_ping = time.time()
                            except Exception:
                                break

            except Exception as e:
                safe_print(f"[WS] GPU 查询/开机异常: {e}")

        try:
            asyncio.run(_run())
        except Exception as e:
            safe_print(f"[WS] 运行异常: {e}")

    # 在后台线程中执行 WS 查询和开机
    _ws_thread = threading.Thread(target=_ws_query_and_boot, daemon=True)
    _ws_thread.start()

    # 同时进行 HTTP 健康检查循环（WS 开机成功后 health check 自然通过）
    health_check_interval = 3  # 每3秒检查一次（加快轮询）
    health_check_timeout = 1800  # 最多等待30分钟
    health_start_time = time.time()
    gpu_was_offline = False

    while True:
        # 如果 WS 已经确认 GPU 在线，直接跳过等待，立刻提交任务
        if _gpu_ws_status["online_event"].is_set():
            safe_print("[HEYGEM-ONLINE] WS 确认 GPU 在线，直接提交任务")
            break

        try:
            resp = _req.get(f"{server_url}/api/heygem/health", headers=headers, timeout=10)
            resp.raise_for_status()
            hdata = resp.json()
            if hdata.get("code") != 0 or not hdata.get("initialized"):
                elapsed = int(time.time() - health_start_time)
                progress(0.01, desc=f"GPU 服务器初始化中... ({elapsed}s)")
                time.sleep(health_check_interval)
                continue

            safe_print(f"[HEYGEM-ONLINE] 服务器健康: {hdata}")
            if gpu_was_offline:
                safe_print(f"[HEYGEM-ONLINE] GPU 服务器已上线，继续处理任务")
            break

        except _req.exceptions.RequestException as e:
            error_msg = str(e)
            elapsed = int(time.time() - health_start_time)

            if elapsed > health_check_timeout:
                raise gr.Error(f"GPU 服务器等待超时 ({elapsed}s)，请检查服务器状态或联系管理员")

            if "Connection" in error_msg or "timeout" in error_msg.lower() or "Max retries" in error_msg:
                gpu_was_offline = True
                wait_minutes = elapsed // 60
                wait_seconds = elapsed % 60
                time_str = f"{wait_minutes}分{wait_seconds}秒" if wait_minutes > 0 else f"{wait_seconds}秒"
                progress(0.01, desc=f"等待 GPU 服务器上线... (已等待 {time_str})")
                time.sleep(health_check_interval)
                continue
            else:
                raise gr.Error(f"无法连接 HeyGem 服务器 ({server_url}): {e}")

    # ── 1) 计算本地文件 hash ──
    progress(0.02, desc="计算文件指纹...")
    if detail_cb:
        try: detail_cb(_dual_progress_html("准备上传", 2, "计算文件hash", 0, 0))
        except Exception: pass

    video_hash = _md5_of_local_file(video_path)
    audio_hash = _md5_of_local_file(audio_path)
    safe_print(f"[HEYGEM-ONLINE] video hash={video_hash}, audio hash={audio_hash}")

    # ── 2) 检查服务器是否已有这些文件 ──
    progress(0.03, desc="检查服务器文件...")
    if detail_cb:
        try: detail_cb(_dual_progress_html("检查文件", 3, "比对服务器", 0, 0))
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
        safe_print(f"[HEYGEM-ONLINE] check_files 失败，将全量上传: {e}")
        check_data = {}

    video_exists = check_data.get(video_hash, False)
    audio_exists = check_data.get(audio_hash, False)

    # ── 3) 仅上传缺失的文件 ──
    upload_items = []
    if not video_exists:
        upload_items.append(("video", video_path, video_hash, video_ext))
    else:
        safe_print(f"[HEYGEM-ONLINE] 视频文件已在服务器，跳过上传")
    if not audio_exists:
        upload_items.append(("audio", audio_path, audio_hash, audio_ext))
    else:
        safe_print(f"[HEYGEM-ONLINE] 音频文件已在服务器，跳过上传")

    for i, (ftype, fpath, fhash, fext) in enumerate(upload_items):
        pct = 4 + i * 3
        progress(pct / 100, desc=f"上传{ftype}到服务器...")
        if detail_cb:
            try:
                sz = os.path.getsize(fpath)
                detail_cb(_dual_progress_html("上传文件", pct, f"{ftype} ({sz//1024}KB)", int(i / max(len(upload_items), 1) * 100), int(time.time() - t0)))
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
                raise RuntimeError(udata.get("msg", "上传失败"))
            safe_print(f"[HEYGEM-ONLINE] 上传完成: {ftype} -> {udata.get('data', {}).get('hash')}")
        except _req.exceptions.RequestException as e:
            raise gr.Error(f"上传{ftype}到服务器失败: {e}")

    # ── 4) 通过 hash 提交合成任务 ──
    progress(0.10, desc="提交合成任务...")
    if detail_cb:
        try: detail_cb(_dual_progress_html("提交任务", 10, "发送请求", 0, int(time.time() - t0)))
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
            raise RuntimeError(data.get("msg", "提交失败"))
        task_id = data["data"]["task_id"]
        queue_info = data["data"].get("queue", {})
        safe_print(f"[HEYGEM-ONLINE] 任务已提交: {task_id}, 队列: {queue_info}")
    except _req.exceptions.RequestException as e:
        raise gr.Error(f"提交合成任务失败: {e}")
    except Exception as e:
        raise gr.Error(f"提交合成任务失败: {e}")

    # ── 5) 轮询进度 ──
    progress(0.12, desc="等待服务器处理...")
    poll_interval = 2
    max_wait = 1800

    while True:
        elapsed = time.time() - t0
        if elapsed > max_wait:
            raise gr.Error(f"合成超时 ({int(elapsed)}s)，请检查服务器状态")

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
            safe_print(f"[HEYGEM-ONLINE] 轮询异常: {e}")
            time.sleep(poll_interval)
            continue

        status = pdata.get("status", "")
        pct = pdata.get("progress", 0)
        msg = pdata.get("message", "")
        queue_pos = pdata.get("queue_position", 0)
        el = int(elapsed)

        if status == "queued":
            desc = f"排队中 (第{queue_pos}位)..."
            progress(0.12, desc=desc)
            if detail_cb:
                try: detail_cb(_dual_progress_html("排队等待", 12, f"队列位置 {queue_pos}", 0, el))
                except Exception: pass

        elif status in ("processing", "synthesizing", "encoding"):
            safe_pct = max(12, min(95, pct))
            grad_pct = 0.12 + (safe_pct - 12) * 0.01
            progress(min(0.95, grad_pct), desc=f"{msg} ({safe_pct}%)")
            if detail_cb:
                try:
                    cur_frame = pdata.get("current_frame", 0)
                    total_frame = pdata.get("total_frames", 0)
                    step_label = f"{cur_frame}/{total_frame} 帧" if total_frame else msg
                    detail_cb(_dual_progress_html("在线合成", safe_pct, step_label, safe_pct, el))
                except Exception: pass

        elif status == "done":
            safe_print(f"[HEYGEM-ONLINE] 合成完成，开始下载结果...")
            progress(0.95, desc="下载合成结果...")
            if detail_cb:
                try: detail_cb(_dual_progress_html("下载结果", 95, "正在下载", 50, el))
                except Exception: pass
            break

        elif status == "error":
            err = pdata.get("error", "未知错误")
            raise gr.Error(f"服务器合成失败: {err}")

        time.sleep(poll_interval)

    # ── 6) 下载结果 ──
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
            raise RuntimeError("下载的结果文件异常")

        safe_print(f"[HEYGEM-ONLINE] 下载完成: {out} ({os.path.getsize(out)} bytes)")
    except _req.exceptions.RequestException as e:
        raise gr.Error(f"下载合成结果失败: {e}")

    el = int(time.time() - t0)
    if detail_cb:
        try: detail_cb(_dual_progress_html("完成", 100, "全部完成", 100, el))
        except Exception: pass
    progress(1.0, desc="✅ 完成")
    return out, "✅ 在线视频合成完成"


def run_heygem_auto(video_path, audio_path, progress=gr.Progress(), detail_cb=None,
                    output_path_override=None, steps=12, if_gfpgan=False,
                    heygem_mode=None):
    """根据 heygem_mode 参数或 HEYGEM_MODE 环境变量选择本地或在线合成"""
    if heygem_mode is None:
        mode = os.getenv("HEYGEM_MODE", "local").strip().lower()
    else:
        mode = str(heygem_mode).strip().lower()
        # UI 传入的可能是中文
        if "在线" in mode or "online" in mode:
            mode = "online"
        else:
            mode = "local"
    if mode == "online":
        return run_heygem_online(video_path, audio_path, progress, detail_cb=None,
                                output_path_override=output_path_override)
    return run_heygem(video_path, audio_path, progress, detail_cb,
                      output_path_override, steps, if_gfpgan)


# ══════════════════════════════════════════════════════════════
#  批量任务辅助函数
# ══════════════════════════════════════════════════════════════
def generate_speech_batch(text, prompt_audio, out_path,
                          top_p=0.8, top_k=30, temperature=0.8,
                          num_beams=3, repetition_penalty=10.0, max_mel_tokens=1500):
    global tts
    if not text.strip(): raise RuntimeError("文本为空")
    if not prompt_audio: raise RuntimeError("缺少参考音频")
    # 确保 TTS 模型已加载且在 GPU 上（视频合成后模型已卸载，需重新加载）
    _restore_tts_gpu()
    if tts is None: raise RuntimeError("模型未加载")
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
                '<div style="font-size:24px;margin-bottom:8px;">📋</div>'
                '<div style="font-size:13px;">暂无任务 — 在左侧填写信息后点击「加入队列」</div></div>')
    status_cfg = {
        "等待中":  ("#f1f5f9","#64748b","⏳"),
        "进行中":  ("#ede9fe","#6d28d9","⚙️"),
        "✅ 完成": ("#f0fdf4","#15803d","✅"),
        "❌ 失败": ("#fff1f2","#be123c","❌"),
    }
    rows = ""
    for i, t in enumerate(tasks):
        idx = i + 1
        status = t.get("status", "等待中")
        sbg, sc, si = status_cfg.get(status, ("#f1f5f9","#64748b","⏳"))
        ab = ('<span class="bt-badge bt-badge-tts">🎙 文字合成</span>'
              if t.get("audio_mode") == "tts" else
              '<span class="bt-badge bt-badge-audio">🎵 上传音频</span>')
        vb = ('<span class="bt-badge bt-badge-shared">🎬 公共视频</span>'
              if t.get("video_mode") == "shared" else
              '<span class="bt-badge bt-badge-own">🎬 专属视频</span>')
        chip = (f'<span style="background:{sbg};color:{sc};border-radius:20px;'
                f'padding:2px 9px;font-size:11px;font-weight:700;">{si} {status}</span>')
        if status not in ("进行中", "✅ 完成"):
            js_code = ("var el=document.querySelector('#bt-del-trigger textarea');"
                       "if(el){el.value='" + str(idx) + "';"
                       "el.dispatchEvent(new Event('input',{bubbles:true}));}")
            del_btn = (
                '<button onclick="' + js_code + '" '
                'style="background:none;border:none;cursor:pointer;color:#cbd5e1;'
                'font-size:15px;padding:3px 6px;border-radius:6px;line-height:1;" '
                'onmouseover="this.style.background=\'#fee2e2\';this.style.color=\'#dc2626\'" '
                'onmouseout="this.style.background=\'none\';this.style.color=\'#cbd5e1\'"'
                '>✕</button>'
            )
        else:
            del_btn = ""
        row_bg = ("#f0fdf4" if "完成" in status else
                  ("#fff1f2" if "失败" in status else
                   ("#f5f3ff" if status == "进行中" else "transparent")))
        rows += (
            f'<tr style="border-bottom:1px solid #f1f5f9;background:{row_bg};">'
            f'<td style="padding:10px 8px;font-weight:800;color:#6366f1;font-size:13px;text-align:center;width:40px;">#{idx}</td>'
            f'<td style="padding:10px 8px;font-size:13px;color:#0f172a;font-weight:600;">{t.get("name","任务"+str(idx))}</td>'
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
        f'<span style="font-size:12px;font-weight:700;color:#fff;">共 {cnt} 个任务</span>'
        f'<span style="font-size:11px;color:rgba(255,255,255,.75);">点击行末 ✕ 可删除</span></div>'
        f'<table style="width:100%;border-collapse:collapse;font-family:Microsoft YaHei,sans-serif;">'
        f'<thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">'
        f'<th style="padding:8px;text-align:center;font-size:11px;color:#64748b;width:40px;">序</th>'
        f'<th style="padding:8px;text-align:left;font-size:11px;color:#64748b;">任务名称</th>'
        f'<th style="padding:8px;text-align:left;font-size:11px;color:#64748b;">音频</th>'
        f'<th style="padding:8px;text-align:left;font-size:11px;color:#64748b;">视频</th>'
        f'<th style="padding:8px;text-align:left;font-size:11px;color:#64748b;">状态</th>'
        f'<th style="padding:8px;width:36px;"></th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def _hint(kind, msg):
    """生成提示 HTML 小条"""
    if kind == "ok":
        bg, ic, tc = "#f0fdf4", "✅", "#15803d"
    elif kind == "warning":
        bg, ic, tc = "#fff7ed", "⚠️", "#92400e"
    else:
        bg, ic, tc = "#fff1f2", "❌", "#be123c"
    return (f'<div style="background:{bg};border-radius:8px;padding:8px 12px;'
            f'font-size:12px;color:{tc};font-weight:600;'
            f'font-family:Microsoft YaHei,sans-serif;margin-top:4px;">'
            f'{ic} {msg}</div>')


def _render_batch_prog(done, total, cur_name, status, msg, out_folder=""):
    pct = int(done / total * 100) if total else 0
    sc = {"运行中": "#6366f1", "已完成": "#16a34a", "失败": "#dc2626"}.get(status, "#64748b")
    folder_hint = f'<div style="font-size:11px;color:#64748b;margin-top:8px;">' + '\U0001f4c1' + f' 输出目录：{out_folder}</div>' if out_folder else ""
    return f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1.5px solid #6366f1;border-radius:12px;padding:14px 16px;font-family:Microsoft YaHei,sans-serif;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;"><span style="width:10px;height:10px;border-radius:50%;background:{sc};flex-shrink:0;"></span><span style="font-size:13px;font-weight:700;color:#e2e8f0;">{status}</span><span style="margin-left:auto;font-size:13px;font-weight:800;color:#6366f1;">{done}/{total}</span></div><div style="background:rgba(99,102,241,.15);border-radius:6px;height:8px;overflow:hidden;margin-bottom:8px;"><div style="height:100%;width:{pct}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:6px;"></div></div><div style="font-size:12px;color:#94a3b8;">{msg}</div>{folder_hint}</div>'


# ══════════════════════════════════════════════════════════════
#  WebSocket 文案提取器（全局单例，保持长连接）
# ══════════════════════════════════════════════════════════════
class TextExtractor:
    """WebSocket 文案提取器，保持长连接"""
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
        """从本地获取卡密"""
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
        """连接WebSocket并注册"""
        if not _WS_OK:
            safe_print("[TextExtractor] websockets 模块未安装")
            return False
        
        try:
            license_key = self._get_license_key()
            if not license_key:
                safe_print("[TextExtractor] 未找到卡密")
                return False
            
            # safe_print(f"[TextExtractor] 正在连接 {self._ws_url}")  # 移除域名日志
            self._ws = await websockets.connect(
                self._ws_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            self._connected = True
            safe_print("[TextExtractor] WebSocket 连接成功")
            
            # 发送注册消息
            register_msg = json.dumps({"type": "register", "key": license_key})
            await self._ws.send(register_msg)
            # safe_print(f"[TextExtractor] 已发送注册消息")  # 移除日志
            
            # 等待注册响应
            try:
                response = await asyncio.wait_for(self._ws.recv(), timeout=10)
                # safe_print(f"[TextExtractor] 收到注册响应: {response}")  # 移除日志
                self._registered = True
            except asyncio.TimeoutError:
                safe_print("[TextExtractor] 注册响应超时，继续运行")
                self._registered = True  # 即使超时也继续
            
            return True
        except Exception as e:
            safe_print(f"[TextExtractor] 连接失败: {e}")
            self._connected = False
            self._registered = False
            return False
    
    async def _listen_loop(self):
        """监听WebSocket消息"""
        while self._connected and self._ws:
            try:
                message = await self._ws.recv()
                # safe_print(f"[TextExtractor] 收到消息: {message[:200]}..." if len(message) > 200 else f"[TextExtractor] 收到消息: {message}")  # 移除日志
                self._response_queue.put(message)
            except websockets.exceptions.ConnectionClosed:
                safe_print("[TextExtractor] 连接已关闭，尝试重连...")
                self._connected = False
                # 尝试重连
                await asyncio.sleep(2)
                await self._connect_and_register()
            except Exception as e:
                safe_print(f"[TextExtractor] 监听错误: {e}")
                break
    
    def _run_event_loop(self):
        """在后台线程运行事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # 连接并注册
        self._loop.run_until_complete(self._connect_and_register())
        
        # 开始监听
        if self._connected:
            try:
                self._loop.run_until_complete(self._listen_loop())
            except Exception as e:
                safe_print(f"[TextExtractor] 事件循环错误: {e}")
    
    def start(self):
        """启动WebSocket连接（后台线程）"""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._thread.start()
            safe_print("[TextExtractor] 后台线程已启动")
    
    def send_request(self, request_data: dict, timeout: float = 30.0,
                    response_type: str = None, request_id: str = None) -> tuple:
        """
        发送通用WebSocket请求
        :param request_data: 请求数据字典
        :param timeout: 超时时间（秒）
        :param response_type: 期望的响应类型（如 "chatglm_video_result"）
        :param request_id: 请求ID，用于匹配响应
        :return: (success, data_or_error)
        """
        if not _WS_OK:
            return False, "websockets 模块未安装"

        if not self._connected or not self._ws:
            self.start()
            time.sleep(2)

        if not self._connected:
            return False, "WebSocket 未连接"

        try:
            # 在事件循环中发送消息
            async def send_msg():
                await self._ws.send(json.dumps(request_data))

            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(send_msg(), self._loop)
                future.result(timeout=5)
            else:
                return False, "事件循环未运行"

            # 等待响应
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = self._response_queue.get(timeout=1)
                    data = json.loads(response)

                    # 如果指定了 request_id，检查是否匹配
                    if request_id and data.get("request_id") != request_id:
                        # 不匹配，放回队列
                        self._response_queue.put(response)
                        continue

                    # 如果指定了 response_type，检查类型
                    if response_type and data.get("type") == response_type:
                        return True, data

                    # 处理通用响应类型
                    msg_type = data.get("type", "")
                    if msg_type == "ack":
                        continue  # 跳过 ack，继续等待最终结果
                    elif msg_type == "gpu_offline" or msg_type == "gpu.power.offline":
                        return False, data.get("msg", "GPU服务器未上线，任务已排队，服务器启动后自动执行（约2分钟）")
                    elif msg_type == "gpu.power.online":
                        # 开机在线广播，不是本请求最终结果，继续等待业务结果
                        continue
                    elif msg_type == "error":
                        return False, data.get("message", "请求失败")
                    elif msg_type == "kicked":
                        return False, "连接被服务器踢出"
                    elif not response_type:
                        # 如果没有指定响应类型，返回任何非 ack 的响应
                        return True, data

                except _queue.Empty:
                    continue
                except json.JSONDecodeError:
                    continue

            return False, "请求超时"

        except Exception as e:
            return False, f"发送请求失败: {e}"

    def extract_text(self, url_or_content: str, timeout: float = 30.0) -> tuple:
        """
        提取文案
        :param url_or_content: URL或内容
        :param timeout: 超时时间（秒）
        :return: (success, content_or_error)
        """
        if not _WS_OK:
            return False, "websockets 模块未安装，请运行: pip install websockets"

        if not self._connected or not self._ws:
            # 尝试启动连接
            self.start()
            time.sleep(2)  # 等待连接建立

        if not self._connected:
            return False, "WebSocket 未连接，请检查网络"

        # 清空队列中的旧消息
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except _queue.Empty:
                break

        # 发送提取请求
        try:
            extract_msg = json.dumps({"type": "url", "url": url_or_content})

            # 在事件循环中发送消息
            async def send_msg():
                await self._ws.send(extract_msg)

            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(send_msg(), self._loop)
                future.result(timeout=5)
            else:
                return False, "事件循环未运行"

            safe_print(f"[TextExtractor] 已发送提取请求: {url_or_content[:50]}...")

            # 等待响应
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = self._response_queue.get(timeout=1)
                    data = json.loads(response)

                    if data.get("type") == "result":
                        content = data.get("content", "")
                        is_error = data.get("error", False)

                        if is_error:
                            # 错误情况：返回失败和错误信息
                            return False, content
                        elif content:
                            # 成功情况：返回成功和内容
                            return True, content
                        else:
                            return False, "返回内容为空"
                    elif data.get("type") == "error":
                        return False, data.get("message", "提取失败")
                except _queue.Empty:
                    continue
                except json.JSONDecodeError:
                    continue

            return False, "请求超时，请重试"

        except Exception as e:
            return False, f"发送请求失败: {e}"


# 全局文案提取器实例
_text_extractor = None

def get_text_extractor():
    """获取全局文案提取器实例"""
    global _text_extractor
    if _text_extractor is None:
        _text_extractor = TextExtractor()
    return _text_extractor

# ══════════════════════════════════════════════════════════════
#  构建 UI
# ══════════════════════════════════════════════════════════════
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

        # ── 进度提示横幅（视频合成时显示）────────────────────
        progress_banner = gr.HTML(
            value='',
            elem_id="zdai-progress-banner",
            visible=False,
        )

        # ════════════════════ 顶层 Tabs ════════════════════
        with gr.Tabs():

            # ── Tab 1：工作台 ────────────────────────────────
            with gr.Tab("🎬  工作台"):
                # ══ 顶部工作台记录管理区 ══
                with gr.Group(elem_classes="panel", elem_id="workspace-record-panel"):
                    gr.HTML('<div style="font-size:14px;font-weight:700;color:#334155;margin-bottom:12px;">💾 工作台记录</div>')
                    
                    with gr.Row():
                        # 左侧：下拉框
                        workspace_record_dropdown = gr.Dropdown(
                            label="选择记录",
                            choices=[],
                            value=None,
                            interactive=True,
                            scale=2,
                            elem_id="workspace-record-dropdown"
                        )
                        
                        # 右侧：4个按钮，两排两列
                        with gr.Column(scale=1, elem_id="workspace-record-buttons"):
                            with gr.Row():
                                workspace_restore_btn = gr.Button("🔄 恢复", variant="primary", scale=1, size="sm")
                                workspace_delete_btn = gr.Button("🗑 删除", variant="secondary", scale=1, size="sm", elem_classes="danger-btn")
                            with gr.Row():
                                workspace_refresh_btn = gr.Button("🔄 刷新列表", variant="secondary", scale=1, size="sm")
                                workspace_clear_btn = gr.Button("🗑 清空所有记录", variant="secondary", scale=1, size="sm", elem_classes="danger-btn")
                    
                    workspace_record_hint = gr.HTML(value="")
                
                with gr.Row(elem_classes="workspace"):

                    # ═══ 步骤 1：文案提取 + 步骤 2：音频合成 ═══════════════════════════
                    with gr.Column(scale=1):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">1</div>'
                            '<span class="step-title">文案提取</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            # ── 文案提取功能区 ──
                            with gr.Group(elem_classes="extract-panel"):
                                gr.HTML(
                                    '<div class="extract-header">'
                                    '<span class="extract-icon">🔗</span>'
                                    '<span class="extract-title">智能文案提取</span>'
                                    '<span class="extract-badge">AI</span>'
                                    '</div>'
                                )
                                extract_input = gr.Textbox(
                                    label="",
                                    placeholder="粘贴抖音/小红书/公众号等链接，或直接输入内容...",
                                    lines=2,
                                    elem_classes="extract-input"
                                )
                                gr.HTML(
                                    '<div class="extract-tip">'
                                    '支持主流平台链接，一键提取文案内容'
                                    '</div>'
                                )
                                extract_btn = gr.Button(
                                    "✨ 提取文案",
                                    variant="primary",
                                    size="sm",
                                    elem_classes="extract-btn"
                                )
                                extract_hint = gr.HTML(value="", elem_classes="extract-hint")
                                
                                # ── AI改写功能（放在提取框内） ──
                                gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:4px 8px;margin-top:12px;margin-bottom:8px;">AI智能改写文案，同时生成标题和话题标签</div>')
                                rewrite_btn = gr.Button("✨ AI改写 + 标题标签", variant="secondary", size="sm")
                            
                            input_text = gr.TextArea(
                                label="文案内容",
                                placeholder="在此输入或粘贴文案内容，或使用上方提取功能...",
                                lines=6)

                        # ═══ 步骤 2：音频合成 ═══════════════════════════
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">2</div>'
                            '<span class="step-title">音频合成</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            audio_mode = gr.Radio(
                                label="选择音频来源",
                                choices=["文字转语音", "直接上传音频"],
                                value="文字转语音",
                                elem_classes="audio-mode-radio")

                            # ── 模式A: 文字转语音 ──
                            with gr.Group(visible=True) as tts_mode_group:
                                # ── TTS 模式切换 ──
                                # 重新读取配置确保获取最新值
                                load_env_file()
                                current_tts_mode = os.getenv('TTS_MODE', 'local')
                                tts_mode_switch = gr.Radio(
                                    label="TTS 模式",
                                    choices=["💻 本地版", "☁️ 在线版"],
                                    value="💻 本地版" if current_tts_mode == 'local' else "☁️ 在线版",
                                    elem_classes="voice-style-radio")
                                gr.HTML(
                                    '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                    '💻 <b>本地版</b>：使用本机 GPU 处理，需要较高配置<br>'
                                    '☁️ <b>在线版</b>：使用云端服务器处理，无需高配置显卡</div>'
                                )
                                
                                gr.HTML('<div class="section-label">🎙 音色选择</div>')
                                with gr.Row():
                                    # 根据当前TTS模式过滤音色列表
                                    voice_select = gr.Dropdown(
                                        label="从音色库选择",
                                        choices=_vc.get_choices(current_tts_mode) if _LIBS_OK else [],
                                        value=None, interactive=True, scale=4)
                                    voice_refresh_btn = gr.Button("⟳", scale=1, min_width=40,
                                                                  variant="secondary")
                                voice_preview = gr.Audio(label="🔊 试听所选音色", interactive=False,
                                                         visible=False)
                                
                                # 隐藏的 prompt_audio 组件（用于内部逻辑，不显示给用户）
                                prompt_audio = gr.Audio(visible=False, type="filepath")

                                # ── 语音风格预设（仅本地版可见）──
                                _is_local_tts = (current_tts_mode == 'local')
                                with gr.Group(visible=_is_local_tts) as local_only_settings_group:
                                    voice_style = gr.Radio(
                                        label="语音风格",
                                        choices=["标准", "稳定播报", "活泼生动", "慢速朗读", "专业模式"],
                                        value="标准",
                                        elem_classes="voice-style-radio")
                                    # ── 合成速度预设 ──
                                    tts_speed_preset = gr.Radio(
                                        label="合成速度",
                                        choices=list(TTS_SPEED_PRESETS.keys()),
                                        value="🚀 快速",
                                        elem_classes="voice-style-radio")
                                    gr.HTML(
                                        '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                        '⚡极快：最快速度，适合预览试听<br>'
                                        '🚀快速：速度优先，默认推荐（FP16）<br>'
                                        '⚖️标准：速度与质量兼顾<br>'
                                        '✨高质量：最佳语音质量，速度较慢</div>'
                                    )

                                    voice_speed = gr.Slider(
                                        label="语速调节",
                                        info="← 慢  |  快 →",
                                        minimum=0.5, maximum=1.5, value=1.0, step=0.05)

                                with gr.Group(visible=False) as pro_mode_group:
                                    with gr.Row():
                                        top_p = gr.Slider(label="词语多样性", info="越高越随机 0.7~0.9", minimum=0.1, maximum=1.0, value=0.8, step=0.05)
                                        top_k = gr.Slider(label="候选词数量", info="越小越保守 20~50", minimum=1, maximum=100, value=30, step=1)
                                    with gr.Row():
                                        temperature = gr.Slider(label="语气活跃度", info="越高越有变化", minimum=0.1, maximum=2.0, value=0.7, step=0.1)
                                        num_beams   = gr.Slider(label="搜索精度", info="越高越慢但更准", minimum=1, maximum=10, value=1, step=1)
                                    with gr.Row():
                                        repetition_penalty = gr.Slider(label="避免重复", info="越高越不重复", minimum=1.0, maximum=20.0, value=8.0, step=0.5)
                                        max_mel_tokens     = gr.Slider(label="最大长度", info="长文本需加大", minimum=500, maximum=3000, value=1500, step=100)
                                    gr.HTML('<div class="divider"></div>')
                                    gr.Markdown("### 🎭 情感控制")
                                    emo_mode = gr.Radio(
                                        label="情感控制模式",
                                        choices=["与音色参考音频相同","使用情感参考音频","使用情感向量控制","使用情感描述文本控制"],
                                        value="与音色参考音频相同")
                                    with gr.Group(visible=False) as emo_audio_group:
                                        emo_audio  = gr.Audio(label="情感参考音频", sources=["upload"], type="filepath")
                                        emo_weight = gr.Slider(label="情感强度", info="0=不混合情感，1=完全使用情感参考", minimum=0.0, maximum=1.0, value=0.6, step=0.1)
                                    with gr.Group(visible=False) as emo_vec_group:
                                        gr.Markdown("调整8个情感向量维度（-1.0 到 1.0）")
                                        with gr.Row():
                                            vec1 = gr.Slider(label="向量1", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                            vec2 = gr.Slider(label="向量2", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                        with gr.Row():
                                            vec3 = gr.Slider(label="向量3", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                            vec4 = gr.Slider(label="向量4", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                        with gr.Row():
                                            vec5 = gr.Slider(label="向量5", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                            vec6 = gr.Slider(label="向量6", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                        with gr.Row():
                                            vec7 = gr.Slider(label="向量7", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                            vec8 = gr.Slider(label="向量8", minimum=-1.0, maximum=1.0, value=0.0, step=0.1)
                                    with gr.Group(visible=False) as emo_text_group:
                                        emo_text = gr.Textbox(
                                            label="情感描述文本",
                                            placeholder="例如：开心、悲伤、愤怒...",
                                            lines=2)
                                    def update_emo_visibility(mode):
                                        return (
                                            gr.update(visible=(mode=="使用情感参考音频")),
                                            gr.update(visible=(mode=="使用情感向量控制")),
                                            gr.update(visible=(mode=="使用情感描述文本控制")))
                                    emo_mode.change(update_emo_visibility,
                                                    inputs=[emo_mode],
                                                    outputs=[emo_audio_group, emo_vec_group, emo_text_group])
                                gen_btn      = gr.Button("🎵  开始语音合成", variant="primary", size="lg")
                                tts_hint = gr.HTML(value="")
                                output_audio = gr.Audio(label="合成结果", interactive=False)

                            # ── 模式B: 直接上传音频 ──
                            with gr.Group(visible=False) as upload_mode_group:
                                gr.HTML(
                                    '<div style="background:#f0f9ff;border:1.5px solid #bae6fd;'
                                    'border-radius:12px;padding:12px 14px;margin-bottom:12px;">'
                                    '<div style="font-size:13px;font-weight:700;color:#0c4a6e;margin-bottom:4px;">📁 直接上传音频文件</div>'
                                    '<div style="font-size:11px;color:#0369a1;line-height:1.6;">'
                                    '上传已有的音频文件，跳过语音合成步骤，直接用于视频合成。<br>'
                                    '支持 WAV、MP3 等常见格式。</div></div>'
                                )
                                direct_audio_upload = gr.Audio(
                                    label="上传音频文件（WAV / MP3）",
                                    sources=["upload"], type="filepath")

                    # ═══ 步骤 3：视频合成 ═══════════════════════════
                    with gr.Column(scale=2):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">3</div>'
                            '<span class="step-title">视频合成</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            # ── 数字人选择 ──
                            gr.HTML('<div class="section-label">🎭 数字人选择</div>')
                            with gr.Row():
                                avatar_select = gr.Dropdown(
                                    label="从数字人库选择",
                                    choices=_av.get_choices() if _LIBS_OK else [],
                                    value=None, interactive=True, scale=4)
                                avatar_refresh_btn = gr.Button("⟳", scale=1, min_width=40,
                                                               variant="secondary")
                            avatar_preview = gr.Video(
                                label="预览", height=190, interactive=False, visible=False)
                            avatar_preview_title = gr.HTML(value="", visible=False)

                            # ── 合成音频 ──
                            gr.HTML('<div class="section-label">🔊 音频（自动引用步骤1的结果，也可手动上传）</div>')
                            audio_for_ls = gr.Audio(
                                label="用于视频合成的音频",
                                type="filepath", interactive=True)

                            # ── 合成模式选择（本地版/在线版）──
                            _default_heygem = os.getenv("HEYGEM_MODE", "local").strip().lower()
                            _heygem_default_label = "🌐 在线版（服务器）" if _default_heygem == "online" else "💻 本地版"
                            gr.HTML('<div class="section-label">🖥️ 合成模式</div>')
                            heygem_mode_radio = gr.Radio(
                                label="选择合成方式",
                                choices=["💻 本地版", "🌐 在线版（服务器）"],
                                value=_heygem_default_label,
                                elem_classes="voice-style-radio")
                            gr.HTML(
                                '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                '💻本地版：使用本机GPU合成，需要 heygem-win-50<br>'
                                '🌐在线版：上传到Linux服务器合成，需配置 HEYGEM_SERVER_URL</div>'
                            )

                            # ── 生成质量选择（仅本地版可见）──
                            _show_quality = (_default_heygem != "online")
                            with gr.Group(visible=_show_quality) as quality_group:
                                gr.HTML('<div class="section-label">⚙️ 生成质量</div>')
                                quality_preset = gr.Radio(
                                    label="速度 ↔ 质量",
                                    choices=list(QUALITY_PRESETS.keys()),
                                    value="⚖️ 标准",
                                    elem_classes="voice-style-radio")
                                gr.HTML(
                                    '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                    '⚡极快：6步，速度最快，适合预览<br>'
                                    '🚀快速：8步，速度与质量兼顾<br>'
                                    '⚖️标准：12步，默认推荐<br>'
                                    '✨高质量：20步，效果最佳但较慢</div>'
                                )

                            ls_btn = gr.Button("🚀  开始合成", variant="primary", size="lg")
                            
                            # ── 合成视频显示区（在步骤3内部）──
                            ls_detail_html = gr.HTML(value="", visible=False, elem_id="ls-detail-box")
                            output_video = gr.Video(
                                label="✨ 合成视频",
                                height=400, elem_id="output-video", interactive=False)

                    # ═══ 步骤 4：字幕合成与画中画 ═══════════════════════════
                    with gr.Column(scale=2):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">4</div>'
                            '<span class="step-title">字幕合成与画中画</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            # ══ 画中画设置 ══════════════════════════════
                            with gr.Group(elem_classes="pip-panel"):
                                gr.HTML(
                                    '<div class="subtitle-panel-head">'
                                    '<div class="subtitle-panel-icon">🖼</div>'
                                    '<span class="subtitle-panel-title">画中画设置</span>'
                                    '</div>'
                                )
                                pip_enable = gr.Checkbox(
                                    label="🖼 启用画中画",
                                    value=False,
                                    elem_classes="kw-checkbox")
                                with gr.Group(visible=False) as pip_settings_group:
                                    pip_mode = gr.Radio(
                                        choices=["🌐 在线生成", "📁 本地上传"],
                                        value="🌐 在线生成",
                                        label="画中画模式",
                                        elem_classes="audio-mode-radio")
                                    # 在线模式：提示词
                                    with gr.Group() as pip_online_group:
                                        pip_prompt = gr.TextArea(
                                            label="🎬 画中画提示词",
                                            placeholder="描述你想要的实景画面，如：现代室内装修施工场景，画面干净高级...\n（AI改写时会自动生成）",
                                            lines=3, max_lines=5)
                                        gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:2px 8px;">'
                                                '提示词越详细，生成的画面越精准。点击「AI改写+标题标签」可自动生成。</div>')
                                    # 本地上传模式
                                    with gr.Group(visible=False) as pip_local_group:
                                        pip_local_files = gr.File(
                                            label="📁 上传画中画视频素材",
                                            file_types=["video"],
                                            file_count="multiple")
                                        gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:2px 8px;">'
                                                '上传1-3个视频片段，将静音后穿插到合成视频中。</div>')
                                    # 通用设置（AI自动决定穿插位置和时长，隐藏手动控制）
                                    with gr.Row(visible=False):
                                        pip_interval = gr.Slider(
                                            minimum=8, maximum=30, value=15, step=1,
                                            label="穿插间隔(秒)")
                                        pip_clip_dur = gr.Slider(
                                            minimum=3, maximum=8, value=5, step=1,
                                            label="每段时长(秒)")
                                    pip_btn = gr.Button("🎬 生成画中画视频", variant="primary", size="lg")
                                    pip_hint = gr.HTML(value="")
                            
                            # ══ 字幕面板 ══════════════════════════════
                            with gr.Group(elem_classes="subtitle-panel", elem_id="subtitle-panel-main"):
                                gr.HTML(
                                    '<div class="subtitle-panel-head">'
                                    '<div class="subtitle-panel-icon">✏️</div>'
                                    '<span class="subtitle-panel-title">智能字幕</span>'
                                    '<span class="subtitle-panel-tip">✨ 支持关键词高亮</span>'
                                    '</div>'
                                )
                                # 基本设置：字体 字号 位置（始终可见）
                                with gr.Row():
                                    _font_grouped = _sub.get_font_choices_grouped() if _LIBS_OK else [("🖥️ 系统字体（默认）", "系统字体"), ("【中文简体】思源黑体 Bold", "SourceHanSansCN-Bold")]
                                    sub_font = gr.Dropdown(
                                        label="字体",
                                        choices=_font_grouped,
                                        value="系统字体",
                                        interactive=True, scale=3)
                                    sub_size = gr.Slider(label="字号 px", minimum=16, maximum=72,
                                                         value=44, step=2, scale=3)
                                    sub_pos = gr.Radio(label="位置", choices=["上","中","下"],
                                                       value="下", scale=2,
                                                       elem_classes="sub-pos-radio")
                                # 字体预览区域
                                sub_font_preview = gr.HTML(value="", visible=False, elem_id="sub-font-preview")
                                # ── 高级设置按钮（弹窗入口）──
                                sub_settings_open_btn = gr.Button(
                                    "⚙️ 高级设置", variant="secondary", size="sm",
                                    elem_classes="sub-settings-btn")

                            # ── 字幕高级设置弹窗（独立于字幕面板）──
                            # visible=True 确保 DOM 始终存在；CSS display:none!important 默认隐藏；
                            # JS .zdai-open 类控制显示（彻底绕开 Gradio visible 在不同版本的差异）
                            with gr.Group(visible=True, elem_id="sub-settings-modal") as sub_settings_modal:
                                gr.HTML(
                                    '<div style="text-align:center;margin-bottom:16px;">'
                                    '<div style="width:44px;height:44px;border-radius:12px;'
                                    'background:linear-gradient(135deg,#0ea5e9,#0284c7);'
                                    'display:flex;align-items:center;justify-content:center;'
                                    'margin:0 auto 12px;font-size:20px;'
                                    'box-shadow:0 4px 12px rgba(14,165,233,.3);">⚙️</div>'
                                    '<div style="font-size:17px;font-weight:800;color:#0f172a;">字幕高级设置</div>'
                                    '</div>'
                                )
                                with gr.Row(elem_classes="sub-modal-columns"):
                                    # ══ 左侧：颜色与样式 + 关键词高亮 ══
                                    with gr.Column(scale=1, min_width=260):
                                        gr.HTML('<div class="sub-modal-section">🎨 颜色与样式</div>')
                                        sub_color_txt = gr.ColorPicker(
                                            label="字幕颜色", value="#FFFFFF")
                                        sub_hi_txt = gr.ColorPicker(
                                            label="高亮颜色", value="#FFD700")
                                        sub_outline_txt = gr.ColorPicker(
                                            label="描边颜色", value="#000000",
                                            elem_id="sub-outline-color")
                                        sub_outline_size = gr.Slider(
                                            label="描边宽度 px", minimum=0, maximum=10,
                                            value=6, step=1)
                                        # 背景颜色隐藏（不再使用）
                                        sub_bg_color = gr.ColorPicker(
                                            value="#000000", visible=False)
                                        sub_bg_opacity = gr.Slider(
                                            value=0, visible=False)
                                        gr.HTML('<div class="sub-modal-section" style="margin-top:14px;">🌟 关键词高亮</div>')
                                        with gr.Row():
                                            sub_kw_enable = gr.Checkbox(
                                                label="🌟 启用关键词放大高亮", value=False,
                                                scale=2, elem_classes="kw-checkbox")
                                            sub_hi_scale = gr.Slider(
                                                label="放大倍数", minimum=1.1, maximum=2.5,
                                                value=1.5, step=0.1, scale=2, visible=False)
                                        with gr.Row(visible=False) as sub_kw_row:
                                            sub_kw_text = gr.Textbox(
                                                label="关键词（逗号分隔）",
                                                placeholder="如：便宜,优质,推荐,限时  — 多个词用逗号隔开",
                                                max_lines=1, scale=1)
                                        
                                        gr.HTML('<div class="sub-modal-section" style="margin-top:14px;">📍 位置微调</div>')
                                        sub_pos_offset = gr.Slider(
                                            label="垂直偏移 px（正数向上，负数向下）",
                                            minimum=-200, maximum=200,
                                            value=0, step=5,
                                            info="在基础位置上微调"
                                        )
                                    # ══ 右侧：AI优化 + 标题设置 + 字幕内容 ══
                                    with gr.Column(scale=1, min_width=260):
                                        gr.HTML('<div class="sub-modal-section">✨ AI优化字幕</div>')
                                        gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:4px 8px;margin-bottom:8px;">AI智能优化字幕标题和关键词高亮</div>')
                                        subtitle_ai_optimize_btn = gr.Button("✨ AI优化字幕", variant="secondary", size="sm")
                                        
                                        gr.HTML('<div class="sub-modal-section" style="margin-top:14px;">📌 标题设置</div>')
                                        sub_title_text = gr.Textbox(
                                            label="标题第一行",
                                            placeholder="输入第一行标题文字，留空则不显示标题",
                                            max_lines=1)
                                        sub_title_text2 = gr.Textbox(
                                            label="标题第二行",
                                            placeholder="输入第二行标题文字（可选）",
                                            max_lines=1)
                                        with gr.Row():
                                            sub_title_font_size = gr.Slider(
                                                label="标题字号", minimum=12, maximum=96,
                                                value=68, step=1, scale=2)
                                            sub_title_duration = gr.Slider(
                                                label="显示时长(秒)", minimum=1, maximum=30,
                                                value=5, step=1, scale=2)
                                        with gr.Row():
                                            sub_title_margin_top = gr.Slider(
                                                label="距顶部距离 px", minimum=0, maximum=400,
                                                value=200, step=5, scale=2)
                                        with gr.Row():
                                            sub_title_color = gr.ColorPicker(
                                                label="标题颜色", value="#FFD700", scale=1)
                                            sub_title_outline_color = gr.ColorPicker(
                                                label="标题描边颜色", value="#000000", scale=1)
                                        sub_text_modal = gr.Textbox(
                                            label="字幕内容",
                                            value="",
                                            visible=False,
                                            lines=1)
                                # ── 底部按钮（全宽）──
                                with gr.Row():
                                    sub_settings_cancel_btn = gr.Button(
                                        "取消", variant="secondary", size="lg",
                                        elem_classes="sub-modal-close-btn")
                                    sub_settings_close_btn = gr.Button(
                                        "✅ 确定", variant="primary", size="lg",
                                        elem_classes="sub-modal-close-btn")

                            with gr.Group(elem_classes="subtitle-panel", elem_id="subtitle-panel-tail"):
                                # ── 字幕文本 + 按钮（始终可见）──
                                sub_text = gr.Textbox(
                                    label="字幕内容（语音合成后自动填入）",
                                    placeholder="完成步骤1语音合成后会自动填入文字，也可手动编辑...",
                                    lines=2,
                                    visible=False)
                                sub_btn = gr.Button("✨  生成带字幕视频", variant="primary", size="lg")
                                sub_hint = gr.HTML(value="")
                        
                        # 字幕视频显示区（独立的panel，紧跟在字幕面板后面）
                        with gr.Column(elem_classes="panel", visible=False, elem_id="sub-video-panel") as sub_video_panel:
                            sub_video = gr.Video(label="🎬 字幕版视频", height=280,
                                                 interactive=False)

                        # 步骤5：BGM背景音乐
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">5</div>'
                            '<span class="step-title">BGM背景音乐</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            bgm_enable = gr.Checkbox(label="🎵 启用背景音乐", value=False, elem_classes="kw-checkbox")
                            
                            bgm_types = gr.CheckboxGroup(
                                label="背景音乐类型",
                                choices=list(_load_music_database().keys()),
                                value=[],
                            )
                            bgm_volume = gr.Slider(
                                label="背景音乐音量",
                                minimum=0.0, maximum=2.0, value=0.3, step=0.05
                            )
                            with gr.Row():
                                bgm_change_btn = gr.Button("🔄 更换BGM", variant="secondary", size="sm")
                                bgm_mix_btn = gr.Button("🎬 AI选择BGM", variant="primary", size="sm")
                                bgm_custom_btn = gr.UploadButton("📁 上传自定义BGM", file_types=["audio"], variant="secondary", size="sm")
                            # 隐藏的自定义BGM组件（用于内部逻辑）
                            bgm_custom_upload = gr.Audio(visible=False, type="filepath")
                            bgm_selected = gr.Textbox(visible=False, value="")
                            bgm_audio_preview = gr.Audio(label="试听BGM", interactive=False, visible=False)
                            bgm_hint = gr.HTML(value="")
                            bgm_path_hidden = gr.Textbox(visible=False, value="")
                            bgm_state = gr.State(value=None)
                            bgm_video = gr.Video(label="🎬 带BGM视频", height=280, interactive=False)

                        # 步骤6：发布平台（下方）
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">6</div>'
                            '<span class="step-title">发布平台</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            gr.HTML('<div style="font-size:13px;color:#64748b;margin-bottom:12px;">优先发布带BGM视频，其次字幕视频，如无字幕则发布合成视频</div>')
                            
                            publish_platforms = gr.CheckboxGroup(
                                label="选择发布平台",
                                choices=["抖音", "视频号", "哔哩哔哩", "小红书", "快手"],
                                value=["抖音"],
                                elem_classes="publish-platform-checkbox"
                            )
                            
                            douyin_title = gr.Textbox(
                                label="视频标题",
                                placeholder="自动使用语音文字前30字，也可手动修改...",
                                max_lines=2)
                            
                            douyin_topics = gr.Textbox(
                                label="话题标签（逗号分隔）",
                                placeholder="如：美食,探店,推荐",
                                max_lines=1)
                            
                            gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:4px 8px;margin-bottom:8px;">使用AI智能优化标题并生成5个话题标签</div>')
                            optimize_btn = gr.Button("✨ AI优化", variant="secondary", size="sm")
                            
                            douyin_btn = gr.Button("🚀 发布到选中平台", variant="primary", size="lg")
                            douyin_hint = gr.HTML(value="")
                    
            # ── Tab 2：数字人管理 ────────────────────────
            with gr.Tab("🎭  数字人"):
                with gr.Row(elem_classes="workspace"):

                    # 左列：上传
                    with gr.Column(scale=1):
                        # 标题在外面，有独立背景
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);">＋</div>'
                            '<span class="step-title">添加数字人</span>'
                            '</div>'
                        )
                        # 内容在白色panel里
                        with gr.Column(elem_classes="panel"):
                            av_upload = gr.File(
                                label="上传视频（MP4 / AVI / MOV / WMV）",
                                file_types=["video"], type="filepath")
                            av_upload_preview = gr.Video(
                                label="预览", height=150, interactive=False, visible=False)
                            av_name = gr.Textbox(
                                label="数字人名称",
                                placeholder="为此数字人起一个名字...", max_lines=1)
                            av_save_btn  = gr.Button("💾  保存", variant="primary", size="lg")
                            av_save_hint = gr.HTML(value="")
                            gr.HTML(
                                '<div style="font-size:11px;color:#94a3b8;line-height:2;margin-top:10px;">'
                                '💡 保存后可在工作台直接选用<br>'
                                '📁 存储于 <b>avatars/</b> 目录</div>'
                            )
                            # 隐藏的删除控件（由列表按钮触发）
                            av_del_dd   = gr.Textbox(visible=False, value="")
                            av_del_btn  = gr.Button("删除", visible=False)
                            av_del_hint = gr.HTML(value="")

                    # 右列：画廊（行内🗑）+ JS桥接隐藏输入 + 预览
                    with gr.Column(scale=2):
                        # 标题在外面，有独立背景
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">📋</div>'
                            '<span class="step-title">数字人库</span>'
                            '</div>'
                        )
                        # 内容在白色panel里
                        with gr.Column(elem_classes="panel"):
                            av_gallery = gr.HTML(
                                value=_av.render_gallery("av-del-input", "av-prev-trigger") if _LIBS_OK else "")
                            # JS桥接：卡片上的🗑按钮写入此隐藏textbox触发删除
                            with gr.Row(elem_id="av-del-input-row"):
                                av_del_js_input = gr.Textbox(
                                elem_id="av-del-input", value="", interactive=True)
                        # JS桥接：卡片点击写入此隐藏textbox触发预览
                        with gr.Row(elem_id="av-prev-trigger-row"):
                            av_prev_js_input = gr.Textbox(
                                elem_id="av-prev-trigger", value="", interactive=True)
                        av_del_real_hint = gr.HTML(value="")
                        gr.HTML('<div class="divider"></div>')
                        gr.HTML('<div class="section-label">🔍 预览（点击上方卡片）</div>')
                        av_prev_video = gr.Video(label="", height=240, interactive=False)
                        av_prev_title = gr.HTML(value="")

            # ── Tab 4：音色模型 ───────────────────────────
            with gr.Tab("🎙  音色模型"):
                with gr.Row(elem_classes="workspace"):

                    # 左列：上传
                    with gr.Column(scale=1):
                        # 标题在外面，有独立背景
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#0ea5e9,#0284c7);">＋</div>'
                            '<span class="step-title">添加音色</span>'
                            '</div>'
                        )
                        # 内容在白色panel里
                        with gr.Column(elem_classes="panel"):
                            # ── 版本选择 ──
                            vc_source = gr.Radio(
                                label="音色版本",
                                choices=["💻 本地版（本机处理）", "☁️ 在线版（云端处理）"],
                                value="💻 本地版（本机处理）",
                                elem_classes="voice-style-radio")
                            gr.HTML(
                                '<div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:2px 8px 8px;">'
                                '💻 <b>本地版</b>：使用本机 GPU 处理，需要较高配置<br>'
                                '☁️ <b>在线版</b>：使用云端服务器处理，无需高配置显卡</div>'
                            )
                            vc_upload = gr.Audio(
                                label="上传参考音频（3-10秒 WAV/MP3）",
                                sources=["upload"], type="filepath")
                            vc_name = gr.Textbox(
                                label="音色名称",
                                placeholder="为此音色起一个名字...", max_lines=1)
                            vc_save_btn  = gr.Button("💾  保存", variant="primary", size="lg")
                            vc_save_hint = gr.HTML(value="")
                            gr.HTML(
                                '<div style="font-size:11px;color:#94a3b8;line-height:2;margin-top:10px;">'
                                '💡 保存后可在工作台直接选用<br>'
                                '💻 本地版存储于 <b>voices/</b> 目录<br>'
                                '☁️ 在线版存储在云端服务器</div>'
                            )
                            # ── 同步在线音色按钮 ──
                            vc_sync_btn = gr.Button("🔄 同步在线音色", variant="secondary", size="sm")
                            vc_del_dd   = gr.Textbox(visible=False, value="")
                            vc_del_btn  = gr.Button("删除", visible=False)
                            vc_del_hint = gr.HTML(value="")

                    # 右列：画廊（行内🗑）+ JS桥接 + 试听
                    with gr.Column(scale=2):
                        # 标题在外面，有独立背景
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#0ea5e9,#0284c7);">📋</div>'
                            '<span class="step-title">音色库</span>'
                            '</div>'
                        )
                        # 内容在白色panel里
                        with gr.Column(elem_classes="panel"):
                            vc_gallery = gr.HTML(
                                value=_vc.render_gallery("vc-del-input", "vc-prev-trigger") if _LIBS_OK else "")
                            with gr.Row(elem_id="vc-del-input-row"):
                                vc_del_js_input = gr.Textbox(
                                    elem_id="vc-del-input", value="", interactive=True)
                            # JS桥接：卡片点击写入此隐藏textbox触发试听
                            with gr.Row(elem_id="vc-prev-trigger-row"):
                                vc_prev_js_input = gr.Textbox(
                                    elem_id="vc-prev-trigger", value="", interactive=True)
                            vc_del_real_hint = gr.HTML(value="")
                            gr.HTML('<div class="divider"></div>')
                            gr.HTML('<div class="section-label">🔊 试听（点击上方卡片）</div>')
                            vc_prev_audio = gr.Audio(label="", interactive=False)

            # ── Tab 5：批量任务 ──────────────────────────────
            with gr.Tab("⚡  批量任务"):
                with gr.Row(elem_classes="workspace"):

                    # ══ 左列：新建任务表单 ══
                    with gr.Column(scale=1, elem_classes="panel bt-form"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">＋</span>新建任务</div>')

                        bt_name = gr.Textbox(label="任务名称",
                            placeholder="留空自动编号（任务1、任务2…）", max_lines=1)

                        # ── 步骤 1：音频 ──
                        gr.HTML('<div class="bt-step-row"><span class="step-chip" style="width:20px;height:20px;font-size:11px;">1</span><span class="bt-step-label">选择音频来源</span></div>')
                        bt_audio_mode = gr.Radio(
                            choices=["文字合成语音", "上传音频文件"],
                            value="文字合成语音", label="", elem_classes="bt-radio")

                        with gr.Group(visible=True) as bt_tts_group:
                            bt_text = gr.Textbox(label="合成文字内容",
                                placeholder="输入要转换为语音的文字...", lines=3)
                            bt_ref_audio = gr.Audio(label="参考音色（3~10 秒）",
                                sources=["upload"], type="filepath")

                        with gr.Group(visible=False) as bt_custom_audio_group:
                            bt_custom_audio = gr.Audio(label="上传音频（WAV / MP3）",
                                sources=["upload"], type="filepath")

                        # ── 步骤 2：视频 ──
                        gr.HTML('<div class="bt-step-row"><span class="step-chip" style="width:20px;height:20px;font-size:11px;">2</span><span class="bt-step-label">选择视频来源</span></div>')
                        bt_video_mode = gr.Radio(
                            choices=["使用公共视频", "上传专属视频"],
                            value="使用公共视频", label="", elem_classes="bt-radio")

                        with gr.Group(visible=False) as bt_own_video_group:
                            bt_own_video = gr.File(label="专属视频（仅此任务）",
                                file_types=["video"], type="filepath")

                        # ── 步骤 3：添加 ──
                        gr.HTML('<div class="bt-step-row"><span class="step-chip" style="width:20px;height:20px;font-size:11px;">3</span><span class="bt-step-label">加入任务队列</span></div>')
                        bt_add_hint = gr.HTML(value="")
                        bt_add_btn  = gr.Button("➕  加入队列", variant="primary", size="lg")

                    # ══ 右列：公共视频 + 批次设置 + 队列 ══
                    with gr.Column(scale=2, elem_classes="panel bt-queue"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">📋</span>任务队列与设置</div>')

                        # 顶部：公共视频 + 批次名称 横排
                        with gr.Row():
                            with gr.Column(scale=1):
                                gr.HTML('<div class="bt-section-title">🎬 公共视频</div>')
                                bt_shared_video = gr.File(label="所有任务共享此人物视频",
                                    file_types=["video"], type="filepath")
                            with gr.Column(scale=1):
                                gr.HTML('<div class="bt-section-title">📁 批次名称</div>')
                                bt_batch_name = gr.Textbox(label="输出文件夹名",
                                    placeholder="留空则使用时间戳", max_lines=1)
                                gr.HTML('<div style="font-size:11px;color:#94a3b8;margin-top:2px;">输出目录：unified_outputs / <b>时间戳_批次名</b></div>')

                        gr.HTML('<div class="divider"></div>')

                        # 任务列表（JS 中的叉号会把 index 写入隐藏 textbox）
                        bt_task_list_html = gr.HTML(
                            value=_render_task_list([]), elem_id="bt-task-list")

                        # 隐藏触发器：JS 写入序号 → Python 删除
                        bt_del_trigger = gr.Textbox(value="", visible=False,
                            elem_id="bt-del-trigger")

                        gr.HTML('<div class="divider"></div>')
                        with gr.Row():
                            bt_start_btn = gr.Button("🚀  开始批量生成", variant="primary", scale=3)
                            bt_clear_btn = gr.Button("🗑 清空队列", variant="stop", scale=1)

                        bt_progress_html = gr.HTML(value="", visible=False, elem_id="bt-progress-box")

                bt_tasks_state = gr.State([])

                # ── AI优化状态跟踪 ──
                ai_rewrite_done = gr.State(False)

                # ── 事件：切换音频来源 ──
                bt_audio_mode.change(
                    lambda m: (gr.update(visible=(m=="文字合成语音")),
                               gr.update(visible=(m=="上传音频文件"))),
                    inputs=[bt_audio_mode], outputs=[bt_tts_group, bt_custom_audio_group])

                # ── 事件：切换视频来源 ──
                bt_video_mode.change(
                    lambda m: gr.update(visible=(m=="上传专属视频")),
                    inputs=[bt_video_mode], outputs=[bt_own_video_group])

                # ── 事件：添加任务 ──
                def _bt_add(tasks, name, am, text, ref, cust, vm, ov):
                    idx = len(tasks) + 1
                    tn  = name.strip() if name.strip() else f"任务{idx}"
                    if am == "文字合成语音":
                        if not text.strip():
                            return tasks, _render_task_list(tasks), _hint("warning","请填写合成文字内容")
                        if not ref:
                            return tasks, _render_task_list(tasks), _hint("warning","请上传参考音色")
                    else:
                        if not cust:
                            return tasks, _render_task_list(tasks), _hint("warning","请上传音频文件")
                    if vm == "上传专属视频" and not ov:
                        return tasks, _render_task_list(tasks), _hint("warning","请上传专属视频或切换为公共视频")
                    task = {"id":idx,"name":tn,
                            "audio_mode":"tts" if am=="文字合成语音" else "custom",
                            "text":text,"ref_audio":ref,"audio_path":cust,
                            "video_mode":"shared" if vm=="使用公共视频" else "own",
                            "video_path":ov,"status":"等待中"}
                    nt = tasks + [task]
                    # 如果用了公共视频，额外提示
                    hint_msg = f"已添加「{tn}」，共 {len(nt)} 个任务"
                    if task["video_mode"] == "shared":
                        hint_msg += " ｜ ⚠️ 请确保已在右侧上传公共视频"
                    return nt, _render_task_list(nt), _hint("ok", hint_msg)

                bt_add_btn.click(_bt_add,
                    inputs=[bt_tasks_state, bt_name, bt_audio_mode, bt_text,
                            bt_ref_audio, bt_custom_audio, bt_video_mode, bt_own_video],
                    outputs=[bt_tasks_state, bt_task_list_html, bt_add_hint])

                # ── 事件：行内叉号删除（JS 触发隐藏 textbox）──
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

                # ── 事件：清空队列 ──
                bt_clear_btn.click(
                    lambda: ([], _render_task_list([]), "", gr.update(visible=False)),
                    outputs=[bt_tasks_state, bt_task_list_html, bt_add_hint, bt_progress_html])

                # ── 事件：开始批量生成 ──
                def _bt_run(tasks, shared_video, batch_name, progress=gr.Progress()):
                    if not tasks:
                        yield (gr.update(visible=True, value=_hint("warning","请先添加至少一个任务")),
                               gr.update(), gr.update()); return

                    # ── 前置校验：有任务用公共视频但未上传 ──
                    needs_shared = any(t.get("video_mode") == "shared" for t in tasks)
                    if needs_shared and (not shared_video or not os.path.exists(str(shared_video))):
                        sc = sum(1 for t in tasks if t.get("video_mode") == "shared")
                        yield (gr.update(visible=True, value=_hint("error",
                               f"有 {sc} 个任务设置为「使用公共视频」，请先在右上角上传公共人物视频！")),
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

                    yield _y(0,"运行中","准备开始，加载资源中...")
                    for i,task in enumerate(rt):
                        idx = i+1; tn = task.get("name",f"任务{idx}")
                        rt[i]["status"] = "进行中"
                        yield _y(i,"运行中",f"▶ 正在处理 {tn}（{idx}/{total}）")
                        try:
                            if task.get("audio_mode") == "tts":
                                ao = os.path.join(batch_dir, f"音频_{idx}.wav")
                                progress(0.1, desc=f"[{idx}/{total}] {tn} — 合成语音...")
                                generate_speech_batch(task["text"], task["ref_audio"], ao)
                                ap = ao
                            else:
                                ap = task.get("audio_path")
                                if not ap or not os.path.exists(ap):
                                    raise RuntimeError("音频文件不存在")
                                ext = os.path.splitext(ap)[1]
                                dst = os.path.join(batch_dir, f"音频_{idx}{ext}")
                                shutil.copy2(ap, dst); ap = dst
                            if task.get("video_mode") == "shared":
                                if not shared_video or not os.path.exists(shared_video):
                                    raise RuntimeError("公共视频未上传")
                                vp = shared_video
                            else:
                                vp = task.get("video_path")
                                if not vp or not os.path.exists(vp):
                                    raise RuntimeError("专属视频不存在")
                            op = os.path.join(batch_dir, f"任务{idx}.mp4")
                            progress(0.3, desc=f"[{idx}/{total}] {tn} — 视频合成...")
                            run_heygem_auto(vp, ap, output_path_override=op, steps=12, if_gfpgan=False)
                            rt[i]["status"] = "✅ 完成"
                            yield _y(idx,"运行中",f"✅ {tn} 完成 → 任务{idx}.mp4")
                        except Exception as e:
                            rt[i]["status"] = "❌ 失败"
                            yield _y(i,"运行中",f"❌ {tn} 失败：{str(e)[:80]}")

                    dc = sum(1 for t in rt if t["status"]=="✅ 完成")
                    fc = total-dc
                    fm = f"全部完成！成功 {dc} 个" + (f"，失败 {fc} 个" if fc else "")
                    yield (gr.update(visible=True, value=_render_batch_prog(total,total,"","已完成",fm,batch_dir)),
                           gr.update(visible=True, value=_render_task_list(rt)),
                           gr.update(value=[]))

                bt_start_btn.click(_bt_run,
                    inputs=[bt_tasks_state, bt_shared_video, bt_batch_name],
                    outputs=[bt_progress_html, bt_task_list_html, bt_tasks_state])


        # ════════════════════ 事件绑定 ════════════════════

        def _hint_html(kind, msg):
            cfg = {
                "ok":      ("#f0fdf4","✅","#15803d"),
                "warning": ("#fff7ed","⚠️","#92400e"),
                "error":   ("#fff1f2","❌","#be123c"),
            }
            bg, ic, tc = cfg.get(kind, cfg["error"])
            return (f'<div style="background:{bg};border-radius:8px;padding:8px 12px;'
                    f'font-size:12px;color:{tc};font-weight:600;'
                    f'font-family:Microsoft YaHei,sans-serif;margin-top:4px;">'
                    f'{ic} {msg}</div>')

        def _make_progress_banner(stage: str, pct: int, cur: int, total: int) -> str:
            """生成帧画面进度横幅 HTML"""
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
                f'已处理 {cur} / {total} 帧</div>'
                f'<style>@keyframes zdai-pulse{{0%,100%{{opacity:1;transform:scale(1)}}'
                f'50%{{opacity:.5;transform:scale(.8)}}}}</style>'
                f'</div>'
            )

        # ══════════════════════════════════════════════════════════
        #  工作台记录保存与恢复
        # ══════════════════════════════════════════════════════════════
        def _load_workspace_records():
            """加载所有工作台记录"""
            if not os.path.exists(WORKSPACE_RECORDS_FILE):
                return []
            try:
                with open(WORKSPACE_RECORDS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []

        def _save_workspace_record(record):
            """保存一条工作台记录"""
            try:
                records = _load_workspace_records()
                records.insert(0, record)
                records = records[:100]  # 最多保留100条
                with open(WORKSPACE_RECORDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                print(f"[ERROR] 保存工作台记录失败: {e}")
                return False

        def _get_workspace_record_choices():
            """获取工作台记录的下拉框选项"""
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
                        record_name = rec.get("time", "未知时间")
                
                time_str = rec.get("time", "")
                # 格式：名称 (时间)，值为索引
                choice_label = f"{record_name} ({time_str})"
                choices.append((choice_label, str(i)))
            
            return choices


        def _delete_workspace_record_by_dropdown(selected_value):
            """通过下拉框选择删除工作台记录"""
            try:
                if not selected_value:
                    return gr.update(), _hint_html("warning", "请先选择要删除的记录")
                
                record_idx = int(selected_value)
                records = _load_workspace_records()
                
                if record_idx < 0 or record_idx >= len(records):
                    return gr.update(), _hint_html("error", "记录不存在或已被删除")
                
                rec = records.pop(record_idx)
                with open(WORKSPACE_RECORDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                
                rec_name = rec.get("record_name") or rec.get("time", "该记录")
                new_choices = _get_workspace_record_choices()
                return gr.update(choices=new_choices, value=None), _hint_html("ok", f"已删除记录：{rec_name}")
            except Exception as e:
                return gr.update(), _hint_html("error", f"删除失败: {e}")
        
        def _clear_workspace_records():
            """清空所有工作台记录"""
            try:
                if os.path.exists(WORKSPACE_RECORDS_FILE):
                    os.remove(WORKSPACE_RECORDS_FILE)
                return gr.update(choices=[], value=None), _hint_html("ok", "已清空所有工作台记录")
            except Exception as e:
                return gr.update(), _hint_html("error", f"清空失败: {e}")

        def _auto_save_workspace(input_text, prompt_audio, voice_select_val, audio_mode_val,
                                direct_audio, avatar_select_val, audio_for_ls_val,
                                output_audio_val, output_video_val,
                                sub_text_val, sub_video_val,
                                # 字幕参数
                                sub_font_val, sub_size_val, sub_pos_val, sub_pos_offset_val,
                                sub_color_val, sub_hi_val, sub_outline_val, sub_outline_size_val,
                                sub_bg_color_val, sub_bg_opacity_val,
                                sub_kw_enable_val, sub_hi_scale_val, sub_kw_text_val,
                                # 发布参数
                                douyin_title_val="", douyin_topics_val="",
                                # 字幕标题参数
                                sub_title_text_val="",
                                sub_title_text2_val="",
                                # 片头参数
                                intro_enable_val=None,
                                # 画中画参数
                                pip_enable_val=None,
                                pip_mode_val=None,
                                pip_prompt_val=None,
                                pip_interval_val=None,
                                pip_clip_dur_val=None,
                                # 可选：用于 AI 改写场景，按原文查找已有记录并替换
                                search_key=None):
            """自动保存当前工作台状态 - 相同文本则更新，不同文本则新建
            当 search_key 不为 None 时，用 search_key 查找已有记录（用于 AI 改写场景：按原文查找并用改写后的文案替换）
            """
            try:
                # 强制输出到文件以便调试
                debug_file = os.path.join(OUTPUT_DIR, "debug_save.txt")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] _auto_save_workspace 被调用\n")
                    f.write(f"  output_audio_val type: {type(output_audio_val)}, value: {output_audio_val}\n")
                    f.write(f"  audio_for_ls_val type: {type(audio_for_ls_val)}, value: {audio_for_ls_val}\n")
                    f.write(f"  output_video_val type: {type(output_video_val)}, value: {output_video_val}\n")
                    f.write(f"  sub_text_val: {sub_text_val}\n")
                    f.write(f"  sub_title_text_val: {sub_title_text_val}\n")
                    f.write(f"  sub_kw_enable_val: {sub_kw_enable_val}\n")
                    f.write(f"  sub_kw_text_val: {sub_kw_text_val}\n")
                
                # 辅助函数：从 Gradio Audio 组件值中提取文件路径
                def extract_audio_path(val):
                    """
                    Gradio Audio 组件可能返回：
                    1. 字符串路径
                    2. 元组 (sample_rate, numpy_array) - 这种情况无法恢复原始路径
                    3. 字典 {'name': 'path', ...}
                    """
                    if val is None:
                        return ""
                    if isinstance(val, str):
                        return val.strip()
                    if isinstance(val, dict) and 'name' in val:
                        return val['name'].strip() if isinstance(val['name'], str) else str(val['name']).strip()
                    # 如果是元组 (sample_rate, array)，说明音频被加载到内存了
                    # 这种情况我们无法获取原始文件路径，只能返回空
                    if isinstance(val, tuple):
                        with open(debug_file, "a", encoding="utf-8") as f:
                            f.write(f"  [WARNING] Audio 组件返回了元组格式，无法获取文件路径\n")
                        return ""
                    return ""
                
                # 辅助函数：将任何值转换为JSON可序列化的类型
                def to_json_safe(val):
                    """将值转换为JSON可序列化的类型"""
                    if val is None:
                        return ""
                    # 处理 numpy 数组
                    if hasattr(val, 'tolist'):
                        return val.tolist()
                    # 处理字符串（去除两端空格）
                    if isinstance(val, str):
                        return val.strip()
                    # 处理其他基本类型
                    if isinstance(val, (int, float, bool)):
                        return val
                    # 尝试转换为字符串
                    return str(val).strip()
                
                # 生成记录名称：使用文本前10个字，如果没有则使用时间
                text = (input_text or "").strip()
                if text:
                    record_name = text[:10]
                else:
                    record_name = time.strftime("%H:%M:%S")
                
                # 提取音频路径（处理 Gradio Audio 组件的不同返回格式）
                output_audio_path = extract_audio_path(output_audio_val)
                audio_for_ls_path = extract_audio_path(audio_for_ls_val)
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  提取的路径:\n")
                    f.write(f"    output_audio_path: {output_audio_path}\n")
                    f.write(f"    audio_for_ls_path: {audio_for_ls_path}\n")
                
                record = {
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "record_name": record_name,
                    "input_text": to_json_safe(input_text),
                    "prompt_audio": to_json_safe(prompt_audio),
                    "voice_select": to_json_safe(voice_select_val),
                    "audio_mode": to_json_safe(audio_mode_val) or "文字转语音",
                    "direct_audio": to_json_safe(direct_audio),
                    "avatar_select": to_json_safe(avatar_select_val),
                    "audio_for_ls": audio_for_ls_path,  # 使用 audio_for_ls 的路径
                    "output_audio": output_audio_path,  # 使用 output_audio 的路径
                    "output_video": to_json_safe(output_video_val),
                    "sub_text": to_json_safe(sub_text_val),
                    "sub_video": to_json_safe(sub_video_val),
                    # 字幕参数
                    "sub_font": to_json_safe(sub_font_val),
                    "sub_size": to_json_safe(sub_size_val) or 38,
                    "sub_pos": to_json_safe(sub_pos_val) or "下",
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
                    # 字幕标题
                    "sub_title_text": to_json_safe(sub_title_text_val),
                    "sub_title_text2": to_json_safe(sub_title_text2_val),
                    # 片头参数
                    "intro_enable": bool(intro_enable_val) if intro_enable_val is not None else False,
                    # 发布参数
                    "douyin_title": to_json_safe(douyin_title_val),
                    "douyin_topics": to_json_safe(douyin_topics_val),
                    # 画中画参数
                    "pip_enable": bool(pip_enable_val) if pip_enable_val is not None else False,
                    "pip_mode": to_json_safe(pip_mode_val) if pip_mode_val is not None else "🌐 在线生成",
                    "pip_prompt": to_json_safe(pip_prompt_val) if pip_prompt_val is not None else "",
                    "pip_interval": to_json_safe(pip_interval_val) if pip_interval_val is not None else 15.0,
                    "pip_clip_dur": to_json_safe(pip_clip_dur_val) if pip_clip_dur_val is not None else 5.0,
                }
                
                # 读取现有记录
                records = _load_workspace_records()
                
                # 查找是否有相同文本的记录（只比较文本内容）
                # 如果提供了 search_key，用 search_key 查找（AI改写场景：按原文查找）
                match_text = (search_key or "").strip() if search_key is not None else text
                existing_idx = -1
                for i, rec in enumerate(records):
                    if rec.get("input_text", "").strip() == match_text:
                        existing_idx = i
                        break
                
                # 如果 input_text 为空且没有找到匹配记录，尝试更新最近一条记录
                # （用户在未输入文案的情况下编辑标题/话题，应更新最新记录而非新建）
                if existing_idx < 0 and not text and records:
                    # 检查最近一条记录的 input_text 是否也为空
                    if not records[0].get("input_text", "").strip():
                        existing_idx = 0
                
                if existing_idx >= 0:
                    # 更新现有记录 - 画中画参数为空时保留旧值
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
                    msg = f"已更新：{record_name}"
                else:
                    # 新建记录
                    records.insert(0, record)
                    records = records[:100]  # 最多保留100条
                    msg = f"已保存：{record_name}"
                
                # 保存到文件
                with open(WORKSPACE_RECORDS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                
                return _hint_html("ok", msg), gr.update(choices=_get_workspace_record_choices())
            except Exception as e:
                import traceback
                traceback.print_exc()
                return _hint_html("error", f"保存失败: {str(e)}"), gr.update()

        def _restore_workspace(record_idx_str):
            """恢复选中的工作台记录"""
            try:
                if not record_idx_str:
                    # 未选择记录,只更新提示,其他组件不动
                    return [gr.update()] * 34 + [_hint_html("warning", "请先选择一条记录")]

                try:
                    record_idx = int(record_idx_str)
                except (ValueError, TypeError):
                    return [gr.update()] * 34 + [_hint_html("error", "无效的记录索引")]

                records = _load_workspace_records()

                if record_idx < 0 or record_idx >= len(records):
                    return [gr.update()] * 34 + [_hint_html("error", "记录不存在")]
                
                rec = records[record_idx]
                
                # 强制输出到文件以便调试
                debug_file = os.path.join(OUTPUT_DIR, "debug_restore.txt")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] _restore_workspace 被调用\n")
                    f.write(f"  output_audio: {rec.get('output_audio', '')}\n")
                    f.write(f"  audio_for_ls: {rec.get('audio_for_ls', '')}\n")
                    f.write(f"  sub_text: {rec.get('sub_text', '')}\n")
                
                # 辅助函数：安全获取文件路径值
                def safe_file_value(path):
                    """只有当路径存在且是文件时才返回，否则返回 None"""
                    if not path or not isinstance(path, str):
                        return None
                    path = path.strip()
                    if not path:
                        return None
                    # 检查文件是否存在
                    exists = os.path.exists(path) and os.path.isfile(path)
                    with open(debug_file, "a", encoding="utf-8") as f:
                        f.write(f"  safe_file_value: {path} -> exists={exists}\n")
                    if exists:
                        return path
                    return None
                
                # 辅助函数：安全获取下拉框选择值
                def safe_dropdown_value(value, choices_func):
                    """检查值是否在选项列表中，如果不在则返回 None"""
                    if not value:
                        return None
                    try:
                        choices = choices_func() if callable(choices_func) else []
                        if value in choices:
                            return value
                        else:
                            # 如果值不在列表中，记录日志但返回None（不报错）
                            with open(debug_file, "a", encoding="utf-8") as f:
                                f.write(f"  警告: 音色 '{value}' 不在当前列表中，可能是TTS模式不匹配\n")
                            return None
                    except Exception as e:
                        with open(debug_file, "a", encoding="utf-8") as f:
                            f.write(f"  safe_dropdown_value 异常: {e}\n")
                        return None
                
                # 获取音频文件路径（即使文件不存在也恢复路径，让用户知道之前的文件）
                output_audio_path = rec.get("output_audio", "")
                audio_for_ls_path = rec.get("audio_for_ls", "")
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  从记录读取的路径:\n")
                    f.write(f"    output_audio_path: {output_audio_path}\n")
                    f.write(f"    audio_for_ls_path: {audio_for_ls_path}\n")
                
                # 如果 output_audio 存在，优先使用它
                # 如果不存在但有路径记录，也显示路径（虽然文件可能已被删除）
                output_audio_value = safe_file_value(output_audio_path)
                if not output_audio_value and output_audio_path:
                    # 文件不存在但有路径记录，仍然尝试恢复（Gradio会显示错误但保留路径）
                    output_audio_value = output_audio_path
                
                audio_for_ls_value = safe_file_value(audio_for_ls_path)
                if not audio_for_ls_value and audio_for_ls_path:
                    audio_for_ls_value = audio_for_ls_path
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  最终恢复的值:\n")
                    f.write(f"    output_audio_value: {output_audio_value}\n")
                    f.write(f"    audio_for_ls_value: {audio_for_ls_value}\n")
                    f.write(f"    sub_text: {rec.get('sub_text', '')}\n")
                    f.write(f"    sub_title_text: {rec.get('sub_title_text', '')}\n")
                    f.write(f"    sub_kw_enable: {rec.get('sub_kw_enable', False)}\n")
                    f.write(f"    sub_kw_text: {rec.get('sub_kw_text', '')}\n")
                
                # 获取字幕视频路径
                sub_video_path = rec.get("sub_video", "")
                if sub_video_path and os.path.exists(sub_video_path):
                    sub_video_update = gr.update(value=sub_video_path, visible=True, show_download_button=True)
                else:
                    sub_video_update = gr.update(visible=False)
                
                # 返回所有需要更新的组件值
                # 获取当前TTS模式，用于过滤音色列表
                current_tts_mode = os.getenv('TTS_MODE', 'local')
                
                result = [
                    gr.update(value=rec.get("input_text", "")),           # input_text
                    gr.update(value=safe_file_value(rec.get("prompt_audio"))),  # prompt_audio
                    gr.update(value=safe_dropdown_value(rec.get("voice_select"), lambda: _vc.get_choices(current_tts_mode) if _LIBS_OK else [])),  # voice_select - 使用当前模式过滤
                    gr.update(value=rec.get("audio_mode", "文字转语音")), # audio_mode
                    gr.update(value=safe_file_value(rec.get("direct_audio"))),  # direct_audio
                    gr.update(value=safe_dropdown_value(rec.get("avatar_select"), lambda: _av.get_choices() if _LIBS_OK else [])),  # avatar_select
                    gr.update(value=audio_for_ls_value) if audio_for_ls_value else gr.update(),  # audio_for_ls
                    gr.update(value=output_audio_value) if output_audio_value else gr.update(),  # output_audio
                    gr.update(value=safe_file_value(rec.get("output_video"))),  # output_video
                    gr.update(value=rec.get("sub_text", "")),             # sub_text - 直接恢复文本
                    sub_video_update,                                      # sub_video - 带 visible 控制
                    # 字幕参数
                    gr.update(value=rec.get("sub_font", "")),             # sub_font
                    gr.update(value=rec.get("sub_size", 38)),             # sub_size
                    gr.update(value=rec.get("sub_pos", "下")),            # sub_pos
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
                    # 字幕标题
                    gr.update(value=rec.get("sub_title_text", "")),        # sub_title_text
                    gr.update(value=rec.get("sub_title_text2", "")),       # sub_title_text2
                    # 发布参数
                    gr.update(value=rec.get("douyin_title", "")),           # douyin_title
                    gr.update(value=rec.get("douyin_topics", "")),          # douyin_topics
                    # 画中画参数
                    gr.update(value=rec.get("pip_enable", False)),          # pip_enable
                    gr.update(value=rec.get("pip_mode", "🌐 在线生成")),     # pip_mode
                    gr.update(value=rec.get("pip_prompt", "")),             # pip_prompt
                    gr.update(value=rec.get("pip_interval", 15.0)),         # pip_interval
                    gr.update(value=rec.get("pip_clip_dur", 5.0)),          # pip_clip_dur
                    _hint_html("ok", f"已恢复记录：{rec.get('record_name', rec.get('time', '未知'))}")
                ]
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  返回的 audio_for_ls 更新: {result[6]}\n")
                
                return result
            except Exception as e:
                return [gr.update()] * 34 + [_hint_html("error", f"恢复失败: {str(e)}")]

        # TTS — 后台线程执行，流式返回进度，UI 不卡
        def tts_wrap(text, pa, voice_name, spd, tp, tk, temp, nb, rp, mmt,
                     emo_m, emo_a, emo_w, emo_t,
                     v1, v2, v3, v4, v5, v6, v7, v8,
                     progress=gr.Progress()):
            # 参数验证
            if not text or not text.strip():
                raise gr.Error("请在文案内容中输入文本")
            
            # 在线/本地以当前 TTS_MODE 为准
            tts_mode = os.getenv('TTS_MODE', 'local')
            is_online = (tts_mode == 'online')

            # 在线版不需要 prompt_audio，本地版需要
            if not is_online and pa is None:
                raise gr.Error("请先选择音色或上传参考音频")
            
            try:
                progress(0.05, desc="正在合成语音...")
                
                r = generate_speech(text, pa, voice_name, tp, tk, temp, nb, rp, mmt,
                                    emo_m, emo_a, emo_w, emo_t,
                                    v1, v2, v3, v4, v5, v6, v7, v8,
                                    progress=progress)
                out_path = r[0]
                
                # 语速调整（ffmpeg atempo）
                speed = float(spd or 1.0)
                if abs(speed - 1.0) > 0.02 and out_path and os.path.exists(out_path):
                    progress(0.92, desc="调整语速...")
                    try:
                        tmp_path = out_path + ".speed.wav"
                        # atempo 范围 0.5~2.0, 链式处理超出范围
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
                
                progress(1.0, desc="完成")
                
                # Windows Toast
                try:
                    ps = (
                        "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
                        "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom,ContentType=WindowsRuntime]|Out-Null;"
                        "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(2);"
                        "$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('织梦AI — 语音合成完成'))|Out-Null;"
                        "$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('音频已生成，可以进行视频合成。'))|Out-Null;"
                        "$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
                        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('织梦AI').Show($n);"
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
                raise gr.Error("合成失败: " + str(e))

        # TTS 按钮点击 - 直接在完成后保存
        def tts_and_save(text, pa, voice_sel, spd, tp, tk, temp, nb, rp, mmt,
                        emo_m, emo_a, emo_w, emo_t,
                        v1, v2, v3, v4, v5, v6, v7, v8,
                        # 保存需要的其他参数
                        audio_mode_val, direct_aud, avatar_sel,
                        out_vid, sub_vid,
                        sub_font_val, sub_size_val, sub_pos_val, sub_pos_offset_val,
                        sub_color_val, sub_hi_val, sub_outline_val, sub_outline_size_val,
                        sub_bg_color_val, sub_bg_opacity_val,
                        sub_kw_enable_val, sub_hi_scale_val, sub_kw_text_val,
                        sub_title_text_val, sub_title_text2_val,
                        douyin_title_val, douyin_topics_val,
                        progress=gr.Progress()):
            """合成并自动保存工作台状态"""
            # 先执行TTS，voice_sel 在第三个位置
            audio_path, audio_for_ls_path = tts_wrap(
                text, pa, voice_sel, spd, tp, tk, temp, nb, rp, mmt,
                emo_m, emo_a, emo_w, emo_t,
                v1, v2, v3, v4, v5, v6, v7, v8,
                progress=progress
            )
            
            # 同步文本到字幕
            sub_text_val = text
            
            # 保存工作台状态
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
            
            # 返回所有需要更新的组件
            debug_file = os.path.join(OUTPUT_DIR, "debug_tts.txt")
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] tts_and_save 返回值:\n")
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
                # 保存需要的参数
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

        # ── 音频模式切换 ──
        def _toggle_audio_mode(mode):
            return (
                gr.update(visible=(mode == "文字转语音")),
                gr.update(visible=(mode == "直接上传音频")),
            )
        audio_mode.change(_toggle_audio_mode,
            inputs=[audio_mode],
            outputs=[tts_mode_group, upload_mode_group])

        # ── 画中画复选框切换 ──
        pip_enable.change(
            lambda v: gr.update(visible=v),
            inputs=[pip_enable],
            outputs=[pip_settings_group])

        # ── 画中画模式切换（在线/本地）──
        def _pip_mode_switch(mode_val):
            is_online = ("在线" in str(mode_val))
            return gr.update(visible=is_online), gr.update(visible=not is_online)
        pip_mode.change(
            _pip_mode_switch,
            inputs=[pip_mode],
            outputs=[pip_online_group, pip_local_group])

        # ── 画中画生成按钮 ──
        def generate_pip_video(current_video, pip_mode_val, pip_prompt_val,
                               pip_local_val, pip_interval_val, pip_clip_dur_val,
                               progress=gr.Progress()):
            """画中画视频生成：在线模式通过 WebSocket chatglm_video 生成，本地模式用用户上传的素材"""
            if not current_video:
                return gr.update(), _hint_html("error", "请先在步骤3生成视频")
            if not os.path.exists(str(current_video)):
                return gr.update(), _hint_html("error", "视频文件不存在，请重新生成")

            is_online = ("在线" in str(pip_mode_val))

            try:
                if is_online:
                    if not pip_prompt_val or not pip_prompt_val.strip():
                        return gr.update(), _hint_html("warning", "请输入画中画提示词（或点击「AI改写+标题标签」自动生成）")
                    progress(0.02, desc="🎬 在线生成画中画...")
                    # 按换行拆分为多个提示词
                    prompts_list = [_pip_force_chinese_person(p.strip()) for p in pip_prompt_val.strip().split('\n') if p.strip()]
                    if not prompts_list:
                        prompts_list = [_pip_force_chinese_person(pip_prompt_val.strip())]

                    # 使用 TextExtractor 连接生成画中画
                    extractor = get_text_extractor()
                    if len(prompts_list) == 1:
                        # 单个提示词 - 暂不支持合成，只生成
                        pip_result = _pip_ws.generate_pip_via_extractor(
                            prompts_list[0],
                            extractor,
                            progress_cb=lambda pct, msg: progress(pct, desc=f"🖼 {msg}")
                        )
                    else:
                        # 多个提示词，批量生成并合成
                        pip_result = _pip_ws.generate_and_compose_pips(
                            str(current_video),
                            prompts_list,
                            extractor,
                            clip_duration=5.0,
                            progress_cb=lambda pct, msg: progress(pct, desc=f"🖼 {msg}")
                        )
                else:
                    # 本地上传模式
                    if not pip_local_val:
                        return gr.update(), _hint_html("warning", "请上传画中画视频素材")
                    # Gradio File 组件返回的是 NamedString / tempfile 路径列表
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
                        return gr.update(), _hint_html("warning", "上传的文件无效，请重新选择")

                    progress(0.05, desc="🖼 本地画中画处理...")
                    pip_result = _pip.apply_pip_local(
                        str(current_video),
                        local_paths,
                        interval=float(pip_interval_val),
                        clip_duration=float(pip_clip_dur_val),
                        progress_cb=lambda pct, msg: progress(pct, desc=f"🖼 {msg}")
                    )

                if pip_result and os.path.exists(pip_result):
                    safe_print(f"[PIP] 画中画处理完成: {pip_result}")
                    progress(1.0, desc="✅ 画中画生成完成")
                    return pip_result, _hint_html("ok", "画中画视频生成完成")
                else:
                    return gr.update(), _hint_html("error", "画中画处理失败，请查看控制台日志")

            except Exception as e:
                safe_print(f"[PIP] 画中画处理失败: {e}")
                traceback.print_exc()
                return gr.update(), _hint_html("error", f"画中画生成失败: {str(e)}")

        pip_btn.click(
            generate_pip_video,
            inputs=[output_video, pip_mode, pip_prompt, pip_local_files,
                    pip_interval, pip_clip_dur],
            outputs=[output_video, pip_hint])

        # ── AI优化字幕函数（根据是否已AI改写，执行不同优化范围）──
        def _optimize_subtitle_with_deepseek(video_text, already_optimized=False):
            """
            使用DeepSeek AI优化字幕。
            - 如果未优化过(already_optimized=False)：关键词+字幕标题+视频标题+话题+画中画提示词
            - 如果已优化过(already_optimized=True)：只优化关键词+字幕标题
            """

            def _two_line_title(t: str) -> str:
                s = (t or "").strip()
                if not s:
                    return ""
                # 常见分隔符：| / ｜ 换行
                for sep in ("\n", "｜", "|", "/"):
                    if sep in s:
                        parts = [p.strip() for p in s.split(sep) if p.strip()]
                        if parts:
                            s1 = parts[0][:10]
                            s2 = (parts[1] if len(parts) > 1 else "")[:10]
                            if not s2 and len(parts) > 2:
                                s2 = parts[2][:10]
                            if not s2 and len(s1) < len(parts[0]):
                                # parts[0] 太长被截断，给第二行补齐
                                s2 = parts[0][10:20]
                            if not s2 and len(s) > 10:
                                s2 = s[10:20]
                            return (s1 + "\n" + s2).strip()
                # 无分隔符：按长度硬切两行
                s1 = s[:10]
                s2 = s[10:20]
                return (s1 + ("\n" + s2 if s2 else "")).strip()
            if not video_text or not video_text.strip():
                if not already_optimized:
                    return "", "", "", "", "", False, _hint_html("warning", "请先输入视频文本内容")
                else:
                    return "", "", False, _hint_html("warning", "请先输入视频文本内容")
            
            if not already_optimized:
                # 全量优化：关键词+字幕标题+视频标题+话题+多个画中画提示词
                prompt = f"""请根据以下视频文本内容，完成五个任务：

任务一：生成两行字幕标题（每行8-10个字，尽量接近10个字）。标题要口语化、有冲击力、适合短视频封面。
        输出时请用"｜"分隔两行，例如：第一行｜第二行（每行8-10字）。
任务二：从文本中提取尽可能多的关键词（用于字幕高亮显示），包括核心名词、动词、形容词等重要词语，不限数量，用逗号分隔
任务三：生成一个吸引人的短视频标题（不超过30字，吸引眼球、引发好奇）
任务四：生成5个相关的热门话题标签，用逗号分隔
任务五：为画中画视频生成多个提示词。每个提示词描述一个不同的真实场景画面，用于AI生成实景B-roll视频素材。
生成1个提示词（例如30秒文案生成1个，60秒文案生成2个，90秒文案生成3个）。每个提示词描述一个适合口播推广的真实场景画面，用于AI生成实景B-roll视频素材。
要求：根据文案朗读时长估算（约每秒3-4个字），按每30秒1个提示词的规则生成对应数量。每个不超过80字。
场景要求：实物场景，适合短视频口播画中画素材，主要用于展示厂家、商品、工作场景或服务环境。画面干净高级，空间通透，主体明确，构图简洁，具有短视频B-roll质感，灯光柔和，真实细节丰富，整体高级感强，生活化但不杂乱，超清写实风格。场景必须不同。

视频文本内容：
{video_text[:500]}

请严格按照以下格式输出，不要添加其他内容：
字幕标题：[你的字幕标题]
关键词：[关键词1,关键词2,关键词3,...]
视频标题：[你的视频标题]
话题：[话馘1,话馘2,话馘3,话馘4,话馘5]
提示词1：[第一处画中画场景描述]
提示词2：[第二处画中画场景描述]
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
                        if line.startswith("字幕标题：") or line.startswith("字幕标题:"):
                            sub_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                        elif line.startswith("关键词：") or line.startswith("关键词:"):
                            new_keywords = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                        elif line.startswith("视频标题：") or line.startswith("视频标题:"):
                            video_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                        elif line.startswith("话题：") or line.startswith("话题:"):
                            new_topics = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                        elif re.match(r'提示词\d*[：:]', line):
                            pip_line = re.sub(r'^提示词\d*[：:]\s*', '', line).strip()
                            if pip_line:
                                pip_prompts_list.append(pip_line)
                    
                    kw_enable = bool(new_keywords.strip())
                    new_pip_prompt = "\n".join(pip_prompts_list) if pip_prompts_list else ""
                    pip_count = len(pip_prompts_list)
                    sub_title = _two_line_title(sub_title)
                    return sub_title, new_keywords, video_title, new_topics, new_pip_prompt, kw_enable, _hint_html("ok", f"AI优化完成！已生成字幕标题、关键词、视频标题、话题和{pip_count}个画中画提示词")
                else:
                    return "", "", "", "", "", False, _hint_html("error", "AI优化失败，未返回内容")
            else:
                # 精简优化：只优化关键词+字幕标题
                prompt = f"""请根据以下视频文本内容，完成两个任务：

任务一：生成两行字幕标题（每行8-10个字，尽量接近10个字）。输出用"｜"分隔两行，例如：第一行｜第二行。
任务二：从文本中提取尽可能多的关键词（用于字幕高亮显示），包括核心名词、动词、形容词等重要词语，不限数量，用逗号分隔

视频文本内容：
{video_text[:300]}

请严格按照以下格式输出，不要添加其他内容：
标题：[你的标题]
关键词：[关键词1,关键词2,关键词3,...]"""
                
                result, error = _call_deepseek_api(prompt)
                if error:
                    return "", "", False, _hint_html("error", error)
                
                if result:
                    lines = result.strip().split('\n')
                    new_title = ""
                    new_keywords = ""
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith("标题：") or line.startswith("标题:"):
                            new_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                        elif line.startswith("关键词：") or line.startswith("关键词:"):
                            new_keywords = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                    
                    kw_enable = bool(new_keywords.strip())
                    new_title = _two_line_title(new_title)
                    return new_title, new_keywords, kw_enable, _hint_html("ok", "AI优化完成！已生成字幕标题和关键词")
                else:
                    return "", "", False, _hint_html("error", "AI优化失败，未返回内容")

        # ── 字幕高级设置弹窗 ──
        # JS .sub-settings-btn 点击事件已在 ui_init.js 中通过 zdai-open 类控制弹窗显示
        sub_settings_open_btn.click(
            lambda txt: gr.update(value=txt or ""),
            inputs=[input_text],
            outputs=[sub_text_modal])
        
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
            """关闭高级设置弹窗并保存到工作台"""
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
                save_hint = _hint_html("error", f"保存失败: {e}")
                dropdown_update = gr.update()
            # JS .sub-modal-close-btn 点击事件已在 ui_init.js 中通过移除 zdai-open 类关闭弹窗
            return gr.update(value=inp_txt or ""), save_hint, dropdown_update
        
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
            outputs=[sub_text,
                    workspace_record_hint, workspace_record_dropdown])
        # JS .sub-modal-close-btn 点击事件已在 ui_init.js 中通过移除 zdai-open 类关闭弹窗
        sub_settings_cancel_btn.click(
            lambda: None,
            outputs=[])
        
        # ── AI优化字幕按钮（根据是否已AI改写，执行不同范围优化，并保存到工作台）──
        def _split_title_lines(title_text):
            """将标题分成两行，每行最多10个字"""
            if not title_text or not title_text.strip():
                return "", ""

            # 支持多种分隔符
            title = title_text.strip()
            for sep in ("\n", "｜", "|", "\\"):
                if sep in title:
                    parts = [p.strip() for p in title.split(sep) if p.strip()]
                    line1 = parts[0][:10] if parts else ""  # 限制第一行最多10字
                    line2 = parts[1][:10] if len(parts) > 1 else ""  # 限制第二行最多10字
                    return line1, line2

            # 如果没有分隔符，且标题超过10个字，自动分成两行
            if len(title) > 10:
                line1 = title[:10]
                line2 = title[10:20]  # 第二行也最多10字
                return line1, line2

            # 标题不超过10字，返回第一行，第二行为空
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
                # 全量优化：字幕标题+关键词+视频标题+话题+画中画提示词
                result = _optimize_subtitle_with_deepseek(video_text, already_optimized=False)
                # result: (sub_title, keywords, video_title, topics, pip_prompt, kw_enable, hint)
                if len(result) == 7:
                    sub_title, new_keywords, video_title, new_topics, new_pip_prompt, kw_enable, hint = result
                    # 将标题分成两行
                    title_line1, title_line2 = _split_title_lines(sub_title)
                else:
                    # 出错时返回少量值
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
                    save_hint = _hint_html("error", f"保存失败: {e}")
                    dropdown_update = gr.update()
                # outputs: sub_title_text, sub_title_text2, sub_kw_text, sub_kw_enable, douyin_title, douyin_topics, pip_prompt, tts_hint, ai_rewrite_done, workspace_hint, workspace_dropdown
                return title_line1, title_line2, new_keywords, kw_enable, video_title, new_topics, new_pip_prompt, hint, True, save_hint, dropdown_update
            else:
                # 精简优化：只优化关键词+字幕标题
                result = _optimize_subtitle_with_deepseek(video_text, already_optimized=True)
                # result: (title, keywords, kw_enable, hint)
                if len(result) == 4:
                    new_title, new_keywords, kw_enable, hint = result
                    # 将标题分成两行
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
                    save_hint = _hint_html("error", f"保存失败: {e}")
                    dropdown_update = gr.update()
                # 精简模式不更新 douyin_title, douyin_topics, pip_prompt
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

        # ── 语音风格预设
        _VOICE_PRESETS = {
            "标准":     dict(tp=0.8,  tk=30, temp=0.7, rp=8.0,  spd=1.0),
            "稳定播报": dict(tp=0.6,  tk=10, temp=0.2, rp=14.0, spd=0.95),
            "活泼生动": dict(tp=0.95, tk=60, temp=1.4, rp=4.0,  spd=1.1),
            "慢速朗读": dict(tp=0.6,  tk=10, temp=0.15, rp=14.0, spd=0.9),
        }
        def _on_voice_style(style):
            is_pro = (style == "专业模式")
            if is_pro:
                return [gr.update(visible=True), gr.update()] + [gr.update()] * 4
            p = _VOICE_PRESETS.get(style, _VOICE_PRESETS["标准"])
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

        # ── TTS 合成速度预设 ──
        def _on_tts_speed(preset):
            p = TTS_SPEED_PRESETS.get(preset, TTS_SPEED_PRESETS["🚀 快速"])
            return [
                gr.update(value=p["num_beams"]),
                gr.update(value=p["max_mel_tokens"]),
            ]
        tts_speed_preset.change(_on_tts_speed,
            inputs=[tts_speed_preset],
            outputs=[num_beams, max_mel_tokens])

        # 直接上传音频时自动填入 audio_for_ls
        def _on_direct_audio(audio_path):
            # 只有当有实际音频路径时才返回，否则返回 gr.update() 不更新
            if audio_path and isinstance(audio_path, str) and audio_path.strip():
                return audio_path
            return gr.update()  # 不更新
        direct_audio_upload.change(_on_direct_audio,
            inputs=[direct_audio_upload],
            outputs=[audio_for_ls])

        # ── 数字人文件上传预览 ──
        def _av_file_preview(file_path, progress=gr.Progress()):
            if not file_path:
                return gr.update(visible=False, value=None)
            # 转码保证浏览器可播放
            try:
                converted = convert_video_for_browser(file_path, progress)
                return gr.update(visible=True, value=converted if converted else file_path, show_download_button=True)
            except Exception:
                return gr.update(visible=True, value=file_path, show_download_button=True)

        av_upload.change(_av_file_preview,
            inputs=[av_upload], outputs=[av_upload_preview])

        # ── 音色库事件 ──
        def _on_voice_select(name):
            if not name or name.startswith("（") or not _LIBS_OK:
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
        
        # ── TTS 模式切换事件 ──
        def _on_tts_mode_switch(mode_choice):
            """切换TTS模式：更新环境变量、音色列表，并在需要时加载模型"""
            global tts, _tts_on_gpu
            
            # 解析模式
            mode = "local" if "本地版" in mode_choice else "online"
            
            # 更新环境变量
            os.environ['TTS_MODE'] = mode
            
            # 保存到配置文件（config.dat）
            try:
                _update_config_key('TTS_MODE', mode)
                safe_print(f"[TTS_MODE] 已切换到: {mode}")
            except Exception as e:
                safe_print(f"[TTS_MODE] 保存失败: {e}")
            
            # 如果切换到本地版且模型未加载，则加载模型
            if mode == "local" and tts is None:
                try:
                    safe_print("[TTS_MODE] 检测到切换到本地版，开始加载 IndexTTS2 模型...")
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
                            safe_print("[TTS_MODE] IndexTTS2 模型加载完成")
                        finally:
                            os.chdir(original_cwd)
                    else:
                        safe_print("[TTS_MODE] 模型目录不存在，无法加载")
                except Exception as e:
                    safe_print(f"[TTS_MODE] 模型加载失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 更新音色列表（根据模式过滤）
            filter_mode = mode  # "local" 或 "online"
            new_choices = _vc.get_choices(filter_mode) if _LIBS_OK else []
            
            # 本地版显示语音风格/合成速度/语速，在线版隐藏
            is_local = (mode == "local")
            return gr.update(choices=new_choices, value=None), gr.update(visible=is_local)
        
        tts_mode_switch.change(
            _on_tts_mode_switch,
            inputs=[tts_mode_switch],
            outputs=[voice_select, local_only_settings_group]
        )

        # ── 数字人库事件 ──
        def _on_avatar_select(name):
            if not name or name.startswith("（") or not _LIBS_OK:
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

        # ── 数字人 Tab 事件 ──────────────────────────────────
        def _av_all_outputs(hint_html):
            """统一返回格式: hint + gallery + 下拉刷新 + 清空隐藏输入框"""
            ch = _av.get_choices() if _LIBS_OK else []
            return (hint_html,
                    _av.render_gallery("av-del-input", "av-prev-trigger") if _LIBS_OK else "",
                    gr.update(choices=ch, value=None),
                    gr.update(value=""))  # 清空隐藏输入框

        def _save_avatar_handler(video, name, progress=gr.Progress()):
            if not _LIBS_OK:
                return _av_all_outputs(_hint_html("error","扩展模块未加载"))
            if not video:
                return _av_all_outputs(_hint_html("warning","请先上传视频"))
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
            print(f"[DEBUG] _del_avatar_handler 被调用，name='{name}'")
            if not _LIBS_OK:
                return _av_all_outputs(_hint_html("error","扩展模块未加载"))
            if not name or not name.strip() or name.startswith("（"):
                return _av_all_outputs(_hint_html("warning","请先选择要删除的数字人"))
            ok, msg = _av.del_avatar(name.strip())
            print(f"[DEBUG] del_avatar 返回: ok={ok}, msg={msg}")
            return _av_all_outputs(_hint_html("ok" if ok else "warning", msg))

        # 卡片内 🗑 按钮 → JS 写入隐藏 textbox → change 事件触发
        av_del_js_input.change(_del_avatar_handler,
            inputs=[av_del_js_input],
            outputs=[av_del_real_hint, av_gallery, avatar_select, av_del_js_input])

        # 点击卡片 → JS 写入隐藏 textbox → change 事件触发预览
        def _preview_avatar(name):
            if not _LIBS_OK or not name or name.startswith("（"):
                return gr.update(value=None), ""
            path = _av.get_path(name)
            return (gr.update(value=path, show_download_button=True) if path and os.path.exists(path) else gr.update(value=None)), ""

        av_prev_js_input.change(_preview_avatar,
            inputs=[av_prev_js_input], outputs=[av_prev_video, av_prev_title])

        # ── 音色 Tab 事件 ──────────────────────────────────
        def _vc_all_outputs(hint_html):
            ch = _vc.get_choices() if _LIBS_OK else []
            return (hint_html,
                    _vc.render_gallery("vc-del-input", "vc-prev-trigger") if _LIBS_OK else "",
                    gr.update(choices=ch, value=None),
                    gr.update(value=""))  # 清空隐藏输入框

        def _save_voice(audio, name, source_choice):
            if not _LIBS_OK:
                return _vc_all_outputs(_hint_html("error","扩展模块未加载"))
            # 根据选择的版本调用不同的保存方法
            if "在线版" in source_choice:
                ok, msg = _vc.add_online_voice(audio, name)
            else:
                ok, msg = _vc.add_local_voice(audio, name)
            return _vc_all_outputs(_hint_html("ok" if ok else "warning", msg))

        vc_save_btn.click(_save_voice,
            inputs=[vc_upload, vc_name, vc_source],
            outputs=[vc_save_hint, vc_gallery, voice_select, vc_del_js_input])
        
        # ── 同步在线音色按钮 ──
        def _sync_online_voices():
            if not _LIBS_OK:
                return _vc_all_outputs(_hint_html("error","扩展模块未加载"))
            ok, msg = _vc.sync_online_voices()
            return _vc_all_outputs(_hint_html("ok" if ok else "warning", msg))
        
        vc_sync_btn.click(_sync_online_voices,
            outputs=[vc_save_hint, vc_gallery, voice_select, vc_del_js_input])

        def _del_voice_handler(name):
            print(f"[DEBUG] _del_voice_handler 被调用，name='{name}'")
            if not _LIBS_OK:
                return _vc_all_outputs(_hint_html("error","扩展模块未加载"))
            if not name or not name.strip() or name.startswith("（"):
                return _vc_all_outputs(_hint_html("warning","请先选择要删除的音色"))
            ok, msg = _vc.del_voice(name.strip())
            print(f"[DEBUG] del_voice 返回: ok={ok}, msg={msg}")
            return _vc_all_outputs(_hint_html("ok" if ok else "warning", msg))

        # 卡片内 🗑 按钮 → JS bridge
        vc_del_js_input.change(_del_voice_handler,
            inputs=[vc_del_js_input],
            outputs=[vc_del_real_hint, vc_gallery, voice_select, vc_del_js_input])

        # 点击卡片 → JS 写入隐藏 textbox → change 事件触发试听
        vc_prev_js_input.change(
            lambda n: (_vc.get_path(n) if (_LIBS_OK and n and not n.startswith("（")) else None),
            inputs=[vc_prev_js_input], outputs=[vc_prev_audio])

        # ── 关键词高亮开关 ──
        def _toggle_kw(enabled):
            return gr.update(visible=enabled), gr.update(visible=enabled)
        sub_kw_enable.change(_toggle_kw, inputs=[sub_kw_enable],
                             outputs=[sub_kw_row, sub_hi_scale])

        # ── 字体选择预览 ──

        def _render_font_preview(font_path, text, width=580, height=64, font_size=30):
            """用 Pillow 渲染字体预览图，返回 base64 PNG 字符串"""
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
            """字体选择后用 Pillow 渲染预览图片"""
            if not font_name or font_name in ("系统字体", "默认字体"):
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
            status = "✅ 已下载" if in_fonts else f"⬇️ 生成时自动下载 ({size_mb:.1f}MB)"
            
            # 优先用 font_cache 精简版，其次用 fonts/ 完整版
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
            
            # 根据分类用 display_name + 数字 作为预览文字
            cat_suffix = {"zh_cn": "中文字幕", "zh_tw": "中文字幕", "en": "Subtitle"}
            preview_text = f"{display} {cat_suffix.get(category, '字幕')} 1234"
            
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
                    'padding:12px 0;">预览不可用</div>'
                )
            
            html = (
                f'<div style="padding:8px;background:#1a1a2e;border-radius:8px;">'
                f'{img_html}'
                f'<div style="color:#aaa;font-size:12px;text-align:center;'
                f'margin-top:6px;padding-bottom:4px;">'
                f'🔤 {display} &nbsp; {status}</div>'
                f'</div>'
            )
            return gr.update(value=html, visible=True)
        
        sub_font.change(_on_font_select, inputs=[sub_font], outputs=[sub_font_preview])

        # ── 字幕生成 ──
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
                return "", _hint_html("error","扩展模块未加载")

            # 解析视频路径（gr.Video 在不同 Gradio 版本返回格式不同）
            if isinstance(vid, dict):
                vid_path = (vid.get("video") or {}).get("path") or vid.get("path") or ""
            else:
                vid_path = str(vid) if vid else ""
            if not vid_path or not os.path.exists(vid_path):
                return "", _hint_html("warning","请先完成视频合成再添加字幕")

            aud_path = str(aud) if (aud and isinstance(aud, str)) else None

            # 合并两行标题
            combined_title = ""
            if title_text and title_text.strip():
                combined_title = title_text.strip()
                if title_text2 and title_text2.strip():
                    combined_title += "｜" + title_text2.strip()
            elif title_text2 and title_text2.strip():
                combined_title = title_text2.strip()

            # 调试日志
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
                        _hint_html("ok", "字幕视频已生成: " + os.path.basename(out)))
            except Exception as e:
                # 安全打印异常堆栈
                try:
                    traceback.print_exc()
                except:
                    print(f"[ERROR] Exception: {repr(e)}")
                # 安全处理异常消息，避免编码错误
                try:
                    error_msg = str(e)[:300]
                except:
                    error_msg = repr(e)[:300]
                return ("",
                        _hint_html("error", f"字幕生成失败: {error_msg}"))

        # 字幕按钮点击 - 直接在完成后保存
        def subtitle_and_save(out_vid, aud_for_ls, sub_txt, sub_fnt, sub_sz, sub_ps, sub_ps_off,
                             sub_col, sub_hi, sub_out, sub_out_sz,
                             sub_bg_col, sub_bg_op, sub_kw_en, sub_kw_txt, sub_hi_sc,
                             # 标题参数
                             title_txt, title_txt2, title_fs, title_dur, title_col, title_out_col, title_mt,
                             # 保存需要的其他参数
                             inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                             avatar_sel, out_aud,
                             douyin_title_val, douyin_topics_val,
                             progress=gr.Progress()):
            """生成字幕并自动保存工作台状态"""
            # 先返回加载状态
            yield gr.update(), _hint_html("info", "🎬 正在生成字幕视频，请稍候..."), gr.update(), gr.update()

            # 字幕内容直接使用文案内容（避免维护两份文本）
            sub_txt = inp_txt or ""
            # 先生成字幕
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

            # 保存工作台状态
            # 注意：使用实际的音频和视频路径
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

            # 返回字幕视频，需要设置 visible=True 和 show_download_button=True
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
                # 标题参数
                sub_title_text, sub_title_text2, sub_title_font_size, sub_title_duration, sub_title_color,
                sub_title_outline_color, sub_title_margin_top,
                # 保存需要的参数
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
        
        # ═══════════════════════════════════════════════════════════
        # DeepSeek API 集成
        # ═══════════════════════════════════════════════════════════
        
        _deepseek_last_call = [0.0]  # 上次调用时间戳（用列表以便闭包内修改）
        _DEEPSEEK_COOLDOWN = 60     # 冷却时间（秒）

        def _call_deepseek_api(prompt, system_prompt="你是一个专业的文案创作助手。"):
            """
            调用DeepSeek API（限流：60秒内只允许调用一次）
            :param prompt: 用户提示词
            :param system_prompt: 系统提示词
            :return: API返回的文本内容
            """
            now = time.time()
            elapsed = now - _deepseek_last_call[0]
            if elapsed < _DEEPSEEK_COOLDOWN:
                remaining = int(_DEEPSEEK_COOLDOWN - elapsed)
                return None, f"⏳ 请求过于频繁，请 {remaining} 秒后再试"

            try:
                import requests
                
                # DeepSeek API配置
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                if not api_key:
                    # 尝试从 config.dat 读取
                    cfg = _read_config_lines(_CONFIG_FILE)
                    api_key = cfg.get("DEEPSEEK_API_KEY", "").strip().strip('"').strip("'")
                
                if not api_key:
                    return None, "❌ 未配置DeepSeek API密钥\n\n请在设置中配置 DEEPSEEK_API_KEY"
                
                # 记录本次调用时间（在实际发请求前记录，防止并发绕过）
                _deepseek_last_call[0] = time.time()
                
                # 调用API
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
                    error_msg = f"API请求失败 (状态码: {response.status_code})"
                    try:
                        error_detail = response.json().get("error", {}).get("message", "")
                        if error_detail:
                            error_msg += f"\n{error_detail}"
                    except:
                        pass
                    return None, error_msg
                    
            except requests.exceptions.Timeout:
                return None, "❌ API请求超时，请检查网络连接"
            except Exception as e:
                return None, f"❌ API调用失败: {str(e)}"
        
        def _rewrite_text_with_deepseek(original_text):
            """使用DeepSeek AI改写文案,同时优化标题、生成话题标签、关键词和画中画提示词"""
            if not original_text or not original_text.strip():
                return original_text, "", "", "", "", False, _hint_html("warning", "请先输入文本内容")
            
            prompt = f"""请完成以下五个任务：

任务一：将以下文案改写得更加生动、吸引人，保持原意但提升表达效果。
要求：必须保留原文的所有段落和完整内容，不要删减、合并或缩短，保持和原文相近的字数和段落数。使用更生动的词汇和表达方式，让文案更有感染力和吸引力。

任务二：根据文案内容，生成一个吸引人的短视频标题（不超过30字，吸引眼球、引发好奇）。

任务三：根据文案内容，生成5个相关的热门话题标签，用逗号分隔。

任务四：从文案中提取尽可能多的关键词（用于字幕高亮显示），包括核心名词、动词、形容词等重要词语，不限数量，用逗号分隔。

任务五：根据文案内容，为画中画视频生成提示词。每30秒视频生成1个提示词（例如30秒文案=1个，60秒文案=2个，90秒文案=3个）。根据文案长度估算朗读时长（约每秒3-4个字），计算所需提示词数量。
要求：
- 每个提示词对应文案中一个适合插入画中画的位置（如讲解某个具体场景/物件/活动时）
- 严格按每30秒1个的规则生成对应数量的提示词
- 每个提示词不超过80字，必须包含动态元素和动作描述，画面要有运动感和生命力
- 动态要求：必须包含人物动作、物体移动、镜头运动等动态元素，避免静态画面。例如：人物走动、手部操作、物品展示、镜头推拉摇移等
- 画面风格：超清写实风格，构图简洁，光线明亮自然
- 每个提示词的场景必须不同，与对应文案段落内容相关

原文案：
{original_text}

请严格按照以下格式输出，不要添加其他内容：
文案：[改写后的完整文案]
标题：[你的标题]
话题：[话馘1,话馘2,话馘3,话馘4,话馘5]
关键词：[关键词1,关键词2,关键词3,...]
提示词1：[第一处画中画场景描述]
提示词2：[第二处画中画场景描述]
..."""
            
            result, error = _call_deepseek_api(prompt)
            
            if error:
                return original_text, "", "", "", "", False, _hint_html("error", error)
            
            if result:
                # 解析返回结果
                lines = result.strip().split('\n')
                new_text = original_text
                new_title = ""
                new_topics = ""
                new_keywords = ""
                pip_prompts_list = []  # 多个画中画提示词
                
                # 解析多行文案：文案可能跨越多行，直到遇到"标题："或"话题："
                in_text_block = False
                text_lines = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("文案：") or stripped.startswith("文案:"):
                        first_line = stripped.split("：", 1)[-1].split(":", 1)[-1].strip()
                        if first_line:
                            text_lines.append(first_line)
                        in_text_block = True
                    elif stripped.startswith("标题：") or stripped.startswith("标题:"):
                        in_text_block = False
                        new_title = stripped.split("：", 1)[-1].split(":", 1)[-1].strip()
                    elif stripped.startswith("话题：") or stripped.startswith("话题:"):
                        in_text_block = False
                        new_topics = stripped.split("：", 1)[-1].split(":", 1)[-1].strip()
                    elif stripped.startswith("关键词：") or stripped.startswith("关键词:"):
                        in_text_block = False
                        new_keywords = stripped.split("：", 1)[-1].split(":", 1)[-1].strip()
                    elif re.match(r'提示词\d*[：:]', stripped):
                        in_text_block = False
                        pip_line = re.sub(r'^提示词\d*[：:]\s*', '', stripped).strip()
                        if pip_line:
                            pip_prompts_list.append(pip_line)
                    elif in_text_block and stripped:
                        text_lines.append(stripped)
                
                if text_lines:
                    new_text = "\n".join(text_lines)
                
                # 如果没解析到文案（可能AI没严格按格式），用整个结果作为改写文案
                if new_text == original_text and not any(
                    line.strip().startswith(("文案：", "文案:")) for line in lines
                ):
                    text_parts = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith(("标题：", "标题:", "话题：", "话题:", "关键词：", "关键词:")) or re.match(r'提示词\d*[：:]', line):
                            break
                        if line:
                            text_parts.append(line)
                    if text_parts:
                        new_text = "\n".join(text_parts)
                
                # 如果有关键词，自动开启关键词高亮
                kw_enable = bool(new_keywords.strip())
                
                # 多个提示词用换行分隔
                new_pip_prompt = "\n".join(pip_prompts_list) if pip_prompts_list else ""
                
                pip_count = len(pip_prompts_list)
                return new_text, new_title, new_topics, new_keywords, new_pip_prompt, kw_enable, _hint_html("ok", f"AI改写完成！已生成标题、话题、关键词和{pip_count}个画中画提示词")
            else:
                return original_text, "", "", "", "", False, _hint_html("error", "AI改写失败，未返回内容")
        
        def _optimize_title_with_deepseek(current_title, current_topics, video_text):
            """使用DeepSeek AI优化标题并生成话题标签"""
            if not video_text or not video_text.strip():
                return current_title, current_topics, _hint_html("warning", "请先输入视频文本内容")
            
            prompt = f"""请根据以下视频文本内容，生成一个吸引人的抖音视频标题和5个相关话题标签。

视频文本内容：
{video_text[:200]}

要求：
1. 标题：不超过30字，要吸引眼球、引发好奇
2. 话题标签：5个，用逗号分隔，要热门且相关
3. 输出格式严格按照：
标题：[你的标题]
话题：[话题1,话题2,话题3,话题4,话题5]

请直接输出，不要添加其他内容。"""
            
            result, error = _call_deepseek_api(prompt)
            
            if error:
                return current_title, current_topics, _hint_html("error", error)
            
            if result:
                # 解析返回结果
                lines = result.strip().split('\n')
                new_title = current_title
                new_topics = current_topics
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("标题：") or line.startswith("标题:"):
                        new_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                    elif line.startswith("话题：") or line.startswith("话题:"):
                        new_topics = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                
                return new_title, new_topics, _hint_html("ok", "AI优化完成")
            else:
                return current_title, current_topics, _hint_html("error", "AI优化失败，未返回内容")
        
        # 绑定AI改写按钮（一次API调用同时改写文案+生成标题+生成标签+画中画提示词）
        def _rewrite_and_save(original_text,
                              # 保存需要的参数
                              prmt_aud, voice_sel, audio_mode_val, direct_aud,
                              avatar_sel, aud_for_ls, out_aud, out_vid,
                              sub_vid,
                              sub_fnt, sub_sz, sub_ps, sub_ps_off,
                              sub_col, sub_hi, sub_out, sub_out_sz,
                              sub_bg_col, sub_bg_op,
                              sub_kw_en, sub_hi_sc, sub_kw_txt):
            """改写文案并同步返回给字幕，同时保存工作台记录"""
            try:
                new_text, title, topics, new_keywords, new_pip_prompt, kw_enable, hint = _rewrite_text_with_deepseek(original_text)
                # 将标题分成两行
                title_line1, title_line2 = _split_title_lines(title)
            except Exception as e:
                new_text = original_text
                title, topics, new_keywords, new_pip_prompt, kw_enable = "", "", "", "", False
                title_line1, title_line2 = "", ""
                hint = _hint_html("error", f"AI改写异常: {e}")
            
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
                print(f"[AI改写] 保存工作台失败: {e}")
                traceback.print_exc()
                save_hint = _hint_html("error", f"保存工作台失败: {e}")
                dropdown_update = gr.update()
            
            # outputs: input_text, douyin_title, douyin_topics, sub_kw_text, sub_kw_enable, pip_prompt, tts_hint, sub_text, sub_title_text, sub_title_text2, ai_rewrite_done, workspace_hint, workspace_dropdown
            return new_text, title, topics, new_keywords, kw_enable, new_pip_prompt, hint, new_text, title_line1, title_line2, True, save_hint, dropdown_update
        rewrite_btn.click(
            _rewrite_and_save,
            inputs=[input_text,
                    # 保存需要的参数
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
        
        
        # 清空提示
        input_text.change(lambda: "", outputs=[tts_hint])
        
        # 绑定AI优化按钮（优化后同时保存工作台）
        def _optimize_and_save(current_title, current_topics, video_text,
                               # 保存需要的参数
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
                    sub_title_text_val="",  # AI优化标题不影响字幕标题
                    sub_title_text2_val=""
                )
            except Exception as e:
                print(f"[AI优化] 保存工作台失败: {e}")
                save_hint = _hint_html("error", f"保存工作台失败: {e}")
                dropdown_update = gr.update()
            return new_title, new_topics, hint, save_hint, dropdown_update
        optimize_btn.click(
            _optimize_and_save,
            inputs=[douyin_title, douyin_topics, input_text,
                    # 保存需要的参数
                    prompt_audio, voice_select, audio_mode, direct_audio_upload,
                    avatar_select, audio_for_ls, output_audio, output_video,
                    sub_text, sub_video,
                    sub_font, sub_size, sub_pos, sub_pos_offset,
                    sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                    sub_bg_color, sub_bg_opacity,
                    sub_kw_enable, sub_hi_scale, sub_kw_text],
            outputs=[douyin_title, douyin_topics, douyin_hint,
                    workspace_record_hint, workspace_record_dropdown])
        
        # 手动编辑视频标题/话题时自动保存工作台
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
                # 只有标题或话题非空时才保存（避免清空时触发无用保存）
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
                print(f"[标题话题自动保存] 失败: {e}")
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
        
        # 抖音发布
        def _publish_overlay_html(step_name, step_detail="", is_done=False, is_error=False):
            """生成发布进度居中浮层 HTML"""
            if is_done:
                return ""  # 完成后清空浮层，由最终结果替代
            if is_error:
                return ""  # 错误时清空浮层
            return (
                f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
                f'border:2px solid #6366f1;border-radius:16px;'
                f'padding:28px 24px;margin:8px 0;'
                f'box-shadow:0 8px 32px rgba(99,102,241,.25);'
                f'text-align:center;">'
                # 旋转动画
                f'<div style="width:48px;height:48px;border:4px solid rgba(99,102,241,.2);'
                f'border-top-color:#6366f1;border-radius:50%;'
                f'animation:zdai-publish-spin .8s linear infinite;'
                f'margin:0 auto 16px;"></div>'
                # 当前步骤
                f'<div style="font-size:16px;font-weight:800;color:#e2e8f0;'
                f'font-family:Microsoft YaHei,sans-serif;margin-bottom:6px;">'
                f'{step_name}</div>'
                # 步骤详情
                f'<div style="font-size:13px;color:#94a3b8;'
                f'font-family:Microsoft YaHei,sans-serif;margin-bottom:16px;">'
                f'{step_detail}</div>'
                # 请勿操作警告
                f'<div style="display:inline-flex;align-items:center;gap:8px;'
                f'background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.3);'
                f'border-radius:8px;padding:8px 16px;">'
                f'<span style="font-size:16px;">⚠️</span>'
                f'<span style="font-size:12px;color:#fbbf24;font-weight:600;'
                f'font-family:Microsoft YaHei,sans-serif;">'
                f'发布进行中，请勿操作页面</span>'
                f'</div>'
                f'<style>@keyframes zdai-publish-spin{{to{{transform:rotate(360deg)}}}}</style>'
                f'</div>'
            )

        def _do_platform_publish(bgm_video, sub_video, output_video, title_text, topics_text, platforms, progress=gr.Progress()):
            """发布视频到选中的平台 - 优先使用字幕视频（生成器，实时显示进度）"""
            # ── 前置校验 ──
            if not platforms:
                yield _hint_html("warning", "请至少选择一个发布平台")
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
                deps_str = "、".join(missing_deps)
                yield _hint_html("error",
                        f"❌ 缺少依赖：{deps_str}<br><br>"
                        "请运行以下命令安装：<br>"
                        "1. 双击运行「安装抖音发布依赖.bat」<br>"
                        "或<br>"
                        f"2. 手动运行：pip install {' '.join(missing_deps)}")
                return

            # 解析视频路径（优先：带BGM视频 > 字幕视频 > 合成视频）
            video_to_use = None
            video_type = ""

            if bgm_video:
                if isinstance(bgm_video, dict):
                    bgm_video_path = (bgm_video.get("video") or {}).get("path") or bgm_video.get("path") or bgm_video.get("value") or ""
                else:
                    bgm_video_path = str(bgm_video) if bgm_video else ""
                if bgm_video_path and os.path.exists(bgm_video_path):
                    video_to_use = bgm_video_path
                    video_type = "带BGM视频"

            if sub_video:
                if isinstance(sub_video, dict):
                    sub_video_path = (sub_video.get("video") or {}).get("path") or sub_video.get("path") or sub_video.get("value") or ""
                else:
                    sub_video_path = str(sub_video) if sub_video else ""
                if sub_video_path and os.path.exists(sub_video_path):
                    if not video_to_use:
                        video_to_use = sub_video_path
                        video_type = "字幕视频"
            if not video_to_use and output_video:
                if isinstance(output_video, dict):
                    output_video_path = (output_video.get("video") or {}).get("path") or output_video.get("path") or output_video.get("value") or ""
                else:
                    output_video_path = str(output_video) if output_video else ""
                if output_video_path and os.path.exists(output_video_path):
                    video_to_use = output_video_path
                    video_type = "合成视频"
            if not video_to_use:
                yield _hint_html("warning", "请先生成视频（可以是最终合成视频或字幕视频）")
                return

            topics = []
            if topics_text:
                topics = [t.strip() for t in re.split(r'[,，、\s]+', topics_text.strip()) if t.strip()]

            # ── 逐平台发布 ──
            all_results = []
            for platform_name in platforms:
                yield _publish_overlay_html(f"准备发布到{platform_name}...", "正在初始化发布流程")

                q = _queue.Queue()
                result = {"success": False, "message": ""}

                def _run_publish(pname=platform_name):
                    try:
                        if pname == "抖音":
                            import lib_douyin_publish as douyin_pub
                            publisher = douyin_pub.DouyinPublisher()
                        elif pname == "视频号":
                            import lib_shipinhao_publish as sph_pub
                            publisher = sph_pub.ShipinhaoPublisher()
                        elif pname == "哔哩哔哩":
                            import lib_bilibili_publish as bilibili_pub
                            publisher = bilibili_pub.BilibiliPublisher()
                        elif pname == "小红书":
                            import lib_xiaohongshu_publish as xhs_pub
                            publisher = xhs_pub.XiaohongshuPublisher()
                        elif pname == "快手":
                            import lib_kuaishou_publish as ks_pub
                            publisher = ks_pub.KuaishouPublisher()
                        else:
                            result["success"] = False
                            result["message"] = f"{pname} 平台暂未支持"
                            q.put(("done",))
                            return

                        def step_cb(name, detail):
                            q.put(("step", name, detail))

                        def progress_cb(pct, msg):
                            q.put(("progress", pct, msg))

                        s, m = publisher.publish(
                            video_to_use,
                            title_text or "精彩视频",
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

                current_step = f"准备发布到{platform_name}..."
                current_detail = "正在初始化发布流程"
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
                            yield _publish_overlay_html(f"[{platform_name}] {msg}", f"进度 {pct}%")
                    except _queue.Empty:
                        yield _publish_overlay_html(current_step, current_detail)

                all_results.append((platform_name, result["success"], result["message"]))

            # ── 汇总结果 ──
            result_parts = []
            has_error = False
            for pname, success, msg in all_results:
                if success:
                    result_parts.append(f"✅ {pname}：{msg}")
                else:
                    has_error = True
                    if "chromedriver" in msg.lower() or "chrome" in msg.lower():
                        result_parts.append(f"❌ {pname}：Chrome 浏览器驱动问题")
                    else:
                        result_parts.append(f"❌ {pname}：{msg[:150]}")

            result_html = "<br>".join(result_parts)
            if video_type:
                result_html += f"<br><br>发布的视频：{video_type}"

            if has_error:
                yield _hint_html("warning", result_html)
            else:
                yield _hint_html("ok", result_html)

        douyin_btn.click(_do_platform_publish,
            inputs=[bgm_video, sub_video, output_video, douyin_title, douyin_topics, publish_platforms],
            outputs=[douyin_hint])

        def _mix_bgm_entry(enable_val, types_val, current_selected_val, bgm_path_val, bgm_state_val, vol_val, sub_vid, out_vid,
                          # 保存需要的参数
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
                raise gr.Error("请先启用背景音乐")

            selected_label = ""
            state_path = ""
            state_title = ""
            if isinstance(bgm_state_val, dict):
                state_path = (bgm_state_val.get("bgm_path") or "").strip()
                state_title = (bgm_state_val.get("title") or "").strip()

            # 优先复用 State 中的已选音乐（避免重复点击时换歌）
            if state_path and os.path.exists(state_path):
                bgm_path_val = state_path
                selected_label = state_title
            else:
                # 其次复用 textbox 里已有的本地路径
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
                # 兼容 gradio dict
                for v in (sub_vid, out_vid):
                    if isinstance(v, dict):
                        p = (v.get("video") or {}).get("path") or v.get("path") or v.get("value")
                        if p and os.path.exists(p):
                            base_video = p
                            break
            if not base_video:
                raise gr.Error("请先生成视频（步骤3或步骤4）")
            out = mix_bgm_into_video(base_video, bgm_path_val, float(vol_val or 1.0), progress=progress)
            hint = _hint_html("ok", "背景音乐已合成到视频")
            if selected_label:
                hint = _hint_html("ok", f"已自动选择并合成BGM：{selected_label}")
            shown = (selected_label or (current_selected_val or "")).strip()
            new_state = {"bgm_path": bgm_path_val, "title": shown}

            # 保存工作台状态
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
                print(f"[BGM混音] 保存工作台失败: {e}")
                traceback.print_exc()
                save_hint = _hint_html("error", f"保存工作台失败: {e}")
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
                cur_path = (bgm_state_val.get("bgm_path") or "").strip()
                cur_title = (bgm_state_val.get("title") or "").strip()

            # 尽量避免重复选到同一首
            last_err = None
            for _ in range(8):
                try:
                    item, local_path, shown = prepare_random_bgm_and_download(types_val, progress=progress)
                    if local_path and cur_path and os.path.exists(cur_path) and os.path.abspath(local_path) == os.path.abspath(cur_path):
                        continue
                    if shown and cur_title and shown.strip() == cur_title.strip():
                        continue
                    new_state = {"bgm_path": local_path, "title": shown}
                    return (
                        gr.update(value=shown),
                        gr.update(value=local_path),
                        gr.update(value=local_path, visible=True),
                        _hint_html("ok", f"已更换BGM：{shown}"),  # 移除了✅，_hint_html会自动添加
                        new_state,
                    )
                except Exception as e:
                    last_err = e
                    continue
            raise gr.Error(f"更换BGM失败: {last_err}")
        
        def _use_custom_bgm(custom_audio_path):
            """使用自定义上传的BGM"""
            if not custom_audio_path or not os.path.exists(custom_audio_path):
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    _hint_html("warning", "请先上传自定义BGM文件"),
                    gr.update()
                )
            
            # 复制到BGM缓存目录
            import shutil
            filename = os.path.basename(custom_audio_path)
            cache_path = _safe_bgm_cache_path(filename)
            
            try:
                shutil.copy2(custom_audio_path, cache_path)
                new_state = {"bgm_path": cache_path, "title": f"自定义：{filename}"}
                return (
                    gr.update(value=f"自定义：{filename}"),
                    gr.update(value=cache_path),
                    gr.update(value=cache_path, visible=True),
                    _hint_html("ok", f"已使用自定义BGM：{filename}"),
                    new_state,
                )
            except Exception as e:
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    _hint_html("error", f"复制BGM文件失败：{e}"),
                    gr.update()
                )

        bgm_change_btn.click(
            _change_bgm,
            inputs=[bgm_types, bgm_state],
            outputs=[bgm_selected, bgm_path_hidden, bgm_audio_preview, bgm_hint, bgm_state]
        )
        
        # 自定义BGM上传按钮
        bgm_custom_btn.upload(
            _use_custom_bgm,
            inputs=[bgm_custom_btn],
            outputs=[bgm_selected, bgm_path_hidden, bgm_audio_preview, bgm_hint, bgm_state]
        )
        
        # BGM启用/禁用（不再需要显示/隐藏自定义上传，按钮始终可见）

        bgm_mix_btn.click(
            _mix_bgm_entry,
            inputs=[bgm_enable, bgm_types, bgm_selected, bgm_path_hidden, bgm_state, bgm_volume, sub_video, output_video,
                   # 保存需要的参数
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

        # 视频合成
        def ls_wrap(avatar_name, auto_a, input_txt, quality_name="⚖️ 标准",
                    heygem_mode_val="💻 本地版", progress=gr.Progress()):
            # 把数字人名转换成文件路径
            video = None
            if _LIBS_OK and avatar_name and not avatar_name.startswith("（"):
                video = _av.get_path(avatar_name)
            if not video:
                if not avatar_name or avatar_name.startswith("（"):
                    raise gr.Error("请先在步骤3左侧选择一个数字人")
                else:
                    raise gr.Error(f"数字人 '{avatar_name}' 的视频文件不存在，请重新添加该数字人")
            audio  = auto_a
            if not audio or not os.path.exists(str(audio)):
                raise gr.Error("音频文件不存在，请先在步骤1生成或上传音频，再点击合成")
            preset = QUALITY_PRESETS.get(quality_name, QUALITY_PRESETS["⚖️ 标准"])
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

            # 初始展示：用户可理解的阶段进度卡片
            _t0 = time.time()
            _last_detail = _dual_progress_html("准备中", 5, "初始化", 0, 0)
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
                    # 超时时保持上一次的进度内容不变，不覆盖 detail_cb 的输出
                    yield gr.update(), gr.update(value=_last_detail, visible=True)

            if result["err"]:
                yield gr.update(), gr.update(value=_dual_progress_html("出错", 0, "失败", 0, int(time.time() - _t0)), visible=True)
                raise gr.Error(str(result["err"]))

            out      = result["out"]
            
            # 调试输出
            debug_file = os.path.join(OUTPUT_DIR, "debug_ls_wrap.txt")
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ls_wrap 完成\n")
                f.write(f"  out type: {type(out)}\n")
                f.write(f"  out value: {out}\n")
            
            try:
                ps = (
                    "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
                    "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom,ContentType=WindowsRuntime]|Out-Null;"
                    "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(2);"
                    "$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('织梦AI — 合成完成'))|Out-Null;"
                    "$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('视频合成已完成！'))|Out-Null;"
                    "$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
                    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('织梦AI').Show($n);"
                )
                subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                                 creationflags=subprocess.CREATE_NO_WINDOW,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            # 视频合成完成后显示抖音发布区域，并自动填充标题
            # 返回：视频路径（字符串）、详情
            # 注意：第一个返回值是视频路径字符串，不是 gr.update 对象
            yield out, gr.update(value=_dual_progress_html("✅ 完成", 100, "全部完成", 100, int(time.time() - _t0)), visible=True)

        # 视频合成按钮点击 - 直接在完成后保存
        def video_and_save(avatar_sel, aud_for_ls, inp_txt, quality_name, heygem_mode_val,
                          pip_enabled, pip_mode_val, pip_prompt_val,
                          pip_local_val, pip_interval_val, pip_clip_dur_val,
                          # 保存需要的其他参数
                          prmt_aud, voice_sel, audio_mode_val, direct_aud,
                          out_aud, sub_txt, sub_vid,
                          sub_fnt, sub_sz, sub_ps, sub_ps_off,
                          sub_col, sub_hi, sub_out, sub_out_sz,
                          sub_bg_col, sub_bg_op,
                          sub_kw_en, sub_hi_sc, sub_kw_txt,
                          sub_title_txt, sub_title_txt2,
                          douyin_title_val, douyin_topics_val,
                          progress=gr.Progress()):
            """合成视频并自动保存工作台状态"""
            # 开始时禁用按钮，防止重复点击
            yield gr.update(), gr.update(), gr.update(), gr.update(), gr.update(interactive=False)

            try:
                final_result = None
                for result in ls_wrap(avatar_sel, aud_for_ls, inp_txt, quality_name=quality_name,
                                     heygem_mode_val=heygem_mode_val, progress=progress):
                    yield result + (gr.update(), gr.update(), gr.update(interactive=False))
                    final_result = result
            
                if final_result:
                    video_path, ls_detail = final_result

                    # ── 画中画处理 ──
                    # 只有在勾选画中画且有有效提示词或素材时才处理
                    should_process_pip = False
                    if pip_enabled and video_path and os.path.exists(str(video_path)):
                        is_online = ("在线" in str(pip_mode_val))
                        if is_online:
                            # 在线模式：需要有提示词
                            should_process_pip = pip_prompt_val and pip_prompt_val.strip()
                        else:
                            # 本地模式：需要有上传的素材
                            if isinstance(pip_local_val, list):
                                should_process_pip = any(hasattr(f, 'name') or os.path.exists(str(f)) for f in pip_local_val)
                            elif pip_local_val:
                                should_process_pip = True

                    if should_process_pip:
                        try:
                            # 等待视频文件完全写入（最多等待5秒）
                            import time as _wait_time
                            for _ in range(10):
                                if os.path.exists(str(video_path)) and os.path.getsize(str(video_path)) > 1024:
                                    _wait_time.sleep(0.5)  # 再等待0.5秒确保文件完全写入
                                    break
                                _wait_time.sleep(0.5)

                            yield gr.update(), gr.update(
                                value='<div style="display:flex;align-items:center;gap:10px;padding:12px 16px;'
                                      'background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;">'
                                      '<div style="width:18px;height:18px;border:2.5px solid #bae6fd;'
                                      'border-top-color:#0ea5e9;border-radius:50%;'
                                      'animation:zdai-spin .7s linear infinite;flex-shrink:0;"></div>'
                                      '<span style="font-size:13px;color:#0369a1;font-weight:600;">'
                                      '🖼 正在处理画中画替换…</span>'
                                      '<style>@keyframes zdai-spin{to{transform:rotate(360deg)}}</style></div>',
                                visible=True), gr.update(), gr.update(), gr.update(interactive=False)

                            is_online = ("在线" in str(pip_mode_val))
                            pip_result = ""
                            if is_online:
                                if pip_prompt_val and pip_prompt_val.strip():
                                    prompts_list = [_pip_force_chinese_person(p.strip()) for p in pip_prompt_val.strip().split('\n') if p.strip()]
                                    if not prompts_list:
                                        prompts_list = [_pip_force_chinese_person(pip_prompt_val.strip())]

                                    # 使用 TextExtractor 连接生成画中画
                                    extractor = get_text_extractor()
                                    if len(prompts_list) == 1:
                                        # 单个提示词 - 暂不支持合成
                                        pip_result = _pip_ws.generate_pip_via_extractor(
                                            prompts_list[0],
                                            extractor,
                                            progress_cb=lambda pct, msg: safe_print(f"[PIP] {pct:.0%} {msg}")
                                        )
                                    else:
                                        # 多个提示词，批量生成并合成
                                        pip_result = _pip_ws.generate_and_compose_pips(
                                            str(video_path),
                                            prompts_list,
                                            extractor,
                                            clip_duration=5.0,
                                            progress_cb=lambda pct, msg: safe_print(f"[PIP] {pct:.0%} {msg}")
                                        )
                                else:
                                    safe_print("[PIP] 在线模式但无提示词，跳过画中画")
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
                                    safe_print("[PIP] 本地模式但无有效素材，跳过画中画")

                            if pip_result and os.path.exists(pip_result):
                                safe_print(f"[PIP] 画中画处理完成: {pip_result}")
                                video_path = pip_result
                            else:
                                safe_print("[PIP] 画中画处理未产出结果")
                        except Exception as e:
                            safe_print(f"[PIP] 画中画处理失败（不影响视频输出）: {e}")
                            traceback.print_exc()

                # 调试输出
                debug_file = os.path.join(OUTPUT_DIR, "debug_video_save.txt")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] video_and_save 保存前\n")
                    f.write(f"  video_path type: {type(video_path)}\n")
                    f.write(f"  video_path value: {video_path}\n")
                
                # 保存工作台状态
                # 注意：这里传递的 audio_for_ls 是实际使用的音频，output_audio 也应该是同一个
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
                
                # 最后一次 yield，包含保存结果并重新启用按钮
                # 注意：第一个值需要是视频路径，Gradio 会自动处理
                yield video_path, ls_detail, hint_msg, dropdown_update, gr.update(interactive=True)
            except Exception as e:
                # 异常时也要重新启用按钮（否则会卡死）
                err_hint = _hint_html("error", f"合成失败：{e}")
                yield gr.update(), gr.update(), gr.update(value=err_hint, visible=True), gr.update(), gr.update(interactive=True)
                return
        
        ls_btn.click(
            video_and_save,
            inputs=[
                avatar_select, audio_for_ls, input_text, quality_preset, heygem_mode_radio,
                pip_enable, pip_mode, pip_prompt, pip_local_files,
                pip_interval, pip_clip_dur,
                # 保存需要的参数
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

        # 合成模式切换：在线版隐藏质量选项
        heygem_mode_radio.change(
            lambda m: gr.update(visible=("本地" in m)),
            inputs=[heygem_mode_radio],
            outputs=[quality_group])

        # ══════════════════════════════════════════════════════════
        #  工作台记录事件绑定
        # ══════════════════════════════════════════════════════════════
        
        # 刷新工作台记录列表
        workspace_refresh_btn.click(
            lambda: gr.update(choices=_get_workspace_record_choices()),
            outputs=[workspace_record_dropdown])
        
        # 清空所有工作台记录
        workspace_clear_btn.click(
            _clear_workspace_records,
            outputs=[workspace_record_dropdown, workspace_record_hint])
        
        # 恢复工作台记录（通过下拉框选择）
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
        
        # 删除工作台记录（通过下拉框选择）
        workspace_delete_btn.click(
            _delete_workspace_record_by_dropdown,
            inputs=[workspace_record_dropdown],
            outputs=[workspace_record_dropdown, workspace_record_hint])

        # ════════════════════════════════════════════════════════════════
        #  文案提取事件绑定
        # ════════════════════════════════════════════════════════════════
        
        def _do_extract_text(url_or_content, progress=gr.Progress()):
            """提取文案处理函数"""
            if not url_or_content or not url_or_content.strip():
                return gr.update(), _hint_html("warning", "请输入链接或内容")
            
            progress(0.2, desc="正在提取文案...")
            
            # 获取文案提取器实例
            extractor = get_text_extractor()
            
            # 启动WebSocket连接（如果还没启动）
            extractor.start()
            
            progress(0.4, desc="正在发送请求...")
            
            # 提取文案
            success, result = extractor.extract_text(url_or_content.strip(), timeout=30)
            
            progress(1.0, desc="完成")
            
            if success:
                # 提取成功，返回内容到合成文本框
                return gr.update(value=result), '<div class="hint-ok">✅ 文案提取成功！</div>'
            else:
                # 提取失败
                return gr.update(), f'<div class="hint-err">❌ {result}</div>'
        
        extract_btn.click(
            _do_extract_text,
            inputs=[extract_input],
            outputs=[input_text, extract_hint]
        )

        # 页面加载时自动刷新工作台记录列表，并初始化WebSocket连接
        def _init_load():
            # 后台初始化文案提取器的WebSocket连接
            try:
                extractor = get_text_extractor()
                extractor.start()
                safe_print("[TextExtractor] WebSocket 连接已在后台初始化")
            except Exception as e:
                safe_print(f"[TextExtractor] 初始化失败: {e}")
            
            return gr.update(choices=_get_workspace_record_choices())
        
        app.load(_init_load, outputs=[workspace_record_dropdown])

        return app


# ══════════════════════════════════════════════════════════════
#  卡密验证 (Gradio 启动前，用 tkinter 弹窗)
# ══════════════════════════════════════════════════════════════
def _license_gate():
    """卡密验证门控。返回 True=通过, False=退出"""
    try:
        import lib_license as lic
    except ImportError:
        return True  # 没有 lib_license 模块 → 跳过验证

    # 1) 检查本地已保存的卡密
    status, info = lic.check_saved_license()
    if status == "valid":
        ok, msg = lic.validate_online(info.get("license_key", ""))
        if ok:
            safe_print("[LICENSE] OK")
            return True
        safe_print(f"[LICENSE] online verify fail: {msg}")

    # 2) 需要登录 — 弹出 tkinter 对话框
    try:
        import tkinter as tk
        from PIL import Image, ImageTk, ImageDraw
    except ImportError:
        safe_print("[LICENSE] tkinter not available, skip")
        return True

    result = {"passed": False}
    root = tk.Tk()
    root.title("软件激活")
    root.resizable(False, False)
    root.configure(bg="#eef2ff")

    # 更大的窗口，避免任何控件挤压
    w, h = 520, 560
    sx = (root.winfo_screenwidth() - w) // 2
    sy = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{sx}+{sy}")

    # 外层容器（模拟商业化卡片阴影效果）
    page = tk.Frame(root, bg="#eef2ff")
    page.pack(fill="both", expand=True, padx=18, pady=18)

    card_shadow = tk.Frame(page, bg="#dbe4ff")
    card_shadow.pack(fill="both", expand=True, padx=2, pady=2)

    card = tk.Frame(card_shadow, bg="#ffffff", relief="flat", bd=0)
    card.pack(fill="both", expand=True, padx=(0, 2), pady=(0, 2))

    # 顶部品牌区
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
        text="软件激活登录",
        font=("Microsoft YaHei", 18, "bold"),
        bg="#ffffff",
        fg="#0f172a"
    ).pack(anchor="w", pady=(10, 4))

    tk.Label(
        top,
        text="请输入有效卡密完成激活。首次使用前需阅读并勾选用户协议。",
        font=("Microsoft YaHei", 9),
        bg="#ffffff",
        fg="#64748b",
        justify="left"
    ).pack(anchor="w")

    # 分隔线
    tk.Frame(card, bg="#e5e7eb", height=1).pack(fill="x", padx=20, pady=(4, 12))

    body = tk.Frame(card, bg="#ffffff")
    body.pack(fill="both", expand=True, padx=20, pady=(0, 14))

    # 输入卡片
    input_card = tk.Frame(body, bg="#f8fafc", relief="solid", bd=1)
    input_card.pack(fill="x", pady=(0, 12))

    tk.Label(input_card, text="激活卡密", font=("Microsoft YaHei", 10, "bold"),
             bg="#f8fafc", fg="#1f2937").pack(anchor="w", padx=12, pady=(10, 6))
    tk.Label(input_card, text="建议粘贴完整卡密，系统将进行在线校验。", font=("Microsoft YaHei", 8),
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

    # 协议区域（更规整）
    agreement_var = tk.BooleanVar(value=False)
    agreement_box = tk.Frame(body, bg="#fff7ed", relief="solid", bd=1)
    agreement_box.pack(fill="x", pady=(0, 12))

    tk.Label(
        agreement_box,
        text="⚠ 使用前请先阅读并同意《用户协议》与《隐私协议》",
        font=("Microsoft YaHei", 9, "bold"),
        bg="#fff7ed",
        fg="#c2410c",
        anchor="w"
    ).pack(fill="x", padx=12, pady=(10, 6))

    tk.Label(
        agreement_box,
        text="本软件仅提供技术辅助能力，不对内容合规、AI生成结果准确性、平台审核结果、账号状态及经营结果作任何保证。",
        font=("Microsoft YaHei", 8),
        bg="#fff7ed",
        fg="#9a3412",
        justify="left",
        wraplength=450,
        anchor="w"
    ).pack(fill="x", padx=12, pady=(0, 8))

    agree_row = tk.Frame(agreement_box, bg="#fff7ed")
    agree_row.pack(fill="x", padx=10, pady=(0, 10))

    # 自定义勾选框（避免系统默认样式过丑）
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

    agree_text_label = tk.Label(agree_row, text="我已阅读并同意", font=("Microsoft YaHei", 9), bg="#fff7ed", fg="#374151", cursor="hand2")
    agree_text_label.pack(side="left")
    agree_text_label.bind("<Button-1>", _toggle_agreement)

    def _render_md_to_tk(text_widget, md_text):
        """将 Markdown 渲染到 tkinter Text widget（带格式标签）"""
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
                tw.insert("end", "━" * 60 + "\n", "hr")
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
                prefix = "  • " if not li_m.group(2)[0].isdigit() else f"  {li_m.group(2)} "
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
        default_text = "用户协议文件缺失，请将 user_agreement.md 放在程序同目录下。"
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
            return default_text + "\n\n读取错误：%s" % (e,)
        return default_text

    def _load_privacy_text():
        default_text = "隐私协议文件缺失，请将 privacy_policy_total.md 或 privacy_policy.md 放在程序同目录下。"
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
            return default_text + "\n\n读取错误：%s" % (e,)
        return default_text

    def show_agreement():
        agreement_window = tk.Toplevel(root)
        agreement_window.title("用户协议与隐私协议")
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
        tk.Label(header, text="用户协议与隐私协议", font=("Microsoft YaHei", 13, "bold"),
                 bg="#ffffff", fg="#0f172a").pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(header, text="请完整阅读后勾选同意。建议由实际运营负责人阅读并确认。",
                 font=("Microsoft YaHei", 9), bg="#ffffff", fg="#64748b").pack(anchor="w", padx=14, pady=(0, 12))

        # ── Tab 按钮栏 ──
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

        tab_btns["user"] = tk.Button(tab_bar, text="📄 用户协议", font=("Microsoft YaHei", 10, "bold"),
                                     bg="#4f46e5", fg="#ffffff", relief="flat", bd=0, padx=18, pady=6,
                                     cursor="hand2", command=lambda: switch_tab(0))
        tab_btns["user"].pack(side="left", padx=(0, 4))

        tab_btns["privacy"] = tk.Button(tab_bar, text="🔒 隐私协议", font=("Microsoft YaHei", 10, "bold"),
                                        bg="#e2e8f0", fg="#475569", relief="flat", bd=0, padx=18, pady=6,
                                        cursor="hand2", command=lambda: switch_tab(1))
        tab_btns["privacy"].pack(side="left")

        # ── 内容区 ──
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

        # 用户协议 tab
        tab_frames["user"] = tk.Frame(content_area, bg="#f1f5f9")
        _make_text_panel(tab_frames["user"], _load_agreement_text())

        # 隐私协议 tab
        tab_frames["privacy"] = tk.Frame(content_area, bg="#f1f5f9")
        _make_text_panel(tab_frames["privacy"], _load_privacy_text())

        # 默认显示第一个 tab
        switch_tab(0)

        footer = tk.Frame(shell, bg="#f1f5f9")
        footer.pack(fill="x")
        tk.Label(footer, text="提示：勾选协议仅表示您已知悉并承诺合规使用，不代表平台审核通过或账号安全无风险。",
                 font=("Microsoft YaHei", 8), bg="#f1f5f9", fg="#64748b", wraplength=760, justify="left").pack(anchor="w", pady=(0, 10))
        tk.Button(
            footer, text="同意", command=agreement_window.destroy,
            font=("Microsoft YaHei", 10, "bold"), bg="#4f46e5", fg="white",
            activebackground="#4338ca", activeforeground="white",
            relief="flat", cursor="hand2", bd=0, padx=20, pady=8
        ).pack(side="right")

    link_label = tk.Label(
        agree_row,
        text="《用户协议》与《隐私协议》",
        font=("Microsoft YaHei", 9, "underline"),
        bg="#fff7ed",
        fg="#4338ca",
        cursor="hand2"
    )
    link_label.pack(side="left")
    link_label.bind("<Button-1>", lambda e: show_agreement())

    # 状态提示区（固定高度容器，避免挤压主按钮）
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

    # 底部主操作区（按钮固定大高度）
    action_box = tk.Frame(card, bg="#ffffff")
    action_box.pack(fill="x", padx=20, pady=(0, 18))
    tk.Frame(action_box, bg="#e5e7eb", height=1).pack(fill="x", pady=(0, 12))

    # 自定义主按钮（使用PIL创建圆角渐变按钮）
    btn_state = {"enabled": False}
    
    # 按钮尺寸
    btn_width = 460
    btn_height = 56
    corner_radius = 10
    
    def create_rounded_gradient_button(width, height, radius, color1, color2, shadow=False):
        """创建圆角渐变按钮图片"""
        img_height = height + 6 if shadow else height
        img = Image.new('RGBA', (width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if shadow:
            # 绘制阴影
            shadow_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_img)
            shadow_draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=(0, 0, 0, 30))
            img.paste(shadow_img, (2, 5), shadow_img)
        
        # 绘制渐变背景
        gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        for y in range(height):
            ratio = y / height
            r = int(color1[0] + (color2[0] - color1[0]) * ratio)
            g = int(color1[1] + (color2[1] - color1[1]) * ratio)
            b = int(color1[2] + (color2[2] - color1[2]) * ratio)
            gradient_draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
        # 创建圆角蒙版
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=255)
        
        # 应用圆角蒙版
        gradient.putalpha(mask)
        img.paste(gradient, (0, 0), gradient)
        
        return img
    
    # 禁用状态颜色 (淡紫色)
    disabled_color1 = (165, 180, 252)  # #a5b4fc
    disabled_color2 = (196, 181, 253)  # #c4b5fd
    
    # 启用状态颜色 (紫色渐变)
    normal_color1 = (99, 102, 241)   # #6366f1
    normal_color2 = (124, 58, 237)   # #7c3aed
    
    # 悬停状态颜色 (更亮的紫色)
    hover_color1 = (129, 140, 248)   # #818cf8
    hover_color2 = (139, 92, 246)    # #8b5cf6
    
    # 点击状态颜色 (更深的紫色)
    active_color1 = (79, 70, 229)    # #4f46e5
    active_color2 = (109, 40, 217)   # #6d28d9
    
    # 创建按钮图片
    btn_disabled_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, disabled_color1, disabled_color2, shadow=False)
    btn_normal_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, normal_color1, normal_color2, shadow=True)
    btn_hover_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, hover_color1, hover_color2, shadow=True)
    btn_active_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, active_color1, active_color2, shadow=False)
    
    # 转换为Tkinter图片
    btn_disabled_tk = ImageTk.PhotoImage(btn_disabled_img)
    btn_normal_tk = ImageTk.PhotoImage(btn_normal_img)
    btn_hover_tk = ImageTk.PhotoImage(btn_hover_img)
    btn_active_tk = ImageTk.PhotoImage(btn_active_img)
    
    # 按钮容器
    btn_container = tk.Frame(action_box, bg="#ffffff", height=70)
    btn_container.pack(fill="x")
    btn_container.pack_propagate(False)
    
    btn_canvas = tk.Canvas(btn_container, bg="#ffffff", highlightthickness=0, height=70, width=btn_width)
    btn_canvas.pack()
    
    # 保持引用防止被垃圾回收
    btn_canvas.btn_images = [btn_disabled_tk, btn_normal_tk, btn_hover_tk, btn_active_tk]
    
    # 在Canvas上绘制按钮背景
    btn_x, btn_y = 0, 5
    btn_bg_id = btn_canvas.create_image(btn_x, btn_y, image=btn_disabled_tk, anchor="nw", tags="btn_bg")
    
    # 绘制按钮文字
    text_id = btn_canvas.create_text(
        btn_x + btn_width // 2,
        btn_y + btn_height // 2,
        text="🚀  登录启动",
        font=("Microsoft YaHei", 15, "bold"),
        fill="#eef2ff",
        tags="btn_text"
    )
    
    # 创建透明的点击区域
    click_area = btn_canvas.create_rectangle(
        btn_x, btn_y, btn_x + btn_width, btn_y + btn_height,
        fill="", outline="", tags="click_area"
    )
    
    is_pressed = [False]
    
    def _btn_click(_e=None):
        if btn_state["enabled"]:
            _do_login()

    # 绑定点击事件
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
    
    # 绑定事件到点击区域和文字
    for tag in ("click_area", "btn_text"):
        btn_canvas.tag_bind(tag, "<Enter>", _on_btn_enter)
        btn_canvas.tag_bind(tag, "<Leave>", _on_btn_leave)
        btn_canvas.tag_bind(tag, "<ButtonPress-1>", _on_btn_press)
        btn_canvas.tag_bind(tag, "<ButtonRelease-1>", _on_btn_release)
    
    subline = tk.Label(
        action_box,
        text="激活即表示您理解：软件提供技术能力，不对平台规则变化、审核结果、封禁、经营损失等负责。",
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
            msg_label.config(text="请输入卡密", fg="#ef4444")
            return
        if not agreement_var.get():
            msg_label.config(text="请先阅读并勾选《用户协议》与《隐私协议》", fg="#ef4444")
            return

        msg_label.config(text="正在验证卡密，请稍候...", fg="#4f46e5")
        root.update_idletasks()
        ok, msg = lic.validate_online(key)
        if ok:
            msg_label.config(text="激活成功，正在进入系统...", fg="#16a34a")
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

    key_entry.bind("<Return>", lambda e: _do_login() if agreement_var.get() else msg_label.config(text="请先勾选并同意《用户协议》与《隐私协议》", fg="#ef4444"))

    def _on_close():
        result["passed"] = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()
    return result["passed"]


# ══════════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # 卡密验证已在 app_backend.py 中完成，这里不再重复验证
    # if not _license_gate():
    #     safe_print("[LICENSE] denied, exit")
    #     sys.exit(0)

    auto_load_model()
    try:
        # 在线版无需预热 HeyGem（节省启动时间/资源）
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
                # ★ 关键：允许 Gradio 静态服务访问 BASE_DIR（logo.jpg / 转换视频等）
                allowed_paths=[BASE_DIR, OUTPUT_DIR,
                              os.path.join(BASE_DIR,"avatars"),
                              os.path.join(BASE_DIR,"voices"),
                              os.path.join(BASE_DIR,"fonts"),
                              os.path.join(BASE_DIR,"font_cache")],
            )
            break
        except OSError:
            continue
