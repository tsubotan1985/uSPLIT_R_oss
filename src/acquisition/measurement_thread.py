import time
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import QThread, Signal

from src.hardware.multi_device import MultiDeviceController
from src.acquisition.file_saver import save_frame, save_metadata, create_measurement_dir


SENSOR_ID_TO_DIR: dict[str, str] = {
    "E02": "Sensor01",
    "I03": "Sensor02",
    "J03": "Sensor03",
}


class MeasurementThread(QThread):
    frame_acquired = Signal(str, int, object)
    measurement_error = Signal(str, str)
    interval_missed = Signal(int)

    def __init__(
        self,
        multi_ctrl: MultiDeviceController,
        interval: float = 1.0,
        save_dir: str | Path | None = None,
        comment: str = "",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._multi_ctrl = multi_ctrl
        self._interval = interval
        self._save_dir = Path(save_dir) if save_dir else Path.cwd()
        self._comment = comment
        self._running = False
        self._frame_counter: dict[str, int] = {}
        self._missed_count = 0
        self._measurement_dir: Path | None = None

    def run(self) -> None:
        self._running = True
        try:
            self._measurement_dir = create_measurement_dir(self._save_dir)
            meta = {
                "interval": self._interval,
                "sensor_ids": self._multi_ctrl.sensor_order,
            }
            if self._comment:
                meta["comment"] = self._comment
            save_metadata(self._measurement_dir, meta)

            while self._running:
                t0 = time.perf_counter()
                results = self._multi_ctrl.acquire_all(integration_time=self._interval)
                import logging
                logger = logging.getLogger("usplit")
                logger.info(f"acquire_all returned {len(results)} results: {list(results.keys())}")
                for sensor_id, data in results.items():
                    n = self._frame_counter.get(sensor_id, 0) + 1
                    self._frame_counter[sensor_id] = n
                    if isinstance(data, np.ndarray):
                        logger.info(f"frame {n} [{sensor_id}]: shape={data.shape}, max={data.max():.0f}, nonzero={int((data>0).sum())}")
                        dir_name = SENSOR_ID_TO_DIR.get(sensor_id, sensor_id)
                        save_frame(data, dir_name, n, self._measurement_dir)
                    self.frame_acquired.emit(sensor_id, n, data)
                elapsed = time.perf_counter() - t0
                remaining = int(self._interval * 1000 - elapsed * 1000)
                if remaining > 0:
                    self.msleep(remaining)
        except Exception as e:
            self.measurement_error.emit("system", str(e))

    def stop(self) -> None:
        self._running = False
