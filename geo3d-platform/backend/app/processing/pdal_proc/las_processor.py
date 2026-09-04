"""
LiDAR LAS Point Cloud Processor
Handles LAS binary parsing, metadata extraction, CRS transformation (to WGS84 & ECEF),
point cloud classification statistics, and OGC 3D Tiles (.pnts + tileset.json) generation.
"""

import os
import math
import struct
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pyproj
from shapely.geometry import Polygon, mapping

logger = logging.getLogger(__name__)

# Standard ASPRS classification names
ASPRS_CLASSIFICATIONS = {
    0: "Created, never classified",
    1: "Unclassified",
    2: "Ground",
    3: "Low Vegetation",
    4: "Medium Vegetation",
    5: "High Vegetation",
    6: "Building",
    7: "Low Point (noise)",
    8: "Model Key-point",
    9: "Water",
    10: "Rail",
    11: "Road Surface",
    12: "Overlap",
    13: "Wire - Guard",
    14: "Wire - Conductor",
    15: "Transmission Tower",
    16: "Wire-Structure Connector",
    17: "Bridge Deck",
    18: "High Noise"
}

# Standard classification colors (RGB 0-255)
CLASSIFICATION_COLORS = {
    0: (160, 160, 160),     # Gray
    1: (180, 180, 180),     # Light gray
    2: (139, 90, 43),       # Brown (Ground)
    3: (144, 238, 144),     # Light green
    4: (46, 139, 87),       # Sea green
    5: (34, 139, 34),       # Forest green
    6: (220, 20, 60),       # Crimson (Building)
    7: (255, 0, 0),         # Red (Noise)
    8: (255, 215, 0),       # Gold
    9: (30, 144, 255),      # Dodger blue (Water)
    11: (105, 105, 105),    # Dim gray (Roads)
}


