"""
Generate a synthetic LAS point cloud for Phase 2 development testing.
This creates a realistic terrain-like point cloud that can be used to test
the PDAL processing pipeline without downloading a large external dataset.

The dataset simulates a small hill/valley terrain ~200m x 200m with:
- Ground points (bare earth)
- Vegetation points (trees)
- Building points

CRS: EPSG:26913 (UTM Zone 13N, Colorado)
Approximate real-world location: Boulder, Colorado area

Run: python scripts/processing/generate_sample_data.py
Output: data/samples/sample_terrain.las
"""

import struct
import math
import random
import os

random.seed(42)

# Output path
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "samples")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sample_terrain.las")

# Area definition (UTM Zone 13N, near Boulder CO)
# Easting ~480000m, Northing ~4430000m
ORIGIN_X = 480000.0
ORIGIN_Y = 4430000.0
AREA_SIZE = 200.0  # 200m x 200m

# Point counts
N_GROUND = 50000
N_VEGETATION = 15000
N_BUILDINGS = 5000
TOTAL_POINTS = N_GROUND + N_VEGETATION + N_BUILDINGS

def terrain_z(x, y):
    """Realistic terrain height: hill + valley."""
    nx = (x - ORIGIN_X) / AREA_SIZE
    ny = (y - ORIGIN_Y) / AREA_SIZE
    z = (
        1750.0
        + 15.0 * math.sin(nx * math.pi * 2) * math.cos(ny * math.pi * 2)
        + 8.0 * math.sin(nx * math.pi * 4 + 0.5) * math.sin(ny * math.pi * 3)
        + 3.0 * math.sin(nx * math.pi * 8) * math.cos(ny * math.pi * 6)
    )
    return z


def write_las_file(filepath, points):
    """Write a minimal LAS 1.2 file with point format 0."""
    N = len(points)

    # Scale / offset
    scale_xy = 0.001
    scale_z  = 0.001
    off_x = ORIGIN_X
    off_y = ORIGIN_Y
    off_z = 1745.0

    # Header
    header = bytearray()
    header += b"LASF"                          # File signature
    header += struct.pack("<H", 0)             # File source ID
    header += struct.pack("<H", 0)             # Global encoding
    header += struct.pack("<I", 0)             # Project ID-1
    header += struct.pack("<H", 0)             # Project ID-2
    header += struct.pack("<H", 0)             # Project ID-3
    header += b"\x00" * 8                     # Project ID-4
    header += struct.pack("<B", 1)             # Version major (1)
    header += struct.pack("<B", 2)             # Version minor (2)
    header += b"Geo3D Sample" + b"\x00" * (32 - len("Geo3D Sample"))  # System ID
    header += b"Geo3D Generator " + b"\x00" * (32 - 16)               # Generating software
    header += struct.pack("<H", 1)             # File creation day of year
    header += struct.pack("<H", 2026)          # File creation year
    header += struct.pack("<H", 227)           # Header size (LAS 1.2)
    header += struct.pack("<I", 227)           # Offset to point data
    header += struct.pack("<I", 0)             # Number of variable length records
    header += struct.pack("<B", 0)             # Point data format ID
    header += struct.pack("<H", 20)            # Point data record length (format 0 = 20 bytes)
    header += struct.pack("<I", N)             # Number of point records
    header += struct.pack("<5I", N, 0, 0, 0, 0)  # Points by return
    # Scale factors
    header += struct.pack("<d", scale_xy)      # X scale factor
    header += struct.pack("<d", scale_xy)      # Y scale factor
    header += struct.pack("<d", scale_z)       # Z scale factor
    # Offsets
    header += struct.pack("<d", off_x)
    header += struct.pack("<d", off_y)
    header += struct.pack("<d", off_z)
    # Bounds
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    header += struct.pack("<d", max(xs))       # Max X
    header += struct.pack("<d", min(xs))       # Min X
    header += struct.pack("<d", max(ys))       # Max Y
    header += struct.pack("<d", min(ys))       # Min Y
    header += struct.pack("<d", max(zs))       # Max Z
    header += struct.pack("<d", min(zs))       # Min Z

    assert len(header) == 227, f"Header length mismatch: {len(header)}"

    # Point records (format 0: X (4) Y (4) Z (4) intensity (2) return_flags (1) class (1) scan_angle (1) user_data (1) src_id (2) = 20 bytes)
    point_data = bytearray()
    for x, y, z, classification, intensity in points:
        ix = int(round((x - off_x) / scale_xy))
        iy = int(round((y - off_y) / scale_xy))
        iz = int(round((z - off_z) / scale_z))
        point_data += struct.pack("<i", ix)
        point_data += struct.pack("<i", iy)
        point_data += struct.pack("<i", iz)
        point_data += struct.pack("<H", intensity)
        point_data += struct.pack("<B", 0b00001001)  # return 1 of 1, scan dir 0, edge 0
        point_data += struct.pack("<B", classification)
        point_data += struct.pack("<b", 0)           # scan angle rank
        point_data += struct.pack("<B", 0)           # user data
        point_data += struct.pack("<H", 0)           # point source ID

    with open(filepath, "wb") as f:
        f.write(header)
        f.write(point_data)


