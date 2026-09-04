import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.processing_job import ProcessingJob
from app.schemas.schemas import JobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get processing job status and details."""
    result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return JobResponse.model_validate(job)


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    project_id: uuid.UUID | None = None,
    dataset_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List processing jobs with optional filters."""
    query = select(ProcessingJob).order_by(desc(ProcessingJob.created_at)).limit(limit)

    if project_id:
        query = query.where(ProcessingJob.project_id == project_id)
    if dataset_id:
        query = query.where(ProcessingJob.dataset_id == dataset_id)
    if status:
        query = query.where(ProcessingJob.status == status.upper())

    result = await db.execute(query)
    jobs = result.scalars().all()
    return [JobResponse.model_validate(j) for j in jobs]
