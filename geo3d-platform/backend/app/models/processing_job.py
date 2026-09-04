import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, func, JSON, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )

    # Job classification
    # Types: ingest | validate | process_pointcloud | process_raster | generate_terrain
    #        generate_mesh | tile | analyze | ai_classify | odm_process
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Status: QUEUED | RUNNING | COMPLETED | FAILED | CANCELLED
    status: Mapped[str] = mapped_column(String(32), default="QUEUED")

    # Progress 0-100
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # Input parameters as JSON
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Output asset IDs and info
    output_assets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Logging
    log_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")  # noqa: F821
    dataset: Mapped[Optional["Dataset"]] = relationship("Dataset", back_populates="jobs")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ProcessingJob id={self.id} type={self.job_type!r} status={self.status!r}>"
