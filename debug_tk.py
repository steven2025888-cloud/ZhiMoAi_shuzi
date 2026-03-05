# -*- coding: utf-8 -*-
"""
debug_tk.py — Tcl/Tk 环境诊断与自动修复工具
==============================================
用法：
  1. 将此文件复制到打包后的安装目录（如 D:\ZhiMoAI）
  2. 双击运行，或在 cmd 中执行：
       D:\ZhiMoAI\FunCosyVoice3\python310\python.exe debug_tk.py
  3. 脚本会自动诊断、尝试修复、验证修复结果

输出内容包括：
  - Python / Tcl DLL 版本
  - 所有 init.tcl / tk.tcl 文件及其内部版本号
  - 版本号不匹配时自动修补
  - 修补后尝试 import tkinter; tk.Tk() 验证
"""
import os, sys, re, ctypes, glob, traceback

# ── 基本路径 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR = os.path.join(BASE_DIR, "FunCosyVoice3")
ENV_DIR = os.path.join(INDEXTTS_DIR, "python310")

SEP = "=" * 64

def heading(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# ══════════════════════════════════════════════════════════════
#  1. 基础环境信息
# ══════════════════════════════════════════════════════════════
heading("1. 基础环境信息")
print(f"  Python:      {sys.executable}")
print(f"  版本:        {sys.version}")
print(f"  平台:        {sys.platform}")
print(f"  BASE_DIR:    {BASE_DIR}")
print(f"  ENV_DIR:     {ENV_DIR}  (exists={os.path.isdir(ENV_DIR)})")
print(f"  TCL_LIBRARY: {os.environ.get('TCL_LIBRARY', '(未设置)')}")
print(f"  TK_LIBRARY:  {os.environ.get('TK_LIBRARY', '(未设置)')}")


# ══════════════════════════════════════════════════════════════
#  2. 检测 Tcl DLL 实际版本
# ══════════════════════════════════════════════════════════════
heading("2. Tcl DLL 版本检测")
actual_ver = None
dll_names = ['tcl86t.dll', 'tcl86.dll']
dll_dirs = [
    os.path.join(ENV_DIR, 'DLLs'),
    os.path.join(ENV_DIR, 'Library', 'bin'),
    ENV_DIR,
    os.path.join(ENV_DIR, 'bin'),
]
for dll_dir in dll_dirs:
    for dll_name in dll_names:
        dll_path = os.path.join(dll_dir, dll_name)
        if not os.path.exists(dll_path):
            continue
        try:
            tcl_dll = ctypes.CDLL(dll_path)
            _major = ctypes.c_int()
            _minor = ctypes.c_int()
            _patch = ctypes.c_int()
            tcl_dll.Tcl_GetVersion(
                ctypes.byref(_major), ctypes.byref(_minor),
                ctypes.byref(_patch), None
            )
            actual_ver = f"{_major.value}.{_minor.value}.{_patch.value}"
            print(f"  [OK] DLL: {dll_path}")
            print(f"       Tcl_GetVersion() => {actual_ver}")
            break
        except Exception as e:
            print(f"  [FAIL] {dll_path}: {e}")
    if actual_ver:
        break

if not actual_ver:
    print("  [ERROR] 未找到任何 Tcl DLL，无法获取实际版本")
    print("          请确认安装目录结构完整")


# ══════════════════════════════════════════════════════════════
#  3. 扫描所有 init.tcl / tk.tcl 文件
# ══════════════════════════════════════════════════════════════
heading("3. 扫描 Tcl/Tk 脚本文件")

tcl_re = re.compile(r'(package\s+require\s+-exact\s+Tcl\s+)([\d.]+)')
tk_re  = re.compile(r'(package\s+require\s+-exact\s+Tk\s+)([\d.]+)')

# 候选路径（覆盖所有可能被 _tkinter 搜索到的位置）
init_tcl_candidates = set()
tk_tcl_candidates = set()

search_roots = [ENV_DIR, INDEXTTS_DIR, BASE_DIR]
for root in search_roots:
    if not os.path.isdir(root):
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if fn == 'init.tcl':
                init_tcl_candidates.add(os.path.normcase(os.path.abspath(full)))
            elif fn == 'tk.tcl':
                tk_tcl_candidates.add(os.path.normcase(os.path.abspath(full)))

print(f"\n  找到 init.tcl: {len(init_tcl_candidates)} 个")
for p in sorted(init_tcl_candidates):
    try:
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
        m = tcl_re.search(content)
        ver = m.group(2) if m else "(未找到版本行)"
        # 检查原始行中的实际空格
        raw_m = re.search(r'package require -exact Tcl\s+([\d.]+)', content)
        raw_line = raw_m.group(0) if raw_m else ""
        match_tag = "✓" if (m and m.group(2) == actual_ver) else "✗ 版本不匹配"
        print(f"    {p}")
        print(f"      版本: {ver}  [{match_tag}]")
        if raw_line:
            print(f"      原始行: '{raw_line}'")
    except Exception as e:
        print(f"    {p}: 读取失败 ({e})")

print(f"\n  找到 tk.tcl: {len(tk_tcl_candidates)} 个")
for p in sorted(tk_tcl_candidates):
    try:
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
        m = tk_re.search(content)
        ver = m.group(2) if m else "(未找到版本行)"
        raw_m = re.search(r'package require -exact Tk\s+([\d.]+)', content)
        raw_line = raw_m.group(0) if raw_m else ""
        match_tag = "✓" if (m and m.group(2) == actual_ver) else "✗ 版本不匹配"
        print(f"    {p}")
        print(f"      版本: {ver}  [{match_tag}]")
        if raw_line:
            print(f"      原始行: '{raw_line}'")
    except Exception as e:
        print(f"    {p}: 读取失败 ({e})")


# ══════════════════════════════════════════════════════════════
#  4. 自动修补
# ══════════════════════════════════════════════════════════════
heading("4. 自动修补版本号")

if not actual_ver:
    print("  [SKIP] 无法确定 DLL 版本，跳过修补")
else:
    patched_count = 0

    # 修补 init.tcl
    for p in sorted(init_tcl_candidates):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
            m = tcl_re.search(content)
            if m and m.group(2) != actual_ver:
                old_ver = m.group(2)
                new_content = tcl_re.sub(r'\g<1>' + actual_ver, content)
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    f.flush()
                    os.fsync(f.fileno())
                print(f"  [PATCHED] {p}: Tcl {old_ver} -> {actual_ver}")
                patched_count += 1
            elif m:
                print(f"  [OK] {p}: 版本已正确 ({m.group(2)})")
        except Exception as e:
            print(f"  [ERROR] {p}: {e}")

    # 修补 tk.tcl
    for p in sorted(tk_tcl_candidates):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
            m = tk_re.search(content)
            if m and m.group(2) != actual_ver:
                old_ver = m.group(2)
                new_content = tk_re.sub(r'\g<1>' + actual_ver, content)
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    f.flush()
                    os.fsync(f.fileno())
                # 验证
                with open(p, 'r', encoding='utf-8') as f:
                    verify = f.read()
                vm = tk_re.search(verify)
                ok = vm and vm.group(2) == actual_ver
                tag = "✓ 验证通过" if ok else "✗ 验证失败"
                print(f"  [PATCHED] {p}: Tk {old_ver} -> {actual_ver}  [{tag}]")
                patched_count += 1
            elif m:
                print(f"  [OK] {p}: 版本已正确 ({m.group(2)})")
        except Exception as e:
            print(f"  [ERROR] {p}: {e}")

    if patched_count == 0:
        print("  所有文件版本号已正确，无需修补")
    else:
        print(f"\n  共修补 {patched_count} 个文件")


# ══════════════════════════════════════════════════════════════
#  5. 设置环境变量
# ══════════════════════════════════════════════════════════════
heading("5. 设置 TCL_LIBRARY / TK_LIBRARY 环境变量")

for sub in ['Library/lib', 'lib']:
    tcl_dir = os.path.join(ENV_DIR, sub, 'tcl8.6')
    tk_dir  = os.path.join(ENV_DIR, sub, 'tk8.6')
    if os.path.isdir(tcl_dir) and 'TCL_LIBRARY' not in os.environ:
        os.environ['TCL_LIBRARY'] = tcl_dir
        print(f"  TCL_LIBRARY = {tcl_dir}")
    if os.path.isdir(tk_dir) and 'TK_LIBRARY' not in os.environ:
        os.environ['TK_LIBRARY'] = tk_dir
        print(f"  TK_LIBRARY  = {tk_dir}")

print(f"  (最终) TCL_LIBRARY = {os.environ.get('TCL_LIBRARY', '(未设置)')}")
print(f"  (最终) TK_LIBRARY  = {os.environ.get('TK_LIBRARY', '(未设置)')}")


# ══════════════════════════════════════════════════════════════
#  6. 验证：尝试 import tkinter + tk.Tk()
# ══════════════════════════════════════════════════════════════
heading("6. 验证 tkinter")

try:
    import tkinter as tk
    print(f"  import tkinter 成功")
    print(f"  tkinter.TkVersion  = {tk.TkVersion}")
    print(f"  tkinter.TclVersion = {tk.TclVersion}")
except Exception as e:
    print(f"  [ERROR] import tkinter 失败: {e}")
    traceback.print_exc()
    print(f"\n{'='*64}")
    print("  诊断完成（tkinter 导入失败）")
    print(f"{'='*64}")
    input("\n按回车键退出...")
    sys.exit(1)

try:
    print("\n  尝试创建 tk.Tk() ...")
    root = tk.Tk()
    root.withdraw()
    tcl_ver_runtime = root.tk.eval('info patchlevel')
    print(f"  [OK] tk.Tk() 创建成功！")
    print(f"  Tcl 运行时版本 (info patchlevel): {tcl_ver_runtime}")
    root.destroy()
    print(f"  root.destroy() 成功")
except Exception as e:
    print(f"  [ERROR] tk.Tk() 失败: {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
#  完成
# ══════════════════════════════════════════════════════════════
print(f"\n{'='*64}")
print("  诊断与修复完成")
print(f"{'='*64}")

input("\n按回车键退出...")
