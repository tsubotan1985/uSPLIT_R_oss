from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.hardware.pixet_manager import PixetManager
from src.hardware.device_controller import DeviceController


SENSOR_IDS = ["E02", "I03", "J03"]


class MultiDeviceController:
    def __init__(self, pixet_mgr: PixetManager | None = None) -> None:
        self._pixet_mgr = pixet_mgr
        self.controllers: dict[str, DeviceController] = {}
        self.sensor_order: list[str] = []
        self._executor = ThreadPoolExecutor(max_workers=3)

    def discover_and_match(self) -> dict[str, int]:
        if self._pixet_mgr is None:
            self._pixet_mgr = PixetManager.initialize()
        devices = self._pixet_mgr.list_devices()
        mapping: dict[str, int] = {}
        assigned: set[int] = set()
        for sensor_id in SENSOR_IDS:
            matched = None
            for idx, dev in enumerate(devices):
                if idx in assigned:
                    continue
                if sensor_id in dev.deviceID():
                    matched = idx
                    break
            if matched is not None:
                mapping[sensor_id] = matched
                assigned.add(matched)
        remaining = [i for i in range(len(devices)) if i not in assigned]
        for i, sensor_id in enumerate(SENSOR_IDS):
            if sensor_id not in mapping and i < len(remaining):
                mapping[sensor_id] = remaining[i]
        return mapping

    def connect_all(self) -> None:
        mapping = self.discover_and_match()
        for sensor_id, dev_idx in mapping.items():
            ctrl = DeviceController(self._pixet_mgr)
            ctrl.connect(dev_idx)
            self.controllers[sensor_id] = ctrl
            self.sensor_order.append(sensor_id)

    def acquire_all(self, integration_time: float = 1.0) -> dict[str, Any]:
        results: dict[str, Any] = {}
        futures: dict[Any, str] = {}
        for sensor_id in self.sensor_order:
            ctrl = self.controllers.get(sensor_id)
            if ctrl is None or not ctrl.is_connected:
                continue
            future = self._executor.submit(ctrl.acquire_frame, integration_time=integration_time)
            futures[future] = sensor_id
        for future in as_completed(futures):
            sensor_id = futures[future]
            try:
                results[sensor_id] = future.result()
            except Exception:
                continue
        return results

    def get_all_temperatures(self) -> dict[str, float | None]:
        temps: dict[str, float | None] = {}
        for sensor_id in self.sensor_order:
            ctrl = self.controllers.get(sensor_id)
            if ctrl is None:
                temps[sensor_id] = None
            else:
                temps[sensor_id] = ctrl.get_temperature()
        return temps

    def get_all_device_info(self) -> dict[str, dict[str, str]]:
        infos: dict[str, dict[str, str]] = {}
        for sensor_id in self.sensor_order:
            ctrl = self.controllers.get(sensor_id)
            if ctrl is not None:
                infos[sensor_id] = ctrl.get_device_info()
        return infos

    def disconnect_all(self) -> None:
        self._executor.shutdown(wait=False)
        for ctrl in self.controllers.values():
            ctrl.disconnect()
        self.controllers.clear()
        self.sensor_order.clear()
