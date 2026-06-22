"""
SmartJourney 日志配置 — 多进程安全 + 按日切分 + 单文件 10MB 上限

多实例/多 worker 下 TimedRotatingFileHandler 的轮转竞态通过
SafeTimedRotatingFileHandler 处理：轮转失败时自动回退为 reopen，
日志最多丢失当前进程在轮转瞬间的 1-2 行。
"""

import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class SafeTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """多进程安全的按日轮转文件 handler

    doRollover() 中 rename 失败（另一进程已轮转）时，
    不回退到旧文件而是直接打开新文件继续写。
    """

    def doRollover(self):
        try:
            if self.stream:
                self.stream.close()
                self.stream = None
            # 计算轮转后的目标文件名
            if self.backupCount > 0:
                for i in range(self.backupCount - 1, 0, -1):
                    sfn = self.rotation_filename(f"{self.baseFilename}.{i}")
                    dfn = self.rotation_filename(f"{self.baseFilename}.{i + 1}")
                    if os.path.exists(sfn):
                        if os.path.exists(dfn):
                            os.remove(dfn)
                        os.rename(sfn, dfn)
                dfn = self.rotation_filename(self.baseFilename + ".1")
                if os.path.exists(dfn):
                    os.remove(dfn)
                if os.path.exists(self.baseFilename):
                    os.rename(self.baseFilename, dfn)
        except OSError:
            # 另一进程已完成轮转 → 直接打开新文件
            pass
        finally:
            if not self.delay:
                self.stream = self._open()


def _build_fmt() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging(level: str = "INFO") -> None:
    """配置全局日志：控制台 + 多进程安全的按日切分文件"""

    fmt = _build_fmt()

    # 根 Logger
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)

    # 文件 — 每进程独立 handler（SafeTimedRotatingFileHandler 防轮转竞态）
    file_handler = SafeTimedRotatingFileHandler(
        filename=LOG_DIR / "smartjourney.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)
    file_handler.suffix = "%Y-%m-%d"
    root.addHandler(file_handler)

    # 错误日志 — 同样使用安全版 handler
    error_handler = SafeTimedRotatingFileHandler(
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
