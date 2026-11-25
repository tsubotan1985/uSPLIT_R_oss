from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class SensorView(QWidget):
    def __init__(self, title: str, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        self.image = QLabel("No data")
        self.image.setStyleSheet("border: 1px solid #555; background: #0a0e27;")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(200, 200)
        layout.addWidget(self.image, stretch=1)
        self.frame_label = QLabel()
        self.frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self.frame_label)
        self._latest: int = -1

    def show_latest(self, directory: Path) -> None:
        if not directory.exists():
            return
        pngs = sorted(directory.glob("frame_*.png"))
        if not pngs:
            return
        newest = pngs[-1]
        try:
            num = int(newest.stem.split("_")[1])
        except (IndexError, ValueError):
            return
        if num <= self._latest:
            return
        pix = QPixmap(str(newest))
        if pix.isNull():
            return
        w = self.image.width() - 4
        h = self.image.height() - 4
        if w > 0 and h > 0:
            scaled = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
            self.image.setPixmap(scaled)
        self.frame_label.setText(f"Frame: {num:06d}")
        self._latest = num


class VisualizationTab(QWidget):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._views: dict[str, SensorView] = {}
        self._dirs: dict[str, Path] = {}

        layout = QHBoxLayout(self)
        for label in ["Sensor01 (E02)", "Sensor02 (I03)", "Sensor03 (J03)"]:
            sv = SensorView(label)
            self._views[label] = sv
            layout.addWidget(sv, stretch=1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.setInterval(1000)

    def set_watch_dir(self, sensor_display: str, png_dir: Path) -> None:
        self._dirs[sensor_display] = png_dir

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        for disp, d in self._dirs.items():
            v = self._views.get(disp)
            if v is not None:
                v.show_latest(d)