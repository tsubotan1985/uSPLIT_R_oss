import os
import threading
from pathlib import Path
from typing import Any

from src.hardware.pixet_manager import PixetManager


CALIB_DIR = Path(__file__).resolve().parent.parent.parent / "pixet_sdk" / "configs"



class DeviceController:
    def __init__(self, pixet_mgr: PixetManager) -> None:
        self._pixet_mgr = pixet_mgr
        self._dev_lock = threading.Lock()
        self.device: Any = None
        self.sensor_id: str = ""
        self.is_connected = False

    def connect(self, device_index: int) -> None:
        with self._dev_lock:
            devices = self._pixet_mgr.list_devices()
            if device_index >= len(devices):
                raise RuntimeError(f"Device index {device_index} out of range (available: {len(devices)})")
            self.device = devices[device_index]
            device_id = self.device.deviceID()
            self.sensor_id = self._extract_sensor_id(device_id)
            self.load_calibration()
            self.is_connected = True

    def load_calibration(self) -> None:
        if self.device is None:
            return
        device_id = self.device.deviceID()
        if not CALIB_DIR.exists():
            return
        for xml_path in sorted(CALIB_DIR.iterdir()):
            if xml_path.suffix.lower() != ".xml":
                continue
            if xml_path.stem in device_id or device_id in xml_path.stem:
                self.device.loadConfigFromFile(str(xml_path))
                return

    def acquire_frame(self, integration_time: float = 1.0) -> Any:
        with self._dev_lock:
            if not self.is_connected or self.device is None:
                raise RuntimeError("Device not connected")
            import tempfile
            import numpy as np
            fd, tmp = tempfile.mkstemp(suffix=".txt")
            os.close(fd)
            try:
                pixet = self._pixet_mgr.pixet
                chip = self.device.chipType()
                if chip in (pixet.PX_CHIPTYPE_TPX, pixet.PX_CHIPTYPE_MXR):
                    pixcfg = self.device.pixCfg()
                    pixcfg.setModeAll(pixet.PX_TPXMODE_TOT)
                rc = self.device.doSimpleAcquisition(1, integration_time, pixet.PX_FTYPE_ASCII_FRAME, tmp)
                if rc != 0:
                    raise RuntimeError(f"Acquisition failed with code {rc}")
                data = np.loadtxt(tmp, dtype=np.float64)
                return data
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)

    def get_temperature(self) -> float | None:
        with self._dev_lock:
            if not self.is_connected or self.device is None:
                return None
            params = self.device.parameters()
            for name in ["TemperatureChip", "Temperature", "TemperatureCpu"]:
                try:
                    if params.hasParam(name):
                        p = params.get(name)
                        if hasattr(p, "getDouble"):
                            return p.getDouble()
                        if hasattr(p, "value"):
                            return float(p.value())
                except Exception:
                    continue
            return None

    def get_device_info(self) -> dict[str, str]:
        info: dict[str, str] = {}
        if not self.is_connected or self.device is None:
            return info
        try:
            info["Serial"] = self.device.deviceID().split("-")[-1]
        except Exception:
            pass
        with self._dev_lock:
            try:
                params = self.device.parameters()
                for name in ["Temperature", "BiasSense"]:
                    try:
                        if params.hasParam(name):
                            p = params.get(name)
                            val: str = ""
                            if hasattr(p, "getDouble"):
                                raw = p.getDouble()
                                if name == "BiasSense":
                                    val = f"{raw:.1f}"
                                else:
                                    val = f"{raw:.1f}"
                            if not val and hasattr(p, "getString"):
                                val = p.getString()
                            if val:
                                info[name] = val
                    except Exception:
                        continue
            except Exception:
                pass
        return info

    def disconnect(self) -> None:
        with self._dev_lock:
            self.device = None
            self.is_connected = False
            self.sensor_id = ""

    @staticmethod
    def _extract_sensor_id(device_id: str) -> str:
        for ident in ["E02", "I03", "J03"]:
            if ident in device_id:
                return ident
        return device_id.replace(" ", "_")
