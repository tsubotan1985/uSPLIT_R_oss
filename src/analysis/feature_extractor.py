import numpy as np
from skimage.measure import label, regionprops


def extract_features(matrix: np.ndarray) -> tuple[list[dict], np.ndarray, list]:
    binary = matrix > 0
    labelled = label(binary)
    props = regionprops(labelled, intensity_image=matrix)
    features = []
    for rp in props:
        features.append({
            "area": int(rp.area),
            "perimeter": float(rp.perimeter),
            "centroid_row": float(rp.centroid[0]),
            "centroid_col": float(rp.centroid[1]),
            "intensity_max": float(rp.intensity_max),
            "intensity_mean": float(rp.intensity_mean),
            "intensity_sum": float(rp.intensity_mean * rp.area),
            "intensity_std": float(np.std(rp.intensity_image[rp.image])),
            "bbox_height": int(rp.bbox[2] - rp.bbox[0]),
            "bbox_width": int(rp.bbox[3] - rp.bbox[1]),
            "eccentricity": float(rp.eccentricity),
            "solidity": float(rp.solidity),
            "extent": float(rp.extent),
            "orientation": float(rp.orientation),
        })
    return features, labelled, props
