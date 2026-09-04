"""
Base Data Provider Abstract Class
Defines the standard interface for geospatial LiDAR and raster data providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class DatasetMetadata(BaseModel):
    provider_id: str
    dataset_id: str
    name: str
    description: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    doi: Optional[str] = None
    license: Optional[str] = "Open / Check Source"
    attribution: Optional[str] = None
    crs: str
    point_count: Optional[int] = None
    point_density: Optional[float] = None
    bounds: Dict[str, float]  # min_x, min_y, max_x, max_y or WGS84 bounds
    min_z: Optional[float] = None
    max_z: Optional[float] = None
    format: str = "LAZ"
    has_rgb: bool = False
    has_intensity: bool = True
    classifications: List[int] = []


class BaseDataProvider(ABC):
    """Abstract base class for all dataset sources."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the data provider (e.g. OpenTopography, USGS 3DEP)."""
        pass

    @abstractmethod
    async def search_datasets(self, query: str = "", bbox: Optional[List[float]] = None) -> List[DatasetMetadata]:
        """Search available datasets matching query or geographic bounding box."""
        pass

    @abstractmethod
    async def get_metadata(self, dataset_id: str) -> Optional[DatasetMetadata]:
        """Retrieve detailed metadata for a specific dataset identifier."""
        pass

    @abstractmethod
    async def fetch_subset(
        self,
        dataset_id: str,
        bbox: List[float],
        output_path: str,
        max_points: int = 500000
    ) -> str:
        """Download or extract an AOI subset to the given local output path."""
        pass
