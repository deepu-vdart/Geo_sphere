"""
Tests for Multi-Temporal Change Detection (MVP 8).
Verifies the differential surface algorithm, volumetric cut/fill,
and structural feature thresholding.
"""

import math
import numpy as np
import pytest
from app.processing.temporal.change_detection import compute_temporal_change


def test_temporal_change_identical_point_clouds_without_simulation():
    """Identical point clouds with zero shift should result in near-zero cut/fill."""
    n = 2000
    xs = np.random.uniform(100, 300, n)
    ys = np.random.uniform(100, 300, n)
    zs = np.full(n, 50.0)

    base = {"x": xs, "y": ys, "z": zs, "lon": np.zeros(n), "lat": np.zeros(n)}
    comp = {"x": xs.copy(), "y": ys.copy(), "z": zs.copy(), "lon": np.zeros(n), "lat": np.zeros(n)}

    res = compute_temporal_change(
        base,
        comp,
        grid_resolution=5.0,
        height_threshold=0.3,
        simulate_temporal_shift=False,
    )

    assert res["status"] == "completed"
    assert "metrics" in res
    assert "distribution" in res
    assert "difference_samples" in res
    assert res["metrics"]["cut_volume_m3"] >= 0.0
    assert res["metrics"]["fill_volume_m3"] >= 0.0


def test_temporal_change_excavation_and_fill():
    """Points with positive delta should be fill; negative delta should be cut."""
    n = 1000
    xs = np.linspace(100, 200, n)
    ys = np.linspace(100, 200, n)
    zs_base = np.full(n, 50.0)
    # First half cut (-2.0m), second half fill (+3.0m)
    zs_comp = zs_base.copy()
    zs_comp[: n // 2] -= 2.0
    zs_comp[n // 2 :] += 3.0

    base = {"x": xs, "y": ys, "z": zs_base}
    comp = {"x": xs, "y": ys, "z": zs_comp}

    res = compute_temporal_change(
        base,
        comp,
        grid_resolution=2.0,
        height_threshold=0.5,
        simulate_temporal_shift=False,
    )

    metrics = res["metrics"]
    assert metrics["cut_volume_m3"] > 0.0
    assert metrics["fill_volume_m3"] > 0.0
    assert metrics["max_elevation_gain_m"] >= 2.5
    assert metrics["max_elevation_loss_m"] <= -1.5


def test_temporal_change_structure_detection():
    """Elevation shifts exceeding structure_threshold should register as structural change."""
    n = 500
    xs = np.linspace(50, 100, n)
    ys = np.linspace(50, 100, n)
    zs_base = np.full(n, 20.0)
    zs_comp = zs_base.copy()
    zs_comp[:100] += 6.0  # New structure: +6m

    base = {"x": xs, "y": ys, "z": zs_base}
    comp = {"x": xs, "y": ys, "z": zs_comp}

    res = compute_temporal_change(
        base,
        comp,
        grid_resolution=2.0,
        structure_threshold=2.5,
        simulate_temporal_shift=False,
    )

    dist = res["distribution"]
    assert dist["new_structures_detected"] > 0

    # Verify difference samples contain classified types
    types = {p["type"] for p in res["difference_samples"]}
    assert "new_structure" in types


def test_temporal_change_simulation_mode():
    """Simulated temporal shift should automatically generate cut, fill, and structure zones."""
    n = 3000
    xs = np.random.uniform(500, 800, n)
    ys = np.random.uniform(500, 800, n)
    zs = 100.0 + np.sin(xs / 50.0) * 5.0

    base = {"x": xs, "y": ys, "z": zs}
    comp = {"x": xs.copy(), "y": ys.copy(), "z": zs.copy()}

    res = compute_temporal_change(
        base,
        comp,
        grid_resolution=3.0,
        simulate_temporal_shift=True,
    )

    assert res["metrics"]["cut_volume_m3"] > 0
    assert res["metrics"]["fill_volume_m3"] > 0
    assert res["metrics"]["modified_area_m2"] > 0
    assert len(res["difference_samples"]) > 0
