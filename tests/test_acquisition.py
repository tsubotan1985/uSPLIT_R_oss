from unittest.mock import MagicMock, patch
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication

from src.acquisition.measurement_thread import MeasurementThread
from src.acquisition.file_saver import create_measurement_dir, save_frame


@pytest.fixture(scope="session")
def qapp() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


class TestFileSaver:
    def test_create_measurement_dir_structure(self, tmp_path: Path) -> None:
        root = create_measurement_dir(tmp_path)
        assert root.exists()
        for i in range(1, 4):
            assert (root / f"Sensor{i:02d}").exists()
        assert (root / "analysis_results").exists()

    def test_save_frame_creates_file(self, tmp_path: Path) -> None:
        root = create_measurement_dir(tmp_path)
        data = np.zeros((256, 256), dtype=np.int32)
        filepath = save_frame(data, "Sensor01", 1, root)
        assert filepath.exists()
        loaded = np.loadtxt(filepath, dtype=np.int32)
        assert loaded.shape == (256, 256)


class TestMeasurementThread:
    def test_run_and_stop(self, qapp: QCoreApplication, tmp_path: Path) -> None:
        mock_ctrl = MagicMock()
        mock_ctrl.sensor_order = ["E02"]
        mock_ctrl.acquire_all.return_value = {"E02": np.zeros((256, 256))}
        thread = MeasurementThread(mock_ctrl, interval=0.1, save_dir=str(tmp_path))
        thread._measurement_dir = tmp_path
        received: list[tuple[str, int, object]] = []

        def on_frame(sensor_id: str, frame_num: int, data: object) -> None:
            received.append((sensor_id, frame_num, data))
            if len(received) >= 2:
                thread.stop()

        thread.frame_acquired.connect(on_frame)
        thread.start()
        import time
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            qapp.processEvents()
            if len(received) >= 2:
                break
        thread.wait(2000)
        assert len(received) >= 2

    def test_stop_immediately(self, qapp: QCoreApplication) -> None:
        mock_ctrl = MagicMock()
        mock_ctrl.sensor_order = []
        mock_ctrl.acquire_all.return_value = {}
        thread = MeasurementThread(mock_ctrl, interval=1.0)
        thread.stop()
        assert not thread._running
