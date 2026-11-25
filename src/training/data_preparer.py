import logging
from pathlib import Path
from typing import Callable

import numpy as np

from src.analysis.data_loader import (
    DEAD_PIXEL_THRESHOLD,
    EDGE_MARGIN,
    InvalidDataFileError,
    load_out_file,
    preprocess,
)
from src.analysis.feature_extractor import extract_features


_logger = logging.getLogger("usplit")


def prepare_from_folders(
    alpha_dir: str | Path,
    beta_dir: str | Path,
    gamma_dir: str | Path,
    alpha_threshold: float = 1000,
    dead_pixel_threshold: float | None = None,
    edge_margin: int | None = None,
    on_skip: Callable[[Path, str], None] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    features_list: list[list[float]] = []
    labels_list: list[int] = []
    skipped: list[tuple[Path, str]] = []
    dead = DEAD_PIXEL_THRESHOLD if dead_pixel_threshold is None else float(dead_pixel_threshold)
    margin = EDGE_MARGIN if edge_margin is None else int(edge_margin)

    EXTENSIONS = ["*.out", "*.txt", "*.dat", "*.asc"]
    for label, dir_path in [(0, alpha_dir), (1, beta_dir), (2, gamma_dir)]:
        d = Path(dir_path)
        if not d.exists():
            continue
        files: list[Path] = []
        for ext in EXTENSIONS:
            files.extend(d.glob(ext))
        files = sorted(set(files))
        _logger.info(f"prepare_from_folders: {d.name}: {len(files)} files")
        for fpath in files:
            try:
                matrix = load_out_file(str(fpath), edge_margin=margin)
                matrix = preprocess(matrix, dead_pixel_threshold=dead, edge_margin=margin)
                features, _, _ = extract_features(matrix)
            except (InvalidDataFileError, OSError, ValueError) as e:
                # 1ファイルの破損で学習全体を止めない。理由は残す
                skipped.append((fpath, str(e)))
                _logger.warning(f"skip {fpath.name}: {e}")
                if on_skip is not None:
                    on_skip(fpath, str(e))
                continue
            for feat in features:
                if label == 0 and feat["intensity_max"] < alpha_threshold:
                    continue
                features_list.append([
                    feat["area"],
                    feat["perimeter"],
                    feat["centroid_row"],
                    feat["centroid_col"],
                    feat["intensity_max"],
                    feat["intensity_mean"],
                    feat["intensity_sum"],
                    feat["intensity_std"],
                    feat["bbox_height"],
                    feat["bbox_width"],
                    feat["eccentricity"],
                    feat["solidity"],
                    feat["extent"],
                    feat["orientation"],
                ])
                labels_list.append(label)

    if skipped:
        _logger.warning(f"prepare_from_folders: {len(skipped)} ファイルをスキップしました")
    return np.array(features_list), np.array(labels_list)


def split_train_test(
    features: np.ndarray, labels: np.ndarray, test_ratio: float = 0.2
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    from sklearn.model_selection import train_test_split
    return train_test_split(features, labels, test_size=test_ratio, stratify=labels, random_state=42)
