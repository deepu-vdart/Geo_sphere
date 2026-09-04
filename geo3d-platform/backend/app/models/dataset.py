import uuid
import os
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, DateTime, BigInteger, ForeignKey, func, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dataset type: point_cloud | raster | vector | image | mesh
    dataset_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # File format: las, laz, geotiff, dem, dsm, dtm, geojson, shp, ply, obj, jpg, png
    file_format: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Storage
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # CRS
    crs: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    crs_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Spatial extent (PostGIS)
    extent: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326), nullable=True
    )

    # Elevation range
    min_z: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_z: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Point cloud specifics
    point_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    point_density: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Raster specifics
    resolution_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raster_width: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    raster_height: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    band_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Extra metadata as JSON
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Processing status
    processing_status: Mapped[str] = mapped_column(String(32), default="pending")
    validation_errors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(32), default="active")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="datasets")  # noqa: F821
    assets: Mapped[list["Asset"]] = relationship(  # noqa: F821
        "Asset", back_populates="dataset", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(  # noqa: F821
        "ProcessingJob", back_populates="dataset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} name={self.name!r} type={self.dataset_type!r}>"
