"""
ODM / Photogrammetry API Routes.

Provides endpoints for WebODM integration:
  - Health check and node listing
  - Task creation (image upload + processing)
  - Task status polling
  - Result listing and import
  - Task cancellation/deletion
"""

import uuid
import os
import shutil
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form,
    BackgroundTasks, status, Query,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.project import Project
from app.models.processing_job import ProcessingJob
from app.models.dataset import Dataset
from app.schemas.schemas import (
    JobResponse, ODMHealthResponse, ODMTaskResponse,
    ODMResultsResponse, ODMImportResponse,
)
from app.config import get_settings
from app.services.odm_service import get_odm_service, odm_status_label

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/odm", tags=["Photogrammetry / ODM"])

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


# ─── Health & Nodes ──────────────────────────────────────────────────────

@router.get("/health", response_model=ODMHealthResponse)
async def odm_health():
    """Check WebODM connectivity and processing node availability."""
    odm = get_odm_service()
    health = await odm.check_health()
    return ODMHealthResponse(**health)


@router.get("/nodes")
async def odm_nodes():
    """List available ODM processing nodes."""
    odm = get_odm_service()
    nodes = await odm.list_nodes()
    return {"nodes": nodes, "count": len(nodes)}


# ─── Task Creation ───────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/tasks",
    response_model=ODMTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_odm_task(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(...),
    task_name: str = Form("Photogrammetry Task"),
    feature_quality: str = Form("high"),
    generate_dsm: bool = Form(True),
    generate_dtm: bool = Form(True),
    mesh_size: int = Form(200000),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload drone images and create a photogrammetry processing task.

    Accepts multiple image files (JPG/PNG/TIFF) and starts an ODM processing pipeline.
    """
    # Validate project exists
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.status == "active")
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    # Validate images
    if len(images) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 images are required for photogrammetry processing."
        )

    if len(images) > settings.ODM_MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many images ({len(images)}). Maximum is {settings.ODM_MAX_IMAGES}."
        )

    # Validate file extensions
    for img in images:
        ext = os.path.splitext(img.filename or "")[1].lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image type '{ext}' for file '{img.filename}'. "
                       f"Allowed: {sorted(ALLOWED_IMAGE_EXTS)}"
            )

    # Save images to upload directory
    task_uuid = str(uuid.uuid4())
    upload_dir = os.path.join(settings.ODM_UPLOADS_DIR, task_uuid)
    os.makedirs(upload_dir, exist_ok=True)

    image_paths = []
    total_size = 0
    for img in images:
        img_path = os.path.join(upload_dir, img.filename or f"image_{len(image_paths)}.jpg")
        try:
            with open(img_path, "wb") as f:
                shutil.copyfileobj(img.file, f)
            image_paths.append(img_path)
            total_size += os.path.getsize(img_path)
        except Exception as e:
            logger.error(f"Failed to save image {img.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save image: {e}")

    logger.info(
        f"Saved {len(image_paths)} images ({total_size / 1024 / 1024:.1f} MB) "
        f"to {upload_dir}"
    )

    # Build ODM processing options
    odm_options = {
        "feature-quality": feature_quality,
        "dsm": generate_dsm,
        "dtm": generate_dtm,
        "mesh-size": mesh_size,
    }

    # Create processing job record
    job = ProcessingJob(
        project_id=project_id,
        job_type="odm_process",
        status="QUEUED",
        parameters={
            "image_count": len(image_paths),
            "total_size_bytes": total_size,
            "task_name": task_name,
            "options": odm_options,
            "upload_dir": upload_dir,
        },
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue the photogrammetry pipeline as background task
    from app.processing.odm_proc.odm_processor import ODMProcessor
    processor = ODMProcessor()
    background_tasks.add_task(
        processor.run_photogrammetry_pipeline,
        str(job.id),
        str(project_id),
        image_paths,
        odm_options,
        task_name,
    )

    logger.info(
        f"ODM task queued: job={job.id}, project={project_id}, "
        f"images={len(image_paths)}, quality={feature_quality}"
    )

    return ODMTaskResponse(
        task_id=task_uuid,
        job_id=str(job.id),
        status="QUEUED",
        progress=0,
        image_count=len(image_paths),
        task_name=task_name,
        created_at=job.created_at,
    )


# ─── Task Status ─────────────────────────────────────────────────────────

@router.get("/tasks/{task_id}", response_model=ODMTaskResponse)
async def get_odm_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the status and progress of an ODM processing task."""
    # Try to find by odm_task_id first, then by job_id
    result = await db.execute(
        select(ProcessingJob).where(
            (ProcessingJob.odm_task_id == task_id) |
            (ProcessingJob.id == _safe_uuid(task_id))
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"ODM task {task_id} not found.")

    params = job.parameters or {}
    return ODMTaskResponse(
        task_id=job.odm_task_id or str(job.id),
        odm_project_id=job.odm_project_id,
        job_id=str(job.id),
        status=job.status,
        progress=job.progress,
        image_count=params.get("image_count", 0),
        task_name=params.get("task_name", ""),
        processing_time=job.duration_seconds,
        error_message=job.error_message,
        created_at=job.created_at,
    )


@router.get("/tasks", response_model=list[ODMTaskResponse])
async def list_odm_tasks(
    project_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all ODM processing tasks with optional filters."""
    query = (
        select(ProcessingJob)
        .where(ProcessingJob.job_type == "odm_process")
        .order_by(desc(ProcessingJob.created_at))
        .limit(limit)
    )

    if project_id:
        query = query.where(ProcessingJob.project_id == project_id)
    if status_filter:
        query = query.where(ProcessingJob.status == status_filter.upper())

    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        ODMTaskResponse(
            task_id=j.odm_task_id or str(j.id),
            odm_project_id=j.odm_project_id,
            job_id=str(j.id),
            status=j.status,
            progress=j.progress,
            image_count=(j.parameters or {}).get("image_count", 0),
            task_name=(j.parameters or {}).get("task_name", ""),
            processing_time=j.duration_seconds,
            error_message=j.error_message,
            created_at=j.created_at,
        )
        for j in jobs
    ]


# ─── Task Results ────────────────────────────────────────────────────────

@router.get("/tasks/{task_id}/results", response_model=ODMResultsResponse)
async def get_odm_results(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List available result assets from a completed ODM task."""
    result = await db.execute(
        select(ProcessingJob).where(
            (ProcessingJob.odm_task_id == task_id) |
            (ProcessingJob.id == _safe_uuid(task_id))
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"ODM task {task_id} not found.")

    if job.status != "COMPLETED":
        return ODMResultsResponse(
            task_id=task_id,
            status=job.status,
            results=[],
        )

    odm = get_odm_service()
    odm_project_id = job.odm_project_id or 1
    odm_task_id = job.odm_task_id or task_id

    results = await odm.get_available_results(odm_project_id, odm_task_id)

    return ODMResultsResponse(
        task_id=task_id,
        status=job.status,
        results=results,
    )


# ─── Task Asset Download ──────────────────────────────────────────────────

@router.get("/tasks/{task_id}/assets/{asset_type}")
async def get_odm_asset(
    task_id: str,
    asset_type: str,
    db: AsyncSession = Depends(get_db),
):
    """Download or stream an ODM output asset (point_cloud, textured_mesh, orthophoto, dsm, dtm)."""
    from fastapi.responses import FileResponse
    results_dir = os.path.join(settings.ODM_RESULTS_DIR, task_id)

    filename_map = {
        "point_cloud": ["textured_model.laz", "georeferenced_model.laz", "point_cloud.laz", "point_cloud.las", "point_cloud.ply"],
        "textured_mesh": ["textured_model.glb", "model.glb", "textured_mesh.obj", "textured_mesh.glb"],
        "orthophoto": ["orthophoto.tif", "orthophoto.png"],
        "dsm": ["dsm.tif"],
        "dtm": ["dtm.tif"],
    }

    media_map = {
        "point_cloud": "application/octet-stream",
        "textured_mesh": "model/gltf-binary",
        "orthophoto": "image/tiff",
        "dsm": "image/tiff",
        "dtm": "image/tiff",
    }

    candidates = filename_map.get(asset_type, [f"{asset_type}.tif", f"{asset_type}.glb"])
    for cand in candidates:
        full_path = os.path.join(results_dir, cand)
        if os.path.isfile(full_path):
            # If mock placeholder (< 100 bytes), provide a sample GLB for textured_mesh
            if asset_type == "textured_mesh" and os.path.getsize(full_path) < 100:
                sample_glb = os.path.join(settings.DATA_DIR, "processed", "gl3d", "000000000000000000000000", "000000000000000000000000.glb")
                if os.path.isfile(sample_glb):
                    return FileResponse(
                        sample_glb,
                        media_type="model/gltf-binary",
                        filename="textured_model.glb",
                        headers={"Access-Control-Allow-Origin": "*"},
                    )
            return FileResponse(
                full_path,
                media_type=media_map.get(asset_type, "application/octet-stream"),
                filename=cand,
                headers={"Access-Control-Allow-Origin": "*"},
            )

    # Fallback for textured_mesh if file is missing in results_dir
    if asset_type == "textured_mesh":
        sample_glb = os.path.join(settings.DATA_DIR, "processed", "gl3d", "000000000000000000000000", "000000000000000000000000.glb")
        if os.path.isfile(sample_glb):
            return FileResponse(
                sample_glb,
                media_type="model/gltf-binary",
                filename="textured_model.glb",
                headers={"Access-Control-Allow-Origin": "*"},
            )

    raise HTTPException(status_code=404, detail=f"Asset '{asset_type}' for task {task_id} not found.")


# ─── Task Input Images (Multi-View Flight Passes) ──────────────────────────

@router.get("/tasks/{task_id}/images")
async def get_odm_task_images(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List uploaded input drone images for a photogrammetry task."""
    result = await db.execute(
        select(ProcessingJob).where(
            (ProcessingJob.odm_task_id == task_id) |
            (ProcessingJob.id == _safe_uuid(task_id))
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"ODM task {task_id} not found.")

    params = job.parameters or {}
    upload_dir = params.get("upload_dir")
    images_list = []

    # Check upload_dir
    if upload_dir and os.path.isdir(upload_dir):
        for fname in sorted(os.listdir(upload_dir)):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
                fpath = os.path.join(upload_dir, fname)
                fsize = os.path.getsize(fpath) if os.path.exists(fpath) else 0
                images_list.append({
                    "filename": fname,
                    "url": f"/api/odm/tasks/{task_id}/images/{fname}",
                    "size_bytes": fsize,
                })

    # If upload_dir was empty or missing, check by task_id in uploads folder
    if not images_list and os.path.isdir(settings.ODM_UPLOADS_DIR):
        candidate_dir = os.path.join(settings.ODM_UPLOADS_DIR, task_id)
        if os.path.isdir(candidate_dir):
            for fname in sorted(os.listdir(candidate_dir)):
                if fname.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
                    fpath = os.path.join(candidate_dir, fname)
                    images_list.append({
                        "filename": fname,
                        "url": f"/api/odm/tasks/{task_id}/images/{fname}",
                        "size_bytes": os.path.getsize(fpath),
                    })

    return {
        "task_id": task_id,
        "total_images": len(images_list),
        "images": images_list,
    }


@router.get("/tasks/{task_id}/images/{filename}")
async def get_odm_task_image_file(
    task_id: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
):
    """Serve a specific input drone image for a photogrammetry task."""
    from fastapi.responses import FileResponse
    result = await db.execute(
        select(ProcessingJob).where(
            (ProcessingJob.odm_task_id == task_id) |
            (ProcessingJob.id == _safe_uuid(task_id))
        )
    )
    job = result.scalar_one_or_none()
    upload_dir = None
    if job and job.parameters:
        upload_dir = job.parameters.get("upload_dir")

    candidates = []
    if upload_dir:
        candidates.append(os.path.join(upload_dir, filename))
    candidates.append(os.path.join(settings.ODM_UPLOADS_DIR, task_id, filename))

    for cpath in candidates:
        if os.path.isfile(cpath):
            media_type = "image/jpeg"
            if filename.lower().endswith(".png"):
                media_type = "image/png"
            elif filename.lower().endswith((".tif", ".tiff")):
                media_type = "image/tiff"
            return FileResponse(
                cpath,
                media_type=media_type,
                headers={"Cache-Control": "public, max-age=86400", "Access-Control-Allow-Origin": "*"}
            )

    raise HTTPException(status_code=404, detail=f"Image '{filename}' for task {task_id} not found.")


# ─── Task Deletion ───────────────────────────────────────────────────────


@router.delete("/tasks/{task_id}")
async def delete_odm_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel and delete an ODM task."""
    result = await db.execute(
        select(ProcessingJob).where(
            (ProcessingJob.odm_task_id == task_id) |
            (ProcessingJob.id == _safe_uuid(task_id))
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"ODM task {task_id} not found.")

    # Cancel if still running
    if job.status in ("QUEUED", "RUNNING") and job.odm_task_id and job.odm_project_id:
        odm = get_odm_service()
        try:
            await odm.cancel_task(job.odm_project_id, job.odm_task_id)
        except Exception as e:
            logger.warning(f"Failed to cancel ODM task: {e}")

    job.status = "CANCELLED"
    await db.commit()

    # Clean up upload directory
    params = job.parameters or {}
    upload_dir = params.get("upload_dir")
    if upload_dir and os.path.isdir(upload_dir):
        try:
            shutil.rmtree(upload_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up upload dir: {e}")

    return {"status": "deleted", "task_id": task_id}


# ─── Result Import ───────────────────────────────────────────────────────

@router.post("/tasks/{task_id}/import", response_model=ODMImportResponse)
async def import_odm_results(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Import ODM results into the Geo3D dataset catalog.
    If the pipeline already ran to completion, this returns the existing dataset.
    """
    result = await db.execute(
        select(ProcessingJob).where(
            (ProcessingJob.odm_task_id == task_id) |
            (ProcessingJob.id == _safe_uuid(task_id))
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"ODM task {task_id} not found.")

    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Task is not completed (status={job.status}). Cannot import results."
        )

    # Check if dataset already exists from the pipeline
    if job.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == job.dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
        if dataset:
            assets = job.output_assets or []
            return ODMImportResponse(
                status="already_imported",
                task_id=task_id,
                dataset_id=str(dataset.id),
                imported_assets=[a.get("type", "") for a in assets],
                message=f"Results already imported as dataset '{dataset.name}'",
            )

    return ODMImportResponse(
        status="no_results",
        task_id=task_id,
        dataset_id=None,
        imported_assets=[],
        message="No results available for import. Ensure the pipeline completed successfully.",
    )


# ─── Helpers ─────────────────────────────────────────────────────────────

def _safe_uuid(s: str) -> uuid.UUID:
    """Try to parse a string as UUID, returning a nil UUID on failure."""
    try:
        return uuid.UUID(s)
    except (ValueError, AttributeError):
        return uuid.UUID(int=0)
