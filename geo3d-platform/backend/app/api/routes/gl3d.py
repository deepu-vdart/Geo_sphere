"""
GL3D REST API Endpoints.
Browse, preview, and ingest GL3D photogrammetry scenes into Geo3D platform.
"""

import os
import uuid
import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.config import get_settings
from app.providers.gl3d import GL3DProvider

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/gl3d", tags=["GL3D Dataset"])

# Shared provider instance
_provider = GL3DProvider()


# ─── Response Models ─────────────────────────────────────────────────────────


class GL3DSceneSummary(BaseModel):
    scene_id: str
    name: str
    description: str
    category: str
    category_label: Optional[str] = "(a) Urban area"
    mesh_type: Optional[str] = "3D Triangular Surface Mesh"
    image_count: int
    is_downloaded: bool


class GL3DSceneDetail(BaseModel):
    scene_id: str
    name: str
    description: str
    category: str
    category_label: Optional[str] = "(a) Urban area"
    mesh_type: Optional[str] = "3D Triangular Surface Mesh"
    image_count: int
    camera_count: int
    is_downloaded: bool
    has_cameras: bool
    has_depths: bool
    has_images: bool
    cameras: Optional[list] = None
    metadata: Optional[dict] = None


class GL3DIngestRequest(BaseModel):
    project_name: Optional[str] = None
    max_points: int = 250000


class GL3DIngestResponse(BaseModel):
    status: str
    scene_id: str
    project_id: Optional[str] = None
    dataset_id: Optional[str] = None
    message: str


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/scenes", response_model=list[GL3DSceneSummary])
async def list_gl3d_scenes(
    q: str = Query("", description="Search query for scene name, ID, or category"),
):
    """List available GL3D photogrammetry scenes from the catalog."""
    from app.providers.gl3d import GL3D_SAMPLE_SCENES

    results = []
    query = q.lower().strip()

    for scene in GL3D_SAMPLE_SCENES:
        if query and not (
            query in scene["name"].lower()
            or query in scene["scene_id"].lower()
            or query in scene["category"].lower()
            or query in scene.get("category_label", "").lower()
            or query in scene["description"].lower()
        ):
            continue

        image_count = await _provider._get_image_count(scene["scene_id"])
        is_downloaded = os.path.isdir(_provider.get_scene_data_dir(scene["scene_id"]))

        results.append(GL3DSceneSummary(
            scene_id=scene["scene_id"],
            name=scene["name"],
            description=scene["description"],
            category=scene["category"],
            category_label=scene.get("category_label", "(a) Urban area"),
            mesh_type=scene.get("mesh_type", "3D Triangular Surface Mesh"),
            image_count=image_count,
            is_downloaded=is_downloaded,
        ))

    return results


@router.get("/scenes/{scene_id}", response_model=GL3DSceneDetail)
async def get_gl3d_scene(scene_id: str):
    """Get detailed metadata for a specific GL3D scene."""
    from app.providers.gl3d import GL3D_SAMPLE_SCENES
    from app.processing.gl3d_proc.gl3d_parser import get_scene_summary

    # Find in catalog
    scene_info = None
    for s in GL3D_SAMPLE_SCENES:
        if s["scene_id"] == scene_id:
            scene_info = s
            break

    if not scene_info:
        raise HTTPException(status_code=404, detail=f"Scene {scene_id} not found in catalog")

    image_count = await _provider._get_image_count(scene_id)
    scene_dir = _provider.get_scene_data_dir(scene_id)
    is_downloaded = os.path.isdir(scene_dir)

    detail = GL3DSceneDetail(
        scene_id=scene_id,
        name=scene_info["name"],
        description=scene_info["description"],
        category=scene_info["category"],
        category_label=scene_info.get("category_label", "(a) Urban area"),
        mesh_type=scene_info.get("mesh_type", "3D Triangular Surface Mesh"),
        image_count=image_count,
        camera_count=0,
        is_downloaded=is_downloaded,
        has_cameras=False,
        has_depths=False,
        has_images=False,
    )

    # If downloaded locally, get detailed info
    if is_downloaded:
        summary = get_scene_summary(scene_dir)
        detail.camera_count = summary.get("camera_count", 0)
        detail.has_cameras = summary.get("has_cameras", False)
        detail.has_depths = summary.get("has_depths", False)
        detail.has_images = summary.get("has_images", False)

        # Load camera positions for visualization
        if detail.has_cameras:
            from app.processing.gl3d_proc.gl3d_parser import parse_cameras
            cameras_path = os.path.join(scene_dir, "geolabel", "cameras.txt")
            cams = parse_cameras(cameras_path)
            detail.cameras = [
                {
                    "image_id": c.image_id,
                    "center": c.center.tolist(),
                    "forward": c.rotation[2, :].tolist(),
                    "up": (-c.rotation[1, :]).tolist(),
                    "fx": c.fx,
                    "fy": c.fy,
                }
                for c in cams[:200]  # Limit to 200 cameras for API response size
            ]

    return detail


