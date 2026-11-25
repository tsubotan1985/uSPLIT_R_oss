from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import QThread, Signal

from src.analysis.data_loader import load_out_file, preprocess
from src.analysis.feature_extractor import extract_features
from src.analysis.classifier import Classifier
from src.analysis.spectrum import compute_energy_spectrum
from src.analysis.time_series import TimeSeriesAggregator
from skimage.measure import label


class AnalysisThread(QThread):
    analysis_complete = Signal(str, object)
    classification_updated = Signal(str, dict)

    def __init__(
        self,
        classifier: Classifier,
        time_series: TimeSeriesAggregator,
        measurement_dir: str | Path | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._classifier = classifier
        self._time_series = time_series
        self._measurement_dir = Path(measurement_dir) if measurement_dir else None
        self._running = False
        self._processed: set[str] = set()

    def set_measurement_dir(self, path: str | Path) -> None:
        self._measurement_dir = Path(path)

    def stop(self) -> None:
        self._running = False

    def should_yield(self) -> bool:
        return not self._running

    def run(self) -> None:
        self._running = True
        while self._running:
            self.process_pending_files()
            self.msleep(1000)

    def process_pending_files(self) -> None:
        if not self._measurement_dir or not self._measurement_dir.exists():
            return
        for fpath in sorted(self._measurement_dir.rglob("frame_*.out")):
            if self.should_yield():
                break
            key = str(fpath)
            if key in self._processed:
                continue
            self._processed.add(key)
            try:
                self._process_single_file(fpath)
            except Exception:
                continue

    def _process_single_file(self, fpath: Path) -> None:
        matrix = load_out_file(str(fpath))
        matrix = preprocess(matrix)
        features, _, _ = extract_features(matrix)
        if not features:
            return
        classification = self._classifier.predict(features)
        sensor_dir = fpath.parent.name
        alpha = sum(1 for c in classification if c.get("class") == 0)
        beta = sum(1 for c in classification if c.get("class") == 1)
        gamma = sum(1 for c in classification if c.get("class") == 2)
        counts = {"alpha": alpha, "beta": beta, "gamma": gamma, "total": len(classification)}
        self.classification_updated.emit(sensor_dir, counts)
        self._time_series.accumulate(0, sensor_dir, classification)
        self.analysis_complete.emit(str(fpath), counts)
