# -*- coding: utf-8 -*-
import os
import sys
import time
import gc
import subprocess
import traceback
import shutil
import threading
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR = os.path.join(BASE_DIR, "IndexTTS2-SonicVale")
LATENTSYNC_DIR = os.path.join(BASE_DIR, "LatentSync")
OUTPUT_DIR = os.path.join(BASE_DIR, "unified_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# CRITICAL: Set HF cache paths BEFORE any imports that might load infer_v2.py
# infer_v2.py sets HF_HUB_CACHE='./checkpoints/hf_cache' at module level (line 4)
# We must override it with absolute path BEFORE that module is imported
HF_CACHE_DIR = os.path.abspath(os.path.join(INDEXTTS_DIR, "checkpoints", "hf_cache"))
os.makedirs(HF_CACHE_DIR, exist_ok=True)
os.environ['HF_HUB_CACHE'] = HF_CACHE_DIR
os.environ['HF_HOME'] = HF_CACHE_DIR
os.environ['HUGGINGFACE_HUB_CACHE'] = HF_CACHE_DIR
os.environ['TRANSFORMERS_CACHE'] = HF_CACHE_DIR
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

LATENTSYNC_PYTHON = os.path.join(LATENTSYNC_DIR, "latents_env", "python.exe")
LATENTSYNC_CKPT = os.path.join(LATENTSYNC_DIR, "checkpoints", "latentsync_unet.pt")
LATENTSYNC_CONFIG = os.path.join(LATENTSYNC_DIR, "configs", "unet", "stage2.yaml")

# NOW it's safe to add to sys.path - infer_v2.py will see our env vars
sys.path.insert(0, INDEXTTS_DIR)
sys.path.insert(0, os.path.join(INDEXTTS_DIR, "indextts"))

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import gradio as gr
import torch

tts = None
GRADIO_PORT = 7870


def auto_load_model():
    global tts
    model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
    if not os.path.exists(model_dir):
        print(f"[ERR] model dir not found: {model_dir}")
        return
    for f in ["bpe.model", "gpt.pth", "config.yaml", "s2mel.pth", "wav2vec2bert_stats.pt"]:
        if not os.path.exists(os.path.join(model_dir, f)):
            print(f"[ERR] missing: {f}")
            return
    
    original_cwd = os.getcwd()
    os.chdir(INDEXTTS_DIR)
    try:
        print("[MODEL] Loading IndexTTS2...")
        from indextts.infer_v2 import IndexTTS2
        tts = IndexTTS2(
            model_dir=model_dir,
            cfg_path=os.path.join(model_dir, "config.yaml"),
            use_fp16=True,
        )
        print(f"[MODEL] OK (v{tts.model_version or '1.0'})")
    except Exception as e:
        print(f"[MODEL] FAIL: {e}")
        traceback.print_exc()
    finally:
        os.chdir(original_cwd)


def generate_speech(
    text, prompt_audio,
    emo_mode, emo_audio, emo_weight,
    vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8,
    progress=gr.Progress()
):
    global tts
    if tts is None:
        raise gr.Error("Model not loaded!")
    if not text or not text.strip():
        raise gr.Error("Please input text!")
    if prompt_audio is None:
        raise gr.Error("Please upload reference audio!")
    timestamp = int(time.time())
    output_path = os.path.join(OUTPUT_DIR, f"tts_{timestamp}.wav")
    original_cwd = os.getcwd()
    os.chdir(INDEXTTS_DIR)
    try:
        tts.gr_progress = progress
        progress(0.1, desc="Synthesizing...")
        kwargs = {
            "do_sample": True, "top_p": 0.8, "top_k": 30, "temperature": 0.8,
            "length_penalty": 0.0, "num_beams": 3, "repetition_penalty": 10.0,
            "max_mel_tokens": 1500,
        }
        emo_ref = None
        vec = None
        if emo_mode == "\u4f7f\u7528\u60c5\u611f\u53c2\u8003\u97f3\u9891" and emo_audio:
            emo_ref = emo_audio
        elif emo_mode == "\u4f7f\u7528\u60c5\u611f\u5411\u91cf\u63a7\u5236":
            vec = [vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8]
            vec = tts.normalize_emo_vec(vec, apply_bias=True)
        tts.infer(
            spk_audio_prompt=prompt_audio, text=text, output_path=output_path,
            emo_audio_prompt=emo_ref, emo_alpha=emo_weight, emo_vector=vec,
            use_emo_text=False, **kwargs
        )
        os.chdir(original_cwd)
        progress(1.0, desc="Done")
        return output_path, "\u2705 \u8bed\u97f3\u5408\u6210\u5b8c\u6210\uff01", output_path
    except Exception as e:
        os.chdir(original_cwd)
        traceback.print_exc()
        raise gr.Error(f"TTS failed: {e}")


def setup_latentsync_env():
    ckd = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints")
    os.makedirs(ckd, exist_ok=True)
    for fn in ["2DFAN4-cd938726ad.zip", "s3fd-619a316812.pth"]:
        dst = os.path.join(ckd, fn)
        src = os.path.join(LATENTSYNC_DIR, "checkpoints", "auxiliary", fn)
        if not os.path.exists(dst) and os.path.exists(src):
            try:
                os.symlink(src, dst)
            except OSError:
                shutil.copy2(src, dst)


def run_latentsync(video_path, audio_path, progress=gr.Progress()):
    if not video_path:
        raise gr.Error("Please upload video!")
    if not audio_path:
        raise gr.Error("Please generate speech first or upload audio!")
    if not os.path.exists(LATENTSYNC_PYTHON):
        raise gr.Error(f"LatentSync Python not found: {LATENTSYNC_PYTHON}")
    if not os.path.exists(LATENTSYNC_CKPT):
        raise gr.Error(f"LatentSync checkpoint not found: {LATENTSYNC_CKPT}")
    timestamp = int(time.time())
    output_path = os.path.join(OUTPUT_DIR, f"lipsync_{timestamp}.mp4")
    setup_latentsync_env()
    progress(0.05, desc="Preparing LatentSync...")
    env = os.environ.copy()
    ls_env = os.path.join(LATENTSYNC_DIR, "latents_env")
    ffmpeg_path = os.path.join(LATENTSYNC_DIR, "ffmpeg-7.1", "bin")
    env["HF_HOME"] = os.path.join(LATENTSYNC_DIR, "huggingface")
    env["PYTHONPATH"] = LATENTSYNC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    env["PATH"] = f"{ls_env};{os.path.join(ls_env, 'Library', 'bin')};{ffmpeg_path};{env.get('PATH', '')}"
    env.pop("TRANSFORMERS_CACHE", None)
    env.pop("HUGGINGFACE_HUB_CACHE", None)
    cmd = [
        LATENTSYNC_PYTHON, "-m", "scripts.inference",
        "--unet_config_path", LATENTSYNC_CONFIG,
        "--inference_ckpt_path", LATENTSYNC_CKPT,
        "--video_path", video_path,
        "--audio_path", audio_path,
        "--video_out_path", output_path,
        "--inference_steps", "20",
        "--guidance_scale", "1.5",
        "--seed", "1247",
    ]
    print(f"[LatentSync] {' '.join(cmd)}")
    progress(0.1, desc="Running LatentSync...")
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=LATENTSYNC_DIR, env=env,
            encoding="utf-8", errors="replace", creationflags=flags,
        )
        log_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                log_lines.append(line)
                print(f"[LS] {line}")
                if "%" in line:
                    try:
                        pct = float(line.split("%")[0].split()[-1]) / 100.0
                        progress(0.1 + 0.85 * pct)
                    except:
                        pass
        if process.wait() != 0:
            raise gr.Error("LatentSync failed:\n" + "\n".join(log_lines[-10:]))
        if os.path.exists(output_path):
            progress(1.0, desc="Done")
            return output_path, "\u2705 \u53e3\u578b\u540c\u6b65\u89c6\u9891\u751f\u6210\u5b8c\u6210\uff01"
        else:
            raise gr.Error("Output file not found")
    except subprocess.SubprocessError as e:
        raise gr.Error(f"Process failed: {e}")


