from typing import Any
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QTextEdit

from src.logger import log_signal


LEVEL_COLORS = {
    "DEBUG": "gray",
    "INFO": "white",
    "WARNING": "gold",
    "ERROR": "red",
}


class LogPanel(QTextEdit):
    append_signal = Signal(str)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("background-color: #1e1e1e; color: white; font-family: Consolas; font-size: 10pt;")
        self._queue: deque[tuple[str, str]] = deque()
        self.append_signal.connect(self._do_append)
        log_signal.connect(self._on_log)

    def _on_log(self, level: str, message: str) -> None:
        self._queue.append((level, message))
        QTimer.singleShot(0, self._flush)

    def _flush(self) -> None:
        while self._queue:
            level, msg = self._queue.popleft()
            color = LEVEL_COLORS.get(level, "white")
            self.append_signal.emit(f'<span style="color:{color};">{msg}</span>')

    @Slot(str)
    def _do_append(self, html: str) -> None:
        self.append(html)
