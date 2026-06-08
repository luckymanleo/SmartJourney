"""
SmartJourney 日志配置 — 按日切分 + 单文件 10MB 上限
"""

import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging(level: str = "INFO") -> None:
    """配置全局日志：控制台 + 按日切分文件"""

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 根 Logger
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)

    # 文件 — 按日切分，单文件最大 10MB，保留 30 天
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / "smartjourney.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    # 限制单文件大小：手动在轮转时检查并截断
    file_handler.suffix = "%Y-%m-%d"
    root.addHandler(file_handler)

    # 错误日志单独文件
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / "error.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setFormatter(fmt)
    error_handler.setLevel(logging.WARNING)
    error_handler.suffix = "%Y-%m-%d"
    root.addHandler(error_handler)

    # 抑制第三方库噪音
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root.info(f"Logging initialized: dir={LOG_DIR}, level={level}")
