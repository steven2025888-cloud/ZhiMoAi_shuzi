# -*- coding: utf-8 -*-
import os, sys, time, subprocess, traceback, shutil, re, json

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR  = os.path.join(BASE_DIR, "IndexTTS2-SonicVale")
LATENTSYNC_DIR = os.path.join(BASE_DIR, "LatentSync")
OUTPUT_DIR    = os.path.join(BASE_DIR, "unified_outputs")
HISTORY_FILE  = os.path.join(OUTPUT_DIR, "history.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HF_CACHE_DIR = os.path.abspath(os.path.join(INDEXTTS_DIR, "checkpoints", "hf_cache"))
os.makedirs(HF_CACHE_DIR, exist_ok=True)
os.environ['HF_HUB_CACHE']          = HF_CACHE_DIR
os.environ['HF_HOME']               = HF_CACHE_DIR
os.environ['HUGGINGFACE_HUB_CACHE'] = HF_CACHE_DIR
os.environ['TRANSFORMERS_CACHE']    = HF_CACHE_DIR
os.environ['TRANSFORMERS_OFFLINE']  = '1'
os.environ['HF_HUB_OFFLINE']        = '1'

LATENTSYNC_PYTHON = os.path.join(LATENTSYNC_DIR, "latents_env", "python.exe")
LATENTSYNC_CKPT   = os.path.join(LATENTSYNC_DIR, "checkpoints", "latentsync_unet.pt")
LATENTSYNC_CONFIG = os.path.join(LATENTSYNC_DIR, "configs", "unet", "stage2.yaml")

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
APP_SUB  = "AI语音克隆 · 智能口型同步 · 专业级解决方案"


# ══════════════════════════════════════════════════════════════
#  安全 print（防 GBK 终端崩溃）
# ══════════════════════════════════════════════════════════════
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
#  页面 JS
# ══════════════════════════════════════════════════════════════
REMOVE_FOOTER_JS = """
() => {
    const S=['footer','.footer','.built-with','#footer','div[class*="footer"]',
        '.show-api','.api-docs','a[href*="gradio.app"]','a[href*="huggingface"]',
        'button[aria-label="Settings"]','.hamburger-menu','span.version'].join(',');
    const rm=()=>document.querySelectorAll(S).forEach(e=>{e.style.cssText='display:none!important';try{e.remove()}catch(_){}});
    rm(); new MutationObserver(rm).observe(document.documentElement,{childList:true,subtree:true});

    const PREF='zdai_pref';
    document.body.insertAdjacentHTML('beforeend',`
      <div id="zdai-cm" style="display:none;position:fixed;inset:0;z-index:99999;align-items:center;justify-content:center;">
        <div style="position:absolute;inset:0;background:rgba(15,23,42,.5);backdrop-filter:blur(4px)" onclick="window._zm.hide()"></div>
        <div style="position:relative;background:#fff;border-radius:18px;padding:32px 28px 24px;width:360px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.18)">
          <div style="font-size:36px;margin-bottom:8px">💡</div>
          <div style="font-size:17px;font-weight:800;color:#0f172a;margin-bottom:6px">关闭 织梦AI</div>
          <div style="font-size:13px;color:#64748b;margin-bottom:20px;line-height:1.6">最小化后程序在通知区域运行，不占用额外内存。</div>
          <div style="display:flex;gap:8px;margin-bottom:16px">
            <button onclick="window._zm.minimize()" style="flex:1;padding:11px;border-radius:9px;border:1px solid #e2e8f0;background:#f8fafc;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit">⊟ 最小化到通知区域</button>
            <button onclick="window._zm.exit()" style="flex:1;padding:11px;border-radius:9px;border:none;background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit">✕ 退出程序</button>
          </div>
          <label style="display:flex;align-items:center;justify-content:center;gap:6px;font-size:12px;color:#94a3b8;cursor:pointer">
            <input type="checkbox" id="zdai-na" style="accent-color:#6366f1"> <span>记住选择，不再提示</span>
          </label>
        </div>
      </div>`);

    window._zm={
        show(){const p=localStorage.getItem(PREF);if(p==='min'){this.minimize();return;}if(p==='exit'){this.exit();return;}document.getElementById('zdai-cm').style.display='flex';},
        hide(){document.getElementById('zdai-cm').style.display='none';},
        _save(v){if(document.getElementById('zdai-na')?.checked)localStorage.setItem(PREF,v);},
        minimize(){this._save('min');this.hide();try{window.pywebview.api.minimize_to_tray();}catch(_){}},
        exit(){this._save('exit');this.hide();try{window.pywebview.api.close_app();}catch(_){window.close();}}
    };

    if('Notification' in window && Notification.permission==='default') Notification.requestPermission();
    window._zdaiNotify=(t,b)=>{
        const go=()=>new Notification(t,{body:b});
        if(Notification.permission==='granted')go();
        else if(Notification.permission!=='denied')Notification.requestPermission().then(p=>{if(p==='granted')go();});
    };
}
"""

# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
CUSTOM_CSS = """
footer,.footer,.built-with,#footer,.show-api,.api-docs,
a[href*="gradio.app"],a[href*="huggingface"],
button[aria-label="Settings"],.hamburger-menu,span.version
{display:none!important;height:0!important;overflow:hidden!important;}
.topbar{background:#fff;border-bottom:1px solid #e2e8f0;padding:0 24px;height:54px;
 display:flex;align-items:center;justify-content:space-between;
 box-shadow:0 1px 4px rgba(0,0,0,.06);position:sticky;top:0;z-index:100;}
.topbar-brand{display:flex;align-items:center;gap:10px;}
.topbar-logo{width:34px;height:34px;border-radius:9px;
 background:linear-gradient(135deg,#6366f1,#8b5cf6);
 display:flex;align-items:center;justify-content:center;
 font-size:16px;font-weight:900;color:#fff;}
.topbar-name{font-size:16px;font-weight:800;color:#0f172a;}
.topbar-sub{font-size:11px;color:#94a3b8;}
.badge-ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;
 border-radius:20px;padding:3px 12px;font-size:11px;font-weight:600;}
.badge-err{background:#fff1f2;border:1px solid #fecdd3;color:#be123c;
 border-radius:20px;padding:3px 12px;font-size:11px;font-weight:600;}
.workspace{padding:14px 16px 18px!important;gap:12px!important;}
.panel{background:#fff!important;border:1px solid #e2e8f0!important;
 border-radius:12px!important;padding:16px 14px!important;
 box-shadow:0 1px 4px rgba(0,0,0,.05)!important;}
.panel-head{display:flex;align-items:center;gap:6px;
 font-size:13px;font-weight:700;color:#0f172a;
 border-bottom:1px solid #f1f5f9;padding-bottom:10px;margin-bottom:12px;}
.step-chip{width:22px;height:22px;border-radius:6px;
 background:linear-gradient(135deg,#6366f1,#8b5cf6);
 color:#fff;font-size:11px;font-weight:700;flex-shrink:0;
 display:inline-flex;align-items:center;justify-content:center;}
.divider{border:none;border-top:1px solid #f1f5f9;margin:10px 0;}
.status-ok{color:#15803d!important;font-size:12px!important;font-weight:500;}
.status-err{color:#dc2626!important;font-size:12px!important;font-weight:500;}
.op-log-wrap{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
 padding:8px 12px;min-height:48px;max-height:130px;overflow-y:auto;}
.op-log-item{display:flex;gap:8px;padding:4px 0;
 border-bottom:1px solid #f1f5f9;font-size:12px;color:#334155;line-height:1.5;}
.op-log-item:last-child{border-bottom:none;}
.op-log-time{color:#94a3b8;font-size:11px;flex-shrink:0;}
.op-log-ok{color:#16a34a;font-weight:700;flex-shrink:0;}
.op-log-err{color:#dc2626;font-weight:700;flex-shrink:0;}
input[type=range]{accent-color:#6366f1!important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:3px;}
"""


# ══════════════════════════════════════════════════════════════
#  模型加载
# ══════════════════════════════════════════════════════════════
def auto_load_model():
    global tts
    model_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
    if not os.path.exists(model_dir):
        safe_print("[ERR] model dir not found"); return
    original_cwd = os.getcwd()
    os.chdir(INDEXTTS_DIR)
    try:
        safe_print("[MODEL] Loading IndexTTS2...")
        from indextts.infer_v2 import IndexTTS2
        tts = IndexTTS2(model_dir=model_dir,
                        cfg_path=os.path.join(model_dir, "config.yaml"), use_fp16=True)
        safe_print("[MODEL] OK")
    except Exception as e:
        safe_print("[MODEL] FAIL: " + str(e)); traceback.print_exc()
    finally:
        os.chdir(original_cwd)


# ══════════════════════════════════════════════════════════════
#  语音合成
# ══════════════════════════════════════════════════════════════
def generate_speech(text, prompt_audio, top_p, top_k, temperature, num_beams, 
                   repetition_penalty, max_mel_tokens, progress=gr.Progress()):
    global tts
    if tts is None:    raise gr.Error("模型未加载，请等待初始化完成")
    if not text.strip(): raise gr.Error("请输入要合成的文本内容")
    if prompt_audio is None: raise gr.Error("请上传参考音频文件")

    ts = int(time.time())
    out = os.path.join(OUTPUT_DIR, f"tts_{ts}.wav")
    cwd = os.getcwd(); os.chdir(INDEXTTS_DIR)
    try:
        progress(0.1, desc="正在合成语音...")
        kw = dict(
            do_sample=True, 
            top_p=float(top_p), 
            top_k=int(top_k), 
            temperature=float(temperature),
            length_penalty=0.0, 
            num_beams=int(num_beams), 
            repetition_penalty=float(repetition_penalty), 
            max_mel_tokens=int(max_mel_tokens)
        )
        tts.infer(spk_audio_prompt=prompt_audio, text=text,
                  output_path=out, use_emo_text=False, **kw)
        os.chdir(cwd); progress(1.0, desc="合成完成")
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
        if   "preprocess" in low or "loading" in low: stage = "预处理"
        elif "inference"  in low:                     stage = "推理"
        elif "postprocess" in low or "saving" in low: stage = "后处理"
        else:                                          stage = "生成"
        mp = re.search(r'(\d+)%', line)
        ms = re.search(r'(\d+)/(\d+)', line)
        if not mp or not ms: return None
        return stage, int(mp.group(1)), int(ms.group(1)), int(ms.group(2))
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
    progress(0.2, desc="转换视频格式...")
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        p = subprocess.Popen(
            [ffmpeg, "-i", video_path, "-c:v", "libx264", "-preset", "ultrafast",
             "-crf", "23", "-c:a", "aac", "-b:a", "128k",
             "-movflags", "+faststart", "-pix_fmt", "yuv420p", "-y", out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        progress(0.6, desc="转换中...")
        p.communicate(timeout=120)
        progress(1.0, desc="视频就绪")
        return out if p.returncode == 0 and os.path.exists(out) else video_path
    except Exception:
        return video_path


# ══════════════════════════════════════════════════════════════
#  口型同步
# ══════════════════════════════════════════════════════════════
def run_latentsync(video_path, audio_path, progress=gr.Progress()):
    if not video_path:                      raise gr.Error("请上传人物视频")
    if not audio_path:                      raise gr.Error("请选择或上传音频文件")
    if not os.path.exists(video_path):      raise gr.Error("视频文件不存在，请重新上传")
    if not os.path.exists(audio_path):      raise gr.Error("音频文件不存在，请重新选择")

    ts   = int(time.time())
    sv   = os.path.join(OUTPUT_DIR, f"in_v_{ts}{os.path.splitext(video_path)[1]}")
    sa   = os.path.join(OUTPUT_DIR, f"in_a_{ts}{os.path.splitext(audio_path)[1]}")
    out  = os.path.join(OUTPUT_DIR, f"lipsync_{ts}.mp4")
    try:
        shutil.copy2(video_path, sv); shutil.copy2(audio_path, sa)
    except Exception as e:
        raise gr.Error("复制文件失败: " + str(e))

    progress(0.05, desc="初始化中...")
    env = os.environ.copy()
    ls_env = os.path.join(LATENTSYNC_DIR, "latents_env")
    fb     = os.path.join(LATENTSYNC_DIR, "ffmpeg-7.1", "bin")
    env["HF_HOME"]    = os.path.join(LATENTSYNC_DIR, "huggingface")
    env["PYTHONPATH"] = LATENTSYNC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    env["PATH"]       = ";".join([ls_env, os.path.join(ls_env, "Library", "bin"), fb, env.get("PATH", "")])
    for k in ("TRANSFORMERS_CACHE","HUGGINGFACE_HUB_CACHE","TRANSFORMERS_OFFLINE","HF_HUB_OFFLINE"):
        env.pop(k, None)

    cmd = [LATENTSYNC_PYTHON, "-m", "scripts.inference",
           "--unet_config_path", LATENTSYNC_CONFIG, "--inference_ckpt_path", LATENTSYNC_CKPT,
           "--video_path", sv, "--audio_path", sa, "--video_out_path", out,
           "--inference_steps", "20", "--guidance_scale", "1.5", "--seed", "1247"]

    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, cwd=LATENTSYNC_DIR, env=env,
                                encoding="utf-8", errors="replace", creationflags=flags, bufsize=1)
    except subprocess.SubprocessError as e:
        raise gr.Error("启动生成引擎失败: " + str(e))

    last = 0.05
    progress(0.08, desc="正在加载模型权重...")

    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None: break
        if not line: continue
        line = line.strip()
        if not line: continue
        safe_print("[LS] " + line)
        parsed = parse_progress_line(line)
        if not parsed: continue
        stage, pct, cur, total = parsed

        if stage == "预处理":
            prog = 0.08 + (pct / 100.0) * 0.04
            desc = f"预处理 {pct}%  ({cur}/{total})"
        elif stage in ("推理", "生成"):
            if pct >= 100:
                prog = 0.89; desc = "推理完成，正在合成视频..."
            else:
                prog = 0.12 + (pct / 100.0) * 0.76
                desc = f"生成帧画面  {pct}%  ({cur}/{total})"
        elif stage == "后处理":
            prog = 0.90 + (pct / 100.0) * 0.06
            desc = f"后处理 {pct}%  ({cur}/{total})"
        else:
            prog = last; desc = f"{stage} {pct}%  ({cur}/{total})"

        prog = max(prog, last); last = prog
        progress(prog, desc=desc)

    if last < 0.93:
        progress(0.94, desc="正在写入视频文件...")

    if proc.wait() != 0:
        raise gr.Error("口型同步生成失败，请检查视频/音频格式是否正确")
    if not os.path.exists(out):
        raise gr.Error("输出视频文件未找到，请重试")

    progress(1.0, desc="✅ 生成完成")
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
    return out, "✅ 口型同步完成"


# ══════════════════════════════════════════════════════════════
#  构建 UI
# ══════════════════════════════════════════════════════════════
def build_ui():
    badge = ('<span class="badge-ok">● 模型已就绪</span>' if tts
             else '<span class="badge-err">● 模型加载失败</span>')

    with gr.Blocks(
        title=APP_NAME,
        css=CUSTOM_CSS,
        js=REMOVE_FOOTER_JS,
        theme=gr.themes.Base(),
    ) as app:

        # ── 顶部导航栏 ──────────────────────────────────────
        gr.HTML(f"""
        <div class="topbar">
          <div class="topbar-brand">
            <div class="topbar-logo">织</div>
            <div>
              <div class="topbar-name">{APP_NAME}</div>
              <div class="topbar-sub">{APP_SUB}</div>
            </div>
          </div>
          <div>{badge}</div>
        </div>
        """)

        # ── 三列工作区 ───────────────────────────────────────
        with gr.Row(elem_classes="workspace", equal_height=True):

            # ── 列 1：语音合成 ──────────────────────────────
            with gr.Column(scale=1, elem_classes="panel"):
                gr.HTML('<div class="panel-head"><span class="step-chip">1</span>语音合成</div>')
                input_text = gr.TextArea(
                    label="输入文本",
                    placeholder="在此粘贴或输入需要合成的文字内容...",
                    lines=4,
                )
                prompt_audio = gr.Audio(
                    label="参考音频（3-10 秒，用于克隆音色）",
                    sources=["upload"], type="filepath",
                )
                
                # 高级设置（可折叠）
                with gr.Accordion("⚙️ 高级设置", open=False):
                    with gr.Row():
                        top_p = gr.Slider(
                            label="Top-P (采样概率阈值)",
                            minimum=0.1, maximum=1.0, value=0.8, step=0.05,
                            info="控制生成多样性，越高越随机"
                        )
                        top_k = gr.Slider(
                            label="Top-K (候选词数量)",
                            minimum=1, maximum=100, value=30, step=1,
                            info="限制候选词数量"
                        )
                    with gr.Row():
                        temperature = gr.Slider(
                            label="Temperature (温度)",
                            minimum=0.1, maximum=2.0, value=0.8, step=0.1,
                            info="控制随机性，越高越随机"
                        )
                        num_beams = gr.Slider(
                            label="Beam Search (束搜索)",
                            minimum=1, maximum=10, value=3, step=1,
                            info="束搜索数量，越大质量越好但速度越慢"
                        )
                    with gr.Row():
                        repetition_penalty = gr.Slider(
                            label="Repetition Penalty (重复惩罚)",
                            minimum=1.0, maximum=20.0, value=10.0, step=0.5,
                            info="防止重复，越大越不容易重复"
                        )
                        max_mel_tokens = gr.Slider(
                            label="Max Mel Tokens (最大长度)",
                            minimum=500, maximum=3000, value=1500, step=100,
                            info="生成音频的最大长度"
                        )
                
                gen_btn    = gr.Button("🎵  开始语音合成", variant="primary")
                tts_status = gr.Markdown("", elem_classes="status-ok")
                output_audio = gr.Audio(label="合成结果", interactive=False)

            # ── 列 2：口型同步 ──────────────────────────────
            with gr.Column(scale=1, elem_classes="panel"):
                gr.HTML('<div class="panel-head"><span class="step-chip">2</span>口型同步</div>')
                video_input = gr.Video(
                    label="上传人物视频（上传后自动转换格式）",
                    sources=["upload"], height=220,
                )
                video_status = gr.Markdown("", elem_classes="status-ok")
                gr.HTML('<div class="divider"></div>')
                with gr.Tabs():
                    with gr.Tab("使用已合成的语音"):
                        audio_for_ls = gr.Audio(
                            label="自动引用第一步合成结果",
                            type="filepath", interactive=False,
                        )
                    with gr.Tab("上传自定义音频"):
                        custom_audio = gr.Audio(
                            label="上传音频文件",
                            sources=["upload"], type="filepath",
                        )
                ls_btn    = gr.Button("🚀  生成口型同步视频", variant="primary")
                ls_status = gr.Markdown("", elem_classes="status-ok")

            # ── 列 3：生成结果 ──────────────────────────────
            with gr.Column(scale=1, elem_classes="panel"):
                gr.HTML('<div class="panel-head"><span class="step-chip">3</span>生成结果</div>')
                with gr.Group(elem_classes="compact-video"):
                    output_video = gr.Video(label="最终合成视频", height=460)

        # ── 底部：操作日志 + 历史记录 ────────────────────────
        with gr.Row(elem_classes="workspace"):
            with gr.Column(scale=1, elem_classes="panel"):
                gr.HTML('<div class="panel-head"><span class="step-chip">📋</span>操作日志</div>')
                op_log = gr.HTML(
                    value='<div class="op-log-wrap"><div class="op-log-item"><span class="op-log-ok">●</span><span class="op-log-msg">系统就绪，等待操作...</span></div></div>'
                )
            with gr.Column(scale=2, elem_classes="panel"):
                gr.HTML('<div class="panel-head"><span class="step-chip">📁</span>合成历史记录</div>')
                with gr.Row():
                    refresh_hist_btn = gr.Button("🔄 刷新", variant="secondary", scale=1, min_width=90)
                    open_folder_btn  = gr.Button("📂 打开文件夹", variant="secondary", scale=1, min_width=120)
                hist_dropdown = gr.Dropdown(
                    label="历史合成视频（点击选择直接播放）",
                    choices=[], value=None, interactive=True,
                )
                hist_video = gr.Video(label="视频预览", height=260, interactive=False)

        # ── 事件绑定 ─────────────────────────────────────────
        _log = []

        def _log_add(ok, msg):
            import time as _t
            _log.append({"ok":ok,"t":_t.strftime("%H:%M:%S"),"msg":msg})
            rows=""
            for e in list(reversed(_log))[:6]:
                ic='<span class="op-log-ok">✓</span>' if e["ok"] else '<span class="op-log-err">✗</span>'
                rows+=f'<div class="op-log-item">{ic}<span class="op-log-time">{e["t"]}</span><span class="op-log-msg">{e["msg"]}</span></div>'
            return f'<div class="op-log-wrap">{rows}</div>'

        def _hist_choices():
            if not os.path.exists(HISTORY_FILE): return []
            try:
                with open(HISTORY_FILE,'r',encoding='utf-8') as f: h=json.load(f)
                return [(f'{"✅" if os.path.exists(i["video_path"]) else "❌"}  {i["time"]}  {os.path.basename(i["video_path"])}  ({i["size_mb"]}MB)',i["video_path"]) for i in h]
            except: return []

        def tts_wrap(text, pa, tp, tk, temp, nb, rp, mmt):
            r = generate_speech(text, pa, tp, tk, temp, nb, rp, mmt)
            return r[0], _log_add(True,"语音合成完成 — "+os.path.basename(r[0])), r[2]

        gen_btn.click(tts_wrap,
            inputs=[input_text,prompt_audio,top_p,top_k,temperature,num_beams,repetition_penalty,max_mel_tokens],
            outputs=[output_audio,op_log,audio_for_ls])

        def auto_convert(video, progress=gr.Progress()):
            if not video: return None, _log_add(False,"未选择视频")
            converted = convert_video_for_browser(video, progress)
            if converted and converted != video and os.path.exists(converted):
                return converted, _log_add(True,"视频就绪 — "+os.path.basename(converted))
            return video, _log_add(True,"视频上传完成")

        video_input.upload(auto_convert,
            inputs=[video_input], outputs=[video_input,op_log])

        def ls_wrap(video, auto_a, custom_a):
            out, _ = run_latentsync(video, custom_a if custom_a else auto_a)
            return out, _log_add(True,"口型同步完成 — "+os.path.basename(out)), gr.update(choices=_hist_choices())

        ls_btn.click(ls_wrap,
            inputs=[video_input,audio_for_ls,custom_audio],
            outputs=[output_video,op_log,hist_dropdown])

        refresh_hist_btn.click(lambda: gr.update(choices=_hist_choices(),value=None), outputs=[hist_dropdown])
        open_folder_btn.click(lambda: (subprocess.Popen(["explorer",OUTPUT_DIR],creationflags=subprocess.CREATE_NO_WINDOW) if sys.platform=="win32" else None) or _log_add(True,"已打开文件夹"), outputs=[op_log])
        hist_dropdown.change(lambda p: p if p and os.path.exists(p) else None, inputs=[hist_dropdown], outputs=[hist_video])

    return app


# ══════════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
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
            )
            break
        except OSError:
            continue