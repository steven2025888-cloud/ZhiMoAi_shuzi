# -*- coding: utf-8 -*-
"""
将 Python venv 转换为独立(standalone)环境。

步骤：
  1. 读取 pyvenv.cfg 找到 base Python 安装路径
  2. 复制 python.exe / python3XX.dll / DLLs / Lib(stdlib) 到 venv 目录
  3. 删除 pyvenv.cfg
  4. 删除 Scripts/activate* 等 venv 激活脚本（不再需要）
"""
import os
import sys
import shutil
import glob
import re


def read_pyvenv_cfg(env_dir):
    """解析 pyvenv.cfg，返回 dict"""
    cfg = {}
    cfg_path = os.path.join(env_dir, "pyvenv.cfg")
    if not os.path.exists(cfg_path):
        return cfg
    with open(cfg_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


def find_base_python(cfg):
    """从 pyvenv.cfg 的 home 字段找到 base Python 安装目录"""
    home = cfg.get("home", "")
    if not home or not os.path.isdir(home):
        return None
    # home 通常指向 base Python 的目录（如 C:\Python310）
    # 或其 Scripts 子目录
    if os.path.exists(os.path.join(home, "python.exe")):
        return home
    parent = os.path.dirname(home)
    if os.path.exists(os.path.join(parent, "python.exe")):
        return parent
    return home


def copy_tree_merge(src, dst):
    """递归复制目录，合并到已有目录（不覆盖已存在文件）"""
    if not os.path.isdir(src):
        return
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copy_tree_merge(s, d)
        else:
            if not os.path.exists(d):
                shutil.copy2(s, d)


def _replace_venv_shims(env_dir):
    """用真正的解释器替换 Scripts/ 下的 venv 壳"""
    scripts_dir = os.path.join(env_dir, "Scripts")
    for name in ["python.exe", "pythonw.exe"]:
        real = os.path.join(env_dir, name)
        shim = os.path.join(scripts_dir, name)
        if os.path.exists(real) and os.path.exists(shim):
            # 检查文件大小：venv 壳通常很小（<100KB），真正的解释器更大
            if os.path.getsize(shim) < os.path.getsize(real):
                os.remove(shim)
                shutil.copy2(real, shim)
                print(f"  [替换] Scripts/{name} (venv壳 → 真正解释器)")


def make_standalone(env_dir):
    print(f"[STANDALONE] 环境目录: {env_dir}")

    cfg = read_pyvenv_cfg(env_dir)
    if not cfg:
        print("[STANDALONE] 未找到 pyvenv.cfg，检查 Scripts/python.exe 是否需要替换...")
        # 即使 pyvenv.cfg 已删除，Scripts/python.exe 可能仍是 venv 壳
        _replace_venv_shims(env_dir)
        return True

    base_dir = find_base_python(cfg)
    if not base_dir:
        print(f"[STANDALONE] [ERROR] 无法定位 base Python: home={cfg.get('home')}")
        return False

    print(f"[STANDALONE] Base Python: {base_dir}")

    # 1. 复制 python.exe, pythonw.exe 到 env 根目录
    for exe in ["python.exe", "pythonw.exe"]:
        src = os.path.join(base_dir, exe)
        dst = os.path.join(env_dir, exe)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"  [复制] {exe}")

    # 2. 复制 python3*.dll, vcruntime*.dll
    for pattern in ["python3*.dll", "python*.dll", "vcruntime*.dll"]:
        for src in glob.glob(os.path.join(base_dir, pattern)):
            name = os.path.basename(src)
            dst = os.path.join(env_dir, name)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                print(f"  [复制] {name}")

    # 3. 复制 DLLs/ 目录
    src_dlls = os.path.join(base_dir, "DLLs")
    dst_dlls = os.path.join(env_dir, "DLLs")
    if os.path.isdir(src_dlls):
        copy_tree_merge(src_dlls, dst_dlls)
        print(f"  [合并] DLLs/")

    # 4. 复制 Lib/ (stdlib) — 跳过 site-packages（venv 已有自己的）
    src_lib = os.path.join(base_dir, "Lib")
    dst_lib = os.path.join(env_dir, "Lib")
    if os.path.isdir(src_lib):
        os.makedirs(dst_lib, exist_ok=True)
        for item in os.listdir(src_lib):
            if item == "site-packages":
                continue  # 保留 venv 的 site-packages
            s = os.path.join(src_lib, item)
            d = os.path.join(dst_lib, item)
            if os.path.isdir(s):
                if not os.path.exists(d):
                    shutil.copytree(s, d)
            else:
                if not os.path.exists(d):
                    shutil.copy2(s, d)
        print(f"  [合并] Lib/ (stdlib)")

    # 5. 复制 libs/ (link libraries, e.g. python310.lib)
    src_libs = os.path.join(base_dir, "libs")
    dst_libs = os.path.join(env_dir, "libs")
    if os.path.isdir(src_libs):
        copy_tree_merge(src_libs, dst_libs)
        print(f"  [合并] libs/")

    # 8. 删除 pyvenv.cfg
    cfg_path = os.path.join(env_dir, "pyvenv.cfg")
    if os.path.exists(cfg_path):
        os.remove(cfg_path)
        print(f"  [删除] pyvenv.cfg")

    # 9. 清理 venv 激活脚本（不再需要）
    scripts_dir = os.path.join(env_dir, "Scripts")
    for name in ["activate", "activate.bat", "Activate.ps1", "deactivate.bat"]:
        p = os.path.join(scripts_dir, name)
        if os.path.exists(p):
            os.remove(p)
            print(f"  [删除] Scripts/{name}")

    # 10. 替换 Scripts/python.exe
    _replace_venv_shims(env_dir)

    # 11. 验证
    py_exe = os.path.join(env_dir, "python.exe")
    if not os.path.exists(py_exe):
        py_exe = os.path.join(env_dir, "Scripts", "python.exe")
    if os.path.exists(py_exe):
        print(f"\n[STANDALONE] [OK] 独立环境就绪: {py_exe}")
    else:
        print(f"\n[STANDALONE] [WARN] 未找到 python.exe")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python make_env_standalone.py <env_dir>")
        sys.exit(1)
    env_dir = os.path.abspath(sys.argv[1])
    if not os.path.isdir(env_dir):
        print(f"[ERROR] 目录不存在: {env_dir}")
        sys.exit(1)
    ok = make_standalone(env_dir)
    sys.exit(0 if ok else 1)
