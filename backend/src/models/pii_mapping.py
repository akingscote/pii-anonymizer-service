"""PIIMapping model for storing PII-to-substitute mappings."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.database import Base


class PIIMapping(Base):
    """Stores the mapping between original PII values (as hashes) and their substitutes.

    Original PII is NEVER stored in plaintext - only SHA-256 hashes.
    Hash is computed as SHA-256(original_value + entity_type) to prevent rainbow table attacks.
    """

    __tablename__ = "pii_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    substitute: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_used: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    substitution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        # Primary lookup path - must be unique per entity type
        Index("idx_lookup", "original_hash", "entity_type", unique=True),
        # For statistics queries
        Index("idx_entity_type", "entity_type"),
        # For timestamp-based export queries
        Index("idx_last_used", "last_used"),
    )

    def __repr__(self) -> str:
        return (
            f"<PIIMapping(id={self.id}, entity_type={self.entity_type}, "
            f"substitute={self.substitute[:20]}..., count={self.substitution_count})>"
        )
