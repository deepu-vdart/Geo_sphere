"""
DALES-2 Dataset Adapter & Benchmark Tools (MVP 6)
Handles DALES-2 dataset specifications, tile indexing, semantic class mapping,
and synthetic benchmark generation for 3D object detection & semantic segmentation.

Reference:
DALES: A Large Scale Aerial LiDAR Dataset for Semantic Segmentation (Varney et al., 2020)
DALES-2: 15 semantic classes, 40+ tiles, 500M+ annotated airborne LiDAR returns.
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# ── DALES-2 15 Semantic Classes ───────────────────────────────────────────────
DALES_CLASSES: Dict[int, Dict[str, Any]] = {
    0:  {"name": "Ground",              "color": "#8B5A2B", "asprs": 2,  "category": "ground"},
    1:  {"name": "Vegetation",          "color": "#228B22", "asprs": 5,  "category": "vegetation"},
    2:  {"name": "Car",                 "color": "#FF4500", "asprs": 0,  "category": "vehicle"},
    3:  {"name": "Powerline",           "color": "#FFD700", "asprs": 14, "category": "infrastructure"},
    4:  {"name": "Fence",               "color": "#D2691E", "asprs": 0,  "category": "infrastructure"},
    5:  {"name": "Tree",                "color": "#006400", "asprs": 5,  "category": "tree"},
    6:  {"name": "Pick-up Truck",       "color": "#FF6347", "asprs": 0,  "category": "vehicle"},
    7:  {"name": "Van",                 "color": "#FF1493", "asprs": 0,  "category": "vehicle"},
    8:  {"name": "Truck",               "color": "#8A2BE2", "asprs": 0,  "category": "vehicle"},
    9:  {"name": "Utility Pole",        "color": "#00CED1", "asprs": 15, "category": "pole"},
    10: {"name": "Light Pole",          "color": "#1E90FF", "asprs": 15, "category": "pole"},
    11: {"name": "Traffic Light",       "color": "#4169E1", "asprs": 0,  "category": "pole"},
    12: {"name": "Building",            "color": "#DC143C", "asprs": 6,  "category": "building"},
    13: {"name": "Wire / Cable",        "color": "#F0E68C", "asprs": 13, "category": "infrastructure"},
    14: {"name": "Other",               "color": "#A0A0A0", "asprs": 0,  "category": "other"},
}

# Mapping from ASPRS standard classes to DALES-2 semantic labels
ASPRS_TO_DALES: Dict[int, int] = {
    0: 0,    # Created / Never classified -> Ground fallback
    1: 1,    # Unclassified -> Low vegetation fallback
    2: 0,    # Ground -> Ground
    3: 1,    # Low Vegetation -> Vegetation
    4: 1,    # Medium Vegetation -> Vegetation
    5: 5,    # High Vegetation -> Tree
    6: 12,   # Building -> Building
    7: 14,   # Low Point / Noise -> Other
    8: 14,   # Model Key Point -> Other
    9: 14,   # Water -> Other
    10: 14,  # Rail -> Other
    11: 14,  # Road Surface -> Other
    13: 13,  # Wire - Guard -> Wire / Cable
    14: 13,  # Wire - Conductor -> Wire / Cable
    15: 9,   # Transmission Tower -> Utility Pole
    16: 13,  # Wire-Structure Connector -> Wire / Cable
    17: 10,  # Bridge Deck -> Light Pole / Infra
    18: 14,  # High Noise -> Other
}

# Reverse mapping: DALES to ASPRS
DALES_TO_ASPRS: Dict[int, int] = {
    cls_id: meta["asprs"] for cls_id, meta in DALES_CLASSES.items()
}


class DALESAdapter:
    """
    Adapter for reading, converting, validating, and generating DALES-2 datasets.
    """

    @staticmethod
    def get_class_meta(class_id: int) -> Dict[str, Any]:
        """Return class metadata (name, hex color, ASPRS equivalent, category)."""
        return DALES_CLASSES.get(class_id, {
            "name": f"Class {class_id}",
            "color": "#94a3b8",
            "asprs": 0,
            "category": "other"
        })

    @staticmethod
    def parse_tile_id(filename: str) -> Optional[Dict[str, Any]]:
        """
        Parse DALES standard tile filename pattern:
        `dales2_{xmin}_{ymin}.laz` (e.g. `dales2_5080_54400.laz`)
        Tile coordinates are in NAD83 Ohio South State Plane (m).
        """
        import re
        m = re.search(r"dales2?_(\d+)_(\d+)", filename.lower())
        if not m:
            return None
        xmin = int(m.group(1)) * 1000
        ymin = int(m.group(2)) * 1000
        return {
            "tile_name": f"{m.group(1)}_{m.group(2)}",
            "crs": "EPSG:26913",  # NAD83 / Ohio South
            "bbox_native": {
                "min_x": xmin,
                "max_x": xmin + 500,
                "min_y": ymin,
                "max_y": ymin + 500
            }
        }

    @staticmethod
    def asprs_to_dales_array(classes: np.ndarray) -> np.ndarray:
        """Convert an array of ASPRS class codes into DALES-2 semantic labels."""
        dales_arr = np.full(classes.shape, 14, dtype=np.int32)
        for asprs_code, dales_code in ASPRS_TO_DALES.items():
            dales_arr[classes == asprs_code] = dales_code
        return dales_arr

    @staticmethod
    def generate_benchmark_tile(
        num_points: int = 5000,
        center_lon: float = -84.1896,
        center_lat: float = 39.7586,
        base_alt: float = 245.0
    ) -> Dict[str, Any]:
        """
        Generate a synthetic benchmark tile containing distinct, realistic 3D objects:
        - Ground plane with gentle slope
        - 2 Rectangular Buildings with distinct heights
        - 3 Vehicles (Cars & Pick-up) parked/driving
        - 4 Utility Poles along a road transect
        - 3 Tree clusters with dome canopies
        """
        np.random.seed(42)

        points_list: List[Tuple[float, float, float, int, int, int]] = []  # x, y, z, intensity, dales_cls, asprs_cls

        # 1. Ground Plane (60% of points)
        n_ground = int(num_points * 0.55)
        gx = np.random.uniform(-100, 100, n_ground)
        gy = np.random.uniform(-100, 100, n_ground)
        gz = base_alt + 0.02 * gx + 0.01 * gy + np.random.normal(0, 0.05, n_ground)
        g_int = np.random.randint(40, 120, n_ground)
        for i in range(n_ground):
            points_list.append((float(gx[i]), float(gy[i]), float(gz[i]), int(g_int[i]), 0, 2))

        # 2. Building 1: Office Structure (30m x 20m, 12m height) centered at (-30, 20)
        n_b1 = int(num_points * 0.15)
        b1_x = np.random.uniform(-45, -15, n_b1)
        b1_y = np.random.uniform(10, 30, n_b1)
        # Rooftop & walls
        b1_z = base_alt + 12.0 + np.random.normal(0, 0.1, n_b1)
        # 20% on walls
        wall_mask = np.random.rand(n_b1) < 0.25
        b1_z[wall_mask] = np.random.uniform(base_alt, base_alt + 12.0, wall_mask.sum())
        b1_int = np.random.randint(180, 255, n_b1)
        for i in range(n_b1):
            points_list.append((float(b1_x[i]), float(b1_y[i]), float(b1_z[i]), int(b1_int[i]), 12, 6))

        # 3. Building 2: Residential Structure (15m x 12m, 7m height) centered at (40, -30)
        n_b2 = int(num_points * 0.10)
        b2_x = np.random.uniform(32, 48, n_b2)
        b2_y = np.random.uniform(-36, -24, n_b2)
        b2_z = base_alt + 7.5 + np.random.normal(0, 0.1, n_b2)
        b2_int = np.random.randint(150, 220, n_b2)
        for i in range(n_b2):
            points_list.append((float(b2_x[i]), float(b2_y[i]), float(b2_z[i]), int(b2_int[i]), 12, 6))

        # 4. Vehicles (Cars & Trucks) parked near building 1
        # Car 1: 4.8m x 1.9m, 1.5m height at (-10, 5)
        n_v1 = int(num_points * 0.03)
        v1_x = np.random.uniform(-12.4, -7.6, n_v1)
        v1_y = np.random.uniform(4.0, 6.0, n_v1)
        v1_z = base_alt + np.random.uniform(0.3, 1.6, n_v1)
        v1_int = np.random.randint(120, 200, n_v1)
        for i in range(n_v1):
            points_list.append((float(v1_x[i]), float(v1_y[i]), float(v1_z[i]), int(v1_int[i]), 2, 0))

        # Car 2: Pick-up truck at (-5, 12)
        n_v2 = int(num_points * 0.03)
        v2_x = np.random.uniform(-7.5, -2.5, n_v2)
        v2_y = np.random.uniform(11.0, 13.0, n_v2)
        v2_z = base_alt + np.random.uniform(0.4, 2.0, n_v2)
        v2_int = np.random.randint(140, 210, n_v2)
        for i in range(n_v2):
            points_list.append((float(v2_x[i]), float(v2_y[i]), float(v2_z[i]), int(v2_int[i]), 6, 0))

        # 5. Utility Poles (Poles along y = -10 road)
        pole_locs = [(-50, -10), (-10, -10), (30, -10), (70, -10)]
        for px, py in pole_locs:
            n_pole = 25
            pole_z = np.linspace(base_alt, base_alt + 9.5, n_pole)
            pole_x = px + np.random.normal(0, 0.15, n_pole)
            pole_y = py + np.random.normal(0, 0.15, n_pole)
            pole_int = np.random.randint(190, 240, n_pole)
            for i in range(n_pole):
                points_list.append((float(pole_x[i]), float(pole_y[i]), float(pole_z[i]), int(pole_int[i]), 9, 15))

        # 6. Tree Clusters (3 trees with crown diameter ~6m and height 8-10m)
        tree_locs = [(-50, 50, 9.0), (10, 60, 10.5), (60, 30, 8.0)]
        for tx, ty, th in tree_locs:
            n_tree = int(num_points * 0.03)
            # Canopy dome
            theta = np.random.uniform(0, 2 * math.pi, n_tree)
            phi = np.random.uniform(0, math.pi / 2, n_tree)
            r = np.random.uniform(0.5, 3.5, n_tree)
            tree_x = tx + r * np.sin(phi) * np.cos(theta)
            tree_y = ty + r * np.sin(phi) * np.sin(theta)
            tree_z = base_alt + th - 2.5 + r * np.cos(phi)
            tree_int = np.random.randint(30, 90, n_tree)
            for i in range(n_tree):
                points_list.append((float(tree_x[i]), float(tree_y[i]), float(tree_z[i]), int(tree_int[i]), 5, 5))

        # Convert to numpy arrays
        arr = np.array(points_list, dtype=np.float64)
        x_m = arr[:, 0]
        y_m = arr[:, 1]
        z_m = arr[:, 2]
        intensity = arr[:, 3].astype(np.int32)
        dales_cls = arr[:, 4].astype(np.int32)
        asprs_cls = arr[:, 5].astype(np.int32)

        # Approximate conversion from meters offset to WGS84 coordinates
        # 1 deg lat ~ 111,000m, 1 deg lon ~ 111,000m * cos(lat)
        m_per_deg_lat = 111000.0
        m_per_deg_lon = 111000.0 * math.cos(math.radians(center_lat))

        lons = center_lon + (x_m / m_per_deg_lon)
        lats = center_lat + (y_m / m_per_deg_lat)

        return {
            "x": x_m,
            "y": y_m,
            "z": z_m,
            "lon": lons,
            "lat": lats,
            "intensity": intensity,
            "dales_classification": dales_cls,
            "asprs_classification": asprs_cls,
            "total_points": len(points_list),
            "center": {"lon": center_lon, "lat": center_lat, "alt": base_alt},
            "bounds": {
                "min_x": float(np.min(x_m)),
                "max_x": float(np.max(x_m)),
                "min_y": float(np.min(y_m)),
                "max_y": float(np.max(y_m)),
                "min_z": float(np.min(z_m)),
                "max_z": float(np.max(z_m)),
            }
        }


dales_adapter = DALESAdapter()
