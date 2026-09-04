"""
Multi-Temporal Change Detection REST API (MVP 8)
Endpoints for comparative multi-survey elevation analysis and volumetric cut/fill estimation.
"""

import uuid
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.dataset import Dataset
from app.models.processing_job import ProcessingJob
from app.processing.pdal_proc.las_processor import LASProcessor
from app.processing.temporal.change_detection import compute_temporal_change

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/temporal", tags=["Multi-Temporal Change Detection"])


class CompareRequest(BaseModel):
    baseline_dataset_id: uuid.UUID
    comparison_dataset_id: uuid.UUID
    grid_resolution: float = 2.0
    height_threshold: float = 0.3


# In-memory cache for fast comparison results
_COMPARISON_CACHE = {}


@router.post("/compare")
async def trigger_temporal_comparison(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute multi-temporal difference (DoD) between two survey datasets.
    Returns cut/fill volumetric metrics and 3D difference points.
    """
    # 1. Validate datasets
    res1 = await db.execute(select(Dataset).where(Dataset.id == req.baseline_dataset_id))
    ds_base = res1.scalar_one_or_none()
    if not ds_base:
        raise HTTPException(status_code=404, detail="Baseline dataset not found.")

    res2 = await db.execute(select(Dataset).where(Dataset.id == req.comparison_dataset_id))
    ds_comp = res2.scalar_one_or_none()
    if not ds_comp:
        raise HTTPException(status_code=404, detail="Comparison dataset not found.")

    # 2. Extract points from both
    try:
        proc_base = LASProcessor(ds_base.file_path, default_crs=ds_base.crs or "EPSG:26913")
        base_raw = proc_base.extract_points(max_points=75000)

        proc_comp = LASProcessor(ds_comp.file_path, default_crs=ds_comp.crs or "EPSG:26913")
        comp_raw = proc_comp.extract_points(max_points=75000)
    except Exception as e:
        logger.exception(f"Failed to load points for comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract point clouds: {str(e)}")

    # 3. Compute temporal change
    result = compute_temporal_change(
        baseline_pts=base_raw,
        comparison_pts=comp_raw,
        grid_resolution=req.grid_resolution,
        height_threshold=req.height_threshold,
    )

    comparison_id = str(uuid.uuid4())
    payload = {
        "comparison_id": comparison_id,
        "baseline_dataset": {
            "id": str(ds_base.id),
            "name": ds_base.name,
            "crs": ds_base.crs,
        },
        "comparison_dataset": {
            "id": str(ds_comp.id),
            "name": ds_comp.name,
            "crs": ds_comp.crs,
        },
        **result,
    }

    _COMPARISON_CACHE[comparison_id] = payload
    return payload


@router.get("/compare/{comparison_id}")
async def get_comparison_result(comparison_id: str):
    """Retrieve cached temporal comparison result by ID."""
    if comparison_id not in _COMPARISON_CACHE:
        raise HTTPException(status_code=404, detail="Comparison result not found or expired.")
    return _COMPARISON_CACHE[comparison_id]
