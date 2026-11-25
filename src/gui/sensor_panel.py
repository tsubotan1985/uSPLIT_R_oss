from typing import Any

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


_HUMAN_NAMES: dict[str, str] = {
    "Temperature": "Temp",
    "BiasSense": "Bias",
    "Serial": "Serial",
}

_UNIT_KEYWORDS: dict[str, str] = {
    "Temp": "\u00b0C",
    "Bias": "V",
}


def _label(key: str, value: str) -> str:
    display = _HUMAN_NAMES.get(key, key)
    return f"{display}: {value}"


class SensorPanel(QWidget):
    def __init__(self, title: str, parent: Any = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("border: 1px solid #555; padding: 5px;")
        layout = QVBoxLayout(self)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.title_label)

        self.alpha_label = QLabel("\u03b1: --")
        self.beta_label = QLabel("\u03b2: --")
        self.gamma_label = QLabel("\u03b3: --")
        self.total_label = QLabel("Total: --")
        self.status_label = QLabel("Status: \u25cf")
        self.status_label.setStyleSheet("color: red;")

        for lbl in [self.alpha_label, self.beta_label, self.gamma_label,
                     self.total_label, self.status_label]:
            layout.addWidget(lbl)

        self._param_labels: dict[str, QLabel] = {}
        self._param_layout = layout

    def update_counts(self, alpha: int, beta: int, gamma: int, total: int) -> None:
        self.alpha_label.setText(f"\u03b1: {alpha}")
        self.beta_label.setText(f"\u03b2: {beta}")
        self.gamma_label.setText(f"\u03b3: {gamma}")
        self.total_label.setText(f"Total: {total}")

    def update_info(self, info: dict[str, str]) -> None:
        seen: set[str] = set()
        for key, value in info.items():
            seen.add(key)
            if key not in self._param_labels:
                lbl = QLabel()
                lbl.setStyleSheet("font-size: 9pt;")
                self._param_layout.addWidget(lbl)
                self._param_labels[key] = lbl
            unit = ""
            for kw, u in _UNIT_KEYWORDS.items():
                if kw in key:
                    unit = u
                    break
            suffix = f" {unit}" if unit else ""
            self._param_labels[key].setText(f"{_label(key, value)}{suffix}")

        for key in list(self._param_labels.keys()):
            if key not in seen:
                self._param_labels[key].deleteLater()
                del self._param_labels[key]

    def update_status(self, connected: bool) -> None:
        color = "green" if connected else "red"
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText("Status: \u25cf")