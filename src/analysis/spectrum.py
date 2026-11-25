import numpy as np


def compute_energy_spectrum(
    matrix: np.ndarray,
    cluster_labels: np.ndarray,
    classification: list[dict],
    num_bins: int = 256,
) -> dict[str, np.ndarray]:
    spectra: dict[str, list[float]] = {"alpha": [], "beta": [], "gamma": [], "total": []}
    label_ids = np.unique(cluster_labels)
    label_ids = label_ids[label_ids > 0]
    for i, label_id in enumerate(label_ids):
        mask = cluster_labels == label_id
        total_energy = float(np.sum(matrix[mask]))
        if i < len(classification):
            cls = classification[i]["class"]
            key = ["alpha", "beta", "gamma"][cls] if cls < 3 else "total"
            spectra[key].append(total_energy)
        spectra["total"].append(total_energy)
    result = {}
    for key, values in spectra.items():
        if values:
            hist, _ = np.histogram(values, bins=num_bins, range=(0, max(values)))
            result[key] = hist
        else:
            result[key] = np.zeros(num_bins, dtype=int)
    return result
