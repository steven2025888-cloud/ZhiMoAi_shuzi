# -*- coding: utf-8 -*-
import os, sys, time, gc, subprocess, traceback, shutil, threading
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR = os.path.join(BASE_DIR, "IndexTTS2-SonicVale")
LATENTSYNC_DIR = os.path.join(BASE_DIR, "LatentSync")
OUTPUT_DIR = os.path.join(BASE_DIR, "unified_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

sys.path.insert(0, INDEXTTS_DIR)
sys.path.insert(0, os.path.join(INDEXTTS_DIR, "indextts"))

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
import gradio as gr
import torch

# 抑制 asyncio 和 h11 的连接错误日志（Edge 视频预览断开连接是正常的）
import logging
logging.getLogger("h11").setLevel(logging.CRITICAL)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

tts = None
GRADIO_PORT = 7870


def auto_load_model():
    global tts
    model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
    if not os.path.exists(model_dir):
        print("[ERR] model dir not found: " + model_dir)
        return
    for f in ["bpe.model", "gpt.pth", "config.yaml", "s2mel.pth", "wav2vec2bert_stats.pt"]:
        if not os.path.exists(os.path.join(model_dir, f)):
            print("[ERR] missing: " + f)
            return
    original_cwd = os.getcwd()
    os.chdir(INDEXTTS_DIR)
    try:
        print("[MODEL] Loading IndexTTS2...")
        from indextts.infer_v2 import IndexTTS2
        tts = IndexTTS2(model_dir=model_dir, cfg_path=os.path.join(model_dir, "config.yaml"), use_fp16=True)
        print("[MODEL] OK (v" + str(tts.model_version or "1.0") + ")")
    except Exception as e:
        print("[MODEL] FAIL: " + str(e))
        traceback.print_exc()
    finally:
        os.chdir(original_cwd)


def generate_speech(text, prompt_audio, emo_mode, emo_audio, emo_weight,
                    vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8, progress=gr.Progress()):
    global tts
    if tts is None:
        raise gr.Error("\u6a21\u578b\u672a\u52a0\u8f7d\uff01")
    if not text or not text.strip():
        raise gr.Error("\u8bf7\u8f93\u5165\u6587\u672c\uff01")
    if prompt_audio is None:
        raise gr.Error("\u8bf7\u4e0a\u4f20\u53c2\u8003\u97f3\u9891\uff01")
    timestamp = int(time.time())
    output_path = os.path.join(OUTPUT_DIR, "tts_" + str(timestamp) + ".wav")
    original_cwd = os.getcwd()
    os.chdir(INDEXTTS_DIR)
    try:
        tts.gr_progress = progress
        progress(0.1, desc="\u6b63\u5728\u5408\u6210...")
        kwargs = {"do_sample": True, "top_p": 0.8, "top_k": 30, "temperature": 0.8,
                  "length_penalty": 0.0, "num_beams": 3, "repetition_penalty": 10.0, "max_mel_tokens": 1500}
        emo_ref = None
        vec = None
        if emo_mode == "\u4f7f\u7528\u60c5\u611f\u53c2\u8003\u97f3\u9891" and emo_audio:
            emo_ref = emo_audio
        elif emo_mode == "\u4f7f\u7528\u60c5\u611f\u5411\u91cf\u63a7\u5236":
            vec = [vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8]
            vec = tts.normalize_emo_vec(vec, apply_bias=True)
        tts.infer(spk_audio_prompt=prompt_audio, text=text, output_path=output_path,
                  emo_audio_prompt=emo_ref, emo_alpha=emo_weight, emo_vector=vec, use_emo_text=False, **kwargs)
        os.chdir(original_cwd)
        progress(1.0, desc="\u5b8c\u6210")
        return output_path, "\u2705 \u8bed\u97f3\u5408\u6210\u5b8c\u6210\uff01", output_path
    except Exception as e:
        os.chdir(original_cwd)
        traceback.print_exc()
        raise gr.Error("TTS \u5931\u8d25: " + str(e))


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
        raise gr.Error("\u8bf7\u4e0a\u4f20\u89c6\u9891\uff01")
    if not audio_path:
        raise gr.Error("\u8bf7\u5148\u751f\u6210\u8bed\u97f3\u6216\u4e0a\u4f20\u97f3\u9891\uff01")
    
    # 验证视频文件是否完整可读
    if not os.path.exists(video_path):
        raise gr.Error("\u89c6\u9891\u6587\u4ef6\u672a\u627e\u5230\uff01\u8bf7\u7b49\u5f85\u4e0a\u4f20\u5b8c\u6210\u3002")
    try:
        file_size = os.path.getsize(video_path)
        if file_size < 1024:
            raise gr.Error("\u89c6\u9891\u6587\u4ef6\u592a\u5c0f\uff0c\u4e0a\u4f20\u53ef\u80fd\u672a\u5b8c\u6210\u3002\u8bf7\u91cd\u8bd5\u3002")
    except Exception as e:
        raise gr.Error("\u65e0\u6cd5\u8bfb\u53d6\u89c6\u9891\u6587\u4ef6: " + str(e))
    
    if not os.path.exists(LATENTSYNC_PYTHON):
        raise gr.Error("LatentSync Python \u672a\u627e\u5230: " + LATENTSYNC_PYTHON)
    if not os.path.exists(LATENTSYNC_CKPT):
        raise gr.Error("LatentSync \u6a21\u578b\u672a\u627e\u5230: " + LATENTSYNC_CKPT)
    
    timestamp = int(time.time())
    
    # 复制文件到安全目录，避免 Gradio 临时文件被清理
    safe_video = os.path.join(OUTPUT_DIR, "input_video_" + str(timestamp) + os.path.splitext(video_path)[1])
    safe_audio = os.path.join(OUTPUT_DIR, "input_audio_" + str(timestamp) + os.path.splitext(audio_path)[1])
    try:
        shutil.copy2(video_path, safe_video)
        shutil.copy2(audio_path, safe_audio)
    except Exception as e:
        raise gr.Error("\u590d\u5236\u8f93\u5165\u6587\u4ef6\u5931\u8d25: " + str(e))
    
    output_path = os.path.join(OUTPUT_DIR, "lipsync_" + str(timestamp) + ".mp4")
    setup_latentsync_env()
    progress(0.05, desc="\u51c6\u5907\u4e2d...")
    env = os.environ.copy()
    ls_env = os.path.join(LATENTSYNC_DIR, "latents_env")
    ffmpeg_path = os.path.join(LATENTSYNC_DIR, "ffmpeg-7.1", "bin")
    env["HF_HOME"] = os.path.join(LATENTSYNC_DIR, "huggingface")
    env["PYTHONPATH"] = LATENTSYNC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    env["PATH"] = ls_env + ";" + os.path.join(ls_env, "Library", "bin") + ";" + ffmpeg_path + ";" + env.get("PATH", "")
    env.pop("TRANSFORMERS_CACHE", None)
    env.pop("HUGGINGFACE_HUB_CACHE", None)
    env.pop("TRANSFORMERS_OFFLINE", None)
    env.pop("HF_HUB_OFFLINE", None)
    cmd = [LATENTSYNC_PYTHON, "-m", "scripts.inference",
           "--unet_config_path", LATENTSYNC_CONFIG, "--inference_ckpt_path", LATENTSYNC_CKPT,
           "--video_path", safe_video, "--audio_path", safe_audio, "--video_out_path", output_path,
           "--inference_steps", "20", "--guidance_scale", "1.5", "--seed", "1247"]
    print("[LatentSync] " + " ".join(cmd))
    progress(0.1, desc="\u6b63\u5728\u751f\u6210\u53e3\u578b\u540c\u6b65\u89c6\u9891...")
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, cwd=LATENTSYNC_DIR, env=env,
                                   encoding="utf-8", errors="replace", creationflags=flags)
        log_lines = []
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                log_lines.append(line)
                print("[LS] " + line)
                
                # 解析详细进度信息，格式如: "Doing inference...:  55%|██████    | 29/53"
                if "|" in line and "/" in line:
                    try:
                        # 提取阶段描述
                        stage_desc = "\u63a8\u7406\u4e2d"
                        if "preprocess" in line.lower() or "loading" in line.lower():
                            stage_desc = "\u9884\u5904\u7406"
                        elif "inference" in line.lower() or "doing inference" in line.lower():
                            stage_desc = "\u63a8\u7406\u4e2d"
                        elif "postprocess" in line.lower() or "saving" in line.lower():
                            stage_desc = "\u540e\u5904\u7406"
                        
                        # 提取百分比
                        percent_str = line.split("|")[0].split(":")[-1].strip().replace("%", "")
                        percent = int(percent_str)
                        
                        # 提取当前步数/总步数
                        steps_part = line.split("|")[-1].strip()
                        if "/" in steps_part:
                            current_step = steps_part.split("/")[0].strip()
                            total_steps = steps_part.split("/")[1].split()[0].strip()
                            
                            # 计算总进度（假设推理阶段占主要时间 30-90%）
                            total_progress = 0.3 + (percent / 100.0) * 0.6
                            
                            # 显示详细信息
                            desc = f"{stage_desc} {percent}% ({current_step}/{total_steps})"
                            progress(total_progress, desc=desc)
                    except Exception as e:
                        # 如果解析失败，尝试简单的百分比提取
                        if "%" in line:
                            try:
                                pct = float(line.split("%")[0].split()[-1])
                                progress(0.3 + (pct / 100.0) * 0.6, desc=f"\u5904\u7406\u4e2d {int(pct)}%")
                            except Exception:
                                pass
                # 检测其他阶段关键词
                elif "loading" in line.lower() or "preparing" in line.lower():
                    progress(0.15, desc="\u52a0\u8f7d\u6a21\u578b...")
                elif "saving" in line.lower() or "writing" in line.lower():
                    progress(0.92, desc="\u4fdd\u5b58\u89c6\u9891...")
        
        if process.wait() != 0:
            raise gr.Error("LatentSync \u5931\u8d25:\n" + "\n".join(log_lines[-10:]))
        if os.path.exists(output_path):
            progress(1.0, desc="\u5b8c\u6210")
            # 清理临时输入文件
            try:
                if os.path.exists(safe_video):
                    os.remove(safe_video)
                if os.path.exists(safe_audio):
                    os.remove(safe_audio)
            except Exception:
                pass
            return output_path, "\u2705 \u53e3\u578b\u540c\u6b65\u89c6\u9891\u751f\u6210\u5b8c\u6210\uff01"
        else:
            raise gr.Error("\u8f93\u51fa\u6587\u4ef6\u672a\u627e\u5230")
    except subprocess.SubprocessError as e:
        raise gr.Error("\u8fdb\u7a0b\u5931\u8d25: " + str(e))


