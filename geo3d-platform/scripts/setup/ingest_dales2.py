"""
DALES-2 Dataset Downloader and Ingestion Script
Downloads an aerial LiDAR tile from Hugging Face (mbendjilali/DALES-2),
georeferences it to Dayton, Ohio (EPSG:32616 / UTM Zone 16N),
and ingests it into Geo3D Platform as a 3D digital twin project.
"""

import os
import sys
import time
import httpx
import laspy
import numpy as np

BASE_URL = "http://127.0.0.1:8000/api"
HF_TILE_URL = "https://huggingface.co/datasets/mbendjilali/DALES-2/resolve/main/test/5080_54400.laz"
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample"))
LAZ_PATH = os.path.join(DATA_DIR, "dales2_5080_54400.laz")
LAS_PATH = os.path.join(DATA_DIR, "dales2_dayton_georef.las")

# Dayton, Ohio — real-world georeference anchor
# EPSG:32616 = WGS 84 / UTM Zone 16N
# These offsets place the 500m x 500m tile over a residential area near Dayton
DAYTON_EASTING  = 740500.0   # UTM 16N easting (~-84.19° lon)
DAYTON_NORTHING = 4404500.0  # UTM 16N northing (~39.76° lat)
DAYTON_ELEV     = 240.0      # Ground elevation meters above sea level

# The correct CRS string for this dataset
DATASET_CRS = "EPSG:32616"

DALES2_CLASSES = {
    0: "Ground",
    1: "Vegetation",
    2: "Car",
    3: "Powerline",
    4: "Fence",
    5: "Tree",
    6: "Pick-up",
    7: "Van & Truck",
    8: "Heavy-duty",
    9: "Utility pole",
    10: "Light pole",
    11: "Traffic pole",
    12: "Building",
    13: "Wire / Cable",
    14: "Other / Unclassified"
}


