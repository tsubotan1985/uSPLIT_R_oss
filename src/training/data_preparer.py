import logging
from pathlib import Path

import numpy as np

from src.analysis.data_loader import load_out_file, preprocess
from src.analysis.feature_extractor import extract_features


_logger = logging.getLogger("usplit")


def prepare_from_folders(
    alpha_dir: str | Path,
    beta_dir: str | Path,
    gamma_dir: str | Path,
    alpha_threshold: float = 1000,
) -> tuple[np.ndarray, np.ndarray]:
    features_list: list[list[float]] = []
    labels_list: list[int] = []

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
                matrix = load_out_file(str(fpath))
                matrix = preprocess(matrix)
                features, _, _ = extract_features(matrix)
            except Exception:
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

    return np.array(features_list), np.array(labels_list)


def split_train_test(
    features: np.ndarray, labels: np.ndarray, test_ratio: float = 0.2
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    from sklearn.model_selection import train_test_split
    return train_test_split(features, labels, test_size=test_ratio, stratify=labels, random_state=42)
