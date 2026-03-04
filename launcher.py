# -*- coding: utf-8 -*-
"""
织梦AI - 启动器程序
功能：
  - 合并 启动应用.bat 和 启动应用.vbs 的功能
  - 自动清理超大日志文件
  - 记录运行日志
  - 无窗口启动
"""
import os
import sys
import subprocess
import shutil
import time
import tempfile
import logging
from datetime import datetime
import traceback
import ctypes

# 获取正确的BASE_DIR（支持PyInstaller打包）
if getattr(sys, 'frozen', False):
    # 如果是PyInstaller打包的exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 如果是Python脚本
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置日志
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 配置日志格式
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
        ]
    )
    logger = logging.getLogger(__name__)
except Exception as e:
    # 如果日志配置失败，使用基本的print
    print(f"日志配置失败: {e}")
    logger = None


def log_info(msg):
    """记录日志"""
    if logger:
        logger.info(msg)
    else:
        print(f"[INFO] {msg}")


def log_error(msg):
    """记录错误"""
    if logger:
        logger.error(msg)
    else:
        print(f"[ERROR] {msg}")


def log_warning(msg):
    """记录警告"""
    if logger:
        logger.warning(msg)
    else:
        print(f"[WARNING] {msg}")


def _find_zhimoai_windows():
    """用纯 ctypes 枚举所有标题含 '织梦AI' 或 '专业版' 的可见窗口"""
    u32 = ctypes.windll.user32
    results = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.POINTER(ctypes.c_int))

    def _cb(hwnd, _lp):
        try:
            # 只匹配可见窗口
            if not u32.IsWindowVisible(hwnd):
                return True
            length = u32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            u32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            # 必须包含 '织梦AI' 才匹配（避免误匹配其他含 '专业版' 的程序）
            if '织梦AI' in title:
                results.append(hwnd)
        except Exception:
            pass
        return True

    u32.EnumWindows(WNDENUMPROC(_cb), 0)
    return results


def check_single_instance():
    """检查是否已有 app_backend 在运行（通过端口 17870 检测，与 app_backend 的 socket 锁一致）"""
    import socket as _sock
    try:
        # 尝试绑定 app_backend 使用的单实例端口
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
        s.bind(('127.0.0.1', 17870))
        s.close()
        # 绑定成功 → 没有其他实例在运行
        return True
    except OSError:
        # 端口已被占用 → app_backend 正在运行
        log_info("检测到 app_backend 已在运行（端口 17870 已占用）")
        # 尝试激活已有窗口
        try:
            existing = _find_zhimoai_windows()
            if existing:
                log_info(f"找到织梦AI窗口 (hwnd={existing[0]})，激活")
                bring_to_front(existing[0])
            else:
                log_info("未找到织梦AI窗口，可能正在启动中")
        except Exception:
            pass
        return False
    except Exception as e:
        log_warning(f"单实例检查失败: {e}")
        return True


def bring_to_front(hwnd):
    """用纯 ctypes 将窗口恢复并置顶"""
    try:
        u32 = ctypes.windll.user32
        SW_RESTORE = 9
        # 如果窗口最小化或隐藏，先恢复
        u32.ShowWindow(hwnd, SW_RESTORE)
        # 置顶
        u32.SetForegroundWindow(hwnd)
        log_info(f"已激活窗口 hwnd={hwnd}")
    except Exception as e:
        log_warning(f"激活窗口失败: {e}")


def _clean_stale_mei_dirs():
    """清理上次运行残留的 _MEI* 临时目录（PyInstaller --onefile 遗留）"""
    try:
        tmp = tempfile.gettempdir()
        mei_pass = getattr(sys, '_MEIPASS', None)
        for name in os.listdir(tmp):
            if not name.startswith('_MEI'):
                continue
            path = os.path.join(tmp, name)
            # 不要删除当前正在使用的 _MEI 目录
            if mei_pass and os.path.normcase(os.path.normpath(path)) == os.path.normcase(os.path.normpath(mei_pass)):
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    log_info(f"已清理残留 _MEI 目录: {name}")
            except Exception:
                pass
    except Exception as e:
        log_warning(f"清理 _MEI 目录失败: {e}")


