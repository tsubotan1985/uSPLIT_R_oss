import joblib
import numpy as np
from pathlib import Path
from typing import Any


class Classifier:
    def __init__(self, model_path: str | Path | None = None) -> None:
        self._model: Any = None
        if model_path is not None:
            self.load_model(model_path)

    def load_model(self, model_path: str | Path) -> None:
        self._model = joblib.load(model_path)

    _FEATURE_KEYS = [
        "area", "perimeter", "centroid_row", "centroid_col",
        "intensity_max", "intensity_mean", "intensity_sum", "intensity_std",
        "bbox_height", "bbox_width", "eccentricity", "solidity", "extent", "orientation",
    ]

    def predict(self, features_list: list[dict]) -> list[dict]:
        if not features_list:
            return []
        if self._model is None:
            return self._rule_based_predict(features_list)
        X = np.array([[f[k] for k in self._FEATURE_KEYS] for f in features_list])
        classes = self._model.predict(X)
        probs = self._model.predict_proba(X) if hasattr(self._model, "predict_proba") else None
        results = []
        for i, cls in enumerate(classes):
            result: dict = {"class": int(cls)}
            if probs is not None:
                result["confidence"] = float(np.max(probs[i]))
            results.append(result)
        return results

    @staticmethod
    def _rule_based_predict(features_list: list[dict]) -> list[dict]:
        results = []
        for f in features_list:
            imax = f["intensity_max"]
            area = f["area"]
            if imax > 5000 and area <= 5:
                cls = 0
            elif area > 5 and imax > 2000:
                cls = 1
            else:
                cls = 2
            results.append({"class": cls, "confidence": 0.0})
        return results
