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
    test_distance_metrics_calculation,
    test_area_and_perimeter_metrics,
    test_vertical_height_calculation,
    test_slope_and_aspect_analysis,
    test_volume_estimation,
    test_elevation_profile_generation
)
from tests.test_processing import (
    test_las_processor_header,
    test_las_processor_metadata_and_stats,
    test_raster_processor_metadata
)
from tests.test_dales_detection import (
    test_dales_class_metadata,
    test_dales_tile_parsing,
    test_asprs_to_dales_mapping,
    test_dales_benchmark_tile_generation,
    test_3d_object_detector_bounding_boxes,
    test_3d_detector_empty_input,
)
from tests.test_large_dataset_optimization import (
    test_chunked_point_streaming,
    test_memory_safe_sampling,
    test_ogc_3d_tiles_compliance_and_headers,
    test_spatial_index_octree_bounds,
    test_tiling_throughput_benchmark,
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
        ("Distance 2D/3D Calculation", test_distance_metrics_calculation),
        ("Area Metric Calculation", test_area_and_perimeter_metrics),
        ("Height Difference (Delta Z)", test_vertical_height_calculation),
        ("Slope & Aspect Analysis", test_slope_and_aspect_analysis),
        ("Cut/Fill Volume Estimation", test_volume_estimation),
        ("Elevation Profile Transect", test_elevation_profile_generation),
        ("LAS Header Parsing", test_las_processor_header),
        ("LAS Metadata & Stats Breakdown", test_las_processor_metadata_and_stats),
        ("Raster Metadata Processing", test_raster_processor_metadata),
        ("DALES-2 Semantic Class Metadata", test_dales_class_metadata),
        ("DALES Tile ID Parsing", test_dales_tile_parsing),
        ("ASPRS to DALES Translation", test_asprs_to_dales_mapping),
        ("DALES-2 Benchmark Tile Generator", test_dales_benchmark_tile_generation),
        ("3D Object Detection & Bounding Boxes", test_3d_object_detector_bounding_boxes),
        ("3D Detector Empty Input Handling", test_3d_detector_empty_input),
        ("Chunked Point Streaming (>1 GB Datasets)", test_chunked_point_streaming),
        ("Memory-Safe Point Sampling", test_memory_safe_sampling),
        ("OGC 3D Tiles 1.1 Header & Spec Compliance", test_ogc_3d_tiles_compliance_and_headers),
        ("Octree Spatial Index Bounds & Partitioning", test_spatial_index_octree_bounds),
        ("Tiling Throughput & Memory Benchmark", test_tiling_throughput_benchmark),
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
