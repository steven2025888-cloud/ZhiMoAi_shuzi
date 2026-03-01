# -*- coding: utf-8 -*-
"""
织梦AI - Python代码加密工具
功能：将所有.py文件编译为.pyc字节码文件
"""
import os
import py_compile
import shutil
import sys
import compileall
import subprocess

# 项目根目录（本脚本在 build_scripts/ 子目录下）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 需要加密的Python文件
PYTHON_FILES = [
    "app_backend.py",
    "unified_app.py",
    "lib_avatar.py",
    "lib_voice.py",
    "lib_subtitle.py",
    "lib_license.py",
    "lib_douyin_publish.py",
    "lib_meta_store.py",
]

# 备份目录
BACKUP_DIR = os.path.join(BASE_DIR, "py_backup")


def backup_files():
    """备份原始Python文件"""
    print("备份原始Python文件...")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    for py_file in PYTHON_FILES:
        source_path = os.path.join(BASE_DIR, py_file)
        if os.path.exists(source_path):
            backup_path = os.path.join(BACKUP_DIR, py_file)
            shutil.copy2(source_path, backup_path)
            print(f"  [备份] {py_file}")


def compile_to_pyc():
    """编译Python文件为pyc并移到根目录"""
    print("\n编译Python文件为字节码...")
    
    # 使用项目内的Python环境编译
    python_exe = os.path.join(BASE_DIR, "_internal_tts", "installer_files", "env", "python.exe")
    
    if not os.path.exists(python_exe):
        print(f"  [警告] 未找到项目Python环境: {python_exe}")
        print(f"  [提示] 将使用系统Python编译")
        python_exe = "python"
    else:
        print(f"  [使用] {python_exe}")
    
    success_count = 0
    fail_count = 0
    
    for py_file in PYTHON_FILES:
        source_path = os.path.join(BASE_DIR, py_file)
        if not os.path.exists(source_path):
            print(f"  [跳过] {py_file} (文件不存在)")
            continue
        
        try:
            # 使用指定的Python编译
            result = subprocess.run(
                [python_exe, "-m", "py_compile", source_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"  [错误] {py_file} 编译失败: {result.stderr}")
                fail_count += 1
                continue
            
            # 找到生成的pyc文件
            cache_dir = os.path.join(BASE_DIR, "__pycache__")
            module_name = os.path.splitext(py_file)[0]
            
            # 查找对应的pyc文件
            pyc_found = False
            if os.path.exists(cache_dir):
                for filename in os.listdir(cache_dir):
                    if filename.startswith(module_name + ".cpython") and filename.endswith(".pyc"):
                        # 移动到根目录并重命名为简单的.pyc
                        src_pyc = os.path.join(cache_dir, filename)
                        dst_pyc = os.path.join(BASE_DIR, py_file + "c")
                        shutil.move(src_pyc, dst_pyc)
                        print(f"  [编译] {py_file} -> {py_file}c")
                        pyc_found = True
                        success_count += 1
                        break
            
            if not pyc_found:
                print(f"  [警告] {py_file} 编译成功但未找到pyc文件")
                fail_count += 1
                
        except Exception as e:
            print(f"  [错误] {py_file} 编译失败: {e}")
            fail_count += 1
    
    return success_count, fail_count


def delete_py_files():
    """删除原始.py文件，只保留.pyc"""
    print("\n删除原始.py文件...")
    for py_file in PYTHON_FILES:
        source_path = os.path.join(BASE_DIR, py_file)
        if os.path.exists(source_path):
            os.remove(source_path)
            print(f"  [删除] {py_file}")


def restore_backup():
    """从备份恢复原始Python文件"""
    if not os.path.exists(BACKUP_DIR):
        print("[提示] 没有找到备份目录")
        return
    
    print("正在从备份恢复原始文件...")
    count = 0
    for py_file in PYTHON_FILES:
        backup_path = os.path.join(BACKUP_DIR, py_file)
        if os.path.exists(backup_path):
            target_path = os.path.join(BASE_DIR, py_file)
            
            # 删除可能存在的pyc文件
            pyc_path = target_path + "c"
            if os.path.exists(pyc_path):
                os.remove(pyc_path)
            
            # 恢复py文件
            shutil.copy2(backup_path, target_path)
            print(f"  [恢复] {py_file}")
            count += 1
    
    print(f"\n已恢复 {count} 个文件")


def encrypt_all():
    """加密所有Python文件"""
    print("=" * 80)
    print("织梦AI - Python代码加密工具")
    print("=" * 80)
    print()
    print("此操作会：")
    print("  1. 备份原始.py文件到 py_backup/ 目录")
    print("  2. 将.py文件编译为.pyc字节码")
    print("  3. 删除原始.py文件")
    print()
    print("恢复方法：python encrypt_python.py --restore")
    print()
    
    # 备份原文件
    backup_files()
    
    # 编译为pyc
    success, fail = compile_to_pyc()
    
    # 删除原py文件
    if success > 0:
        delete_py_files()
    
    print()
    print("=" * 80)
    print(f"加密完成: 成功 {success} 个, 失败 {fail} 个")
    print(f"备份目录: {BACKUP_DIR}")
    print("=" * 80)
    print()
    print("注意：")
    print("  1. Python会自动识别并导入.pyc文件")
    print("  2. .pyc文件是字节码，无法直接阅读源代码")
    print("  3. 打包时会包含.pyc文件而不是.py文件")
    print()
    
    return success, fail


if __name__ == "__main__":
    try:
        # 检查是否是恢复模式
        if len(sys.argv) > 1 and sys.argv[1] == "--restore":
            restore_backup()
            sys.exit(0)
        
        success, fail = encrypt_all()
        sys.exit(0 if fail == 0 else 1)
    except Exception as e:
        print(f"[错误] 加密过程异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
