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
            # Create a small placeholder file for mock mode
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
