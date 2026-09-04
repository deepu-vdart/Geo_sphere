import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, DateTime, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Coordinate reference system
    crs: Mapped[Optional[str]] = mapped_column(String(64), default="EPSG:4326")

    # Bounding box as PostGIS geometry (WGS84 polygon)
    bounding_box: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326), nullable=True
    )

    # Center point
    center_point: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )

    # Elevation range
    min_elevation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_elevation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

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
    datasets: Mapped[list["Dataset"]] = relationship(  # noqa: F821
        "Dataset", back_populates="project", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(  # noqa: F821
        "ProcessingJob", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"
