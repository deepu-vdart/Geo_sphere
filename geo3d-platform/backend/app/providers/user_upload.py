"""
User Upload Data Provider
Handles local and uploaded LAS / LAZ / GeoTIFF files.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from app.providers.base import BaseDataProvider, DatasetMetadata

logger = logging.getLogger(__name__)


class UserUploadProvider(BaseDataProvider):
    """Provider for direct user LAS/LAZ/GeoTIFF uploads."""

    @property
    def provider_name(self) -> str:
        return "User Upload"

    async def search_datasets(self, query: str = "", bbox: Optional[List[float]] = None) -> List[DatasetMetadata]:
        return []

    async def get_metadata(self, dataset_id: str) -> Optional[DatasetMetadata]:
        return None

    async def fetch_subset(
        self,
        dataset_id: str,
        bbox: List[float],
        output_path: str,
        max_points: int = 500000
    ) -> str:
        return output_path
