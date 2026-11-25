import json
from datetime import datetime
from pathlib import Path

import numpy as np
import joblib


def _convert(obj: object) -> object:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def _clean(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = _clean(v)
        elif isinstance(v, (list, tuple)):
            out[k] = [_convert(x) for x in v]
        else:
            out[k] = _convert(v)
    return out


MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


def save(model: object, path: str | Path, metadata: dict | None = None) -> Path:
    p = MODELS_DIR / Path(path)
    model_path = p.with_suffix(".joblib")
    joblib.dump(model, model_path)
    meta_path = p.with_name(p.stem + "_metadata.json")
    if metadata is None:
        metadata = {}
    metadata.setdefault("saved_at", datetime.now().isoformat())
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(_clean(metadata), f, indent=2, ensure_ascii=False)
    return model_path
