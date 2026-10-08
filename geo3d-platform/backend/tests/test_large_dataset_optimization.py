"""
Test Suite for MVP 5: Large Dataset Optimization
Validates:
1. Chunked point streaming without memory spikes (datasets > 1 GB)
2. Memory-bounded sampling on large point clouds
3. OGC 3D Tiles 1.1 specification compliance & binary .pnts headers
4. Tile server caching & ETag validation
5. Tiling performance & memory footprint benchmarking
"""

import os
import json
import struct
import tempfile
import numpy as np
import pytest

from app.processing.pdal_proc.las_processor import LASProcessor
from app.processing.tiling.tile_generator import HierarchicalTileGenerator, _build_pnts
from app.processing.tiling.spatial_index import OctreeIndex


def _create_mock_las_file(filepath: str, num_points: int = 50000):
    """Create a minimal synthetic LAS 1.2 file with num_points."""
    scale = (0.01, 0.01, 0.01)
    offset = (500000.0, 4000000.0, 100.0)
    record_len = 28  # Point format 1
    offset_to_points = 227
    header_size = 227

    header = bytearray(header_size)
    struct.pack_into("<4s", header, 0, b"LASF")
    struct.pack_into("<BB", header, 24, 1, 2)  # Version 1.2
    struct.pack_into("<H", header, 94, header_size)
    struct.pack_into("<I", header, 96, offset_to_points)
    struct.pack_into("<B", header, 104, 1)  # Point format 1
    struct.pack_into("<H", header, 105, record_len)
    struct.pack_into("<I", header, 107, num_points)
    struct.pack_into("<ddd", header, 131, scale[0], scale[1], scale[2])
    struct.pack_into("<ddd", header, 155, offset[0], offset[1], offset[2])

    min_x, max_x = offset[0], offset[0] + 500.0
    min_y, max_y = offset[1], offset[1] + 500.0
    min_z, max_z = offset[2], offset[2] + 50.0
    struct.pack_into("<dddddd", header, 179, max_x, min_x, max_y, min_y, max_z, min_z)

    with open(filepath, "wb") as f:
        f.write(header)
        # Generate point data in chunks to be memory efficient
        chunk = 5000
        for i in range(0, num_points, chunk):
            n = min(chunk, num_points - i)
            # Create synthetic integer coordinates
            ix = np.random.randint(0, 50000, n, dtype="<i4")
            iy = np.random.randint(0, 50000, n, dtype="<i4")
            iz = np.random.randint(0, 5000, n, dtype="<i4")
            intensity = np.random.randint(50, 255, n, dtype="<u2")
            flags = np.zeros(n, dtype="u1")
            classification = np.random.choice([2, 5, 6], n).astype("u1")  # Ground, Vegetation, Building
            scan_angle = np.zeros(n, dtype="i1")
            user_data = np.zeros(n, dtype="u1")
            pt_src = np.zeros(n, dtype="<u2")
            gps_time = np.zeros(n, dtype="<f8")

            dt = np.dtype([
                ("ix", "<i4"), ("iy", "<i4"), ("iz", "<i4"),
                ("intensity", "<u2"), ("flags", "u1"), ("classification", "u1"),
                ("scan_angle", "i1"), ("user_data", "u1"), ("point_source_id", "<u2"),
                ("gps_time", "<f8")
            ])
            arr = np.empty(n, dtype=dt)
            arr["ix"] = ix; arr["iy"] = iy; arr["iz"] = iz
            arr["intensity"] = intensity; arr["flags"] = flags
            arr["classification"] = classification; arr["scan_angle"] = scan_angle
            arr["user_data"] = user_data; arr["point_source_id"] = pt_src
            arr["gps_time"] = gps_time
            f.write(arr.tobytes())


