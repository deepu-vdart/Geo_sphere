"""
AI Geospatial Analysis REST API Endpoints
Serves structured AI-ready terrain analysis and automated site suitability reports.
"""

import uuid
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.dataset import Dataset
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Geospatial Analysis"])


@router.get("/datasets/{dataset_id}/summary")
async def get_ai_terrain_summary(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an AI-ready structured terrain analysis summary for a dataset.
    """
    res = await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active"))
    dataset = res.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    meta = dataset.metadata_json or {}
    meta["name"] = dataset.name
    meta["crs"] = dataset.crs
    meta["min_z"] = dataset.min_z
    meta["max_z"] = dataset.max_z
    meta["point_count"] = dataset.point_count
    meta["point_density"] = dataset.point_density

    summary = ai_service.generate_terrain_summary(dataset_metadata=meta)
    return {
        "dataset_id": str(dataset_id),
        **summary
    }


class ChatQueryRequest(BaseModel):
    dataset_id: uuid.UUID
    query: str


@router.post("/chat")
async def chat_with_geospatial_assistant(
    req: ChatQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Conversational AI Geospatial Assistant (MVP 7).
    Parses user query, inspects dataset metrics, and returns grounded answer
    plus actionable CesiumJS viewer commands.
    """
    res = await db.execute(select(Dataset).where(Dataset.id == req.dataset_id, Dataset.status == "active"))
    dataset = res.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    meta = dataset.metadata_json or {}
    meta["name"] = dataset.name
    meta["crs"] = dataset.crs
    meta["min_z"] = dataset.min_z
    meta["max_z"] = dataset.max_z
    meta["point_count"] = dataset.point_count
    meta["point_density"] = dataset.point_density

    # Extract small point sample for spatial queries like fly_to_peak if available
    points_sample = None
    if dataset.file_path:
        try:
            from app.processing.pdal_proc.las_processor import LASProcessor
            proc = LASProcessor(dataset.file_path, default_crs=dataset.crs or "EPSG:26913")
            points_sample = proc.get_sample_points(sample_size=1000)
        except Exception:
            pass

    response = ai_service.process_chat_query(
        query=req.query,
        dataset_metadata=meta,
        sample_points=points_sample
    )

    return {
        "dataset_id": str(req.dataset_id),
        **response
    }

