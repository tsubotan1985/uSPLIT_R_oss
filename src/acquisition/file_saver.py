import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


def create_measurement_dir(base_path: str | Path) -> Path:
    base = Path(base_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = base / f"measurement_{timestamp}"
    for i in range(1, 4):
        (root / f"Sensor{i:02d}").mkdir(parents=True, exist_ok=True)
    (root / "analysis_results").mkdir(exist_ok=True)
    return root


def save_frame(
    data: np.ndarray,
    sensor_id: str,
    frame_number: int,
    measurement_dir: Path,
) -> Path:
    sensor_dir = measurement_dir / sensor_id
    filename = f"frame_{frame_number:06d}.out"
    filepath = sensor_dir / filename
    np.savetxt(filepath, data, fmt="%d")
    return filepath


def save_metadata(measurement_dir: Path, metadata: dict[str, Any]) -> Path:
    filepath = measurement_dir / "metadata.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    return filepath
