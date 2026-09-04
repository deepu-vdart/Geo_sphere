"""
Spatial Measurement Module
Computes 3D Euclidean distance, geodesic distance, vertical height differences,
and 2D/3D polygon surface areas and perimeters.
"""

import math
from typing import List, Dict, Any, Tuple
import pyproj
from shapely.geometry import Polygon

GEOD = pyproj.Geod(ellps="WGS84")


def compute_distance_metrics(points: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Compute 2D geodesic distance, 3D Euclidean distance, and segment breakdowns
    for a list of {lon, lat, alt} points.
    """
    if len(points) < 2:
        return {
            "total_horizontal_distance_m": 0.0,
            "total_3d_distance_m": 0.0,
            "segments": [],
            "elevation_diff_m": 0.0,
            "point_count": len(points)
        }

    total_horiz = 0.0
    total_3d = 0.0
    segments = []

    # Project to ECEF for precise 3D Euclidean distance
    ecef_transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)

    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]

        # Geodesic horizontal distance
        _, _, horiz_dist = GEOD.inv(p1["lon"], p1["lat"], p2["lon"], p2["lat"])

        # 3D ECEF distance
        x1, y1, z1 = ecef_transformer.transform(p1["lon"], p1["lat"], p1.get("alt", 0.0))
        x2, y2, z2 = ecef_transformer.transform(p2["lon"], p2["lat"], p2.get("alt", 0.0))
        dist_3d = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

        delta_z = p2.get("alt", 0.0) - p1.get("alt", 0.0)
        slope_pct = (delta_z / max(0.001, horiz_dist)) * 100.0 if horiz_dist > 0 else 0.0
        slope_deg = math.degrees(math.atan2(abs(delta_z), max(0.001, horiz_dist)))

        total_horiz += horiz_dist
        total_3d += dist_3d

        segments.append({
            "segment_index": i + 1,
            "from_point": {"lon": p1["lon"], "lat": p1["lat"], "alt": p1.get("alt", 0.0)},
            "to_point": {"lon": p2["lon"], "lat": p2["lat"], "alt": p2.get("alt", 0.0)},
            "horizontal_distance_m": round(horiz_dist, 2),
            "distance_3d_m": round(dist_3d, 2),
            "delta_z_m": round(delta_z, 2),
            "slope_degrees": round(slope_deg, 1),
            "slope_percent": round(slope_pct, 1)
        })

    first_pt = points[0]
    last_pt = points[-1]
    total_delta_z = last_pt.get("alt", 0.0) - first_pt.get("alt", 0.0)

    return {
        "point_count": len(points),
        "total_horizontal_distance_m": round(total_horiz, 2),
        "total_3d_distance_m": round(total_3d, 2),
        "elevation_diff_m": round(total_delta_z, 2),
        "segments": segments
    }


def compute_area_metrics(points: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Compute polygon surface area (m², hectares, acres, km²) and perimeter.
    """
    if len(points) < 3:
        return {
            "area_sq_m": 0.0,
            "area_hectares": 0.0,
            "area_acres": 0.0,
            "area_sq_km": 0.0,
            "perimeter_m": 0.0,
            "vertex_count": len(points)
        }

    lons = [p["lon"] for p in points]
    lats = [p["lat"] for p in points]

    # Geodesic polygon area
    poly_area, poly_perim = GEOD.polygon_area_perimeter(lons, lats)
    area_sq_m = abs(poly_area)
    perimeter_m = abs(poly_perim)

    return {
        "vertex_count": len(points),
        "area_sq_m": round(area_sq_m, 2),
        "area_hectares": round(area_sq_m / 10000.0, 4),
        "area_acres": round(area_sq_m * 0.000247105, 4),
        "area_sq_km": round(area_sq_m / 1_000_000.0, 6),
        "perimeter_m": round(perimeter_m, 2)
    }


def compute_vertical_height(base_point: Dict[str, float], top_point: Dict[str, float]) -> Dict[str, Any]:
    """
    Compute vertical height difference (Delta Z), horizontal offset, and line of sight.
    """
    _, _, horiz_dist = GEOD.inv(base_point["lon"], base_point["lat"], top_point["lon"], top_point["lat"])
    delta_z = top_point.get("alt", 0.0) - base_point.get("alt", 0.0)
    hypot_3d = math.sqrt(horiz_dist ** 2 + delta_z ** 2)
    angle_deg = math.degrees(math.atan2(delta_z, max(0.001, horiz_dist)))

    return {
        "height_delta_z_m": round(abs(delta_z), 2),
        "direction": "up" if delta_z >= 0 else "down",
        "horizontal_offset_m": round(horiz_dist, 2),
        "direct_distance_3d_m": round(hypot_3d, 2),
        "angle_degrees": round(angle_deg, 1)
    }
