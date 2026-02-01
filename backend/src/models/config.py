"""AnonymizationConfig model for storing user configuration."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.database import Base

if TYPE_CHECKING:
    from backend.src.models.entity_type_config import EntityTypeConfig


class AnonymizationConfig(Base):
    """Stores the user's anonymization configuration settings.

    Only one config can have is_active=TRUE at a time.
    """

    __tablename__ = "anonymization_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en_US")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship to entity type configurations
    entity_types: Mapped[list["EntityTypeConfig"]] = relationship(
        "EntityTypeConfig", back_populates="config", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<AnonymizationConfig(id={self.id}, name={self.name}, "
            f"active={self.is_active}, threshold={self.confidence_threshold})>"
        )
