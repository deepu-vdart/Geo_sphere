"""
Terrain Derivatives REST API Endpoints
Provides DTM, DSM, Hillshade, Slope, Aspect, Roughness, and Contours generation and retrieval.
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.dataset import Dataset
from app.processing.gdal_proc.terrain_derivatives import terrain_engine
from app.processing.pdal_proc.las_processor import LASProcessor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/terrain", tags=["Terrain Products"])


@router.get("/datasets/{dataset_id}/derivatives")
async def get_terrain_derivatives(
    dataset_id: uuid.UUID,
    grid_resolution: float = Query(1.0, ge=0.25, le=10.0, description="Grid resolution in meters"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate comprehensive terrain products (DTM, DSM, Hillshade, Slope, Aspect, Roughness, Contours)
    from a point cloud dataset.
    """
    res = await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active"))
    dataset = res.scalar_one_or_none()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset not found or file missing.")

    if dataset.dataset_type != "point_cloud":
        raise HTTPException(status_code=400, detail="Terrain derivatives require a point cloud dataset.")

    try:
        proc = LASProcessor(dataset.file_path, default_crs=dataset.crs or "EPSG:32616")
        points = proc.extract_points()

        center_lon = -84.19
        center_lat = 39.76
        if dataset.metadata_json and "center" in dataset.metadata_json:
            center_lon = dataset.metadata_json["center"].get("lon", center_lon)
            center_lat = dataset.metadata_json["center"].get("lat", center_lat)

        derivatives = terrain_engine.compute_all_derivatives(
            points=points,
            grid_resolution=grid_resolution,
            crs=dataset.crs or "EPSG:32616",
            origin_lon=center_lon,
            origin_lat=center_lat
        )

        return {
            "dataset_id": str(dataset_id),
            "dataset_name": dataset.name,
            "crs": dataset.crs,
            **derivatives
        }
    except Exception as e:
        logger.exception(f"Failed to generate terrain derivatives: {e}")
        raise HTTPException(status_code=500, detail=f"Terrain processing error: {str(e)}")


@router.get("/datasets/{dataset_id}/contours")
async def get_contours(
    dataset_id: uuid.UUID,
    interval: float = Query(2.0, ge=0.5, le=20.0, description="Contour interval in meters (e.g. 0.5, 1, 2, 5, 10)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate GeoJSON vector contour lines from dataset elevation surface.
    """
    res = await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active"))
    dataset = res.scalar_one_or_none()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found.")

    try:
        proc = LASProcessor(dataset.file_path, default_crs=dataset.crs or "EPSG:32616")
        points = proc.extract_points()

        center_lon = -84.19
        center_lat = 39.76
        if dataset.metadata_json and "center" in dataset.metadata_json:
            center_lon = dataset.metadata_json["center"].get("lon", center_lon)
            center_lat = dataset.metadata_json["center"].get("lat", center_lat)

        derivatives = terrain_engine.compute_all_derivatives(
            points=points,
            grid_resolution=1.0,
            origin_lon=center_lon,
            origin_lat=center_lat
        )

        return derivatives.get("contours", {"type": "FeatureCollection", "features": []})
    except Exception as e:
        logger.error(f"Error generating contours: {e}")
        raise HTTPException(status_code=500, detail=f"Contour generation error: {str(e)}")