custom_css = """
.gradio-container { max-width: 100% !important; }
"""


def build_ui():
    with gr.Blocks(css=custom_css, title="TTS + LipSync") as app:
        gr.Markdown("# 璇煶鍚堟垚 + 鍙ｅ瀷鍚屾 宸ヤ綔鍙?)
        
        model_ver = tts.model_version if tts else "?"
        if tts:
            gr.Markdown(f"鉁?妯″瀷宸插姞杞?(v{model_ver})")
        else:
            gr.Markdown("鉂?妯″瀷鏈姞杞?)

        gr.Markdown("## 绗竴姝ワ細璇煶鍚堟垚")
        with gr.Row():
            with gr.Column():
                input_text = gr.TextArea(label="杈撳叆鏂囨湰", placeholder="璇疯緭鍏ヨ鍚堟垚鐨勬枃鏈?..", lines=4)
                prompt_audio = gr.Audio(label="闊宠壊鍙傝€冮煶棰?, sources=["upload", "microphone"], type="filepath")
                with gr.Accordion("鎯呮劅鎺у埗锛堝彲閫夛級", open=False):
                    emo_mode = gr.Radio(
                        choices=["涓庨煶鑹插弬鑰冮煶棰戠浉鍚?, "浣跨敤鎯呮劅鍙傝€冮煶棰?, "浣跨敤鎯呮劅鍚戦噺鎺у埗"],
                        value="涓庨煶鑹插弬鑰冮煶棰戠浉鍚?, label="鎯呮劅鎺у埗鏂瑰紡")
                    emo_audio = gr.Audio(label="鎯呮劅鍙傝€冮煶棰?, type="filepath", visible=False)
                    emo_weight = gr.Slider(label="鎯呮劅鏉冮噸", minimum=0.0, maximum=1.0, value=0.65, step=0.01, visible=False)
                    with gr.Group(visible=False) as vec_group:
                        with gr.Row():
                            vec1 = gr.Slider(label="鍠?, minimum=0, maximum=1, value=0, step=0.05)
                            vec2 = gr.Slider(label="鎬?, minimum=0, maximum=1, value=0, step=0.05)
                            vec3 = gr.Slider(label="鍝€", minimum=0, maximum=1, value=0, step=0.05)
                            vec4 = gr.Slider(label="鎯?, minimum=0, maximum=1, value=0, step=0.05)
                        with gr.Row():
                            vec5 = gr.Slider(label="鍘屾伓", minimum=0, maximum=1, value=0, step=0.05)
                            vec6 = gr.Slider(label="浣庤惤", minimum=0, maximum=1, value=0, step=0.05)
                            vec7 = gr.Slider(label="鎯婂枩", minimum=0, maximum=1, value=0, step=0.05)
                            vec8 = gr.Slider(label="骞抽潤", minimum=0, maximum=1, value=0, step=0.05)
            with gr.Column():
                gen_btn = gr.Button("鐢熸垚璇煶", variant="primary", size="lg")
                tts_status = gr.Markdown("绛夊緟鐢熸垚...")
                output_audio = gr.Audio(label="鐢熸垚鐨勮闊?, interactive=False)

        def on_emo_change(mode):
            show_audio = (mode == "浣跨敤鎯呮劅鍙傝€冮煶棰?)
            show_weight = (mode != "涓庨煶鑹插弬鑰冮煶棰戠浉鍚?)
            show_vec = (mode == "浣跨敤鎯呮劅鍚戦噺鎺у埗")
            return (
                gr.update(visible=show_audio),
                gr.update(visible=show_weight),
                gr.update(visible=show_vec),
            )
        emo_mode.change(on_emo_change, inputs=[emo_mode], outputs=[emo_audio, emo_weight, vec_group])

        gr.Markdown("---")
        gr.Markdown("## 绗簩姝ワ細鍙ｅ瀷鍚屾瑙嗛")
        with gr.Row():
            with gr.Column():
                video_input = gr.Video(label="涓婁紶鍘熷瑙嗛", sources=["upload"])
                audio_for_ls = gr.Audio(label="鍚屾闊抽锛堣嚜鍔ㄤ娇鐢ㄤ笂涓€姝ヨ闊筹級", type="filepath", interactive=True)
                ls_btn = gr.Button("鐢熸垚鍙ｅ瀷鍚屾瑙嗛", variant="primary", size="lg")
                ls_status = gr.Markdown("绛夊緟鐢熸垚...")
            with gr.Column():
                output_video = gr.Video(label="鐢熸垚鐨勮棰?)

        gen_btn.click(
            generate_speech,
            inputs=[input_text, prompt_audio, emo_mode, emo_audio, emo_weight,
                    vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8],
            outputs=[output_audio, tts_status, audio_for_ls])
        ls_btn.click(
            run_latentsync,
            inputs=[video_input, audio_for_ls],
            outputs=[output_video, ls_status])
    return app

