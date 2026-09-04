"""
Unit and integration tests for Phase 2 LiDAR and Raster processing engines.
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.processing.pdal_proc.las_processor import LASProcessor, ASPRS_CLASSIFICATIONS
from app.processing.gdal_proc.raster_processor import RasterProcessor

SAMPLE_LAS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "samples", "sample_terrain.las")
)


def test_las_processor_header():
    assert os.path.exists(SAMPLE_LAS), "Sample LAS file must exist."
    processor = LASProcessor(SAMPLE_LAS, default_crs="EPSG:26913")
    header = processor.parse_header()

    assert header["version"] in ("1.2", "1.3", "1.4")
    assert header["total_points"] > 50000
    assert header["bounds"]["min_z"] < header["bounds"]["max_z"]


def test_las_processor_metadata_and_stats():
    processor = LASProcessor(SAMPLE_LAS, default_crs="EPSG:26913")
    stats = processor.get_metadata_and_stats(max_sample_points=50000)

    assert "point_count" in stats
    assert stats["point_count"] == 69998
    assert "point_density" in stats
    assert stats["point_density"] > 0
    assert "classification_breakdown" in stats

    # Verify ground, veg, building classes present
    classes = stats["classification_breakdown"]
    assert 2 in classes  # Ground
    assert 5 in classes  # High Veg
    assert 6 in classes  # Building

    assert stats["min_z"] < stats["max_z"]
    assert -180 <= stats["center"]["lon"] <= 180
    assert -90 <= stats["center"]["lat"] <= 90


def test_las_processor_3d_tiles_generation(tmp_path):
    processor = LASProcessor(SAMPLE_LAS, default_crs="EPSG:26913")
    output_dir = str(tmp_path / "tiles")

    tiles = processor.generate_3d_tiles(output_dir, max_points=10000)

    assert os.path.exists(tiles["tileset_json"])
    assert os.path.exists(tiles["tile_pnts"])

    with open(tiles["tile_pnts"], "rb") as f:
        magic = f.read(4)
        assert magic == b"pnts"


def test_las_processor_sample_points():
    processor = LASProcessor(SAMPLE_LAS, default_crs="EPSG:26913")
    samples = processor.get_sample_points(sample_size=100)

    assert len(samples) > 0
    assert "lon" in samples[0]
    assert "lat" in samples[0]
    assert "alt" in samples[0]
    assert "classification" in samples[0]


def test_raster_processor_metadata():
    # Test RasterProcessor fallback structure
    r_proc = RasterProcessor("dummy.tif")
    r_proc.metadata = {
        "width": 512,
        "height": 512,
        "bands": 1,
        "crs": "EPSG:4326",
        "file_size_bytes": 1024,
        "resolution_x": 1.0,
        "resolution_y": 1.0,
    }
    r_proc._parsed = True
    stats = r_proc.get_metadata_and_stats()

    assert stats["width"] == 512
    assert stats["bands"] == 1
    assert stats["crs"] == "EPSG:4326"
    assert "wgs84_bounds" in stats
