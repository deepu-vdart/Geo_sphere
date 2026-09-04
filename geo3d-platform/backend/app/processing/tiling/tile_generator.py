"""
OGC 3D Tiles 1.1 Hierarchical Point Cloud Tile Generator.

Builds a proper multi-level tileset.json with LOD (Level of Detail) using an
octree spatial partition. Each leaf produces a .pnts binary tile. Internal nodes
produce coarser .pnts tiles sampled from their children.

Output directory structure:
    {output_dir}/
        tileset.json          <- Root tileset descriptor
        tiles/
            r.pnts            <- Root coarse tile (all points, thinned)
            r_0.pnts          <- Octant child tile
            r_0_3.pnts        <- Deep leaf tile
            ...
"""

import os
import json
import math
import struct
import logging
import numpy as np
import pyproj
from typing import Dict, Any, List, Optional

from app.processing.tiling.spatial_index import OctreeIndex, OctreeNode

logger = logging.getLogger(__name__)


# ── Tile colours (ASPRS → RGB) ────────────────────────────────────────────────

ASPRS_RGB: Dict[int, tuple] = {
    0: (139, 90,  43),   # Ground (brown)
    1: (180, 180, 180),  # Unclassified (gray)
    2: (139, 90,  43),   # Ground
    3: (144, 238, 144),  # Low Vegetation
    4: ( 46, 139,  87),  # Medium Vegetation
    5: ( 34, 139,  34),  # High Vegetation (forest green)
    6: (220,  20,  60),  # Building (crimson)
    7: (255,   0,   0),  # Noise (red)
    8: (138,  43, 226),  # Heavy Vehicle (purple)
    9: ( 30, 144, 255),  # Water (blue)
   10: ( 30, 144, 255),  # Light Pole
   11: (105, 105, 105),  # Road / Traffic
   12: (220,  20,  60),  # Building
   13: (240, 230, 140),  # Wire
   14: (160, 160, 160),  # Other
}


def _classify_color(classes: np.ndarray) -> np.ndarray:
    """Map classification codes → RGB uint8 (N,3)."""
    rgb = np.full((len(classes), 3), 180, dtype=np.uint8)
    for code, color in ASPRS_RGB.items():
        mask = (classes == code)
        rgb[mask] = color
    return rgb


def _build_pnts(
    ecef_x: np.ndarray, ecef_y: np.ndarray, ecef_z: np.ndarray,
    colors: np.ndarray,
) -> bytes:
    """Encode a set of ECEF points as a .pnts binary blob."""
    n_pts = len(ecef_x)
    if n_pts == 0:
        return b""

    center_x = float(np.mean(ecef_x))
    center_y = float(np.mean(ecef_y))
    center_z = float(np.mean(ecef_z))

    rel_x = (ecef_x - center_x).astype(np.float32)
    rel_y = (ecef_y - center_y).astype(np.float32)
    rel_z = (ecef_z - center_z).astype(np.float32)

    positions = np.column_stack([rel_x, rel_y, rel_z]).astype(np.float32)
    pos_bytes = positions.tobytes()
    rgb_bytes = colors.tobytes()

    ft_dict = {
        "POINTS_LENGTH": n_pts,
        "RTC_CENTER": [center_x, center_y, center_z],
        "POSITION": {"byteOffset": 0},
        "RGB": {"byteOffset": len(pos_bytes)},
    }
    ft_json = json.dumps(ft_dict).encode("utf-8")
    pad = (8 - len(ft_json) % 8) % 8
    ft_json_padded = ft_json + b" " * pad

    ft_bin = pos_bytes + rgb_bytes
    bin_pad = (8 - len(ft_bin) % 8) % 8
    ft_bin_padded = ft_bin + b"\x00" * bin_pad

    header_len = 28
    total_len = header_len + len(ft_json_padded) + len(ft_bin_padded)

    header = struct.pack(
        "<4sIIIIII",
        b"pnts", 1, total_len,
        len(ft_json_padded), len(ft_bin_padded),
        0, 0,
    )
    return header + ft_json_padded + ft_bin_padded


def _bounding_region(
    lons: np.ndarray, lats: np.ndarray, z: np.ndarray,
) -> List[float]:
    """Return [west, south, east, north, minH, maxH] in radians / metres."""
    return [
        math.radians(float(lons.min())),
        math.radians(float(lats.min())),
        math.radians(float(lons.max())),
        math.radians(float(lats.max())),
        float(z.min()),
        float(z.max()),
    ]


# ── Public entry point ─────────────────────────────────────────────────────────

