from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.analysis.classifier import Classifier, ModelFeatureMismatch
from src.config import Config


MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


class MeasurementControl(QWidget):
    start_requested = Signal(float, str, str)
    stop_requested = Signal()
    clear_requested = Signal()
    model_changed = Signal(str)

    def __init__(self, config: Config | None = None, parent: Any = None) -> None:
        super().__init__(parent)
        self._config = config or Config()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(4)

        row1 = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("Clear")

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["0.1 s", "1 s", "10 s", "30 s", "60 s"])
        self.interval_combo.setCurrentText("1 s")
        self.interval_combo.setToolTip("0.1s: 1秒周期で0.1秒間測定（センサー通信ラグ対策）")

        default_save = str(self._config.get("save_dir") or Path.home() / "uSPLIT-R")
        self.save_path = QLineEdit(default_save)

        self.browse_btn = QPushButton("Browse...")

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(180)
        self.model_combo.setToolTip("Select trained model for classification")
        self.apply_model_btn = QPushButton("Apply")
        self._refresh_models()

        row1.addWidget(self.start_btn)
        row1.addWidget(self.stop_btn)
        row1.addWidget(self.clear_btn)
        row1.addWidget(QLabel("Interval:"))
        row1.addWidget(self.interval_combo)
        row1.addWidget(QLabel("Save to:"))
        row1.addWidget(self.save_path, stretch=1)
        row1.addWidget(self.browse_btn)
        row1.addWidget(QLabel("Model:"))
        row1.addWidget(self.model_combo)
        row1.addWidget(self.apply_model_btn)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Comment:"))
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("測定条件やメモを入力（日本語可）")
        row2.addWidget(self.comment_edit, stretch=1)
        self.classifier_label = QLabel("分類: rule-based")
        self.classifier_label.setToolTip(
            "学習済みモデル未使用のフォールバック。閾値は config.json の rule_based で変更できます"
        )
        row2.addWidget(self.classifier_label)
        layout.addLayout(row2)

        self.hw_label = QLabel("")
        self.hw_label.setWordWrap(True)
        self.hw_label.setStyleSheet("color: #c0392b;")
        self.hw_label.setVisible(False)
        layout.addWidget(self.hw_label)

        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.clear_btn.clicked.connect(lambda: self.clear_requested.emit())
        self.browse_btn.clicked.connect(self._on_browse)
        self.apply_model_btn.clicked.connect(self._on_apply_model)

    def _refresh_models(self) -> None:
        self.model_combo.clear()
        self.model_combo.addItem("(rule-based)")
        if MODELS_DIR.exists():
            for fpath in sorted(MODELS_DIR.glob("*.joblib")):
                self.model_combo.addItem(fpath.stem, str(fpath))

    def select_model_by_path(self, model_path: str) -> None:
        idx = self.model_combo.findData(model_path)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)

    def _on_apply_model(self) -> None:
        path = self.model_combo.currentData()
        if not path:
            return
        try:
            Classifier(path)
        except ModelFeatureMismatch as e:
            # 特徴量が食い違ったまま推論すると黙って誤分類するので、適用させない
            QMessageBox.warning(
                self,
                "モデル非互換",
                f"{e}\n\nこのモデルは現在の特徴量セットで学習されていません。",
            )
            self.model_combo.setCurrentIndex(0)
            return
        except Exception as e:
            import logging
            logging.getLogger("usplit").error(f"Model validation failed: {e}")
            QMessageBox.warning(self, "モデル読み込み失敗", str(e))
            return
        self.model_changed.emit(path)

    def _on_start(self) -> None:
        interval = float(self.interval_combo.currentText().replace(" s", ""))
        save_dir = self.save_path.text().strip()
        comment = self.comment_edit.text().strip()
        self.start_requested.emit(interval, save_dir, comment)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _on_stop(self) -> None:
        self.stop_requested.emit()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_browse(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "Select save directory")
        if dir_path:
            self.save_path.setText(dir_path)
            self._config.set("save_dir", dir_path)
            self._config.save()

    def set_hardware_available(self, available: bool, reason: str = "") -> None:
        """Pixet SDK が使えないときは Start を押せなくし、理由を画面に出す。"""
        self.start_btn.setEnabled(available)
        if available:
            self.hw_label.setVisible(False)
            self.hw_label.setText("")
            self.start_btn.setToolTip("")
        else:
            self.hw_label.setText(
                f"測定は無効です: {reason or 'Pixet SDK が見つかりません'}"
                "（学習タブ・可視化タブは使用できます）"
            )
            self.hw_label.setVisible(True)
            self.start_btn.setToolTip(reason)

    def restore_start_button(self) -> None:
        """測定が開始できなかったときにボタン状態を戻す。"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def set_classifier_label(self, model_path: str | None) -> None:
        if model_path:
            self.classifier_label.setText(f"分類: {Path(model_path).stem}")
        else:
            self.classifier_label.setText("分類: rule-based")
