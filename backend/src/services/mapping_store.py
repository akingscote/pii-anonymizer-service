"""Mapping store service for managing PII-to-substitute mappings."""

import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from backend.src.models import PIIMapping


class MappingStore:
    """Service for managing PII-to-substitute mappings in the database.

    Provides consistent substitution by looking up existing mappings
    before generating new ones.
    """

    def __init__(self, db: Session):
        """Initialize with database session.

        Args:
            db: SQLAlchemy session
        """
        self._db = db

    @staticmethod
    def compute_hash(original_value: str, entity_type: str) -> str:
        """Compute SHA-256 hash of original value combined with entity type.

        The entity type is included to prevent different entity types
        with the same value from colliding.

        Args:
            original_value: The original PII value
            entity_type: The Presidio entity type

        Returns:
            64-character hex string (SHA-256)
        """
        combined = f"{original_value}|{entity_type}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def get_substitute(self, original_value: str, entity_type: str) -> str | None:
        """Look up an existing substitute for a PII value.

        Args:
            original_value: The original PII value
            entity_type: The Presidio entity type

        Returns:
            The substitute value if found, None otherwise
        """
        original_hash = self.compute_hash(original_value, entity_type)

        mapping = (
            self._db.query(PIIMapping)
            .filter(
                PIIMapping.original_hash == original_hash,
                PIIMapping.entity_type == entity_type,
            )
            .first()
        )

        return mapping.substitute if mapping else None

    def create_mapping(
        self, original_value: str, substitute: str, entity_type: str
    ) -> PIIMapping:
        """Create a new PII-to-substitute mapping.

        Args:
            original_value: The original PII value
            substitute: The generated substitute value
            entity_type: The Presidio entity type

        Returns:
            The created PIIMapping object
        """
        original_hash = self.compute_hash(original_value, entity_type)
        now = datetime.utcnow()

        mapping = PIIMapping(
            original_hash=original_hash,
            substitute=substitute,
            entity_type=entity_type,
            first_seen=now,
            last_used=now,
            substitution_count=1,
        )

        self._db.add(mapping)
        self._db.flush()  # Ensure ID is assigned

        return mapping

    def increment_count(self, original_value: str, entity_type: str) -> int:
        """Increment the substitution count for an existing mapping.

        Args:
            original_value: The original PII value
            entity_type: The Presidio entity type

        Returns:
            The new substitution count
        """
        original_hash = self.compute_hash(original_value, entity_type)

        mapping = (
            self._db.query(PIIMapping)
            .filter(
                PIIMapping.original_hash == original_hash,
                PIIMapping.entity_type == entity_type,
            )
            .first()
        )

        if mapping:
            mapping.substitution_count += 1
            mapping.last_used = datetime.utcnow()
            self._db.flush()
            return mapping.substitution_count

        return 0

    def get_or_create(
        self, original_value: str, entity_type: str, generator_func
    ) -> tuple[str, bool]:
        """Get existing substitute or create new one.

        This is the main entry point for consistent substitution.

        Args:
            original_value: The original PII value
            entity_type: The Presidio entity type
            generator_func: Function to generate a new substitute if needed.
                           Called as generator_func(entity_type, original_value)

        Returns:
            Tuple of (substitute_value, is_new_mapping)
        """
        # Try to get existing mapping
        existing = self.get_substitute(original_value, entity_type)
        if existing:
            self.increment_count(original_value, entity_type)
            return existing, False

        # Generate new substitute and create mapping
        # Pass both entity_type and original_value for smart generation
        substitute = generator_func(entity_type, original_value)
        self.create_mapping(original_value, substitute, entity_type)
        return substitute, True

    def list_all(self, limit: int = 1000, offset: int = 0) -> tuple[list[PIIMapping], int]:
        """List all PII mappings with pagination.

        Args:
            limit: Maximum number of mappings to return
            offset: Number of mappings to skip

        Returns:
            Tuple of (list of mappings, total count)
        """
        total = self._db.query(PIIMapping).count()
        mappings = (
            self._db.query(PIIMapping)
            .order_by(PIIMapping.first_seen.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return mappings, total

    def get_by_id(self, mapping_id: int) -> PIIMapping | None:
        """Get a mapping by its ID.

        Args:
            mapping_id: The mapping ID

        Returns:
            The mapping if found, None otherwise
        """
        return self._db.query(PIIMapping).filter(PIIMapping.id == mapping_id).first()

    def update_substitute(self, mapping_id: int, new_substitute: str) -> PIIMapping | None:
        """Update the substitute value for a mapping.

        Args:
            mapping_id: The mapping ID
            new_substitute: The new substitute value

        Returns:
            The updated mapping if found, None otherwise
        """
        mapping = self.get_by_id(mapping_id)
        if mapping:
            mapping.substitute = new_substitute
            self._db.flush()
        return mapping

    def delete_all(self) -> int:
        """Delete all PII mappings.

        Returns:
            Number of mappings deleted
        """
        count = self._db.query(PIIMapping).delete()
        self._db.flush()
        return count

    def delete_by_id(self, mapping_id: int) -> bool:
        """Delete a specific mapping by ID.

        Args:
            mapping_id: The mapping ID

        Returns:
            True if deleted, False if not found
        """
        result = self._db.query(PIIMapping).filter(PIIMapping.id == mapping_id).delete()
        self._db.flush()
        return result > 0

    def list_by_timestamp(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        entity_type: str | None = None,
    ) -> list[PIIMapping]:
        """List mappings filtered by timestamp range.

        Args:
            since: Only include mappings last used after this time
            until: Only include mappings last used before this time
            entity_type: Filter by entity type (optional)

        Returns:
            List of matching mappings ordered by last_used
        """
        query = self._db.query(PIIMapping)

        if since:
            query = query.filter(PIIMapping.last_used >= since)
        if until:
            query = query.filter(PIIMapping.last_used <= until)
        if entity_type:
            query = query.filter(PIIMapping.entity_type == entity_type)

        return query.order_by(PIIMapping.last_used.desc()).all()
