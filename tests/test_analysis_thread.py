from unittest.mock import MagicMock, patch
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication

from src.analysis.analysis_thread import AnalysisThread
from src.analysis.classifier import Classifier
from src.analysis.time_series import TimeSeriesAggregator


@pytest.fixture(scope="session")
def qapp() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


class TestAnalysisThread:
    def test_should_yield_returns_false_during_run(self, qapp: QCoreApplication) -> None:
        cls = Classifier()
        ts = TimeSeriesAggregator()
        thread = AnalysisThread(cls, ts)
        thread._running = True
        assert not thread.should_yield()

    def test_should_yield_returns_true_when_stopped(self, qapp: QCoreApplication) -> None:
        cls = Classifier()
        ts = TimeSeriesAggregator()
        thread = AnalysisThread(cls, ts)
        thread._running = False
        assert thread.should_yield()

    def test_stop_sets_running_false(self, qapp: QCoreApplication) -> None:
        cls = Classifier()
        ts = TimeSeriesAggregator()
        thread = AnalysisThread(cls, ts)
        thread._running = True
        thread.stop()
        assert not thread._running

    def test_processes_files_in_directory(self, qapp: QCoreApplication, tmp_path: Path) -> None:
        sensor_dir = tmp_path / "Sensor01"
        sensor_dir.mkdir(parents=True)
        data = np.zeros((256, 256), dtype=np.float64)
        data[10:12, 10:12] = 5000
        np.savetxt(sensor_dir / "frame_000001.out", data, fmt="%d")

        cls = Classifier()
        ts = TimeSeriesAggregator()
        thread = AnalysisThread(cls, ts, measurement_dir=str(tmp_path))
        thread._running = True

        processed_before = len(thread._processed)
        thread.process_pending_files()
        processed_after = len(thread._processed)

        assert processed_after > processed_before
        assert ts.get_series("Sensor01") != []
