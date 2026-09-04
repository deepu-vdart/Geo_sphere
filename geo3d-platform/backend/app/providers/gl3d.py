"""
GL3D (Geometric Learning with 3D Reconstruction) Data Provider.
Provides access to the GL3D dataset catalog of 543 photogrammetry scenes
with drone images, SfM camera parameters, triangulated meshes, and depth maps.

Dataset: https://github.com/lzx551402/GL3D
Paper: Shen et al., "Matchable Image Retrieval by Learning from Surface Reconstruction", ACCV 2018
"""

import os
import logging
from typing import Dict, Any, List, Optional

import httpx

from app.providers.base import BaseDataProvider, DatasetMetadata

logger = logging.getLogger(__name__)

# GitHub raw base URLs for GL3D data
GL3D_REPO = "lzx551402/GL3D"
GL3D_RAW_BASE = f"https://raw.githubusercontent.com/{GL3D_REPO}"
GL3D_MASTER_RAW = f"{GL3D_RAW_BASE}/master"
GL3D_V2_RAW = f"{GL3D_RAW_BASE}/v2"
GL3D_API_BASE = f"https://api.github.com/repos/{GL3D_REPO}"

# OneDrive download links from GL3D README (v2 branch)
GL3D_DOWNLOADS = {
    "gl3d_imgs": "https://1drv.ms/u/s!Anl8gFgW1C7LknxGy1gesj30SQ1I",
    "gl3d_cams": "https://1drv.ms/u/s!Anl8gFgW1C7Lkmf-zEcSRRlGPQyv",
    "gl3d_kpts": "https://1drv.ms/u/s!Anl8gFgW1C7LkzlYK0CSNzcGc2m0",
    "gl3d_depths": "https://1drv.ms/u/s!Anl8gFgW1C7LkzqH3fqIR-z3ZZis",
    "gl3d_corr": "https://1drv.ms/u/s!Anl8gFgW1C7LkmhoY66o5bViFhZ-",
}

# Curated sample scenes from GL3D (representative subset for quick demo)
# Scene IDs are hex strings from the data/ directory in the GL3D repo
GL3D_SAMPLE_SCENES = [
    {
        "scene_id": "000000000000000000000000",
        "name": "GL3D Scene 0 — Urban High-Rise Area",
        "description": "Urban high-rise building complex with curved pavilion, roadways, and multi-altitude drone flight passes.",
        "category": "urban",
        "category_label": "(a) Urban area",
        "mesh_type": "High-Rise Towers & Curved Pavilion Complex",
        "anchor": {"lon": 8.5417, "lat": 47.3769, "alt": 450.0},
    },
    {
        "scene_id": "000000000000000000000002",
        "name": "GL3D Scene 2 — Scenic Pagoda Spire",
        "description": "Multi-tiered pagoda temple spire with flared eaves, apex finial, and multi-scale drone orbital capture.",
        "category": "scenic",
        "category_label": "(c) Scenic spot",
        "mesh_type": "Multi-Tiered Pagoda Temple Spire",
        "anchor": {"lon": 110.2902, "lat": 25.2736, "alt": 180.0},
    },
    {
        "scene_id": "000000000000000000000008",
        "name": "GL3D Scene 8 — Rural Terraced Canyon & Dam",
        "description": "Stepped agricultural terraces, mountain gorge elevation relief, and concrete dam formation.",
        "category": "rural",
        "category_label": "(b) Rural area",
        "mesh_type": "Stepped Terraces & Mountain Dam Gorge",
        "anchor": {"lon": 110.1415, "lat": 25.7592, "alt": 620.0},
    },
    {
        "scene_id": "000000000000000000000010",
        "name": "GL3D Scene 16 — Ancient Bronze Ding Artifact",
        "description": "Ancient ceremonial Bronze Ding vessel with four legs, twin rim loop handles, and surface engravings.",
        "category": "object",
        "category_label": "(d) Small object",
        "mesh_type": "Ancient Bronze Ding (Ceremonial Vessel)",
        "anchor": {"lon": 108.9535, "lat": 34.2238, "alt": 410.0},
    },
    {
        "scene_id": "563de9bfba4f35d92bd2d07e",
        "name": "GL3D Altizure Scene — Historic Heritage Site",
        "description": "Historic monument with stone courtyard walls, twin brick kiln chimneys, and snow-covered terrain.",
        "category": "heritage",
        "category_label": "(c) Scenic spot",
        "mesh_type": "Heritage Kiln Towers & Stone Monument",
        "anchor": {"lon": 117.2147, "lat": 29.2941, "alt": 120.0},
    },
    {
        "scene_id": "5644bdac138263b51db9f669",
        "name": "GL3D Altizure Scene — Rural Stepped Landscape",
        "description": "Rural stepped farming landscape with natural drainage channels and terrace contours.",
        "category": "rural",
        "category_label": "(b) Rural area",
        "mesh_type": "Contoured Rural Farmland",
        "anchor": {"lon": 102.7845, "lat": 24.3854, "alt": 1650.0},
    },
    {
        "scene_id": "56d73ba74bd29b8c35abade2",
        "name": "GL3D Altizure Scene — Desert Ridge & Coastal",
        "description": "Desert sand dunes with sharp ridge crests and waterfront shore elevation relief.",
        "category": "coastal",
        "category_label": "(b) Rural area",
        "mesh_type": "Desert Dune Crests & Coastal Relief",
        "anchor": {"lon": 55.1562, "lat": 25.0754, "alt": 25.0},
    },
    {
        "scene_id": "000000000000000000000005",
        "name": "GL3D Scene 5 — Dense Urban Blocks",
        "description": "Dense multi-story commercial and residential blocks with street network.",
        "category": "urban",
        "category_label": "(a) Urban area",
        "mesh_type": "Commercial City Center Grid",
        "anchor": {"lon": 114.1694, "lat": 22.3193, "alt": 35.0},
    },
]


