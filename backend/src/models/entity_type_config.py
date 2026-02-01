"""EntityTypeConfig model for per-entity-type configuration."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.database import Base

if TYPE_CHECKING:
    from backend.src.models.config import AnonymizationConfig


class EntityTypeConfig(Base):
    """Stores per-entity-type configuration within a parent AnonymizationConfig.

    Valid strategies: replace, mask, hash, redact
    """

    __tablename__ = "entity_type_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("anonymization_configs.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    strategy: Mapped[str] = mapped_column(String(20), nullable=False, default="replace")
    strategy_params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationship to parent config
    config: Mapped["AnonymizationConfig"] = relationship(
        "AnonymizationConfig", back_populates="entity_types"
    )

    __table_args__ = (
        # Each entity type can only appear once per config
        Index("idx_config_entity", "config_id", "entity_type", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<EntityTypeConfig(id={self.id}, entity_type={self.entity_type}, "
            f"enabled={self.enabled}, strategy={self.strategy})>"
        )
