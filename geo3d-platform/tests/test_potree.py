"""
Unit and Integration Tests for Potree 1.8+ / COPC REST API Endpoints.
Tests Potree metadata, point streaming, 2D cross-section slicing, and COPC downloads.
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, get_db
from app.models.project import Project
from app.models.dataset import Dataset
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_potree_metadata_and_points():
    """Test Potree 2.0 metadata and high-density points streaming."""
    await init_db()

    # Create dummy project & dataset
    async for db in get_db():
        proj_id = uuid.uuid4()
        ds_id = uuid.uuid4()

        proj = Project(
            id=proj_id,
            name="Potree Test Project",
            crs="EPSG:32617",
            status="active"
        )
        db.add(proj)

        ds = Dataset(
            id=ds_id,
            project_id=proj_id,
            name="Aukerman Drone Point Cloud",
            dataset_type="photogrammetry",
            crs="EPSG:32617",
            min_z=275.0,
            max_z=305.0,
            point_count=9481325,
            status="active",
            metadata_json={"anchor": {"lon": -81.7518, "lat": 41.3041, "alt": 285.0}}
        )
        db.add(ds)
        await db.commit()
        break

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test Metadata
        meta_res = await ac.get(f"/api/datasets/{ds_id}/potree/metadata.json")
        assert meta_res.status_code == 200
        meta = meta_res.json()
        assert meta["version"] == "2.0"
        assert meta["points"] == 9481325
        assert meta["projection"] == "EPSG:32617"
        assert "boundingBox" in meta
        assert "pointAttributes" in meta

        # 2. Test Point Streaming
        pts_res = await ac.get(f"/api/datasets/{ds_id}/potree/points?limit=500")
        assert pts_res.status_code == 200
        pts_data = pts_res.json()
        assert pts_data["point_count"] > 0
        assert pts_data["has_normals"] is True
        assert pts_data["has_colors"] is True

        first_pt = pts_data["points"][0]
        assert "x" in first_pt
        assert "y" in first_pt
        assert "z" in first_pt
        assert "r" in first_pt
        assert "g" in first_pt
        assert "b" in first_pt
        assert "nx" in first_pt
        assert "ny" in first_pt
        assert "nz" in first_pt
        assert "classification" in first_pt

        # 3. Test 2D Cross Section Slicing
        slice_res = await ac.post(
            f"/api/datasets/{ds_id}/potree/cross-section",
            json={
                "p1": {"x": -50.0, "y": -50.0, "z": 285.0},
                "p2": {"x": 50.0, "y": 50.0, "z": 285.0},
                "corridor_width": 5.0,
                "max_points": 500
            }
        )
        assert slice_res.status_code == 200
        slice_data = slice_res.json()
        assert slice_data["transect_length_m"] > 0
        assert "min_elevation" in slice_data
        assert "max_elevation" in slice_data
        assert "points" in slice_data
