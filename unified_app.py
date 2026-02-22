# -*- coding: utf-8 -*-
import os, sys, time, subprocess, traceback, shutil, re, json, queue as _queue, threading
import asyncio

# ── WebSocket 模块（用于提取文案功能）──
try:
    import websockets
    _WS_OK = True
except ImportError:
    _WS_OK = False
    print("[WARN] websockets 模块未安装，提取文案功能将不可用")

# ── 新功能模块（数字人 / 音色 / 字幕）──
try:
    import lib_avatar as _av
    import lib_voice  as _vc
    import lib_subtitle as _sub
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

# ── 清除代理 ──
for _k in ('http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','all_proxy'):
    os.environ.pop(_k, None)
    os.environ[_k] = ''
os.environ['no_proxy'] = '127.0.0.1,localhost'
os.environ['NO_PROXY'] = '127.0.0.1,localhost'

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
PLATFORM_AGREEMENT_FILE = os.path.join(BASE_DIR, "platform_ai_usage_agreement.txt")
LEGACY_AGREEMENT_FILE = os.path.join(BASE_DIR, "platform_publish_agreement.txt")
DOUYIN_AGREEMENT_FILE = os.path.join(BASE_DIR, "douyin_publish_agreement.txt")  # 兼容旧版本
INDEXTTS_DIR   = os.path.join(BASE_DIR, "_internal_tts")
LATENTSYNC_DIR = os.path.join(BASE_DIR, "_internal_sync")
OUTPUT_DIR     = os.path.join(BASE_DIR, "unified_outputs")
HISTORY_FILE   = os.path.join(OUTPUT_DIR, "history.json")
WORKSPACE_RECORDS_FILE = os.path.join(OUTPUT_DIR, "workspace_records.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HF_CACHE_DIR = os.path.abspath(os.path.join(INDEXTTS_DIR, "checkpoints", "hf_cache"))
os.makedirs(HF_CACHE_DIR, exist_ok=True)
for _e, _v in [
    ('HF_HUB_CACHE', HF_CACHE_DIR), ('HF_HOME', HF_CACHE_DIR),
    ('HUGGINGFACE_HUB_CACHE', HF_CACHE_DIR), ('TRANSFORMERS_CACHE', HF_CACHE_DIR),
    ('TRANSFORMERS_OFFLINE', '1'), ('HF_HUB_OFFLINE', '1'),
]:
    os.environ[_e] = _v

LATENTSYNC_PYTHON = os.path.join(LATENTSYNC_DIR, "latents_env", "python.exe")
LATENTSYNC_CKPT   = os.path.join(LATENTSYNC_DIR, "checkpoints", "latentsync_unet.pt")
LATENTSYNC_CONFIG = os.path.join(LATENTSYNC_DIR, "configs", "unet", "stage2_efficient.yaml")

sys.path.insert(0, INDEXTTS_DIR)
sys.path.insert(0, os.path.join(INDEXTTS_DIR, "indextts"))

import warnings; warnings.filterwarnings("ignore")
import gradio as gr
import logging
logging.getLogger("h11").setLevel(logging.CRITICAL)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

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


# ══════════════════════════════════════════════════════════════
#  JS：注入全局逻辑（在 Gradio js= 参数中运行，页面加载后立即执行）
# ══════════════════════════════════════════════════════════════
# 从外部文件加载JS
try:
    with open(os.path.join(BASE_DIR, "ui_init.js"), "r", encoding="utf-8") as f:
        INIT_JS = f.read()
except Exception as e:
    print(f"[WARNING] 无法加载 ui_init.js: {e}")
    INIT_JS = "() => { console.log('[织梦AI] JS加载失败'); }"

# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
# 从外部文件加载CSS
try:
    with open(os.path.join(BASE_DIR, "ui_style.css"), "r", encoding="utf-8") as f:
        CUSTOM_CSS = f.read()
except Exception as e:
    print(f"[WARNING] 无法加载 ui_style.css: {e}")
    CUSTOM_CSS = ""



# ══════════════════════════════════════════════════════════════
def auto_load_model():
    global tts
    model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
    if not os.path.exists(model_dir):
        safe_print("[ERR] model dir not found"); return
    original_cwd = os.getcwd()
    os.chdir(INDEXTTS_DIR)
    try:
        safe_print("[MODEL] 正在加载 IndexTTS2 声学模型...")
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

    # ── 后台预热 _internal_sync 引擎 ──
    def _warmup_latentsync():
        try:
            if not os.path.exists(LATENTSYNC_PYTHON):
                safe_print("[WARMUP] _internal_sync Python 未找到，跳过预热")
                return
            if not os.path.exists(LATENTSYNC_CKPT):
                safe_print("[WARMUP] _internal_sync 模型文件未找到，跳过预热")
                return

            safe_print("[WARMUP] 正在预热 _internal_sync 引擎...")
            env = os.environ.copy()
            ls_env = os.path.join(LATENTSYNC_DIR, "latents_env")
            fb = os.path.join(LATENTSYNC_DIR, "ffmpeg-7.1", "bin")
            env["HF_HOME"] = os.path.join(LATENTSYNC_DIR, "huggingface")
            env["PYTHONPATH"] = LATENTSYNC_DIR + os.pathsep + env.get("PYTHONPATH", "")
            env["PATH"] = ";".join([ls_env, os.path.join(ls_env, "Library", "bin"), fb, env.get("PATH", "")])
            for k in ("TRANSFORMERS_CACHE", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_OFFLINE", "HF_HUB_OFFLINE"):
                env.pop(k, None)

            warmup_code = (
                "import sys, os; "
                "sys.path.insert(0, os.getcwd()); "
                "import torch; "
                "print('[WARMUP] PyTorch loaded'); "
                "from omegaconf import OmegaConf; "
                "print('[WARMUP] OmegaConf loaded'); "
                "from latentsync.utils.util import load_model; "
                "print('[WARMUP] _internal_sync modules loaded'); "
                "print('[WARMUP] Engine warmup complete')"
            )
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.run(
                [LATENTSYNC_PYTHON, "-c", warmup_code],
                cwd=LATENTSYNC_DIR, env=env,
                capture_output=True, text=True, timeout=120,
                creationflags=flags
            )
            if proc.returncode == 0:
                safe_print("[WARMUP] _internal_sync 引擎预热完成")
            else:
                safe_print(f"[WARMUP] _internal_sync 预热返回非零码: {proc.returncode}")
                if proc.stderr:
                    safe_print(f"[WARMUP] stderr: {proc.stderr[-300:]}")
        except subprocess.TimeoutExpired:
            safe_print("[WARMUP] _internal_sync 预热超时，跳过")
        except Exception as e:
            safe_print(f"[WARMUP] _internal_sync 预热失败: {e}")

    threading.Thread(target=_warmup_latentsync, daemon=True).start()


# ══════════════════════════════════════════════════════════════
#  语音合成
# ══════════════════════════════════════════════════════════════
def generate_speech(text, prompt_audio, top_p, top_k, temperature, num_beams,
                    repetition_penalty, max_mel_tokens, emo_mode, emo_audio, emo_weight,
                    emo_text, vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                    progress=gr.Progress()):
    global tts
    if tts is None:          raise gr.Error("模型未加载，请等待初始化完成")
    if not text.strip():     raise gr.Error("请输入要合成的文本内容")
    if prompt_audio is None: raise gr.Error("请上传参考音频文件")

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


# ══════════════════════════════════════════════════════════════
#  进度行解析
# ══════════════════════════════════════════════════════════════
def parse_progress_line(line: str):
    try:
        if "|" not in line or "/" not in line: return None
        low = line.lower()

        # 判断阶段
        if   "preprocess" in low or "loading" in low: stage = "预处理"
        elif "inference"  in low:                     stage = "推理"
        elif "postprocess" in low or "saving" in low: stage = "后处理"
        else:                                          stage = "生成"

        # 判断进度类型（步骤进度 vs 帧进度）
        progress_type = "frame" if "frame" in low else "step"

        mp = re.search(r'(\d+)%', line)
        ms = re.search(r'(\d+)/(\d+)', line)
        if not mp or not ms: return None
        return stage, int(mp.group(1)), int(ms.group(1)), int(ms.group(2)), progress_type
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
#  视频格式转换
# ══════════════════════════════════════════════════════════════
def convert_video_for_browser(video_path, progress=gr.Progress()):
    if not video_path or not os.path.exists(video_path): return None
    ffmpeg = os.path.join(LATENTSYNC_DIR, "ffmpeg-7.1", "bin", "ffmpeg.exe")
    if not os.path.exists(ffmpeg): return video_path
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

# ══════════════════════════════════════════════════════════════
#  视频合成（带进度更新）
# ══════════════════════════════════════════════════════════════
def run_latentsync(video_path, audio_path, progress=gr.Progress(), detail_cb=None, output_path_override=None):
    if not video_path:                 raise gr.Error("请上传人物视频")
    if not audio_path:                 raise gr.Error("请先在步骤1准备音频（文字转语音 或 直接上传音频文件）")
    if not os.path.exists(video_path): raise gr.Error("视频文件不存在，请重新上传")
    if not os.path.exists(audio_path): raise gr.Error("音频文件不存在，请重新选择")

    ts  = int(time.time())
    sv  = os.path.join(OUTPUT_DIR, f"in_v_{ts}{os.path.splitext(video_path)[1]}")
    sa  = os.path.join(OUTPUT_DIR, f"in_a_{ts}{os.path.splitext(audio_path)[1]}")
    out = output_path_override if output_path_override else os.path.join(OUTPUT_DIR, f"lipsync_{ts}.mp4")
    try:
        shutil.copy2(video_path, sv); shutil.copy2(audio_path, sa)
    except Exception as e:
        raise gr.Error("复制文件失败: " + str(e))

    progress(0.05, desc="初始化中...")
    env     = os.environ.copy()
    ls_env  = os.path.join(LATENTSYNC_DIR, "latents_env")
    fb      = os.path.join(LATENTSYNC_DIR, "ffmpeg-7.1", "bin")
    env["HF_HOME"]    = os.path.join(LATENTSYNC_DIR, "huggingface")
    env["PYTHONPATH"] = LATENTSYNC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    env["PATH"]       = ";".join([ls_env, os.path.join(ls_env, "Library","bin"), fb, env.get("PATH","")])
    for k in ("TRANSFORMERS_CACHE","HUGGINGFACE_HUB_CACHE","TRANSFORMERS_OFFLINE","HF_HUB_OFFLINE"):
        env.pop(k, None)

    cmd = [LATENTSYNC_PYTHON, "-m", "scripts.inference",
           "--unet_config_path", LATENTSYNC_CONFIG,
           "--inference_ckpt_path", LATENTSYNC_CKPT,
           "--video_path", sv, "--audio_path", sa,
           "--video_out_path", out,
           "--inference_steps", "12", "--guidance_scale", "1.2", "--seed", "1247"]

    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, cwd=LATENTSYNC_DIR, env=env,
                                encoding="utf-8", errors="replace", creationflags=flags, bufsize=1)
    except subprocess.SubprocessError as e:
        raise gr.Error("启动生成引擎失败: " + str(e))

    last = 0.05
    progress(0.08, desc="正在生成视频...")

    # 保存两层进度信息
    step_progress = None  # 步骤进度 (3/4)
    frame_progress = None  # 帧进度 (13/21)
    
    # 模型加载阶段 — 静默处理，只显示统一的"正在生成"
    model_loaded = False

    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None: break
        if not line: continue
        line = line.strip()
        if not line: continue
        safe_print("[LS] " + line)
        
        # 模型加载阶段：不显示细节，统一显示"正在生成视频"
        loading_keywords = ["Loading", "loading", "Initializing", "initializing", "model", "checkpoint"]
        if not model_loaded and any(kw in line for kw in loading_keywords):
            if last < 0.12:
                last = min(last + 0.005, 0.12)
                progress(last, desc="正在生成视频...")
            continue
        
        parsed = parse_progress_line(line)
        if not parsed: continue
        model_loaded = True  # 有实际进度了 = 模型已加载
        stage, pct, cur, total, progress_type = parsed

        # 根据类型保存进度
        if progress_type == "step":
            step_progress = (pct, cur, total)
        elif progress_type == "frame":
            frame_progress = (pct, cur, total)

        if stage == "预处理":
            prog = 0.08 + (pct / 100.0) * 0.04
            desc = f"预处理 {pct}%"
        elif stage in ("推理", "生成"):
            if pct >= 100:
                prog = 0.89; desc = "生成中..."
            else:
                if frame_progress:
                    prog = 0.12 + (frame_progress[0] / 100.0) * 0.76
                    f_pct, f_cur, f_total = frame_progress
                    if step_progress:
                        s_pct, s_cur, s_total = step_progress
                        desc = f"生成中 {prog*100:.0f}%  帧{f_cur}/{f_total}  步骤{s_cur}/{s_total}"
                        if detail_cb:
                            detail_cb(_make_detail_html(f_pct, f_cur, f_total, s_pct, s_cur, s_total, prog))
                    else:
                        desc = f"生成中 {prog*100:.0f}%（{f_cur}/{f_total}）"
                else:
                    prog = 0.12 + (pct / 100.0) * 0.76
                    desc = f"生成中 {prog*100:.0f}%（{cur}/{total}）"
        elif stage == "后处理":
            prog = 0.90 + (pct / 100.0) * 0.06
            desc = f"收尾处理 {pct}%"
        else:
            prog = last; desc = f"{stage} {pct}%"

        prog = max(prog, last); last = prog
        progress(prog, desc=desc)

    if last < 0.93:
        progress(0.94, desc="写入文件...")
    if proc.wait() != 0:
        raise gr.Error("视频合成失败，请检查视频/音频格式是否正确")
    if not os.path.exists(out):
        raise gr.Error("输出视频文件未找到，请重试")

    progress(1.0, desc="✅ 完成")
    for f in (sv, sa):
        try:
            if os.path.exists(f): os.remove(f)
        except Exception:
            pass

    try:
        entry = {"time": time.strftime("%Y-%m-%d %H:%M"), "video_path": out,
                 "size_mb": round(os.path.getsize(out)/1048576, 1)}
        hist = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as hf:
                hist = json.load(hf)
        hist.insert(0, entry)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as hf:
            json.dump(hist[:50], hf, ensure_ascii=False)
    except Exception:
        pass
    return out, "✅ 视频合成完成"



# ══════════════════════════════════════════════════════════════
#  批量任务辅助函数
# ══════════════════════════════════════════════════════════════
def generate_speech_batch(text, prompt_audio, out_path,
                          top_p=0.8, top_k=30, temperature=0.8,
                          num_beams=3, repetition_penalty=10.0, max_mel_tokens=1500):
    global tts
    if tts is None: raise RuntimeError("模型未加载")
    if not text.strip(): raise RuntimeError("文本为空")
    if not prompt_audio: raise RuntimeError("缺少参考音频")
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
            
            safe_print(f"[TextExtractor] 正在连接 {self._ws_url}")
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
            safe_print(f"[TextExtractor] 已发送注册消息")
            
            # 等待注册响应
            try:
                response = await asyncio.wait_for(self._ws.recv(), timeout=10)
                safe_print(f"[TextExtractor] 收到注册响应: {response}")
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
                safe_print(f"[TextExtractor] 收到消息: {message[:200]}..." if len(message) > 200 else f"[TextExtractor] 收到消息: {message}")
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

                    # ═══ 步骤 1：文案提取 ═══════════════════════════
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
                            
                            input_text = gr.TextArea(
                                label="文案内容",
                                placeholder="在此输入或粘贴文案内容，或使用上方提取功能...",
                                lines=6)
                            
                            gr.HTML('<div style="font-size:11px;color:#94a3b8;padding:4px 8px;margin-bottom:8px;">AI智能改写文案，同时生成标题和话题标签（节省算力）</div>')
                            rewrite_btn = gr.Button("✨ AI改写 + 标题标签", variant="secondary", size="sm")

                    # ═══ 步骤 2：音频合成 ═══════════════════════════
                    with gr.Column(scale=1):
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
                                gr.HTML('<div class="section-label">🎙 音色选择</div>')
                                with gr.Row():
                                    voice_select = gr.Dropdown(
                                        label="从音色库选择",
                                        choices=_vc.get_choices() if _LIBS_OK else [],
                                        value=None, interactive=True, scale=4)
                                    voice_refresh_btn = gr.Button("⟳", scale=1, min_width=40,
                                                                  variant="secondary")
                                voice_preview = gr.Audio(label="🔊 试听所选音色", interactive=False,
                                                         visible=False)
                                
                                # 隐藏的 prompt_audio 组件（用于内部逻辑，不显示给用户）
                                prompt_audio = gr.Audio(visible=False, type="filepath")

                                # ── 语音风格预设 ──
                                voice_style = gr.Radio(
                                    label="语音风格",
                                    choices=["标准", "稳定播报", "活泼生动", "慢速朗读", "专业模式"],
                                    value="标准",
                                    elem_classes="voice-style-radio")
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
                    with gr.Column(scale=1):
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

                            ls_btn = gr.Button("🚀  开始合成", variant="primary", size="lg")
                            
                            # ── 合成视频显示区（在步骤3内部）──
                            ls_detail_html = gr.HTML(value="", visible=False, elem_id="ls-detail-box")
                            output_video = gr.Video(
                                label="✨ 合成视频",
                                height=400, elem_id="output-video", interactive=False)

                    # ═══ 步骤 4+5：字幕合成 + 发布平台（右侧纵向排列）═══════════════════════════
                    with gr.Column(scale=2):
                        # 步骤4：字幕合成（上方）
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">4</div>'
                            '<span class="step-title">字幕合成</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            # ══ 字幕面板 ══════════════════════════════
                            with gr.Group(elem_classes="subtitle-panel"):
                                gr.HTML(
                                    '<div class="subtitle-panel-head">'
                                    '<div class="subtitle-panel-icon">✏️</div>'
                                    '<span class="subtitle-panel-title">智能字幕</span>'
                                    '<span class="subtitle-panel-tip">✨ 支持关键词高亮</span>'
                                    '</div>'
                                )
                                # 行1：字体 字号 位置
                                with gr.Row():
                                    sub_font = gr.Dropdown(
                                        label="字体",
                                        choices=_sub.get_font_choices() if _LIBS_OK else ["系统字体"],
                                        value="系统字体",
                                        interactive=True, scale=3)
                                    sub_size = gr.Slider(label="字号 px", minimum=16, maximum=72,
                                                         value=32, step=2, scale=3)
                                    sub_pos = gr.Radio(label="位置", choices=["上","中","下"],
                                                       value="下", scale=2,
                                                       elem_classes="sub-pos-radio")
                                # 行2：颜色 — 每行2个确保显示完整
                                with gr.Row():
                                    sub_color_txt = gr.ColorPicker(
                                        label="字幕颜色", value="#FFFFFF", scale=1)
                                    sub_hi_txt = gr.ColorPicker(
                                        label="高亮颜色", value="#FFD700", scale=1)
                                with gr.Row():
                                    sub_outline_txt = gr.ColorPicker(
                                        label="描边颜色", value="#000000", scale=1,
                                        elem_id="sub-outline-color")
                                    sub_outline_size = gr.Slider(
                                        label="描边宽度 px", minimum=0, maximum=10,
                                        value=6, step=1, scale=1)
                                with gr.Row():
                                    sub_bg_color = gr.ColorPicker(
                                        label="背景颜色", value="#000000", scale=1)
                                    sub_bg_opacity = gr.Slider(
                                        label="背景透明度", minimum=0, maximum=100,
                                        value=0, step=5, scale=1,
                                        info="0=全透明 100=不透明")
                                # 行3：关键词高亮
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
                                # 行4：标题设置
                                gr.HTML('<div style="font-size:12px;font-weight:700;color:#475569;margin:10px 0 6px;">📌 标题设置（显示在视频顶部）</div>')
                                sub_title_text = gr.Textbox(
                                    label="标题内容",
                                    placeholder="输入标题文字，留空则不显示标题",
                                    max_lines=1)
                                with gr.Row():
                                    sub_title_duration = gr.Slider(
                                        label="显示时长(秒)", minimum=1, maximum=30,
                                        value=5, step=1, scale=2)
                                    sub_title_margin_top = gr.Slider(
                                        label="距顶部距离 px", minimum=0, maximum=200,
                                        value=30, step=5, scale=2)
                                with gr.Row():
                                    sub_title_color = gr.ColorPicker(
                                        label="标题颜色", value="#FFFFFF", scale=1)
                                    sub_title_outline_color = gr.ColorPicker(
                                        label="标题描边颜色", value="#000000", scale=1)
                                # 行5：字幕文本
                                sub_text = gr.Textbox(
                                    label="字幕内容（语音合成后自动填入）",
                                    placeholder="完成步骤1语音合成后会自动填入文字，也可手动编辑...",
                                    lines=2)
                                sub_btn = gr.Button("✨  生成带字幕视频", variant="primary", size="lg")
                                sub_hint = gr.HTML(value="")
                        
                        # 字幕视频显示区（独立的panel，紧跟在字幕面板后面）
                        with gr.Column(elem_classes="panel", visible=False, elem_id="sub-video-panel") as sub_video_panel:
                            sub_video = gr.Video(label="🎬 字幕版视频", height=280,
                                                 interactive=False)
                        
                        # 步骤5：发布平台（下方）
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">5</div>'
                            '<span class="step-title">发布平台</span>'
                            '</div>'
                        )
                        with gr.Column(elem_classes="panel"):
                            gr.HTML('<div style="font-size:13px;color:#64748b;margin-bottom:12px;">优先发布字幕视频，如无字幕则发布合成视频</div>')
                            
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
                    
            # ── Tab 2：合成历史 ──────────────────────────────
            with gr.Tab("📁  合成历史", elem_classes="hist-tab"):
                with gr.Row(elem_classes="workspace"):
                    with gr.Column(scale=1, elem_classes="panel"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">📋</span>历史记录</div>')
                        with gr.Row():
                            refresh_hist_btn = gr.Button("🔄  刷新列表", variant="secondary", scale=1, min_width=100)
                            open_folder_btn  = gr.Button("📂  打开文件夹", variant="secondary", scale=1, min_width=120)
                            clear_hist_btn   = gr.Button("🗑  清空历史", variant="stop", scale=1, min_width=100)
                        hist_dropdown = gr.Dropdown(
                            label="选择记录（点击直接播放）",
                            choices=[], value=None, interactive=True)
                        gr.HTML('<div class="divider"></div>')
                        hist_info = gr.HTML(
                            value='<div style="font-size:12px;color:#94a3b8;padding:8px 0">尚无记录，完成一次视频合成后自动保存。</div>'
                        )

                        # ── 清空确认弹窗（默认隐藏）──
                        with gr.Group(visible=False, elem_id="clear-confirm-overlay") as clear_confirm_group:
                            gr.HTML("""
                            <div style="text-align:center;padding-bottom:8px;">
                              <div style="width:52px;height:52px;border-radius:14px;
                                background:linear-gradient(135deg,#fbbf24,#f59e0b);
                                display:flex;align-items:center;justify-content:center;
                                margin:0 auto 16px;font-size:26px;">🗑</div>
                              <div style="font-size:18px;font-weight:800;color:#0f172a;margin-bottom:10px;">
                                清空历史记录
                              </div>
                              <div style="font-size:13px;color:#64748b;line-height:1.8;margin-bottom:4px;">
                                请选择清空方式：
                              </div>
                              <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
                                padding:12px 14px;text-align:left;font-size:12px;color:#475569;line-height:1.9;">
                                <b>🗂 仅移除记录</b> — 清空历史列表，磁盘视频文件<b>保留不动</b><br>
                                <b>🗑 连同文件删除</b> — 清空列表并<b>彻底删除</b>所有已生成视频
                              </div>
                            </div>
                            """)
                            with gr.Row():
                                cancel_clear_btn    = gr.Button("取消", variant="secondary", scale=1)
                                clear_records_btn   = gr.Button("🗂 仅移除记录", variant="secondary", scale=1)
                                clear_all_files_btn = gr.Button("🗑 连同文件一起删除", variant="stop", scale=1)

                    with gr.Column(scale=2, elem_classes="panel"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">▶</span>视频预览</div>')
                        hist_video = gr.Video(label="", height=420, interactive=False)


            # ── Tab 3：数字人管理 ────────────────────────────
            with gr.Tab("🎭  数字人"):
                with gr.Row(elem_classes="workspace"):

                    # 左列：上传
                    with gr.Column(scale=1, elem_classes="panel"):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);">＋</div>'
                            '<span class="step-title">添加数字人</span>'
                            '</div>'
                        )
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
                    with gr.Column(scale=2, elem_classes="panel"):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num">📋</div>'
                            '<span class="step-title">数字人库</span>'
                            '</div>'
                        )
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

            # ── Tab 4：音色模型 ───────────────────────────────
            with gr.Tab("🎙  音色模型"):
                with gr.Row(elem_classes="workspace"):

                    # 左列：上传
                    with gr.Column(scale=1, elem_classes="panel"):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#0ea5e9,#0284c7);">＋</div>'
                            '<span class="step-title">添加音色</span>'
                            '</div>'
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
                            '📁 存储于 <b>voices/</b> 目录</div>'
                        )
                        vc_del_dd   = gr.Textbox(visible=False, value="")
                        vc_del_btn  = gr.Button("删除", visible=False)
                        vc_del_hint = gr.HTML(value="")

                    # 右列：画廊（行内🗑）+ JS桥接 + 试听
                    with gr.Column(scale=2, elem_classes="panel"):
                        gr.HTML(
                            '<div class="step-header">'
                            '<div class="step-num" style="background:linear-gradient(135deg,#0ea5e9,#0284c7);">📋</div>'
                            '<span class="step-title">音色库</span>'
                            '</div>'
                        )
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
                            run_latentsync(vp, ap, output_path_override=op)
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

        def _hist_choices():
            if not os.path.exists(HISTORY_FILE): return []
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as hf:
                    h = json.load(hf)
                return [
                    (f'{"✅" if os.path.exists(i["video_path"]) else "❌"}  '
                     f'{i["time"]}  {os.path.basename(i["video_path"])}  ({i["size_mb"]}MB)',
                     i["video_path"])
                    for i in h
                ]
            except Exception:
                return []

        def _hist_info_html():
            choices = _hist_choices()
            if not choices:
                return '<div style="font-size:12px;color:#94a3b8;padding:8px 0">尚无记录。</div>'
            total = len(choices)
            ok    = sum(1 for _,p in choices if os.path.exists(p))
            return (f'<div style="font-size:12px;color:#475569;padding:8px 0">'
                    f'共 <b>{total}</b> 条，<span style="color:#16a34a">✅ {ok} 个有效</span></div>')

        # ══════════════════════════════════════════════════════════════
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
                return gr.update(choices=[], value=None), _hint_html("ok", "✅ 已清空所有工作台记录")
            except Exception as e:
                return gr.update(), _hint_html("error", f"清空失败: {e}")

        def _auto_save_workspace(input_text, prompt_audio, voice_select_val, audio_mode_val,
                                direct_audio, avatar_select_val, audio_for_ls_val,
                                output_audio_val, output_video_val,
                                sub_text_val, sub_video_val,
                                # 字幕参数
                                sub_font_val, sub_size_val, sub_pos_val,
                                sub_color_val, sub_hi_val, sub_outline_val, sub_outline_size_val,
                                sub_bg_color_val, sub_bg_opacity_val,
                                sub_kw_enable_val, sub_hi_scale_val, sub_kw_text_val):
            """自动保存当前工作台状态 - 相同文本则更新，不同文本则新建"""
            try:
                # 强制输出到文件以便调试
                debug_file = os.path.join(OUTPUT_DIR, "debug_save.txt")
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] _auto_save_workspace 被调用\n")
                    f.write(f"  output_audio_val type: {type(output_audio_val)}, value: {output_audio_val}\n")
                    f.write(f"  audio_for_ls_val type: {type(audio_for_ls_val)}, value: {audio_for_ls_val}\n")
                    f.write(f"  output_video_val type: {type(output_video_val)}, value: {output_video_val}\n")
                    f.write(f"  sub_text_val: {sub_text_val}\n")
                
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
                    "sub_size": to_json_safe(sub_size_val) or 32,
                    "sub_pos": to_json_safe(sub_pos_val) or "下",
                    "sub_color": to_json_safe(sub_color_val) or "#FFFFFF",
                    "sub_hi_color": to_json_safe(sub_hi_val) or "#FFD700",
                    "sub_outline_color": to_json_safe(sub_outline_val) or "#000000",
                    "sub_outline_size": to_json_safe(sub_outline_size_val) or 6,
                    "sub_bg_color": to_json_safe(sub_bg_color_val) or "#000000",
                    "sub_bg_opacity": to_json_safe(sub_bg_opacity_val) or 0,
                    "sub_kw_enable": bool(sub_kw_enable_val) if sub_kw_enable_val is not None else False,
                    "sub_hi_scale": to_json_safe(sub_hi_scale_val) or 1.5,
                    "sub_kw_text": to_json_safe(sub_kw_text_val),
                }
                
                # 读取现有记录
                records = _load_workspace_records()
                
                # 查找是否有相同文本的记录（只比较文本内容）
                existing_idx = -1
                for i, rec in enumerate(records):
                    if rec.get("input_text", "").strip() == text:
                        existing_idx = i
                        break
                
                if existing_idx >= 0:
                    # 更新现有记录
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
                    return [gr.update()] * 23 + [_hint_html("warning", "无效的记录索引")]
                
                record_idx = int(record_idx_str)
                records = _load_workspace_records()
                
                if record_idx < 0 or record_idx >= len(records):
                    return [gr.update()] * 23 + [_hint_html("error", "记录不存在")]
                
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
                    except Exception:
                        pass
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
                
                # 获取字幕视频路径
                sub_video_path = rec.get("sub_video", "")
                if sub_video_path and os.path.exists(sub_video_path):
                    sub_video_update = gr.update(value=sub_video_path, visible=True, show_download_button=True)
                else:
                    sub_video_update = gr.update(visible=False)
                
                # 返回所有需要更新的组件值
                result = [
                    gr.update(value=rec.get("input_text", "")),           # input_text
                    gr.update(value=safe_file_value(rec.get("prompt_audio"))),  # prompt_audio
                    gr.update(value=safe_dropdown_value(rec.get("voice_select"), lambda: _vc.get_choices() if _LIBS_OK else [])),  # voice_select
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
                    gr.update(value=rec.get("sub_size", 32)),             # sub_size
                    gr.update(value=rec.get("sub_pos", "下")),            # sub_pos
                    gr.update(value=rec.get("sub_color", "#FFFFFF")),     # sub_color_txt
                    gr.update(value=rec.get("sub_hi_color", "#FFD700")),  # sub_hi_txt
                    gr.update(value=rec.get("sub_outline_color", "#000000")), # sub_outline_txt
                    gr.update(value=rec.get("sub_outline_size", 6)),      # sub_outline_size
                    gr.update(value=rec.get("sub_bg_color", "#000000")),  # sub_bg_color
                    gr.update(value=rec.get("sub_bg_opacity", 0)),        # sub_bg_opacity
                    gr.update(value=rec.get("sub_kw_enable", False)),     # sub_kw_enable
                    gr.update(value=rec.get("sub_hi_scale", 1.5)),        # sub_hi_scale
                    gr.update(value=rec.get("sub_kw_text", "")),          # sub_kw_text
                    _hint_html("ok", f"已恢复记录：{rec.get('record_name', rec.get('time', '未知'))}")
                ]
                
                with open(debug_file, "a", encoding="utf-8") as f:
                    f.write(f"  返回的 audio_for_ls 更新: {result[6]}\n")
                
                return result
            except Exception as e:
                return [gr.update()] * 23 + [_hint_html("error", f"恢复失败: {str(e)}")]

        # TTS — 后台线程执行，流式返回进度，UI 不卡
        def tts_wrap(text, pa, spd, tp, tk, temp, nb, rp, mmt,
                     emo_m, emo_a, emo_w, emo_t,
                     v1, v2, v3, v4, v5, v6, v7, v8,
                     progress=gr.Progress()):
            # 参数验证
            if not text or not text.strip():
                raise gr.Error("请在文案内容中输入文本")
            if pa is None:
                raise gr.Error("请先选择音色或上传参考音频")
            try:
                progress(0.05, desc="正在合成语音...")
                
                r = generate_speech(text, pa, tp, tk, temp, nb, rp, mmt,
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
                        ffmpeg_bin = os.path.join(LATENTSYNC_DIR, "ffmpeg-7.1", "bin", "ffmpeg.exe")
                        if not os.path.exists(ffmpeg_bin):
                            ffmpeg_bin = "ffmpeg"
                        cmd = [ffmpeg_bin, "-y", "-i", out_path,
                               "-filter:a", f"atempo={atempo_val}",
                               "-vn", tmp_path]
                        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                        subprocess.run(cmd, capture_output=True, timeout=60, creationflags=flags)
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
        def tts_and_save(text, pa, spd, tp, tk, temp, nb, rp, mmt,
                        emo_m, emo_a, emo_w, emo_t,
                        v1, v2, v3, v4, v5, v6, v7, v8,
                        # 保存需要的其他参数
                        voice_sel, audio_mode_val, direct_aud, avatar_sel,
                        out_vid, sub_vid,
                        sub_font_val, sub_size_val, sub_pos_val,
                        sub_color_val, sub_hi_val, sub_outline_val, sub_outline_size_val,
                        sub_bg_color_val, sub_bg_opacity_val,
                        sub_kw_enable_val, sub_hi_scale_val, sub_kw_text_val,
                        progress=gr.Progress()):
            """TTS合成并自动保存工作台状态"""
            # 先执行TTS
            audio_path, audio_for_ls_path = tts_wrap(
                text, pa, spd, tp, tk, temp, nb, rp, mmt,
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
                sub_font_val, sub_size_val, sub_pos_val,
                sub_color_val, sub_hi_val, sub_outline_val, sub_outline_size_val,
                sub_bg_color_val, sub_bg_opacity_val,
                sub_kw_enable_val, sub_hi_scale_val, sub_kw_text_val
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
                input_text, prompt_audio, voice_speed, top_p, top_k, temperature,
                num_beams, repetition_penalty, max_mel_tokens,
                emo_mode, emo_audio, emo_weight, emo_text,
                vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
                # 保存需要的参数
                voice_select, audio_mode, direct_audio_upload, avatar_select,
                output_video, sub_video,
                sub_font, sub_size, sub_pos,
                sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                sub_bg_color, sub_bg_opacity,
                sub_kw_enable, sub_hi_scale, sub_kw_text
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

        # ── 语音风格预设 ──
        _VOICE_PRESETS = {
            "标准":     dict(tp=0.8,  tk=30, temp=0.7, nb=1, rp=8.0,  mmt=1500, spd=1.0),
            "稳定播报": dict(tp=0.6,  tk=10, temp=0.2, nb=3, rp=14.0, mmt=1500, spd=0.95),
            "活泼生动": dict(tp=0.95, tk=60, temp=1.4, nb=1, rp=4.0,  mmt=1500, spd=1.1),
            "慢速朗读": dict(tp=0.6,  tk=10, temp=0.15,nb=3, rp=14.0, mmt=2500, spd=0.9),
        }
        def _on_voice_style(style):
            is_pro = (style == "专业模式")
            if is_pro:
                return [gr.update(visible=True), gr.update()] + [gr.update()] * 6
            p = _VOICE_PRESETS.get(style, _VOICE_PRESETS["标准"])
            return [
                gr.update(visible=False),
                gr.update(value=p["spd"]),
                gr.update(value=p["tp"]),
                gr.update(value=p["tk"]),
                gr.update(value=p["temp"]),
                gr.update(value=p["nb"]),
                gr.update(value=p["rp"]),
                gr.update(value=p["mmt"]),
            ]
        voice_style.change(_on_voice_style,
            inputs=[voice_style],
            outputs=[pro_mode_group, voice_speed, top_p, top_k, temperature, num_beams, repetition_penalty, max_mel_tokens])

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
            """统一返回格式：hint + gallery + 下拉刷新 + 清空隐藏输入框"""
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

        def _save_voice(audio, name):
            if not _LIBS_OK:
                return _vc_all_outputs(_hint_html("error","扩展模块未加载"))
            ok, msg = _vc.add_voice(audio, name)
            return _vc_all_outputs(_hint_html("ok" if ok else "warning", msg))

        vc_save_btn.click(_save_voice,
            inputs=[vc_upload, vc_name],
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

        # ── 字幕生成 ──
        def _do_subtitle(vid, aud, text,
                         font, size, pos,
                         color_txt, hi_txt, outline_txt, outline_size,
                         bg_color, bg_opacity,
                         kw_enable, kw_str, hi_scale,
                         title_text="", title_duration=5,
                         title_color="#FFFFFF", title_outline_color="#000000",
                         title_margin_top=30,
                         progress=gr.Progress()):
            if not _LIBS_OK:
                return gr.update(visible=False), _hint_html("error","扩展模块未加载")

            # 解析视频路径（gr.Video 在不同 Gradio 版本返回格式不同）
            if isinstance(vid, dict):
                vid_path = (vid.get("video") or {}).get("path") or vid.get("path") or ""
            else:
                vid_path = str(vid) if vid else ""
            if not vid_path or not os.path.exists(vid_path):
                return gr.update(visible=False), _hint_html("warning","请先完成视频合成再添加字幕")

            aud_path = str(aud) if (aud and isinstance(aud, str)) else None

            def _cb(pct, msg): progress(pct, desc=msg)
            try:
                out = _sub.burn_subtitles(
                    vid_path, aud_path, text or "",
                    font, size,
                    color_txt, hi_txt, outline_txt, int(outline_size or 0),
                    pos,
                    kw_enable=bool(kw_enable),
                    kw_str=kw_str or "",
                    hi_scale=float(hi_scale or 1.5),
                    bg_color=bg_color or "#000000",
                    bg_opacity=int(bg_opacity or 0),
                    title_text=title_text or "",
                    title_duration=int(title_duration or 5),
                    title_color=title_color or "#FFFFFF",
                    title_outline_color=title_outline_color or "#000000",
                    title_margin_top=int(title_margin_top or 30),
                    progress_cb=_cb
                )
                return (out,
                        _hint_html("ok", "✅ 字幕视频已生成: " + os.path.basename(out)))
            except Exception as e:
                traceback.print_exc()
                return ("",
                        _hint_html("error", f"字幕生成失败: {str(e)[:300]}"))

        # 字幕按钮点击 - 直接在完成后保存
        def subtitle_and_save(out_vid, aud_for_ls, sub_txt, sub_fnt, sub_sz, sub_ps,
                             sub_col, sub_hi, sub_out, sub_out_sz,
                             sub_bg_col, sub_bg_op, sub_kw_en, sub_kw_txt, sub_hi_sc,
                             # 标题参数
                             title_txt, title_dur, title_col, title_out_col, title_mt,
                             # 保存需要的其他参数
                             inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                             avatar_sel, out_aud,
                             progress=gr.Progress()):
            """生成字幕并自动保存工作台状态"""
            # 先生成字幕
            sub_vid_path, sub_hnt = _do_subtitle(
                out_vid, aud_for_ls, sub_txt, sub_fnt, sub_sz, sub_ps,
                sub_col, sub_hi, sub_out, sub_out_sz,
                sub_bg_col, sub_bg_op, sub_kw_en, sub_kw_txt, sub_hi_sc,
                title_text=title_txt or "",
                title_duration=int(title_dur or 5),
                title_color=title_col or "#FFFFFF",
                title_outline_color=title_out_col or "#000000",
                title_margin_top=int(title_mt or 30),
                progress=progress
            )
            
            # 保存工作台状态
            # 注意：使用实际的音频和视频路径
            hint_msg, dropdown_update = _auto_save_workspace(
                inp_txt, prmt_aud, voice_sel, audio_mode_val, direct_aud,
                avatar_sel, aud_for_ls, aud_for_ls, out_vid,
                sub_txt, sub_vid_path,
                sub_fnt, sub_sz, sub_ps,
                sub_col, sub_hi, sub_out, sub_out_sz,
                sub_bg_col, sub_bg_op,
                sub_kw_en, sub_hi_sc, sub_kw_txt
            )
            
            # 返回字幕视频，需要设置 visible=True 和 show_download_button=True
            if sub_vid_path:
                sub_vid_update = gr.update(value=sub_vid_path, visible=True, show_download_button=True)
            else:
                sub_vid_update = gr.update(visible=False)
            
            return sub_vid_update, sub_hnt, hint_msg, dropdown_update
        
        sub_btn.click(
            subtitle_and_save,
            inputs=[
                output_video, audio_for_ls,
                sub_text, sub_font, sub_size, sub_pos,
                sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                sub_bg_color, sub_bg_opacity,
                sub_kw_enable, sub_kw_text, sub_hi_scale,
                # 标题参数
                sub_title_text, sub_title_duration, sub_title_color,
                sub_title_outline_color, sub_title_margin_top,
                # 保存需要的参数
                input_text, prompt_audio, voice_select, audio_mode, direct_audio_upload,
                avatar_select, output_audio
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
        
        def _call_deepseek_api(prompt, system_prompt="你是一个专业的文案创作助手。"):
            """
            调用DeepSeek API
            :param prompt: 用户提示词
            :param system_prompt: 系统提示词
            :return: API返回的文本内容
            """
            try:
                import requests
                
                # DeepSeek API配置
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                if not api_key:
                    # 尝试从.env文件读取
                    env_file = os.path.join(BASE_DIR, ".env")
                    if os.path.exists(env_file):
                        with open(env_file, "r", encoding="utf-8") as f:
                            for line in f:
                                if line.startswith("DEEPSEEK_API_KEY="):
                                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                    break
                
                if not api_key:
                    return None, "❌ 未配置DeepSeek API密钥\n\n请在.env文件中添加：\nDEEPSEEK_API_KEY=your_api_key"
                
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
            """使用DeepSeek AI改写文案，同时优化标题和生成话题标签（单次API调用节省算力）"""
            if not original_text or not original_text.strip():
                return original_text, "", "", _hint_html("warning", "⚠️ 请先输入文本内容")
            
            prompt = f"""请完成以下三个任务：

任务一：将以下文案改写得更加生动、吸引人，保持原意但提升表达效果。
要求：保持原文的核心信息和长度，使用更生动的词汇和表达方式，让文案更有感染力和吸引力。

任务二：根据文案内容，生成一个吸引人的短视频标题（不超过30字，吸引眼球、引发好奇）。

任务三：根据文案内容，生成5个相关的热门话题标签，用逗号分隔。

原文案：
{original_text}

请严格按照以下格式输出，不要添加其他内容：
文案：[改写后的完整文案]
标题：[你的标题]
话题：[话题1,话题2,话题3,话题4,话题5]"""
            
            result, error = _call_deepseek_api(prompt)
            
            if error:
                return original_text, "", "", _hint_html("error", error)
            
            if result:
                # 解析返回结果
                lines = result.strip().split('\n')
                new_text = original_text
                new_title = ""
                new_topics = ""
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("文案：") or line.startswith("文案:"):
                        new_text = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                    elif line.startswith("标题：") or line.startswith("标题:"):
                        new_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                    elif line.startswith("话题：") or line.startswith("话题:"):
                        new_topics = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                
                # 如果没解析到文案（可能AI没严格按格式），用整个结果作为改写文案
                if new_text == original_text and not any(
                    line.strip().startswith(("文案：", "文案:")) for line in lines
                ):
                    # 尝试把标题/话题之前的内容作为文案
                    text_parts = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith(("标题：", "标题:", "话题：", "话题:")):
                            break
                        if line:
                            text_parts.append(line)
                    if text_parts:
                        new_text = "\n".join(text_parts)
                
                return new_text, new_title, new_topics, _hint_html("ok", "✅ AI改写完成！已同时生成标题和话题标签")
            else:
                return original_text, "", "", _hint_html("error", "❌ AI改写失败，未返回内容")
        
        def _optimize_title_with_deepseek(current_title, current_topics, video_text):
            """使用DeepSeek AI优化标题并生成话题标签"""
            if not video_text or not video_text.strip():
                return current_title, current_topics, _hint_html("warning", "⚠️ 请先输入视频文本内容")
            
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
                
                return new_title, new_topics, _hint_html("ok", "✅ AI优化完成！")
            else:
                return current_title, current_topics, _hint_html("error", "❌ AI优化失败，未返回内容")
        
        # 绑定AI改写按钮（一次API调用同时改写文案+生成标题+生成标签）
        rewrite_btn.click(
            _rewrite_text_with_deepseek,
            inputs=[input_text],
            outputs=[input_text, douyin_title, douyin_topics, tts_hint])
        
        # 清空提示
        input_text.change(lambda: "", outputs=[tts_hint])
        
        # 绑定AI优化按钮
        optimize_btn.click(
            _optimize_title_with_deepseek,
            inputs=[douyin_title, douyin_topics, input_text],
            outputs=[douyin_title, douyin_topics, douyin_hint])
        
        # 抖音发布
        def _do_douyin_publish(sub_video, output_video, title_text, topics_text, progress=gr.Progress()):
            """发布视频到抖音 - 优先使用字幕视频，如果没有则使用最终合成视频"""
            try:
                # 检查依赖是否安装
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
                    return _hint_html("error", 
                            f"❌ 缺少依赖：{deps_str}<br><br>"
                            "请运行以下命令安装：<br>"
                            "1. 双击运行「安装抖音发布依赖.bat」<br>"
                            "或<br>"
                            f"2. 手动运行：pip install {' '.join(missing_deps)}")
                
                # 导入抖音发布模块
                import lib_douyin_publish as douyin_pub
                
                # 优先使用字幕视频，如果没有则使用最终合成视频
                video_to_use = None
                video_type = ""
                
                # 解析字幕视频路径
                if sub_video:
                    if isinstance(sub_video, dict):
                        sub_video_path = (sub_video.get("video") or {}).get("path") or sub_video.get("path") or sub_video.get("value") or ""
                    else:
                        sub_video_path = str(sub_video) if sub_video else ""
                    
                    if sub_video_path and os.path.exists(sub_video_path):
                        video_to_use = sub_video_path
                        video_type = "字幕视频"
                
                # 如果没有字幕视频，使用最终合成视频
                if not video_to_use and output_video:
                    if isinstance(output_video, dict):
                        output_video_path = (output_video.get("video") or {}).get("path") or output_video.get("path") or output_video.get("value") or ""
                    else:
                        output_video_path = str(output_video) if output_video else ""
                    
                    if output_video_path and os.path.exists(output_video_path):
                        video_to_use = output_video_path
                        video_type = "合成视频"
                
                if not video_to_use:
                    return _hint_html("warning", "⚠️ 请先生成视频（可以是最终合成视频或字幕视频）")
                
                # 解析话题
                topics = []
                if topics_text:
                    topics = [t.strip() for t in re.split(r'[,，、\s]+', topics_text.strip()) if t.strip()]
                
                # 创建发布器
                publisher = douyin_pub.DouyinPublisher()
                
                # 进度回调
                def progress_cb(pct, msg):
                    progress(pct / 100, desc=msg)
                
                # 发布
                success, message = publisher.publish(
                    video_to_use,
                    title_text or "精彩视频",
                    topics,
                    progress_callback=progress_cb
                )
                
                if success:
                    return _hint_html("ok", f"✅ {message}<br>发布的视频：{video_type}")
                else:
                    return _hint_html("error", f"❌ {message}")
                    
            except Exception as e:
                traceback.print_exc()
                error_msg = str(e)
                
                # 友好的错误提示
                if "chromedriver" in error_msg.lower() or "chrome" in error_msg.lower():
                    return _hint_html("error", 
                            "❌ Chrome 浏览器驱动问题<br><br>"
                            "请尝试：<br>"
                            "1. 双击运行「安装抖音发布依赖.bat」<br>"
                            "2. 确保已安装 Chrome 浏览器<br>"
                            "3. 重启程序")
                else:
                    return _hint_html("error", f"❌ 发布失败: {error_msg[:300]}")
        
        douyin_btn.click(_do_douyin_publish,
            inputs=[sub_video, output_video, douyin_title, douyin_topics],
            outputs=[douyin_hint])

        # 视频合成
        def ls_wrap(avatar_name, auto_a, input_txt, progress=gr.Progress()):
            # 把数字人名转换成文件路径
            video = None
            if _LIBS_OK and avatar_name and not avatar_name.startswith("（"):
                video = _av.get_path(avatar_name)
            audio  = auto_a
            q      = _queue.Queue()
            result = {"out": None, "err": None}

            def _detail_cb(html):
                q.put(("detail", html))

            def _run():
                try:
                    out, _ = run_latentsync(video, audio, progress, detail_cb=_detail_cb)
                    result["out"] = out
                except Exception as e:
                    result["err"] = e
                finally:
                    q.put(("done",))

            threading.Thread(target=_run, daemon=True).start()

            # 简洁的状态提示（不用大块HTML，直接进度条推进）
            yield gr.update(), gr.update(value='<div style="display:flex;align-items:center;gap:10px;padding:12px 16px;background:#f0f4ff;border:1px solid #c7d2fe;border-radius:10px;"><div style="width:18px;height:18px;border:2.5px solid #c7d2fe;border-top-color:#6366f1;border-radius:50%;animation:zdai-spin .7s linear infinite;flex-shrink:0;"></div><span style="font-size:13px;color:#4338ca;font-weight:600;">正在生成视频，请稍候...</span><style>@keyframes zdai-spin{to{transform:rotate(360deg)}}</style></div>', visible=True)

            while True:
                try:
                    item = q.get(timeout=0.3)
                    if item[0] == "done":
                        break
                    elif item[0] == "detail":
                        yield gr.update(), gr.update(value=item[1], visible=True)
                except _queue.Empty:
                    yield gr.update(), gr.update()

            if result["err"]:
                yield gr.update(), gr.update(visible=False)
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
            yield out, gr.update(visible=False)

        # 视频合成按钮点击 - 直接在完成后保存
        def video_and_save(avatar_sel, aud_for_ls, inp_txt,
                          # 保存需要的其他参数
                          prmt_aud, voice_sel, audio_mode_val, direct_aud,
                          out_aud, sub_txt, sub_vid,
                          sub_fnt, sub_sz, sub_ps,
                          sub_col, sub_hi, sub_out, sub_out_sz,
                          sub_bg_col, sub_bg_op,
                          sub_kw_en, sub_hi_sc, sub_kw_txt,
                          progress=gr.Progress()):
            """合成视频并自动保存工作台状态"""
            # 先合成视频（ls_wrap 是生成器，需要逐步 yield）
            final_result = None
            for result in ls_wrap(avatar_sel, aud_for_ls, inp_txt, progress=progress):
                # 在视频合成过程中，传递中间结果，但不保存工作台
                # 返回 4 个值：前 2 个来自 ls_wrap，后 2 个是空的工作台更新
                yield result + (gr.update(), gr.update())
                final_result = result
            
            # 视频合成完成后，保存工作台状态
            if final_result:
                video_path, ls_detail = final_result
                
                # 现在 video_path 直接就是视频路径字符串
                # 不需要从 gr.update 对象中提取
                
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
                    sub_fnt, sub_sz, sub_ps,
                    sub_col, sub_hi, sub_out, sub_out_sz,
                    sub_bg_col, sub_bg_op,
                    sub_kw_en, sub_hi_sc, sub_kw_txt
                )
                
                # 最后一次 yield，包含保存结果
                # 注意：第一个值需要是视频路径，Gradio 会自动处理
                yield video_path, ls_detail, hint_msg, dropdown_update
        
        ls_btn.click(
            video_and_save,
            inputs=[
                avatar_select, audio_for_ls, input_text,
                # 保存需要的参数
                prompt_audio, voice_select, audio_mode, direct_audio_upload,
                output_audio, sub_text, sub_video,
                sub_font, sub_size, sub_pos,
                sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                sub_bg_color, sub_bg_opacity,
                sub_kw_enable, sub_hi_scale, sub_kw_text
            ],
            outputs=[output_video, ls_detail_html,
                    workspace_record_hint, workspace_record_dropdown])

        # 历史操作
        def _do_refresh():
            return gr.update(choices=_hist_choices(), value=None), _hist_info_html()
        refresh_hist_btn.click(_do_refresh, outputs=[hist_dropdown, hist_info])

        open_folder_btn.click(
            lambda: (
                subprocess.Popen(["explorer", OUTPUT_DIR],
                    creationflags=subprocess.CREATE_NO_WINDOW)
                if sys.platform == "win32" else None
            ),
            outputs=[])

        # 清空历史：显示确认弹窗
        clear_hist_btn.click(
            lambda: gr.update(visible=True),
            outputs=[clear_confirm_group])

        # 取消
        cancel_clear_btn.click(
            lambda: gr.update(visible=False),
            outputs=[clear_confirm_group])

        # 仅移除记录条目（不删文件）
        def _clear_records_only():
            try:
                if os.path.exists(HISTORY_FILE):
                    os.remove(HISTORY_FILE)
            except Exception:
                pass
            return (gr.update(visible=False),
                    gr.update(choices=[], value=None),
                    '<div style="font-size:12px;color:#94a3b8;padding:8px 0">记录已清空，视频文件仍保留在磁盘上。</div>')

        clear_records_btn.click(
            _clear_records_only,
            outputs=[clear_confirm_group, hist_dropdown, hist_info])

        # 彻底删除（连同文件）
        def _clear_all_with_files():
            deleted, failed = 0, 0
            deleted_paths = set()

            # 第一步：从 history.json 中读取所有记录路径
            try:
                if os.path.exists(HISTORY_FILE):
                    with open(HISTORY_FILE, 'r', encoding='utf-8') as hf:
                        hist = json.load(hf)
                    for item in hist:
                        vp = item.get("video_path", "")
                        if not vp:
                            continue
                        # 兼容正反斜杠
                        vp = os.path.normpath(vp)
                        deleted_paths.add(vp)
                        try:
                            if os.path.exists(vp):
                                os.remove(vp)
                                deleted += 1
                        except Exception:
                            failed += 1
                    os.remove(HISTORY_FILE)
            except Exception:
                pass

            # 第二步：扫描 OUTPUT_DIR，删除所有 lipsync_ / converted_ / tts_ 文件
            try:
                prefixes = ("lipsync_", "converted_", "in_v_", "in_a_")
                for fname in os.listdir(OUTPUT_DIR):
                    if any(fname.startswith(p) for p in prefixes):
                        fpath = os.path.normpath(os.path.join(OUTPUT_DIR, fname))
                        if fpath not in deleted_paths:
                            try:
                                os.remove(fpath)
                                deleted += 1
                                deleted_paths.add(fpath)
                            except Exception:
                                failed += 1
            except Exception:
                pass

            info_msg = (f'<div style="font-size:12px;color:#94a3b8;padding:8px 0">'
                        f'已彻底清空，共删除 <b>{deleted}</b> 个文件'
                        f'{f"，{failed} 个删除失败（可能已被占用）" if failed else ""}。</div>')
            return (gr.update(visible=False),
                    gr.update(choices=[], value=None),
                    info_msg,
                    None)

        clear_all_files_btn.click(
            _clear_all_with_files,
            outputs=[clear_confirm_group, hist_dropdown, hist_info, hist_video])

        def _load_hist(p):
            if not p: return gr.update(value=None), ""
            if not os.path.exists(p):
                return gr.update(value=None), '<div style="font-size:12px;color:#dc2626">❌ 文件不存在</div>'
            sz   = round(os.path.getsize(p)/1048576, 1)
            info = f'<div style="font-size:12px;color:#16a34a;padding:4px 0">✅ {os.path.basename(p)} ({sz} MB)</div>'
            return gr.update(value=p, show_download_button=True), info
        hist_dropdown.change(_load_hist, inputs=[hist_dropdown], outputs=[hist_video, hist_info])

        # ══════════════════════════════════════════════════════════════
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
                sub_font, sub_size, sub_pos,
                sub_color_txt, sub_hi_txt, sub_outline_txt, sub_outline_size,
                sub_bg_color, sub_bg_opacity,
                sub_kw_enable, sub_hi_scale, sub_kw_text,
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

        # 页面加载时自动刷新工作台记录列表和历史记录，并初始化WebSocket连接
        def _init_load():
            # 后台初始化文案提取器的WebSocket连接
            try:
                extractor = get_text_extractor()
                extractor.start()
                safe_print("[TextExtractor] WebSocket 连接已在后台初始化")
            except Exception as e:
                safe_print(f"[TextExtractor] 初始化失败: {e}")
            
            return (
                gr.update(choices=_get_workspace_record_choices()),
                gr.update(choices=_hist_choices(), value=None),
                _hist_info_html()
            )
        
        app.load(_init_load, outputs=[workspace_record_dropdown, hist_dropdown, hist_info])

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
        text="请输入有效卡密完成激活。首次使用前需阅读并勾选平台发布协议。",
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
        text="⚠ 使用平台功能与AI生成功能前，请先阅读并同意协议与风险提示",
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

    def _load_agreement_text():
        default_text = """平台与AI功能使用协议

协议文件缺失：platform_ai_usage_agreement.txt（兼容旧文件名）

请将协议文件放在程序同目录下。"""
        try:
            candidates = []
            for _name in ("PLATFORM_AGREEMENT_FILE", "LEGACY_AGREEMENT_FILE", "DOUYIN_AGREEMENT_FILE"):
                if _name in globals():
                    candidates.append(globals().get(_name))
            candidates.extend([
                os.path.join(BASE_DIR, "platform_ai_usage_agreement.txt"),
                os.path.join(BASE_DIR, "platform_publish_agreement.txt"),
                os.path.join(BASE_DIR, "douyin_publish_agreement.txt"),
            ])
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
        agreement_window.title("平台与AI功能使用协议")
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
        tk.Label(header, text="平台与AI功能使用协议", font=("Microsoft YaHei", 13, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(header, text="请完整阅读后勾选同意。建议由实际运营负责人阅读并确认。", font=("Microsoft YaHei", 9), bg="#ffffff", fg="#64748b").pack(anchor="w", padx=14, pady=(0, 12))

        text_wrap = tk.Frame(shell, bg="#f1f5f9")
        text_wrap.pack(fill="both", expand=True, pady=12)

        text_border = tk.Frame(text_wrap, bg="#cbd5e1", padx=1, pady=1)
        text_border.pack(fill="both", expand=True)

        text_container = tk.Frame(text_border, bg="#ffffff")
        text_container.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side="right", fill="y")

        text_widget = tk.Text(
            text_container,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Microsoft YaHei", 9),
            padx=16,
            pady=14,
            relief="flat",
            bd=0,
            bg="#ffffff",
            fg="#334155",
            insertbackground="#334155",
            spacing1=2,
            spacing2=2,
            spacing3=2
        )
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        text_widget.insert("1.0", _load_agreement_text())
        text_widget.config(state="disabled")

        footer = tk.Frame(shell, bg="#f1f5f9")
        footer.pack(fill="x")
        tk.Label(footer, text="提示：勾选协议仅表示您已知悉并承诺合规使用，不代表平台审核通过或账号安全无风险。",
                 font=("Microsoft YaHei", 8), bg="#f1f5f9", fg="#64748b", wraplength=760, justify="left").pack(anchor="w", pady=(0, 10))
        tk.Button(
            footer,
            text="关闭",
            command=agreement_window.destroy,
            font=("Microsoft YaHei", 10, "bold"),
            bg="#4f46e5",
            fg="white",
            activebackground="#4338ca",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            bd=0,
            padx=20,
            pady=8
        ).pack(side="right")

    link_label = tk.Label(
        agree_row,
        text="《平台与AI功能使用协议》",
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

    # 自定义主按钮（固定高度 + Label 居中，彻底绕开系统按钮字体裁切）
    btn_state = {"enabled": False}

    btn_shell = tk.Frame(action_box, bg="#a5b4fc", height=80, cursor="arrow", relief="flat", bd=0)
    btn_shell.pack(fill="x")
    btn_shell.pack_propagate(False)

    btn_inner = tk.Frame(btn_shell, bg="#a5b4fc", relief="flat", bd=0)
    btn_inner.pack(fill="both", expand=True)

    btn_label = tk.Label(
        btn_inner,
        text="登录启动",
        font=("Microsoft YaHei", 16, "bold"),
        bg="#a5b4fc",
        fg="#eef2ff",
        bd=0
    )
    btn_label.place(relx=0.5, rely=0.5, anchor="center")

    def _btn_click(_e=None):
        if btn_state["enabled"]:
            _do_login()

    for _w in (btn_shell, btn_inner, btn_label):
        _w.bind("<Button-1>", _btn_click)

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

    def _paint_btn(bg: str, fg: str, cursor: str):
        btn_shell.configure(bg=bg, cursor=cursor)
        btn_inner.configure(bg=bg, cursor=cursor)
        btn_label.configure(bg=bg, fg=fg, cursor=cursor)

    def _set_btn_enabled(enabled: bool):
        btn_state["enabled"] = bool(enabled)
        if enabled:
            _paint_btn("#4f46e5", "#ffffff", "hand2")
        else:
            _paint_btn("#a5b4fc", "#eef2ff", "arrow")

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
            msg_label.config(text="请先阅读并勾选《平台与AI功能使用协议》", fg="#ef4444")
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

    def _btn_hover_in(e=None):
        try:
            if btn_state["enabled"]:
                _paint_btn("#4338ca", "#ffffff", "hand2")
        except Exception:
            pass

    def _btn_hover_out(e=None):
        try:
            if btn_state["enabled"]:
                _paint_btn("#4f46e5", "#ffffff", "hand2")
        except Exception:
            pass

    for _w in (btn_shell, btn_inner, btn_label):
        _w.bind("<Enter>", _btn_hover_in)
        _w.bind("<Leave>", _btn_hover_out)

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

    key_entry.bind("<Return>", lambda e: _do_login() if agreement_var.get() else msg_label.config(text="请先勾选并同意《平台与AI功能使用协议》", fg="#ef4444"))

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
                              os.path.join(BASE_DIR,"fonts")],
            )
            break
        except OSError:
            continue
