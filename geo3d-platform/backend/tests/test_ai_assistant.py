"""
Unit tests for MVP 7: AI Geospatial Assistant
Validates terrain metric summarization, conversational spatial queries,
Cesium viewer action dispatch (fly_to, filter_classes, activate_tool),
and pin coordinate generation.
"""

import pytest
from app.services.ai_service import ai_service


@pytest.fixture
def mock_dataset_metadata():
    return {
        "name": "Dayton DALES-2 LiDAR Survey",
        "crs": "EPSG:32616",
        "min_z": 220.5,
        "max_z": 315.8,
        "point_count": 520000,
        "point_density": 24.5,
        "center": {"lon": -84.1896, "lat": 39.7586, "alt": 250.0},
        "classification_breakdown": {
            "2": {"name": "Ground", "percentage": 42.5},
            "5": {"name": "High Vegetation", "percentage": 28.0},
            "6": {"name": "Buildings", "percentage": 22.0},
            "9": {"name": "Water", "percentage": 2.5},
            "7": {"name": "Noise", "percentage": 0.5},
        }
    }


@pytest.fixture
def mock_sample_points():
    return [
        {"lon": -84.1890, "lat": 39.7580, "alt": 225.0, "classification": 2},
        {"lon": -84.1892, "lat": 39.7582, "alt": 260.0, "classification": 5},
        {"lon": -84.1898, "lat": 39.7590, "alt": 315.8, "classification": 6},  # Highest / Peak
        {"lon": -84.1885, "lat": 39.7575, "alt": 220.5, "classification": 2},  # Lowest
    ]


def test_ai_terrain_summary_generation(mock_dataset_metadata):
    """Verify structured terrain metrics aggregation and suitability rating."""
    summary = ai_service.generate_terrain_summary(mock_dataset_metadata)
    assert summary["status"] == "ready"
    metrics = summary["structured_metrics"]
    assert metrics["dataset_name"] == "Dayton DALES-2 LiDAR Survey"
    assert metrics["elevation"]["min_m"] == 220.5
    assert metrics["elevation"]["max_m"] == 315.8
    assert metrics["elevation"]["relief_m"] == 95.3
    assert metrics["composition_percentages"]["ground"] == 42.5
    assert metrics["composition_percentages"]["buildings"] == 22.0
    assert len(summary["geospatial_insights"]) >= 1
    assert summary["development_suitability"] in ["High", "Moderate"]


def test_ai_chat_peak_query(mock_dataset_metadata, mock_sample_points):
    """Verify 'highest point' query generates fly_to action with 3D pin at peak."""
    res = ai_service.process_chat_query(
        query="Take me to the highest elevation point",
        dataset_metadata=mock_dataset_metadata,
        sample_points=mock_sample_points
    )
    assert res["tool_called"] == "fly_to_peak"
    action = res["action"]
    assert action["type"] == "fly_to"
    assert action["coords"]["lon"] == -84.1898
    assert action["coords"]["lat"] == 39.7590
    assert action["coords"]["alt"] > 315.8

    # Verify pin payload for Cesium 3D rendering
    assert "pin" in action
    pin = action["pin"]
    assert pin["lon"] == -84.1898
    assert pin["lat"] == 39.7590
    assert pin["alt"] == 315.8
    assert "Peak" in pin["label"]
    assert "315.8" in res["reply"]


def test_ai_chat_lowest_query(mock_dataset_metadata, mock_sample_points):
    """Verify 'lowest point' query generates fly_to action with base pin."""
    res = ai_service.process_chat_query(
        query="Show the lowest depression in this survey",
        dataset_metadata=mock_dataset_metadata,
        sample_points=mock_sample_points
    )
    assert res["tool_called"] == "fly_to_lowest"
    action = res["action"]
    assert action["type"] == "fly_to"
    assert action["coords"]["lon"] == -84.1885
    assert action["coords"]["lat"] == 39.7575
    assert "pin" in action
    assert "220.5" in res["reply"]


def test_ai_chat_building_isolation(mock_dataset_metadata):
    """Verify building isolation query dispatches filter_classes action with ASPRS 6 & 12."""
    res = ai_service.process_chat_query(
        query="Show only buildings and structures",
        dataset_metadata=mock_dataset_metadata
    )
    assert res["tool_called"] == "filter_buildings"
    action = res["action"]
    assert action["type"] == "filter_classes"
    assert 6 in action["classes"]
    assert 12 in action["classes"]
    assert action["color_mode"] == "classification"
    assert "Buildings Filtered" in res["reply"]


def test_ai_chat_vegetation_isolation(mock_dataset_metadata):
    """Verify vegetation query dispatches filter_classes action with canopy classes."""
    res = ai_service.process_chat_query(
        query="Isolate trees and vegetation canopy",
        dataset_metadata=mock_dataset_metadata
    )
    assert res["tool_called"] == "filter_vegetation"
    action = res["action"]
    assert action["type"] == "filter_classes"
    assert set(action["classes"]) == {3, 4, 5}
    assert "Vegetation Isolated" in res["reply"]


def test_ai_chat_bare_earth_mode(mock_dataset_metadata):
    """Verify ground query isolates Class 2 and switches to elevation ramp."""
    res = ai_service.process_chat_query(
        query="Switch to bare earth terrain mode",
        dataset_metadata=mock_dataset_metadata
    )
    assert res["tool_called"] == "filter_ground"
    action = res["action"]
    assert action["type"] == "filter_classes"
    assert action["classes"] == [2]
    assert action["color_mode"] == "elevation"


def test_ai_chat_suitability_query(mock_dataset_metadata):
    """Verify development suitability query activates slope tool with analysis recommendation."""
    res = ai_service.process_chat_query(
        query="Is this area suitable for construction development?",
        dataset_metadata=mock_dataset_metadata
    )
    assert res["tool_called"] == "analyze_suitability"
    assert res["action"]["type"] == "activate_tool"
    assert res["action"]["tool"] == "slope"
    assert "Site Development Suitability" in res["reply"]


def test_ai_chat_measurement_tool_activation(mock_dataset_metadata):
    """Verify natural language requests can trigger profile and volume tools."""
    profile_res = ai_service.process_chat_query(
        query="I need an elevation profile cross section",
        dataset_metadata=mock_dataset_metadata
    )
    assert profile_res["action"]["type"] == "activate_tool"
    assert profile_res["action"]["tool"] == "profile"

    volume_res = ai_service.process_chat_query(
        query="Calculate cut and fill earthwork volume",
        dataset_metadata=mock_dataset_metadata
    )
    assert volume_res["action"]["type"] == "activate_tool"
    assert volume_res["action"]["tool"] == "volume"


def test_ai_chat_color_modes(mock_dataset_metadata):
    """Verify color mode switching commands."""
    res_elev = ai_service.process_chat_query(
        query="Change color mode to elevation ramp",
        dataset_metadata=mock_dataset_metadata
    )
    assert res_elev["action"] == {"type": "set_color_mode", "mode": "elevation"}

    res_intensity = ai_service.process_chat_query(
        query="Show lidar intensity",
        dataset_metadata=mock_dataset_metadata
    )
    assert res_intensity["action"] == {"type": "set_color_mode", "mode": "intensity"}