def build_ui():
    custom_css = """
    .gradio-container {max-width: 100%!important}
    .step-box {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
        background: #f8f9fa;
    }
    .step-title {
        font-size: 1.2em;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
    }
    .step-number {
        background: #4CAF50;
        color: white;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 10px;
        font-weight: bold;
    }
    .video-container video {
        max-height: 400px;
        width: auto;
        margin: 0 auto;
        display: block;
    }
    """
    
    with gr.Blocks(css=custom_css, title="TTS + LipSync") as app:
        gr.Markdown("# 🎙️ 语音合成 + 👄 口型同步工作台")
        if tts:
            gr.Markdown("✅ 模型已加载 (v" + str(tts.model_version or "1.0") + ")")
        else:
            gr.Markdown("❌ 模型未加载")
        
        with gr.Row(equal_height=False):
            # 左侧：语音合成
            with gr.Column(scale=1):
                with gr.Group(elem_classes="step-box"):
                    gr.HTML('<div class="step-title"><span class="step-number">1</span>语音合成（可选）</div>')
                    gr.Markdown("💡 如果已有音频，可跳过此步骤，直接在右侧上传")
                    
                    input_text = gr.TextArea(
                        label="📝 输入文本",
                        placeholder="请输入要合成的文字内容...",
                        lines=4)
                    prompt_audio = gr.Audio(
                        label="🎤 音色参考音频",
                        sources=["upload", "microphone"],
                        type="filepath")
                    
                    with gr.Accordion("🎭 情感控制（高级选项）", open=False):
                        emo_mode = gr.Radio(
                            choices=["与音色参考音频相同", "使用情感参考音频", "使用情感向量控制"],
                            value="与音色参考音频相同",
                            label="情感控制方式")
                        emo_audio = gr.Audio(label="情感参考音频", type="filepath", visible=False)
                        emo_weight = gr.Slider(
                            label="情感权重",
                            minimum=0.0, maximum=1.0, value=0.65,
                            step=0.01, visible=False)
                        with gr.Group(visible=False) as vec_group:
                            gr.Markdown("**情感向量调节**")
                            with gr.Row():
                                vec1 = gr.Slider(label="😊 喜", minimum=0, maximum=1, value=0, step=0.05)
                                vec2 = gr.Slider(label="😠 怒", minimum=0, maximum=1, value=0, step=0.05)
                                vec3 = gr.Slider(label="😢 哀", minimum=0, maximum=1, value=0, step=0.05)
                                vec4 = gr.Slider(label="😨 惧", minimum=0, maximum=1, value=0, step=0.05)
                            with gr.Row():
                                vec5 = gr.Slider(label="🤢 厌恶", minimum=0, maximum=1, value=0, step=0.05)
                                vec6 = gr.Slider(label="😔 低落", minimum=0, maximum=1, value=0, step=0.05)
                                vec7 = gr.Slider(label="😲 惊喜", minimum=0, maximum=1, value=0, step=0.05)
                                vec8 = gr.Slider(label="😌 平静", minimum=0, maximum=1, value=0, step=0.05)
                    
                    gen_btn = gr.Button("🎵 生成语音", variant="primary", size="lg")
                    tts_status = gr.Markdown("")
                    output_audio = gr.Audio(label="🔊 生成的语音", interactive=False)
            
            # 右侧：口型同步
            with gr.Column(scale=1):
                with gr.Group(elem_classes="step-box"):
                    gr.HTML('<div class="step-title"><span class="step-number">2</span>上传视频和音频</div>')
                    
                    video_input = gr.Video(
                        label="🎬 上传原始视频",
                        sources=["upload"],
                        height=400,
                        show_label=True)
                    
                    with gr.Tabs():
                        with gr.Tab("📥 使用左侧生成的语音"):
                            audio_for_ls = gr.Audio(
                                label="自动使用左侧生成的语音",
                                type="filepath",
                                interactive=False)
                        with gr.Tab("📤 上传自定义音频"):
                            custom_audio = gr.Audio(
                                label="上传音频文件（支持 WAV/MP3）",
                                sources=["upload"],
                                type="filepath")
                
                with gr.Group(elem_classes="step-box"):
                    gr.HTML('<div class="step-title"><span class="step-number">3</span>生成口型同步视频</div>')
                    ls_btn = gr.Button("🎬 生成口型同步视频", variant="primary", size="lg")
                    ls_status = gr.Markdown("")
                    output_video = gr.Video(
                        label="✨ 生成的视频",
                        height=400,
                        show_label=True)
        def on_emo_change(mode):
            return (gr.update(visible=(mode == "\u4f7f\u7528\u60c5\u611f\u53c2\u8003\u97f3\u9891")),
                    gr.update(visible=(mode != "\u4e0e\u97f3\u8272\u53c2\u8003\u97f3\u9891\u76f8\u540c")),
                    gr.update(visible=(mode == "\u4f7f\u7528\u60c5\u611f\u5411\u91cf\u63a7\u5236")))
        emo_mode.change(on_emo_change, inputs=[emo_mode], outputs=[emo_audio, emo_weight, vec_group])
        gen_btn.click(generate_speech,
                      inputs=[input_text, prompt_audio, emo_mode, emo_audio, emo_weight, vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8],
                      outputs=[output_audio, tts_status, audio_for_ls])
        
        def run_lipsync_wrapper(video, auto_audio, custom_audio):
            # 优先使用自定义音频，如果没有则使用自动生成的音频
            audio_to_use = custom_audio if custom_audio else auto_audio
            return run_latentsync(video, audio_to_use)
        
        ls_btn.click(run_lipsync_wrapper,
                     inputs=[video_input, audio_for_ls, custom_audio],
                     outputs=[output_video, ls_status])
    return app


