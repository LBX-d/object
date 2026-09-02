"""
日志工具

统一日志格式，同时输出到控制台和滚动日志文件（backend/logs/app.log）。
用法：from app.utils.logger import get_logger; logger = get_logger("模块名")
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_configured = False


def _setup_root_logger() -> None:
    """配置根日志器（只执行一次）"""
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())

    formatter = logging.Formatter(_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台输出
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    # 文件输出：单文件最大 5MB，保留 3 个备份
    file_handler = RotatingFileHandler(
        Path(settings.LOG_DIR) / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取指定模块的日志器"""
    global _configured
    if not _configured:
        _setup_root_logger()
        _configured = True
    return logging.getLogger(name)
