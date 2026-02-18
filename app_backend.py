# -*- coding: utf-8 -*-
# 启动应用_backend.py — 由 启动应用.vbs 通过 pythonw.exe 调用
#
# 架构（主线程流程）：
#   1. 立即显示 tkinter 启动画面
#   2. 后台线程：启动 Gradio 子进程
#   3. 后台线程：轮询端口，就绪后通知主线程退出 mainloop
#   4. 主线程：销毁 tkinter → 调用 webview.start()
#   5. 任何异常 → 显示在错误窗口，不静默

import os, sys, time, socket, threading, subprocess, signal, traceback

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR = os.path.join(BASE_DIR, "IndexTTS2-SonicVale")

os.environ['PYTHONNOUSERSITE'] = '1'
os.environ['http_proxy']  = ''
os.environ['https_proxy'] = ''

gradio_process = None
_cleaned_up    = False
_gradio_url    = None        # 就绪后由子线程写入
_root_ref      = [None]      # 保存 tkinter root，供子线程调用 root.after
_webview_win   = [None]      # pywebview 窗口引用
_tray_icon     = [None]      # 系统托盘图标引用


# ══════════════════════════════════════════════════════════════
#  pywebview JS API（Gradio 页面 JS 可通过 pywebview.api.xxx() 调用）
# ══════════════════════════════════════════════════════════════
class AppApi:
    def minimize_to_tray(self):
        """最小化到系统通知区域（托盘）"""
        w = _webview_win[0]
        if w:
            try: w.hide()
            except Exception: pass
        _start_tray_icon()

    def close_app(self):
        """用户确认退出，彻底关闭程序（必须在子线程，否则死锁）"""
        import threading as _t
        _t.Thread(target=cleanup, daemon=True).start()

_api = AppApi()


def _start_tray_icon():
    """在后台线程启动系统托盘图标（点击恢复窗口）"""
    def run():
        try:
            import pystray
            from PIL import Image, ImageDraw
            # 绘制简单图标（64x64 紫色圆形）
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], fill='#6366f1')
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("msyh.ttc", 28)
                d.text((32, 32), "织", font=font, fill='white', anchor='mm')
            except Exception:
                d.text((20, 18), "AI", fill='white')

            def on_restore(icon, item):
                icon.stop()
                _tray_icon[0] = None
                w = _webview_win[0]
                if w:
                    try: w.show()
                    except Exception: pass

            def on_exit(icon, item):
                icon.stop()
                cleanup()

            menu = pystray.Menu(
                pystray.MenuItem('打开织梦AI', on_restore, default=True),
                pystray.MenuItem('退出程序', on_exit),
            )
            icon = pystray.Icon('ZhiMoAI', img, '织梦AI大模型', menu)
            _tray_icon[0] = icon
            icon.run()
        except Exception:
            # pystray 不可用时降级为普通最小化
            w = _webview_win[0]
            if w:
                try: w.minimize()
                except Exception: pass

    threading.Thread(target=run, daemon=True).start()


# ══════════════════════════════════════════════════════════════
#  读取 .env 配置
# ══════════════════════════════════════════════════════════════
def load_env_config():
    """读取.env配置文件"""
    config = {
        'DEBUG_MODE': False,
        'SERVER_PORT_START': 7870,
        'SERVER_PORT_END': 7874
    }
    
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'DEBUG_MODE':
                            config['DEBUG_MODE'] = value.lower() in ('true', '1', 'yes', 'on')
                        elif key == 'SERVER_PORT_START':
                            config['SERVER_PORT_START'] = int(value)
                        elif key == 'SERVER_PORT_END':
                            config['SERVER_PORT_END'] = int(value)
        except Exception:
            pass
    
    return config

# 加载配置
ENV_CONFIG = load_env_config()


