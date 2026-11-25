import json
import os
from pathlib import Path
from typing import Any


APP_NAME = "microSPLIT-R"
CONFIG_DIR = Path(os.environ.get("APPDATA", ".")) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "save_dir": str(Path.home() / "measurements"),
    "interval": 1.0,
    "model_path": "",
    "window_geometry": None,
    "log_level": "INFO",
    "alpha_filter_threshold": 1000,
}


class Config:
    def __init__(self, filepath: Path | None = None) -> None:
        self._filepath = filepath or CONFIG_FILE
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        self._data = DEFAULTS.copy()
        if self._filepath.exists():
            try:
                with open(self._filepath, encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def reset_to_defaults(self) -> None:
        self._data = DEFAULTS.copy()
