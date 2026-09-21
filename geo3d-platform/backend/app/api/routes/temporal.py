"""
Multi-Temporal Change Detection REST API (MVP 8)
Endpoints for comparative multi-survey elevation analysis and volumetric cut/fill estimation.
"""

import os
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
    comparison_dataset_id: Optional[uuid.UUID] = None
    grid_resolution: float = 2.0
    height_threshold: float = 0.3
    simulate_temporal_shift: bool = False


# In-memory cache for fast comparison results
_COMPARISON_CACHE = {}


def _extract_dataset_points(ds: Dataset, max_points: int = 75000) -> dict:
    """Extract point coordinates from LAS, LAZ, or PLY files."""
    import numpy as np
    ext = os.path.splitext(ds.file_path)[1].lower() if ds.file_path else ""

    if ext == ".ply" or ds.file_format == "ply":
        from app.processing.gl3d_proc.gl3d_mesh_generator import load_ply_points
        pts, _ = load_ply_points(ds.file_path) if ds.file_path and os.path.exists(ds.file_path) else (np.empty((0, 3)), np.empty((0, 3)))
        if len(pts) == 0:
            raise ValueError(f"No points found in PLY file: {ds.file_path}")
        if len(pts) > max_points:
            sub_idx = np.random.choice(len(pts), max_points, replace=False)
            pts = pts[sub_idx]
        meta = ds.metadata_json if isinstance(ds.metadata_json, dict) else {}
        anchor = meta.get("anchor", {"lon": 8.5417, "lat": 47.3769, "alt": 450.0})
        lons = anchor["lon"] + pts[:, 0] * 1e-5
        lats = anchor["lat"] + pts[:, 1] * 1e-5
        return {
            "x": pts[:, 0].astype(np.float64),
            "y": pts[:, 1].astype(np.float64),
            "z": pts[:, 2].astype(np.float64),
            "lon": lons.astype(np.float64),
            "lat": lats.astype(np.float64),
        }
    else:
        proc = LASProcessor(ds.file_path, default_crs=ds.crs or "EPSG:26913")
        return proc.extract_points(max_points=max_points)


@router.post("/compare")
async def trigger_temporal_comparison(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute multi-temporal difference (DoD) between two survey datasets.
    Supports real comparative surveys or simulated temporal shifts.
    Returns cut/fill volumetric metrics and 3D difference points.
    """
    # 1. Validate baseline dataset
    res1 = await db.execute(select(Dataset).where(Dataset.id == req.baseline_dataset_id))
    ds_base = res1.scalar_one_or_none()
    if not ds_base:
        raise HTTPException(status_code=404, detail="Baseline dataset not found.")

    comp_id = req.comparison_dataset_id or req.baseline_dataset_id
    simulate_shift = req.simulate_temporal_shift or (comp_id == req.baseline_dataset_id)

    # 2. Extract points from baseline
    try:
        base_raw = _extract_dataset_points(ds_base, max_points=75000)
    except Exception as e:
        logger.exception(f"Failed to load baseline points for comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract baseline point cloud: {str(e)}")

    # 3. Extract points from comparison or synthesize copy
    if comp_id == req.baseline_dataset_id:
        ds_comp = ds_base
        comp_name = f"{ds_base.name} (Simulated T2)"
        comp_raw = {k: (v.copy() if hasattr(v, 'copy') else v) for k, v in base_raw.items()}
    else:
        res2 = await db.execute(select(Dataset).where(Dataset.id == comp_id))
        ds_comp = res2.scalar_one_or_none()
        if not ds_comp:
            raise HTTPException(status_code=404, detail="Comparison dataset not found.")
        try:
            comp_raw = _extract_dataset_points(ds_comp, max_points=75000)
            comp_name = ds_comp.name
        except Exception as e:
            logger.exception(f"Failed to load comparison points: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to extract comparison point cloud: {str(e)}")

    # 4. Compute temporal change
    result = compute_temporal_change(
        baseline_pts=base_raw,
        comparison_pts=comp_raw,
        grid_resolution=req.grid_resolution,
        height_threshold=req.height_threshold,
        simulate_temporal_shift=simulate_shift,
    )

    comparison_id = str(uuid.uuid4())
    payload = {
        "comparison_id": comparison_id,
        "is_simulated": simulate_shift,
        "baseline_dataset": {
            "id": str(ds_base.id),
            "name": ds_base.name,
            "crs": ds_base.crs,
        },
        "comparison_dataset": {
            "id": str(ds_comp.id),
            "name": comp_name,
            "crs": ds_comp.crs,
        },
        **result,
    }

    _COMPARISON_CACHE[comparison_id] = payload
    return payload


@router.get("/demo")
async def get_demo_temporal_comparison(
    db: AsyncSession = Depends(get_db),
):
    """Generate an instant demo comparison using an available dataset or synthetic terrain."""
    import numpy as np

    # Find any active point cloud dataset
    res = await db.execute(
        select(Dataset).where(Dataset.dataset_type.in_(["point_cloud", "gl3d_scene"])).limit(1)
    )
    ds = res.scalar_one_or_none()

    if ds and ds.file_path and os.path.exists(ds.file_path):
        req = CompareRequest(
            baseline_dataset_id=ds.id,
            comparison_dataset_id=ds.id,
            grid_resolution=2.0,
            height_threshold=0.3,
            simulate_temporal_shift=True,
        )
        return await trigger_temporal_comparison(req, db)

    # Pure synthetic fallback if no dataset uploaded yet
    n_pts = 5000
    xs = np.random.uniform(500000, 500500, n_pts)
    ys = np.random.uniform(4000000, 4000500, n_pts)
    zs = 100.0 + np.sin(xs / 50.0) * 8.0 + np.cos(ys / 50.0) * 8.0
    lons = -84.1896 + (xs - 500000) * 1e-5
    lats = 39.7586 + (ys - 4000000) * 1e-5

    base_raw = {"x": xs, "y": ys, "z": zs, "lon": lons, "lat": lats}
    comp_raw = {"x": xs.copy(), "y": ys.copy(), "z": zs.copy(), "lon": lons.copy(), "lat": lats.copy()}

    result = compute_temporal_change(
        baseline_pts=base_raw,
        comparison_pts=comp_raw,
        grid_resolution=2.0,
        height_threshold=0.3,
        simulate_temporal_shift=True,
    )

    comparison_id = str(uuid.uuid4())
    payload = {
        "comparison_id": comparison_id,
        "is_simulated": True,
        "baseline_dataset": {
            "id": str(uuid.uuid4()),
            "name": "Survey Epoch 2024 (Baseline)",
            "crs": "EPSG:26913",
        },
        "comparison_dataset": {
            "id": str(uuid.uuid4()),
            "name": "Survey Epoch 2026 (Comparative)",
            "crs": "EPSG:26913",
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