# ══════════════════════════════════════════════════════════════
#  错误弹窗（在 tkinter 窗口中展示，不静默）
# ══════════════════════════════════════════════════════════════
def show_error_window(title: str, msg: str):
    """销毁当前启动画面，弹出错误详情窗口"""
    import tkinter as tk
    from tkinter import scrolledtext

    # 先关闭已有的 splash
    if _root_ref[0]:
        try:
            _root_ref[0].destroy()
        except Exception:
            pass

    err_root = tk.Tk()
    err_root.title(f"VocalSync AI Studio — {title}")
    err_root.configure(bg="#ffffff")
    err_root.resizable(True, True)

    W, H = 560, 340
    sw, sh = err_root.winfo_screenwidth(), err_root.winfo_screenheight()
    err_root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

    import tkinter as tk
    # 标题
    tk.Label(err_root, text=f"⚠  {title}", font=("Microsoft YaHei", 12, "bold"),
             bg="#ffffff", fg="#dc2626").pack(anchor="w", padx=16, pady=(16, 4))

    # 错误内容（可滚动、可选中复制）
    box = scrolledtext.ScrolledText(
        err_root, font=("Consolas", 9), bg="#fef2f2", fg="#7f1d1d",
        wrap="word", bd=0, relief="flat", padx=8, pady=8,
    )
    box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
    box.insert("end", msg)
    box.configure(state="disabled")

    tk.Label(err_root, text="请截图此错误信息并联系技术支持",
             font=("Microsoft YaHei", 9), bg="#ffffff", fg="#94a3b8").pack(pady=(0,4))

    tk.Button(err_root, text="关闭", command=err_root.destroy,
              font=("Microsoft YaHei", 10), bg="#2563eb", fg="#fff",
              bd=0, padx=20, pady=6, cursor="hand2").pack(pady=(0, 14))

    err_root.mainloop()


# ══════════════════════════════════════════════════════════════
#  进程清理
# ══════════════════════════════════════════════════════════════
def kill_process_tree(pid):
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
        except Exception:
            pass
    else:
        try:
            import signal as _s; os.killpg(os.getpgid(pid), _s.SIGKILL)
        except Exception:
            pass


def cleanup():
    global _cleaned_up, gradio_process
    if _cleaned_up: return
    _cleaned_up = True
    if gradio_process and gradio_process.pid:
        kill_process_tree(gradio_process.pid)
    os._exit(0)


# ══════════════════════════════════════════════════════════════
#  启动 Gradio 子进程（后台线程）
# ══════════════════════════════════════════════════════════════
def start_gradio():
    global gradio_process
    python_path = os.path.join(INDEXTTS_DIR, "installer_files", "env", "python.exe")
    script_path = os.path.join(BASE_DIR, "unified_app.py")

    # 路径检查
    if not os.path.exists(python_path):
        _notify_error("Python 解释器未找到",
                      f"路径不存在：\n{python_path}\n\n"
                      "请确认 IndexTTS2-SonicVale\\installer_files\\env\\python.exe 存在。")
        return
    if not os.path.exists(script_path):
        _notify_error("主程序未找到",
                      f"路径不存在：\n{script_path}\n\n"
                      "请确认 unified_app.py 与启动脚本在同一目录。")
        return

    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    log_path = os.path.join(BASE_DIR, "gradio_error.log")
    try:
        with open(log_path, 'w', encoding='utf-8', errors='replace') as log_f:
            gradio_process = subprocess.Popen(
                [python_path, "-u", script_path],
                stdout=log_f, stderr=log_f,
                creationflags=flags,
            )
            gradio_process.wait()
        if gradio_process.returncode not in (0, None):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as lf:
                    err = lf.read()[-3000:]
            except Exception:
                err = "(无法读取日志)"
            _notify_error("Gradio 运行出错", f"退出码: {gradio_process.returncode}\n\n{err}")
    except Exception:
        _notify_error("Gradio 启动失败", traceback.format_exc())


def _notify_error(title: str, detail: str):
    """从子线程安全地通知主线程显示错误窗口"""
    root = _root_ref[0]
    if root:
        try:
            root.after(0, lambda: _do_show_error(title, detail))
            return
        except Exception:
            pass
    # 主线程 tkinter 已不可用，直接弹
    show_error_window(title, detail)


def _do_show_error(title: str, detail: str):
    """在主线程中运行：关闭 splash，打开错误窗口"""
    root = _root_ref[0]
    if root:
        try: root.quit()
        except Exception: pass
    # 稍延迟，让 mainloop 先退出
    threading.Thread(target=lambda: (time.sleep(0.3), show_error_window(title, detail)),
                     daemon=True).start()


# ══════════════════════════════════════════════════════════════
#  轮询端口（后台线程）
# ══════════════════════════════════════════════════════════════
def wait_for_gradio(timeout=180):
    global _gradio_url
    # 使用配置文件中的端口范围
    port_start = ENV_CONFIG['SERVER_PORT_START']
    port_end = ENV_CONFIG['SERVER_PORT_END']
    ports = tuple(range(port_start, port_end + 1))
    
    deadline = time.time() + timeout
    while time.time() < deadline:
        for port in ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    s.close(); _gradio_url = f'http://127.0.0.1:{port}'
                    # 通知主线程退出 mainloop
                    root = _root_ref[0]
                    if root:
                        try: root.after(0, root.quit)
                        except Exception: pass
                    return
                s.close()
            except Exception:
                pass
        time.sleep(0.8)
    # 超时：用默认 URL 继续
    _gradio_url = f'http://127.0.0.1:{ports[0]}'
    root = _root_ref[0]
    if root:
        try: root.after(0, root.quit)
        except Exception: pass


