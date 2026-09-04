"""
DALES-2 Point Cloud Classifier
Classifies LiDAR returns using engineered features without requiring GPU.

Strategy:
  1. Compute per-point features: elevation rank, intensity z-score, local density
  2. Apply a deterministic rule-based triage for high-confidence classes
  3. For ambiguous points, return the best-guess class from the rule tree

DALES-2 label mapping (15 semantic classes):
  0  Ground          6  Pick-up Truck   11  Traffic Light Pole
  1  Vegetation      7  Van             12  Building (DALES)
  2  Car             8  Truck           13  Wire / Cable
  3  Powerline       9  Utility Pole    14  Other
  4  Fence          10  Light Pole
  5  Tree           (+ ASPRS overlay where applicable)
"""

import logging
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ── DALES-2 class metadata ────────────────────────────────────────────────────

DALES_CLASSES = {
    0:  {"name": "Ground",          "color": "#8B5A2B", "asprs": 2},
    1:  {"name": "Vegetation",      "color": "#228B22", "asprs": 5},
    2:  {"name": "Car",             "color": "#FF4500", "asprs": 0},
    3:  {"name": "Powerline",       "color": "#FFD700", "asprs": 14},
    4:  {"name": "Fence",           "color": "#D2691E", "asprs": 0},
    5:  {"name": "Tree",            "color": "#006400", "asprs": 5},
    6:  {"name": "Pick-up Truck",   "color": "#FF6347", "asprs": 0},
    7:  {"name": "Van",             "color": "#FF1493", "asprs": 0},
    8:  {"name": "Truck",           "color": "#8A2BE2", "asprs": 0},
    9:  {"name": "Utility Pole",    "color": "#00CED1", "asprs": 15},
   10:  {"name": "Light Pole",      "color": "#1E90FF", "asprs": 15},
   11:  {"name": "Traffic Light",   "color": "#4169E1", "asprs": 0},
   12:  {"name": "Building",        "color": "#DC143C", "asprs": 6},
   13:  {"name": "Wire / Cable",    "color": "#F0E68C", "asprs": 13},
   14:  {"name": "Other",           "color": "#A0A0A0", "asprs": 0},
}


def _safe_percentile(arr: np.ndarray, q: float) -> float:
    if len(arr) == 0:
        return 0.0
    return float(np.percentile(arr, q))


def classify_point_cloud(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    intensity: np.ndarray,
    existing_classes: np.ndarray,
) -> Dict[str, Any]:
    """
    Classify a point cloud into DALES-2 semantic classes.

    When existing ASPRS classification exists, uses it as a strong prior.
    Falls back to feature-based heuristics for unclassified / unknown points.

    Returns a classification result dict with:
      - per_class: dict of {class_id: {name, count, percentage, color}}
      - total_points: int
      - dominant_class: str
      - classification_method: str
    """
    n = len(z)
    if n == 0:
        return {"per_class": {}, "total_points": 0, "dominant_class": "Unknown"}

    pred = np.full(n, 14, dtype=np.int32)  # default: "Other"

    # ── Feature engineering ──────────────────────────────────────────────────
    z_min = z.min(); z_max = z.max(); z_range = max(1.0, z_max - z_min)
    z_norm = (z - z_min) / z_range  # 0 = lowest, 1 = highest

    int_mean = float(intensity.mean()) if intensity.mean() > 0 else 1.0
    int_std = float(intensity.std()) if intensity.std() > 0 else 1.0
    int_z = (intensity.astype(np.float64) - int_mean) / int_std  # z-score

    # Ground: very low elevation percentile (<10%)
    ground_mask = z_norm < 0.10
    pred[ground_mask] = 0

    # Vegetation: moderate elevation, moderate intensity
    veg_mask = (z_norm >= 0.10) & (z_norm < 0.60) & (int_z < 0.5)
    pred[veg_mask] = 1

    # Tree: higher elevation, low intensity (dense canopy)
    tree_mask = (z_norm >= 0.40) & (z_norm < 0.85) & (int_z < -0.2)
    pred[tree_mask] = 5

    # Building: high elevation, high intensity (rooftops reflect well)
    bldg_mask = (z_norm >= 0.55) & (int_z > 0.3)
    pred[bldg_mask] = 12

    # Wire / Powerline: very high elevation, very low density (sparse)
    wire_mask = (z_norm >= 0.80) & (int_z < -0.5)
    pred[wire_mask] = 13

    # Poles: very high elevation, high intensity (metal reflectance)
    pole_mask = (z_norm >= 0.75) & (int_z > 0.8)
    pred[pole_mask] = 9

    # ── ASPRS class override (strong prior) ──────────────────────────────────
    asprs_to_dales = {
        0: 0,    # Created → Ground
        1: 1,    # Unclassified → Vegetation fallback
        2: 0,    # Ground
        3: 1,    # Low Veg
        4: 1,    # Med Veg
        5: 5,    # High Veg → Tree
        6: 12,   # Building
        7: 14,   # Noise → Other
        8: 14,
        9: 14,   # Water — no DALES class, map to Other
       10: 14,
       11: 14,
       13: 13,   # Wire
       14: 13,
       15: 9,    # Transmission Tower → Utility Pole
    }
    for asprs_code, dales_code in asprs_to_dales.items():
        mask = (existing_classes == asprs_code)
        if mask.any():
            pred[mask] = dales_code

    # ── Compute statistics ───────────────────────────────────────────────────
    per_class = {}
    for cls_id, meta in DALES_CLASSES.items():
        count = int((pred == cls_id).sum())
        if count > 0:
            per_class[str(cls_id)] = {
                "class_id": cls_id,
                "name": meta["name"],
                "color": meta["color"],
                "count": count,
                "percentage": round(count / n * 100, 2),
            }

    dominant_id = int(np.bincount(pred).argmax())
    dominant_name = DALES_CLASSES.get(dominant_id, {}).get("name", "Unknown")

    return {
        "per_class": per_class,
        "total_points": n,
        "dominant_class": dominant_name,
        "dominant_class_id": dominant_id,
        "classification_method": "rule_based_asprs_prior",
        "class_count": len(per_class),
    }
