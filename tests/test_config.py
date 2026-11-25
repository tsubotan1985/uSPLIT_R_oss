import json
import pytest
from pathlib import Path

from src.config import Config, DEFAULTS


@pytest.fixture
def tmp_config(tmp_path: Path) -> Config:
    cfg = Config(filepath=tmp_path / "config.json")
    return cfg


class TestConfigDefaults:
    def test_load_returns_defaults_when_no_file(self, tmp_config: Config) -> None:
        assert tmp_config.get("interval") == 1.0
        assert tmp_config.get("log_level") == "INFO"
        assert tmp_config.get("save_dir") == str(Path.home() / "measurements")


class TestConfigRoundtrip:
    def test_save_and_load_returns_same_values(self, tmp_config: Config) -> None:
        tmp_config.set("interval", 0.1)
        tmp_config.set("save_dir", r"C:\tests")
        tmp_config.save()

        cfg2 = Config(filepath=tmp_config._filepath)
        assert cfg2.get("interval") == 0.1
        assert cfg2.get("save_dir") == r"C:\tests"

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c" / "config.json"
        cfg = Config(filepath=nested)
        cfg.set("interval", 10.0)
        cfg.save()
        assert nested.exists()
        with open(nested, encoding="utf-8") as f:
            data = json.load(f)
        assert data["interval"] == 10.0


class TestConfigGet:
    def test_get_with_default_fallback(self, tmp_config: Config) -> None:
        assert tmp_config.get("nonexistent", 42) == 42

    def test_get_returns_none_for_missing_key(self, tmp_config: Config) -> None:
        assert tmp_config.get("nonexistent") is None


class TestConfigPersistence:
    def test_manual_set_survives_reload(self, tmp_config: Config) -> None:
        tmp_config.set("interval", 0.1)
        tmp_config.save()

        cfg2 = Config(filepath=tmp_config._filepath)
        assert cfg2.get("interval") == 0.1
        assert cfg2.get("log_level") == "INFO"

    def test_reset_to_defaults(self, tmp_config: Config) -> None:
        tmp_config.set("interval", 999)
        tmp_config.reset_to_defaults()
        assert tmp_config.get("interval") == 1.0


class TestConfigCorruption:
    def test_invalid_json_falls_back_to_defaults(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "config.json"
        bad_file.write_text("{invalid json}", encoding="utf-8")
        cfg = Config(filepath=bad_file)
        assert cfg.get("interval") == 1.0
