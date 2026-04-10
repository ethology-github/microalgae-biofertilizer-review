# -*- encoding: utf-8 -*-
"""
共享工具模块 - 提供日志、JSON读写、进度跟踪等通用功能
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别，默认INFO
    
    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def load_json(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    加载JSON文件
    
    Args:
        file_path: JSON文件路径
    
    Returns:
        解析后的Python列表
    """
    path = Path(file_path)
    if not path.exists():
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        return [data]
    return data if isinstance(data, list) else []


def save_json(data: List[Dict[str, Any]], file_path: Union[str, Path], indent: int = 2) -> None:
    """
    保存数据到JSON文件
    
    Args:
        data: 要保存的Python对象
        file_path: 输出文件路径
        indent: JSON缩进空格数
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


class ProgressTracker:
    """
    进度跟踪器，用于显示长时间运行的进度
    """
    
    def __init__(self, total: int, desc: str = "Processing"):
        """
        初始化进度跟踪器
        
        Args:
            total: 总任务数
            desc: 任务描述
        """
        self.total = total
        self.current = 0
        self.desc = desc
        self._bar_length = 40
    
    def update(self, n: int = 1) -> None:
        """
        更新进度
        
        Args:
            n: 本次增量，默认1
        """
        self.current += n
        self._display()
    
    def _display(self) -> None:
        """内部方法：显示进度条"""
        filled = int(self._bar_length * self.current / self.total) if self.total > 0 else 0
        bar = '█' * filled + '░' * (self._bar_length - filled)
        pct = f"{100 * self.current / self.total:.1f}%" if self.total > 0 else "0%"
        sys.stdout.write(f'\r{self.desc}: |{bar}| {pct} ({self.current}/{self.total})')
        sys.stdout.flush()
    
    def finish(self) -> None:
        """完成进度条显示"""
        self.current = self.total
        self._display()
        sys.stdout.write('\n')
        sys.stdout.flush()
