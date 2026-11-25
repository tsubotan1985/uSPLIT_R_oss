from pathlib import Path

import numpy as np
import pytest

from src.analysis.data_loader import (
    InvalidDataFileError,
    load_out_file,
    load_out_files,
    preprocess,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


class TestLoadOutFile:
    def test_loads_valid_matrix(self, tmp_path: Path) -> None:
        p = _write(tmp_path / "ok.out", "1 2 3 4 5\n6 7 8 9 10\n1 1 1 1 1\n2 2 2 2 2\n3 3 3 3 3\n")
        matrix = load_out_file(p)
        assert matrix.shape == (5, 5)

    def test_raises_for_empty_file(self, tmp_path: Path) -> None:
        p = _write(tmp_path / "empty.out", "")
        with pytest.raises(InvalidDataFileError, match="空"):
            load_out_file(p)

    def test_raises_for_ragged_rows(self, tmp_path: Path) -> None:
        p = _write(tmp_path / "ragged.out", "1 2 3\n4 5\n6 7 8\n")
        with pytest.raises(InvalidDataFileError, match="読み込みに失敗"):
            load_out_file(p)

    def test_raises_for_too_small_matrix(self, tmp_path: Path) -> None:
        # 端2ピクセルを捨てるので 4x4 以下は使い物にならない
        p = _write(tmp_path / "small.out", "1 2 3\n4 5 6\n7 8 9\n")
        with pytest.raises(InvalidDataFileError, match="小さすぎます"):
            load_out_file(p)

    def test_raises_for_nan(self, tmp_path: Path) -> None:
        text = "\n".join(" ".join(["1"] * 5) for _ in range(5))
        p = _write(tmp_path / "nan.out", text.replace("1", "nan", 1))
        with pytest.raises(InvalidDataFileError, match="NaN"):
            load_out_file(p)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidDataFileError, match="読み込みに失敗"):
            load_out_file(tmp_path / "missing.out")


class TestLoadOutFiles:
    def test_separates_failures(self, tmp_path: Path) -> None:
        good = _write(tmp_path / "good.out", "\n".join(" ".join(["1"] * 5) for _ in range(5)))
        bad = _write(tmp_path / "bad.out", "")
        matrices, failures = load_out_files([good, bad])
        assert len(matrices) == 1
        assert len(failures) == 1
        assert failures[0][0] == bad


class TestPreprocess:
    def test_zeroes_dead_pixels_and_edges(self) -> None:
        matrix = np.full((5, 5), 1.0)
        matrix[2, 2] = 20000.0
        out = preprocess(matrix, dead_pixel_threshold=11000, edge_margin=1)
        assert out[2, 2] == 0
        assert np.all(out[0, :] == 0)
        assert np.all(out[:, 0] == 0)
        assert out[2, 2] != matrix[2, 2] or matrix[2, 2] == 0
        assert matrix[2, 2] == 20000.0  # 入力は変更しない

    def test_rejects_1d_input(self) -> None:
        with pytest.raises(InvalidDataFileError, match="2次元"):
            preprocess(np.zeros(5))
