"""
WebODM REST API Client Service.

Provides a full client for the WebODM/NodeODM photogrammetry engine:
  - Authentication (login / token caching)
  - Project CRUD
  - Task creation, image upload, processing
  - Progress polling
  - Result asset downloading (point cloud, orthophoto, DSM, DTM, mesh)
  - Health & node checks
  - Mock/demo mode when WEBODM_URL is not configured
"""

import os
import io
import uuid
import json
import time
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Mock Data ────────────────────────────────────────────────────────────────

MOCK_NODE = {
    "id": 1,
    "hostname": "nodeodm-mock",
    "port": 3000,
    "api_version": "2.1.0",
    "engine": "ODM",
    "engine_version": "3.3.0",
    "online": True,
    "queue_count": 0,
    "max_parallel_tasks": 2,
}

MOCK_PROCESSING_OPTIONS = [
    {"name": "feature-quality", "label": "Feature Quality", "type": "enum",
     "values": ["ultra", "high", "medium", "low", "lowest"], "default": "high"},
    {"name": "mesh-size", "label": "Mesh Size (faces)", "type": "int", "default": 200000},
    {"name": "orthophoto-resolution", "label": "Orthophoto Resolution (cm/px)", "type": "float", "default": 5.0},
    {"name": "dsm", "label": "Generate DSM", "type": "bool", "default": True},
    {"name": "dtm", "label": "Generate DTM", "type": "bool", "default": True},
    {"name": "pc-quality", "label": "Point Cloud Quality", "type": "enum",
     "values": ["ultra", "high", "medium", "low", "lowest"], "default": "medium"},
]


# ─── ODM Service ──────────────────────────────────────────────────────────────

