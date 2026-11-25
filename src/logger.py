import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


class LogSignal:
    def __init__(self) -> None:
        self._callbacks: list[Callable[[str, str], None]] = []

    def connect(self, callback: Callable[[str, str], None]) -> None:
        self._callbacks.append(callback)

    def disconnect(self, callback: Callable[[str, str], None]) -> None:
        self._callbacks.remove(callback)

    def emit(self, level: str, message: str) -> None:
        for cb in self._callbacks:
            cb(level, message)


class _LogEmitter(logging.Handler):
    def __init__(self, signal: LogSignal) -> None:
        super().__init__()
        self._signal = signal

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._signal.emit(record.levelname, msg)
        except Exception:
            self.handleError(record)


log_signal = LogSignal()


def setup_logger(name: str = "usplit") -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    emitter = _LogEmitter(log_signal)
    emitter.setLevel(logging.INFO)
    emitter.setFormatter(formatter)
    logger.addHandler(emitter)

    return logger
