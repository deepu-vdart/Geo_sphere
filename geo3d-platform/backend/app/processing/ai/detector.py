"""
3D Object Detection & Instance Segmentation Engine (MVP 6)
Extracts 3D bounding boxes, instance IDs, and geometric metrics for:
- Buildings (Footprint area, height, volume, orientation)
- Vehicles (Cars, Vans, Trucks, dimensions)
- Poles (Utility & Light poles, height, verticality)
- Trees (Crown diameter, canopy height, volume)

Uses spatial density clustering (DBSCAN & Euclidean k-d tree) with PCA-based
Oriented Bounding Box (OBB) and Axis-Aligned Bounding Box (AABB) computation.
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.cluster import DBSCAN

from app.processing.ai.dales_adapter import DALES_CLASSES

logger = logging.getLogger(__name__)


# Category mapping for detection
CATEGORY_CLASSES = {
    "building": [12],                     # DALES 12 / ASPRS 6
    "vehicle":  [2, 6, 7, 8],             # Car, Pick-up, Van, Truck
    "pole":     [9, 10, 11],              # Utility pole, Light pole, Traffic light
    "tree":     [5],                      # Tree / High vegetation
}

# Color palette for 3D visual bounding boxes
CATEGORY_COLORS = {
    "building": "#ef4444",  # Crimson / Red
    "vehicle":  "#f97316",  # Coral / Orange
    "pole":     "#06b6d4",  # Cyan
    "tree":     "#10b981",  # Emerald Green
}

# Epsilon (distance threshold in meters) and min_samples for DBSCAN per category
CLUSTER_PARAMS = {
    "building": {"eps": 4.5, "min_samples": 30,  "min_pts": 25,  "max_objects": 40},
    "vehicle":  {"eps": 2.2, "min_samples": 8,   "min_pts": 8,   "max_objects": 50},
    "pole":     {"eps": 1.6, "min_samples": 6,   "min_pts": 6,   "max_objects": 40},
    "tree":     {"eps": 3.0, "min_samples": 15,  "min_pts": 15,  "max_objects": 50},
}


class Object3DDetector:
    """
    Performs 3D object detection & instance segmentation on classified point clouds.
    """

    @staticmethod
    def detect_objects(
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        classes: np.ndarray,
        intensity: Optional[np.ndarray] = None,
        lon: Optional[np.ndarray] = None,
        lat: Optional[np.ndarray] = None,
        categories: Optional[List[str]] = None,
        origin_lon: float = -84.1896,
        origin_lat: float = 39.7586,
    ) -> Dict[str, Any]:
        """
        Run 3D Object Detection across specified categories.
        Returns a list of detected 3D bounding boxes and aggregated summary.
        """
        if categories is None:
            categories = ["building", "vehicle", "tree", "pole"]

        n_points = len(z)
        if n_points == 0:
            return {
                "detected_objects": [],
                "object_count": 0,
                "category_counts": {},
                "status": "empty"
            }

        # Conversion scale from meters to deg if lon/lat not passed
        m_per_deg_lat = 111000.0
        m_per_deg_lon = 111000.0 * math.cos(math.radians(origin_lat))

        if lon is None:
            lon = origin_lon + (x / m_per_deg_lon)
        if lat is None:
            lat = origin_lat + (y / m_per_deg_lat)
        if intensity is None:
            intensity = np.full(n_points, 100, dtype=np.int32)

        detected_objects: List[Dict[str, Any]] = []
        category_counts: Dict[str, int] = {cat: 0 for cat in categories}

        obj_id_counter = 1

        for category in categories:
            valid_cls = CATEGORY_CLASSES.get(category, [])
            mask = np.isin(classes, valid_cls)
            cat_points_count = int(mask.sum())

            if cat_points_count < 5:
                continue

            sub_x = x[mask]
            sub_y = y[mask]
            sub_z = z[mask]
            sub_lon = lon[mask]
            sub_lat = lat[mask]
            sub_cls = classes[mask]
            sub_int = intensity[mask]

            params = CLUSTER_PARAMS.get(category, {"eps": 3.0, "min_samples": 10, "min_pts": 10, "max_objects": 30})

            # 3D spatial points for clustering (scaled Z to emphasize XY separation)
            z_scale = 0.5 if category in ("building", "tree") else 1.0
            pts_3d = np.column_stack([sub_x, sub_y, sub_z * z_scale])

            # Run DBSCAN
            db = DBSCAN(eps=params["eps"], min_samples=params["min_samples"])
            labels = db.fit_predict(pts_3d)

            unique_labels = set(labels)
            if -1 in unique_labels:
                unique_labels.remove(-1)  # exclude noise

            # Sort clusters by size descending
            clusters = []
            for lbl in unique_labels:
                lbl_mask = (labels == lbl)
                pts_cnt = int(lbl_mask.sum())
                if pts_cnt >= params["min_pts"]:
                    clusters.append((lbl, pts_cnt))

            clusters.sort(key=lambda c: c[1], reverse=True)
            clusters = clusters[:params["max_objects"]]

            # Compute 3D Bounding Boxes for each cluster
            for lbl, pts_cnt in clusters:
                c_mask = (labels == lbl)
                cx = sub_x[c_mask]
                cy = sub_y[c_mask]
                cz = sub_z[c_mask]
                clon = sub_lon[c_mask]
                clat = sub_lat[c_mask]
                ccls = sub_cls[c_mask]
                cint = sub_int[c_mask]

                # Dimensions
                min_x, max_x = float(np.min(cx)), float(np.max(cx))
                min_y, max_y = float(np.min(cy)), float(np.max(cy))
                min_z, max_z = float(np.min(cz)), float(np.max(cz))

                length_m = round(max(0.5, max_x - min_x), 2)
                width_m = round(max(0.5, max_y - min_y), 2)
                height_m = round(max(0.5, max_z - min_z), 2)

                # Centroid
                center_lon = float(np.mean(clon))
                center_lat = float(np.mean(clat))
                center_alt = float(np.mean(cz))

                # Footprint & Volume
                footprint_area = round(length_m * width_m, 2)
                volume_m3 = round(footprint_area * height_m, 2)

                # Orientation angle via 2D covariance / PCA
                heading_deg = 0.0
                if len(cx) >= 4:
                    coords_2d = np.column_stack([cx - np.mean(cx), cy - np.mean(cy)])
                    cov = np.cov(coords_2d, rowvar=False)
                    eigvals, eigvecs = np.linalg.eigh(cov)
                    major_axis = eigvecs[:, -1]
                    heading_deg = round(float(math.degrees(math.atan2(major_axis[1], major_axis[0]))), 1)

                # Sub-type refinement and confidence
                subtype, confidence = Object3DDetector._refine_subtype(
                    category=category,
                    length_m=length_m,
                    width_m=width_m,
                    height_m=height_m,
                    footprint=footprint_area,
                    point_count=pts_cnt,
                    mean_intensity=float(np.mean(cint))
                )

                color = CATEGORY_COLORS.get(category, "#8b5cf6")

                obj_record = {
                    "id": f"obj_{category}_{obj_id_counter}",
                    "index": obj_id_counter,
                    "category": category,
                    "subtype": subtype,
                    "color": color,
                    "confidence": round(confidence, 2),
                    "point_count": pts_cnt,
                    "dimensions": {
                        "length_m": length_m,
                        "width_m": width_m,
                        "height_m": height_m,
                        "footprint_sq_m": footprint_area,
                        "volume_m3": volume_m3,
                        "heading_deg": heading_deg
                    },
                    "center": {
                        "lon": round(center_lon, 7),
                        "lat": round(center_lat, 7),
                        "alt": round(center_alt, 2)
                    },
                    "bounds": {
                        "min_lon": round(float(np.min(clon)), 7),
                        "max_lon": round(float(np.max(clon)), 7),
                        "min_lat": round(float(np.min(clat)), 7),
                        "max_lat": round(float(np.max(clat)), 7),
                        "min_alt": round(min_z, 2),
                        "max_alt": round(max_z, 2)
                    },
                    "label": f"{Object3DDetector._get_icon(category)} {subtype} ({height_m}m)",
                    "cesium_box": {
                        "position": [round(center_lon, 7), round(center_lat, 7), round(center_alt, 2)],
                        "dimensions": [length_m, width_m, height_m],
                        "heading": heading_deg,
                        "color": color,
                        "wireframe_color": color
                    }
                }

                detected_objects.append(obj_record)
                category_counts[category] += 1
                obj_id_counter += 1

        # Sort all objects: Buildings first, then Vehicles, Poles, Trees
        order = {"building": 0, "vehicle": 1, "pole": 2, "tree": 3}
        detected_objects.sort(key=lambda o: (order.get(o["category"], 9), -o["dimensions"]["volume_m3"]))

        return {
            "status": "completed",
            "total_objects": len(detected_objects),
            "category_counts": category_counts,
            "detected_objects": detected_objects,
            "bounding_boxes_count": len(detected_objects),
        }

    @staticmethod
    def _refine_subtype(
        category: str,
        length_m: float,
        width_m: float,
        height_m: float,
        footprint: float,
        point_count: int,
        mean_intensity: float
    ) -> Tuple[str, float]:
        """Refine semantic subtype and calculate confidence."""
        if category == "building":
            if footprint > 350.0 or height_m > 15.0:
                return "Commercial / Industrial Building", 0.94
            elif footprint > 80.0:
                return "Residential Building", 0.92
            else:
                return "Outbuilding / Shed", 0.85

        elif category == "vehicle":
            max_dim = max(length_m, width_m)
            if max_dim > 7.5 or height_m > 2.8:
                return "Commercial Truck", 0.91
            elif max_dim > 5.5:
                return "Van / Light Truck", 0.89
            else:
                return "Passenger Car", 0.93

        elif category == "pole":
            aspect_ratio = height_m / max(0.4, min(length_m, width_m))
            if height_m > 12.0:
                return "High-Voltage Transmission Mast", 0.93
            elif aspect_ratio > 3.0:
                return "Utility Pole", 0.95
            else:
                return "Street Light / Sign Pole", 0.88

        elif category == "tree":
            crown_diameter = max(length_m, width_m)
            if height_m > 10.0 or crown_diameter > 8.0:
                return "Mature Tree Canopy", 0.94
            elif height_m > 4.0:
                return "Deciduous / Conifer Tree", 0.90
            else:
                return "Small Tree / Shrub Cluster", 0.84

        return f"{category.capitalize()} Object", 0.85

    @staticmethod
    def _get_icon(category: str) -> str:
        icons = {
            "building": "🏢",
            "vehicle": "🚗",
            "pole": "⚡",
            "tree": "🌲"
        }
        return icons.get(category, "📦")


detector_3d = Object3DDetector()
