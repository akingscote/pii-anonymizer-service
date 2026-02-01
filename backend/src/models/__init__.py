"""Database models package."""

from backend.src.models.audit_log import AuditLog
from backend.src.models.config import AnonymizationConfig
from backend.src.models.entity_type_config import EntityTypeConfig
from backend.src.models.pii_mapping import PIIMapping

__all__ = ["PIIMapping", "AnonymizationConfig", "EntityTypeConfig", "AuditLog"]


def verify_indexes():
    """Verify that all required indexes exist.

    Call this after database initialization to ensure
    performance-critical indexes are in place.
    """
    from sqlalchemy import inspect
    from backend.src.database import engine

    inspector = inspect(engine)

    expected_indexes = {
        "pii_mappings": ["idx_lookup", "idx_entity_type"],
        "entity_type_configs": ["idx_config_entity"],
        "audit_logs": ["ix_audit_logs_timestamp", "idx_operation"],
    }

    missing = []
    for table, indexes in expected_indexes.items():
        try:
            existing = {idx["name"] for idx in inspector.get_indexes(table)}
            for idx in indexes:
                if idx not in existing:
                    missing.append(f"{table}.{idx}")
        except Exception:
            pass  # Table might not exist yet

    if missing:
        import logging
        logging.warning(f"Missing database indexes: {missing}")

    return len(missing) == 0
