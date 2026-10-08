"""
Unit and integration tests for MVP 6: DALES-2 Dataset Adapter & 3D Object Detection.
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.processing.ai.dales_adapter import dales_adapter, DALES_CLASSES, ASPRS_TO_DALES
from app.processing.ai.detector import detector_3d, Object3DDetector


def test_dales_class_metadata():
    """Verify DALES-2 15 semantic classes are defined with colors, names, and categories."""
    assert len(DALES_CLASSES) == 15
    for cls_id in range(15):
        assert cls_id in DALES_CLASSES
        meta = dales_adapter.get_class_meta(cls_id)
        assert "name" in meta
        assert "color" in meta
        assert meta["color"].startswith("#")
        assert "category" in meta

    assert DALES_CLASSES[12]["name"] == "Building"
    assert DALES_CLASSES[0]["name"] == "Ground"
    assert DALES_CLASSES[2]["name"] == "Car"
    assert DALES_CLASSES[9]["name"] == "Utility Pole"
    assert DALES_CLASSES[5]["name"] == "Tree"


def test_dales_tile_parsing():
    """Verify DALES standard tile filename parsing and native bounds."""
    tile = dales_adapter.parse_tile_id("dales2_5080_54400.laz")
    assert tile is not None
    assert tile["tile_name"] == "5080_54400"
    assert tile["crs"] == "EPSG:26913"
    assert tile["bbox_native"]["min_x"] == 5080000
    assert tile["bbox_native"]["max_x"] == 5080500


def test_asprs_to_dales_mapping():
    """Verify ASPRS class translation to DALES-2 semantic labels."""
    asprs_sample = np.array([2, 5, 6, 9, 15, 0], dtype=np.int32)
    dales_labels = dales_adapter.asprs_to_dales_array(asprs_sample)

    assert dales_labels[0] == 0   # Ground
    assert dales_labels[1] == 5   # High Veg -> Tree
    assert dales_labels[2] == 12  # Building
    assert dales_labels[3] == 14  # Water -> Other
    assert dales_labels[4] == 9   # Transmission Tower -> Utility Pole
    assert dales_labels[5] == 0   # Created -> Ground


def test_dales_benchmark_tile_generation():
    """Verify synthetic benchmark tile generation with realistic point distributions."""
    bench = dales_adapter.generate_benchmark_tile(num_points=3000)
    assert bench["total_points"] > 2500
    assert len(bench["x"]) == bench["total_points"]
    assert len(bench["y"]) == bench["total_points"]
    assert len(bench["z"]) == bench["total_points"]
    assert len(bench["lon"]) == bench["total_points"]
    assert len(bench["lat"]) == bench["total_points"]

    classes = set(bench["dales_classification"])
    assert 0 in classes   # Ground
    assert 12 in classes  # Building
    assert 2 in classes or 6 in classes  # Vehicles
    assert 9 in classes   # Utility Pole
    assert 5 in classes   # Tree


def test_3d_object_detector_bounding_boxes():
    """Verify 3D Object Detection identifies instances with metric bounding boxes."""
    bench = dales_adapter.generate_benchmark_tile(num_points=5000)

    res = detector_3d.detect_objects(
        x=bench["x"],
        y=bench["y"],
        z=bench["z"],
        classes=bench["dales_classification"],
        intensity=bench["intensity"],
        lon=bench["lon"],
        lat=bench["lat"],
        categories=["building", "vehicle", "tree", "pole"]
    )

    assert res["status"] == "completed"
    assert res["total_objects"] > 0
    assert "building" in res["category_counts"]
    assert res["category_counts"]["building"] >= 1

    objects = res["detected_objects"]
    assert len(objects) == res["total_objects"]

    # Verify building object properties
    buildings = [o for o in objects if o["category"] == "building"]
    assert len(buildings) >= 1
    bldg = buildings[0]

    assert "id" in bldg
    assert "dimensions" in bldg
    dims = bldg["dimensions"]
    assert dims["length_m"] > 5.0
    assert dims["width_m"] > 5.0
    assert dims["height_m"] > 3.0
    assert dims["volume_m3"] > 50.0
    assert dims["footprint_sq_m"] > 25.0

    # Verify Cesium box properties
    cbox = bldg["cesium_box"]
    assert len(cbox["position"]) == 3
    assert len(cbox["dimensions"]) == 3
    assert cbox["color"] == "#ef4444"

    # Verify vehicles detected
    vehicles = [o for o in objects if o["category"] == "vehicle"]
    assert len(vehicles) >= 1
    v = vehicles[0]
    assert v["dimensions"]["height_m"] < 5.0  # Vehicles are under 5m high

    # Verify poles detected
    poles = [o for o in objects if o["category"] == "pole"]
    assert len(poles) >= 1
    p = poles[0]
    assert p["dimensions"]["height_m"] >= 6.0  # Utility poles are tall


def test_3d_detector_empty_input():
    """Verify graceful handling of empty point clouds."""
    res = detector_3d.detect_objects(
        x=np.array([]),
        y=np.array([]),
        z=np.array([]),
        classes=np.array([])
    )
    assert res["object_count"] == 0
    assert len(res["detected_objects"]) == 0