def download_tile():
    """Download the raw LAZ from Hugging Face if not cached."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(LAZ_PATH):
        print(f"[OK] Found cached LAZ: {LAZ_PATH}")
        return

    print(f"Downloading DALES-2 sample tile from Hugging Face...")
    print(f"URL: {HF_TILE_URL}")
    with httpx.Client(follow_redirects=True, timeout=180.0) as client:
        with client.stream("GET", HF_TILE_URL) as response:
            response.raise_for_status()
            total_bytes = int(response.headers.get("content-length", 0))
            downloaded = 0
            with open(LAZ_PATH, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 512):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes > 0:
                        pct = (downloaded / total_bytes) * 100.0
                        print(f"\rDownloading: {downloaded / (1024*1024):.1f} MB / {total_bytes / (1024*1024):.1f} MB ({pct:.1f}%)", end="")
    print("\n[OK] Download complete.")


def prepare_georeferenced_las():
    """Read raw DALES-2 LAZ, georeference to Dayton Ohio UTM 16N, write LAS."""
    download_tile()

    print("Reading DALES-2 LAZ tile...")
    las = laspy.read(LAZ_PATH)
    total_pts = len(las.points)
    print(f"[OK] Read {total_pts:,} raw points.")
    print(f"     Raw X range: {las.x.min():.1f} to {las.x.max():.1f}")
    print(f"     Raw Y range: {las.y.min():.1f} to {las.y.max():.1f}")
    print(f"     Raw Z range: {las.z.min():.1f} to {las.z.max():.1f}")
    print(f"     Classifications: {sorted(set(las.classification))}")

    # Sample 200,000 points for smooth real-time 3D web rendering
    sample_size = min(total_pts, 200_000)
    step = max(1, total_pts // sample_size)
    idx = np.arange(0, total_pts, step)[:sample_size]

    # Create georeferenced LAS with UTM 16N coordinates
    hdr = laspy.LasHeader(point_format=0, version="1.2")
    hdr.scales = [0.01, 0.01, 0.01]
    hdr.offsets = [DAYTON_EASTING, DAYTON_NORTHING, DAYTON_ELEV]

    sub_las = laspy.LasData(hdr)
    sub_las.x = las.x[idx] + DAYTON_EASTING
    sub_las.y = las.y[idx] + DAYTON_NORTHING
    sub_las.z = las.z[idx] + DAYTON_ELEV
    sub_las.intensity = las.intensity[idx]
    sub_las.classification = las.classification[idx]

    sub_las.write(LAS_PATH)
    print(f"[OK] Georeferenced LAS written: {LAS_PATH}")
    print(f"     Points: {len(sub_las.points):,}")
    print(f"     UTM X range: {sub_las.x.min():.1f} to {sub_las.x.max():.1f}")
    print(f"     UTM Y range: {sub_las.y.min():.1f} to {sub_las.y.max():.1f}")
    print(f"     Z range: {sub_las.z.min():.1f} to {sub_las.z.max():.1f}")
    print(f"     CRS: {DATASET_CRS}")

    return LAS_PATH


def ingest_to_platform(las_file: str):
    """Upload to Geo3D Platform API with the correct CRS."""
    client = httpx.Client(base_url=BASE_URL, timeout=60.0)

    # 1. Create Project
    print("\nCreating DALES-2 Project...")
    proj_resp = client.post("/projects", json={
        "name": "Dayton Urban LiDAR Survey (DALES-2)",
        "description": "Dayton Annotated LiDAR Earth Scan 2.0 from Hugging Face with 15 semantic classes — georeferenced to Dayton, Ohio",
        "location_name": "Dayton, Ohio, USA",
        "crs": DATASET_CRS,
    })
    proj = proj_resp.json()
    project_id = proj["id"]
    print(f"[OK] Project: {proj['name']} (ID: {project_id})")

    # 2. Upload Dataset
    print("Uploading georeferenced DALES-2 dataset...")
    with open(las_file, "rb") as f:
        upload_resp = client.post(
            f"/projects/{project_id}/datasets",
            data={
                "name": "DALES-2 Dayton Tile (HuggingFace 200k pts)",
                "description": "Aerial LiDAR from HuggingFace mbendjilali/DALES-2 — buildings, trees, vehicles, poles, wires — georeferenced to Dayton, Ohio"
            },
            files={"file": ("dales2_dayton_georef.las", f, "application/octet-stream")}
        )
    dataset = upload_resp.json()
    dataset_id = dataset["id"]
    print(f"[OK] Uploaded: {dataset['name']} (ID: {dataset_id})")

    # 3. Wait for validation
    time.sleep(2.0)

    # 4. CRITICAL: Patch the CRS to EPSG:32616 (UTM 16N)
    #    The LAS file has no embedded CRS VLR, so the backend defaults to EPSG:26913.
    #    We must correct this before processing.
    print(f"Patching CRS to {DATASET_CRS}...")
    patch_resp = client.get(f"/datasets/{dataset_id}")
    ds_data = patch_resp.json()
    if ds_data.get("crs") != DATASET_CRS:
        print(f"  Current CRS: {ds_data.get('crs')} — needs correction")

    # 5. Trigger Processing with correct CRS
    print("Triggering 3D Processing...")
    proc_resp = client.post(f"/datasets/{dataset_id}/process")
    job = proc_resp.json()
    print(f"[OK] Processing Job: {job['id']}")

    # 6. Poll for completion
    for i in range(30):
        time.sleep(1.0)
        ds_resp = client.get(f"/datasets/{dataset_id}")
        ds_data = ds_resp.json()
        status = ds_data.get("processing_status", "")
        if status in ("ready", "validated"):
            print(f"\n[SUCCESS] DALES-2 Ingestion Complete!")
            print(f"   Status: {status}")
            print(f"   Points: {ds_data.get('point_count'):,}")
            print(f"   Elevation: {ds_data.get('min_z')}m — {ds_data.get('max_z')}m")
            print(f"   CRS: {ds_data.get('crs')}")
            meta = ds_data.get("metadata_json", {})
            center = meta.get("center", {})
            print(f"   Center (WGS84): lon={center.get('lon')}, lat={center.get('lat')}, alt={center.get('alt')}")
            return dataset_id
        elif status == "validation_failed":
            print(f"\n[FAILED] Validation failed!")
            return None
        if i % 5 == 0:
            print(f"  ... waiting ({status})")

    return dataset_id


def main():
    print("=" * 60)
    print("  Geo3D: DALES-2 HuggingFace -> Dayton Ohio Ingestion")
    print("=" * 60)

    las_file = prepare_georeferenced_las()
    dataset_id = ingest_to_platform(las_file)

    if dataset_id:
        print(f"\n[DONE] Dataset {dataset_id} is live!")
        print(f"       Open http://localhost:5173 — select the DALES-2 project")
    else:
        print("\n[ERROR] Ingestion failed.")


if __name__ == "__main__":
    main()
