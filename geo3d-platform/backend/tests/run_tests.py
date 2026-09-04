import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_geospatial_pipeline import (
    test_data_providers_registry,
    test_opentopography_search,
    test_pdal_pipeline_templates,
    test_terrain_derivatives_engine,
    test_ai_geospatial_summary
)
from tests.test_analysis import (
    test_distance_calculation,
    test_area_calculation,
    test_height_calculation,
    test_slope_aspect_calculation,
    test_volume_calculation,
    test_elevation_profile_generation
)
from tests.test_processing import (
    test_las_processor_synthetic,
    test_raster_processor
)


def run_all():
    print("=" * 60)
    print("  Geo3D Platform — Automated Geospatial Test Suite")
    print("=" * 60)

    tests = [
        ("Data Providers Registry", test_data_providers_registry),
        ("PDAL Pipeline Templates", test_pdal_pipeline_templates),
        ("Terrain Derivatives Engine (DTM/DSM/Hillshade/Slope/Contours)", test_terrain_derivatives_engine),
        ("AI Geospatial Terrain Summary", test_ai_geospatial_summary),
        ("Distance 2D/3D Calculation", test_distance_calculation),
        ("Area Metric Calculation", test_area_calculation),
        ("Height Difference (Delta Z)", test_height_calculation),
        ("Slope & Aspect Analysis", test_slope_aspect_calculation),
        ("Cut/Fill Volume Estimation", test_volume_calculation),
        ("Elevation Profile Transect", test_elevation_profile_generation),
        ("LAS Point Cloud Processing", test_las_processor_synthetic),
        ("Raster GeoTIFF Processing", test_raster_processor),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    # Async tests
    async_tests = [
        ("OpenTopography Catalog Search", test_opentopography_search),
    ]

    for name, fn in async_tests:
        try:
            asyncio.run(fn())
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    print("=" * 60)
    print(f"  Results: {passed} PASSED, {failed} FAILED / Total {passed + failed}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
