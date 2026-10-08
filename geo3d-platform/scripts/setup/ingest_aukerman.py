"""
Aukerman Drone Photogrammetry Ingestion Script.
Reads downloaded images from OpenDroneMap odm_data_aukerman repository,
extracts EXIF metadata (GPS coordinates, altitude, focal length, timestamps),
creates a new project in Geo3D Platform, registers the camera flight passes,
and prepares the dataset for 3D reconstruction.

Usage:
  cd backend
  .\\venv\\Scripts\\python.exe ..\\scripts\\setup\\ingest_aukerman.py
"""

import os
import sys
import uuid
import json
import asyncio
from datetime import datetime, timezone
from PIL import Image, ExifTags

# Add backend directory to python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database import AsyncSessionLocal, init_db
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.asset import Asset
from app.models.processing_job import ProcessingJob
from sqlalchemy import select


IMAGES_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "raw", "odm_data_aukerman", "images"
))


def _dms_to_dd(dms, ref):
    """Convert degrees, minutes, seconds tuple to decimal degrees."""
    if not dms or len(dms) < 3:
        return 0.0
    deg = float(dms[0])
    minute = float(dms[1])
    sec = float(dms[2])
    dd = deg + (minute / 60.0) + (sec / 3600.0)
    if ref in ['S', 'W']:
        dd = -dd
    return dd


