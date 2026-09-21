"""
Tests for ODM / Photogrammetry Integration (MVP 4).

Tests the ODM service, API routes, and processing pipeline in mock mode.
"""

import pytest
import uuid
import os
from unittest.mock import AsyncMock, patch, MagicMock

# ─── ODM Service Tests ───────────────────────────────────────────────────────


class TestODMService:
    """Test the WebODM REST API client in mock mode."""

    def test_service_singleton(self):
        """ODM service should be lazily instantiated as a singleton."""
        from app.services.odm_service import get_odm_service

        svc1 = get_odm_service()
        svc2 = get_odm_service()
        assert svc1 is svc2

    def test_service_is_mock_when_no_url(self):
        """Service should be in mock mode when WEBODM_URL is empty."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = ""
        assert svc.is_mock is True

    def test_service_not_mock_when_url_set(self):
        """Service should not be in mock mode when WEBODM_URL is set."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = "http://webodm:8000"
        assert svc.is_mock is False

    @pytest.mark.asyncio
    async def test_mock_health_check(self):
        """Mock health check should return expected structure."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = ""  # force mock mode
        health = await svc.check_health()

        assert health["connected"] is False
        assert health["mock_mode"] is True
        assert health["node_count"] == 1
        assert len(health["nodes"]) == 1
        assert health["nodes"][0]["hostname"] == "nodeodm-mock"
        assert isinstance(health["processing_options"], list)

    @pytest.mark.asyncio
    async def test_mock_create_project(self):
        """Mock project creation should return valid structure."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = ""
        result = await svc.create_project("Test Survey", "Description")

        assert result["id"] == 1
        assert result["name"] == "Test Survey"

    @pytest.mark.asyncio
    async def test_mock_create_task(self):
        """Mock task creation should return task with images_count."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = ""
        result = await svc.create_task(
            odm_project_id=1,
            image_paths=["/fake/image1.jpg", "/fake/image2.jpg", "/fake/image3.jpg"],
            options={"feature-quality": "high"},
            task_name="Test Task",
        )

        assert "id" in result
        assert result["images_count"] == 3
        assert result["name"] == "Test Task"
        assert result["mock"] is True

    @pytest.mark.asyncio
    async def test_mock_task_status(self):
        """Mock task status should return COMPLETED."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = ""
        result = await svc.get_task(1, "fake-task-id")

        assert result["status"]["code"] == 40  # COMPLETED
        assert "available_assets" in result
        assert "orthophoto.tif" in result["available_assets"]

    @pytest.mark.asyncio
    async def test_mock_available_results(self):
        """Mock results should list standard ODM outputs."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = ""
        results = await svc.get_available_results(1, "fake-task-id")

        assert len(results) == 5
        result_types = {r["type"] for r in results}
        assert "orthophoto" in result_types
        assert "dsm" in result_types
        assert "dtm" in result_types
        assert "point_cloud" in result_types
        assert "textured_mesh" in result_types

    @pytest.mark.asyncio
    async def test_mock_download_result(self, tmp_path):
        """Mock download should create a placeholder file."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = ""
        output_dir = str(tmp_path / "results")
        path = await svc.download_result(1, "fake-task", "orthophoto", output_dir)

        assert path is not None
        assert os.path.exists(path)
        assert path.endswith("orthophoto.tif")

    @pytest.mark.asyncio
    async def test_mock_list_nodes(self):
        """Mock nodes should return 1 node."""
        from app.services.odm_service import ODMService

        svc = ODMService()
        svc.base_url = ""
        nodes = await svc.list_nodes()

        assert len(nodes) == 1
        assert nodes[0]["online"] is True

    def test_odm_status_labels(self):
        """Status code labels should map correctly."""
        from app.services.odm_service import odm_status_label

        assert odm_status_label(10) == "QUEUED"
        assert odm_status_label(20) == "RUNNING"
        assert odm_status_label(30) == "FAILED"
        assert odm_status_label(40) == "COMPLETED"
        assert odm_status_label(50) == "CANCELLED"
        assert odm_status_label(99) == "UNKNOWN"


# ─── Schema Tests ─────────────────────────────────────────────────────────


class TestODMSchemas:
    """Test ODM Pydantic schemas."""

    def test_odm_health_response_schema(self):
        """ODMHealthResponse should accept valid data."""
        from app.schemas.schemas import ODMHealthResponse

        resp = ODMHealthResponse(
            connected=False,
            mock_mode=True,
            message="Demo mode",
            node_count=1,
        )
        assert resp.connected is False
        assert resp.node_count == 1

    def test_odm_task_response_schema(self):
        """ODMTaskResponse should accept valid data."""
        from app.schemas.schemas import ODMTaskResponse

        resp = ODMTaskResponse(
            task_id="abc-123",
            status="QUEUED",
            progress=0,
            image_count=25,
            task_name="Test",
        )
        assert resp.task_id == "abc-123"
        assert resp.status == "QUEUED"

    def test_odm_results_response_schema(self):
        """ODMResultsResponse should accept valid data."""
        from app.schemas.schemas import ODMResultsResponse

        resp = ODMResultsResponse(
            task_id="abc-123",
            status="COMPLETED",
            results=[
                {"type": "orthophoto", "name": "orthophoto.tif", "format": "geotiff", "description": "test"},
            ],
        )
        assert len(resp.results) == 1

    def test_odm_import_response_schema(self):
        """ODMImportResponse should accept valid data."""
        from app.schemas.schemas import ODMImportResponse

        resp = ODMImportResponse(
            status="already_imported",
            task_id="abc-123",
            dataset_id="def-456",
            imported_assets=["orthophoto", "dsm"],
            message="Already imported",
        )
        assert len(resp.imported_assets) == 2


# ─── Model Tests ──────────────────────────────────────────────────────────


class TestProcessingJobODMFields:
    """Test ODM-specific fields on ProcessingJob model."""

    def test_processing_job_has_odm_fields(self):
        """ProcessingJob should have odm_task_id and odm_project_id."""
        from app.models import ProcessingJob

        job = ProcessingJob(
            project_id=uuid.uuid4(),
            job_type="odm_process",
            odm_task_id="test-task-123",
            odm_project_id=42,
        )
        assert job.odm_task_id == "test-task-123"
        assert job.odm_project_id == 42
        assert job.job_type == "odm_process"
