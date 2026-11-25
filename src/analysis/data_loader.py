from pathlib import Path
from typing import Iterable
import warnings

import numpy as np


DEAD_PIXEL_THRESHOLD = 11000
EDGE_MARGIN = 2


class InvalidDataFileError(ValueError):
    """フレームファイルとして解釈できない入力。"""


def load_out_file(filepath: str | Path, edge_margin: int = EDGE_MARGIN) -> np.ndarray:
    """1フレーム分の .out を読み込み、最低限の妥当性を検証する。

    空ファイル・非矩形・NaN を含むファイルは InvalidDataFileError を送出する。
    """
    try:
        with warnings.catch_warnings():
            # 空ファイルは numpy が UserWarning を出す。ここでは例外として扱う
            warnings.simplefilter("ignore", UserWarning)
            matrix = np.loadtxt(filepath, dtype=np.float64, ndmin=2)
    except (ValueError, OSError) as e:
        raise InvalidDataFileError(f"{filepath}: 読み込みに失敗しました ({e})") from e

    if matrix.size == 0:
        raise InvalidDataFileError(f"{filepath}: データが空です")
    if matrix.ndim != 2:
        raise InvalidDataFileError(f"{filepath}: 2次元配列ではありません (shape={matrix.shape})")
    if matrix.shape[0] <= 2 * edge_margin or matrix.shape[1] <= 2 * edge_margin:
        raise InvalidDataFileError(f"{filepath}: 行列が小さすぎます (shape={matrix.shape})")
    if not np.all(np.isfinite(matrix)):
        raise InvalidDataFileError(f"{filepath}: NaN/Inf を含みます")
    return matrix


def load_out_files(
    paths: Iterable[str | Path], edge_margin: int = EDGE_MARGIN
) -> tuple[list[np.ndarray], list[tuple[Path, str]]]:
    """複数ファイルを読み、成功した行列と失敗（パス, 理由）を分けて返す。"""
    matrices: list[np.ndarray] = []
    failures: list[tuple[Path, str]] = []
    for p in paths:
        try:
            matrices.append(load_out_file(p, edge_margin=edge_margin))
        except InvalidDataFileError as e:
            failures.append((Path(p), str(e)))
    return matrices, failures


def preprocess(
    matrix: np.ndarray,
    dead_pixel_threshold: float = DEAD_PIXEL_THRESHOLD,
    edge_margin: int = EDGE_MARGIN,
) -> np.ndarray:
    """デッドピクセル除去と端の余白ゼロ埋め。入力は変更しない。"""
    if matrix.ndim != 2:
        raise InvalidDataFileError(f"2次元配列ではありません (shape={matrix.shape})")
    result = np.array(matrix, dtype=np.float64, copy=True)
    result[result > dead_pixel_threshold] = 0
    m = int(edge_margin)
    if m > 0:
        result[:m, :] = 0
        result[-m:, :] = 0
        result[:, :m] = 0
        result[:, -m:] = 0
    return result