# ══════════════════════════════════════════════════════════════
#  启动画面状态文案时间表
# ══════════════════════════════════════════════════════════════
STATUS_TIMELINE = [
    ( 0,  "正在启动运行环境，请稍候..."),
    ( 4,  "正在加载语音合成引擎..."),
    (10,  "正在初始化声学模型与音色编码器..."),
    (18,  "正在加载口型同步模型..."),
    (28,  "正在分配 GPU / CPU 推理资源..."),
    (40,  "正在启动界面服务..."),
    (55,  "界面服务启动中，即将就绪..."),
    (80,  "最后准备中，马上就好..."),
    (110, "仍在加载，模型文件较大请耐心等待..."),
]


# ══════════════════════════════════════════════════════════════
#  构建 tkinter 启动画面
# ══════════════════════════════════════════════════════════════
def build_splash():
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    _root_ref[0] = root

    root.title("织梦AI大模型")
    root.resizable(False, False)
    root.overrideredirect(True)   # 无系统标题栏

    W, H = 520, 300
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
    root.configure(bg="#0f172a")
    root.attributes("-topmost", True)

    # 外框（模拟阴影）
    outer = tk.Frame(root, bg="#1e293b", bd=0)
    outer.place(x=3, y=3, width=W-3, height=H-3)

    card = tk.Frame(root, bg="#ffffff", bd=0)
    card.place(x=0, y=0, width=W-3, height=H-3)

    # 顶部渐变彩条
    gradient_frame = tk.Frame(card, bg="#6366f1", height=6)
    gradient_frame.pack(fill="x", side="top")

    # Logo + 标题
    logo_row = tk.Frame(card, bg="#ffffff")
    logo_row.pack(pady=(28, 0))

    # Logo圆形
    logo_box = tk.Canvas(logo_row, width=52, height=52, bg="#ffffff", highlightthickness=0)
    logo_box.pack(side="left", padx=(0, 14))
    # 绘制渐变圆形
    logo_box.create_oval(2, 2, 50, 50, fill="#6366f1", outline="#8b5cf6", width=2)
    logo_box.create_text(26, 26, text="织", font=("Microsoft YaHei", 18, "bold"), fill="#ffffff")

    title_col = tk.Frame(logo_row, bg="#ffffff")
    title_col.pack(side="left")
    tk.Label(title_col, text="织梦AI大模型",
             font=("Microsoft YaHei", 18, "bold"),
             bg="#ffffff", fg="#0f172a").pack(anchor="w")
    tk.Label(title_col, text="AI语音克隆 · 智能口型同步 · 专业级解决方案",
             font=("Microsoft YaHei", 9),
             bg="#ffffff", fg="#64748b").pack(anchor="w", pady=(2, 0))

    # 分割线
    tk.Frame(card, bg="#e2e8f0", height=1).pack(fill="x", padx=28, pady=(20, 0))

    # 状态文字（可更新）
    status_var = tk.StringVar(value=STATUS_TIMELINE[0][1])
    tk.Label(card, textvariable=status_var,
             font=("Microsoft YaHei", 10), bg="#ffffff", fg="#6366f1",
             anchor="w").pack(fill="x", padx=32, pady=(16, 8))

    # 进度条
    style = ttk.Style()
    style.theme_use("default")
    style.configure("B.Horizontal.TProgressbar",
                    troughcolor="#e2e8f0", background="#6366f1",
                    bordercolor="#e2e8f0", lightcolor="#6366f1", darkcolor="#6366f1")
    pb = ttk.Progressbar(card, style="B.Horizontal.TProgressbar",
                         mode="indeterminate", length=456)
    pb.pack(padx=32, pady=(0, 18))
    pb.start(8)

    # 底部小字
    tk.Frame(card, bg="#e2e8f0", height=1).pack(fill="x", padx=28)
    bottom_frame = tk.Frame(card, bg="#ffffff")
    bottom_frame.pack(pady=12)
    tk.Label(bottom_frame, text="🔒 本地运行 · 数据安全",
             font=("Microsoft YaHei", 8), bg="#ffffff", fg="#94a3b8"
             ).pack(side="left", padx=8)
    tk.Label(bottom_frame, text="·",
             font=("Microsoft YaHei", 8), bg="#ffffff", fg="#cbd5e1"
             ).pack(side="left")
    tk.Label(bottom_frame, text="v2.0 商业版",
             font=("Microsoft YaHei", 8), bg="#ffffff", fg="#94a3b8"
             ).pack(side="left", padx=8)

    # ── 鼠标拖动移动窗口 ─────────────────────────────────
    _drag = {"x": 0, "y": 0}

    def on_press(e):
        _drag["x"] = e.x_root - root.winfo_x()
        _drag["y"] = e.y_root - root.winfo_y()

    def on_drag(e):
        root.geometry(f"+{e.x_root - _drag['x']}+{e.y_root - _drag['y']}")

    root.bind("<ButtonPress-1>", on_press)
    root.bind("<B1-Motion>", on_drag)
    card.bind("<ButtonPress-1>", on_press)
    card.bind("<B1-Motion>", on_drag)

    return root, status_var


