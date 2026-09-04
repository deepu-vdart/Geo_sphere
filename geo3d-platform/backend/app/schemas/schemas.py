import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# ─── Project Schemas ────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location_name: Optional[str] = None
    crs: Optional[str] = "EPSG:4326"


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    location_name: Optional[str] = None
    crs: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    location_name: Optional[str]
    crs: Optional[str]
    min_elevation: Optional[float]
    max_elevation: Optional[float]
    status: str
    created_at: datetime
    updated_at: datetime
    dataset_count: Optional[int] = 0


class ProjectListResponse(BaseModel):
    total: int
    projects: list[ProjectResponse]


# ─── Dataset Schemas ─────────────────────────────────────────────────────────

class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    dataset_type: str  # point_cloud | raster | vector | image | mesh
    file_format: Optional[str] = None


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str]
    dataset_type: str
    file_format: Optional[str]
    file_size_bytes: Optional[int]
    original_filename: Optional[str]
    crs: Optional[str]
    min_z: Optional[float]
    max_z: Optional[float]
    point_count: Optional[int]
    point_density: Optional[float]
    resolution_x: Optional[float]
    resolution_y: Optional[float]
    raster_width: Optional[int]
    raster_height: Optional[int]
    processing_status: str
    status: str
    metadata_json: Optional[dict]
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    total: int
    datasets: list[DatasetResponse]


# ─── Processing Job Schemas ──────────────────────────────────────────────────

class JobCreate(BaseModel):
    job_type: str
    parameters: Optional[dict[str, Any]] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    dataset_id: Optional[uuid.UUID]
    job_type: str
    status: str
    progress: int
    parameters: Optional[dict]
    output_assets: Optional[list]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    created_at: datetime


# ─── Asset Schemas ───────────────────────────────────────────────────────────

class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    asset_type: str
    name: str
    description: Optional[str]
    file_size_bytes: Optional[int]
    file_format: Optional[str]
    url: Optional[str]
    metadata_json: Optional[dict]
    created_at: datetime


# ─── Health Schema ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    timestamp: datetime


# ─── Error Schema ────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
