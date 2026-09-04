"""
Area of Interest (AOI) REST API Endpoints
Provides AOI validation, area estimation, point count calculation, and subset cropping.
"""

import uuid
import math
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.dataset import Dataset
from app.analysis.measurement import compute_area_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/aoi", tags=["Area of Interest"])

MAX_AOI_AREA_SQKM = 25.0  # 25 km² limit for development processing
WARNING_AOI_AREA_SQKM = 5.0  # 5 km² warning threshold


class AOIPoint(BaseModel):
    lon: float
    lat: float


class AOIEstimateRequest(BaseModel):
    dataset_id: Optional[uuid.UUID] = None
    bbox: Optional[List[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat]")
    polygon: Optional[List[AOIPoint]] = Field(None, description="Polygon vertices")


class AOICropRequest(BaseModel):
    dataset_id: uuid.UUID
    aoi_name: str = "AOI Subset"
    bbox: Optional[List[float]] = None
    polygon: Optional[List[AOIPoint]] = None


@router.post("/estimate")
async def estimate_aoi(
    req: AOIEstimateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate AOI, calculate surface area, and estimate point count & memory size
    prior to executing heavy processing pipelines.
    """
    pts = []
    if req.polygon and len(req.polygon) >= 3:
        pts = [{"lon": p.lon, "lat": p.lat, "alt": 0.0} for p in req.polygon]
    elif req.bbox and len(req.bbox) == 4:
        min_x, min_y, max_x, max_y = req.bbox
        pts = [
            {"lon": min_x, "lat": min_y, "alt": 0.0},
            {"lon": max_x, "lat": min_y, "alt": 0.0},
            {"lon": max_x, "lat": max_y, "alt": 0.0},
            {"lon": min_x, "lat": max_y, "alt": 0.0},
        ]
    else:
        raise HTTPException(status_code=400, detail="Must provide valid bounding box or polygon (3+ vertices).")

    metrics = compute_area_metrics(pts)
    area_sqkm = metrics["area_sq_km"]

    # Point density estimate
    point_density = 25.0  # default 25 pts/m²
    if req.dataset_id:
        ds_res = await db.execute(select(Dataset).where(Dataset.id == req.dataset_id))
        ds = ds_res.scalar_one_or_none()
        if ds and ds.point_density:
            point_density = ds.point_density

    estimated_points = int(metrics["area_sq_m"] * point_density)
    estimated_size_mb = round((estimated_points * 32) / (1024 * 1024), 2)  # ~32 bytes per point

    warning = None
    if area_sqkm > MAX_AOI_AREA_SQKM:
        warning = f"AOI area ({area_sqkm:.2f} km²) exceeds maximum configured limit of {MAX_AOI_AREA_SQKM} km²."
    elif area_sqkm > WARNING_AOI_AREA_SQKM:
        warning = f"Large AOI ({area_sqkm:.2f} km²). Processing may take several minutes."

    return {
        "valid": area_sqkm <= MAX_AOI_AREA_SQKM,
        "warning": warning,
        "area_metrics": metrics,
        "estimated_point_count": estimated_points,
        "estimated_processing_mb": estimated_size_mb,
        "assumed_density_pts_m2": point_density
    }
