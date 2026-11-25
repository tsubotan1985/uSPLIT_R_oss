from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)


class TrainingTab(QWidget):
    training_started = Signal(str, str, str, str, float, int)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        group = QGroupBox("Training Configuration")
        form = QFormLayout(group)

        self.alpha_path = QLineEdit()
        self.beta_path = QLineEdit()
        self.gamma_path = QLineEdit()

        def make_browse_row(path_edit: QLineEdit) -> tuple[QWidget, QPushButton]:
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            btn = QPushButton("Browse...")
            btn.clicked.connect(lambda: self._browse_dir(path_edit))
            h.addWidget(path_edit, stretch=1)
            h.addWidget(btn)
            return w, btn

        row_a, self.alpha_browse = make_browse_row(self.alpha_path)
        row_b, self.beta_browse = make_browse_row(self.beta_path)
        row_g, self.gamma_browse = make_browse_row(self.gamma_path)
        form.addRow("α 線 フォルダ:", row_a)
        form.addRow("β 線 フォルダ:", row_b)
        form.addRow("γ 線 フォルダ:", row_g)

        self.filter_threshold = QLineEdit("1000")
        form.addRow("α 線フィルタ閾値:", self.filter_threshold)

        self.model_name = QLineEdit()
        self.model_name.setPlaceholderText("LGBM_YYYYMMDD_HHMM")
        form.addRow("保存モデル名:", self.model_name)

        optuna_row = QHBoxLayout()
        self.optuna_check = QCheckBox("Optuna 最適化")
        self.optuna_trials = QSpinBox()
        self.optuna_trials.setRange(10, 500)
        self.optuna_trials.setValue(50)
        self.optuna_trials.setEnabled(False)
        self.optuna_check.toggled.connect(self.optuna_trials.setEnabled)
        optuna_row.addWidget(self.optuna_check)
        optuna_row.addWidget(QLabel("試行回数:"))
        optuna_row.addWidget(self.optuna_trials)
        optuna_row.addStretch()
        form.addRow("最適化:", optuna_row)

        self.train_btn = QPushButton("Start Training")
        self.progress_bar = QProgressBar()

        layout.addWidget(group)
        layout.addWidget(self.train_btn)
        layout.addWidget(self.progress_bar)
        layout.addStretch()

        self.result_label = QLabel()
        self.result_label.setStyleSheet("background: #1e1e1e; color: white; padding: 10px;")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        self.train_btn.clicked.connect(self._on_start_training)

    def _browse_dir(self, line_edit: QLineEdit) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "Select folder")
        if dir_path:
            line_edit.setText(dir_path)

    def update_progress(self, stage: str, pct: int) -> None:
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{stage} ({pct}%)")

    def _on_start_training(self) -> None:
        alpha = self.alpha_path.text().strip()
        beta = self.beta_path.text().strip()
        gamma = self.gamma_path.text().strip()
        name = self.model_name.text().strip()
        threshold = float(self.filter_threshold.text().strip())
        n_trials = self.optuna_trials.value() if self.optuna_check.isChecked() else 0
        self.training_started.emit(alpha, beta, gamma, name, threshold, n_trials)