class LASProcessor:
    """Processor for LAS LiDAR files."""

    def __init__(self, file_path: str, default_crs: Optional[str] = None):
        self.file_path = file_path
        self.default_crs = default_crs or "EPSG:26913"  # UTM Zone 13N fallback if not specified
        self.header: Dict[str, Any] = {}
        self.vlr_records: List[Dict[str, Any]] = []
        self._parsed = False

    def parse_header(self) -> Dict[str, Any]:
        """Read and parse the LAS header."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"LAS file not found: {self.file_path}")

        file_size = os.path.getsize(self.file_path)
        with open(self.file_path, "rb") as f:
            sig = f.read(4)
            if sig != b"LASF":
                raise ValueError(f"Invalid LAS file signature: {sig!r}. Expected b'LASF'.")

            # Read remaining public header block (227 bytes for LAS 1.2/1.3, up to 375 for 1.4)
            f.seek(0)
            raw_header = f.read(375)

            # Unpack base header fields
            # Pos 24: Version Major (1 byte), Version Minor (1 byte)
            v_major, v_minor = struct.unpack_from("<BB", raw_header, 24)
            header_size, offset_to_points = struct.unpack_from("<HI", raw_header, 94)
            num_vlrs, point_format, point_record_len, num_points_legacy = struct.unpack_from(
                "<IBHI", raw_header, 100
            )

            # Scale factors
            scale_x, scale_y, scale_z = struct.unpack_from("<ddd", raw_header, 131)
            # Offsets
            off_x, off_y, off_z = struct.unpack_from("<ddd", raw_header, 155)
            # Extents (min/max)
            max_x, min_x = struct.unpack_from("<dd", raw_header, 179)
            max_y, min_y = struct.unpack_from("<dd", raw_header, 195)
            max_z, min_z = struct.unpack_from("<dd", raw_header, 211)

            total_points = num_points_legacy
            # For LAS 1.4, check extended number of points if legacy is 0 or header is larger
            if v_major == 1 and v_minor >= 4 and len(raw_header) >= 255:
                # LAS 1.4 extended point records count at byte 247 (uint64)
                if len(raw_header) >= 255:
                    ext_num_points = struct.unpack_from("<Q", raw_header, 247)[0]
                    if ext_num_points > 0:
                        total_points = ext_num_points

            # Read VLRs to look for GeoTIFF keys / WKT CRS
            f.seek(header_size)
            vlrs = []
            detected_crs = None

            for _ in range(num_vlrs):
                vlr_header = f.read(54)
                if len(vlr_header) < 54:
                    break
                user_id = vlr_header[2:18].decode("ascii", errors="ignore").rstrip("\x00")
                record_id = struct.unpack_from("<H", vlr_header, 18)[0]
                record_len = struct.unpack_from("<H", vlr_header, 20)[0]
                description = vlr_header[22:54].decode("ascii", errors="ignore").rstrip("\x00")
                payload = f.read(record_len)

                vlrs.append({
                    "user_id": user_id,
                    "record_id": record_id,
                    "length": record_len,
                    "description": description
                })

                # Check for OGC WKT or GeoTIFF projection record
                if "LASF_Projection" in user_id or "liblas" in user_id:
                    if record_id == 2112:  # OGC WKT Coordinate System
                        detected_crs = payload.decode("utf-8", errors="ignore").rstrip("\x00")
                    elif record_id == 34735:  # GeoKeyDirectoryTag
                        # Try to detect EPSG code from GeoKeys
                        try:
                            num_keys = struct.unpack_from("<H", payload, 6)[0]
                            for ki in range(num_keys):
                                k_id, k_loc, k_count, k_val = struct.unpack_from("<HHHH", payload, 8 + ki * 8)
                                if k_id in (3072, 2048):  # ProjectedCSTypeGeoKey or GeographicTypeGeoKey
                                    detected_crs = f"EPSG:{k_val}"
                        except Exception:
                            pass

            self.header = {
                "version": f"{v_major}.{v_minor}",
                "header_size": header_size,
                "offset_to_points": offset_to_points,
                "point_format": point_format,
                "point_record_len": point_record_len,
                "total_points": total_points,
                "scale": (scale_x, scale_y, scale_z),
                "offset": (off_x, off_y, off_z),
                "bounds": {
                    "min_x": min_x, "max_x": max_x,
                    "min_y": min_y, "max_y": max_y,
                    "min_z": min_z, "max_z": max_z,
                },
                "detected_crs": detected_crs or self.default_crs,
                "file_size_bytes": file_size
            }
            self.vlr_records = vlrs
            self._parsed = True
            return self.header

    def extract_points(self, max_points: Optional[int] = None) -> Dict[str, Any]:
        """
        Read point coordinates, classification, and intensity.
        Returns dict of numpy arrays: x, y, z, classification, intensity, (r, g, b if available).
        """
        if not self._parsed:
            self.parse_header()

        total = self.header["total_points"]
        num_to_read = min(total, max_points) if max_points else total
        offset = self.header["offset_to_points"]
        rec_len = self.header["point_record_len"]
        pt_fmt = self.header["point_format"]

        scale_x, scale_y, scale_z = self.header["scale"]
        off_x, off_y, off_z = self.header["offset"]

        with open(self.file_path, "rb") as f:
            f.seek(offset)
            raw_bytes = f.read(num_to_read * rec_len)

        # Parse binary points with numpy structured array for high speed
        dt_list = [
            ("ix", "<i4"),
            ("iy", "<i4"),
            ("iz", "<i4"),
            ("intensity", "<u2"),
        ]

        if pt_fmt in (0, 1, 2, 3, 4, 5):
            dt_list.extend([
                ("flags", "u1"),
                ("classification", "u1"),
                ("scan_angle", "i1"),
                ("user_data", "u1"),
                ("point_source_id", "<u2"),
            ])
            if pt_fmt in (1, 3, 4, 5):  # GPS time formats
                dt_list.append(("gps_time", "<f8"))
            if pt_fmt in (2, 3, 5):  # RGB formats
                dt_list.extend([
                    ("red", "<u2"),
                    ("green", "<u2"),
                    ("blue", "<u2"),
                ])
        elif pt_fmt in (6, 7, 8, 9, 10):  # LAS 1.4 formats
            dt_list.extend([
                ("return_flags", "<u2"),
                ("classification", "u1"),
                ("user_data", "u1"),
                ("scan_angle", "<i2"),
                ("point_source_id", "<u2"),
                ("gps_time", "<f8"),
            ])
            if pt_fmt in (7, 8, 10):  # RGB formats
                dt_list.extend([
                    ("red", "<u2"),
                    ("green", "<u2"),
                    ("blue", "<u2"),
                ])

        # Fill remaining padding to match rec_len
        current_len = sum(np.dtype(t).itemsize for _, t in dt_list)
        if rec_len > current_len:
            dt_list.append(("padding", f"V{rec_len - current_len}"))

        dt = np.dtype(dt_list)
        arr = np.frombuffer(raw_bytes[:num_to_read * rec_len], dtype=dt)

        # Unscale coordinates
        x = arr["ix"].astype(np.float64) * scale_x + off_x
        y = arr["iy"].astype(np.float64) * scale_y + off_y
        z = arr["iz"].astype(np.float64) * scale_z + off_z

        intensity = arr["intensity"]
        classification = arr["classification"] & 0x1F  # 5 bits for standard class in LAS <= 1.3

        result = {
            "x": x,
            "y": y,
            "z": z,
            "intensity": intensity,
            "classification": classification,
            "has_rgb": "red" in arr.dtype.names
        }

        if result["has_rgb"]:
            r = arr["red"]
            g = arr["green"]
            b = arr["blue"]
            if r.max() > 255 or g.max() > 255 or b.max() > 255:
                result["r"] = (r >> 8).astype(np.uint8)
                result["g"] = (g >> 8).astype(np.uint8)
                result["b"] = (b >> 8).astype(np.uint8)
            else:
                result["r"] = r.astype(np.uint8)
                result["g"] = g.astype(np.uint8)
                result["b"] = b.astype(np.uint8)

        return result

    def get_metadata_and_stats(self, max_sample_points: int = 100000) -> Dict[str, Any]:
        """Compute full metadata, CRS conversion, WGS84 bounding polygon, and class stats."""
        if not self._parsed:
            self.parse_header()

        data = self.extract_points(max_points=max_sample_points)
        x = data["x"]
        y = data["y"]
        z = data["z"]
        classes = data["classification"]
        intensities = data["intensity"]

        crs_str = self.header["detected_crs"]
        try:
            transformer_wgs84 = pyproj.Transformer.from_crs(crs_str, "EPSG:4326", always_xy=True)
            lons, lats = transformer_wgs84.transform(x, y)
        except Exception as e:
            logger.warning(f"Could not transform with CRS {crs_str}: {e}. Fallback to identity / direct coords.")
            lons, lats = x, y

        min_lon, max_lon = float(np.min(lons)), float(np.max(lons))
        min_lat, max_lat = float(np.min(lats)), float(np.max(lats))
        min_z, max_z = float(np.min(z)), float(np.max(z))

        # Build WGS84 Polygon extent
        bbox_poly = Polygon([
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
            (min_lon, min_lat),
        ])

        # Area & density
        dx = self.header["bounds"]["max_x"] - self.header["bounds"]["min_x"]
        dy = self.header["bounds"]["max_y"] - self.header["bounds"]["min_y"]
        area_sqm = max(1.0, abs(dx * dy))
        point_density = round(self.header["total_points"] / area_sqm, 2)

        # Classification histogram
        unique_classes, counts = np.unique(classes, return_counts=True)
        class_histogram = {}
        for c, count in zip(unique_classes, counts):
            c_int = int(c)
            class_histogram[c_int] = {
                "name": ASPRS_CLASSIFICATIONS.get(c_int, f"Class {c_int}"),
                "count": int(count),
                "percentage": round(float(count) / len(classes) * 100.0, 1)
            }

        return {
            "version": self.header["version"],
            "point_count": self.header["total_points"],
            "point_density": point_density,
            "crs": crs_str,
            "min_z": min_z,
            "max_z": max_z,
            "center": {
                "lon": round((min_lon + max_lon) / 2.0, 7),
                "lat": round((min_lat + max_lat) / 2.0, 7),
                "alt": round((min_z + max_z) / 2.0, 2)
            },
            "wgs84_bounds": {
                "min_lon": min_lon,
                "max_lon": max_lon,
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_z": min_z,
                "max_z": max_z
            },
            "native_bounds": self.header["bounds"],
            "extent_geojson": mapping(bbox_poly),
            "classification_breakdown": class_histogram,
            "intensity_stats": {
                "min": int(np.min(intensities)),
                "max": int(np.max(intensities)),
                "mean": round(float(np.mean(intensities)), 1)
            }
        }

    def generate_3d_tiles(self, output_dir: str, max_points: int = 150000) -> Dict[str, str]:
        """
        Generate OGC 3D Tiles 1.0 Point Cloud (.pnts + tileset.json) for CesiumJS.
        """
        os.makedirs(output_dir, exist_ok=True)
        meta = self.get_metadata_and_stats()
        crs_str = self.header["detected_crs"]

        total = self.header["total_points"]
        step = max(1, total // max_points)
        raw_pts = self.extract_points()

        x = raw_pts["x"][::step]
        y = raw_pts["y"][::step]
        z = raw_pts["z"][::step]
        classes = raw_pts["classification"][::step]
        intensities = raw_pts["intensity"][::step]
        has_rgb = raw_pts["has_rgb"]

        n_pts = len(x)
        logger.info(f"Generating 3D Tiles for {n_pts:,} points (sampled from {total:,})")

        # Transform to WGS84 degrees
        try:
            transformer_wgs84 = pyproj.Transformer.from_crs(crs_str, "EPSG:4326", always_xy=True)
            lons, lats = transformer_wgs84.transform(x, y)
        except Exception:
            lons, lats = x, y

        # Transform to ECEF (EPSG:4978)
        transformer_ecef = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978", always_xy=True)
        ecef_x, ecef_y, ecef_z = transformer_ecef.transform(lons, lats, z)

        # Calculate RTC_CENTER (Relative To Center) in ECEF
        center_x = float(np.mean(ecef_x))
        center_y = float(np.mean(ecef_y))
        center_z = float(np.mean(ecef_z))

        # Position relative to center as float32
        rel_x = (ecef_x - center_x).astype(np.float32)
        rel_y = (ecef_y - center_y).astype(np.float32)
        rel_z = (ecef_z - center_z).astype(np.float32)

        # Interleave positions [x0, y0, z0, x1, y1, z1, ...]
        positions = np.empty((n_pts, 3), dtype=np.float32)
        positions[:, 0] = rel_x
        positions[:, 1] = rel_y
        positions[:, 2] = rel_z
        pos_bytes = positions.tobytes()

        # Build RGB colors (from LAS RGB, or classification coloring if no RGB)
        if has_rgb and "r" in raw_pts:
            r = raw_pts["r"][::step]
            g = raw_pts["g"][::step]
            b = raw_pts["b"][::step]
            rgb = np.empty((n_pts, 3), dtype=np.uint8)
            rgb[:, 0] = r
            rgb[:, 1] = g
            rgb[:, 2] = b
        else:
            rgb = np.empty((n_pts, 3), dtype=np.uint8)
            for c_code, color in CLASSIFICATION_COLORS.items():
                mask = (classes == c_code)
                rgb[mask] = color
            unassigned = np.ones(n_pts, dtype=bool)
            for c_code in CLASSIFICATION_COLORS.keys():
                unassigned &= (classes != c_code)
            rgb[unassigned] = (200, 200, 200)

        rgb_bytes = rgb.tobytes()

        # Build Feature Table JSON
        feature_table_dict = {
            "POINTS_LENGTH": n_pts,
            "RTC_CENTER": [center_x, center_y, center_z],
            "POSITION": {"byteOffset": 0},
            "RGB": {"byteOffset": len(pos_bytes)},
        }
        feature_table_json = json.dumps(feature_table_dict).encode("utf-8")
        ft_json_padded = feature_table_json + b" " * ((8 - len(feature_table_json) % 8) % 8)

        # Binary payload
        ft_binary = pos_bytes + rgb_bytes
        ft_bin_padded = ft_binary + b"\x00" * ((8 - len(ft_binary) % 8) % 8)

        bt_json_padded = b""
        bt_bin_padded = b""

        header_len = 28
        total_len = (
            header_len
            + len(ft_json_padded)
            + len(ft_bin_padded)
            + len(bt_json_padded)
            + len(bt_bin_padded)
        )

        pnts_header = struct.pack(
            "<4sIIIIII",
            b"pnts",
            1,
            total_len,
            len(ft_json_padded),
            len(ft_bin_padded),
            len(bt_json_padded),
            len(bt_bin_padded),
        )

        pnts_filepath = os.path.join(output_dir, "tile.pnts")
        with open(pnts_filepath, "wb") as f:
            f.write(pnts_header)
            f.write(ft_json_padded)
            f.write(ft_bin_padded)

        # Bounding volume in WGS84 radians [west, south, east, north, min_height, max_height]
        bounds = meta["wgs84_bounds"]
        west = math.radians(bounds["min_lon"])
        south = math.radians(bounds["min_lat"])
        east = math.radians(bounds["max_lon"])
        north = math.radians(bounds["max_lat"])
        min_h = bounds["min_z"]
        max_h = bounds["max_z"]

        tileset_dict = {
            "asset": {
                "version": "1.0",
                "generator": "Geo3D Platform 3D Tiles Generator"
            },
            "geometricError": 500.0,
            "root": {
                "boundingVolume": {
                    "region": [west, south, east, north, min_h, max_h]
                },
                "geometricError": 0.0,
                "refine": "ADD",
                "content": {
                    "uri": "tile.pnts"
                }
            }
        }

        tileset_filepath = os.path.join(output_dir, "tileset.json")
        with open(tileset_filepath, "w") as f:
            json.dump(tileset_dict, f, indent=2)

        return {
            "tileset_json": tileset_filepath,
            "tile_pnts": pnts_filepath
        }

    def get_sample_points(self, sample_size: int = 20000) -> List[Dict[str, Any]]:
        """Return a lightweight sample of points for fast in-browser preview."""
        data = self.extract_points()
        total = len(data["x"])
        step = max(1, total // sample_size)

        x = data["x"][::step]
        y = data["y"][::step]
        z = data["z"][::step]
        cls = data["classification"][::step]
        intensities = data["intensity"][::step]

        crs_str = self.header["detected_crs"]
        try:
            transformer = pyproj.Transformer.from_crs(crs_str, "EPSG:4326", always_xy=True)
            lons, lats = transformer.transform(x, y)
        except Exception:
            lons, lats = x, y

        samples = []
        for lon, lat, elev, c, inten in zip(lons, lats, z, cls, intensities):
            samples.append({
                "lon": round(float(lon), 7),
                "lat": round(float(lat), 7),
                "alt": round(float(elev), 2),
                "classification": int(c),
                "intensity": int(inten),
            })
        return samples
