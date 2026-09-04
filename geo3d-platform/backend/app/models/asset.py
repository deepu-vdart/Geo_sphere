import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, BigInteger, DateTime, ForeignKey, func, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )

    # Asset types: terrain_mesh | dtm | dsm | point_cloud_optimized | tileset
    #              orthophoto | textured_mesh | 3dtiles | hillshade | thumbnail
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # File location
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_format: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Web delivery URL (relative to static server or CDN)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extra metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="assets")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Asset id={self.id} type={self.asset_type!r} name={self.name!r}>"
