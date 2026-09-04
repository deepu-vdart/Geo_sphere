import uuid
import os
import shutil
import logging
import numpy as np
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.processing_job import ProcessingJob
from app.schemas.schemas import DatasetResponse, DatasetListResponse, JobResponse
from app.config import get_settings
from app.services import dataset_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Datasets"])

ALLOWED_EXTENSIONS = {
    ".las", ".laz", ".ply",          # point cloud
    ".tif", ".tiff", ".geotiff",     # raster
    ".dem", ".dtm", ".dsm",          # elevation
    ".geojson", ".json",             # vector
    ".shp", ".zip",                  # shapefile (zipped)
    ".jpg", ".jpeg", ".png",         # imagery
    ".obj", ".glb", ".gltf",         # mesh
}


@router.get("/projects/{project_id}/datasets", response_model=DatasetListResponse)
async def list_datasets(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all datasets for a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.status == "active")
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    result = await db.execute(
        select(Dataset)
        .where(Dataset.project_id == project_id, Dataset.status == "active")
        .order_by(Dataset.created_at.desc())
    )
    datasets = result.scalars().all()
    return DatasetListResponse(
        total=len(datasets),
        datasets=[DatasetResponse.model_validate(d) for d in datasets]
    )


@router.post("/projects/{project_id}/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Upload a dataset file and queue validation/ingestion."""
    # Check project exists
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.status == "active")
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # Determine dataset type
    dataset_type = dataset_service.infer_dataset_type(ext)

    # Save file to raw data directory
    dataset_id = uuid.uuid4()
    raw_dir = os.path.join(settings.RAW_DIR, str(project_id), str(dataset_id))
    os.makedirs(raw_dir, exist_ok=True)
    file_path = os.path.join(raw_dir, file.filename or f"upload{ext}")

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    file_size = os.path.getsize(file_path)

    # Create dataset record — inherit CRS from project if available
    dataset = Dataset(
        id=dataset_id,
        project_id=project_id,
        name=name,
        description=description or None,
        dataset_type=dataset_type,
        file_format=ext.lstrip("."),
        file_path=file_path,
        file_size_bytes=file_size,
        original_filename=file.filename,
        processing_status="pending",
        crs=project.crs if project.crs else None,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    # Create a validation job
    job = ProcessingJob(
        project_id=project_id,
        dataset_id=dataset_id,
        job_type="validate",
        status="QUEUED",
        parameters={"file_path": file_path, "dataset_type": dataset_type},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue background validation
    background_tasks.add_task(
        dataset_service.run_validation_job,
        str(job.id), file_path, dataset_type
    )

    logger.info(f"Dataset {dataset_id} uploaded for project {project_id}, job {job.id} queued.")
    return DatasetResponse.model_validate(dataset)


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single dataset by ID."""
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active")
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    return DatasetResponse.model_validate(dataset)


@router.post("/datasets/{dataset_id}/process", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_processing(
    dataset_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger processing pipeline for a validated dataset."""
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active")
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")

    if dataset.processing_status not in ("validated", "pending", "ready"):
        raise HTTPException(
            status_code=400,
            detail=f"Dataset processing_status is '{dataset.processing_status}'. Must be 'validated', 'pending', or 'ready'."
        )

    job = ProcessingJob(
        project_id=dataset.project_id,
        dataset_id=dataset_id,
        job_type=f"process_{dataset.dataset_type}",
        status="QUEUED",
        parameters={"file_path": dataset.file_path, "dataset_type": dataset.dataset_type},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(
        dataset_service.run_processing_job,
        str(job.id), dataset.file_path, dataset.dataset_type
    )

    return JobResponse.model_validate(job)


@router.get("/datasets/{dataset_id}/tileset.json")
@router.head("/datasets/{dataset_id}/tileset.json")
async def get_tileset_json(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Serve OGC 3D Tiles tileset.json specification for point clouds."""
    from fastapi.responses import FileResponse

    tiles_dir = os.path.join(settings.TILES_DIR, str(dataset_id))
    tileset_path = os.path.join(tiles_dir, "tileset.json")

    if not os.path.exists(tileset_path):
        # Check if dataset exists and try on-the-fly generation if validated
        result = await db.execute(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active")
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")

        if dataset.file_path and os.path.exists(dataset.file_path) and dataset.dataset_type == "point_cloud":
            try:
                from app.processing.pdal_proc.las_processor import LASProcessor
                from app.processing.tiling.tile_generator import HierarchicalTileGenerator
                proc = LASProcessor(dataset.file_path, default_crs=dataset.crs or "EPSG:26913")
                gen = HierarchicalTileGenerator(proc)
                gen.generate(tiles_dir, max_tile_points=8000, max_total_points=250000)
            except Exception as e:
                logger.error(f"Failed to generate tileset on-the-fly: {e}")
                raise HTTPException(status_code=404, detail="3D Tileset not generated yet.")
        else:
            raise HTTPException(status_code=404, detail="3D Tileset not found for this dataset.")


    return FileResponse(tileset_path, media_type="application/json")


@router.get("/datasets/{dataset_id}/tile.pnts")
@router.head("/datasets/{dataset_id}/tile.pnts")
@router.get("/datasets/{dataset_id}/tiles/{filename}")
@router.head("/datasets/{dataset_id}/tiles/{filename}")
async def get_tile_file(
    dataset_id: uuid.UUID,
    filename: str = "tile.pnts",
):
    """Serve binary .pnts tile content for 3D Tiles streaming (flat and nested filenames)."""
    from fastapi.responses import FileResponse

    tiles_dir = os.path.join(settings.TILES_DIR, str(dataset_id))

    # Support both flat tile.pnts and hierarchical tiles/ subdirectory
    candidate_paths = [
        os.path.join(tiles_dir, "tiles", filename),
        os.path.join(tiles_dir, filename),
    ]
    tile_path = next((p for p in candidate_paths if os.path.exists(p)), None)

    if not tile_path:
        raise HTTPException(status_code=404, detail=f"Tile file '{filename}' not found.")

    return FileResponse(tile_path, media_type="application/octet-stream",
                        headers={"Access-Control-Allow-Origin": "*"})


@router.get("/datasets/{dataset_id}/model.glb")
@router.head("/datasets/{dataset_id}/model.glb")
async def get_dataset_glb_model(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Serve binary glTF 2.0 (.glb) solid 3D polygonal surface mesh."""
    from fastapi.responses import FileResponse

    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active")
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    meta = dataset.metadata_json if isinstance(dataset.metadata_json, dict) else {}
    glb_path = meta.get("glb_path")

    # Check if glb_path exists
    if glb_path and os.path.exists(glb_path):
        return FileResponse(
            glb_path,
            media_type="model/gltf-binary",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # Generate on the fly for GL3D datasets
    if dataset.dataset_type == "gl3d_scene" or dataset.file_format == "ply":
        from app.processing.gl3d_proc.gl3d_mesh_generator import (
            build_mesh_from_point_cloud, load_ply_points, generate_scene_mesh,
        )
        scene_id = meta.get("scene_id", str(dataset_id))
        category = meta.get("category", "urban")

        out_dir = os.path.join(settings.PROCESSED_DIR, "gl3d", scene_id)
        os.makedirs(out_dir, exist_ok=True)
        gen_glb_path = os.path.join(out_dir, f"{scene_id}.glb")

        # Try loading the real point cloud PLY first
        ply_path = meta.get("ply_path", "")
        points, colors = load_ply_points(ply_path) if ply_path else (np.empty((0,3)), np.empty((0,3)))

        if len(points) > 0:
            # Subsample for mesh to keep GLB manageable
            max_mesh_pts = 30000
            if len(points) > max_mesh_pts:
                rng = np.random.default_rng(seed=99)
                idx = rng.choice(len(points), size=max_mesh_pts, replace=False)
                points, colors = points[idx], colors[idx]
            mesh = build_mesh_from_point_cloud(points, colors, name=f"GL3D_{scene_id}")
        else:
            # Fallback to procedural if no PLY available
            mesh = generate_scene_mesh(category=category, scene_id=scene_id)

        mesh.write_glb(gen_glb_path)

        # Update metadata
        meta["glb_path"] = gen_glb_path
        dataset.metadata_json = meta
        await db.commit()

        return FileResponse(
            gen_glb_path,
            media_type="model/gltf-binary",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    raise HTTPException(status_code=404, detail="3D surface mesh model not available for this dataset.")


@router.get("/datasets/{dataset_id}/mesh.obj")
async def get_dataset_obj_mesh(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Serve Wavefront OBJ 3D mesh."""
    from fastapi.responses import FileResponse

    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active")
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    meta = dataset.metadata_json if isinstance(dataset.metadata_json, dict) else {}
    obj_path = meta.get("obj_path")

    if obj_path and os.path.exists(obj_path):
        return FileResponse(
            obj_path,
            media_type="text/plain",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    raise HTTPException(status_code=404, detail="OBJ mesh not found for this dataset.")





@router.get("/datasets/{dataset_id}/points-sample")
async def get_points_sample(
    dataset_id: uuid.UUID,
    sample_size: int = 15000,
    db: AsyncSession = Depends(get_db),
):
    """Get sampled point cloud coordinates and attributes for rapid web rendering."""
    result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "active")
    )
    dataset = result.scalar_one_or_none()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found.")

    if dataset.dataset_type == "gl3d_scene" or dataset.file_format == "ply":
        from app.processing.gl3d_proc.gl3d_parser import read_ply_sample
        anchor = None
        if dataset.metadata_json and isinstance(dataset.metadata_json, dict):
            anchor = dataset.metadata_json.get("anchor")

        samples = read_ply_sample(dataset.file_path, sample_size=sample_size, anchor=anchor)
        return {
            "dataset_id": str(dataset_id),
            "point_count": dataset.point_count or len(samples),
            "sample_count": len(samples),
            "crs": dataset.crs or "LOCAL_SFM",
            "min_z": dataset.min_z,
            "max_z": dataset.max_z,
            "points": samples
        }

    if dataset.dataset_type != "point_cloud":
        raise HTTPException(status_code=400, detail="Points sample only available for point cloud or GL3D scene datasets.")

    try:
        from app.processing.pdal_proc.las_processor import LASProcessor
        proc = LASProcessor(dataset.file_path, default_crs=dataset.crs or "EPSG:26913")
        samples = proc.get_sample_points(sample_size=sample_size)
        return {
            "dataset_id": str(dataset_id),
            "point_count": dataset.point_count,
            "sample_count": len(samples),
            "crs": dataset.crs,
            "min_z": dataset.min_z,
            "max_z": dataset.max_z,
            "points": samples
        }
    except Exception as e:
        logger.error(f"Error sampling point cloud: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sample points: {e}")