class ODMService:
    """
    Asynchronous WebODM REST API client.
    Falls back to mock mode when WEBODM_URL is not configured.
    """

    def __init__(self):
        self.base_url = settings.WEBODM_URL.rstrip("/") if settings.WEBODM_URL else ""
        self.username = settings.WEBODM_USERNAME or "admin"
        self.password = settings.WEBODM_PASSWORD or "admin"
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    @property
    def is_mock(self) -> bool:
        return not bool(self.base_url)

    # ── Authentication ────────────────────────────────────────────────────

    async def _get_token(self) -> str:
        """Authenticate with WebODM and cache the token."""
        if self._token and time.time() < self._token_expiry:
            return self._token

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.base_url}/api/token-auth/",
                json={"username": self.username, "password": self.password},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["token"]
            self._token_expiry = time.time() + 3600  # cache for 1 hour
            return self._token

    async def _headers(self) -> Dict[str, str]:
        token = await self._get_token()
        return {"Authorization": f"JWT {token}"}

    # ── Health ────────────────────────────────────────────────────────────

    async def check_health(self) -> Dict[str, Any]:
        """Check WebODM connectivity and node availability."""
        if self.is_mock:
            return {
                "connected": False,
                "mock_mode": True,
                "message": "WebODM URL not configured. Running in mock/demo mode.",
                "nodes": [MOCK_NODE],
                "node_count": 1,
                "processing_options": MOCK_PROCESSING_OPTIONS,
            }

        try:
            headers = await self._headers()
            async with httpx.AsyncClient(timeout=10) as client:
                # Check processing nodes
                resp = await client.get(
                    f"{self.base_url}/api/processingnodes/",
                    headers=headers,
                )
                resp.raise_for_status()
                nodes = resp.json()

            return {
                "connected": True,
                "mock_mode": False,
                "message": f"Connected to WebODM at {self.base_url}",
                "nodes": nodes,
                "node_count": len(nodes),
                "processing_options": MOCK_PROCESSING_OPTIONS,
            }
        except Exception as e:
            logger.warning(f"WebODM health check failed: {e}")
            return {
                "connected": False,
                "mock_mode": False,
                "message": f"Cannot reach WebODM at {self.base_url}: {str(e)}",
                "nodes": [],
                "node_count": 0,
                "processing_options": MOCK_PROCESSING_OPTIONS,
            }

    # ── Node Management ───────────────────────────────────────────────────

    async def list_nodes(self) -> List[Dict[str, Any]]:
        """List available processing nodes."""
        if self.is_mock:
            return [MOCK_NODE]

        headers = await self._headers()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/api/processingnodes/",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Project CRUD ──────────────────────────────────────────────────────

    async def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new WebODM project."""
        if self.is_mock:
            return {
                "id": 1,
                "name": name,
                "description": description,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.base_url}/api/projects/",
                headers=headers,
                json={"name": name, "description": description},
            )
            resp.raise_for_status()
            return resp.json()

    async def list_projects(self) -> List[Dict[str, Any]]:
        """List all WebODM projects."""
        if self.is_mock:
            return []

        headers = await self._headers()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/api/projects/",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Task Management ───────────────────────────────────────────────────

    async def create_task(
        self,
        odm_project_id: int,
        image_paths: List[str],
        options: Optional[Dict[str, Any]] = None,
        task_name: str = "Photogrammetry Task",
    ) -> Dict[str, Any]:
        """
        Create an ODM task with uploaded images.

        Args:
            odm_project_id: WebODM project ID
            image_paths: List of local file paths to drone images
            options: ODM processing options (feature-quality, dsm, dtm, etc.)
            task_name: Human-readable task name

        Returns:
            Task info dict with 'id', 'status', etc.
        """
        if self.is_mock:
            mock_task_id = str(uuid.uuid4())
            return {
                "id": mock_task_id,
                "project": odm_project_id,
                "name": task_name,
                "status": {"code": 10},  # 10 = QUEUED
                "images_count": len(image_paths),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "options": options or {},
                "mock": True,
            }

        headers = await self._headers()

        # Build ODM options list
        odm_options = []
        if options:
            for key, val in options.items():
                odm_options.append({"name": key, "value": val})

        async with httpx.AsyncClient(timeout=300) as client:
            # Open all image files
            files = []
            for img_path in image_paths:
                fname = os.path.basename(img_path)
                files.append(("images", (fname, open(img_path, "rb"), "image/jpeg")))

            data = {
                "name": task_name,
                "options": json.dumps(odm_options),
            }

            try:
                resp = await client.post(
                    f"{self.base_url}/api/projects/{odm_project_id}/tasks/",
                    headers=headers,
                    data=data,
                    files=files,
                )
                resp.raise_for_status()
                return resp.json()
            finally:
                # Close all file handles
                for _, (_, fh, _) in files:
                    fh.close()

    async def get_task(self, odm_project_id: int, task_id: str) -> Dict[str, Any]:
        """Get task details and status."""
        if self.is_mock:
            return self._mock_task_status(task_id)

        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.base_url}/api/projects/{odm_project_id}/tasks/{task_id}/",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def cancel_task(self, odm_project_id: int, task_id: str) -> Dict[str, Any]:
        """Cancel a running task."""
        if self.is_mock:
            return {"success": True}

        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.base_url}/api/projects/{odm_project_id}/tasks/{task_id}/cancel/",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_task(self, odm_project_id: int, task_id: str) -> bool:
        """Delete a task."""
        if self.is_mock:
            return True

        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{self.base_url}/api/projects/{odm_project_id}/tasks/{task_id}/",
                headers=headers,
            )
            return resp.status_code in (200, 204)

    # ── Result Downloads ──────────────────────────────────────────────────

    async def get_available_results(
        self, odm_project_id: int, task_id: str
    ) -> List[Dict[str, Any]]:
        """
        List available result assets from a completed task.
        WebODM produces: orthophoto.tif, dsm.tif, dtm.tif, georeferenced_model.laz, textured_model.glb
        """
        if self.is_mock:
            return [
                {"type": "orthophoto", "name": "orthophoto.tif", "format": "geotiff",
                 "description": "Georeferenced orthophoto mosaic"},
                {"type": "dsm", "name": "dsm.tif", "format": "geotiff",
                 "description": "Digital Surface Model"},
                {"type": "dtm", "name": "dtm.tif", "format": "geotiff",
                 "description": "Digital Terrain Model"},
                {"type": "point_cloud", "name": "georeferenced_model.laz", "format": "laz",
                 "description": "Georeferenced dense point cloud"},
                {"type": "textured_mesh", "name": "textured_model.glb", "format": "glb",
                 "description": "Textured 3D mesh model"},
            ]

        task = await self.get_task(odm_project_id, task_id)
        available = task.get("available_assets", [])

        results = []
        asset_map = {
            "orthophoto.tif": ("orthophoto", "geotiff", "Georeferenced orthophoto mosaic"),
            "dsm.tif": ("dsm", "geotiff", "Digital Surface Model"),
            "dtm.tif": ("dtm", "geotiff", "Digital Terrain Model"),
            "georeferenced_model.laz": ("point_cloud", "laz", "Georeferenced dense point cloud"),
            "textured_model.glb": ("textured_mesh", "glb", "Textured 3D mesh model"),
        }

        for asset_name in available:
            if asset_name in asset_map:
                atype, afmt, adesc = asset_map[asset_name]
                results.append({
                    "type": atype,
                    "name": asset_name,
                    "format": afmt,
                    "description": adesc,
                })

        return results

    async def download_result(
        self,
        odm_project_id: int,
        task_id: str,
        asset_type: str,
        output_dir: str,
    ) -> Optional[str]:
        """
        Download a result asset from a completed task.

        Args:
            odm_project_id: WebODM project ID
            task_id: WebODM task UUID
            asset_type: One of 'orthophoto', 'dsm', 'dtm', 'point_cloud', 'textured_mesh'
            output_dir: Local directory to save the downloaded file

        Returns:
            Local file path of the downloaded asset, or None on failure.
        """
        os.makedirs(output_dir, exist_ok=True)

        asset_endpoints = {
            "orthophoto": ("download/orthophoto", "orthophoto.tif"),
            "dsm": ("download/dsm", "dsm.tif"),
            "dtm": ("download/dtm", "dtm.tif"),
            "point_cloud": ("download/georeferenced_model.laz", "georeferenced_model.laz"),
            "textured_mesh": ("download/textured_model.glb", "textured_model.glb"),
        }

        if asset_type not in asset_endpoints:
            logger.warning(f"Unknown asset type: {asset_type}")
            return None

        endpoint, filename = asset_endpoints[asset_type]
        output_path = os.path.join(output_dir, filename)

        if self.is_mock:
            if asset_type == "textured_mesh":
                sample_glb = os.path.join(settings.DATA_DIR, "processed", "gl3d", "000000000000000000000000", "000000000000000000000000.glb")
                if os.path.isfile(sample_glb):
                    shutil.copyfile(sample_glb, output_path)
                    return output_path
            # Create a small placeholder file for other mock results
            with open(output_path, "wb") as f:
                f.write(b"MOCK_ODM_RESULT")
            return output_path


        try:
            headers = await self._headers()
            url = f"{self.base_url}/api/projects/{odm_project_id}/tasks/{task_id}/{endpoint}"

            async with httpx.AsyncClient(timeout=600) as client:
                async with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    with open(output_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            f.write(chunk)

            logger.info(f"Downloaded {asset_type} → {output_path} ({os.path.getsize(output_path)} bytes)")
            return output_path

        except Exception as e:
            logger.error(f"Failed to download {asset_type} from task {task_id}: {e}")
            return None

    # ── Polling ───────────────────────────────────────────────────────────

    async def poll_task_until_complete(
        self,
        odm_project_id: int,
        task_id: str,
        poll_interval: float = 5.0,
        max_polls: int = 1440,  # ~2 hours at 5s intervals
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Poll a task until it completes, fails, or times out.

        Args:
            odm_project_id: WebODM project ID
            task_id: WebODM task UUID
            poll_interval: Seconds between polls
            max_polls: Maximum number of polls before timeout
            progress_callback: Optional async callable(progress_pct, status_code) for updates

        Returns:
            Final task status dict
        """
        for i in range(max_polls):
            task = await self.get_task(odm_project_id, task_id)
            status_code = task.get("status", {}).get("code", -1)

            # Status codes: 10=QUEUED, 20=RUNNING, 30=FAILED, 40=COMPLETED, 50=CANCELLED
            progress = task.get("running_progress", 0.0)

            if progress_callback:
                await progress_callback(progress, status_code)

            if status_code in (30, 40, 50):  # terminal states
                return task

            await asyncio.sleep(poll_interval)

        return {"status": {"code": 30}, "error": "Polling timed out"}

    # ── Mock Helpers ──────────────────────────────────────────────────────

    def _mock_task_status(self, task_id: str) -> Dict[str, Any]:
        """Generate a mock task status (simulates COMPLETED state)."""
        return {
            "id": task_id,
            "status": {"code": 40},  # 40 = COMPLETED
            "name": "Mock Photogrammetry Task",
            "images_count": 25,
            "running_progress": 1.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "processing_time": 120,
            "available_assets": [
                "orthophoto.tif",
                "dsm.tif",
                "dtm.tif",
                "georeferenced_model.laz",
                "textured_model.glb",
            ],
            "options": {},
            "mock": True,
        }


