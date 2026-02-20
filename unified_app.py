# -*- coding: utf-8 -*-
import os, sys, time, subprocess, traceback, shutil, re, json, queue as _queue, threading

# ── 清除代理 ──
for _k in ('http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','all_proxy'):
    os.environ.pop(_k, None)
    os.environ[_k] = ''
os.environ['no_proxy'] = '127.0.0.1,localhost'
os.environ['NO_PROXY'] = '127.0.0.1,localhost'

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR   = os.path.join(BASE_DIR, "IndexTTS2-SonicVale")
LATENTSYNC_DIR = os.path.join(BASE_DIR, "LatentSync")
OUTPUT_DIR     = os.path.join(BASE_DIR, "unified_outputs")
HISTORY_FILE   = os.path.join(OUTPUT_DIR, "history.json")
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
INIT_JS = r"""
() => {
    /* ── 1. 禁用 SharedArrayBuffer 让 Gradio 自动降级到服务端处理 ── */
    try {
        Object.defineProperty(window,'SharedArrayBuffer',{get:()=>undefined,configurable:true});

        // 静默处理 FFmpeg 加载错误，不阻止请求但捕获错误
        window.addEventListener('unhandledrejection', function(event) {
            if (event.reason && event.reason.message &&
                (event.reason.message.includes('ffmpeg') ||
                 event.reason.message.includes('SharedArrayBuffer'))) {
                console.log('[织梦AI] FFmpeg WASM 已禁用，使用服务端处理');
                event.preventDefault(); // 阻止错误显示
            }
        });
    } catch(_){}

    /* ── 2. 隐藏 Gradio 页脚和无关按钮 ── */
    const _rmSel = [
        'footer','.footer','.built-with','#footer','div[class*="footer"]',
        '.show-api','.api-docs','a[href*="gradio.app"]','a[href*="huggingface"]',
        'button[aria-label="Settings"]','.hamburger-menu','span.version'
    ].join(',');
    const _rm = () => document.querySelectorAll(_rmSel).forEach(e => {
        e.style.cssText = 'display:none!important'; try { e.remove(); } catch(_){}
    });
    _rm();
    new MutationObserver(_rm).observe(document.documentElement, {childList:true, subtree:true});

    /* ── 3. 关闭确认对话框 ── */
    const PREF = 'zdai_pref';
    document.body.insertAdjacentHTML('beforeend', `
      <div id="zdai-cm" style="display:none;position:fixed;inset:0;z-index:99999;align-items:center;justify-content:center;">
        <div style="position:absolute;inset:0;background:rgba(15,23,42,.6);backdrop-filter:blur(6px)" onclick="window._zm.hide()"></div>
        <div style="position:relative;background:#fff;border-radius:20px;padding:36px 32px 28px;width:380px;text-align:center;box-shadow:0 24px 64px rgba(0,0,0,.22)">
          <div style="width:56px;height:56px;border-radius:14px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:26px;">🖥</div>
          <div style="font-size:18px;font-weight:800;color:#0f172a;margin-bottom:8px">关闭 织梦AI</div>
          <div style="font-size:13px;color:#64748b;margin-bottom:24px;line-height:1.7">最小化到通知区域后程序继续运行，<br>不会中断正在进行的任务。</div>
          <div style="display:flex;gap:10px;margin-bottom:18px">
            <button onclick="window._zm.minimize()" style="flex:1;padding:12px;border-radius:10px;border:1.5px solid #e2e8f0;background:#f8fafc;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;color:#374151;transition:all .15s">⊟ 最小化到通知区域</button>
            <button onclick="window._zm.exit()" style="flex:1;padding:12px;border-radius:10px;border:none;background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .15s">✕ 退出程序</button>
          </div>
          <label style="display:flex;align-items:center;justify-content:center;gap:6px;font-size:12px;color:#94a3b8;cursor:pointer">
            <input type="checkbox" id="zdai-na" style="accent-color:#6366f1"> <span>记住选择，不再提示</span>
          </label>
        </div>
      </div>

      <!-- ── 底部日志面板（默认收起，仅显示最新一条）── -->
      <div id="zdai-log-bar" style="
          position:fixed;bottom:0;left:0;right:0;z-index:9000;
          background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
          border-top:2px solid #6366f1;
          box-shadow:0 -4px 32px rgba(0,0,0,.4);
          font-family:'Microsoft YaHei',system-ui,sans-serif;
          transition:height .2s cubic-bezier(.4,0,.2,1);
          height:44px;overflow:hidden;">

        <!-- 标题栏（始终可见）-->
        <div id="zdai-log-hd" onclick="window._zdaiLogToggle()" style="
            height:44px;display:flex;align-items:center;gap:10px;
            padding:0 18px;cursor:pointer;user-select:none;">
          <span style="width:22px;height:22px;border-radius:6px;flex-shrink:0;
              background:linear-gradient(135deg,#6366f1,#8b5cf6);
              display:inline-flex;align-items:center;justify-content:center;
              font-size:12px;">📋</span>
          <span style="font-size:13px;font-weight:700;color:#e2e8f0;flex-shrink:0;">操作日志</span>
          <span id="zdai-log-badge" style="
              background:#6366f1;color:#fff;border-radius:20px;
              padding:0 8px;font-size:11px;font-weight:700;
              min-width:20px;text-align:center;line-height:18px;height:18px;
              display:inline-flex;align-items:center;flex-shrink:0;">0</span>
          <!-- 最新一条日志预览 -->
          <span id="zdai-log-preview" style="
              font-size:12px;color:#94a3b8;flex:1;
              overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></span>
          <span id="zdai-log-arrow" style="color:#6366f1;font-size:12px;
              transition:transform .2s;flex-shrink:0;margin-left:4px;">▲</span>
          <span id="zdai-log-btn" style="
              color:#6366f1;font-size:11px;font-weight:600;
              padding:3px 10px;border:1px solid #6366f1;border-radius:20px;
              flex-shrink:0;margin-left:2px;letter-spacing:.3px;">展开</span>
        </div>

        <!-- 日志内容区 -->
        <div id="zdai-log-body" style="
            height:180px;overflow-y:auto;padding:8px 16px 12px;
            border-top:1px solid rgba(99,102,241,.25);"></div>
      </div>`);

    /* ── 4. 折叠逻辑 ── */
    var _logOpen = false;   /* 默认收起 */
    window._zdaiLogToggle = function() {
        _logOpen = !_logOpen;
        var bar   = document.getElementById('zdai-log-bar');
        var arrow = document.getElementById('zdai-log-arrow');
        var btn   = document.getElementById('zdai-log-btn');
        if (bar)   bar.style.height       = _logOpen ? '224px' : '44px';
        if (arrow) arrow.style.transform  = _logOpen ? 'rotate(180deg)' : '';
        if (btn)   btn.textContent        = _logOpen ? '收起' : '展开';
    };

    /* ── 5. 日志同步：轮询 Gradio 渲染的隐藏元素 #zdai-log-src ── */
    var _lastLogHtml = '';
    function _syncLog() {
        var src = document.getElementById('zdai-log-src');
        if (src) {
            var inner = src.querySelector('#zdai-log-inner');
            var html  = inner ? inner.innerHTML : src.innerHTML;
            if (html && html !== _lastLogHtml) {
                _lastLogHtml = html;
                var body    = document.getElementById('zdai-log-body');
                var badge   = document.getElementById('zdai-log-badge');
                var preview = document.getElementById('zdai-log-preview');
                if (body) {
                    body.innerHTML = html;
                    body.scrollTop = body.scrollHeight;
                }
                if (badge) {
                    var cnt = (html.match(/class="log-entry"/g) || []).length;
                    badge.textContent = cnt;
                }
                /* 最新一条预览（取最后一个 log-entry 的文本） */
                if (preview && inner) {
                    var entries = inner.querySelectorAll('.log-entry');
                    if (entries.length > 0) {
                        var last = entries[entries.length - 1];
                        var txt  = last.textContent || last.innerText || '';
                        preview.textContent = txt.trim();
                    }
                }
                /* 有新日志时若已展开则保持，若收起不自动展开（用户可看预览）*/
            }
        }
        setTimeout(_syncLog, 600);
    }
    setTimeout(_syncLog, 1800);

    /* ── 6. 进度浮层（口型同步期间显示生成进度）── */
    document.body.insertAdjacentHTML('beforeend', `
      <div id="zdai-prog" style="
          display:none;position:fixed;
          bottom:54px;right:20px;z-index:8900;
          background:linear-gradient(135deg,#1e293b,#0f172a);
          border:1.5px solid #6366f1;border-radius:14px;
          padding:14px 18px;min-width:260px;
          box-shadow:0 8px 32px rgba(0,0,0,.4);
          font-family:'Microsoft YaHei',system-ui,sans-serif;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
          <div style="width:8px;height:8px;border-radius:50%;background:#6366f1;
              animation:zdai-pulse 1.2s infinite;flex-shrink:0;"></div>
          <span id="zdai-prog-stage" style="font-size:12px;font-weight:700;color:#e2e8f0;">正在处理</span>
          <span id="zdai-prog-pct" style="font-size:12px;color:#6366f1;font-weight:700;margin-left:auto;">0%</span>
        </div>
        <div style="background:rgba(99,102,241,.15);border-radius:6px;height:6px;overflow:hidden;">
          <div id="zdai-prog-bar" style="height:100%;width:0%;border-radius:6px;
              background:linear-gradient(90deg,#6366f1,#8b5cf6);
              transition:width .4s ease;"></div>
        </div>
        <div id="zdai-prog-detail" style="font-size:11px;color:#64748b;margin-top:6px;"></div>
      </div>
      <style>
        @keyframes zdai-pulse {
          0%,100%{opacity:1;transform:scale(1)}
          50%{opacity:.5;transform:scale(.8)}
        }
      </style>`);

    window._zdaiSetProg = function(pct, stage, detail) {
        var el = document.getElementById('zdai-prog');
        if (!el) return;
        if (pct === null) { el.style.display = 'none'; return; }
        el.style.display = 'block';
        var bar  = document.getElementById('zdai-prog-bar');
        var pctEl= document.getElementById('zdai-prog-pct');
        var stEl = document.getElementById('zdai-prog-stage');
        var dtEl = document.getElementById('zdai-prog-detail');
        if (bar)   bar.style.width    = pct + '%';
        if (pctEl) pctEl.textContent  = pct + '%';
        if (stEl)  stEl.textContent   = stage || '处理中';
        if (dtEl)  dtEl.textContent   = detail || '';
    };

    /* ── 7. 系统通知 ── */
    window._zdaiNotify = (t, b) => {
        try { if (window.pywebview?.api) window.pywebview.api.send_notification(t, b); } catch(_){}
    };

    /* ── 8. 关闭/最小化逻辑 ── */
    window._zm = {
        show() {
            const p = localStorage.getItem(PREF);
            if (p === 'min')  { this.minimize(); return; }
            if (p === 'exit') { this.exit();     return; }
            document.getElementById('zdai-cm').style.display = 'flex';
        },
        hide() { document.getElementById('zdai-cm').style.display = 'none'; },
        _save(v) {
            if (document.getElementById('zdai-na')?.checked)
                localStorage.setItem(PREF, v);
        },
        minimize() {
            this._save('min'); this.hide();
            setTimeout(() => {
                const api = window.pywebview?.api;
                if (api && typeof api.minimize_to_tray === 'function') {
                    Promise.resolve(api.minimize_to_tray())
                        .then(() => console.log('[织梦AI] 最小化完成'))
                        .catch(e => console.error('[织梦AI] 最小化失败:', e));
                } else {
                    console.warn('[织梦AI] pywebview.api 不可用，等待重试...');
                    setTimeout(() => {
                        if (window.pywebview?.api?.minimize_to_tray)
                            window.pywebview.api.minimize_to_tray();
                    }, 1000);
                }
            }, 200);
        },
        exit() {
            this._save('exit'); this.hide();
            document.body.insertAdjacentHTML('beforeend',
                '<div style="position:fixed;inset:0;background:rgba(15,23,42,.95);z-index:999999;' +
                'display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;' +
                'color:#fff;font-family:Microsoft YaHei,sans-serif;">' +
                '<div style="font-size:32px;">🌙</div>' +
                '<div style="font-size:16px;font-weight:700;">正在退出织梦AI...</div>' +
                '<div style="font-size:12px;color:#64748b;">正在保存数据并关闭服务</div></div>');
            setTimeout(() => {
                const api = window.pywebview?.api;
                if (api && typeof api.close_app === 'function') {
                    Promise.resolve(api.close_app()).catch(() => {});
                }
            }, 100);
        }
    };
}
"""

# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
CUSTOM_CSS = """
/* ── 全局重置 ── */
footer,.footer,.built-with,#footer,.show-api,.api-docs,
a[href*="gradio.app"],a[href*="huggingface"],
button[aria-label="Settings"],.hamburger-menu,span.version
{display:none!important;height:0!important;overflow:hidden!important;}

/* ── 全局背景 & 容器 ── */
body, .gradio-container { background:#f1f5f9!important; }
.gradio-container {
  padding-bottom:54px!important;
  min-height:0!important;
  overflow-x:hidden!important;
}

/* ── 顶栏 ── */
.topbar {
  background:#fff;
  border-bottom:1px solid #e2e8f0;
  padding:0 24px;height:56px;
  display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 1px 6px rgba(0,0,0,.06);
  position:sticky;top:0;z-index:100;
}
.topbar-brand { display:flex;align-items:center;gap:12px; }
.topbar-logo  {
  width:36px;height:36px;border-radius:10px;
  background:linear-gradient(135deg,#6366f1,#8b5cf6);
  display:flex;align-items:center;justify-content:center;
  font-size:18px;font-weight:900;color:#fff;
  box-shadow:0 2px 8px rgba(99,102,241,.35);
}
.topbar-name  { font-size:16px;font-weight:800;color:#0f172a;letter-spacing:.3px; }
.topbar-sub   { font-size:11px;color:#94a3b8;margin-top:1px; }

/* ── 状态徽章 ── */
.badge-ok  {
  background:linear-gradient(135deg,#f0fdf4,#dcfce7);
  border:1px solid #bbf7d0;color:#15803d;
  border-radius:20px;padding:4px 14px;font-size:11px;font-weight:700;
  box-shadow:0 1px 3px rgba(0,0,0,.05);
}
.badge-err {
  background:linear-gradient(135deg,#fff1f2,#ffe4e6);
  border:1px solid #fecdd3;color:#be123c;
  border-radius:20px;padding:4px 14px;font-size:11px;font-weight:700;
}

/* ── 工作区 ── */
.workspace { padding:12px!important; gap:12px!important; }

/* ── 面板 ── */
.panel {
  background:#fff!important;
  border:1px solid #e2e8f0!important;
  border-radius:14px!important;
  padding:14px 14px!important;
  box-shadow:0 2px 8px rgba(0,0,0,.05)!important;
  transition:box-shadow .2s!important;
}
.panel:hover { box-shadow:0 4px 16px rgba(0,0,0,.09)!important; }

/* ── 面板标题（编号 chip 与标题同行显示）── */
.panel-head {
  display:flex;align-items:center;gap:8px;
  font-size:14px;font-weight:800;color:#0f172a;
  border-bottom:2px solid #f1f5f9;
  padding-bottom:10px;margin-bottom:12px;
  line-height:1.3;
}
.step-chip {
  width:24px;height:24px;border-radius:7px;flex-shrink:0;
  background:linear-gradient(135deg,#6366f1,#8b5cf6);
  color:#fff;font-size:12px;font-weight:800;
  display:inline-flex;align-items:center;justify-content:center;
  box-shadow:0 2px 6px rgba(99,102,241,.4);
}

/* ── 分割线 ── */
.divider { border:none;border-top:1px solid #f1f5f9;margin:10px 0; }

/* ── 状态文字 ── */
.status-ok  { color:#15803d!important;font-size:12px!important;font-weight:600!important; }
.status-err { color:#dc2626!important;font-size:12px!important;font-weight:600!important; }

/* ── 控件美化 ── */
input[type=range] { accent-color:#6366f1!important; }
button.primary    { box-shadow:0 2px 8px rgba(99,102,241,.3)!important; }

/* ── 滚动条 ── */
::-webkit-scrollbar { width:4px;height:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#cbd5e1;border-radius:4px; }
::-webkit-scrollbar-thumb:hover { background:#94a3b8; }

/* ── Gradio flex 高度修复 ── */
.stretch > div > .column > *,
.stretch > div > .column > .form > * { flex-grow:0!important; }
.stretch.svelte-1xp0cw7>.column>*,
.stretch.svelte-1xp0cw7>.column>.form>* { flex-grow:0!important;flex-shrink:0; }

/* ── 生成结果列：让视频自然撑满，不被裁剪 ── */
#output-video-col {
  overflow:visible!important;
}
/* 视频组件本体，限制最大高度避免溢出到日志栏 */
#output-video video {
  max-height:calc(100vh - 240px)!important;
  width:100%!important;
  object-fit:contain!important;
  border-radius:8px!important;
  background:#0f172a!important;
  display:block!important;
}
/* 进度详情卡片 */
#ls-detail-box {
  margin-bottom:8px;
}

/* ── 历史视频 ── */
.hist-tab video { max-height:360px; }

/* ── 进度描述支持换行（步骤信息独占一行）── */
.progress-description, [class*="progress"] p,
.progress-text, tqdm { white-space:pre-wrap!important; }

/* ── 清空历史弹窗：position:fixed 全屏居中遮罩 ── */
#clear-confirm-overlay {
  position:fixed!important;
  top:0!important; left:0!important;
  width:100vw!important; height:100vh!important;
  z-index:9990!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  background:rgba(15,23,42,0.70)!important;
  backdrop-filter:blur(8px)!important;
  padding:0!important; margin:0!important;
  border:none!important; border-radius:0!important;
  box-shadow:none!important;
}
#clear-confirm-overlay > div.form {
  background:#fff!important;
  border-radius:20px!important;
  padding:36px 32px 28px!important;
  max-width:460px!important;
  width:90%!important;
  box-shadow:0 24px 64px rgba(0,0,0,.3)!important;
  border:none!important;
}

/* ── 日志数据源（视觉隐藏，DOM中存在）── */
#zdai-log-src {
  position:fixed;left:-9999px;top:-9999px;
  width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none;
}

/* ── 日志条目（底部面板里渲染）── */
.log-entry {
  font-size:12px;color:#cbd5e1;line-height:1.7;
  padding:4px 0;border-bottom:1px solid rgba(100,116,139,.12);
  display:flex;align-items:baseline;gap:5px;
  font-family:'Microsoft YaHei',system-ui,sans-serif;
}
.log-entry:last-child { border-bottom:none; }
.log-ok   { color:#4ade80;font-weight:700;flex-shrink:0; }
.log-err  { color:#f87171;font-weight:700;flex-shrink:0; }
.log-time { color:#64748b;font-size:11px;margin-right:3px;flex-shrink:0; }

/* ── Tab 标签美化 ── */
.tabs > .tabitem { border:none!important; }
/* ══ 批量任务 ══ */
.bt-form, .bt-queue {
  background:#fff!important;border:1px solid #e2e8f0!important;
  border-radius:14px!important;padding:16px 14px!important;
  box-shadow:0 2px 8px rgba(0,0,0,.05)!important;
}
.bt-step-row {
  display:flex;align-items:center;gap:8px;
  margin:12px 0 6px;padding-top:10px;border-top:1px solid #f1f5f9;
}
.bt-step-label { font-size:13px;font-weight:700;color:#0f172a; }
.bt-section-title { font-size:12px;font-weight:700;color:#6366f1;margin-bottom:6px; }
.bt-radio .wrap { flex-direction:row!important;flex-wrap:wrap!important;gap:6px!important; }
.bt-radio label {
  flex:1!important;text-align:center!important;font-size:12px!important;font-weight:600!important;
  padding:6px 10px!important;border-radius:8px!important;border:1.5px solid #e2e8f0!important;
  cursor:pointer!important;transition:all .15s!important;background:#fafafa!important;min-width:80px!important;
}
.bt-radio label:has(input:checked) {
  border-color:#6366f1!important;background:#ede9fe!important;color:#4c1d95!important;
}
.bt-badge { border-radius:20px;padding:2px 9px;font-size:11px;font-weight:700;display:inline-block;white-space:nowrap; }
.bt-badge-tts    { background:#ede9fe;color:#6d28d9; }
.bt-badge-audio  { background:#e0f2fe;color:#0369a1; }
.bt-badge-shared { background:#fce7f3;color:#9d174d; }
.bt-badge-own    { background:#f0fdf4;color:#166534; }
#bt-progress-box { margin-top:10px; }
#bt-task-list    { min-height:60px;margin-top:4px; }
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
        progress(0.1, desc="正在合成语音...")
        kw = dict(
            do_sample=True, top_p=float(top_p), top_k=int(top_k),
            temperature=float(temperature), length_penalty=0.0,
            num_beams=int(num_beams), repetition_penalty=float(repetition_penalty),
            max_mel_tokens=int(max_mel_tokens)
        )
        emo_ref_path, vec, use_emo_text = None, None, False
        if emo_mode == "使用情感参考音频":
            emo_ref_path = emo_audio
        elif emo_mode == "使用情感向量控制":
            vec = tts.normalize_emo_vec([vec1,vec2,vec3,vec4,vec5,vec6,vec7,vec8], apply_bias=True)
        elif emo_mode == "使用情感描述文本控制":
            use_emo_text = True

        progress(0.3, desc="生成音频中...")
        final_emo_text = None
        if emo_text and isinstance(emo_text, str) and emo_text.strip():
            final_emo_text = emo_text.strip()

        tts.infer(
            spk_audio_prompt=prompt_audio, text=text, output_path=out,
            emo_audio_prompt=emo_ref_path, emo_alpha=float(emo_weight),
            emo_vector=vec, use_emo_text=use_emo_text, emo_text=final_emo_text,
            use_random=False, **kw
        )
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
#  口型同步（带进度更新）
# ══════════════════════════════════════════════════════════════
def run_latentsync(video_path, audio_path, progress=gr.Progress(), detail_cb=None, output_path_override=None):
    if not video_path:                 raise gr.Error("请上传人物视频")
    if not audio_path:                 raise gr.Error("请选择或上传音频文件")
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

    # 保存两层进度信息
    step_progress = None  # 步骤进度 (3/4)
    frame_progress = None  # 帧进度 (13/21)

    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None: break
        if not line: continue
        line = line.strip()
        if not line: continue
        safe_print("[LS] " + line)
        parsed = parse_progress_line(line)
        if not parsed: continue
        stage, pct, cur, total, progress_type = parsed

        # 根据类型保存进度
        if progress_type == "step":
            step_progress = (pct, cur, total)
        elif progress_type == "frame":
            frame_progress = (pct, cur, total)

        if stage == "预处理":
            prog = 0.08 + (pct / 100.0) * 0.04
            desc = f"预处理 {pct}%  ({cur}/{total})"
        elif stage in ("推理", "生成"):
            if pct >= 100:
                prog = 0.89; desc = "推理完成，正在合成视频..."
            else:
                # 计算总体进度（使用帧进度优先）
                if frame_progress:
                    prog = 0.12 + (frame_progress[0] / 100.0) * 0.76
                    f_pct, f_cur, f_total = frame_progress
                    # 显示帧进度和步骤进度（用空格分隔，模拟两行效果）
                    if step_progress:
                        s_pct, s_cur, s_total = step_progress
                        desc = f"帧 {f_pct}%({f_cur}/{f_total})  步骤 {s_pct}%({s_cur}/{s_total})  总 {prog*100:.1f}%"
                        if detail_cb:
                            detail_cb(_make_detail_html(f_pct, f_cur, f_total, s_pct, s_cur, s_total, prog))
                    else:
                        desc = f"帧画面 {f_pct}%（{f_cur}/{f_total}）  总进度 {prog*100:.1f}%"
                else:
                    prog = 0.12 + (pct / 100.0) * 0.76
                    desc = f"帧画面 {pct}%（{cur}/{total}）  总进度 {prog*100:.1f}%"
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
#  构建 UI
# ══════════════════════════════════════════════════════════════
def build_ui():
    badge = ('<span class="badge-ok">● 模型已就绪</span>' if tts
             else '<span class="badge-err">● 模型加载失败</span>')

    # logo 路径：使用相对路径或base64编码
    logo_path = os.path.join(BASE_DIR, 'logo.jpg')
    logo_url = None
    if os.path.exists(logo_path):
        # 尝试使用Gradio的文件路径格式
        logo_url = logo_path.replace('\\', '/')
    else:
        logo_url = None

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

        # ── 顶部导航栏 ────────────────────────────────────────
        logo_img_html = ''
        if logo_url:
            logo_img_html = f'''<img src="file/{logo_url}"
                 style="width:36px;height:36px;border-radius:10px;object-fit:cover;box-shadow:0 2px 8px rgba(0,0,0,.15);"
                 onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">'''

        gr.HTML(f"""
        <div class="topbar">
          <div class="topbar-brand">
            {logo_img_html}
            <div class="topbar-logo" style="display:{'none' if logo_url else 'flex'};">织</div>
            <div>
              <div class="topbar-name">{APP_NAME}</div>
              <div class="topbar-sub">{APP_SUB}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:12px;">
            {badge}
            <span style="font-size:11px;color:#cbd5e1;background:#1e293b;
                padding:3px 10px;border-radius:20px;border:1px solid #334155;">
              v2.0 专业版
            </span>
          </div>
        </div>
        """)

        # ── 进度提示横幅（口型同步时显示）────────────────────
        progress_banner = gr.HTML(
            value='',
            elem_id="zdai-progress-banner",
            visible=False,
        )

        # ════════════════════ 顶层 Tabs ════════════════════
        with gr.Tabs():

            # ── Tab 1：工作台 ────────────────────────────────
            with gr.Tab("🎬  工作台"):
                with gr.Row(elem_classes="workspace"):

                    # 列 1：语音合成
                    with gr.Column(scale=1, elem_classes="panel"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">1</span>语音合成</div>')
                        input_text = gr.TextArea(
                            label="输入文本",
                            placeholder="在此粘贴或输入需要合成的文字内容...",
                            lines=4)
                        prompt_audio = gr.Audio(
                            label="参考音频（3-10 秒，用于克隆音色）",
                            sources=["upload"], type="filepath")
                        with gr.Accordion("⚙️ 高级设置", open=False):
                            with gr.Row():
                                top_p = gr.Slider(label="词语多样性", info="越高输出越随机，建议 0.7~0.9", minimum=0.1, maximum=1.0, value=0.8, step=0.05)
                                top_k = gr.Slider(label="候选词数量", info="限制每步候选词，越小越保守，建议 20~50", minimum=1, maximum=100, value=30, step=1)
                            with gr.Row():
                                temperature = gr.Slider(label="语气活跃度", info="越高语气越有变化，越低越平稳", minimum=0.1, maximum=2.0, value=0.8, step=0.1)
                                num_beams   = gr.Slider(label="精确搜索强度", info="越高越精确但更慢，建议 1~5", minimum=1, maximum=10, value=3, step=1)
                            with gr.Row():
                                repetition_penalty = gr.Slider(label="避免重复程度", info="越高越不会重复相同词语", minimum=1.0, maximum=20.0, value=10.0, step=0.5)
                                max_mel_tokens     = gr.Slider(label="最大音频长度", info="更长文本需要更大数值，建议 1000~2000", minimum=500, maximum=3000, value=1500, step=100)
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
                        output_audio = gr.Audio(label="合成结果", interactive=False)

                    # 列 2：口型同步
                    with gr.Column(scale=1, elem_classes="panel"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">2</span>口型同步</div>')
                        video_input = gr.File(
                            label="上传人物视频（支持 MP4/AVI/MOV 等格式）",
                            file_types=["video"],
                            type="filepath")
                        video_preview = gr.Video(
                            label="视频预览",
                            height=220,
                            interactive=False,
                            visible=False)
                        gr.HTML('<div class="divider"></div>')
                        with gr.Tabs():
                            with gr.Tab("使用已合成的语音"):
                                audio_for_ls = gr.Audio(
                                    label="自动引用第一步合成结果",
                                    type="filepath", interactive=False)
                            with gr.Tab("上传自定义音频"):
                                custom_audio = gr.Audio(
                                    label="上传音频文件",
                                    sources=["upload"], type="filepath")
                        ls_btn = gr.Button("🚀  生成口型同步视频", variant="primary", size="lg")

                    # 列 3：生成结果
                    with gr.Column(scale=2, elem_classes="panel", elem_id="output-video-col"):
                        gr.HTML('<div class="panel-head"><span class="step-chip">3</span>生成结果</div>')
                        ls_detail_html = gr.HTML(value="", visible=False, elem_id="ls-detail-box")
                        output_video = gr.Video(label="最终合成视频", height=520, elem_id="output-video")

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
                            value='<div style="font-size:12px;color:#94a3b8;padding:8px 0">尚无记录，完成一次口型同步后自动保存。</div>'
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


            # ── Tab 3：批量任务 ──────────────────────────────
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
                            progress(0.3, desc=f"[{idx}/{total}] {tn} — 口型同步...")
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


                        # ── 日志数据源（Gradio 渲染到 DOM，CSS 视觉隐藏）────
        op_log_html = gr.HTML(
            value='<div id="zdai-log-inner">'
                  '<div class="log-entry">'
                  '<span class="log-ok">●</span>'
                  '<span class="log-time">--:--:--</span>'
                  '系统就绪，等待操作...</div></div>',
            elem_id="zdai-log-src",
        )

        # ════════════════════ 事件绑定 ════════════════════
        _log = []

        def _make_log(ok: bool, msg: str) -> str:
            _log.append({"ok": ok, "t": time.strftime("%H:%M:%S"), "msg": msg})
            recent  = _log[-25:]
            entries = ""
            for item in recent:
                ic = '<span class="log-ok">✓</span>' if item["ok"] else '<span class="log-err">✗</span>'
                entries += (f'<div class="log-entry">'
                            f'{ic}<span class="log-time">{item["t"]}</span>'
                            f'{item["msg"]}</div>')
            return f'<div id="zdai-log-inner">{entries}</div>'

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

        # TTS
        def tts_wrap(text, pa, tp, tk, temp, nb, rp, mmt,
                     emo_m, emo_a, emo_w, emo_t,
                     v1, v2, v3, v4, v5, v6, v7, v8):
            r = generate_speech(text, pa, tp, tk, temp, nb, rp, mmt,
                                emo_m, emo_a, emo_w, emo_t,
                                v1, v2, v3, v4, v5, v6, v7, v8)
            try:
                ps = (
                    "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
                    "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom,ContentType=WindowsRuntime]|Out-Null;"
                    "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(2);"
                    "$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('织梦AI — 语音合成完成'))|Out-Null;"
                    "$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('音频已生成，可以进行口型同步。'))|Out-Null;"
                    "$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
                    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('织梦AI').Show($n);"
                )
                subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                                 creationflags=subprocess.CREATE_NO_WINDOW,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return r[0], _make_log(True, "语音合成完成 — " + os.path.basename(r[0])), r[2]

        gen_btn.click(tts_wrap,
            inputs=[input_text, prompt_audio, top_p, top_k, temperature,
                    num_beams, repetition_penalty, max_mel_tokens,
                    emo_mode, emo_audio, emo_weight, emo_text,
                    vec1, vec2, vec3, vec4, vec5, vec6, vec7, vec8],
            outputs=[output_audio, op_log_html, audio_for_ls])

        # 视频上传
        def auto_convert(video, progress=gr.Progress()):
            if not video:
                return None, None, gr.update(visible=False), _make_log(False, "未选择视频")
            try:
                converted = convert_video_for_browser(video, progress)
                if converted and converted != video and os.path.exists(converted):
                    return converted, converted, gr.update(visible=True), _make_log(True, "视频就绪 — " + os.path.basename(converted))
                return video, video, gr.update(visible=True), _make_log(True, "视频上传完成")
            except Exception as e:
                safe_print(f"[ERR] 视频转换失败: {e}")
                traceback.print_exc()
                # 即使转换失败，也返回原视频，让用户可以继续使用
                return video, video, gr.update(visible=True), _make_log(True, "视频上传完成（未转换）")

        video_input.upload(auto_convert,
            inputs=[video_input], outputs=[video_input, video_preview, video_preview, op_log_html])

        # 口型同步
        def ls_wrap(video, auto_a, custom_a, progress=gr.Progress()):
            audio  = custom_a if custom_a else auto_a
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

            # 显示加载状态
            loading_html = (
                '<div style="background:linear-gradient(135deg,#1e293b,#0f172a);' +
                'border:1.5px solid #6366f1;border-radius:12px;padding:12px 16px;' +
                'font-family:Microsoft YaHei,sans-serif;font-size:12px;color:#94a3b8;text-align:center;">' +
                '<span style="color:#6366f1;font-weight:700;">⏳ 正在生成...</span></div>'
            )
            yield gr.update(), gr.update(), gr.update(value=loading_html, visible=True)

            while True:
                try:
                    item = q.get(timeout=0.3)
                    if item[0] == "done":
                        break
                    elif item[0] == "detail":
                        yield gr.update(), gr.update(), gr.update(value=item[1], visible=True)
                except _queue.Empty:
                    yield gr.update(), gr.update(), gr.update()

            if result["err"]:
                yield gr.update(), _make_log(False, f"口型同步失败: {result['err']}"), gr.update(visible=False)
                raise gr.Error(str(result["err"]))

            out      = result["out"]
            log_html = _make_log(True, "口型同步完成 — " + os.path.basename(out))
            try:
                ps = (
                    "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
                    "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom,ContentType=WindowsRuntime]|Out-Null;"
                    "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(2);"
                    "$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('织梦AI — 合成完成'))|Out-Null;"
                    "$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('视频口型同步已完成！'))|Out-Null;"
                    "$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
                    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('织梦AI').Show($n);"
                )
                subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                                 creationflags=subprocess.CREATE_NO_WINDOW,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            yield gr.update(value=out), log_html, gr.update(visible=False)

        ls_btn.click(ls_wrap,
            inputs=[video_input, audio_for_ls, custom_audio],
            outputs=[output_video, op_log_html, ls_detail_html])

        # 历史操作
        def _do_refresh():
            return gr.update(choices=_hist_choices(), value=None), _hist_info_html(), _make_log(True, "历史记录已刷新")
        refresh_hist_btn.click(_do_refresh, outputs=[hist_dropdown, hist_info, op_log_html])

        # 初始化时自动刷新历史列表
        def _auto_refresh():
            return gr.update(choices=_hist_choices(), value=None), _hist_info_html()
        app.load(_auto_refresh, outputs=[hist_dropdown, hist_info])

        open_folder_btn.click(
            lambda: (
                subprocess.Popen(["explorer", OUTPUT_DIR],
                    creationflags=subprocess.CREATE_NO_WINDOW)
                if sys.platform == "win32" else None,
                _make_log(True, "已打开输出文件夹")
            )[1],
            outputs=[op_log_html])

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
                    '<div style="font-size:12px;color:#94a3b8;padding:8px 0">记录已清空，视频文件仍保留在磁盘上。</div>',
                    _make_log(True, "历史记录条目已清空（文件保留）"))

        clear_records_btn.click(
            _clear_records_only,
            outputs=[clear_confirm_group, hist_dropdown, hist_info, op_log_html])

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
                    None,
                    _make_log(True, f"历史记录及 {deleted} 个文件已彻底删除"))

        clear_all_files_btn.click(
            _clear_all_with_files,
            outputs=[clear_confirm_group, hist_dropdown, hist_info, hist_video, op_log_html])

        def _load_hist(p):
            if not p: return None, ""
            if not os.path.exists(p):
                return None, '<div style="font-size:12px;color:#dc2626">❌ 文件不存在</div>'
            sz   = round(os.path.getsize(p)/1048576, 1)
            info = f'<div style="font-size:12px;color:#16a34a;padding:4px 0">✅ {os.path.basename(p)} ({sz} MB)</div>'
            return p, info
        hist_dropdown.change(_load_hist, inputs=[hist_dropdown], outputs=[hist_video, hist_info])

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
                # ★ 关键：允许 Gradio 静态服务访问 BASE_DIR（logo.jpg / 转换视频等）
                allowed_paths=[BASE_DIR, OUTPUT_DIR],
            )
            break
        except OSError:
            continue