def clean_logs():
    """清理超大日志文件"""
    try:
        log_cleaner = os.path.join(BASE_DIR, "log_cleaner.py")
        log_cleaner_pyc = os.path.join(BASE_DIR, "log_cleaner.pyc")
        
        # 优先使用pyc
        if os.path.exists(log_cleaner_pyc):
            log_cleaner = log_cleaner_pyc
        elif not os.path.exists(log_cleaner):
            return
        
        # 尝试多个可能的Python路径
        python_paths = [
            os.path.join(BASE_DIR, "_internal_tts", "installer_files", "env", "python.exe"),
            os.path.join(BASE_DIR, "_internal_tts", "installer_files", "env", "Scripts", "python.exe"),
            os.path.join(BASE_DIR, "IndexTTS2-SonicVale", "installer_files", "env", "python.exe"),
            os.path.join(BASE_DIR, "IndexTTS2-SonicVale", "installer_files", "env", "Scripts", "python.exe"),
        ]
        
        python_exe = None
        for path in python_paths:
            if os.path.exists(path):
                python_exe = path
                break
        
        if python_exe:
            subprocess.run([python_exe, log_cleaner], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    except Exception as e:
        log_warning(f"日志清理失败: {e}")


def start_app():
    """启动应用"""
    try:
        log_info("=" * 80)
        log_info(f"织梦AI大模型 v2.0 启动器")
        log_info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_info(f"工作目录: {BASE_DIR}")
        log_info("=" * 80)

        debug_flag = os.path.join(BASE_DIR, "debug_console.flag")
        debug_console = os.path.exists(debug_flag)
        if debug_console:
            log_warning(f"[DEBUG] 已启用调试控制台模式: {debug_flag}")
        
        # 1. 检查环境（日志清理延后到启动后，减少用户等待时间）
        log_info("[1/3] 检查运行环境...")
        
        # 尝试多个可能的Python路径
        # 注意：根目录 python.exe 优先于 Scripts\python.exe（后者可能是 venv 壳）
        python_paths = [
            os.path.join(BASE_DIR, "_internal_tts", "installer_files", "env", "python.exe"),
            os.path.join(BASE_DIR, "_internal_tts", "installer_files", "env", "Scripts", "python.exe"),
            os.path.join(BASE_DIR, "IndexTTS2-SonicVale", "installer_files", "env", "python.exe"),
            os.path.join(BASE_DIR, "IndexTTS2-SonicVale", "installer_files", "env", "Scripts", "python.exe"),
        ]
        
        python_exe = None
        for path in python_paths:
            if os.path.exists(path):
                python_exe = path
                log_info(f"  找到Python: {path}")
                break
            else:
                log_info(f"  未找到: {path}")
        
        if not python_exe:
            log_error("Python 解释器未找到")
            log_error("尝试的路径:")
            for path in python_paths:
                log_error(f"  - {path}")
            log_error(f"BASE_DIR: {BASE_DIR}")
            log_error("请确保 _internal_tts 文件夹已正确安装")
            # 弹窗通知用户
            try:
                tried = "\n".join(python_paths)
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Python 解释器未找到！\n\n已检查路径：\n{tried}\n\n安装目录：{BASE_DIR}\n\n请确保 _internal_tts 文件夹已正确安装。",
                    "织梦AI - 启动失败",
                    0x10
                )
            except Exception:
                pass
            return False
        
        # 检查主程序（支持.py和.pyc）
        app_backend = os.path.join(BASE_DIR, "app_backend.py")
        app_backend_pyc = os.path.join(BASE_DIR, "app_backend.pyc")
        
        if os.path.exists(app_backend_pyc):
            app_backend = app_backend_pyc
            log_info(f"  使用加密版本: {app_backend}")
        elif os.path.exists(app_backend):
            log_info(f"  使用源代码版本: {app_backend}")
        else:
            log_error(f"主程序未找到: {app_backend}")
            return False
        
        # 2.5 设置 Tcl/Tk 环境变量（绕过打包后路径解析错误）
        env_dir = os.path.dirname(python_exe)  # python.exe 所在目录即 env
        # 搜索顺序: Conda布局 → 标准CPython布局 → lib/
        for sub in ['Library/lib', 'tcl', 'lib']:
            _tcl_dir = os.path.join(env_dir, sub, 'tcl8.6')
            _tk_dir = os.path.join(env_dir, sub, 'tk8.6')
            if os.path.isdir(_tcl_dir) and 'TCL_LIBRARY' not in os.environ:
                os.environ['TCL_LIBRARY'] = _tcl_dir
                log_info(f"  设置 TCL_LIBRARY={_tcl_dir}")
            if os.path.isdir(_tk_dir) and 'TK_LIBRARY' not in os.environ:
                os.environ['TK_LIBRARY'] = _tk_dir
                log_info(f"  设置 TK_LIBRARY={_tk_dir}")
        
        if 'TCL_LIBRARY' not in os.environ:
            log_warning("  未找到 tcl8.6 目录，tkinter 可能无法正常工作")

        # 3. 启动应用
        log_info("[3/3] 启动应用...")
        log_info(f"Python: {python_exe}")
        log_info(f"主程序: {app_backend}")
        
        # 将子进程输出重定向到日志文件（便于排查打包后无窗口的问题）
        backend_log = os.path.join(LOG_DIR, "backend_startup.log")
        crash_log = os.path.join(LOG_DIR, "crash.log")

        # ── 关键修复：清除 _MEI 临时目录对子进程的 PATH 污染 ──
        # PyInstaller --onefile 会将 _MEI* 目录加入 PATH / DLL搜索路径，
        # 子进程继承后会锁住 _MEI 中的 DLL，导致 launcher 退出时无法清理临时目录。
        child_env = os.environ.copy()
        mei_pass = getattr(sys, '_MEIPASS', None)
        if mei_pass:
            log_info(f"  检测到 _MEIPASS={mei_pass}，清理子进程 PATH")
            # 从 PATH 中移除所有包含 _MEI 的路径
            path_parts = child_env.get('PATH', '').split(os.pathsep)
            clean_parts = [p for p in path_parts if '_MEI' not in p]
            child_env['PATH'] = os.pathsep.join(clean_parts)
            # 移除 PyInstaller 注入的内部变量
            for key in list(child_env.keys()):
                if key.startswith('_MEIPASS') or key == '_PYI_SPLASH_IPC':
                    del child_env[key]

        # debug_console 模式：不使用 pythonw，不隐藏窗口，不重定向 stdout/stderr（直接在控制台显示）
        if debug_console:
            # launcher 自身是 --noconsole 构建的，因此这里强制创建新控制台窗口
            flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            process = subprocess.Popen(
                [python_exe, "-u", app_backend],
                cwd=BASE_DIR,
                env=child_env,
                creationflags=flags,
            )
        else:
            # ── 关键修复：使用 python.exe + CREATE_NO_WINDOW ──
            # 不再使用 pythonw.exe！
            # pythonw.exe 会静默吞掉所有错误（import失败、模块缺失等完全无输出）
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            log_info(f"  使用python.exe + CREATE_NO_WINDOW (隐藏窗口)")

            log_f = open(backend_log, "w", encoding="utf-8", errors="replace")
            process = subprocess.Popen(
                [python_exe, "-u", app_backend],
                cwd=BASE_DIR,
                env=child_env,
                stdout=log_f,
                stderr=log_f,
                creationflags=flags
            )

        log_info(f"应用已启动 (PID: {process.pid})")
        log_info(f"子进程日志: {backend_log}")
        log_info(f"崩溃日志: {crash_log}")

        # 启动后再清理日志（不阻塞用户）
        try:
            import threading
            threading.Thread(target=clean_logs, daemon=True).start()
        except Exception:
            pass

        # ── 多轮轮询检测早期崩溃 ──
        # 缩短等待时间：5秒足够检测 import 级别的崩溃
        max_wait = 5
        poll_interval = 0.5
        elapsed = 0
        rc = None
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            rc = process.poll()
            if rc is not None:
                break
            log_info(f"  进程存活检查 {elapsed}/{max_wait}s ... PID {process.pid} 运行中")

        if rc is not None:
            # 子进程已退出 → 启动失败
            try:
                if not debug_console:
                    log_f.close()
            except Exception:
                pass

            # 收集所有可用的错误信息
            err_parts = []

            # 1) 读取 backend_startup.log（stdout/stderr 输出）
            try:
                if debug_console:
                    err_parts.append("(调试控制台模式下，请查看控制台输出)")
                else:
                    with open(backend_log, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read().strip()
                    if content:
                        err_parts.append(f"[子进程输出]\n{content[-2000:]}")
                    else:
                        err_parts.append("[子进程输出] (空 — 进程未产生任何输出)")
            except Exception:
                err_parts.append("[子进程输出] (无法读取)")

            # 2) 读取 crash.log（app_backend 内部崩溃处理器写入）
            try:
                if os.path.exists(crash_log):
                    with open(crash_log, "r", encoding="utf-8", errors="replace") as f:
                        crash_content = f.read().strip()
                    if crash_content:
                        err_parts.append(f"[崩溃日志]\n{crash_content[-2000:]}")
            except Exception:
                pass

            err_content = "\n\n".join(err_parts) if err_parts else "(无法获取任何错误信息)"

            log_error(f"app_backend 启动后退出! 退出码={rc}, 存活时间<{elapsed}s")
            log_error(f"错误详情:\n{err_content}")

            # 弹窗提示用户
            try:
                # 截取关键信息用于弹窗（弹窗不能太长）
                popup_msg = (
                    f"应用启动失败 (退出码: {rc})\n\n"
                    f"{err_content[:800]}\n\n"
                    f"完整日志:\n"
                    f"  {backend_log}\n"
                    f"  {crash_log}\n"
                    f"  {LOG_FILE}"
                )
                ctypes.windll.user32.MessageBoxW(
                    0, popup_msg, "织梦AI - 启动失败", 0x10
                )
            except Exception:
                pass
            return False

        log_info(f"应用进程运行正常 (PID: {process.pid}, 已存活>{max_wait}s)")
        log_info("=" * 80)
        return True
        
    except Exception as e:
        log_error(f"启动失败: {e}")
        log_error(traceback.format_exc())
        return False


if __name__ == "__main__":
    try:
        # 清理上次残留的 _MEI 临时目录
        _clean_stale_mei_dirs()

        # 检查单实例
        if not check_single_instance():
            sys.exit(0)
        
        success = start_app()
        sys.exit(0 if success else 1)
    except Exception as e:
        log_error(f"启动器异常: {e}")
        log_error(traceback.format_exc())
        sys.exit(1)