# ── Module-Level Singleton ────────────────────────────────────────────────────

_odm_service: Optional[ODMService] = None


def get_odm_service() -> ODMService:
    """Get or create the ODM service singleton."""
    global _odm_service
    if _odm_service is None:
        _odm_service = ODMService()
    return _odm_service


# ── Status Code Helpers ───────────────────────────────────────────────────────

ODM_STATUS_CODES = {
    10: "QUEUED",
    20: "RUNNING",
    30: "FAILED",
    40: "COMPLETED",
    50: "CANCELLED",
}


def odm_status_label(code: int) -> str:
    """Convert ODM numeric status code to human-readable label."""
    return ODM_STATUS_CODES.get(code, "UNKNOWN")


# ─── Aukerman Benchmark Preset ────────────────────────────────────────────────

AUKERMAN_CAMERAS = [
    {"filename": "DSC00229.JPG", "lon": -81.75046, "lat": 41.30381, "alt": 344.78, "focal": 0.741},
    {"filename": "DSC00230.JPG", "lon": -81.75049, "lat": 41.30419, "alt": 344.33, "focal": 0.741},
    {"filename": "DSC00232.JPG", "lon": -81.75125, "lat": 41.30480, "alt": 344.05, "focal": 0.741},
    {"filename": "DSC00233.JPG", "lon": -81.75145, "lat": 41.30485, "alt": 344.10, "focal": 0.741},
    {"filename": "DSC00238.JPG", "lon": -81.75299, "lat": 41.30340, "alt": 340.91, "focal": 0.741},
    {"filename": "DSC00239.JPG", "lon": -81.75231, "lat": 41.30342, "alt": 342.41, "focal": 0.741},
    {"filename": "DSC00240.JPG", "lon": -81.75174, "lat": 41.30348, "alt": 343.52, "focal": 0.741},
    {"filename": "DSC00241.JPG", "lon": -81.75119, "lat": 41.30350, "alt": 342.96, "focal": 0.741},
    {"filename": "DSC00242.JPG", "lon": -81.75079, "lat": 41.30396, "alt": 342.07, "focal": 0.741},
    {"filename": "DSC00244.JPG", "lon": -81.75160, "lat": 41.30458, "alt": 341.20, "focal": 0.741},
    {"filename": "DSC00249.JPG", "lon": -81.75187, "lat": 41.30362, "alt": 344.25, "focal": 0.741},
    {"filename": "DSC00256.JPG", "lon": -81.75155, "lat": 41.30385, "alt": 340.76, "focal": 0.741},
    {"filename": "DSC00257.JPG", "lon": -81.75103, "lat": 41.30395, "alt": 340.50, "focal": 0.741},
    {"filename": "DSC00258.JPG", "lon": -81.75128, "lat": 41.30424, "alt": 343.12, "focal": 0.741},
    {"filename": "DSC00275.JPG", "lon": -81.75323, "lat": 41.30477, "alt": 340.23, "focal": 0.741},
    {"filename": "DSC00276.JPG", "lon": -81.75372, "lat": 41.30472, "alt": 341.60, "focal": 0.741},
    {"filename": "DSC00279.JPG", "lon": -81.75316, "lat": 41.30342, "alt": 339.27, "focal": 0.741},
    {"filename": "DSC00281.JPG", "lon": -81.75212, "lat": 41.30343, "alt": 339.02, "focal": 0.741},
    {"filename": "DSC00282.JPG", "lon": -81.75161, "lat": 41.30347, "alt": 339.64, "focal": 0.741},
    {"filename": "DSC00283.JPG", "lon": -81.75111, "lat": 41.30350, "alt": 339.49, "focal": 0.741},
    {"filename": "DSC00284.JPG", "lon": -81.75077, "lat": 41.30401, "alt": 339.94, "focal": 0.741},
    {"filename": "DSC00301.JPG", "lon": -81.75098, "lat": 41.30393, "alt": 340.77, "focal": 0.741},
]


