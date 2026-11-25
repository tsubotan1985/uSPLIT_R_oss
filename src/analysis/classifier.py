import json
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np


FEATURE_KEYS = [
    "area", "perimeter", "centroid_row", "centroid_col",
    "intensity_max", "intensity_mean", "intensity_sum", "intensity_std",
    "bbox_height", "bbox_width", "eccentricity", "solidity", "extent", "orientation",
]

DEFAULT_RULE_THRESHOLDS = {
    "alpha_max_intensity": 5000.0,
    "alpha_max_area": 5.0,
    "beta_min_area": 5.0,
    "beta_min_intensity": 2000.0,
}

# LightGBM は ndarray で学習すると "Column_0" のような自動名を付ける。
# 自動名からは特徴量の意味が分からないので、互換性判定には使わない。
_AUTO_NAME = re.compile(r"^(Column|column|Feature|feature)_?\d+$")


class ModelFeatureMismatch(ValueError):
    """モデルの特徴量が現行の feature_extractor の出力と一致しない。"""


def _informative_names(names: Any) -> list[str] | None:
    if not names:
        return None
    out = [str(n) for n in names]
    if all(_AUTO_NAME.match(n) for n in out):
        return None
    return out


class Classifier:
    def __init__(
        self,
        model_path: str | Path | None = None,
        rule_thresholds: dict[str, float] | None = None,
    ) -> None:
        self._model: Any = None
        self._feature_names: list[str] | None = None
        self._rule_thresholds: dict[str, float] = {**DEFAULT_RULE_THRESHOLDS, **(rule_thresholds or {})}
        if model_path is not None:
            self.load_model(model_path)

    @property
    def has_model(self) -> bool:
        return self._model is not None

    @property
    def feature_names(self) -> list[str] | None:
        return self._feature_names

    @property
    def rule_thresholds(self) -> dict[str, float]:
        return dict(self._rule_thresholds)

    def load_model(self, model_path: str | Path) -> None:
        """モデルを読み込み、現行の特徴量セットと互換性があるか検証する。

        互換性がない場合は ModelFeatureMismatch を送出する。列名なしの ndarray で
        学習されたモデルは列順がそのまま推論に使われるため、検証しないと
        エラーにならずに誤分類が続く。
        """
        path = Path(model_path)
        model = joblib.load(path)
        names = self._extract_feature_names(model)
        self._validate_compatibility(model, names, path)
        self._model = model
        self._feature_names = names

    @staticmethod
    def _extract_feature_names(model: Any) -> list[str] | None:
        for attr in ("feature_name_", "feature_names_in_"):
            names = _informative_names(getattr(model, attr, None))
            if names is not None:
                return names
        booster = getattr(model, "booster_", None)
        if booster is not None:
            try:
                return _informative_names(booster.feature_name())
            except Exception:
                return None
        return None

    @classmethod
    def _validate_compatibility(cls, model: Any, names: list[str] | None, path: Path) -> None:
        n = getattr(model, "n_features_in_", None)
        if n is not None and int(n) != len(FEATURE_KEYS):
            raise ModelFeatureMismatch(
                f"{path.name}: 特徴量の数が {n} で、現行の {len(FEATURE_KEYS)} と一致しません"
            )
        if names is not None and names != FEATURE_KEYS:
            missing = [k for k in FEATURE_KEYS if k not in names]
            extra = [k for k in names if k not in FEATURE_KEYS]
            raise ModelFeatureMismatch(
                f"{path.name}: 学習時と現行実装で特徴量セットが違います"
                f"（不足: {missing or 'なし'} / 余剰: {extra or 'なし'}）"
            )
        declared = cls._load_declared_features(path)
        if declared is not None and declared != FEATURE_KEYS:
            missing = [k for k in FEATURE_KEYS if k not in declared]
            extra = [k for k in declared if k not in FEATURE_KEYS]
            raise ModelFeatureMismatch(
                f"{path.name}: メタデータの selected_features が現行実装と一致しません"
                f"（不足: {missing or 'なし'} / 余剰: {extra or 'なし'}）"
            )

    @staticmethod
    def _load_declared_features(path: Path) -> list[str] | None:
        meta_path = path.with_name(f"{path.stem}_metadata.json")
        if not meta_path.exists():
            return None
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        declared = meta.get("selected_features")
        if isinstance(declared, list) and declared:
            return [str(k) for k in declared]
        return None

    def predict(self, features_list: list[dict]) -> list[dict]:
        if not features_list:
            return []
        if self._model is None:
            return self._rule_based_predict(features_list)
        X = np.array([[f[k] for k in FEATURE_KEYS] for f in features_list])
        classes = self._model.predict(X)
        probs = self._model.predict_proba(X) if hasattr(self._model, "predict_proba") else None
        results = []
        for i, cls in enumerate(classes):
            result: dict = {"class": int(cls)}
            if probs is not None:
                result["confidence"] = float(np.max(probs[i]))
            results.append(result)
        return results

    def _rule_based_predict(self, features_list: list[dict]) -> list[dict]:
        th = self._rule_thresholds
        results = []
        for f in features_list:
            imax = f["intensity_max"]
            area = f["area"]
            if imax > th["alpha_max_intensity"] and area <= th["alpha_max_area"]:
                cls = 0
            elif area > th["beta_min_area"] and imax > th["beta_min_intensity"]:
                cls = 1
            else:
                cls = 2
            results.append({"class": cls, "confidence": 0.0})
        return results