def main():
    print("Generating synthetic terrain point cloud...")
    print(f"  Area: {AREA_SIZE}m x {AREA_SIZE}m")
    print(f"  Location: UTM Zone 13N, ~Boulder CO")
    print(f"  Total points: {TOTAL_POINTS:,}")

    points = []

    # Ground points (class 2)
    print("  Generating ground points...")
    for _ in range(N_GROUND):
        x = ORIGIN_X + random.uniform(0, AREA_SIZE)
        y = ORIGIN_Y + random.uniform(0, AREA_SIZE)
        z = terrain_z(x, y) + random.gauss(0, 0.05)
        intensity = random.randint(2000, 8000)
        points.append((x, y, z, 2, intensity))

    # Vegetation points (class 5 — high vegetation)
    print("  Generating vegetation points...")
    # Create tree clusters
    tree_centers = [(
        ORIGIN_X + random.uniform(10, AREA_SIZE - 10),
        ORIGIN_Y + random.uniform(10, AREA_SIZE - 10)
    ) for _ in range(30)]

    per_tree = N_VEGETATION // len(tree_centers)
    for cx, cy in tree_centers:
        ground_z = terrain_z(cx, cy)
        tree_h = random.uniform(5, 18)
        for _ in range(per_tree):
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, 3.0) * (1 - random.random() ** 2)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            z = ground_z + random.uniform(0.5, tree_h)
            intensity = random.randint(1000, 4000)
            points.append((x, y, z, 5, intensity))

    # Building points (class 6 — building)
    print("  Generating building points...")
    buildings = [
        (ORIGIN_X + 50, ORIGIN_Y + 60, 25, 30, 5),   # x, y, w, d, h
        (ORIGIN_X + 120, ORIGIN_Y + 80, 15, 20, 4),
        (ORIGIN_X + 90, ORIGIN_Y + 140, 20, 15, 6),
    ]
    per_building = N_BUILDINGS // len(buildings)
    for bx, by, bw, bd, bh in buildings:
        ground_z = terrain_z(bx, by)
        for _ in range(per_building):
            # Roof and walls
            side = random.random()
            if side < 0.6:  # Roof
                x = bx + random.uniform(0, bw)
                y = by + random.uniform(0, bd)
                z = ground_z + bh
            else:  # Walls
                wall = random.randint(0, 3)
                if wall == 0: x, y = random.uniform(bx, bx + bw), by
                elif wall == 1: x, y = random.uniform(bx, bx + bw), by + bd
                elif wall == 2: x, y = bx, random.uniform(by, by + bd)
                else: x, y = bx + bw, random.uniform(by, by + bd)
                z = ground_z + random.uniform(0, bh)
            intensity = random.randint(5000, 12000)
            points.append((x, y, z, 6, intensity))

    # Shuffle points
    random.shuffle(points)

    print(f"  Writing {len(points):,} points to {OUTPUT_FILE}...")
    write_las_file(OUTPUT_FILE, points)

    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\nSample dataset created successfully!")
    print(f"  File: {OUTPUT_FILE}")
    print(f"  Size: {size_mb:.2f} MB")
    print(f"  Points: {len(points):,}")
    print(f"  Classification: Ground(2)={N_GROUND:,}, Veg(5)={N_VEGETATION:,}, Building(6)={N_BUILDINGS:,}")
    print(f"  CRS: EPSG:26913 (UTM Zone 13N)")
    print(f"  Bounds: X=[{ORIGIN_X}, {ORIGIN_X + AREA_SIZE}], Y=[{ORIGIN_Y}, {ORIGIN_Y + AREA_SIZE}]")


if __name__ == "__main__":
    main()
