"""Statistics API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.src.api.schemas import (
    EntityTypeStats,
    EntityTypeStatsResponse,
    StatsResponse,
    SubstituteDetail,
)
from backend.src.database import get_db
from backend.src.services.stats_service import StatsService

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)) -> StatsResponse:
    """Get aggregate statistics about all PII mappings."""
    service = StatsService(db)
    stats = service.get_overall_stats()

    return StatsResponse(
        total_mappings=stats.total_mappings,
        total_substitutions=stats.total_substitutions,
        by_entity_type=[
            EntityTypeStats(
                entity_type=s.entity_type,
                unique_values=s.unique_values,
                total_substitutions=s.total_substitutions,
            )
            for s in stats.by_entity_type
        ],
        oldest_mapping=stats.oldest_mapping,
        newest_mapping=stats.newest_mapping,
    )


@router.get("/stats/export")
def export_stats(
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
):
    """Export substitution statistics for compliance reporting.

    Supports CSV and JSON formats.
    """
    service = StatsService(db)

    if format == "csv":
        csv_content = service.export_stats_csv()
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pii_stats.csv"},
        )
    else:
        # JSON format - return same as /stats
        stats = service.get_overall_stats()
        return StatsResponse(
            total_mappings=stats.total_mappings,
            total_substitutions=stats.total_substitutions,
            by_entity_type=[
                EntityTypeStats(
                    entity_type=s.entity_type,
                    unique_values=s.unique_values,
                    total_substitutions=s.total_substitutions,
                )
                for s in stats.by_entity_type
            ],
            oldest_mapping=stats.oldest_mapping,
            newest_mapping=stats.newest_mapping,
        )


@router.get("/stats/{entity_type}", response_model=EntityTypeStatsResponse)
def get_stats_by_entity_type(
    entity_type: str,
    db: Session = Depends(get_db),
) -> EntityTypeStatsResponse:
    """Get detailed statistics for a specific entity type."""
    service = StatsService(db)
    result = service.get_stats_by_entity_type(entity_type)

    if result is None:
        raise HTTPException(
            status_code=404, detail=f"No mappings found for entity type: {entity_type}"
        )

    stats, details = result

    return EntityTypeStatsResponse(
        entity_type=stats.entity_type,
        unique_values=stats.unique_values,
        total_substitutions=stats.total_substitutions,
        substitutes=[
            SubstituteDetail(
                substitute=d.substitute,
                count=d.count,
                first_seen=d.first_seen,
            )
            for d in details
        ],
    )
