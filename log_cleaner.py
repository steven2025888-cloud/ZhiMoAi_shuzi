# -*- coding: utf-8 -*-
"""
织梦AI - 日志自动清理工具
功能：
  - vbs_startup.log 超过 50MB 自动清空
  - ws_extract.log 超过 50MB 自动清空
  - logs/app.log 超过 100MB 自动清空
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 日志文件配置：(文件路径, 最大大小MB)
LOG_FILES = [
    (os.path.join(BASE_DIR, "vbs_startup.log"), 50),
    (os.path.join(BASE_DIR, "ws_extract.log"), 50),
    (os.path.join(BASE_DIR, "logs", "app.log"), 100),
]


def get_file_size_mb(filepath):
    """获取文件大小（MB）"""
    try:
        if os.path.exists(filepath):
            size_bytes = os.path.getsize(filepath)
            return size_bytes / (1024 * 1024)
        return 0
    except Exception:
        return 0


def clean_log_file(filepath, max_size_mb):
    """清理日志文件"""
    try:
        current_size = get_file_size_mb(filepath)
        if current_size > max_size_mb:
            # 备份最后1000行
            backup_lines = []
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    backup_lines = lines[-1000:] if len(lines) > 1000 else lines
            except Exception:
                pass
            
            # 清空并写入备份
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"[LOG CLEANED] 日志文件已清理（原大小: {current_size:.2f}MB）\n")
                f.write("=" * 80 + "\n")
                if backup_lines:
                    f.write("[保留最后1000行]\n")
                    f.writelines(backup_lines)
            
            print(f"[清理] {os.path.basename(filepath)} ({current_size:.2f}MB -> {get_file_size_mb(filepath):.2f}MB)")
            return True
        return False
    except Exception as e:
        print(f"[错误] 清理 {filepath} 失败: {e}")
        return False


def clean_all_logs():
    """清理所有日志文件"""
    cleaned_count = 0
    for filepath, max_size in LOG_FILES:
        # 确保目录存在
        log_dir = os.path.dirname(filepath)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception:
                pass
        
        if clean_log_file(filepath, max_size):
            cleaned_count += 1
    
    if cleaned_count > 0:
        print(f"[完成] 共清理 {cleaned_count} 个日志文件")
    return cleaned_count


if __name__ == "__main__":
    try:
        clean_all_logs()
    except Exception as e:
        print(f"[错误] 日志清理失败: {e}")
        sys.exit(1)
