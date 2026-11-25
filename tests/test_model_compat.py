import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest

from src.analysis.classifier import FEATURE_KEYS, Classifier, ModelFeatureMismatch


def _fit_model(n_features: int, feature_names: list[str] | None = None) -> lgb.LGBMClassifier:
    rng = np.random.default_rng(0)
    X = rng.random((40, n_features))
    y = rng.integers(0, 3, size=40)
    model = lgb.LGBMClassifier(n_estimators=5, num_leaves=3, verbosity=-1)
    if feature_names is not None:
        model.fit(pd.DataFrame(X, columns=feature_names), y)
    else:
        model.fit(X, y)
    return model


def _save(model: object, directory: Path, stem: str = "model") -> Path:
    path = directory / f"{stem}.joblib"
    joblib.dump(model, path)
    return path


class TestModelCompatibility:
    def test_accepts_current_feature_set(self, tmp_path: Path) -> None:
        model = _fit_model(len(FEATURE_KEYS), FEATURE_KEYS)
        path = _save(model, tmp_path)
        clf = Classifier(path)
        assert clf.has_model is True
        assert clf.feature_names == FEATURE_KEYS

    def test_accepts_numpy_trained_model_with_auto_names(self, tmp_path: Path) -> None:
        # ndarray 学習だと Column_0.. の自動名になる。意味が分からないので判定しない
        model = _fit_model(len(FEATURE_KEYS))
        path = _save(model, tmp_path)
        clf = Classifier(path)
        assert clf.has_model is True
        assert clf.feature_names is None

    def test_rejects_different_feature_names(self, tmp_path: Path) -> None:
        other = FEATURE_KEYS[:13] + ["intensity_kurtosis"]
        model = _fit_model(len(other), other)
        path = _save(model, tmp_path)
        with pytest.raises(ModelFeatureMismatch, match="特徴量セットが違います"):
            Classifier(path)

    def test_rejects_different_feature_count(self, tmp_path: Path) -> None:
        model = _fit_model(len(FEATURE_KEYS) + 2)
        path = _save(model, tmp_path)
        with pytest.raises(ModelFeatureMismatch, match="特徴量の数"):
            Classifier(path)

    def test_rejects_incompatible_sidecar_metadata(self, tmp_path: Path) -> None:
        model = _fit_model(len(FEATURE_KEYS))
        path = _save(model, tmp_path)
        meta = {"selected_features": ["area", "area_bbox", "extent", "solidity"] + FEATURE_KEYS[4:]}
        path.with_name(f"{path.stem}_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        with pytest.raises(ModelFeatureMismatch, match="selected_features"):
            Classifier(path)

    def test_accepts_matching_sidecar_metadata(self, tmp_path: Path) -> None:
        model = _fit_model(len(FEATURE_KEYS))
        path = _save(model, tmp_path)
        path.with_name(f"{path.stem}_metadata.json").write_text(
            json.dumps({"selected_features": FEATURE_KEYS}), encoding="utf-8"
        )
        assert Classifier(path).has_model is True


class TestBundledModels:
    def test_incompatible_bundled_model_is_rejected(self) -> None:
        """同梱の旧モデルは現行実装と互換でないため、読み込み時に弾かれること。"""
        path = Path(__file__).resolve().parent.parent / "models" / "LGBM_20260120_142338.joblib"
        if not path.exists():
            pytest.skip("同梱モデルなし")
        with pytest.raises(ModelFeatureMismatch):
            Classifier(path)