async def create_aukerman_benchmark_dataset(project_id: uuid.UUID, db) -> Any:
    """
    Import and register the complete DroneDB Aukerman Benchmark dataset.
    Sets up the dense point cloud, true RGB colors, drone camera flight paths,
    and photogrammetry metadata for immediate 3D visualization.
    """
    from app.models.dataset import Dataset
    from app.models.asset import Asset
    from sqlalchemy import select

    # Check if Aukerman dataset already exists for this project
    result = await db.execute(
        select(Dataset).where(
            Dataset.project_id == project_id,
            Dataset.name.like("%Aukerman%"),
            Dataset.status == "active",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    dataset_id = uuid.uuid4()
    dataset = Dataset(
        id=dataset_id,
        project_id=project_id,
        name="Aukerman Park — DroneDB Benchmark",
        description="OpenDroneMap (ODM) photogrammetric 3D point cloud & aerial survey of Aukerman Park (Cleveland, OH). 77 aerial camera stations, 2.81 cm/px GSD.",
        dataset_type="photogrammetry",
        file_format="ply",
        processing_status="ready",
        min_z=275.0,
        max_z=315.0,
        point_count=9481325,
        crs="EPSG:32617",
        metadata_json={
            "source": "dronedb_hub",
            "dronedb_url": "https://hub.dronedb.app/r/odm/aukerman/view/b2RtX2ZpbHRlcnBvaW50cy9wb2ludF9jbG91ZC5wbHk=/pointcloud",
            "anchor": {"lon": -81.7518, "lat": 41.3041, "alt": 285.0},
            "camera_count": 77,
            "reconstructed_shots": 73,
            "average_gsd_cm": 2.81,
            "camera_model": "SONY DSC-WX220",
            "dimensions": ["x", "y", "z", "nx", "ny", "nz", "red", "green", "blue", "views"],
            "available_assets": ["point_cloud", "orthophoto", "dsm", "dtm"],
            "cameras": AUKERMAN_CAMERAS,
        },
    )
    db.add(dataset)
    await db.commit()

    # Create Asset records
    assets_data = [
        {
            "type": "point_cloud",
            "name": "Filtered Dense Point Cloud (point_cloud.ply)",
            "format": "ply",
            "url": "https://hub.dronedb.app/r/odm/aukerman/view/b2RtX2ZpbHRlcnBvaW50cy9wb2ludF9jbG91ZC5wbHk=/pointcloud",
            "size": 265477392,
        },
        {
            "type": "orthophoto",
            "name": "High-Res Orthophoto Mosaic (2.81 cm/px)",
            "format": "geotiff",
            "url": "https://hub.dronedb.app/orgs/odm/ds/aukerman/download/odm_orthophoto/odm_orthophoto.tif",
            "size": 56562000,
        },
        {
            "type": "dsm",
            "name": "Digital Surface Model (DSM)",
            "format": "geotiff",
            "url": "https://hub.dronedb.app/orgs/odm/ds/aukerman/download/odm_georeferencing/dsm.tif",
            "size": 28400000,
        },
    ]

    for item in assets_data:
        asset = Asset(
            dataset_id=dataset_id,
            asset_type=item["type"],
            name=f"Aukerman — {item['name']}",
            description="DroneDB Aukerman open photogrammetry asset",
            file_size_bytes=item["size"],
            file_format=item["format"],
            url=item["url"],
            metadata_json={"source": "dronedb", "original_path": item["name"]},
        )
        db.add(asset)

    await db.commit()
    await db.refresh(dataset)
    return dataset
