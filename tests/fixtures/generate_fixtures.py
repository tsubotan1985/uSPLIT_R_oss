import numpy as np
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent
TRAIN_DIR = FIXTURE_DIR / "train_samples"
SIZE = 256


def make_alpha() -> np.ndarray:
    data = np.zeros((SIZE, SIZE))
    data[50:52, 50:52] = 8000
    data[100:101, 100:101] = 9000
    data[150:152, 150:152] = 7000
    return data


def make_beta() -> np.ndarray:
    data = np.random.rand(SIZE, SIZE) * 500
    data[50:60, 50:60] = np.random.rand(10, 10) * 3000
    data[120:135, 120:135] = np.random.rand(15, 15) * 2500
    return data


def make_gamma() -> np.ndarray:
    data = np.random.rand(SIZE, SIZE) * 200
    data[80:81, 80:81] = 1500
    data[180:181, 180:181] = 1200
    return data


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    TRAIN_DIR.mkdir(parents=True, exist_ok=True)

    for prefix, maker in [("alpha", make_alpha), ("beta", make_beta), ("gamma", make_gamma)]:
        for i in range(1, 6):
            data = maker()
            noise = np.random.rand(SIZE, SIZE) * 100
            data += noise
            filepath = TRAIN_DIR / f"{prefix}_{i:03d}.out"
            np.savetxt(filepath, data, fmt="%d")
            print(f"Created: {filepath}")

    # Single fixture files
    for name, maker in [("alpha_sample.out", make_alpha), ("beta_sample.out", make_beta), ("gamma_sample.out", make_gamma)]:
        data = maker()
        filepath = FIXTURE_DIR / name
        np.savetxt(filepath, data, fmt="%d")
        print(f"Created: {filepath}")

    print("Fixtures generated successfully.")


if __name__ == "__main__":
    main()
