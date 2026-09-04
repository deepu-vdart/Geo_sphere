"""
GL3D Data Format Parser.
Parses GL3D-specific file formats:
  - cameras.txt: intrinsic/extrinsic camera parameters from SfM
  - image_list.txt: image filename list per scene
  - depth maps: PFM (Portable Float Map) format
  - keypoints: binary SIFT keypoint descriptors
"""

import os
import re
import struct
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GL3DCamera:
    """Parsed camera from GL3D cameras.txt."""
    image_id: int
    fx: float
    fy: float
    px: float  # principal point x
    py: float  # principal point y
    skew: float
    translation: np.ndarray  # 3x1
    rotation: np.ndarray     # 3x3
    center: np.ndarray = field(default_factory=lambda: np.zeros(3))  # world-space camera center

    def __post_init__(self):
        # Camera center in world coordinates: C = -R^T * t
        self.center = -self.rotation.T @ self.translation

    @property
    def intrinsic_matrix(self) -> np.ndarray:
        """3x3 intrinsic camera matrix K."""
        return np.array([
            [self.fx, self.skew, self.px],
            [0,       self.fy,   self.py],
            [0,       0,         1      ]
        ])

    @property
    def projection_matrix(self) -> np.ndarray:
        """3x4 projection matrix P = K [R | t]."""
        Rt = np.hstack([self.rotation, self.translation.reshape(3, 1)])
        return self.intrinsic_matrix @ Rt


