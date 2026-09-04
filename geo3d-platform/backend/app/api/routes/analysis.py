"""
Spatial Analysis REST API Endpoints
Provides distance, area, elevation profile, slope/aspect, and volumetric estimation routes.
"""

import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.dataset import Dataset
from app.analysis.measurement import compute_distance_metrics, compute_area_metrics, compute_vertical_height
from app.analysis.elevation_profile import generate_elevation_profile
from app.analysis.slope_aspect import analyze_slope_and_aspect
from app.analysis.volume import estimate_volume

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["Spatial Analysis"])


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class CoordinatePoint(BaseModel):
    lon: float = Field(..., description="Longitude in decimal degrees (-180 to 180)")
    lat: float = Field(..., description="Latitude in decimal degrees (-90 to 90)")
    alt: float = Field(0.0, description="Altitude/Elevation in meters")


class DistanceRequest(BaseModel):
    points: List[CoordinatePoint] = Field(..., min_length=2, description="List of 2+ points")


class AreaRequest(BaseModel):
    points: List[CoordinatePoint] = Field(..., min_length=3, description="List of 3+ polygon vertices")


class HeightRequest(BaseModel):
    base_point: CoordinatePoint
    top_point: CoordinatePoint


class ProfileRequest(BaseModel):
    points: List[CoordinatePoint] = Field(..., min_length=2, description="Transect polyline points")
    dataset_id: Optional[uuid.UUID] = None
    num_samples: int = Field(100, ge=10, le=500)


class SlopeAspectRequest(BaseModel):
    points: List[CoordinatePoint] = Field(..., min_length=2)


class VolumeRequest(BaseModel):
    points: List[CoordinatePoint] = Field(..., min_length=3)
    base_elevation: Optional[float] = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/measure-distance")
async def measure_distance(req: DistanceRequest):
    """Measure 2D geodesic and 3D Euclidean distances with segment breakdowns."""
    pts = [p.model_dump() for p in req.points]
    return compute_distance_metrics(pts)


@router.post("/measure-area")
async def measure_area(req: AreaRequest):
    """Measure polygon surface area (m², hectares, acres, km²) and perimeter."""
    pts = [p.model_dump() for p in req.points]
    return compute_area_metrics(pts)


@router.post("/measure-height")
async def measure_height(req: HeightRequest):
    """Measure vertical height difference (Delta Z) and direct 3D distance."""
    return compute_vertical_height(req.base_point.model_dump(), req.top_point.model_dump())


@router.post("/elevation-profile")
async def get_elevation_profile(
    req: ProfileRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate elevation profile along a transect path.
    Optionally extracts elevation from an active LiDAR dataset.
    """
    pts = [p.model_dump() for p in req.points]
    ds_pts = None
    ds_crs = "EPSG:26913"

    if req.dataset_id:
        result = await db.execute(
            select(Dataset).where(Dataset.id == req.dataset_id, Dataset.status == "active")
        )
        dataset = result.scalar_one_or_none()
        if dataset and dataset.file_path and os.path.exists(dataset.file_path):
            try:
                from app.processing.pdal_proc.las_processor import LASProcessor
                proc = LASProcessor(dataset.file_path, default_crs=dataset.crs or "EPSG:26913")
                ds_pts = proc.extract_points()
                ds_crs = dataset.crs or "EPSG:26913"
            except Exception as e:
                logger.warning(f"Could not extract dataset points for profile: {e}")

    return generate_elevation_profile(
        path_points=pts,
        num_samples=req.num_samples,
        dataset_points=ds_pts,
        dataset_crs=ds_crs
    )


@router.post("/slope-aspect")
async def get_slope_aspect(req: SlopeAspectRequest):
    """Analyze slope angles, gradient percentages, and compass aspect direction."""
    pts = [p.model_dump() for p in req.points]
    return analyze_slope_and_aspect(pts)


@router.post("/volume")
async def get_volume_estimation(req: VolumeRequest):
    """Estimate cut, fill, and net volumetric quantities under a polygon boundary."""
    pts = [p.model_dump() for p in req.points]
    return estimate_volume(
        polygon_points=pts,
        base_elevation=req.base_elevation
    )
