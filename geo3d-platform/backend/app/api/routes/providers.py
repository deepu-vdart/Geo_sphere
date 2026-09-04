"""
Data Providers REST API Endpoints
Provides discovery and metadata lookup across OpenTopography and USGS 3DEP public LiDAR catalogs.
"""

from typing import List, Optional
from fastapi import APIRouter, Query
from app.providers import registry
from app.providers.base import DatasetMetadata

router = APIRouter(prefix="/providers", tags=["Data Providers"])


@router.get("")
async def list_providers():
    """List available remote LiDAR and geospatial data providers."""
    return registry.list_providers()


@router.get("/search", response_model=List[DatasetMetadata])
async def search_datasets(
    q: str = Query("", description="Keyword search query"),
    min_lon: Optional[float] = None,
    min_lat: Optional[float] = None,
    max_lon: Optional[float] = None,
    max_lat: Optional[float] = None,
):
    """Search datasets across OpenTopography and USGS 3DEP catalogs."""
    bbox = None
    if all(v is not None for v in [min_lon, min_lat, max_lon, max_lat]):
        bbox = [min_lon, min_lat, max_lon, max_lat]
    return await registry.search_all(query=q, bbox=bbox)


@router.get("/{provider_id}/{dataset_id}", response_model=Optional[DatasetMetadata])
async def get_dataset_metadata(provider_id: str, dataset_id: str):
    """Get metadata for a specific remote dataset in a provider catalog."""
    provider = registry.get_provider(provider_id)
    if not provider:
        return None
    return await provider.get_metadata(dataset_id)
