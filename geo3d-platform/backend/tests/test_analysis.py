"""
Unit tests for Phase 3 Spatial Analysis & 3D Interactive Measurements.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analysis.measurement import compute_distance_metrics, compute_area_metrics, compute_vertical_height
from app.analysis.elevation_profile import generate_elevation_profile
from app.analysis.slope_aspect import analyze_slope_and_aspect, classify_slope, degrees_to_cardinal
from app.analysis.volume import estimate_volume


def test_distance_metrics_calculation():
    points = [
        {"lon": -105.2332, "lat": 40.0208, "alt": 1750.0},
        {"lon": -105.2300, "lat": 40.0208, "alt": 1780.0},
        {"lon": -105.2300, "lat": 40.0250, "alt": 1760.0},
    ]
    res = compute_distance_metrics(points)

    assert res["point_count"] == 3
    assert res["total_horizontal_distance_m"] > 500.0
    assert res["total_3d_distance_m"] >= res["total_horizontal_distance_m"]
    assert len(res["segments"]) == 2
    assert res["segments"][0]["slope_degrees"] > 0


def test_area_and_perimeter_metrics():
    # Roughly a 200m x 200m square in Boulder
    points = [
        {"lon": -105.2332, "lat": 40.0208, "alt": 1750.0},
        {"lon": -105.2308, "lat": 40.0208, "alt": 1750.0},
        {"lon": -105.2308, "lat": 40.0226, "alt": 1750.0},
        {"lon": -105.2332, "lat": 40.0226, "alt": 1750.0},
    ]
    res = compute_area_metrics(points)

    assert res["vertex_count"] == 4
    assert res["area_sq_m"] > 30000.0  # Approx 40,000 m²
    assert res["area_hectares"] > 3.0
    assert res["perimeter_m"] > 500.0


def test_vertical_height_calculation():
    base_pt = {"lon": -105.2332, "lat": 40.0208, "alt": 1750.0}
    top_pt = {"lon": -105.2332, "lat": 40.0208, "alt": 1795.5}

    res = compute_vertical_height(base_pt, top_pt)

    assert res["height_delta_z_m"] == 45.5
    assert res["direction"] == "up"


def test_elevation_profile_generation():
    path = [
        {"lon": -105.2332, "lat": 40.0208, "alt": 1750.0},
        {"lon": -105.2308, "lat": 40.0226, "alt": 1810.0},
    ]
    res = generate_elevation_profile(path, num_samples=50)

    assert res["total_distance_m"] > 0
    assert res["sample_count"] == 50
    assert res["min_elevation_m"] == 1750.0
    assert res["max_elevation_m"] == 1810.0
    assert res["elevation_gain_m"] == 60.0
    assert len(res["samples"]) == 50


def test_slope_and_aspect_analysis():
    path = [
        {"lon": -105.2332, "lat": 40.0208, "alt": 1750.0},
        {"lon": -105.2300, "lat": 40.0208, "alt": 1800.0},
    ]
    res = analyze_slope_and_aspect(path)

    assert res["average_slope_degrees"] > 0
    assert "dominant_aspect" in res
    assert "classification" in res
    assert res["classification"]["category"] in ("gentle", "moderate", "steep", "flat", "extreme")


def test_volume_estimation():
    points = [
        {"lon": -105.2332, "lat": 40.0208, "alt": 1750.0},
        {"lon": -105.2308, "lat": 40.0208, "alt": 1755.0},
        {"lon": -105.2308, "lat": 40.0226, "alt": 1760.0},
        {"lon": -105.2332, "lat": 40.0226, "alt": 1755.0},
    ]
    res = estimate_volume(points, base_elevation=1750.0)

    assert res["footprint_area_sq_m"] > 0
    assert res["cut_volume_m3"] > 0
    assert res["net_volume_m3"] > 0
    assert res["reference_elevation_m"] == 1750.0