def parse_cameras(cameras_txt_path: str) -> List[GL3DCamera]:
    """
    Parse GL3D cameras.txt file.

    Format per line:
      IMAGE_ID, FX, FY, PX, PY, SKEW, TRANSLATION(3), ROTATION(3x3 row-major)

    Returns list of GL3DCamera objects.
    """
    cameras = []

    if not os.path.exists(cameras_txt_path):
        logger.warning(f"cameras.txt not found: {cameras_txt_path}")
        return cameras

    with open(cameras_txt_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            tokens = line.split()
            if len(tokens) < 18:  # 1 + 5 + 3 + 9 = 18 minimum
                continue

            try:
                vals = [float(t) for t in tokens]
                image_id = int(vals[0])
                fx, fy = vals[1], vals[2]
                px, py = vals[3], vals[4]
                skew = vals[5]
                translation = np.array(vals[6:9])
                rotation = np.array(vals[9:18]).reshape(3, 3)

                cam = GL3DCamera(
                    image_id=image_id,
                    fx=fx, fy=fy,
                    px=px, py=py,
                    skew=skew,
                    translation=translation,
                    rotation=rotation,
                )
                cameras.append(cam)
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse camera line: {line[:80]}... — {e}")
                continue

    logger.info(f"Parsed {len(cameras)} cameras from {cameras_txt_path}")
    return cameras


def parse_image_list(image_list_path: str) -> List[str]:
    """
    Parse GL3D image_list.txt — one image filename per line.
    Returns list of image filenames (relative paths).
    """
    images = []

    if not os.path.exists(image_list_path):
        logger.warning(f"image_list.txt not found: {image_list_path}")
        return images

    with open(image_list_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                images.append(line)

    logger.info(f"Parsed {len(images)} images from {image_list_path}")
    return images


def parse_depth_pfm(pfm_path: str) -> Optional[np.ndarray]:
    """
    Parse a PFM (Portable Float Map) depth file.
    GL3D uses PFM for storing per-pixel depth values.

    Returns 2D numpy array of float32 depth values, or None on failure.
    """
    if not os.path.exists(pfm_path):
        return None

    try:
        with open(pfm_path, 'rb') as f:
            # Read header
            header = f.readline().decode('ascii').strip()
            if header == 'PF':
                color = True
            elif header == 'Pf':
                color = False
            else:
                logger.warning(f"Not a PFM file: {pfm_path}")
                return None

            # Read dimensions
            dim_line = f.readline().decode('ascii').strip()
            width, height = [int(x) for x in dim_line.split()]

            # Read scale / endianness
            scale_line = f.readline().decode('ascii').strip()
            scale = float(scale_line)
            endian = '<' if scale < 0 else '>'
            scale = abs(scale)

            # Read data
            channels = 3 if color else 1
            data = np.frombuffer(f.read(), dtype=f'{endian}f4')
            data = data.reshape(height, width, channels) if color else data.reshape(height, width)

            # PFM stores bottom-to-top, flip vertically
            data = np.flipud(data)

            if scale != 1.0:
                data *= scale

            return data.astype(np.float32)

    except Exception as e:
        logger.warning(f"Failed to parse PFM file {pfm_path}: {e}")
        return None


def compute_scene_extent(cameras: List[GL3DCamera]) -> Dict[str, float]:
    """
    Compute the bounding box of a scene from camera positions.
    Returns dict with min_x, max_x, min_y, max_y, min_z, max_z in local SfM coords.
    """
    if not cameras:
        return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "min_z": 0, "max_z": 0}

    centers = np.array([cam.center for cam in cameras])
    return {
        "min_x": float(centers[:, 0].min()),
        "max_x": float(centers[:, 0].max()),
        "min_y": float(centers[:, 1].min()),
        "max_y": float(centers[:, 1].max()),
        "min_z": float(centers[:, 2].min()),
        "max_z": float(centers[:, 2].max()),
    }


def compute_scene_centroid(cameras: List[GL3DCamera]) -> Tuple[float, float, float]:
    """Compute the centroid of all camera positions."""
    if not cameras:
        return (0.0, 0.0, 0.0)

    centers = np.array([cam.center for cam in cameras])
    centroid = centers.mean(axis=0)
    return (float(centroid[0]), float(centroid[1]), float(centroid[2]))


def cameras_to_point_cloud(
    cameras: List[GL3DCamera],
    depths: Dict[int, np.ndarray],
    images: Dict[int, np.ndarray],
    max_points_per_view: int = 5000,
    depth_min: float = 0.1,
    depth_max: float = 1000.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Unproject depth maps through cameras to create a colored 3D point cloud.

    Args:
        cameras: List of parsed GL3D cameras
        depths: Dict mapping image_id → depth map (HxW float array)
        images: Dict mapping image_id → RGB image (HxWx3 uint8 array)
        max_points_per_view: Max points to sample per depth map
        depth_min: Minimum valid depth
        depth_max: Maximum valid depth

    Returns:
        Tuple of (points_xyz [Nx3 float64], colors_rgb [Nx3 uint8])
    """
    all_points = []
    all_colors = []

    for cam in cameras:
        if cam.image_id not in depths:
            continue

        depth = depths[cam.image_id]
        H, W = depth.shape[:2]

        # Create pixel coordinate grid
        u_coords, v_coords = np.meshgrid(np.arange(W), np.arange(H))
        u_flat = u_coords.flatten().astype(np.float64)
        v_flat = v_coords.flatten().astype(np.float64)
        d_flat = depth.flatten().astype(np.float64)

        # Filter valid depths
        valid = (d_flat > depth_min) & (d_flat < depth_max) & np.isfinite(d_flat)
        valid_idx = np.where(valid)[0]

        if len(valid_idx) == 0:
            continue

        # Subsample if too many valid points
        if len(valid_idx) > max_points_per_view:
            rng = np.random.default_rng(seed=cam.image_id)
            valid_idx = rng.choice(valid_idx, size=max_points_per_view, replace=False)

        u_sel = u_flat[valid_idx]
        v_sel = v_flat[valid_idx]
        d_sel = d_flat[valid_idx]

        # Unproject: ray in camera space
        K_inv = np.linalg.inv(cam.intrinsic_matrix)
        pixels = np.vstack([u_sel, v_sel, np.ones_like(u_sel)])  # 3xN
        rays_cam = K_inv @ pixels  # 3xN normalized rays
        points_cam = rays_cam * d_sel[np.newaxis, :]  # 3xN scaled by depth

        # Transform to world: P_world = R^T * (P_cam - t)
        points_world = cam.rotation.T @ (points_cam - cam.translation.reshape(3, 1))  # 3xN
        all_points.append(points_world.T)  # Nx3

        # Get colors
        if cam.image_id in images:
            img = images[cam.image_id]
            u_int = np.clip(u_sel.astype(int), 0, img.shape[1] - 1)
            v_int = np.clip(v_sel.astype(int), 0, img.shape[0] - 1)
            colors = img[v_int, u_int]  # Nx3
            all_colors.append(colors)
        else:
            # Default gray
            all_colors.append(np.full((len(valid_idx), 3), 180, dtype=np.uint8))

    if not all_points:
        return np.empty((0, 3), dtype=np.float64), np.empty((0, 3), dtype=np.uint8)

    points_xyz = np.vstack(all_points)
    colors_rgb = np.vstack(all_colors).astype(np.uint8)

    logger.info(f"Generated point cloud with {len(points_xyz)} points from {len(all_points)} views")
    return points_xyz, colors_rgb


def get_scene_summary(scene_dir: str) -> Dict[str, Any]:
    """
    Quick summary of a GL3D scene directory without loading full data.
    Returns image count, camera count, and available data files.
    """
    summary: Dict[str, Any] = {
        "scene_id": os.path.basename(scene_dir),
        "image_count": 0,
        "camera_count": 0,
        "has_cameras": False,
        "has_depths": False,
        "has_keypoints": False,
        "has_images": False,
    }

    # Image list
    img_list = os.path.join(scene_dir, "image_list.txt")
    if os.path.exists(img_list):
        images = parse_image_list(img_list)
        summary["image_count"] = len(images)

    # Cameras
    cameras_path = os.path.join(scene_dir, "geolabel", "cameras.txt")
    if os.path.exists(cameras_path):
        summary["has_cameras"] = True
        cams = parse_cameras(cameras_path)
        summary["camera_count"] = len(cams)

    # Depth maps
    depths_dir = os.path.join(scene_dir, "depths")
    if os.path.isdir(depths_dir):
        summary["has_depths"] = True

    # Keypoints
    kpts_dir = os.path.join(scene_dir, "img_kpts")
    if os.path.isdir(kpts_dir):
        summary["has_keypoints"] = True

    # Images
    for img_dir in ["undist_images", "blended_images"]:
        if os.path.isdir(os.path.join(scene_dir, img_dir)):
            summary["has_images"] = True
            break

    return summary


def read_ply_sample(
    ply_path: str,
    sample_size: int = 25000,
    anchor: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Read sampled vertices from a binary PLY file produced by GL3DProcessor.
    Converts local coordinates to WGS84 (lon, lat, alt) via anchor if provided.
    """
    import math

    if not os.path.exists(ply_path):
        return []

    # Default anchor: Zurich scenic area if none specified
    if not anchor:
        anchor = {"lon": 8.5417, "lat": 47.3769, "alt": 450.0}

    anchor_lon = float(anchor.get("lon", 8.5417))
    anchor_lat = float(anchor.get("lat", 47.3769))
    anchor_alt = float(anchor.get("alt", 450.0))
    cos_lat = math.cos(math.radians(anchor_lat))

    points = []
    try:
        with open(ply_path, "rb") as f:
            header_lines = []
            while True:
                line = f.readline().decode("ascii", errors="ignore").strip()
                header_lines.append(line)
                if line == "end_header":
                    break

            # Parse vertex count
            vertex_count = 0
            for h in header_lines:
                if h.startswith("element vertex"):
                    vertex_count = int(h.split()[-1])
                    break

            if vertex_count == 0:
                return []

            # Determine subsample step
            step = max(1, vertex_count // sample_size)
            stride = 15  # 3*4 (xyz float32) + 3*1 (rgb uchar) = 15 bytes per vertex

            data = f.read(vertex_count * stride)
            dt = np.dtype([
                ("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                ("r", "u1"), ("g", "u1"), ("b", "u1")
            ])
            arr = np.frombuffer(data, dtype=dt)

            sampled = arr[::step][:sample_size]
            for pt in sampled:
                x, y, z = float(pt["x"]), float(pt["y"]), float(pt["z"])
                r, g, b = int(pt["r"]), int(pt["g"]), int(pt["b"])

                lon = anchor_lon + (x / (111320.0 * cos_lat))
                lat = anchor_lat + (y / 110540.0)
                alt = anchor_alt + z

                points.append({
                    "lon": round(lon, 7),
                    "lat": round(lat, 7),
                    "alt": round(alt, 2),
                    "classification": 1,
                    "intensity": int((r + g + b) // 3 * 200),
                })
    except Exception as e:
        logger.warning(f"Failed to read PLY sample from {ply_path}: {e}")

    return points

