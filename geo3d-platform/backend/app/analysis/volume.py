"""
Volume Estimation Module
Computes cut, fill, and net volumetric calculations for 3D polygons, stockpiles, and terrain pits.
"""

import math
from typing import List, Dict, Any, Optional
import numpy as np
from app.analysis.measurement import compute_area_metrics


def estimate_volume(
    polygon_points: List[Dict[str, float]],
    base_elevation: Optional[float] = None,
    grid_resolution: float = 2.0
) -> Dict[str, Any]:
    """
    Estimate volume under a polygon boundary relative to a base plane or fitted surface.
    """
    if len(polygon_points) < 3:
        raise ValueError("At least 3 polygon boundary points required for volume estimation.")

    area_info = compute_area_metrics(polygon_points)
    area_sq_m = area_info["area_sq_m"]

    elevations = [p.get("alt", 0.0) for p in polygon_points]
    min_elev = float(np.min(elevations))
    max_elev = float(np.max(elevations))
    avg_elev = float(np.mean(elevations))

    # Base elevation reference
    ref_elev = base_elevation if base_elevation is not None else min_elev

    # Approximate triangular prism / mesh volume
    # Delta Z relative to reference plane for each vertex
    deltas = [e - ref_elev for e in elevations]
    avg_thickness = float(np.mean(deltas))

    # Cut volume (positive volume above reference plane)
    cut_deltas = [max(0.0, d) for d in deltas]
    avg_cut_h = float(np.mean(cut_deltas))
    cut_volume_m3 = round(area_sq_m * avg_cut_h, 2)

    # Fill volume (void below reference plane)
    fill_deltas = [abs(min(0.0, d)) for d in deltas]
    avg_fill_h = float(np.mean(fill_deltas))
    fill_volume_m3 = round(area_sq_m * avg_fill_h, 2)

    net_volume_m3 = round(cut_volume_m3 - fill_volume_m3, 2)

    return {
        "footprint_area_sq_m": area_sq_m,
        "reference_elevation_m": round(ref_elev, 2),
        "min_elevation_m": round(min_elev, 2),
        "max_elevation_m": round(max_elev, 2),
        "average_elevation_m": round(avg_elev, 2),
        "average_height_m": round(avg_thickness, 2),
        "cut_volume_m3": cut_volume_m3,
        "fill_volume_m3": fill_volume_m3,
        "net_volume_m3": net_volume_m3,
        "unit": "cubic_meters"
    }
