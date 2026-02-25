# -*- coding: utf-8 -*-
"""
log_cleaner.py - 日志自动清理工具

当日志文件超过指定大小时自动清理，保留最后若干行。
"""

import os
import sys
from dataclasses import dataclass
from typing import List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 保留的行数
BACKUP_LINES = 1000


@dataclass
class LogFileConfig:
    """日志文件配置"""
    path: str
    max_size_mb: int


# 日志文件配置列表
LOG_FILES: List[LogFileConfig] = [
    LogFileConfig(os.path.join(BASE_DIR, "vbs_startup.log"), 50),
    LogFileConfig(os.path.join(BASE_DIR, "ws_extract.log"), 50),
    LogFileConfig(os.path.join(BASE_DIR, "logs", "app.log"), 100),
]


def get_file_size_mb(filepath: str) -> float:
    """获取文件大小(MB)"""
    try:
        return os.path.getsize(filepath) / (1024 * 1024) if os.path.exists(filepath) else 0.0
    except OSError:
        return 0.0


def _read_last_lines(filepath: str, n: int) -> List[str]:
    """读取文件最后n行"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return lines[-n:] if len(lines) > n else lines
    except (IOError, OSError):
        return []


def clean_log_file(config: LogFileConfig) -> bool:
    """
    清理单个日志文件
    
    Args:
        config: 日志文件配置
        
    Returns:
        是否执行了清理
    """
    filepath = config.path
    current_size = get_file_size_mb(filepath)
    
    if current_size <= config.max_size_mb:
        return False
    
    try:
        # 备份最后若干行
        backup_lines = _read_last_lines(filepath, BACKUP_LINES)
        
        # 清空并写入备份
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"[LOG CLEANED] 日志文件已清理（原大小: {current_size:.2f}MB）\n")
            f.write("=" * 80 + "\n")
            if backup_lines:
                f.write(f"[保留最后{len(backup_lines)}行]\n")
                f.writelines(backup_lines)
        
        new_size = get_file_size_mb(filepath)
        print(f"[清理] {os.path.basename(filepath)} ({current_size:.2f}MB -> {new_size:.2f}MB)")
        return True
        
    except (IOError, OSError) as e:
        print(f"[错误] 清理 {filepath} 失败: {e}")
        return False


def ensure_log_dir(filepath: str) -> None:
    """确保日志目录存在"""
    log_dir = os.path.dirname(filepath)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError:
            pass


def clean_all_logs() -> int:
    """
    清理所有日志文件
    
    Returns:
        清理的文件数量
    """
    cleaned_count = 0
    
    for config in LOG_FILES:
        ensure_log_dir(config.path)
        if clean_log_file(config):
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
