# -*- coding: utf-8 -*-
"""
织梦AI - 打包专用Python编译工具
功能：临时编译.pyc文件用于打包，不删除原始.py文件
"""
import os
import sys
import subprocess
import shutil

# 项目根目录（本脚本在 build_scripts/ 子目录下）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 需要编译的Python文件
PYTHON_FILES = [
    "app_backend.py",
    "unified_app.py",
    "lib_avatar.py",
    "lib_voice.py",
    "lib_subtitle.py",
    "lib_license.py",
    "lib_douyin_publish.py",
    "lib_bilibili_publish.py",
    "lib_shipinhao_publish.py",
    "lib_xiaohongshu_publish.py",
    "lib_meta_store.py",
    "ws_worker.py",
]


def clean_pyc_files():
    """清理临时生成的.pyc文件"""
    print("清理临时.pyc文件...")
    count = 0
    for py_file in PYTHON_FILES:
        pyc_file = os.path.join(BASE_DIR, py_file + "c")
        if os.path.exists(pyc_file):
            os.remove(pyc_file)
            print(f"  [删除] {py_file}c")
            count += 1
    
    # 清理__pycache__目录
    cache_dir = os.path.join(BASE_DIR, "__pycache__")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print(f"  [删除] __pycache__/")
    
    print(f"已清理 {count} 个.pyc文件")


def compile_to_pyc():
    """编译Python文件为.pyc（不删除原文件）"""
    print("编译Python文件为字节码...")
    
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
                        # 复制到根目录并重命名为简单的.pyc
                        src_pyc = os.path.join(cache_dir, filename)
                        dst_pyc = os.path.join(BASE_DIR, py_file + "c")
                        shutil.copy2(src_pyc, dst_pyc)
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


def main():
    """主函数"""
    print("=" * 80)
    print("织梦AI - 打包专用Python编译工具")
    print("=" * 80)
    print()
    
    # 检查是否是清理模式
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        clean_pyc_files()
        return 0
    
    print("此操作会：")
    print("  1. 将.py文件编译为.pyc字节码")
    print("  2. 保留原始.py文件不变")
    print("  3. 打包完成后需要运行 --clean 清理.pyc")
    print()
    
    # 编译为pyc
    success, fail = compile_to_pyc()
    
    print()
    print("=" * 80)
    print(f"编译完成: 成功 {success} 个, 失败 {fail} 个")
    print("=" * 80)
    print()
    print("注意：")
    print("  1. 原始.py文件未被修改")
    print("  2. .pyc文件仅用于打包")
    print("  3. 打包完成后运行: python build_pyc_for_package.py --clean")
    print()
    
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[错误] 编译过程异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