@router.get("/scenes/{scene_id}/cameras")
async def get_gl3d_cameras(scene_id: str, limit: int = Query(100, ge=1, le=1000)):
    """Get parsed camera parameters for a GL3D scene as JSON."""
    scene_dir = _provider.get_scene_data_dir(scene_id)

    if not os.path.isdir(scene_dir):
        # Try downloading first
        await _provider.fetch_subset(scene_id, [], scene_dir)

    cameras_path = os.path.join(scene_dir, "geolabel", "cameras.txt")
    if not os.path.exists(cameras_path):
        raise HTTPException(status_code=404, detail=f"No cameras.txt for scene {scene_id}")

    from app.processing.gl3d_proc.gl3d_parser import parse_cameras, compute_scene_extent
    cams = parse_cameras(cameras_path)
    extent = compute_scene_extent(cams)

    return {
        "scene_id": scene_id,
        "total_cameras": len(cams),
        "returned": min(limit, len(cams)),
        "extent": extent,
        "cameras": [
            {
                "image_id": c.image_id,
                "center": c.center.tolist(),
                "forward": c.rotation[2, :].tolist(),
                "up": (-c.rotation[1, :]).tolist(),
                "fx": c.fx,
                "fy": c.fy,
                "px": c.px,
                "py": c.py,
            }
            for c in cams[:limit]
        ],
    }


@router.get("/scenes/{scene_id}/images")
async def get_gl3d_images(scene_id: str, limit: int = Query(20, ge=1, le=100)):
    """Get image list for a GL3D scene."""
    scene_dir = _provider.get_scene_data_dir(scene_id)

    # Try local first, then fetch from GitHub
    img_list_path = os.path.join(scene_dir, "image_list.txt")
    if not os.path.exists(img_list_path):
        await _provider.fetch_subset(scene_id, [], scene_dir)

    if not os.path.exists(img_list_path):
        raise HTTPException(status_code=404, detail=f"No image_list.txt for scene {scene_id}")

    from app.processing.gl3d_proc.gl3d_parser import parse_image_list
    images = parse_image_list(img_list_path)

    return {
        "scene_id": scene_id,
        "total_images": len(images),
        "returned": min(limit, len(images)),
        "images": images[:limit],
    }