class HierarchicalTileGenerator:
    """
    Generates a proper OGC 3D Tiles 1.1 tileset with octree LOD from a LAS
    point cloud.

    Usage::

        gen = HierarchicalTileGenerator(las_processor)
        result = gen.generate(output_dir, max_tile_points=8000)
    """

    def __init__(self, las_processor):
        self.proc = las_processor

    def generate(
        self,
        output_dir: str,
        max_tile_points: int = 8000,
        max_total_points: int = 250000,
    ) -> Dict[str, Any]:
        """
        Build the full hierarchical tileset.

        Returns a dict with keys: tileset_json, tile_count, point_count.
        """
        tiles_dir = os.path.join(output_dir, "tiles")
        os.makedirs(tiles_dir, exist_ok=True)

        # ── 1. Load points ─────────────────────────────────────────────────────
        raw = self.proc.extract_points()
        total = len(raw["x"])
        step = max(1, total // max_total_points)
        x = raw["x"][::step]
        y = raw["y"][::step]
        z = raw["z"][::step]
        classes = raw["classification"][::step]
        n_pts = len(x)
        logger.info(f"TileGen: {n_pts:,} points (sampled from {total:,})")

        # ── 2. CRS → WGS84 → ECEF ──────────────────────────────────────────────
        crs_str = self.proc.header.get("detected_crs", "EPSG:26913")
        try:
            t_wgs = pyproj.Transformer.from_crs(crs_str, "EPSG:4326", always_xy=True)
            lons, lats = t_wgs.transform(x, y)
        except Exception:
            lons, lats = x, y

        t_ecef = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)
        ex, ey, ez = t_ecef.transform(lons, lats, z)

        colors = _classify_color(classes)

        # ── 3. Build octree ────────────────────────────────────────────────────
        octree = OctreeIndex(max_depth=5, max_points_leaf=max_tile_points)
        octree.build(x, y, z)

        # ── 4. Write tiles recursively ────────────────────────────────────────
        tile_count = [0]

        def write_tile(node: OctreeNode) -> Optional[Dict]:
            if node.indices is None or len(node.indices) == 0:
                return None

            idx = node.indices
            n_lon = lons[idx]; n_lat = lats[idx]; n_z = z[idx]
            n_ex = ex[idx];    n_ey = ey[idx];    n_ez = ez[idx]
            n_cls = classes[idx]

            # Subsample internal nodes for coarse LOD
            if not node.is_leaf and len(idx) > max_tile_points:
                lod_step = max(1, len(idx) // max_tile_points)
                s = np.arange(0, len(idx), lod_step)
                n_ex_t = n_ex[s]; n_ey_t = n_ey[s]; n_ez_t = n_ez[s]
                n_cls_t = n_cls[s]
            else:
                n_ex_t, n_ey_t, n_ez_t = n_ex, n_ey, n_ez
                n_cls_t = n_cls

            col = _classify_color(n_cls_t)
            blob = _build_pnts(n_ex_t, n_ey_t, n_ez_t, col)

            tile_filename = f"{node.node_id}.pnts"
            tile_path = os.path.join(tiles_dir, tile_filename)
            with open(tile_path, "wb") as fh:
                fh.write(blob)
            tile_count[0] += 1

            # Geometric error: larger for shallower nodes
            geo_err = node.diagonal * 0.05 * (1 + node.depth * 0.5)

            region = _bounding_region(n_lon, n_lat, n_z)

            tile_node: Dict[str, Any] = {
                "boundingVolume": {"region": region},
                "geometricError": geo_err,
                "refine": "REPLACE",
                "content": {"uri": f"tiles/{tile_filename}"},
            }

            if not node.is_leaf:
                children_json = []
                for child in node.children:
                    if child is not None:
                        c_json = write_tile(child)
                        if c_json:
                            children_json.append(c_json)
                if children_json:
                    tile_node["children"] = children_json

            return tile_node

        root_tile = write_tile(octree.root)
        logger.info(f"TileGen: wrote {tile_count[0]} .pnts tiles")

        # ── 5. Compute overall bounding region ─────────────────────────────────
        overall_region = _bounding_region(lons, lats, z)

        # ── 6. Write tileset.json ──────────────────────────────────────────────
        tileset = {
            "asset": {
                "version": "1.1",
                "generator": "Geo3D Platform Hierarchical Tile Generator v4.0"
            },
            "geometricError": 1000.0,
            "root": {
                "boundingVolume": {"region": overall_region},
                "geometricError": root_tile["geometricError"] if root_tile else 500.0,
                "refine": "REPLACE",
                "content": root_tile["content"] if root_tile else None,
                "children": root_tile.get("children", []) if root_tile else [],
            }
        }

        tileset_path = os.path.join(output_dir, "tileset.json")
        with open(tileset_path, "w") as fh:
            json.dump(tileset, fh, indent=2)

        logger.info(f"TileGen: tileset.json written to {tileset_path}")

        return {
            "tileset_json": tileset_path,
            "tile_count": tile_count[0],
            "point_count": n_pts,
            "tiles_dir": tiles_dir,
        }
