# -*- coding: utf-8 -*-
# app_backend.py — 由 启动应用.vbs 通过 pythonw.exe 调用
#
# 架构：
#   1. 立即显示 tkinter 启动画面
#   2. 后台线程：启动 Gradio 子进程
#   3. 后台线程：轮询端口，就绪后通知主线程退出 mainloop
#   4. 主线程：销毁 tkinter → 调用 webview.start()

import os, sys, time, socket, threading, subprocess, signal, traceback

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR = os.path.join(BASE_DIR, "IndexTTS2-SonicVale")

os.environ['PYTHONNOUSERSITE'] = '1'
os.environ['http_proxy']  = ''
os.environ['https_proxy'] = ''

gradio_process = None
_cleaned_up    = False
_gradio_url    = None
_root_ref      = [None]
_webview_win   = [None]
_tray_icon     = [None]
_hwnd          = [None]   # 主窗口 HWND 缓存


# ══════════════════════════════════════════════════════════════
#  工具：查找主窗口 HWND（每次重新枚举）
# ══════════════════════════════════════════════════════════════
def _get_main_hwnd():
    """实时枚举所有窗口，找到织梦AI主窗口句柄"""
    try:
        import ctypes
        result = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.POINTER(ctypes.c_int))

        def callback(hwnd, _):
            try:
                if not ctypes.windll.user32.IsWindowVisible(hwnd):
                    return True
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                # 匹配任意包含「织梦AI」或「专业版」的窗口
                if '织梦AI' in title or '专业版' in title:
                    result.append(hwnd)
                    print(f"[HWND] 找到: hwnd={hwnd} title={title!r}")
            except Exception:
                pass
            return True

        ctypes.windll.user32.EnumWindows(WNDENUMPROC(callback), 0)
        if result:
            _hwnd[0] = result[0]
            return result[0]
    except Exception as e:
        print(f"[HWND] 枚举失败: {e}")
    return _hwnd[0]   # 返回上次缓存


