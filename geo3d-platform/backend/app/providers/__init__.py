"""
Data Providers Registry
Provides discovery and unified access to OpenTopography, USGS 3DEP, User Upload, and GL3D datasets.
"""

from typing import Dict, List, Optional
from app.providers.base import BaseDataProvider, DatasetMetadata
from app.providers.opentopography import OpenTopographyProvider
from app.providers.usgs_3dep import USGS3DEPProvider
from app.providers.user_upload import UserUploadProvider
from app.providers.gl3d import GL3DProvider


class ProviderRegistry:
    """Registry managing all active LiDAR, raster, and photogrammetry data sources."""

    def __init__(self):
        self._providers: Dict[str, BaseDataProvider] = {
            "opentopography": OpenTopographyProvider(),
            "usgs_3dep": USGS3DEPProvider(),
            "user_upload": UserUploadProvider(),
            "gl3d": GL3DProvider(),
        }

    def get_provider(self, provider_id: str) -> Optional[BaseDataProvider]:
        return self._providers.get(provider_id)

    def list_providers(self) -> List[Dict[str, str]]:
        return [
            {"id": pid, "name": provider.provider_name}
            for pid, provider in self._providers.items()
        ]

    async def search_all(self, query: str = "", bbox: Optional[List[float]] = None) -> List[DatasetMetadata]:
        all_results = []
        for provider in self._providers.values():
            try:
                results = await provider.search_datasets(query=query, bbox=bbox)
                all_results.extend(results)
            except Exception:
                pass
        return all_results


registry = ProviderRegistry()
