"""
Unit and Integration Tests for GL3D Photogrammetry Dataset Integration.
Tests:
  - GL3D camera parser (intrinsics, extrinsics, world-center)
  - Image list parser
  - PLY point cloud writer & reader with geographic anchor transforms
  - GL3DProvider catalog & search
"""

import os
import struct
import tempfile
import pytest
import numpy as np

from app.processing.gl3d_proc.gl3d_parser import (
    GL3DCamera,
    parse_cameras,
    parse_image_list,
    compute_scene_extent,
    compute_scene_centroid,
    read_ply_sample,
)
from app.processing.gl3d_proc.gl3d_processor import GL3DProcessor
from app.providers.gl3d import GL3DProvider
from app.providers import registry


def test_gl3d_camera_math():
    """Test camera center computation and intrinsic matrix."""
    # Identity rotation, translation along -Z
    cam = GL3DCamera(
        image_id=0,
        fx=1000.0, fy=1000.0,
        px=500.0, py=500.0,
        skew=0.0,
        translation=np.array([10.0, 20.0, 30.0]),
        rotation=np.eye(3),
    )
    # C = -R^T * t = -I * [10, 20, 30] = [-10, -20, -30]
    assert np.allclose(cam.center, np.array([-10.0, -20.0, -30.0]))
    assert cam.intrinsic_matrix.shape == (3, 3)
    assert cam.intrinsic_matrix[0, 0] == 1000.0
    assert cam.projection_matrix.shape == (3, 4)


def test_parse_cameras_from_file(tmp_path):
    """Test parsing GL3D cameras.txt format."""
    cam_file = tmp_path / "cameras.txt"
    cam_file.write_text(
        "# IMAGE_ID FX FY PX PY SKEW T1 T2 T3 R11 R12 R13 R21 R22 R23 R31 R32 R33\n"
        "0 3995.67 3995.67 2304 1728 0 63.67 -28.86 53.91 1 0 0 0 1 0 0 0 1\n"
        "1 3995.67 3995.67 2304 1728 0 42.54 -29.65 53.70 1 0 0 0 1 0 0 0 1\n"
    )

    cameras = parse_cameras(str(cam_file))
    assert len(cameras) == 2
    assert cameras[0].image_id == 0
    assert cameras[1].image_id == 1
    assert cameras[0].fx == pytest.approx(3995.67)
    assert cameras[0].center[0] == pytest.approx(-63.67)


def test_parse_image_list(tmp_path):
    """Test parsing image_list.txt."""
    img_file = tmp_path / "image_list.txt"
    img_file.write_text(
        "# Image list\n"
        "DJI_0001.JPG\n"
        "DJI_0002.JPG\n"
        "\n"
        "DJI_0003.JPG\n"
    )

    images = parse_image_list(str(img_file))
    assert images == ["DJI_0001.JPG", "DJI_0002.JPG", "DJI_0003.JPG"]


def test_scene_extent_and_centroid():
    """Test extent and centroid calculations."""
    cams = [
        GL3DCamera(0, 500, 500, 250, 250, 0, np.array([0, 0, 0]), np.eye(3)),
        GL3DCamera(1, 500, 500, 250, 250, 0, np.array([-10, -20, -30]), np.eye(3)),
    ]
    # centers: [0, 0, 0] and [10, 20, 30]
    extent = compute_scene_extent(cams)
    assert extent["min_x"] == pytest.approx(0.0)
    assert extent["max_x"] == pytest.approx(10.0)

    centroid = compute_scene_centroid(cams)
    assert centroid == pytest.approx((5.0, 10.0, 15.0))


def test_gl3d_processor_and_ply_sample(tmp_path):
    """Test full processing pipeline and PLY read sampling."""
    scene_dir = tmp_path / "scene_test"
    geolabel_dir = scene_dir / "geolabel"
    geolabel_dir.mkdir(parents=True)

    # Write cameras
    (geolabel_dir / "cameras.txt").write_text(
        "0 1000 1000 500 500 0 -10 -10 -10 1 0 0 0 1 0 0 0 1\n"
        "1 1000 1000 500 500 0 10 10 10 1 0 0 0 1 0 0 0 1\n"
    )
    (scene_dir / "image_list.txt").write_text("img_0.jpg\nimg_1.jpg\n")

    output_dir = tmp_path / "output"
    processor = GL3DProcessor(str(scene_dir))
    metadata = processor.process(str(output_dir))

    assert metadata["camera_count"] == 2
    assert metadata["image_count"] == 2
    assert os.path.exists(metadata["ply_path"])

    # Sample points
    samples = read_ply_sample(metadata["ply_path"], sample_size=10, anchor={"lon": 10.0, "lat": 50.0, "alt": 100.0})
    assert len(samples) > 0
    assert "lon" in samples[0]
    assert "lat" in samples[0]
    assert "alt" in samples[0]
    assert "intensity" in samples[0]


@pytest.mark.asyncio
async def test_gl3d_provider_search():
    """Test GL3DProvider catalog search and retrieval."""
    provider = GL3DProvider()
    assert "GL3D" in provider.provider_name

    # Search all
    all_scenes = await provider.search_datasets()
    assert len(all_scenes) >= 5

    # Keyword search
    urban_scenes = await provider.search_datasets(query="urban")
    assert any("Urban" in s.name for s in urban_scenes)

    # Metadata lookup
    meta = await provider.get_metadata("000000000000000000000000")
    assert meta is not None
def test_gl3d_mesh_generation(tmp_path):
    """Test generating binary GLB and OBJ models for all 4 GL3D scene categories."""
    from app.processing.gl3d_proc.gl3d_mesh_generator import (
        generate_scene_mesh,
        build_urban_mesh,
        build_scenic_mesh,
        build_rural_mesh,
        build_object_mesh,
    )

    categories = ["urban", "scenic", "rural", "object"]
    for cat in categories:
        mesh = generate_scene_mesh(category=cat)
        assert len(mesh.vertices) > 20
        assert len(mesh.faces) > 10
        assert mesh.normals.shape == mesh.vertices.shape

        glb_file = str(tmp_path / f"{cat}.glb")
        obj_file = str(tmp_path / f"{cat}.obj")

        mesh.write_glb(glb_file)
        mesh.write_obj(obj_file)

        assert os.path.exists(glb_file)
        assert os.path.getsize(glb_file) > 100
        assert os.path.exists(obj_file)
        assert os.path.getsize(obj_file) > 100

        # Verify GLB binary header
        with open(glb_file, "rb") as f:
            magic = f.read(4)
            version, total_len = struct.unpack("<II", f.read(8))
            assert magic == b"glTF"
            assert version == 2
            assert total_len == os.path.getsize(glb_file)


def test_gl3d_provider_in_registry():
    """Verify GL3D is registered in ProviderRegistry."""
    provider = registry.get_provider("gl3d")
    assert provider is not None
    assert "GL3D" in provider.provider_name

    providers_list = registry.list_providers()
    assert any(p["id"] == "gl3d" for p in providers_list)


