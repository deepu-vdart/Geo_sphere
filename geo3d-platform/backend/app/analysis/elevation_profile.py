"""
Elevation Profile Analysis Module
Extracts transect elevation profiles from point clouds and terrain models,
calculating distance along path, elevation gain/loss, and slope gradients.
"""

import math
from typing import List, Dict, Any, Optional
import numpy as np
import pyproj
from app.analysis.measurement import GEOD

ecef_transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)


def generate_elevation_profile(
    path_points: List[Dict[str, float]],
    num_samples: int = 100,
    dataset_points: Optional[Dict[str, np.ndarray]] = None,
    dataset_crs: str = "EPSG:26913"
) -> Dict[str, Any]:
    """
    Generate elevation profile along a polyline path.
    """
    if len(path_points) < 2:
        raise ValueError("At least 2 points are required to generate an elevation profile.")

    # Calculate segment lengths
    segment_lengths = []
    total_length = 0.0
    for i in range(len(path_points) - 1):
        p1 = path_points[i]
        p2 = path_points[i + 1]
        _, _, d = GEOD.inv(p1["lon"], p1["lat"], p2["lon"], p2["lat"])
        segment_lengths.append(d)
        total_length += d

    if total_length == 0:
        total_length = 1.0

    # Sample evenly along path
    sample_distances = np.linspace(0, total_length, num_samples)
    sampled_coords = []

    for dist in sample_distances:
        # Find which segment this distance falls in
        accum = 0.0
        seg_idx = 0
        t = 0.0
        for idx, seg_len in enumerate(segment_lengths):
            if accum + seg_len >= dist or idx == len(segment_lengths) - 1:
                seg_idx = idx
                rem = dist - accum
                t = rem / max(0.001, seg_len)
                t = min(1.0, max(0.0, t))
                break
            accum += seg_len

        p1 = path_points[seg_idx]
        p2 = path_points[seg_idx + 1]

        lon = p1["lon"] + t * (p2["lon"] - p1["lon"])
        lat = p1["lat"] + t * (p2["lat"] - p1["lat"])
        base_alt = p1.get("alt", 0.0) + t * (p2.get("alt", 0.0) - p1.get("alt", 0.0))

        sampled_coords.append({
            "distance_m": round(float(dist), 2),
            "lon": round(float(lon), 7),
            "lat": round(float(lat), 7),
            "alt": float(base_alt),
            "segment_index": seg_idx + 1
        })

    # If real dataset points are available, interpolate elevation from dataset
    if dataset_points is not None and "x" in dataset_points and "z" in dataset_points:
        try:
            # Transform sampled lon/lat to dataset CRS
            to_ds_crs = pyproj.Transformer.from_crs("EPSG:4326", dataset_crs, always_xy=True)
            samp_lons = [sc["lon"] for sc in sampled_coords]
            samp_lats = [sc["lat"] for sc in sampled_coords]
            sx, sy = to_ds_crs.transform(samp_lons, samp_lats)

            # Fast 2D KDTree for elevation interpolation
            from scipy.spatial import cKDTree
            pts_2d = np.column_stack((dataset_points["x"], dataset_points["y"]))
            tree = cKDTree(pts_2d)
            query_pts = np.column_stack((sx, sy))

            # Query 5 nearest neighbors for IDW (inverse distance weighted) elevation
            k = min(5, len(dataset_points["x"]))
            dists, idxs = tree.query(query_pts, k=k)

            for i in range(len(sampled_coords)):
                d_row = dists[i]
                idx_row = idxs[i]
                if np.isscalar(d_row):
                    d_row = np.array([d_row])
                    idx_row = np.array([idx_row])

                weights = 1.0 / (d_row + 0.01)
                weights /= np.sum(weights)
                elev = np.sum(weights * dataset_points["z"][idx_row])
                sampled_coords[i]["alt"] = round(float(elev), 2)
        except Exception:
            pass

    # Compute elevation gain, loss, and slopes
    elevations = [sc["alt"] for sc in sampled_coords]
    gain = 0.0
    loss = 0.0
    slopes = []

    for i in range(len(sampled_coords)):
        if i == 0:
            sampled_coords[i]["slope_percent"] = 0.0
        else:
            dz = elevations[i] - elevations[i - 1]
            dx = sampled_coords[i]["distance_m"] - sampled_coords[i - 1]["distance_m"]
            if dz > 0:
                gain += dz
            else:
                loss += abs(dz)
            slope = (dz / max(0.1, dx)) * 100.0
            sampled_coords[i]["slope_percent"] = round(float(slope), 1)
            slopes.append(abs(slope))

    min_elev = float(np.min(elevations))
    max_elev = float(np.max(elevations))
    avg_elev = float(np.mean(elevations))
    max_slope = float(np.max(slopes)) if slopes else 0.0
    avg_slope = float(np.mean(slopes)) if slopes else 0.0

    return {
        "total_distance_m": round(total_length, 2),
        "sample_count": len(sampled_coords),
        "min_elevation_m": round(min_elev, 2),
        "max_elevation_m": round(max_elev, 2),
        "avg_elevation_m": round(avg_elev, 2),
        "elevation_gain_m": round(gain, 2),
        "elevation_loss_m": round(loss, 2),
        "max_slope_percent": round(max_slope, 1),
        "avg_slope_percent": round(avg_slope, 1),
        "samples": sampled_coords
    }