@router.post("/scenes/{scene_id}/ingest", response_model=GL3DIngestResponse)
async def ingest_gl3d_scene(
    scene_id: str,
    request: GL3DIngestRequest,
    background_tasks: BackgroundTasks,
):
    """
    Download and ingest a GL3D scene into the Geo3D platform.
    Creates a project, downloads scene data, processes cameras into a point cloud,
    and generates OGC 3D Tiles for visualization.
    """
    from app.providers.gl3d import GL3D_SAMPLE_SCENES

    # Validate scene exists in catalog
    scene_info = None
    for s in GL3D_SAMPLE_SCENES:
        if s["scene_id"] == scene_id:
            scene_info = s
            break

    if not scene_info:
        raise HTTPException(status_code=404, detail=f"Scene {scene_id} not found")

    # Download scene data from GitHub
    logger.info(f"Downloading GL3D scene {scene_id}...")
    scene_dir = await _provider.fetch_subset(scene_id, [], "")

    # Schedule background processing
    project_name = request.project_name or f"GL3D: {scene_info['name']}"

    background_tasks.add_task(
        _process_gl3d_scene_background,
        scene_id=scene_id,
        scene_dir=scene_dir,
        project_name=project_name,
        scene_description=scene_info["description"],
        max_points=request.max_points,
    )

    return GL3DIngestResponse(
        status="processing",
        scene_id=scene_id,
        message=f"GL3D scene {scene_id} ingestion started. Processing in background.",
    )


async def _process_gl3d_scene_background(
    scene_id: str,
    scene_dir: str,
    project_name: str,
    scene_description: str,
    max_points: int,
):
    """Background task: process a GL3D scene and create platform project + dataset."""
    from app.database import AsyncSessionLocal
    from app.models.project import Project
    from app.models.dataset import Dataset
    from app.models.asset import Asset
    from app.processing.gl3d_proc.gl3d_processor import GL3DProcessor

    logger.info(f"[GL3D] Background processing scene {scene_id}")

    async with AsyncSessionLocal() as db:
        try:
            # Create project
            project = Project(
                name=project_name,
                description=f"GL3D photogrammetry scene: {scene_description}",
                location_name="GL3D Dataset (SfM local coordinates)",
                crs="LOCAL_SFM",
            )
            db.add(project)
            await db.flush()

            # Process scene
            processor = GL3DProcessor(scene_dir, max_total_points=max_points)
            output_dir = os.path.join(settings.PROCESSED_DIR, "gl3d", scene_id)
            metadata = processor.process(output_dir)

            # Assign real-world geographic anchor from scene catalog
            from app.providers.gl3d import GL3D_SAMPLE_SCENES
            anchor = {"lon": 8.5417, "lat": 47.3769, "alt": 450.0}
            for s in GL3D_SAMPLE_SCENES:
                if s["scene_id"] == scene_id and "anchor" in s:
                    anchor = s["anchor"]
                    break

            metadata["anchor"] = anchor
            metadata["center"] = {
                "lon": anchor["lon"],
                "lat": anchor["lat"],
                "alt": anchor["alt"],
            }

            # Create dataset record
            ply_path = metadata.get("ply_path", "")
            dataset = Dataset(
                project_id=project.id,
                name=f"GL3D Scene {scene_id[:8]}… ({metadata.get('camera_count', 0)} cameras)",
                description=scene_description,
                dataset_type="gl3d_scene",
                file_format="ply",
                file_path=ply_path,
                file_size_bytes=os.path.getsize(ply_path) if os.path.exists(ply_path) else 0,
                crs="LOCAL_SFM",
                min_z=metadata.get("extent", {}).get("min_z"),
                max_z=metadata.get("extent", {}).get("max_z"),
                point_count=metadata.get("point_count", 0),
                processing_status="ready",
                metadata_json=metadata,
            )
            db.add(dataset)
            await db.flush()

            # Create camera data asset
            camera_asset = Asset(
                dataset_id=dataset.id,
                asset_type="gl3d_cameras",
                name=f"GL3D Camera Array ({metadata.get('camera_count', 0)} cameras)",
                file_format="json",
                url=f"/api/gl3d/scenes/{scene_id}/cameras",
                metadata_json={
                    "camera_count": metadata.get("camera_count", 0),
                    "scene_id": scene_id,
                },
            )
            db.add(camera_asset)

            await db.commit()
            logger.info(f"[GL3D] Scene {scene_id} ingested — project={project.id}, dataset={dataset.id}")

        except Exception as e:
            logger.exception(f"[GL3D] Failed to process scene {scene_id}: {e}")
            await db.rollback()