# ══════════════════════════════════════════════════════════════
#  主线程：运行启动画面 + 轮询更新状态文案
# ══════════════════════════════════════════════════════════════
def run_splash(root, status_var):
    start_time   = time.time()
    tl_idx       = [0]

    def tick():
        elapsed = time.time() - start_time
        # 更新文案
        i = tl_idx[0]
        while i + 1 < len(STATUS_TIMELINE) and elapsed >= STATUS_TIMELINE[i+1][0]:
            i += 1
        if i != tl_idx[0]:
            tl_idx[0] = i
            status_var.set(STATUS_TIMELINE[i][1])
        # Gradio 就绪 → 更新提示后退出
        if _gradio_url is not None:
            status_var.set("✅ 界面服务已就绪，正在打开窗口...")
            root.after(700, root.quit)
            return
        root.after(300, tick)

    root.after(300, tick)
    root.mainloop()


# ══════════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    signal.signal(signal.SIGINT,  lambda s, f: cleanup())
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda s, f: cleanup())

    # ── 后台线程：启动 Gradio & 等待端口 ────────────────
    threading.Thread(target=start_gradio,   daemon=True).start()
    threading.Thread(target=wait_for_gradio, daemon=True).start()

    # ── 主线程：显示启动画面（含实时状态） ──────────────
    try:
        root, status_var = build_splash()
        run_splash(root, status_var)
        try: root.destroy()
        except Exception: pass
    except Exception as e:
        # tkinter 初始化失败也要继续（极少见）
        pass

    # ── 确保有 URL ───────────────────────────────────────
    if _gradio_url is None:
        _gradio_url = 'http://127.0.0.1:7870'

    # ── 主线程：启动 WebView ─────────────────────────────
    try:
        import webview
    except ImportError:
        python_path = os.path.join(INDEXTTS_DIR, "installer_files", "env", "python.exe")
        try:
            subprocess.run(
                [python_path, "-m", "pip", "install", "pywebview", "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            import webview
        except Exception as e:
            show_error_window("pywebview 安装失败",
                              f"自动安装 pywebview 失败：\n\n{traceback.format_exc()}\n\n"
                              f"请手动运行：\n{python_path} -m pip install pywebview")
            cleanup()

    try:
        # 根据配置决定是否启用开发者工具
        debug_mode = ENV_CONFIG['DEBUG_MODE']
        
        window = webview.create_window(
            '织梦AI大模型 - 专业版', _gradio_url,
            js_api=_api,
            width=1480, height=940, resizable=True,
            min_size=(1200, 800), text_select=True, easy_drag=False,
        )
        _webview_win[0] = window

        # ── 拦截窗口 X 关闭按钮：注入 JS 弹出自定义弹窗 ──
        # 用 closing 事件（返回 False = 阻止关闭）并通过 JS 显示弹窗
        # 注意：只在弹窗用户主动选"退出"时才真正关闭
        def on_closing():
            try:
                window.evaluate_js("window._zm && window._zm.show()")
            except Exception:
                pass
            return False   # 阻止默认关闭，交由弹窗决定

        window.events.closing += on_closing

        # 根据配置启用或禁用调试模式
        if debug_mode:
            webview.start(debug=True)
        else:
            webview.start(debug=False)
    except Exception:
        show_error_window("WebView 启动失败", traceback.format_exc())

    cleanup()