"""
Slope and Aspect Terrain Analysis Module
Calculates slope angle, percent grade, compass aspect orientation, and terrain classification.
"""

import math
from typing import List, Dict, Any, Tuple
import numpy as np
from app.analysis.measurement import GEOD

SLOPE_CLASSES = [
    (2.0, "Flat (< 2°)", "flat"),
    (8.0, "Gentle (2° - 8°)", "gentle"),
    (15.0, "Moderate (8° - 15°)", "moderate"),
    (30.0, "Steep (15° - 30°)", "steep"),
    (90.0, "Extreme / Cliff (> 30°)", "extreme")
]

CARDINAL_DIRECTIONS = [
    (22.5, "North", "N"),
    (67.5, "North-East", "NE"),
    (112.5, "East", "E"),
    (157.5, "South-East", "SE"),
    (202.5, "South", "S"),
    (247.5, "South-West", "SW"),
    (292.5, "West", "W"),
    (337.5, "North-West", "NW"),
    (360.0, "North", "N")
]


def classify_slope(slope_deg: float) -> Dict[str, str]:
    """Classify slope angle into standard geomorphological categories."""
    for max_ang, label, code in SLOPE_CLASSES:
        if slope_deg <= max_ang:
            return {"label": label, "category": code}
    return {"label": "Extreme (> 30°)", "category": "extreme"}


def degrees_to_cardinal(azimuth_deg: float) -> Dict[str, str]:
    """Convert azimuth angle (0-360°) to cardinal direction."""
    azimuth = azimuth_deg % 360.0
    for max_deg, name, code in CARDINAL_DIRECTIONS:
        if azimuth <= max_deg:
            return {"compass_heading_deg": round(azimuth, 1), "cardinal": code, "name": name}
    return {"compass_heading_deg": round(azimuth, 1), "cardinal": "N", "name": "North"}


def analyze_slope_and_aspect(points: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Analyze slope and aspect for a line transect or polygon boundary points.
    """
    if len(points) < 2:
        return {
            "average_slope_degrees": 0.0,
            "max_slope_degrees": 0.0,
            "average_slope_percent": 0.0,
            "dominant_aspect": {"compass_heading_deg": 0.0, "cardinal": "N", "name": "North"},
            "classification": classify_slope(0.0),
            "segments": []
        }

    slopes_deg = []
    slopes_pct = []
    aspects = []
    segments = []

    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]

        fwd_azimuth, _, horiz_dist = GEOD.inv(p1["lon"], p1["lat"], p2["lon"], p2["lat"])
        delta_z = p2.get("alt", 0.0) - p1.get("alt", 0.0)

        # Slope
        slope_pct = (abs(delta_z) / max(0.001, horiz_dist)) * 100.0
        slope_deg = math.degrees(math.atan2(abs(delta_z), max(0.001, horiz_dist)))

        # Aspect (direction of downward slope)
        aspect_azimuth = fwd_azimuth if delta_z < 0 else (fwd_azimuth + 180.0) % 360.0
        aspect_info = degrees_to_cardinal(aspect_azimuth)

        slopes_deg.append(slope_deg)
        slopes_pct.append(slope_pct)
        aspects.append(aspect_azimuth)

        segments.append({
            "segment": i + 1,
            "horizontal_distance_m": round(horiz_dist, 2),
            "delta_z_m": round(delta_z, 2),
            "slope_degrees": round(slope_deg, 1),
            "slope_percent": round(slope_pct, 1),
            "aspect": aspect_info,
            "classification": classify_slope(slope_deg)
        })

    avg_slope_deg = float(np.mean(slopes_deg))
    max_slope_deg = float(np.max(slopes_deg))
    avg_slope_pct = float(np.mean(slopes_pct))
    mean_aspect = float(np.mean(aspects))

    return {
        "average_slope_degrees": round(avg_slope_deg, 1),
        "max_slope_degrees": round(max_slope_deg, 1),
        "average_slope_percent": round(avg_slope_pct, 1),
        "dominant_aspect": degrees_to_cardinal(mean_aspect),
        "classification": classify_slope(avg_slope_deg),
        "segments": segments
    }
