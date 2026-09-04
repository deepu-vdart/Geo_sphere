"""
Unit and integration tests for Phase 4:
  - Track B: Octree Spatial Index and Hierarchical OGC 3D Tiles 1.1 Generator
  - Track C: DALES-2 Semantic Point Cloud Classifier
"""

import os
import sys
import json
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.processing.tiling.spatial_index import OctreeIndex, OctreeNode
from app.processing.tiling.tile_generator import HierarchicalTileGenerator
from app.processing.ai.classifier import classify_point_cloud, DALES_CLASSES
from app.processing.pdal_proc.las_processor import LASProcessor

SAMPLE_LAS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "samples", "sample_terrain.las")
)


def test_octree_index_build():
    x = np.random.uniform(0, 500, 25000)
    y = np.random.uniform(0, 500, 25000)
    z = np.random.uniform(100, 300, 25000)

    tree = OctreeIndex(max_depth=4, max_points_leaf=2000)
    root = tree.build(x, y, z)

    assert root is not None
    assert root.node_id == "r"
    assert not root.is_leaf

    leaves = tree.leaf_nodes()
    assert len(leaves) > 1
    total_leaf_points = sum(len(leaf.indices) for leaf in leaves)
    assert total_leaf_points == 25000

    all_nodes = tree.all_nodes()
    assert len(all_nodes) > len(leaves)


def test_hierarchical_tile_generator(tmp_path):
    assert os.path.exists(SAMPLE_LAS), "Sample LAS file must exist."
    proc = LASProcessor(SAMPLE_LAS, default_crs="EPSG:26913")
    gen = HierarchicalTileGenerator(proc)

    out_dir = str(tmp_path / "hierarchical_tiles")
    res = gen.generate(out_dir, max_tile_points=5000, max_total_points=30000)

    assert "tileset_json" in res
    assert os.path.exists(res["tileset_json"])
    assert res["tile_count"] > 1

    with open(res["tileset_json"], "r") as f:
        tileset = json.load(f)

    assert tileset["asset"]["version"] == "1.1"
    assert "root" in tileset
    assert "boundingVolume" in tileset["root"]
    assert len(tileset["root"]["children"]) > 0

    root_pnts_path = os.path.join(out_dir, "tiles", "r.pnts")
    assert os.path.exists(root_pnts_path)
    with open(root_pnts_path, "rb") as f:
        assert f.read(4) == b"pnts"


def test_dales2_classifier_with_asprs_prior():
    n = 1000
    x = np.linspace(0, 100, n)
    y = np.linspace(0, 100, n)
    z = np.linspace(200, 300, n)
    intensity = np.random.randint(500, 25000, n, dtype="u2")
    # Half ground (ASPRS 2), half building (ASPRS 6)
    asprs_classes = np.array([2] * 500 + [6] * 500, dtype="u1")

    res = classify_point_cloud(x, y, z, intensity, asprs_classes)

    assert res["total_points"] == n
    assert "0" in res["per_class"]  # Ground
    assert "12" in res["per_class"]  # Building
    assert res["per_class"]["0"]["count"] == 500
    assert res["per_class"]["12"]["count"] == 500
    assert res["dominant_class"] in ("Ground", "Building")


def test_dales2_classifier_unclassified_fallback():
    n = 1000
    x = np.random.uniform(0, 100, n)
    y = np.random.uniform(0, 100, n)
    z = np.linspace(100, 200, n)  # Gradient from low to high elevation
    intensity = np.random.randint(100, 5000, n, dtype="u2")
    unclassified = np.ones(n, dtype="u1")  # ASPRS 1 = Unclassified

    res = classify_point_cloud(x, y, z, intensity, unclassified)

    assert res["total_points"] == n
    assert res["class_count"] >= 1
    assert res["classification_method"] == "rule_based_asprs_prior"
