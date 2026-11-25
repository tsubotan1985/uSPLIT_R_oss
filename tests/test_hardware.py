from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from src.hardware.pixet_manager import PixetManager
from src.hardware.multi_device import MultiDeviceController, SENSOR_IDS


@pytest.fixture(autouse=True)
def _reset_pixet_manager() -> None:
    PixetManager._instance = None
    PixetManager._initialized = False


def _make_mock_pixet() -> MagicMock:
    mp = MagicMock()
    mp.pixet.devices.return_value = []
    return mp


class TestPixetManager:
    def test_initialize_returns_singleton(self) -> None:
        mp = _make_mock_pixet()
        with patch.dict("sys.modules", {"pypixet": mp}):
            m1 = PixetManager.initialize()
            m2 = PixetManager.initialize()
            assert m1 is m2

    def test_shutdown_resets_instance(self) -> None:
        mp = _make_mock_pixet()
        with patch.dict("sys.modules", {"pypixet": mp}):
            PixetManager.initialize()
            PixetManager.shutdown()
            with pytest.raises(RuntimeError, match="not initialized"):
                PixetManager.instance()

    def test_list_devices_filters_file_device(self) -> None:
        mp = _make_mock_pixet()
        real = MagicMock()
        real.fullName.return_value = "MiniPIX 1"
        fake = MagicMock()
        fake.fullName.return_value = "FileDevice 0"
        mp.pixet.devices.return_value = [real, fake]
        with patch.dict("sys.modules", {"pypixet": mp}):
            mgr = PixetManager.initialize()
            devices = mgr.list_devices()
            assert len(devices) == 1
            assert devices[0] is real

    def test_instance_raises_before_init(self) -> None:
        with pytest.raises(RuntimeError, match="not initialized"):
            PixetManager.instance()


class MockDevice:
    def __init__(self, device_id: str, name: str = "MiniPIX") -> None:
        self._device_id = device_id
        self._name = name

    def deviceID(self) -> str:
        return self._device_id

    def fullName(self) -> str:
        return self._name

    def chipType(self) -> int:
        return 0

    def parameters(self) -> MagicMock:
        return MagicMock()

    def pixCfg(self) -> MagicMock:
        return MagicMock()

    def doSimpleAcquisition(self, *args: object) -> int:
        return 0

    def loadConfigFromFile(self, path: str) -> int:
        return 0


class TestMultiDeviceController:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        PixetManager._instance = None
        PixetManager._initialized = False

    def test_discover_and_match_by_sensor_id(self) -> None:
        mp = _make_mock_pixet()
        devices = [
            MockDevice("MiniPIX-E02-W0320"),
            MockDevice("MiniPIX-I03-W0320"),
            MockDevice("MiniPIX-J03-W0320"),
        ]
        mp.pixet.devices.return_value = devices
        with patch.dict("sys.modules", {"pypixet": mp}):
            mgr = PixetManager.initialize()
            ctrl = MultiDeviceController(mgr)
            mapping = ctrl.discover_and_match()
            assert len(mapping) == 3
            assert "E02" in mapping
            assert "I03" in mapping
            assert "J03" in mapping

    def test_discover_and_match_partial(self) -> None:
        mp = _make_mock_pixet()
        devices = [MockDevice("MiniPIX-E02-W0320")]
        mp.pixet.devices.return_value = devices
        with patch.dict("sys.modules", {"pypixet": mp}):
            mgr = PixetManager.initialize()
            ctrl = MultiDeviceController(mgr)
            mapping = ctrl.discover_and_match()
            assert len(mapping) <= 3
            assert "E02" in mapping

    def test_discover_and_match_no_devices(self) -> None:
        mp = _make_mock_pixet()
        mp.pixet.devices.return_value = []
        with patch.dict("sys.modules", {"pypixet": mp}):
            mgr = PixetManager.initialize()
            ctrl = MultiDeviceController(mgr)
            mapping = ctrl.discover_and_match()
            assert len(mapping) == 0

    def test_connect_all_creates_controllers(self) -> None:
        mp = _make_mock_pixet()
        devices = [
            MockDevice("MiniPIX-E02-W0320"),
            MockDevice("MiniPIX-I03-W0320"),
            MockDevice("MiniPIX-J03-W0320"),
        ]
        mp.pixet.devices.return_value = devices
        with patch.dict("sys.modules", {"pypixet": mp}):
            with patch("src.hardware.device_controller.DeviceController.connect"):
                mgr = PixetManager.initialize()
                ctrl = MultiDeviceController(mgr)
                ctrl.connect_all()
                assert len(ctrl.controllers) == 3
                for sid in SENSOR_IDS:
                    assert sid in ctrl.controllers

    def test_calibration_matching(self) -> None:
        from src.hardware.device_controller import DeviceController
        mp = _make_mock_pixet()
        dev = MockDevice("MiniPIX-E02-W0320")
        with patch.dict("sys.modules", {"pypixet": mp}):
            mgr = PixetManager.initialize()
            dc = DeviceController(mgr)
            dc.device = dev
            calib_dir = Path(__file__).resolve().parent.parent / "calibration"
            if calib_dir.exists():
                dc.load_calibration()

    def test_acquire_all_skips_disconnected(self) -> None:
        mp = _make_mock_pixet()
        with patch.dict("sys.modules", {"pypixet": mp}):
            mgr = PixetManager.initialize()
            ctrl = MultiDeviceController(mgr)
            ctrl.sensor_order = ["E02", "I03", "J03"]
            mock_ctrl = MagicMock()
            mock_ctrl.is_connected = True
            mock_ctrl.acquire_frame.return_value = "data"
            ctrl.controllers["E02"] = mock_ctrl
            results = ctrl.acquire_all()
            assert "E02" in results
            assert results["E02"] == "data"