# ══════════════════════════════════════════════════════════════
#  JS API（Gradio 页面可调用）
# ══════════════════════════════════════════════════════════════
class AppApi:

    def minimize_to_tray(self):
        """最小化到系统托盘"""
        print("[API] minimize_to_tray 被调用")

        def _do():
            # 1. 确保托盘图标已启动
            if not _tray_icon[0]:
                _start_tray_icon()
                # 最多等 2 秒让 pystray 消息循环就绪
                for _ in range(20):
                    time.sleep(0.1)
                    if _tray_icon[0]:
                        break
            else:
                print("[API] 托盘图标已存在")

            # 2. 用 ctypes 查找并隐藏窗口
            hwnd = _get_main_hwnd()
            print(f"[API] HWND={hwnd}")
            if hwnd:
                try:
                    import ctypes
                    u32 = ctypes.windll.user32
                    # 隐藏窗口
                    u32.ShowWindow(hwnd, 0)           # SW_HIDE = 0
                    # 从任务栏移除（改为工具窗口样式）
                    GWL_EXSTYLE      = -20
                    WS_EX_APPWINDOW  = 0x00040000
                    WS_EX_TOOLWINDOW = 0x00000080
                    style = u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    style = (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
                    u32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                    print(f"[API] ✓ 窗口已隐藏至托盘 (hwnd={hwnd})")
                except Exception as e:
                    print(f"[API] ctypes 失败: {e}")
                    # 兜底：尝试 pywebview 原生
                    w = _webview_win[0]
                    if w:
                        try: w.minimize()
                        except Exception: pass
            else:
                print("[API] ✗ 未找到主窗口 HWND，等待后重试...")
                time.sleep(1.5)
                hwnd2 = _get_main_hwnd()
                if hwnd2:
                    try:
                        import ctypes
                        ctypes.windll.user32.ShowWindow(hwnd2, 0)
                        print(f"[API] ✓ 重试成功 (hwnd={hwnd2})")
                    except Exception as e:
                        print(f"[API] 重试失败: {e}")

        threading.Thread(target=_do, daemon=True).start()

    def close_app(self):
        """强制退出整个程序"""
        print("[API] close_app 被调用")

        def _do():
            try:
                if _tray_icon[0]:
                    _tray_icon[0].stop()
            except Exception:
                pass
            try:
                if gradio_process and gradio_process.pid:
                    kill_process_tree(gradio_process.pid)
            except Exception:
                pass
            print("[API] os._exit(0)")
            os._exit(0)

        threading.Thread(target=_do, daemon=True).start()

    def send_notification(self, title, body):
        """发送 Windows Toast 通知"""
        def _do():
            try:
                ps = (
                    "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
                    "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType=WindowsRuntime] | Out-Null;"
                    f"$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                    f"$xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('{title}')) | Out-Null;"
                    f"$xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{body}')) | Out-Null;"
                    "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml);"
                    "$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('织梦AI');"
                    "$notifier.Show($toast);"
                )
                subprocess.Popen(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()


_api = AppApi()


# ══════════════════════════════════════════════════════════════
#  系统托盘图标
# ══════════════════════════════════════════════════════════════
def _start_tray_icon():
    """在守护线程中启动 pystray 托盘图标"""
    if _tray_icon[0]:
        print("[TRAY] 已存在，跳过")
        return

    def _run():
        try:
            import pystray
            from PIL import Image

            # 加载图标
            img = None
            for path in [
                os.path.join(BASE_DIR, "logo.ico"),
                os.path.join(BASE_DIR, "logo.jpg"),
            ]:
                if os.path.exists(path):
                    try:
                        img = Image.open(path).convert("RGBA")
                        if img.size[0] > 64:
                            img = img.resize((64, 64), Image.Resampling.LANCZOS)
                        print(f"[TRAY] 加载图标: {path}")
                        break
                    except Exception as e:
                        print(f"[TRAY] 加载失败 {path}: {e}")

            if img is None:
                from PIL import ImageDraw
                img = Image.new("RGBA", (64, 64), (99, 102, 241, 255))
                ImageDraw.Draw(img).text((18, 18), "AI", fill="white")
                print("[TRAY] 使用默认图标")

            def on_restore(icon, item):
                print("[TRAY] 恢复窗口")
                icon.stop()
                _tray_icon[0] = None
                hwnd = _get_main_hwnd()
                if hwnd:
                    try:
                        import ctypes
                        u32 = ctypes.windll.user32
                        # 恢复任务栏样式
                        GWL_EXSTYLE      = -20
                        WS_EX_APPWINDOW  = 0x00040000
                        WS_EX_TOOLWINDOW = 0x00000080
                        style = u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                        style = (style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
                        u32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                        u32.ShowWindow(hwnd, 9)          # SW_RESTORE = 9
                        u32.SetForegroundWindow(hwnd)
                        print(f"[TRAY] ✓ 窗口已恢复 (hwnd={hwnd})")
                    except Exception as e:
                        print(f"[TRAY] ctypes 恢复失败: {e}")
                        w = _webview_win[0]
                        if w:
                            try: w.show()
                            except Exception: pass
                else:
                    w = _webview_win[0]
                    if w:
                        try: w.show()
                        except Exception as e:
                            print(f"[TRAY] w.show() 失败: {e}")

            def on_exit(icon, item):
                icon.stop()
                cleanup()

            menu = pystray.Menu(
                pystray.MenuItem("打开织梦AI", on_restore, default=True),
                pystray.MenuItem("退出程序",   on_exit),
            )
            icon = pystray.Icon("ZhiMoAI", img, "织梦AI大模型", menu)
            _tray_icon[0] = icon
            print("[TRAY] 启动 icon.run()")
            icon.run()
            print("[TRAY] icon.run() 结束")
        except ImportError as e:
            print(f"[TRAY] 缺少依赖（pystray / PIL）: {e}")
        except Exception as e:
            print(f"[TRAY] 启动失败: {e}")
            traceback.print_exc()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    print(f"[TRAY] 线程已启动 id={t.ident}")


# ══════════════════════════════════════════════════════════════
#  读取 .env 配置
# ══════════════════════════════════════════════════════════════
def load_env_config():
    config = {'DEBUG_MODE': False, 'SERVER_PORT_START': 7870, 'SERVER_PORT_END': 7874}
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip(); value = value.strip()
                    if   key == 'DEBUG_MODE':          config['DEBUG_MODE'] = value.lower() in ('true','1','yes','on')
                    elif key == 'SERVER_PORT_START':   config['SERVER_PORT_START'] = int(value)
                    elif key == 'SERVER_PORT_END':     config['SERVER_PORT_END']   = int(value)
        except Exception:
            pass
    return config

ENV_CONFIG = load_env_config()


# ══════════════════════════════════════════════════════════════
#  错误弹窗
# ══════════════════════════════════════════════════════════════
def show_error_window(title: str, msg: str):
    import tkinter as tk
    from tkinter import scrolledtext
    if _root_ref[0]:
        try: _root_ref[0].destroy()
        except Exception: pass
    err = tk.Tk()
    err.title(f"织梦AI — {title}")
    err.configure(bg="#ffffff")
    err.resizable(True, True)
    W, H = 560, 340
    sw, sh = err.winfo_screenwidth(), err.winfo_screenheight()
    err.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
    tk.Label(err, text=f"⚠  {title}", font=("Microsoft YaHei", 12, "bold"),
             bg="#ffffff", fg="#dc2626").pack(anchor="w", padx=16, pady=(16,4))
    box = scrolledtext.ScrolledText(err, font=("Consolas", 9), bg="#fef2f2", fg="#7f1d1d",
                                    wrap="word", bd=0, relief="flat", padx=8, pady=8)
    box.pack(fill="both", expand=True, padx=16, pady=(0,8))
    box.insert("end", msg)
    box.configure(state="disabled")
    tk.Label(err, text="请截图此错误信息并联系技术支持",
             font=("Microsoft YaHei", 9), bg="#ffffff", fg="#94a3b8").pack(pady=(0,4))
    tk.Button(err, text="关闭", command=err.destroy,
              font=("Microsoft YaHei", 10), bg="#2563eb", fg="#fff",
              bd=0, padx=20, pady=6, cursor="hand2").pack(pady=(0,14))
    err.mainloop()


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
            import signal as _s
            os.killpg(os.getpgid(pid), _s.SIGKILL)
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
#  启动 Gradio 子进程
# ══════════════════════════════════════════════════════════════
def start_gradio():
    global gradio_process
    python_path = os.path.join(INDEXTTS_DIR, "installer_files", "env", "python.exe")
    script_path = os.path.join(BASE_DIR, "unified_app.py")
    if not os.path.exists(python_path):
        _notify_error("Python 解释器未找到", f"路径不存在：\n{python_path}"); return
    if not os.path.exists(script_path):
        _notify_error("主程序未找到", f"路径不存在：\n{script_path}"); return

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
    root = _root_ref[0]
    if root:
        try:
            root.after(0, lambda: _do_show_error(title, detail))
            return
        except Exception:
            pass
    show_error_window(title, detail)


def _do_show_error(title: str, detail: str):
    root = _root_ref[0]
    if root:
        try: root.quit()
        except Exception: pass
    threading.Thread(target=lambda: (time.sleep(0.3), show_error_window(title, detail)),
                     daemon=True).start()


# ══════════════════════════════════════════════════════════════
#  轮询端口
# ══════════════════════════════════════════════════════════════
def wait_for_gradio(timeout=180):
    global _gradio_url
    port_start = ENV_CONFIG['SERVER_PORT_START']
    port_end   = ENV_CONFIG['SERVER_PORT_END']
    ports      = tuple(range(port_start, port_end + 1))
    deadline   = time.time() + timeout
    while time.time() < deadline:
        for port in ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    s.close()
                    _gradio_url = f'http://127.0.0.1:{port}'
                    root = _root_ref[0]
                    if root:
                        try: root.after(0, root.quit)
                        except Exception: pass
                    return
                s.close()
            except Exception:
                pass
        time.sleep(0.8)
    _gradio_url = f'http://127.0.0.1:{ports[0]}'
    root = _root_ref[0]
    if root:
        try: root.after(0, root.quit)
        except Exception: pass


# ══════════════════════════════════════════════════════════════
#  启动画面
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


def build_splash():
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    _root_ref[0] = root
    root.title("织梦AI大模型")
    root.resizable(False, False)
    root.overrideredirect(True)
    W, H = 520, 300
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
    root.configure(bg="#0f172a")
    root.attributes("-topmost", True)

    outer = tk.Frame(root, bg="#1e293b", bd=0)
    outer.place(x=3, y=3, width=W-3, height=H-3)
    card = tk.Frame(root, bg="#ffffff", bd=0)
    card.place(x=0, y=0, width=W-3, height=H-3)
    tk.Frame(card, bg="#6366f1", height=6).pack(fill="x", side="top")

    logo_row = tk.Frame(card, bg="#ffffff")
    logo_row.pack(pady=(28, 0))

    logo_path = os.path.join(BASE_DIR, "logo.jpg")
    if os.path.exists(logo_path):
        try:
            from PIL import Image, ImageTk
            img = Image.open(logo_path).resize((52, 52), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(logo_row, image=photo, bg="#ffffff")
            lbl.image = photo
            lbl.pack(side="left", padx=(0, 14))
        except Exception:
            _splash_default_logo(logo_row)
    else:
        _splash_default_logo(logo_row)

    title_col = tk.Frame(logo_row, bg="#ffffff")
    title_col.pack(side="left")
    tk.Label(title_col, text="织梦AI大模型",
             font=("Microsoft YaHei", 18, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor="w")
    tk.Label(title_col, text="AI语音克隆 · 智能口型同步 · 专业级解决方案",
             font=("Microsoft YaHei", 9), bg="#ffffff", fg="#64748b").pack(anchor="w", pady=(2,0))

    tk.Frame(card, bg="#e2e8f0", height=1).pack(fill="x", padx=28, pady=(20, 0))
    status_var = tk.StringVar(value=STATUS_TIMELINE[0][1])
    tk.Label(card, textvariable=status_var,
             font=("Microsoft YaHei", 10), bg="#ffffff", fg="#6366f1",
             anchor="w").pack(fill="x", padx=32, pady=(16, 8))

    style = ttk.Style()
    style.theme_use("default")
    style.configure("B.Horizontal.TProgressbar",
                    troughcolor="#e2e8f0", background="#6366f1",
                    bordercolor="#e2e8f0", lightcolor="#6366f1", darkcolor="#6366f1")
    pb = ttk.Progressbar(card, style="B.Horizontal.TProgressbar",
                          mode="indeterminate", length=456)
    pb.pack(padx=32, pady=(0, 18))
    pb.start(8)

    tk.Frame(card, bg="#e2e8f0", height=1).pack(fill="x", padx=28)
    bf = tk.Frame(card, bg="#ffffff")
    bf.pack(pady=12)
    for txt in ["🔒 本地运行 · 数据安全", "·", "v2.0 商业版"]:
        tk.Label(bf, text=txt, font=("Microsoft YaHei", 8),
                 bg="#ffffff", fg="#94a3b8" if txt != "·" else "#cbd5e1").pack(side="left", padx=6)

    _drag = {"x": 0, "y": 0}
    def on_press(e):
        _drag["x"] = e.x_root - root.winfo_x()
        _drag["y"] = e.y_root - root.winfo_y()
    def on_drag(e):
        root.geometry(f"+{e.x_root - _drag['x']}+{e.y_root - _drag['y']}")
    for w in (root, card):
        w.bind("<ButtonPress-1>", on_press)
        w.bind("<B1-Motion>",     on_drag)
    return root, status_var


def _splash_default_logo(parent):
    import tkinter as tk
    c = tk.Canvas(parent, width=52, height=52, bg="#ffffff", highlightthickness=0)
    c.pack(side="left", padx=(0, 14))
    c.create_oval(2, 2, 50, 50, fill="#6366f1", outline="#8b5cf6", width=2)
    c.create_text(26, 26, text="织", font=("Microsoft YaHei", 18, "bold"), fill="#ffffff")


def run_splash(root, status_var):
    start_time = time.time()
    tl_idx = [0]

    def tick():
        elapsed = time.time() - start_time
        i = tl_idx[0]
        while i + 1 < len(STATUS_TIMELINE) and elapsed >= STATUS_TIMELINE[i+1][0]:
            i += 1
        if i != tl_idx[0]:
            tl_idx[0] = i
            status_var.set(STATUS_TIMELINE[i][1])
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
    # ── 单实例检查 ─────────────────────────────────────────
    _lock_socket = None
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(('127.0.0.1', 17870))
        print("[LOCK] 单实例锁已获取")
    except OSError:
        print("[LOCK] 程序已在运行，激活现有窗口...")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 17871))
            s.send(b'ACTIVATE')
            s.close()
        except Exception:
            pass
        sys.exit(0)

    # ── 先进行激活验证（在启动任何服务之前）─────────────────
    print("[LICENSE] 开始激活验证...")
    try:
        sys.path.insert(0, BASE_DIR)
        import lib_license as lic
        
        # 检查本地保存的卡密状态
        status, info = lic.check_saved_license()
        
        if status == "none":
            # 没有卡密，弹出激活窗口
            print("[LICENSE] 未找到激活信息，弹出激活窗口...")
            try:
                import tkinter as tk
                from tkinter import messagebox
                
                machine_code = lic.get_machine_code()
                result = {"passed": False}

                root = tk.Tk()
                root.title("软件激活")
                root.resizable(False, False)
                root.configure(bg="#f8fafc")

                # 居中
                w, h = 420, 260
                sx = (root.winfo_screenwidth() - w) // 2
                sy = (root.winfo_screenheight() - h) // 2
                root.geometry(f"{w}x{h}+{sx}+{sy}")

                # 标题
                tk.Label(root, text="软件激活", font=("Microsoft YaHei", 16, "bold"),
                         bg="#f8fafc", fg="#0f172a").pack(pady=(24, 4))
                tk.Label(root, text="请输入卡密以激活使用", font=("Microsoft YaHei", 10),
                         bg="#f8fafc", fg="#94a3b8").pack(pady=(0, 16))

                # 卡密输入
                frm = tk.Frame(root, bg="#f8fafc")
                frm.pack(padx=32, fill="x")

                tk.Label(frm, text="卡密", font=("Microsoft YaHei", 9, "bold"),
                         bg="#f8fafc", fg="#374151", anchor="w").pack(fill="x")
                key_entry = tk.Entry(frm, font=("Consolas", 11), relief="solid", bd=1)
                key_entry.pack(fill="x", ipady=4, pady=(2, 16))

                msg_label = tk.Label(frm, text="", font=("Microsoft YaHei", 9),
                                      bg="#f8fafc", fg="#ef4444")
                msg_label.pack(fill="x")

                def _do_login():
                    key = key_entry.get().strip()
                    if not key:
                        msg_label.config(text="请输入卡密", fg="#ef4444")
                        return
                    msg_label.config(text="正在验证...", fg="#6366f1")
                    root.update()
                    ok, msg = lic.validate_online(key)
                    if ok:
                        msg_label.config(text="激活成功!", fg="#16a34a")
                        result["passed"] = True
                        root.after(600, root.destroy)
                    else:
                        msg_label.config(text=msg, fg="#ef4444")

                btn = tk.Button(frm, text="激活登录", font=("Microsoft YaHei", 11, "bold"),
                                 bg="#6366f1", fg="white", relief="flat", cursor="hand2",
                                 activebackground="#4f46e5", activeforeground="white",
                                 command=_do_login)
                btn.pack(fill="x", ipady=6, pady=(4, 0))

                key_entry.bind("<Return>", lambda e: _do_login())

                def _on_close():
                    result["passed"] = False
                    root.destroy()

                root.protocol("WM_DELETE_WINDOW", _on_close)
                root.mainloop()

                if not result["passed"]:
                    print("[LICENSE] 激活失败或取消，退出程序")
                    sys.exit(0)
                    
            except Exception as e:
                print(f"[LICENSE] 激活窗口异常: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(0)
                
        elif status == "expired":
            # 卡密已过期
            print(f"[LICENSE] 卡密已过期，需要重新激活")
            # 递归调用自己（重新启动以弹出激活窗口）
            import subprocess
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
            
        else:  # status == "valid"
            # 有效的卡密，再次在线验证
            print(f"[LICENSE] 找到已保存的卡密，验证中...")
            license_key = info.get("license_key", "")
            if license_key:
                ok, msg = lic.validate_online(license_key)
                if not ok:
                    print(f"[LICENSE] 激活验证失败: {msg}")
                    # 清除旧卡密，重新启动
                    lic._clear_local()
                    import subprocess
                    subprocess.Popen([sys.executable] + sys.argv)
                    sys.exit(0)
                print("[LICENSE] 激活验证通过 ✓")
            else:
                print("[LICENSE] 卡密信息异常，重新激活")
                lic._clear_local()
                import subprocess
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit(0)
            
    except Exception as e:
        print(f"[LICENSE] 激活检查异常: {e}")
        import traceback
        traceback.print_exc()
        # 激活检查异常时退出，避免未授权使用
        sys.exit(1)

    # ── 激活通过后，启动服务和初始化窗口 ─────────────────
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda s, f: cleanup())

    threading.Thread(target=start_gradio,    daemon=True).start()
    threading.Thread(target=wait_for_gradio, daemon=True).start()

    try:
        root, status_var = build_splash()
        run_splash(root, status_var)
        try: root.destroy()
        except Exception: pass
    except Exception:
        pass

    if _gradio_url is None:
        _gradio_url = 'http://127.0.0.1:7870'

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
        except Exception:
            show_error_window("pywebview 安装失败", traceback.format_exc())
            cleanup()

    try:
        debug_mode = ENV_CONFIG['DEBUG_MODE']

        # logo.ico：优先使用已有 ico，否则从 logo.jpg 生成
        icon_path = os.path.join(BASE_DIR, "logo.ico")
        if not os.path.exists(icon_path):
            logo_jpg = os.path.join(BASE_DIR, "logo.jpg")
            if os.path.exists(logo_jpg):
                try:
                    from PIL import Image
                    Image.open(logo_jpg).save(icon_path, format='ICO', sizes=[(256,256),(64,64),(32,32),(16,16)])
                    print(f"[ICON] 已生成 logo.ico")
                except Exception as e:
                    print(f"[ICON] 生成 ico 失败: {e}")
                    icon_path = None
            else:
                icon_path = None

        window = webview.create_window(
            title='织梦AI大模型 - 专业版',
            url=_gradio_url,
            js_api=_api,
            width=1480, height=940, resizable=True,
            min_size=(1200, 800), text_select=True, easy_drag=False,
        )
        _webview_win[0] = window

        # 设置窗口图标（异步，窗口创建后）
        def _set_icon_later():
            time.sleep(2.0)   # 等待 webview 渲染引擎初始化
            ico = os.path.join(BASE_DIR, "logo.ico")
            hwnd = _get_main_hwnd()
            print(f"[ICON] 设置图标 hwnd={hwnd} ico_exists={os.path.exists(ico) if ico else False}")
            if hwnd and os.path.exists(ico):
                try:
                    import ctypes
                    u32 = ctypes.windll.user32
                    WM_SETICON      = 0x0080
                    IMAGE_ICON      = 1
                    LR_LOADFROMFILE = 0x10
                    hs = u32.LoadImageW(None, ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    hb = u32.LoadImageW(None, ico, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                    u32.SendMessageW(hwnd, WM_SETICON, 0, hs)   # ICON_SMALL
                    u32.SendMessageW(hwnd, WM_SETICON, 1, hb)   # ICON_BIG
                    print(f"[ICON] ✓ 图标设置成功")
                except Exception as e:
                    print(f"[ICON] ✗ {e}")

        threading.Thread(target=_set_icon_later, daemon=True).start()

        # 拦截 X 按钮 - 改进：无论页面是否加载成功都能弹出确认对话框
        def on_closing():
            def _show_confirm():
                try:
                    # 先尝试通过 JS 显示自定义对话框
                    window.evaluate_js("window._zm && window._zm.show()")
                except Exception:
                    # JS 注入失败（页面未加载或出错），使用系统对话框
                    try:
                        import tkinter as tk
                        from tkinter import messagebox
                        
                        # 创建隐藏的根窗口
                        root = tk.Tk()
                        root.withdraw()
                        root.attributes('-topmost', True)
                        
                        # 显示确认对话框
                        result = messagebox.askyesnocancel(
                            "关闭程序",
                            "选择操作：\n\n"
                            "「是」- 最小化到通知区域（后台运行）\n"
                            "「否」- 退出程序\n"
                            "「取消」- 返回",
                            icon='question'
                        )
                        
                        root.destroy()
                        
                        if result is True:  # 是 - 最小化
                            try:
                                hwnd = _get_main_hwnd()
                                if hwnd:
                                    import ctypes
                                    ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
                            except Exception:
                                pass
                        elif result is False:  # 否 - 退出
                            cleanup()
                        # None - 取消，什么都不做
                        
                    except Exception as e:
                        print(f"[CLOSE] 对话框异常: {e}")
                        # 最后的保底：直接退出
                        cleanup()
            
            threading.Thread(target=_show_confirm, daemon=True).start()
            return False

        window.events.closing += on_closing

        # 单实例激活监听
        def activation_listener():
            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(('127.0.0.1', 17871))
                srv.listen(1)
                srv.settimeout(1.0)
                print("[ACTIVATE] 监听已启动")
                while True:
                    try:
                        conn, _ = srv.accept()
                        if conn.recv(1024) == b'ACTIVATE':
                            hwnd = _get_main_hwnd()
                            if hwnd:
                                try:
                                    import ctypes
                                    ctypes.windll.user32.ShowWindow(hwnd, 9)
                                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                                except Exception:
                                    pass
                            try: window.show()
                            except Exception: pass
                        conn.close()
                    except socket.timeout:
                        continue
                    except Exception:
                        break
            except Exception as e:
                print(f"[ACTIVATE] 异常: {e}")

        threading.Thread(target=activation_listener, daemon=True).start()

        webview.start(debug=debug_mode)

    except Exception:
        show_error_window("WebView 启动失败", traceback.format_exc())

    cleanup()