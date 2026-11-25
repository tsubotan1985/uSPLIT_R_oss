import numpy as np

DEAD_PIXEL_THRESHOLD = 11000


def load_out_file(filepath: str | bytes) -> np.ndarray:
    return np.loadtxt(filepath, dtype=np.float64)


def preprocess(matrix: np.ndarray) -> np.ndarray:
    result = matrix.copy()
    result[result > DEAD_PIXEL_THRESHOLD] = 0
    row, col = result.shape
    margin = 2
    result[:margin, :] = 0
    result[-margin:, :] = 0
    result[:, :margin] = 0
    result[:, -margin:] = 0
    return result