def _count_images_from_list(image_list_content: str) -> int:
    """Count non-empty, non-comment lines in image_list.txt content."""
    return sum(1 for line in image_list_content.strip().split('\n')
               if line.strip() and not line.strip().startswith('#'))


class GL3DProvider(BaseDataProvider):
    """
    Data provider for the GL3D (Geometric Learning with 3D Reconstruction) dataset.
    Catalogs GL3D scenes and provides metadata from the GitHub repository.
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Args:
            data_dir: Local directory containing downloaded GL3D data.
                      If None, uses default data/gl3d/ path.
        """
        if data_dir:
            self.data_dir = data_dir
        else:
            self.data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "gl3d")
            )
        self._image_counts_cache: Dict[str, int] = {}

    @property
    def provider_name(self) -> str:
        return "GL3D (Geometric Learning with 3D Reconstruction)"

    async def search_datasets(
        self, query: str = "", bbox: Optional[List[float]] = None
    ) -> List[DatasetMetadata]:
        """
        Search GL3D scene catalog. Since GL3D uses local SfM coords (no geo-referencing),
        bbox filtering is not applicable — only text query is supported.
        """
        results = []
        q = query.lower().strip()

        for scene in GL3D_SAMPLE_SCENES:
            if q and not (
                q in scene["name"].lower()
                or q in scene["description"].lower()
                or q in scene["scene_id"].lower()
                or q in scene["category"].lower()
            ):
                continue

            image_count = await self._get_image_count(scene["scene_id"])

            results.append(DatasetMetadata(
                provider_id="gl3d",
                dataset_id=scene["scene_id"],
                name=scene["name"],
                description=f"{scene['description']} ({image_count} images)",
                source="GL3D / Altizure — HKUST",
                source_url=f"https://github.com/{GL3D_REPO}",
                doi="https://arxiv.org/abs/1811.10343",
                license="Academic / Research Use",
                attribution="Shen, Luo, Zhou et al. ACCV 2018. 3D reconstructions by Altizure.",
                crs="LOCAL_SFM",
                point_count=image_count * 5000,  # Estimated from depth unprojection
                point_density=None,
                bounds={
                    "min_x": -1.0, "min_y": -1.0,
                    "max_x": 1.0, "max_y": 1.0,
                },
                min_z=None,
                max_z=None,
                format="GL3D_SCENE",
                has_rgb=True,
                has_intensity=False,
                classifications=[],
            ))

        return results

    async def get_metadata(self, dataset_id: str) -> Optional[DatasetMetadata]:
        """Get metadata for a specific GL3D scene."""
        for scene in GL3D_SAMPLE_SCENES:
            if scene["scene_id"] == dataset_id:
                image_count = await self._get_image_count(dataset_id)
                return DatasetMetadata(
                    provider_id="gl3d",
                    dataset_id=dataset_id,
                    name=scene["name"],
                    description=f"{scene['description']} ({image_count} images)",
                    source="GL3D / Altizure — HKUST",
                    source_url=f"https://github.com/{GL3D_REPO}",
                    doi="https://arxiv.org/abs/1811.10343",
                    license="Academic / Research Use",
                    attribution="Shen, Luo, Zhou et al. ACCV 2018.",
                    crs="LOCAL_SFM",
                    point_count=image_count * 5000,
                    bounds={"min_x": -1, "min_y": -1, "max_x": 1, "max_y": 1},
                    format="GL3D_SCENE",
                    has_rgb=True,
                    has_intensity=False,
                    classifications=[],
                )
        return None

    async def fetch_subset(
        self,
        dataset_id: str,
        bbox: List[float],
        output_path: str,
        max_points: int = 500000,
    ) -> str:
        """
        Download GL3D scene data (cameras + image list) from GitHub.
        bbox is ignored for GL3D (no georeferencing).
        """
        scene_dir = os.path.join(self.data_dir, dataset_id)
        os.makedirs(scene_dir, exist_ok=True)
        os.makedirs(os.path.join(scene_dir, "geolabel"), exist_ok=True)

        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            # Download image_list.txt
            img_list_url = f"{GL3D_MASTER_RAW}/data/{dataset_id}/image_list.txt"
            try:
                resp = await client.get(img_list_url)
                if resp.status_code == 200:
                    img_list_path = os.path.join(scene_dir, "image_list.txt")
                    with open(img_list_path, 'w') as f:
                        f.write(resp.text)
                    logger.info(f"Downloaded image_list.txt for scene {dataset_id}")
            except Exception as e:
                logger.warning(f"Failed to download image_list.txt: {e}")

            # Download cameras.txt (from v2 branch geolabel)
            for branch in ["v2", "master"]:
                cam_url = f"{GL3D_RAW_BASE}/{branch}/data/{dataset_id}/geolabel/cameras.txt"
                try:
                    resp = await client.get(cam_url)
                    if resp.status_code == 200 and len(resp.text.strip()) > 10:
                        cam_path = os.path.join(scene_dir, "geolabel", "cameras.txt")
                        with open(cam_path, 'w') as f:
                            f.write(resp.text)
                        logger.info(f"Downloaded cameras.txt for scene {dataset_id} ({branch})")
                        break
                except Exception as e:
                    logger.warning(f"Failed to download cameras.txt ({branch}): {e}")

        return scene_dir

    async def _get_image_count(self, scene_id: str) -> int:
        """Get image count for a scene, with caching."""
        if scene_id in self._image_counts_cache:
            return self._image_counts_cache[scene_id]

        # Check local data first
        local_list = os.path.join(self.data_dir, scene_id, "image_list.txt")
        if os.path.exists(local_list):
            with open(local_list, 'r') as f:
                count = _count_images_from_list(f.read())
                self._image_counts_cache[scene_id] = count
                return count

        # Fetch from GitHub
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                url = f"{GL3D_MASTER_RAW}/data/{scene_id}/image_list.txt"
                resp = await client.get(url)
                if resp.status_code == 200:
                    count = _count_images_from_list(resp.text)
                    self._image_counts_cache[scene_id] = count
                    return count
        except Exception:
            pass

        # Default estimate
        self._image_counts_cache[scene_id] = 0
        return 0

    def get_scene_data_dir(self, scene_id: str) -> str:
        """Get local directory path for a GL3D scene."""
        return os.path.join(self.data_dir, scene_id)

    def list_local_scenes(self) -> List[str]:
        """List scene IDs that have been downloaded locally."""
        if not os.path.isdir(self.data_dir):
            return []
        return [
            d for d in os.listdir(self.data_dir)
            if os.path.isdir(os.path.join(self.data_dir, d))
            and os.path.exists(os.path.join(self.data_dir, d, "image_list.txt"))
        ]
