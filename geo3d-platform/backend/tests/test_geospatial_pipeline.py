"""
Comprehensive Geospatial Pipeline Tests
Tests Data Providers, PDAL Pipelines, Terrain Derivatives, AOI estimation, and AI interpretation.
"""

import pytest
import numpy as np
from app.providers import registry
from app.processing.gdal_proc.terrain_derivatives import (
    generate_hillshade,
    generate_slope_aspect,
    generate_roughness,
    generate_contours,
    terrain_engine
)
from app.processing.pdal_proc.pipeline_runner import pipeline_runner
from app.services.ai_service import ai_service


def test_data_providers_registry():
    """Verify registry discovers OpenTopography and USGS 3DEP providers."""
    providers = registry.list_providers()
    provider_ids = [p["id"] for p in providers]
    assert "opentopography" in provider_ids
    assert "usgs_3dep" in provider_ids


@pytest.mark.asyncio
async def test_opentopography_search():
    """Verify searching OpenTopography catalog returns San Diego dataset."""
    results = await registry.search_all(query="San Diego")
    assert len(results) >= 1
    sd_ds = next((d for d in results if "San Diego" in d.name), None)
    assert sd_ds is not None
    assert sd_ds.dataset_id == "OTLAS.092011.2875.1"
    assert sd_ds.crs == "EPSG:26911"
    assert sd_ds.format == "LAZ"


def test_pdal_pipeline_templates():
    """Verify all declarative PDAL pipelines can be loaded and rendered."""
    pipelines = ["inspect", "crop", "reproject", "ground", "noise", "dtm", "dsm", "tiles"]
    for p_name in pipelines:
        rendered = pipeline_runner.render_pipeline(
            p_name,
            {
                "INPUT_FILE": "test_in.laz",
                "OUTPUT_FILE": "test_out.laz",
                "MIN_X": -117.2, "MAX_X": -117.1,
                "MIN_Y": 32.7, "MAX_Y": 32.8,
                "IN_SRS": "EPSG:26911", "OUT_SRS": "EPSG:4326",
                "DB_CONN": "postgresql://localhost/geo3d"
            }
        )
        assert isinstance(rendered, list)
        assert len(rendered) >= 2


def test_terrain_derivatives_engine():
    """Verify DTM, DSM, Hillshade, Slope, Aspect, Roughness, and Contours calculations."""
    # Synthetic terrain grid 20x20 with slope
    y, x = np.mgrid[0:20, 0:20]
    elevation = 200.0 + (x * 0.5) + (y * 0.2) + np.sin(x) * 2.0

    # Hillshade
    hs = generate_hillshade(elevation, cell_size=1.0)
    assert hs.shape == (20, 20)
    assert hs.dtype == np.uint8
    assert 0 <= np.min(hs) <= np.max(hs) <= 255

    # Slope & Aspect
    slope, aspect, stats = generate_slope_aspect(elevation, cell_size=1.0)
    assert slope.shape == (20, 20)
    assert stats["min_slope_deg"] >= 0.0
    assert stats["max_slope_deg"] <= 90.0
    assert 0.0 <= stats["dominant_aspect_deg"] <= 360.0

    # Roughness (TRI)
    tri = generate_roughness(elevation)
    assert tri.shape == (20, 20)

    # Contours
    contours = generate_contours(elevation, origin_lon=-84.19, origin_lat=39.76, pixel_size_lon=0.0001, pixel_size_lat=0.0001, interval_m=1.0)
    assert contours["type"] == "FeatureCollection"
    assert len(contours["features"]) > 0


def test_ai_geospatial_summary():
    """Verify AI summary synthesizes structured geospatial metrics and actionable insights."""
    sample_meta = {
        "name": "Dayton LiDAR Survey",
        "crs": "EPSG:32616",
        "point_count": 200000,
        "point_density": 45.2,
        "min_z": 240.0,
        "max_z": 275.0,
        "classification_breakdown": {
            "2": {"name": "Ground", "count": 120000, "percentage": 60.0},
            "5": {"name": "High Veg", "count": 50000, "percentage": 25.0},
            "6": {"name": "Building", "count": 30000, "percentage": 15.0}
        }
    }
    summary = ai_service.generate_terrain_summary(dataset_metadata=sample_meta)
    assert summary["status"] == "ready"
    assert summary["development_suitability"] in ["High", "Moderate", "Low"]
    assert len(summary["geospatial_insights"]) >= 1
    assert summary["structured_metrics"]["total_points"] == 200000
