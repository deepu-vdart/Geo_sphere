"""
Dataset service: validation, metadata extraction, and 3D processing pipelines.
Supports LiDAR (LAS/LAZ), Rasters (GeoTIFF/DEM), and vectors.
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
import uuid
from typing import Optional, Dict, Any

from app.config import get_settings
from app.processing.pdal_proc.las_processor import LASProcessor
from app.processing.gdal_proc.raster_processor import RasterProcessor

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Dataset Type Inference ──────────────────────────────────────────────────

POINT_CLOUD_EXTS = {".las", ".laz", ".ply"}
RASTER_EXTS = {".tif", ".tiff", ".geotiff", ".dem", ".dtm", ".dsm"}
VECTOR_EXTS = {".geojson", ".json", ".shp", ".zip"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
MESH_EXTS = {".obj", ".glb", ".gltf"}
GL3D_SCENE_MARKER = "gl3d_scene"  # Special dataset type for GL3D photogrammetry scenes


def infer_dataset_type(ext: str) -> str:
    """Infer dataset category from file extension."""
    ext = ext.lower()
    if ext in POINT_CLOUD_EXTS:
        return "point_cloud"
    if ext in RASTER_EXTS:
        return "raster"
    if ext in VECTOR_EXTS:
        return "vector"
    if ext in IMAGE_EXTS:
        return "image"
    if ext in MESH_EXTS:
        return "mesh"
    if ext == ".gl3d":
        return GL3D_SCENE_MARKER
    return "unknown"


# ─── Validation Job ──────────────────────────────────────────────────────────

async def run_validation_job(job_id: str, file_path: str, dataset_type: str) -> None:
    """
    Background task: validate uploaded dataset and extract metadata, CRS, and bounds.
    """
    from app.database import AsyncSessionLocal
    from app.models.processing_job import ProcessingJob
    from app.models.dataset import Dataset
    from app.models.project import Project
    from sqlalchemy import select

    logger.info(f"[Job {job_id}] Starting validation for {file_path} ({dataset_type})")

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"[Job {job_id}] Job not found in database")
                return

            job.status = "RUNNING"
            job.started_at = datetime.now(timezone.utc)
            job.progress = 10
            await db.commit()

            errors = []
            extracted_metadata: Dict[str, Any] = {}

            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
            elif os.path.getsize(file_path) == 0:
                errors.append("File is empty (0 bytes).")
            elif os.path.getsize(file_path) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                errors.append(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")

            if not errors:
                ext = os.path.splitext(file_path)[1].lower()
                job.progress = 30
                await db.commit()

                # Process point clouds
                if ext in POINT_CLOUD_EXTS:
                    try:
                        # Use dataset's CRS if available, otherwise fall back to default
                        ds_crs = None
                        if job.dataset_id:
                            ds_result2 = await db.execute(
                                select(Dataset).where(Dataset.id == job.dataset_id)
                            )
                            ds2 = ds_result2.scalar_one_or_none()
                            if ds2 and ds2.crs:
                                ds_crs = ds2.crs
                            # Also check project CRS
                            if not ds_crs and ds2 and ds2.project_id:
                                proj_result = await db.execute(
                                    select(Project).where(Project.id == ds2.project_id)
                                )
                                proj = proj_result.scalar_one_or_none()
                                if proj and proj.crs and proj.crs != "EPSG:4326":
                                    ds_crs = proj.crs

                        processor = LASProcessor(file_path, default_crs=ds_crs or "EPSG:26913")
                        stats = processor.get_metadata_and_stats()
                        extracted_metadata = {
                            "point_count": stats["point_count"],
                            "point_density": stats["point_density"],
                            "crs": stats["crs"],
                            "min_z": stats["min_z"],
                            "max_z": stats["max_z"],
                            "wgs84_bounds": stats["wgs84_bounds"],
                            "center": stats["center"],
                            "classification_breakdown": stats["classification_breakdown"],
                            "intensity_stats": stats["intensity_stats"]
                        }
                    except Exception as e:
                        logger.warning(f"[Job {job_id}] LAS metadata extraction warning: {e}")
                        errors.append(f"Could not parse LAS point cloud: {str(e)}")

                # Process rasters
                elif ext in RASTER_EXTS:
                    try:
                        r_processor = RasterProcessor(file_path)
                        r_stats = r_processor.get_metadata_and_stats()
                        extracted_metadata = {
                            "raster_width": r_stats["width"],
                            "raster_height": r_stats["height"],
                            "band_count": r_stats["bands"],
                            "crs": r_stats["crs"],
                            "min_z": r_stats["min_z"],
                            "max_z": r_stats["max_z"],
                            "center": r_stats["center"],
                            "wgs84_bounds": r_stats["wgs84_bounds"]
                        }
                    except Exception as e:
                        logger.warning(f"[Job {job_id}] Raster metadata extraction warning: {e}")
                        errors.append(f"Could not parse raster dataset: {str(e)}")

            job.progress = 75
            await db.commit()

            # Update dataset record in DB
            if job.dataset_id:
                ds_result = await db.execute(
                    select(Dataset).where(Dataset.id == job.dataset_id)
                )
                dataset = ds_result.scalar_one_or_none()
                if dataset:
                    if errors:
                        dataset.processing_status = "validation_failed"
                        dataset.validation_errors = errors
                    else:
                        dataset.processing_status = "validated"
                        dataset.validation_errors = []
                        if "point_count" in extracted_metadata:
                            dataset.point_count = extracted_metadata["point_count"]
                        if "point_density" in extracted_metadata:
                            dataset.point_density = extracted_metadata["point_density"]
                        if "crs" in extracted_metadata:
                            dataset.crs = extracted_metadata["crs"]
                        if "min_z" in extracted_metadata:
                            dataset.min_z = extracted_metadata["min_z"]
                        if "max_z" in extracted_metadata:
                            dataset.max_z = extracted_metadata["max_z"]
                        if "raster_width" in extracted_metadata:
                            dataset.raster_width = extracted_metadata["raster_width"]
                            dataset.raster_height = extracted_metadata["raster_height"]
                            dataset.band_count = extracted_metadata["band_count"]
                        
                        dataset.metadata_json = extracted_metadata

                    await db.commit()

            completed_at = datetime.now(timezone.utc)
            job.status = "FAILED" if errors else "COMPLETED"
            job.progress = 100
            job.completed_at = completed_at
            job.duration_seconds = (completed_at - job.started_at).total_seconds()
            if errors:
                job.error_message = "; ".join(errors)
            else:
                job.log_output = f"Validation passed for {dataset_type}. Extracted metadata successfully."

            await db.commit()
            logger.info(f"[Job {job_id}] Validation finished. Status: {job.status}")

        except Exception as e:
            logger.exception(f"[Job {job_id}] Validation crashed: {e}")
            try:
                job.status = "FAILED"
                job.error_message = str(e)
                await db.commit()
            except Exception:
                pass


# ─── Processing Job ──────────────────────────────────────────────────────────

async def run_processing_job(job_id: str, file_path: str, dataset_type: str) -> None:
    """
    Background task: run 3D processing pipeline on a dataset (e.g. generate OGC 3D Tiles).
    """
    from app.database import AsyncSessionLocal
    from app.models.processing_job import ProcessingJob
    from app.models.dataset import Dataset
    from app.models.asset import Asset
    from sqlalchemy import select

    logger.info(f"[Job {job_id}] Starting 3D processing for {dataset_type} — {file_path}")

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            job.status = "RUNNING"
            job.started_at = datetime.now(timezone.utc)
            job.progress = 15
            job.log_output = f"Initiating 3D processing pipeline for {dataset_type}..."
            await db.commit()

            ds_result = await db.execute(
                select(Dataset).where(Dataset.id == job.dataset_id)
            )
            dataset = ds_result.scalar_one_or_none()
            if not dataset:
                raise ValueError(f"Associated dataset {job.dataset_id} not found.")

            ext = os.path.splitext(file_path)[1].lower()
            dataset_tiles_dir = os.path.join(settings.TILES_DIR, str(dataset.id))
            os.makedirs(dataset_tiles_dir, exist_ok=True)

            if ext in POINT_CLOUD_EXTS:
                job.progress = 30
                job.log_output += f"\n[Step 1/3] Parsing LAS point cloud and computing coordinate transforms..."
                await db.commit()

                # Process LAS
                processor = LASProcessor(file_path, default_crs=dataset.crs or "EPSG:26913")
                stats = processor.get_metadata_and_stats()

                job.progress = 60
                job.log_output += f"\n[Step 2/3] Generating OGC 3D Tiles (.pnts) with LOD and classification colors..."
                await db.commit()

                # Generate hierarchical OGC 3D Tiles 1.1 with octree LOD
                from app.processing.tiling.tile_generator import HierarchicalTileGenerator
                tile_gen = HierarchicalTileGenerator(processor)
                tiles = tile_gen.generate(dataset_tiles_dir, max_tile_points=8000, max_total_points=250000)


                job.progress = 85
                job.log_output += f"\n[Step 3/3] Registering 3D Tileset asset in catalog..."
                await db.commit()

                # Update dataset
                dataset.processing_status = "ready"
                dataset.point_count = stats["point_count"]
                dataset.point_density = stats["point_density"]
                dataset.min_z = stats["min_z"]
                dataset.max_z = stats["max_z"]
                dataset.crs = stats["crs"]
                dataset.metadata_json = stats

                # Create / update 3D Tiles asset
                asset_result = await db.execute(
                    select(Asset).where(
                        Asset.dataset_id == dataset.id,
                        Asset.asset_type == "3d_tiles"
                    )
                )
                asset = asset_result.scalar_one_or_none()
                if not asset:
                    asset = Asset(
                        dataset_id=dataset.id,
                        asset_type="3d_tiles",
                        name=f"{dataset.name} — 3D Tileset",
                        file_path=tiles["tileset_json"],
                        file_format="3dtiles",
                        url=f"/api/datasets/{dataset.id}/tileset.json",
                        metadata_json={
                            "point_count": stats["point_count"],
                            "bounds": stats["wgs84_bounds"],
                            "center": stats["center"]
                        }
                    )
                    db.add(asset)
                else:
                    asset.file_path = tiles["tileset_json"]
                    asset.url = f"/api/datasets/{dataset.id}/tileset.json"
                    asset.metadata_json = {
                        "point_count": stats["point_count"],
                        "bounds": stats["wgs84_bounds"],
                        "center": stats["center"]
                    }

                await db.commit()

            elif ext in RASTER_EXTS:
                job.progress = 40
                job.log_output += f"\n[Step 1/2] Parsing GeoTIFF/DEM raster bands..."
                await db.commit()

                r_proc = RasterProcessor(file_path, default_crs=dataset.crs or "EPSG:4326")
                r_stats = r_proc.get_metadata_and_stats()

                job.progress = 80
                job.log_output += f"\n[Step 2/2] Generating terrain asset catalog entry..."
                dataset.processing_status = "ready"
                dataset.raster_width = r_stats["width"]
                dataset.raster_height = r_stats["height"]
                dataset.band_count = r_stats["bands"]
                dataset.min_z = r_stats["min_z"]
                dataset.max_z = r_stats["max_z"]
                dataset.metadata_json = r_stats

                asset_result = await db.execute(
                    select(Asset).where(
                        Asset.dataset_id == dataset.id,
                        Asset.asset_type == "dem"
                    )
                )
                asset = asset_result.scalar_one_or_none()
                if not asset:
                    asset = Asset(
                        dataset_id=dataset.id,
                        asset_type="dem",
                        name=f"{dataset.name} — Elevation DEM",
                        file_path=file_path,
                        file_format="geotiff",
                        url=f"/api/datasets/{dataset.id}/raw",
                        metadata_json=r_stats
                    )
                    db.add(asset)

                await db.commit()

            completed_at = datetime.now(timezone.utc)
            job.status = "COMPLETED"
            job.progress = 100
            job.completed_at = completed_at
            job.duration_seconds = (completed_at - job.started_at).total_seconds()
            job.log_output += f"\n3D processing completed successfully in {job.duration_seconds:.2f}s."
            await db.commit()

            logger.info(f"[Job {job_id}] 3D processing completed successfully.")

        except Exception as e:
            logger.exception(f"[Job {job_id}] Processing failed: {e}")
            try:
                job.status = "FAILED"
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
            except Exception:
                pass