def open_app_window(port):
    edge_paths = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    edge = None
    for p in edge_paths:
        if os.path.exists(p):
            edge = p
            break
    if not edge:
        print("[WARN] Edge not found, opening default browser")
        import webbrowser
        webbrowser.open("http://localhost:" + str(port))
        return
    url = "http://localhost:" + str(port)
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        # 恢复 --app 模式
        subprocess.Popen([edge, "--app=" + url, "--window-size=1400,900"], creationflags=flags)
        print("[OK] Edge app window opened")
    except Exception as e:
        print("[WARN] Edge failed: " + str(e))
        import webbrowser
        webbrowser.open(url)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=GRADIO_PORT)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--no-window", action="store_true")
    args = parser.parse_args()
    print("=" * 50)
    print("  TTS + LipSync Workspace")
    print("=" * 50)
    auto_load_model()
    setup_latentsync_env()
    gradio_app = build_ui()
    gradio_app.queue(default_concurrency_limit=20, max_size=50)
    if args.no_window:
        gradio_app.launch(server_name="0.0.0.0", server_port=args.port, inbrowser=True, 
                         max_file_size="500mb", show_error=True)
    else:
        def start_gradio():
            gradio_app.launch(server_name=args.host, server_port=args.port, inbrowser=False, quiet=True,
                             max_file_size="500mb", show_error=True)
        gt = threading.Thread(target=start_gradio, daemon=True)
        gt.start()
        time.sleep(3)
        print("[OK] Gradio on http://localhost:" + str(args.port))
        open_app_window(args.port)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
