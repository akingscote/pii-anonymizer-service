"""Statistics service for aggregate substitution statistics."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.src.models import PIIMapping


@dataclass
class EntityTypeStats:
    """Statistics for a single entity type."""

    entity_type: str
    unique_values: int
    total_substitutions: int


@dataclass
class SubstituteDetail:
    """Detail for a substitute value."""

    substitute: str
    count: int
    first_seen: datetime


@dataclass
class OverallStats:
    """Overall statistics."""

    total_mappings: int
    total_substitutions: int
    by_entity_type: list[EntityTypeStats]
    oldest_mapping: datetime | None
    newest_mapping: datetime | None


class StatsService:
    """Service for querying substitution statistics."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self._db = db

    def get_overall_stats(self) -> OverallStats:
        """Get aggregate statistics across all entity types."""
        # Total mappings and substitutions
        totals = self._db.query(
            func.count(PIIMapping.id).label("total_mappings"),
            func.sum(PIIMapping.substitution_count).label("total_substitutions"),
            func.min(PIIMapping.first_seen).label("oldest"),
            func.max(PIIMapping.first_seen).label("newest"),
        ).first()

        total_mappings = totals.total_mappings or 0
        total_substitutions = totals.total_substitutions or 0
        oldest = totals.oldest
        newest = totals.newest

        # Stats by entity type
        by_type = (
            self._db.query(
                PIIMapping.entity_type,
                func.count(PIIMapping.id).label("unique_values"),
                func.sum(PIIMapping.substitution_count).label("total_substitutions"),
            )
            .group_by(PIIMapping.entity_type)
            .all()
        )

        entity_stats = [
            EntityTypeStats(
                entity_type=row.entity_type,
                unique_values=row.unique_values,
                total_substitutions=row.total_substitutions or 0,
            )
            for row in by_type
        ]

        return OverallStats(
            total_mappings=total_mappings,
            total_substitutions=total_substitutions,
            by_entity_type=entity_stats,
            oldest_mapping=oldest,
            newest_mapping=newest,
        )

    def get_stats_by_entity_type(self, entity_type: str) -> tuple[EntityTypeStats, list[SubstituteDetail]] | None:
        """Get detailed statistics for a specific entity type.

        Returns:
            Tuple of (EntityTypeStats, list of SubstituteDetail) or None if not found
        """
        # Get aggregate stats
        agg = (
            self._db.query(
                func.count(PIIMapping.id).label("unique_values"),
                func.sum(PIIMapping.substitution_count).label("total_substitutions"),
            )
            .filter(PIIMapping.entity_type == entity_type)
            .first()
        )

        if not agg or not agg.unique_values:
            return None

        stats = EntityTypeStats(
            entity_type=entity_type,
            unique_values=agg.unique_values,
            total_substitutions=agg.total_substitutions or 0,
        )

        # Get substitute details (limited to top 100 by count)
        substitutes = (
            self._db.query(PIIMapping)
            .filter(PIIMapping.entity_type == entity_type)
            .order_by(PIIMapping.substitution_count.desc())
            .limit(100)
            .all()
        )

        details = [
            SubstituteDetail(
                substitute=m.substitute,
                count=m.substitution_count,
                first_seen=m.first_seen,
            )
            for m in substitutes
        ]

        return stats, details

    def export_stats_csv(self) -> str:
        """Export statistics as CSV format.

        Returns:
            CSV string with headers
        """
        lines = ["entity_type,unique_values,total_substitutions"]

        stats = self.get_overall_stats()
        for entity_stat in stats.by_entity_type:
            lines.append(
                f"{entity_stat.entity_type},{entity_stat.unique_values},{entity_stat.total_substitutions}"
            )

        # Add totals row
        lines.append(f"TOTAL,{stats.total_mappings},{stats.total_substitutions}")

        return "\n".join(lines)
