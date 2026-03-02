# -*- coding: utf-8 -*-
# app_backend.py — 由 launcher.exe 通过 python.exe 调用
#
# 架构：
#   1. 立即显示 tkinter 启动画面
#   2. 后台线程：启动 Gradio 子进程
#   3. 后台线程：轮询端口，就绪后通知主线程退出 mainloop
#   4. 主线程：销毁 tkinter → 调用 webview.start()

import os, sys, time, socket, threading, subprocess, signal, traceback
import ctypes
import json

# ── 全局崩溃处理器（必须在所有其他代码之前设置）──
# 确保任何未捕获的异常都写入 logs/crash.log，不会被静默吞掉
def _install_crash_handler():
    _base = os.path.dirname(os.path.abspath(__file__))
    _log_dir = os.path.join(_base, "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _crash_log = os.path.join(_log_dir, "crash.log")

    def _handler(exc_type, exc_value, exc_tb):
        try:
            with open(_crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"CRASH at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Python: {sys.executable}\n")
                f.write(f"Script: {__file__}\n")
                f.write(f"CWD: {os.getcwd()}\n")
                f.write(f"sys.path: {sys.path[:5]}\n")
                f.write(f"{'='*60}\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
                f.write("\n")
                f.flush()
        except Exception:
            pass
        # 同时输出到 stderr（会被 launcher 捕获到 backend_startup.log）
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _handler

_install_crash_handler()

# ── 启动诊断（输出到 stdout → launcher 会捕获到 backend_startup.log）──
# 注意：pythonw.exe 下 sys.stdout 是 None，需要安全处理
def _safe_print(msg):
    try:
        if sys.stdout:
            print(msg)
            sys.stdout.flush()
    except Exception:
        pass

_safe_print(f"[BOOT] app_backend 启动中...")
_safe_print(f"[BOOT] Python: {sys.executable}")
_safe_print(f"[BOOT] 版本: {sys.version}")
_safe_print(f"[BOOT] 脚本: {__file__}")
_safe_print(f"[BOOT] CWD: {os.getcwd()}")
_safe_print(f"[BOOT] BASE_DIR: {os.path.dirname(os.path.abspath(__file__))}")

# ── 单实例保护（mutex 在进程存活期间持有）──
_APP_MUTEX = None
def _ensure_single_instance():
    global _APP_MUTEX
    if sys.platform != "win32":
        return True
    _APP_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\ZhiMoAI_AppBackend_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.kernel32.CloseHandle(_APP_MUTEX)
        _APP_MUTEX = None
        return False
    return True

if not _ensure_single_instance():
    sys.exit(0)

try:
    import urllib.request
    import urllib.error
except ImportError:
    urllib = None

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR = os.path.join(BASE_DIR, "_internal_tts")

# ── 将 libs/ 加入模块搜索路径（lib_*.py 已移动到 libs/）──
_LIBS_DIR = os.path.join(BASE_DIR, "libs")
if _LIBS_DIR not in sys.path:
    sys.path.insert(0, _LIBS_DIR)

PLATFORM_AI_AGREEMENT_FILE = os.path.join(BASE_DIR, "docs", "user_agreement.md")
if not os.path.exists(PLATFORM_AI_AGREEMENT_FILE):
    PLATFORM_AI_AGREEMENT_FILE = os.path.join(BASE_DIR, "user_agreement.md")


def has_local_tts_content():
    """检测 _internal_tts 文件夹是否有可用的 TTS 模型内容
    
    Returns:
        bool: True 表示有内容可用本地版，False 表示只能用在线版
    """
    if not os.path.exists(INDEXTTS_DIR):
        return False
    
    # 检查关键目录和文件是否存在
    checkpoints_dir = os.path.join(INDEXTTS_DIR, "checkpoints")
    if not os.path.exists(checkpoints_dir):
        return False
    
    # 检查 checkpoints 目录是否有内容（至少有几个文件或子目录）
    try:
        contents = os.listdir(checkpoints_dir)
        # 需要至少有一些内容（模型文件、config.yaml 等）
        if len(contents) < 2:
            return False
        
        # 检查是否有 config.yaml（TTS 模型的关键配置文件）
        config_path = os.path.join(checkpoints_dir, "config.yaml")
        if not os.path.exists(config_path):
            return False
        
        return True
    except Exception as e:
        print(f"[TTS检测] 检查 _internal_tts 内容失败: {e}")
        return False

LEGACY_PLATFORM_AGREEMENT_FILE = os.path.join(BASE_DIR, "platform_publish_agreement.txt")
LEGACY_DOUYIN_AGREEMENT_FILE = os.path.join(BASE_DIR, "user_agreement.md")

# ── 配置文件路径（与 unified_app.py 保持一致）──
_CONFIG_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ZhiMoAI')
_CONFIG_FILE = os.path.join(_CONFIG_DIR, 'config.dat')


def _read_all_config():
    """读取 config.dat + .env（开发覆盖），返回合并 dict"""
    cfg = {}
    # 1) config.dat（主配置）
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip()
        except Exception:
            pass
    # 2) .env（开发覆盖，优先级更高；打包后不存在则跳过）
    env_file = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip()
        except Exception:
            pass
    return cfg


# 从统一接口读取版本信息
try:
    from libs.app_version import get_app_version
    CURRENT_VERSION, CURRENT_BUILD = get_app_version(BASE_DIR)
except Exception as _e:
    CURRENT_VERSION, CURRENT_BUILD = ("2.3.9", 239)
UPDATE_CHECK_URL = "https://api.zhimengai.xyz/api/update/Dspcheck"

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
#  更新检查
# ══════════════════════════════════════════════════════════════
def check_for_updates():
    """检查更新，返回 (has_update, update_info, error_msg)"""
    if not urllib:
        return False, None, "网络模块未加载"
    
    try:
        print(f"[UPDATE] 连接更新服务器: {UPDATE_CHECK_URL}")
        req = urllib.request.Request(
            UPDATE_CHECK_URL,
            headers={
                'User-Agent': 'ZhiMoAI/1.0',
                'Accept': 'application/json'
            }
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            raw_data = response.read().decode('utf-8')
            print(f"[UPDATE] 服务器响应: {raw_data[:200]}")
            data = json.loads(raw_data)
            
        # 解析返回数据
        remote_version = data.get("version", "")
        remote_build = int(data.get("build", 0))
        download_url = data.get("url", "")
        force_update = data.get("force", False)
        description = data.get("desc", "")
        
        print(f"[UPDATE] 远程版本: {remote_version} (Build {remote_build})")
        print(f"[UPDATE] 当前版本: {CURRENT_VERSION} (Build {CURRENT_BUILD})")
        
        # 比较版本号（使用build号）
        if remote_build > CURRENT_BUILD:
            print(f"[UPDATE] 发现新版本")
            return True, {
                "version": remote_version,
                "build": remote_build,
                "url": download_url,
                "force": force_update,
                "desc": description
            }, None
        
        print(f"[UPDATE] 当前已是最新版本")
        return False, None, None
        
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP错误 {e.code}: {e.reason}"
        print(f"[UPDATE] {error_msg}")
        return False, None, error_msg
    except urllib.error.URLError as e:
        error_msg = f"网络连接失败: {e.reason}"
        print(f"[UPDATE] {error_msg}")
        return False, None, error_msg
    except json.JSONDecodeError as e:
        error_msg = f"数据解析失败: {e}"
        print(f"[UPDATE] {error_msg}")
        return False, None, error_msg
    except Exception as e:
        error_msg = f"检查更新失败: {e}"
        print(f"[UPDATE] {error_msg}")
        return False, None, error_msg


def _download_with_resume(url, dest_path, progress_callback=None, cancel_flag=None):
    """从 OSS 下载文件，支持断点续传
    
    Args:
        url: 下载地址（阿里云 OSS 直链）
        dest_path: 保存路径
        progress_callback: 回调函数 (downloaded_bytes, total_bytes)
        cancel_flag: dict {"cancel": bool}，设为 True 可取消下载
    Returns:
        (success: bool, error_msg: str|None)
    """
    tmp_path = dest_path + ".downloading"
    downloaded = 0
    
    # 检查已有的临时文件（断点续传）
    if os.path.exists(tmp_path):
        downloaded = os.path.getsize(tmp_path)
        print(f"[DOWNLOAD] 发现未完成下载，已下载 {downloaded} 字节，继续下载...")
    
    headers = {
        'User-Agent': 'ZhiMoAI/1.0',
    }
    if downloaded > 0:
        headers['Range'] = f'bytes={downloaded}-'
    
    try:
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=30)
        
        # 获取文件总大小
        if downloaded > 0 and response.status == 206:
            # 断点续传成功
            content_range = response.headers.get('Content-Range', '')
            if '/' in content_range:
                total_size = int(content_range.split('/')[-1])
            else:
                total_size = downloaded + int(response.headers.get('Content-Length', 0))
        elif response.status == 200:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0  # 服务器不支持断点续传，重新下载
        else:
            return False, f"HTTP 状态码异常: {response.status}"
        
        print(f"[DOWNLOAD] 文件总大小: {total_size} 字节")
        
        # 写入文件
        mode = 'ab' if downloaded > 0 else 'wb'
        chunk_size = 64 * 1024  # 64KB
        
        with open(tmp_path, mode) as f:
            while True:
                if cancel_flag and cancel_flag.get("cancel"):
                    print("[DOWNLOAD] 用户取消下载")
                    return False, "下载已取消"
                
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                
                f.write(chunk)
                downloaded += len(chunk)
                
                if progress_callback:
                    progress_callback(downloaded, total_size)
        
        response.close()
        
        # 验证下载完成
        if total_size > 0 and downloaded < total_size:
            return False, f"下载不完整: {downloaded}/{total_size}"
        
        # 重命名为正式文件
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(tmp_path, dest_path)
        
        print(f"[DOWNLOAD] 下载完成: {dest_path}")
        return True, None
        
    except urllib.error.HTTPError as e:
        return False, f"HTTP 错误 {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"网络连接失败: {e.reason}"
    except Exception as e:
        return False, f"下载失败: {e}"


def show_update_dialog(update_info, is_force):
    """显示更新对话框，支持从 OSS 直接下载并显示进度"""
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    
    result = {"action": "cancel"}
    cancel_flag = {"cancel": False}
    
    dialog = tk.Tk()
    dialog.title("织梦AI - 发现新版本")
    dialog.resizable(False, False)
    
    # 设置图标
    try:
        icon_path = os.path.join(BASE_DIR, "logo.ico")
        if os.path.exists(icon_path):
            dialog.iconbitmap(icon_path)
    except Exception:
        pass
    
    # 窗口大小和居中
    w, h = 520, 480
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    
    # 背景色
    dialog.configure(bg="#f8fafc")
    
    # 标题区域
    title_frame = tk.Frame(dialog, bg="#3b82f6", height=80)
    title_frame.pack(fill="x")
    title_frame.pack_propagate(False)
    
    tk.Label(
        title_frame,
        text="🎉 发现新版本",
        font=("Microsoft YaHei", 18, "bold"),
        bg="#3b82f6",
        fg="#ffffff"
    ).pack(pady=20)
    
    # 内容区域
    content_frame = tk.Frame(dialog, bg="#f8fafc")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # 版本信息
    info_frame = tk.Frame(content_frame, bg="#ffffff", relief="solid", bd=1)
    info_frame.pack(fill="x", pady=(0, 10))
    
    tk.Label(
        info_frame,
        text=f"当前版本: {CURRENT_VERSION} (Build {CURRENT_BUILD})",
        font=("Microsoft YaHei", 10),
        bg="#ffffff",
        fg="#64748b",
        anchor="w"
    ).pack(fill="x", padx=15, pady=(10, 5))
    
    tk.Label(
        info_frame,
        text=f"最新版本: {update_info['version']} (Build {update_info['build']})",
        font=("Microsoft YaHei", 10, "bold"),
        bg="#ffffff",
        fg="#3b82f6",
        anchor="w"
    ).pack(fill="x", padx=15, pady=(0, 10))
    
    # 更新说明
    tk.Label(
        content_frame,
        text="更新内容：",
        font=("Microsoft YaHei", 10, "bold"),
        bg="#f8fafc",
        fg="#1e293b",
        anchor="w"
    ).pack(fill="x", pady=(0, 5))
    
    desc_box = scrolledtext.ScrolledText(
        content_frame,
        font=("Microsoft YaHei", 9),
        bg="#ffffff",
        fg="#334155",
        wrap="word",
        height=6,
        relief="solid",
        bd=1
    )
    desc_box.pack(fill="both", expand=True)
    desc_box.insert("1.0", update_info.get("desc", "暂无更新说明"))
    desc_box.configure(state="disabled")
    
    # 强制更新提示
    if is_force:
        warning_frame = tk.Frame(content_frame, bg="#fef2f2", relief="solid", bd=1)
        warning_frame.pack(fill="x", pady=(10, 0))
        
        tk.Label(
            warning_frame,
            text="[警告] 此版本为强制更新，必须更新后才能继续使用",
            font=("Microsoft YaHei", 9, "bold"),
            bg="#fef2f2",
            fg="#dc2626"
        ).pack(pady=8)
    
    # ── 下载进度区域（初始隐藏） ──
    progress_frame = tk.Frame(content_frame, bg="#f8fafc")
    # 不 pack，下载时才显示
    
    progress_label = tk.Label(
        progress_frame,
        text="准备下载...",
        font=("Microsoft YaHei", 9),
        bg="#f8fafc",
        fg="#475569",
        anchor="w"
    )
    progress_label.pack(fill="x", pady=(5, 2))
    
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Update.Horizontal.TProgressbar",
                    troughcolor="#e2e8f0", background="#3b82f6",
                    bordercolor="#e2e8f0", lightcolor="#3b82f6", darkcolor="#3b82f6")
    
    progress_bar = ttk.Progressbar(
        progress_frame,
        style="Update.Horizontal.TProgressbar",
        mode="determinate",
        maximum=100
    )
    progress_bar.pack(fill="x", pady=(0, 5))
    
    speed_label = tk.Label(
        progress_frame,
        text="",
        font=("Microsoft YaHei", 8),
        bg="#f8fafc",
        fg="#94a3b8",
        anchor="w"
    )
    speed_label.pack(fill="x")
    
    # ── 按钮区域 ──
    button_frame = tk.Frame(dialog, bg="#f8fafc")
    button_frame.pack(fill="x", padx=20, pady=(0, 20))
    
    def _format_size(size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024*1024):.1f} MB"
        else:
            return f"{size_bytes / (1024*1024*1024):.2f} GB"
    
    _dl_state = {"last_time": 0, "last_bytes": 0}
    
    def _on_progress(downloaded, total):
        """下载进度回调（在下载线程中调用）"""
        if total > 0:
            pct = min(100, downloaded * 100.0 / total)
        else:
            pct = 0
        
        now = time.time()
        speed_text = ""
        if _dl_state["last_time"] > 0:
            dt = now - _dl_state["last_time"]
            if dt > 0.5:  # 每 0.5 秒更新一次速度
                speed = (downloaded - _dl_state["last_bytes"]) / dt
                speed_text = f"速度: {_format_size(int(speed))}/s"
                _dl_state["last_time"] = now
                _dl_state["last_bytes"] = downloaded
        else:
            _dl_state["last_time"] = now
            _dl_state["last_bytes"] = downloaded
        
        # 使用 after 在主线程更新 UI
        def _update_ui():
            try:
                progress_bar["value"] = pct
                progress_label.configure(
                    text=f"下载中: {_format_size(downloaded)} / {_format_size(total)}  ({pct:.1f}%)"
                )
                if speed_text:
                    speed_label.configure(text=speed_text)
            except tk.TclError:
                pass
        
        try:
            dialog.after(0, _update_ui)
        except Exception:
            pass
    
    def _do_download():
        """在后台线程中执行下载"""
        import tempfile
        
        url = update_info["url"]
        # 从 URL 中提取文件名
        filename = "download"
        if '/file=' in update_info["url"]:
            raw = update_info["url"].split('/file=', 1)[1]
            raw = urllib.parse.unquote(raw)
            filename = os.path.basename(raw)
        
        ext = os.path.splitext(filename)[1].lower() or '.mp4'
        
        # 下载到用户临时目录
        download_dir = os.path.join(tempfile.gettempdir(), "ZhiMoAI_Updates")
        os.makedirs(download_dir, exist_ok=True)
        dest_path = os.path.join(download_dir, filename)
        
        print(f"[DOWNLOAD] 开始下载: {url}")
        print(f"[DOWNLOAD] 保存到: {dest_path}")
        
        success, error_msg = _download_with_resume(
            url, dest_path,
            progress_callback=_on_progress,
            cancel_flag=cancel_flag
        )
        
        def _on_complete():
            try:
                if success:
                    progress_label.configure(text="✅ 下载完成！正在安装...")
                    speed_label.configure(text="")
                    progress_bar["value"] = 100
                    download_btn.configure(text="安装中...", state="disabled")
                    if not is_force:
                        later_btn.configure(state="disabled")
                    
                    # 在主线程中执行安装（延迟1秒）
                    def do_install():
                        print(f"[UPDATE] 开始执行安装...")
                        _install_update(dest_path)
                    
                    dialog.after(1000, do_install)
                else:
                    if cancel_flag.get("cancel"):
                        progress_label.configure(text="下载已取消")
                    else:
                        progress_label.configure(text=f"❌ {error_msg}")
                        # 允许重试
                        download_btn.configure(text="重新下载", state="normal",
                                               command=on_download)
                    speed_label.configure(text="")
                    if not is_force:
                        later_btn.configure(state="normal")
            except tk.TclError:
                pass
        
        try:
            dialog.after(0, _on_complete)
        except Exception:
            pass
    
    def _install_update(file_path):
        """运行安装程序并退出当前程序"""
        result["action"] = "install"
        
        print(f"[UPDATE] 准备安装: {file_path}")
        print(f"[UPDATE] 文件是否存在: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            print(f"[UPDATE] 错误：安装文件不存在")
            try:
                messagebox.showerror("错误", f"安装文件不存在:\n{file_path}")
            except Exception:
                pass
            return
        
        # 创建重启脚本
        import tempfile
        restart_script = os.path.join(tempfile.gettempdir(), "zhimoai_restart.bat")
        
        # 获取安装目录
        install_dir = os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'ZhiMoAI')
        bat_path = os.path.join(install_dir, '启动应用.bat')
        log_path = os.path.join(tempfile.gettempdir(), "zhimoai_restart.log")
        
        script_content = f'''@echo off
echo [%date% %time%] 重启脚本开始 >> "{log_path}"

echo 等待安装完成...
timeout /t 8 /nobreak >nul

echo [%date% %time%] 检查安装目录: {install_dir} >> "{log_path}"
echo [%date% %time%] 检查bat文件: {bat_path} >> "{log_path}"

if exist "{bat_path}" (
    echo [%date% %time%] 找到bat文件，准备启动 >> "{log_path}"
    cd /d "{install_dir}"
    start "" "{bat_path}"
    echo [%date% %time%] 已执行启动命令 >> "{log_path}"
) else (
    echo [%date% %time%] 错误：bat文件不存在 >> "{log_path}"
)

timeout /t 2 /nobreak >nul
del "%~f0"
'''
        
        try:
            with open(restart_script, 'w', encoding='gbk') as f:
                f.write(script_content)
            print(f"[UPDATE] 重启脚本已创建: {restart_script}")
            print(f"[UPDATE] 日志文件: {log_path}")
        except Exception as e:
            print(f"[UPDATE] 创建重启脚本失败: {e}")
        
        try:
            # 启动重启脚本（先启动，避免程序退出后无法执行）
            if os.path.exists(restart_script):
                print(f"[UPDATE] 启动重启脚本...")
                # 直接使用cmd.exe执行bat文件，不使用shell=True
                subprocess.Popen(
                    ['cmd.exe', '/c', restart_script],
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
                    close_fds=True
                )
                print(f"[UPDATE] 重启脚本已启动")
                print(f"[UPDATE] 可以查看日志: {log_path}")
            
            # 启动安装程序（静默安装）
            print(f"[UPDATE] 启动安装程序...")
            subprocess.Popen(
                [file_path, "/SILENT", "/CLOSEAPPLICATIONS"],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            print(f"[UPDATE] 安装程序已启动")
            
        except Exception as e:
            print(f"[UPDATE] 启动失败: {e}")
            try:
                # 如果失败，尝试普通安装
                print(f"[UPDATE] 尝试普通安装...")
                os.startfile(file_path)
                print(f"[UPDATE] 普通安装程序已启动")
            except Exception as e2:
                print(f"[UPDATE] 普通安装也失败: {e2}")
                try:
                    messagebox.showerror("错误", f"启动安装程序失败:\n{e}\n\n文件位置:\n{file_path}")
                except Exception:
                    pass
                return
        
        # 关闭对话框并退出程序
        print(f"[UPDATE] 关闭更新对话框...")
        _safe_close_dialog()
        
        # 延迟退出，确保安装程序和重启脚本已启动
        print(f"[UPDATE] 程序将在2秒后退出...")
        time.sleep(2)
        print(f"[UPDATE] 退出当前程序")
        os._exit(0)
    
    def on_download():
        """点击下载按钮"""
        cancel_flag["cancel"] = False
        _dl_state["last_time"] = 0
        _dl_state["last_bytes"] = 0
        
        # 显示进度区域
        progress_frame.pack(fill="x", pady=(10, 0))
        progress_label.configure(text="正在连接服务器...")
        progress_bar["value"] = 0
        speed_label.configure(text="")
        
        # 禁用按钮
        download_btn.configure(text="下载中...", state="disabled")
        later_btn.configure(text="取消下载", state="normal",
                            command=on_cancel_download)
        
        # 启动下载线程
        threading.Thread(target=_do_download, daemon=True).start()
    
    def on_cancel_download():
        """取消下载"""
        cancel_flag["cancel"] = True
        later_btn.configure(state="disabled")
    
    def _safe_close_dialog():
        """安全关闭更新对话框"""
        try:
            dialog.quit()
            dialog.destroy()
        except Exception:
            pass
    
    def on_later():
        if not is_force:
            result["action"] = "later"
            cancel_flag["cancel"] = True
            _safe_close_dialog()
    
    def on_exit():
        result["action"] = "exit"
        cancel_flag["cancel"] = True
        _safe_close_dialog()
        # 确保退出（防止 mainloop 未正确结束）
        try:
            os._exit(0)
        except Exception:
            pass
    
    # 下载按钮
    download_btn = tk.Button(
        button_frame,
        text="⬇ 下载更新",
        command=on_download,
        font=("Microsoft YaHei", 10, "bold"),
        bg="#3b82f6",
        fg="#ffffff",
        bd=0,
        padx=20,
        pady=10,
        cursor="hand2",
        activebackground="#2563eb",
        activeforeground="#ffffff"
    )
    download_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
    
    # 稍后/退出按钮
    if is_force:
        later_btn = tk.Button(
            button_frame,
            text="退出程序",
            command=on_exit,
            font=("Microsoft YaHei", 10),
            bg="#e2e8f0",
            fg="#475569",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            activebackground="#cbd5e1",
            activeforeground="#334155"
        )
    else:
        later_btn = tk.Button(
            button_frame,
            text="稍后更新",
            command=on_later,
            font=("Microsoft YaHei", 10),
            bg="#e2e8f0",
            fg="#475569",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            activebackground="#cbd5e1",
            activeforeground="#334155"
        )
    later_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))
    
    # 如果是强制更新，禁止关闭窗口
    if is_force:
        dialog.protocol("WM_DELETE_WINDOW", on_exit)
    else:
        dialog.protocol("WM_DELETE_WINDOW", on_later)
    
    dialog.mainloop()
    
    return result["action"]


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
                    print(f"[API] [OK] 窗口已隐藏至托盘 (hwnd={hwnd})")
                except Exception as e:
                    print(f"[API] ctypes 失败: {e}")
                    # 兜底：尝试 pywebview 原生
                    w = _webview_win[0]
                    if w:
                        try: w.minimize()
                        except Exception: pass
            else:
                print("[API] [ERROR] 未找到主窗口 HWND，等待后重试...")
                time.sleep(1.5)
                hwnd2 = _get_main_hwnd()
                if hwnd2:
                    try:
                        import ctypes
                        ctypes.windll.user32.ShowWindow(hwnd2, 0)
                        print(f"[API] [OK] 重试成功 (hwnd={hwnd2})")
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

    def save_download_file(self, gradio_file_url):
        """下载 Gradio 文件并弹出另存为对话框"""
        def _do():
            try:
                import urllib.request, urllib.parse
                from tkinter import Tk, filedialog
                
                # 从 URL 提取原始文件名
                # Gradio URL 格式: /file=C:\...\lipsync_xxx.mp4
                fname = "download"
                if '/file=' in gradio_file_url:
                    raw = gradio_file_url.split('/file=', 1)[1]
                    raw = urllib.parse.unquote(raw)
                    fname = os.path.basename(raw)
                
                ext = os.path.splitext(fname)[1].lower() or '.mp4'
                
                # 弹出另存为对话框
                root = Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                save_path = filedialog.asksaveasfilename(
                    parent=root,
                    title='保存文件',
                    initialfile=fname,
                    defaultextension=ext,
                    filetypes=[
                        ('视频文件', '*.mp4 *.avi *.mkv *.mov'),
                        ('音频文件', '*.wav *.mp3 *.flac'),
                        ('所有文件', '*.*'),
                    ]
                )
                root.destroy()
                
                if not save_path:
                    print("[API] 用户取消保存")
                    return
                
                # 如果是本地文件路径，直接复制
                if '/file=' in gradio_file_url:
                    raw = gradio_file_url.split('/file=', 1)[1]
                    raw = urllib.parse.unquote(raw)
                    local_path = os.path.normpath(raw)
                    if os.path.exists(local_path):
                        import shutil
                        shutil.copy2(local_path, save_path)
                        print(f"[API] 文件已保存: {save_path}")
                        return
                
                # 否则通过 HTTP 下载
                print(f"[API] 下载文件: {gradio_file_url}")
                urllib.request.urlretrieve(gradio_file_url, save_path)
                print(f"[API] 文件已保存: {save_path}")
                
            except Exception as e:
                print(f"[API] save_download_file 失败: {e}")
        threading.Thread(target=_do, daemon=True).start()

    def open_file_location(self, file_path):
        """用资源管理器打开文件所在目录并选中文件"""
        def _do():
            try:
                fp = os.path.normpath(file_path)
                if os.path.exists(fp):
                    subprocess.Popen(["explorer", "/select,", fp],
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                    print(f"[API] 打开文件位置: {fp}")
                else:
                    print(f"[API] 文件不存在: {fp}")
            except Exception as e:
                print(f"[API] open_file_location 失败: {e}")
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
                        print(f"[TRAY] [OK] 窗口已恢复 (hwnd={hwnd})")
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
#  读取应用配置
# ══════════════════════════════════════════════════════════════
def load_env_config():
    config = {
        'DEBUG_MODE': False, 
        'SERVER_PORT_START': 7870, 
        'SERVER_PORT_END': 7874,
        'CHECK_UPDATE': True,  # 默认启用更新检查
        'TTS_MODE': 'local'  # TTS 模式：local 或 online（默认本地版）
    }
    try:
        cfg = _read_all_config()
        for key, value in cfg.items():
            if   key == 'DEBUG_MODE':          config['DEBUG_MODE'] = value.lower() in ('true','1','yes','on')
            elif key == 'SERVER_PORT_START':   config['SERVER_PORT_START'] = int(value)
            elif key == 'SERVER_PORT_END':     config['SERVER_PORT_END']   = int(value)
            elif key == 'CHECK_UPDATE':        config['CHECK_UPDATE'] = value.lower() in ('true','1','yes','on')
            elif key == 'TTS_MODE':            config['TTS_MODE'] = value
    except Exception:
        pass
    return config

ENV_CONFIG = load_env_config()



def _render_md_to_tk(text_widget, md_text):
    """将 Markdown 渲染到 tkinter Text widget（带格式标签）"""
    import re
    tw = text_widget

    # 定义样式 tag
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
        """去掉 markdown 行内标记，返回 (text, segments) 用于加粗渲染"""
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
        # 水平线
        if re.match(r'^\s*[\*\-_]{3,}\s*$', line):
            tw.insert("end", "━" * 60 + "\n", "hr")
            continue

        # 标题
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            title = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', m.group(2).strip())
            tag = "h1" if level == 1 else ("h2" if level == 2 else "h3")
            tw.insert("end", title + "\n", tag)
            continue

        # 空行
        if not line.strip():
            tw.insert("end", "\n")
            continue

        # 列表项（子级缩进）
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

        # 普通段落（支持行内加粗）
        segs = _strip_inline(line)
        for txt, is_bold in segs:
            tw.insert("end", txt, ("body", "bold") if is_bold else "body")
        tw.insert("end", "\n")


def _load_platform_ai_agreement_text():
    """加载用户协议原始 markdown 文本"""
    agreement_file = os.path.join(BASE_DIR, "docs", "user_agreement.md")
    if os.path.exists(agreement_file):
        try:
            with open(agreement_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception as e:
            print(f"[WARNING] 读取协议文件失败: {e}")
    return "用户协议文件 (user_agreement.md) 未找到，请联系技术支持。"


def _load_privacy_policy_text():
    """加载隐私协议原始 markdown 文本"""
    candidates = [
        os.path.join(BASE_DIR, "docs", "privacy_policy_total.md"),
        os.path.join(BASE_DIR, "docs", "privacy_policy.md"),
    ]
    for privacy_file in candidates:
        if os.path.exists(privacy_file):
            try:
                with open(privacy_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception as e:
                print(f"[WARNING] 读取隐私协议文件失败: {e}")
    return "隐私协议文件 (privacy_policy_total.md / privacy_policy.md) 未找到，请联系技术支持。"

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
    tk.Label(err, text=f"[警告]  {title}", font=("Microsoft YaHei", 12, "bold"),
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
    
    # 搜索 Python 解释器（与 launcher.py 保持一致的搜索路径）
    python_candidates = [
        os.path.join(INDEXTTS_DIR, "installer_files", "env", "Scripts", "python.exe"),
        os.path.join(INDEXTTS_DIR, "installer_files", "env", "python.exe"),
        os.path.join(BASE_DIR, "IndexTTS2-SonicVale", "installer_files", "env", "Scripts", "python.exe"),
        os.path.join(BASE_DIR, "IndexTTS2-SonicVale", "installer_files", "env", "python.exe"),
    ]
    python_path = None
    for p in python_candidates:
        if os.path.exists(p):
            python_path = p
            print(f"[GRADIO] 找到 Python: {p}")
            break
    
    # 优先查找.py文件（开发模式），如果不存在则查找.pyc（打包模式）
    script_candidates = [
        # 开发模式 - .py文件
        os.path.join(BASE_DIR, "app_ui_optimized_with_agreement_file.py"),
        os.path.join(BASE_DIR, "unified_app.py"),
        # 打包模式 - .pyc文件
        os.path.join(BASE_DIR, "app_ui_optimized_with_agreement_file.pyc"),
        os.path.join(BASE_DIR, "unified_app.pyc"),
    ]
    script_path = next((p for p in script_candidates if os.path.exists(p)), None)
    
    if not python_path:
        tried = "\n".join(f"  - {p}" for p in python_candidates)
        _notify_error("Python 解释器未找到",
                      f"在以下路径均未找到 python.exe：\n{tried}\n\n"
                      f"BASE_DIR: {BASE_DIR}\n"
                      f"请确保 _internal_tts 文件夹已正确安装。")
        return
    if not script_path:
        _notify_error("主程序未找到", "未找到可启动的主程序文件（unified_app.py / .pyc）"); return

    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    log_path = os.path.join(BASE_DIR, "logs", "gradio_error.log")
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
    for txt in ["🔒 本地运行 · 数据安全", "·", f"v{CURRENT_VERSION} (Build {CURRENT_BUILD})"]:
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
    c.create_oval(2, 2, 50, 50, fill="", outline="#a78bfa", width=1, dash=(5, 3))
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
    print("[MAIN] 进入主入口")
    if sys.stdout:
        sys.stdout.flush()

    def _try_activate_existing_instance(retries: int = 30, delay_s: float = 0.2) -> bool:
        """尝试激活已运行实例，避免重复启动多个窗口。"""
        for _ in range(max(1, retries)):
            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.8)
                s.connect(('127.0.0.1', 17871))
                s.sendall(b'ACTIVATE')
                return True
            except Exception:
                time.sleep(delay_s)
            finally:
                try:
                    if s:
                        s.close()
                except Exception:
                    pass
        return False

    # ── 单实例检查 ─────────────────────────────────────────
    print("[MAIN] 开始单实例检查...")
    if sys.stdout:
        sys.stdout.flush()
    _lock_socket = None
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        _lock_socket.bind(('127.0.0.1', 17870))
        print("[LOCK] 单实例锁已获取")
    except OSError:
        print("[LOCK] 程序已在运行，尝试激活现有窗口...")
        if _try_activate_existing_instance():
            print("[LOCK] 已激活现有窗口，当前进程退出")
            sys.exit(0)

        # 激活失败时直接退出，避免继续创建新实例导致多窗口堆积
        print("[LOCK] 未能激活现有窗口，为避免重复实例，当前进程退出")
        sys.exit(0)

    print("[MAIN] 单实例检查通过")
    if sys.stdout:
        sys.stdout.flush()

    # ── 立即启动后台服务（越早越好，与更新检查/登录并行加载）──
    print("[BOOT] 立即启动后台服务...")
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda s, f: cleanup())
    threading.Thread(target=start_gradio, daemon=True).start()
    threading.Thread(target=wait_for_gradio, daemon=True).start()

    # ── 检查更新（Gradio 已在后台加载，缩短超时避免阻塞）──
    if ENV_CONFIG.get('CHECK_UPDATE', True):
        print("[UPDATE] 检查更新...")
        has_update, update_info, error_msg = check_for_updates()
        
        if error_msg:
            print(f"[UPDATE] {error_msg}")
        elif has_update:
            print(f"[UPDATE] 发现新版本: {update_info['version']} (Build {update_info['build']})")
            is_force = update_info.get("force", False)
            
            if is_force:
                print("[UPDATE] 强制更新，必须更新后才能继续")
            
            action = show_update_dialog(update_info, is_force)
            
            if action == "install":
                print("[UPDATE] 用户已安装更新，退出当前程序")
                sys.exit(0)
            elif action == "exit" or (is_force and action not in ("install", "later")):
                print("[UPDATE] 用户选择退出")
                sys.exit(0)
            # action == "later" 继续启动程序
        else:
            print("[UPDATE] 当前已是最新版本")
    else:
        print("[UPDATE] 更新检查已禁用")

    # ── 激活验证 ─────────────────────────────────────────
    print("[LICENSE] 开始激活验证...")
    
    try:
        sys.path.insert(0, BASE_DIR)
        import lib_license as lic
        
        # 检查本地保存的卡密状态
        status, info = lic.check_saved_license()
        
        # 无论什么状态，都弹出登录窗口
        print("[LICENSE] 弹出登录窗口...")
        try:
            import tkinter as tk
            from tkinter import ttk
            try:
                from PIL import Image, ImageTk, ImageDraw
            except ImportError as _pil_err:
                # PIL 损坏/缺失 → 自动修复
                print(f"[LICENSE] PIL 不可用({_pil_err})，尝试自动修复...")
                _fix_py = os.path.join(
                    INDEXTTS_DIR, "installer_files", "env", "Scripts", "python.exe"
                )
                if not os.path.exists(_fix_py):
                    _fix_py = os.path.join(
                        INDEXTTS_DIR, "installer_files", "env", "python.exe"
                    )
                try:
                    subprocess.run(
                        [_fix_py, "-m", "pip", "install", "--force-reinstall",
                         "Pillow>=10.0,<11.0", "--quiet"],
                        timeout=120,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )
                    from PIL import Image, ImageTk, ImageDraw
                    print("[LICENSE] PIL 自动修复成功")
                except Exception as _fix_err:
                    print(f"[LICENSE] PIL 自动修复失败: {_fix_err}")
                    raise _pil_err
            
            machine_code = lic.get_machine_code()
            result = {"passed": False}

            root = tk.Tk()
            root.title("织梦AI大模型 - 专业版")
            root.resizable(False, False)
            
            # 设置窗口图标
            try:
                icon_path = os.path.join(BASE_DIR, "logo.ico")
                if os.path.exists(icon_path):
                    root.iconbitmap(icon_path)
            except Exception:
                pass

            # 居中
            w, h = 560, 780  # 增加窗口高度保证按钮完整显示
            sx = (root.winfo_screenwidth() - w) // 2
            sy = (root.winfo_screenheight() - h) // 2
            root.geometry(f"{w}x{h}+{sx}+{sy}")

            # 创建渐变背景效果的画布
            canvas = tk.Canvas(root, width=w, height=h, highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            
            # 绘制精致的渐变背景（从深蓝紫到浅紫）
            for i in range(h):
                ratio = i / h
                # 从 #1e1b4b 到 #6366f1 的渐变
                r = int(30 + (99 - 30) * ratio)
                g = int(27 + (102 - 27) * ratio)
                b = int(75 + (241 - 75) * ratio)
                color = f'#{r:02x}{g:02x}{b:02x}'
                canvas.create_line(0, i, w, i, fill=color)
            
            # 添加装饰性几何图案
            # 左上角圆形
            canvas.create_oval(-80, -80, 120, 120, fill="", outline="#8b5cf6", width=2, dash=(10, 5))
            canvas.create_oval(-60, -60, 100, 100, fill="", outline="#a78bfa", width=1, dash=(5, 3))
            
            # 右下角圆形
            canvas.create_oval(w-120, h-120, w+80, h+80, fill="", outline="#8b5cf6", width=2, dash=(10, 5))
            canvas.create_oval(w-100, h-100, w+60, h+60, fill="", outline="#a78bfa", width=1, dash=(5, 3))
            
            # 顶部装饰线条
            for i in range(5):
                x1 = 80 + i * 100
                y1 = 50 + (i % 2) * 15
                x2 = x1 + 60
                y2 = y1
                canvas.create_line(x1, y1, x2, y2, fill="#c4b5fd", width=2, capstyle="round")

            # Logo 区域（带光晕效果）
            logo_y = 110
            
            # 外层光晕
            for r in range(70, 50, -5):
                alpha = int(255 * (70 - r) / 20)
                canvas.create_oval(w//2-r, logo_y-r, w//2+r, logo_y+r,
                                   fill="", outline="#c4b5fd", width=1, stipple="gray12")
            
            # Logo和标题已取消，节省空间
            # try:
            #     ...
            # except Exception:
            #     ...
            
            # 标题区域（简化版，只保留主标题）
            canvas.create_text(w//2, 80, text="织梦AI大模型", 
                               font=("Microsoft YaHei", 24, "bold"),
                               fill="#ffffff")
            
            canvas.create_text(w//2, 115, 
                               text="AI语音克隆 · 智能视频合成", 
                               font=("Microsoft YaHei", 10),
                               fill="#e9d5ff")
            
            # 版本号显示（右下角）
            version_text = f"v{CURRENT_VERSION} (Build {CURRENT_BUILD})"
            canvas.create_text(w - 20, h - 15, 
                               text=version_text,
                               font=("Microsoft YaHei", 9),
                               fill="#c4b5fd",
                               anchor="e")

            # 卡密输入区域（玻璃态卡片）
            card_y = 145
            card_h = 530  # 增大卡片高度保证内容完整
            
            # 卡片多层阴影效果
            canvas.create_rectangle(44, card_y+6, w-44, card_y+card_h+6,
                                    fill="#1e1b4b", outline="", stipple="gray25")
            canvas.create_rectangle(42, card_y+4, w-42, card_y+card_h+4,
                                    fill="#312e81", outline="")
            
            # 卡片主体（白色带透明感）
            canvas.create_rectangle(40, card_y, w-40, card_y+card_h,
                                    fill="#ffffff", outline="")
            
            # 卡片顶部装饰条
            canvas.create_rectangle(40, card_y, w-40, card_y+4,
                                    fill="#6366f1", outline="")
            
            # 卡片内容容器
            card_frame = tk.Frame(root, bg="#ffffff")
            card_frame.place(x=70, y=card_y+25, width=w-140, height=card_h-50)

            # 卡密标签（带图标）
            label_frame = tk.Frame(card_frame, bg="#ffffff")
            label_frame.pack(fill="x", pady=(0, 16))
            
            tk.Label(label_frame, text="[KEY]", 
                     font=("Microsoft YaHei", 12, "bold"),
                     bg="#ffffff", fg="#6366f1").pack(side="left", padx=(0, 8))
            tk.Label(label_frame, text="卡密激活", 
                     font=("Microsoft YaHei", 13, "bold"),
                     bg="#ffffff", fg="#1e293b").pack(side="left")
            
            # 装饰线
            canvas.create_line(70, card_y+60, w-70, card_y+60,
                               fill="#e5e7eb", width=1)
            
            # 版本选择（本地版/在线版）—— 同一行布局
            version_container = tk.Frame(card_frame, bg="#ffffff")
            version_container.pack(fill="x", pady=(0, 10))
            
            # 检测本地 TTS 是否可用
            _has_local_tts = has_local_tts_content()
            print(f"[LOGIN] 本地 TTS 模型检测: {'可用' if _has_local_tts else '不可用'}")
            
            # 根据 TTS 检测结果决定默认版本
            if _has_local_tts:
                saved_mode = ENV_CONFIG.get('TTS_MODE', 'local')
                default_version = saved_mode if saved_mode in ('local', 'online') else 'local'
            else:
                default_version = 'online'
            
            version_var = tk.StringVar(value=default_version)
            
            # 标签 + 两个单选按钮在同一行
            version_frame = tk.Frame(version_container, bg="#ffffff")
            version_frame.pack(fill="x")
            
            tk.Label(version_frame, text="TTS模式",
                     font=("Microsoft YaHei", 9),
                     bg="#ffffff", fg="#64748b").pack(side="left", padx=(0, 10))
            
            # 本地版选项
            local_text = "本地版" if _has_local_tts else "本地版(不可用)"
            local_fg = "#1e293b" if _has_local_tts else "#94a3b8"
            local_radio = tk.Radiobutton(
                version_frame,
                text=local_text,
                variable=version_var,
                value="local",
                font=("Microsoft YaHei", 10),
                bg="#ffffff",
                fg=local_fg,
                activebackground="#ffffff",
                activeforeground=local_fg,
                selectcolor="#ffffff",
                indicatoron=True,
                cursor="hand2" if _has_local_tts else "arrow",
                state="normal" if _has_local_tts else "disabled",
                disabledforeground="#94a3b8"
            )
            local_radio.pack(side="left", padx=(0, 16))
            
            # 在线版选项
            online_radio = tk.Radiobutton(
                version_frame,
                text="在线版",
                variable=version_var,
                value="online",
                font=("Microsoft YaHei", 10),
                bg="#ffffff",
                fg="#1e293b",
                activebackground="#ffffff",
                activeforeground="#1e293b",
                selectcolor="#ffffff",
                indicatoron=True,
                cursor="hand2"
            )
            online_radio.pack(side="left")
            
            # 如果没有本地 TTS，显示提示信息
            if not _has_local_tts:
                hint_label = tk.Label(
                    version_container,
                    text="⚠ 未检测到本地模型，仅可使用在线版",
                    font=("Microsoft YaHei", 8),
                    bg="#ffffff",
                    fg="#f59e0b"
                )
                hint_label.pack(anchor="w", pady=(4, 0))
            
            # 卡密输入框（现代风格）
            entry_container = tk.Frame(card_frame, bg="#ffffff")
            entry_container.pack(fill="x", pady=(0, 12))
            
            tk.Label(entry_container, text="请输入您的卡密", 
                     font=("Microsoft YaHei", 9),
                     bg="#ffffff", fg="#64748b").pack(anchor="w", pady=(0, 6))
            
            entry_frame = tk.Frame(entry_container, bg="#f8fafc", 
                                   highlightbackground="#cbd5e1", 
                                   highlightthickness=2)
            entry_frame.pack(fill="x")
            
            key_entry = tk.Entry(entry_frame, 
                                 font=("Consolas", 12), 
                                 relief="flat",
                                 bg="#f8fafc", 
                                 fg="#1e293b",
                                 insertbackground="#6366f1",
                                 bd=0)
            key_entry.pack(fill="x", padx=16, pady=12)
            
            # 输入框获得焦点时的效果
            def on_focus_in(e):
                entry_frame.config(highlightbackground="#6366f1", highlightthickness=2)
            def on_focus_out(e):
                entry_frame.config(highlightbackground="#cbd5e1", highlightthickness=2)
            key_entry.bind("<FocusIn>", on_focus_in)
            key_entry.bind("<FocusOut>", on_focus_out)
            
            # 如果有保存的卡密，预填
            if status == "valid" and info.get("license_key"):
                key_entry.insert(0, info["license_key"])
            
            # 状态提示（精美卡片）
            status_container = tk.Frame(card_frame, bg="#ffffff")
            status_container.pack(fill="x", pady=(0, 12))
            
            if status == "valid":
                expire_time = info.get("expire_time", "")
                status_bg = "#ecfdf5"
                status_border = "#6ee7b7"
                status_icon = "[OK]"
                status_icon_color = "#10b981"
                if expire_time:
                    status_text = f"已保存的卡密 · 有效期至 {expire_time}"
                else:
                    status_text = "已保存的卡密 · 永久有效"
                status_text_color = "#065f46"
            elif status == "expired":
                status_bg = "#fef3c7"
                status_border = "#fcd34d"
                status_icon = "[!]"
                status_icon_color = "#f59e0b"
                status_text = "卡密已过期，请重新输入"
                status_text_color = "#92400e"
            else:
                status_bg = "#eff6ff"
                status_border = "#93c5fd"
                status_icon = "ℹ"
                status_icon_color = "#3b82f6"
                status_text = "首次使用请输入卡密激活"
                status_text_color = "#1e40af"
            
            status_frame = tk.Frame(status_container, bg=status_bg,
                                    highlightbackground=status_border,
                                    highlightthickness=1)
            status_frame.pack(fill="x", padx=2, pady=2)
            
            status_inner = tk.Frame(status_frame, bg=status_bg)
            status_inner.pack(fill="x", padx=12, pady=8)
            
            tk.Label(status_inner, text=status_icon, 
                     font=("Segoe UI Emoji", 12),
                     bg=status_bg, fg=status_icon_color).pack(side="left", padx=(0, 8))
            tk.Label(status_inner, text=status_text, 
                     font=("Microsoft YaHei", 9),
                     bg=status_bg, fg=status_text_color).pack(side="left")

            # 消息提示区域
            msg_label = tk.Label(card_frame, text="", 
                                 font=("Microsoft YaHei", 9),
                                 bg="#ffffff", fg="#ef4444",
                                 wraplength=380, justify="center",
                                 height=2)
            msg_label.pack(fill="x", pady=(0, 12))
            
            # 抖音发布协议勾选 - 简洁美观设计
            agreement_frame = tk.Frame(card_frame, bg="#ffffff")
            agreement_frame.pack(fill="x", pady=(0, 20))
            
            agreement_var = tk.BooleanVar(value=False)
            
            # 勾选框和文字在同一行
            check_frame = tk.Frame(agreement_frame, bg="#ffffff")
            check_frame.pack(anchor="w")
            
            # 自定义勾选框（商业化风格）
            cb_size = 18
            cb_canvas = tk.Canvas(check_frame, width=cb_size, height=cb_size, bg="#ffffff",
                                  highlightthickness=0, bd=0, cursor="hand2")
            cb_canvas.pack(side="left", padx=(0, 6))

            def _draw_checkbox():
                cb_canvas.delete("all")
                if agreement_var.get():
                    cb_canvas.create_round_rect = None
                    cb_canvas.create_rectangle(1,1,cb_size-1,cb_size-1, outline="#6366f1", width=2, fill="#6366f1")
                    cb_canvas.create_line(4, 10, 8, 14, 14, 5, fill="#ffffff", width=2.2, capstyle="round", joinstyle="round")
                else:
                    cb_canvas.create_rectangle(1,1,cb_size-1,cb_size-1, outline="#cbd5e1", width=2, fill="#ffffff")

            def _toggle_agreement(_e=None):
                agreement_var.set(not agreement_var.get())
                _draw_checkbox()

            cb_canvas.bind("<Button-1>", _toggle_agreement)
            _draw_checkbox()

            agree_text_label = tk.Label(check_frame, text="我已阅读并同意", 
                     font=("Microsoft YaHei", 10),
                     bg="#ffffff", fg="#64748b", cursor="hand2")
            agree_text_label.pack(side="left", padx=(0, 0))
            agree_text_label.bind("<Button-1>", _toggle_agreement)
            
            def show_agreement():
                agreement_window = tk.Toplevel(root)
                agreement_window.title("用户协议与隐私协议")
                agreement_window.geometry("700x600")
                agreement_window.resizable(True, True)
                
                # Tab 栏
                tab_bar = tk.Frame(agreement_window, bg="#f1f5f9")
                tab_bar.pack(fill="x", padx=20, pady=(16, 0))

                tab_btns = {}
                tab_frames = {}

                def switch_tab(idx):
                    for i, (btn, frm) in enumerate(zip(tab_btns.values(), tab_frames.values())):
                        if i == idx:
                            btn.config(bg="#4f46e5", fg="#ffffff")
                            frm.pack(fill="both", expand=True)
                        else:
                            btn.config(bg="#e2e8f0", fg="#475569")
                            frm.pack_forget()

                tab_btns["user"] = tk.Button(tab_bar, text="📄 用户协议",
                    font=("Microsoft YaHei", 10, "bold"), bg="#4f46e5", fg="#ffffff",
                    relief="flat", bd=0, padx=16, pady=5, cursor="hand2",
                    command=lambda: switch_tab(0))
                tab_btns["user"].pack(side="left", padx=(0, 4))

                tab_btns["privacy"] = tk.Button(tab_bar, text="🔒 隐私协议",
                    font=("Microsoft YaHei", 10, "bold"), bg="#e2e8f0", fg="#475569",
                    relief="flat", bd=0, padx=16, pady=5, cursor="hand2",
                    command=lambda: switch_tab(1))
                tab_btns["privacy"].pack(side="left")

                content_area = tk.Frame(agreement_window)
                content_area.pack(fill="both", expand=True, padx=20, pady=10)

                def _make_text_panel(parent, md_content):
                    frm = tk.Frame(parent)
                    sb = tk.Scrollbar(frm)
                    sb.pack(side="right", fill="y")
                    tw = tk.Text(frm, wrap="word", yscrollcommand=sb.set,
                                 font=("Microsoft YaHei", 9), padx=14, pady=12,
                                 bg="#ffffff", fg="#334155", relief="flat", bd=0)
                    tw.pack(side="left", fill="both", expand=True)
                    sb.config(command=tw.yview)
                    _render_md_to_tk(tw, md_content)
                    tw.config(state="disabled")
                    return frm

                tab_frames["user"] = _make_text_panel(content_area, _load_platform_ai_agreement_text())
                tab_frames["privacy"] = _make_text_panel(content_area, _load_privacy_policy_text())

                switch_tab(0)
                
                # 关闭按钮
                btn_frame = tk.Frame(agreement_window)
                btn_frame.pack(pady=10)
                tk.Button(btn_frame, text="同意", command=agreement_window.destroy,
                         font=("Microsoft YaHei", 10), bg="#6366f1", fg="white",
                         relief="flat", padx=20, pady=5).pack()
            
            link_label = tk.Label(check_frame, text="《用户协议》与《隐私协议》",
                                 font=("Microsoft YaHei", 10), 
                                 bg="#ffffff", fg="#6366f1",
                                 cursor="hand2")
            link_label.pack(side="left")
            link_label.bind("<Button-1>", lambda e: show_agreement())
            
            # 添加鼠标悬停效果
            def on_link_enter(e):
                link_label.config(fg="#4f46e5", font=("Microsoft YaHei", 10, "underline"))
            def on_link_leave(e):
                link_label.config(fg="#6366f1", font=("Microsoft YaHei", 10))
            link_label.bind("<Enter>", on_link_enter)
            link_label.bind("<Leave>", on_link_leave)

            # 登录按钮 - 使用PIL创建圆角渐变按钮
            btn_width = 400
            btn_height = 54
            corner_radius = 10
            
            def create_rounded_gradient_button(width, height, radius, color1, color2, shadow=False):
                """创建圆角渐变按钮图片"""
                img_height = height + 6 if shadow else height
                img = Image.new('RGBA', (width, img_height), (0, 0, 0, 0))
                
                if shadow:
                    shadow_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                    shadow_draw = ImageDraw.Draw(shadow_img)
                    shadow_draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=(0, 0, 0, 30))
                    img.paste(shadow_img, (2, 5), shadow_img)
                
                gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                gradient_draw = ImageDraw.Draw(gradient)
                for y in range(height):
                    ratio = y / height
                    r = int(color1[0] + (color2[0] - color1[0]) * ratio)
                    g = int(color1[1] + (color2[1] - color1[1]) * ratio)
                    b = int(color1[2] + (color2[2] - color1[2]) * ratio)
                    gradient_draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
                
                mask = Image.new('L', (width, height), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=255)
                gradient.putalpha(mask)
                img.paste(gradient, (0, 0), gradient)
                return img
            
            normal_color1 = (99, 102, 241)
            normal_color2 = (124, 58, 237)
            hover_color1 = (129, 140, 248)
            hover_color2 = (139, 92, 246)
            active_color1 = (79, 70, 229)
            active_color2 = (109, 40, 217)
            disabled_color1 = (148, 163, 184)
            disabled_color2 = (148, 163, 184)
            
            btn_normal_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, normal_color1, normal_color2, shadow=True)
            btn_hover_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, hover_color1, hover_color2, shadow=True)
            btn_active_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, active_color1, active_color2, shadow=False)
            btn_disabled_img = create_rounded_gradient_button(btn_width, btn_height, corner_radius, disabled_color1, disabled_color2, shadow=False)
            
            btn_normal_tk = ImageTk.PhotoImage(btn_normal_img)
            btn_hover_tk = ImageTk.PhotoImage(btn_hover_img)
            btn_active_tk = ImageTk.PhotoImage(btn_active_img)
            btn_disabled_tk = ImageTk.PhotoImage(btn_disabled_img)
            
            btn_container = tk.Frame(card_frame, bg="#ffffff", height=70)
            btn_container.pack(fill="x", pady=(10, 0))
            btn_container.pack_propagate(False)
            
            btn_canvas = tk.Canvas(btn_container, bg="#ffffff", highlightthickness=0, height=70, width=btn_width)
            btn_canvas.pack()
            btn_canvas.btn_images = [btn_normal_tk, btn_hover_tk, btn_active_tk, btn_disabled_tk]
            
            btn_x, btn_y = 0, 5
            btn_bg_id = btn_canvas.create_image(btn_x, btn_y, image=btn_normal_tk, anchor="nw", tags="btn_bg")
            text_id = btn_canvas.create_text(
                btn_x + btn_width // 2,
                btn_y + btn_height // 2,
                text="登录启动",
                font=("Microsoft YaHei", 14, "bold"),
                fill="#ffffff",
                tags="btn_text"
            )
            click_area = btn_canvas.create_rectangle(
                btn_x, btn_y, btn_x + btn_width, btn_y + btn_height,
                fill="", outline="", tags="click_area"
            )
            
            btn_state = {"enabled": True, "pressed": False}
            
            def _do_login():
                if not agreement_var.get():
                    msg_label.config(text="[警告] 请先阅读并同意《用户协议》与《隐私协议》", fg="#f59e0b")
                    return
                key = key_entry.get().strip()
                if not key:
                    msg_label.config(text="[警告] 请输入卡密", fg="#f59e0b")
                    return
                if not btn_state["enabled"]:
                    return
                
                btn_state["enabled"] = False
                btn_canvas.itemconfig(btn_bg_id, image=btn_disabled_tk)
                btn_canvas.itemconfig(text_id, text="验证中...")
                key_entry.config(state="disabled")
                msg_label.config(text="正在验证卡密，请稍候...", fg="#6366f1")
                root.update()
                
                ok, msg = lic.validate_online(key)
                if ok:
                    # 保存 TTS 模式选择到 config.dat
                    selected_mode = version_var.get()
                    try:
                        os.makedirs(_CONFIG_DIR, exist_ok=True)
                        cfg = _read_all_config()
                        cfg['TTS_MODE'] = selected_mode
                        with open(_CONFIG_FILE, 'w', encoding='utf-8') as f:
                            for k, v in cfg.items():
                                f.write(f"{k}={v}\n")
                        
                        # 同时设置环境变量，以便子进程可以读取
                        os.environ['TTS_MODE'] = selected_mode
                        print(f"[LICENSE] TTS 模式已保存到 config.dat: {selected_mode}")
                    except Exception as e:
                        print(f"[LICENSE] 保存 TTS 模式失败: {e}")
                    
                    msg_label.config(text="[OK] 激活成功！正在启动程序...", fg="#22c55e")
                    btn_canvas.itemconfig(text_id, text="[OK] 启动中...")
                    result["passed"] = True
                    result["tts_mode"] = selected_mode  # 保存到result中
                    root.after(1200, root.destroy)
                else:
                    msg_label.config(text=f"[ERROR] {msg}", fg="#ef4444")
                    btn_state["enabled"] = True
                    btn_canvas.itemconfig(btn_bg_id, image=btn_normal_tk)
                    btn_canvas.itemconfig(text_id, text="登录启动")
                    key_entry.config(state="normal")
            
            def _on_btn_enter(e):
                if btn_state["enabled"] and not btn_state["pressed"]:
                    btn_canvas.itemconfig(btn_bg_id, image=btn_hover_tk)
                btn_canvas.config(cursor="hand2" if btn_state["enabled"] else "arrow")
            
            def _on_btn_leave(e):
                if btn_state["enabled"]:
                    btn_canvas.itemconfig(btn_bg_id, image=btn_normal_tk)
                btn_canvas.config(cursor="")
                btn_state["pressed"] = False
            
            def _on_btn_press(e):
                if btn_state["enabled"]:
                    btn_state["pressed"] = True
                    btn_canvas.itemconfig(btn_bg_id, image=btn_active_tk)
                    btn_canvas.move(text_id, 0, 2)
            
            def _on_btn_release(e):
                if btn_state["enabled"]:
                    btn_state["pressed"] = False
                    btn_canvas.itemconfig(btn_bg_id, image=btn_hover_tk)
                    btn_canvas.coords(text_id, btn_x + btn_width // 2, btn_y + btn_height // 2)
                    _do_login()
            
            for tag in ("click_area", "btn_text"):
                btn_canvas.tag_bind(tag, "<Enter>", _on_btn_enter)
                btn_canvas.tag_bind(tag, "<Leave>", _on_btn_leave)
                btn_canvas.tag_bind(tag, "<ButtonPress-1>", _on_btn_press)
                btn_canvas.tag_bind(tag, "<ButtonRelease-1>", _on_btn_release)

            key_entry.bind("<Return>", lambda e: _do_login())
            key_entry.focus_set()

            # 底部信息（精致样式）
            canvas.create_text(w//2, h-35, 
                               text="© 2024 织梦AI", 
                               font=("Microsoft YaHei", 9, "bold"),
                               fill="#e9d5ff")
            canvas.create_text(w//2, h-18, 
                               text="专业版 · 保留所有权利", 
                               font=("Microsoft YaHei", 8),
                               fill="#c4b5fd")

            def _on_close():
                result["passed"] = False
                root.destroy()

            root.protocol("WM_DELETE_WINDOW", _on_close)
            root.mainloop()

            if not result["passed"]:
                print("[LICENSE] 用户取消登录，退出程序")
                cleanup()
                sys.exit(0)
                
        except Exception as e:
            print(f"[LICENSE] 登录窗口异常: {e}")
            import traceback
            traceback.print_exc()
            cleanup()
            sys.exit(0)
            
    except Exception as e:
        print(f"[LICENSE] 激活检查异常: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        sys.exit(1)

    print("[LICENSE] 激活验证通过 [OK]")

    try:
        root, status_var = build_splash()
        run_splash(root, status_var)
        try: root.destroy()
        except Exception: pass
    except Exception:
        pass

    if _gradio_url is None:
        _gradio_url = 'http://127.0.0.1:7870'

    print(f"[MAIN] 准备启动 WebView, gradio_url={_gradio_url}")
    if sys.stdout:
        sys.stdout.flush()

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

        # 获取屏幕尺寸并设置窗口为屏幕的90%
        import tkinter as tk
        try:
            temp_root = tk.Tk()
            screen_width = temp_root.winfo_screenwidth()
            screen_height = temp_root.winfo_screenheight()
            temp_root.destroy()
            
            # 窗口大小为屏幕的80%
            window_width = int(screen_width * 0.8)
            window_height = int(screen_height * 0.8)
            
            # 最小尺寸为屏幕的60%
            min_width = int(screen_width * 0.6)
            min_height = int(screen_height * 0.6)
        except Exception:
            # 如果获取失败，使用默认值
            window_width = 1600
            window_height = 1000
            min_width = 1200
            min_height = 800

        window = webview.create_window(
            title='织梦AI大模型 - 专业版',
            url=_gradio_url,
            js_api=_api,
            width=window_width, height=window_height, resizable=True,
            min_size=(min_width, min_height), text_select=True, easy_drag=False,
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
                    print(f"[ICON] [OK] 图标设置成功")
                except Exception as e:
                    print(f"[ICON] [ERROR] {e}")

        threading.Thread(target=_set_icon_later, daemon=True).start()

        # 拦截 X 按钮 — 改进：防止白屏/错误时关不掉
        _close_attempts = [0, 0.0]  # [计数, 上次时间]

        def on_closing():
            now = time.time()
            _close_attempts[0] += 1
            # 连续快速点击 X（3秒内点2次）→ 强制退出，不弹窗
            if _close_attempts[0] >= 2 and (now - _close_attempts[1]) < 3.0:
                print("[EXIT] 连续关闭，强制退出")
                try: cleanup()
                except Exception: os._exit(0)
                return
            _close_attempts[1] = now

            def _force_exit():
                try:
                    print("[EXIT] 强制退出程序...")
                    cleanup()
                except Exception:
                    try:
                        if gradio_process and gradio_process.pid:
                            kill_process_tree(gradio_process.pid)
                    except Exception:
                        pass
                    os._exit(0)

            def _show_confirm():
                try:
                    import tkinter as tk
                    from tkinter import messagebox

                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)

                    # 10秒超时强制退出
                    def timeout_exit():
                        try: root.destroy()
                        except Exception: pass
                        print("[EXIT] 对话框超时，强制退出")
                        _force_exit()

                    exit_timer = root.after(10000, timeout_exit)

                    result = messagebox.askyesnocancel(
                        "关闭程序",
                        "选择操作：\n\n"
                        "「是」- 最小化到通知区域（后台运行）\n"
                        "「否」- 退出程序\n"
                        "「取消」- 返回\n\n"
                        "提示：快速连按两次 X 可强制退出",
                        icon='question'
                    )

                    if exit_timer:
                        root.after_cancel(exit_timer)
                    root.destroy()

                    if result is True:  # 是 - 最小化
                        try:
                            hwnd = _get_main_hwnd()
                            if hwnd:
                                import ctypes
                                ctypes.windll.user32.ShowWindow(hwnd, 0)
                        except Exception:
                            pass
                    elif result is False:  # 否 - 退出
                        _force_exit()
                    else:
                        # 取消 — 重置计数
                        _close_attempts[0] = 0

                except Exception as e:
                    print(f"[CLOSE] 对话框异常: {e}")
                    _force_exit()

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
