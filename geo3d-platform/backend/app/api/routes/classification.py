"""
Classification REST API — DALES-2 Point Cloud Classification
"""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.dataset import Dataset
from app.models.processing_job import ProcessingJob

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/classification", tags=["AI Classification"])


@router.post("/datasets/{dataset_id}/classify", status_code=202)
async def trigger_classification(
    dataset_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger DALES-2 semantic classification for a point cloud dataset.
    Classification runs as a background job.
    """
    res = await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active"))
    dataset = res.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.dataset_type != "point_cloud":
        raise HTTPException(status_code=400, detail="Classification only supported for point cloud datasets.")
    if not dataset.file_path:
        raise HTTPException(status_code=400, detail="Dataset has no associated file.")

    job = ProcessingJob(
        project_id=dataset.project_id,
        dataset_id=dataset_id,
        job_type="classify_dales2",
        status="QUEUED",
        parameters={"file_path": dataset.file_path, "crs": dataset.crs or "EPSG:26913"},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_run_classification, str(job.id), dataset.file_path, dataset.crs or "EPSG:26913")

    return {"job_id": str(job.id), "status": "QUEUED", "message": "DALES-2 classification job queued."}


@router.get("/datasets/{dataset_id}/classifications")
async def get_classifications(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the latest classification result for a dataset.
    Returns DALES-2 class distribution with confidence.
    """
    res = await db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active"))
    dataset = res.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    meta = dataset.metadata_json or {}
    classification_result = meta.get("dales2_classification")

    if not classification_result:
        # Check if a job is running
        job_res = await db.execute(
            select(ProcessingJob)
            .where(ProcessingJob.dataset_id == dataset_id, ProcessingJob.job_type == "classify_dales2")
            .order_by(ProcessingJob.created_at.desc())
        )
        job = job_res.scalar_one_or_none()
        if job:
            return {
                "dataset_id": str(dataset_id),
                "status": job.status,
                "classification_ready": False,
                "message": f"Classification job {job.status.lower()}.",
            }
        return {
            "dataset_id": str(dataset_id),
            "status": "not_started",
            "classification_ready": False,
            "message": "No classification has been run for this dataset.",
        }

    return {
        "dataset_id": str(dataset_id),
        "status": "completed",
        "classification_ready": True,
        **classification_result,
    }


async def _run_classification(job_id: str, file_path: str, crs: str) -> None:
    """Background task: run DALES-2 classification and store results."""
    import os
    from datetime import datetime, timezone
    from app.database import AsyncSessionLocal
    from app.models.processing_job import ProcessingJob
    from app.models.dataset import Dataset
    from app.processing.pdal_proc.las_processor import LASProcessor
    from app.processing.ai.classifier import classify_point_cloud

    logger.info(f"[ClassifyJob {job_id}] Starting DALES-2 classification for {file_path}")

    async with AsyncSessionLocal() as db:
        try:
            job_res = await db.execute(select(ProcessingJob).where(ProcessingJob.id == uuid.UUID(job_id)))
            job = job_res.scalar_one_or_none()
            if not job:
                return

            job.status = "RUNNING"
            job.started_at = datetime.now(timezone.utc)
            job.progress = 20
            await db.commit()

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            proc = LASProcessor(file_path, default_crs=crs)
            raw = proc.extract_points(max_points=100000)

            job.progress = 60
            await db.commit()

            result = classify_point_cloud(
                x=raw["x"], y=raw["y"], z=raw["z"],
                intensity=raw["intensity"],
                existing_classes=raw["classification"],
            )

            job.progress = 85
            await db.commit()

            # Store result into dataset metadata
            from sqlalchemy.orm.attributes import flag_modified
            ds_res = await db.execute(select(Dataset).where(Dataset.id == job.dataset_id))
            dataset = ds_res.scalar_one_or_none()
            if dataset:
                meta = dict(dataset.metadata_json) if dataset.metadata_json else {}
                meta["dales2_classification"] = result
                dataset.metadata_json = meta
                flag_modified(dataset, "metadata_json")
                await db.commit()
                await db.refresh(dataset)

            completed_at = datetime.now(timezone.utc)
            job.status = "COMPLETED"
            job.progress = 100
            job.completed_at = completed_at
            job.duration_seconds = (completed_at - job.started_at).total_seconds()
            job.log_output = f"Classified {result['total_points']:,} points into {result['class_count']} DALES-2 classes."
            await db.commit()

            logger.info(f"[ClassifyJob {job_id}] Done: dominant_class={result['dominant_class']}")

        except Exception as e:
            logger.exception(f"[ClassifyJob {job_id}] Failed: {e}")
            try:
                job.status = "FAILED"
                job.error_message = str(e)
                await db.commit()
            except Exception:
                pass
