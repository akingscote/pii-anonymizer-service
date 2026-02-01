"""AuditLog model for recording anonymization operations."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.database import Base


class AuditLog(Base):
    """Records each anonymization operation for compliance and debugging.

    NEVER logs actual PII values or substitutes.
    Log entries are append-only (no updates or deletes).
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_types_processed: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_length: Mapped[int] = mapped_column(Integer, nullable=False)
    entities_detected: Mapped[int] = mapped_column(Integer, nullable=False)
    entities_anonymized: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        # For querying by operation type
        Index("idx_operation", "operation"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, operation={self.operation}, "
            f"detected={self.entities_detected}, anonymized={self.entities_anonymized})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "entity_types_processed": self.entity_types_processed,
            "input_length": self.input_length,
            "entities_detected": self.entities_detected,
            "entities_anonymized": self.entities_anonymized,
            "duration_ms": self.duration_ms,
        }
