from unittest.mock import MagicMock

import pytest

from src.gui import main_window as mw
from src.hardware.pixet_manager import PixetManager


@pytest.fixture
def hardware_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(cls):
        raise RuntimeError("Pixet SDK not found")

    monkeypatch.setattr(PixetManager, "initialize", classmethod(_boom))


@pytest.fixture
def hardware_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    ctrl = MagicMock()
    ctrl.sensor_order = []
    monkeypatch.setattr(PixetManager, "initialize", classmethod(lambda cls: object()))
    monkeypatch.setattr(mw, "MultiDeviceController", lambda mgr: ctrl)


class TestMainWindowSmoke:
    def test_without_hardware_disables_measurement(self, qapp, hardware_failure: None) -> None:
        window = mw.MainWindow()
        try:
            assert window.tabs.tabText(0) == "Measurement (no hardware)"
            assert window.meas_ctrl.start_btn.isEnabled() is False
            assert "Pixet SDK not found" in window.meas_ctrl.hw_label.text()
            assert window.meas_ctrl.save_path.text() != ""
        finally:
            window.close()

    def test_with_hardware_enables_measurement(self, qapp, hardware_ok: None) -> None:
        window = mw.MainWindow()
        try:
            assert window.tabs.tabText(0) == "Measurement"
            assert window.meas_ctrl.start_btn.isEnabled() is True
            assert window.meas_ctrl.hw_label.text() == ""
        finally:
            window.close()

    def test_rule_thresholds_come_from_config(self, qapp, hardware_failure: None) -> None:
        window = mw.MainWindow()
        try:
            thresholds = window._classifier.rule_thresholds
            assert set(thresholds) == {
                "alpha_max_intensity",
                "alpha_max_area",
                "beta_min_area",
                "beta_min_intensity",
            }
        finally:
            window.close()