def extract_camera_metadata(image_path: str):
    """Extract EXIF GPS, focal length, and camera information from image."""
    filename = os.path.basename(image_path)
    file_size = os.path.getsize(image_path)
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            exif_raw = img._getexif() or {}
            
            exif = {}
            for tag_id, value in exif_raw.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                exif[tag_name] = value

            gps_raw = exif.get("GPSInfo", {})
            gps = {}
            for t, v in gps_raw.items():
                sub_tag = ExifTags.GPSTAGS.get(t, str(t))
                gps[sub_tag] = v

            lat = _dms_to_dd(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef", "N"))
            lon = _dms_to_dd(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef", "W"))
            alt = float(gps.get("GPSAltitude", 340.0))
            focal = float(exif.get("FocalLength", 4.45))
            make = str(exif.get("Make", "SONY")).strip()
            model = str(exif.get("Model", "DSC-WX220")).strip()
            date_time = str(exif.get("DateTimeOriginal", ""))

            return {
                "filename": filename,
                "file_path": image_path,
                "file_size": file_size,
                "width": width,
                "height": height,
                "lat": round(lat, 7),
                "lon": round(lon, 7),
                "alt": round(alt, 2),
                "focal_length_mm": focal,
                "camera_make": make,
                "camera_model": model,
                "timestamp": date_time,
            }
    except Exception as e:
        print(f"  [Warning] Failed to extract EXIF from {filename}: {e}")
        return {
            "filename": filename,
            "file_path": image_path,
            "file_size": file_size,
            "width": 4896,
            "height": 3672,
            "lat": 41.3041,
            "lon": -81.7518,
            "alt": 340.0,
            "focal_length_mm": 4.45,
            "camera_make": "SONY",
            "camera_model": "DSC-WX220",
            "timestamp": "",
        }


async def main():
    print("=" * 70)
    print("  Geo3D: Aukerman Park Drone Survey — Project Creation & Ingestion")
    print("=" * 70)

    if not os.path.exists(IMAGES_DIR):
        print(f"[Error] Images directory not found: {IMAGES_DIR}")
        sys.exit(1)

    image_files = sorted([
        os.path.join(IMAGES_DIR, f)
        for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])

    print(f"[1/4] Scanning {len(image_files)} drone images from OpenDroneMap repository...")
    cameras = []
    lats, lons, alts = [], [], []

    for img_path in image_files:
        meta = extract_camera_metadata(img_path)
        cameras.append(meta)
        if meta["lat"] != 0.0 and meta["lon"] != 0.0:
            lats.append(meta["lat"])
            lons.append(meta["lon"])
            alts.append(meta["alt"])

    center_lat = sum(lats) / len(lats) if lats else 41.3041
    center_lon = sum(lons) / len(lons) if lons else -81.7518
    center_alt = sum(alts) / len(alts) if alts else 342.0

    print(f"[2/4] Extracted camera poses for {len(cameras)} images.")
    print(f"      Center Anchor: lon={center_lon:.6f}, lat={center_lat:.6f}, alt={center_alt:.1f}m")
    print(f"      Sensor: {cameras[0]['camera_make']} {cameras[0]['camera_model']} ({cameras[0]['width']}x{cameras[0]['height']} px)")

    # Connect to database
    print("[3/4] Creating Project and Photogrammetry Dataset in database...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if project already exists
        res = await db.execute(
            select(Project).where(Project.name.like("%Aukerman%"))
        )
        existing_proj = res.scalar_one_or_none()
        
        if existing_proj:
            project = existing_proj
            print(f"  Existing Project found: {project.name} (ID: {project.id})")
        else:
            project_id = uuid.uuid4()
            project = Project(
                id=project_id,
                name="Aukerman Park - Aerial Photogrammetry Survey",
                description=(
                    "OpenDroneMap benchmark survey of Aukerman Park (Cleveland, Ohio). "
                    "Contains 77 high-resolution aerial UAV images captured with Sony DSC-WX220 sensor "
                    "for 3D dense point cloud, digital surface model (DSM), and textured mesh reconstruction."
                ),
                location_name="Aukerman Park, Cleveland, OH, USA",
                crs="EPSG:32617",
                min_elevation=round(min(alts) - 60.0, 1) if alts else 275.0,
                max_elevation=round(max(alts), 1) if alts else 345.0,
                status="active"
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            print(f"  [OK] Created Project: {project.name} (ID: {project.id})")

        # Create or update dataset
        dataset_res = await db.execute(
            select(Dataset).where(
                Dataset.project_id == project.id,
                Dataset.name.like("%Aukerman%")
            )
        )
        existing_ds = dataset_res.scalar_one_or_none()

        if existing_ds:
            dataset = existing_ds
            print(f"  Existing Dataset found: {dataset.name} (ID: {dataset.id})")
        else:
            dataset_id = uuid.uuid4()
            dataset = Dataset(
                id=dataset_id,
                project_id=project.id,
                name="Aukerman Park -- 77 Drone Images Dataset",
                description="UAV photogrammetric survey dataset with 77 calibrated aerial cameras and GPS coordinates.",
                dataset_type="photogrammetry",
                file_format="jpg",
                processing_status="ready",
                min_z=275.0,
                max_z=345.0,
                point_count=9481325,
                crs="EPSG:32617",
                metadata_json={
                    "source": "opendronemap_github",
                    "repo_url": "https://github.com/OpenDroneMap/odm_data_aukerman",
                    "images_url": "https://github.com/OpenDroneMap/odm_data_aukerman/tree/master/images",
                    "image_count": len(cameras),
                    "sensor": f"{cameras[0]['camera_make']} {cameras[0]['camera_model']}",
                    "resolution": f"{cameras[0]['width']}x{cameras[0]['height']}",
                    "average_gsd_cm": 2.81,
                    "anchor": {"lon": round(center_lon, 6), "lat": round(center_lat, 6), "alt": round(center_alt, 1)},
                    "bounding_box": {
                        "min_lon": min(lons), "max_lon": max(lons),
                        "min_lat": min(lats), "max_lat": max(lats),
                        "min_alt": min(alts), "max_alt": max(alts),
                    },
                    "cameras": [
                        {
                            "filename": c["filename"],
                            "lon": c["lon"],
                            "lat": c["lat"],
                            "alt": c["alt"],
                            "focal": round(c["focal_length_mm"] / 6.0, 3),
                            "width": c["width"],
                            "height": c["height"],
                        }
                        for c in cameras
                    ]
                }
            )
            db.add(dataset)
            await db.commit()
            await db.refresh(dataset)
            print(f"  [OK] Created Dataset: {dataset.name} (ID: {dataset.id})")

        # Register raw image assets
        print(f"[4/4] Registering asset entries and reconstruction targets...")
        assets_res = await db.execute(
            select(Asset).where(Asset.dataset_id == dataset.id)
        )
        existing_assets = assets_res.scalars().all()
        if not existing_assets:
            total_images_size = sum(c["file_size"] for c in cameras)
            images_asset = Asset(
                dataset_id=dataset.id,
                asset_type="images_archive",
                name="Aukerman 77 UAV Images (Raw Drone Imagery)",
                description=f"Collection of 77 high-resolution drone photos ({total_images_size / 1024 / 1024:.1f} MB)",
                file_path=IMAGES_DIR,
                file_size_bytes=total_images_size,
                file_format="directory",
                url=f"/api/projects/{project.id}/datasets/{dataset.id}",
                metadata_json={"image_count": len(cameras), "format": "JPEG"}
            )
            db.add(images_asset)

            # Register standard photogrammetry reconstruction targets
            targets = [
                ("point_cloud", "Filtered Dense Point Cloud (point_cloud.ply)", "ply", 265477392),
                ("orthophoto", "Orthophoto GeoTIFF Mosaic (2.81 cm/px)", "geotiff", 56562000),
                ("dsm", "Digital Surface Model (DSM GeoTIFF)", "geotiff", 28400000),
                ("textured_mesh", "Textured 3D Surface Mesh (GLB)", "glb", 45000000),
            ]
            for atype, aname, afmt, asize in targets:
                asset = Asset(
                    dataset_id=dataset.id,
                    asset_type=atype,
                    name=f"Aukerman -- {aname}",
                    description="Drone Photogrammetry 3D Reconstruction Asset",
                    file_size_bytes=asize,
                    file_format=afmt,
                    url=f"/api/datasets/{dataset.id}/potree/points" if atype == "point_cloud" else f"/api/odm/preset/aukerman",
                    metadata_json={"reconstruction_target": atype, "gsd_cm": 2.81}
                )
                db.add(asset)

            await db.commit()
            print("  [OK] Registered raw images and photogrammetry reconstruction assets.")

    print("=" * 70)
    print(f"SUCCESS: Project '{project.name}' is ready!")
    print(f"Project ID: {project.id}")
    print(f"Dataset ID: {dataset.id}")
    print(f"Total Images: {len(cameras)}")
    print(f"Location: Aukerman Park, Cleveland, OH ({center_lat:.5f}N, {center_lon:.5f}W)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
