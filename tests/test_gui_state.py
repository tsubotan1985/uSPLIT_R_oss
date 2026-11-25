from pathlib import Path

import pytest

from src.config import Config
from src.gui.measurement_control import MeasurementControl


@pytest.fixture
def config(tmp_path: Path) -> Config:
    cfg = Config(filepath=tmp_path / "config.json")
    cfg.set("save_dir", str(tmp_path / "out"))
    return cfg


class TestMeasurementControl:
    def test_save_dir_comes_from_config(self, qapp, config: Config) -> None:
        widget = MeasurementControl(config)
        assert widget.save_path.text() == str(config.get("save_dir"))

    def test_default_save_dir_matches_config_default(self, qapp, tmp_path: Path) -> None:
        widget = MeasurementControl(Config(filepath=tmp_path / "fresh.json"))
        assert widget.save_path.text() == str(Path.home() / "uSPLIT-R")

    def test_hardware_unavailable_disables_start(self, qapp, config: Config) -> None:
        widget = MeasurementControl(config)
        widget.set_hardware_available(False, "Pixet SDK not found")
        assert widget.start_btn.isEnabled() is False
        assert "Pixet SDK not found" in widget.hw_label.text()
        assert widget.hw_label.isVisibleTo(widget) is True

    def test_hardware_available_enables_start(self, qapp, config: Config) -> None:
        widget = MeasurementControl(config)
        widget.set_hardware_available(False, "boom")
        widget.set_hardware_available(True)
        assert widget.start_btn.isEnabled() is True
        assert widget.hw_label.text() == ""

    def test_classifier_label_reflects_model(self, qapp, config: Config) -> None:
        widget = MeasurementControl(config)
        assert "rule-based" in widget.classifier_label.text()
        widget.set_classifier_label("/models/LGBM_20260526.joblib")
        assert "LGBM_20260526" in widget.classifier_label.text()
        widget.set_classifier_label(None)
        assert "rule-based" in widget.classifier_label.text()