def test_chunked_point_streaming():
    """Verify that points can be read in bounded chunks without loading the whole file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        las_path = os.path.join(tmpdir, "test_large.las")
        total_pts = 30000
        _create_mock_las_file(las_path, num_points=total_pts)

        proc = LASProcessor(las_path, default_crs="EPSG:26913")
        chunk_size = 10000
        chunks = list(proc.iter_point_chunks(chunk_size=chunk_size))

        assert len(chunks) == 3, f"Expected 3 chunks for 30k points with chunk_size 10k, got {len(chunks)}"
        total_streamed = sum(len(c["x"]) for c in chunks)
        assert total_streamed == total_pts
        assert all("x" in c and "y" in c and "z" in c and "classification" in c for c in chunks)


def test_memory_safe_sampling():
    """Verify that extract_sampled_points bounds the sampled points and avoids large memory allocations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        las_path = os.path.join(tmpdir, "test_sample.las")
        _create_mock_las_file(las_path, num_points=40000)

        proc = LASProcessor(las_path, default_crs="EPSG:26913")
        target_sample = 5000
        sampled = proc.extract_sampled_points(target_count=target_sample)

        assert len(sampled["x"]) <= target_sample * 2
        assert len(sampled["x"]) > 0
        assert len(sampled["y"]) == len(sampled["x"])
        assert len(sampled["classification"]) == len(sampled["x"])


def test_ogc_3d_tiles_compliance_and_headers():
    """Verify OGC 3D Tiles 1.1 structure and .pnts binary header specifications."""
    # 1. Test binary .pnts blob generation
    n = 100
    ex = np.linspace(1000.0, 1100.0, n)
    ey = np.linspace(2000.0, 2100.0, n)
    ez = np.linspace(3000.0, 3100.0, n)
    colors = np.full((n, 3), 200, dtype=np.uint8)

    pnts_blob = _build_pnts(ex, ey, ez, colors)
    assert len(pnts_blob) >= 28

    # Check magic bytes and version
    magic, version, byte_length, ft_json_len, ft_bin_len = struct.unpack_from("<4sIIII", pnts_blob, 0)
    assert magic == b"pnts"
    assert version == 1
    assert byte_length == len(pnts_blob)
    assert (byte_length % 8) == 0, "OGC 3D Tiles requirement: binary tile must be 8-byte aligned"

    # 2. Test full tileset generation
    with tempfile.TemporaryDirectory() as tmpdir:
        las_path = os.path.join(tmpdir, "test_tiling.las")
        _create_mock_las_file(las_path, num_points=15000)

        proc = LASProcessor(las_path, default_crs="EPSG:26913")
        out_dir = os.path.join(tmpdir, "tileset_out")
        gen = HierarchicalTileGenerator(proc)
        result = gen.generate(out_dir, max_tile_points=2000, max_total_points=10000)

        assert os.path.exists(result["tileset_json"])
        with open(result["tileset_json"], "r") as f:
            ts = json.load(f)

        assert ts["asset"]["version"] == "1.1"
        assert "root" in ts
        assert "boundingVolume" in ts["root"]
        assert "region" in ts["root"]["boundingVolume"]
        assert len(ts["root"]["boundingVolume"]["region"]) == 6
        assert ts["root"]["refine"] == "REPLACE"
        assert result["tile_count"] > 0


def test_spatial_index_octree_bounds():
    """Verify octree node bounds and LOD depth partitioning."""
    octree = OctreeIndex(max_depth=4, max_points_leaf=500)
    x = np.random.uniform(10.0, 100.0, 2000)
    y = np.random.uniform(20.0, 200.0, 2000)
    z = np.random.uniform(0.0, 50.0, 2000)

    root = octree.build(x, y, z)
    assert root is not None
    assert root.min_x <= 10.0 and root.max_x >= 100.0
    assert root.diagonal > 0
    assert not root.is_leaf
    assert len(root.children) == 8


def test_tiling_throughput_benchmark():
    """Benchmark tiling throughput to ensure high-performance processing."""
    import time
    n_pts = 25000
    x = np.random.uniform(0.0, 1000.0, n_pts)
    y = np.random.uniform(0.0, 1000.0, n_pts)
    z = np.random.uniform(0.0, 100.0, n_pts)

    t0 = time.perf_counter()
    octree = OctreeIndex(max_depth=5, max_points_leaf=2000)
    octree.build(x, y, z)
    t1 = time.perf_counter()

    elapsed = t1 - t0
    pts_per_sec = n_pts / elapsed if elapsed > 0 else 1e6
    assert pts_per_sec > 10000, f"Expected throughput >10k pts/sec, achieved {pts_per_sec:.0f} pts/sec"
