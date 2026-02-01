"""Mappings management API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.src.api.schemas import (
    DeleteMappingsResponse,
    MappingExportResponse,
    MappingResponse,
    MappingsListResponse,
    MappingUpdateRequest,
)
from backend.src.database import get_db
from backend.src.services.mapping_store import MappingStore

router = APIRouter()


@router.get("/mappings", response_model=MappingsListResponse)
def list_mappings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> MappingsListResponse:
    """List all PII mappings with pagination."""
    store = MappingStore(db)
    mappings, total = store.list_all(limit=limit, offset=offset)

    return MappingsListResponse(
        mappings=[
            MappingResponse(
                id=m.id,
                original_hash=m.original_hash,
                substitute=m.substitute,
                entity_type=m.entity_type,
                first_seen=m.first_seen,
                last_used=m.last_used,
                substitution_count=m.substitution_count,
            )
            for m in mappings
        ],
        total=total,
    )


@router.get("/mappings/export", response_model=MappingExportResponse)
def export_mappings(
    since: datetime | None = Query(None, description="Export mappings used since this time (ISO format)"),
    until: datetime | None = Query(None, description="Export mappings used until this time (ISO format)"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    format: str = Query("json", pattern="^(json|csv)$", description="Export format"),
    db: Session = Depends(get_db),
):
    """Export mappings filtered by timestamp and optionally by entity type."""
    store = MappingStore(db)
    mappings = store.list_by_timestamp(since=since, until=until, entity_type=entity_type)

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "original_hash", "substitute", "entity_type", "first_seen", "last_used", "substitution_count"])
        for m in mappings:
            writer.writerow([
                m.id,
                m.original_hash,
                m.substitute,
                m.entity_type,
                m.first_seen.isoformat(),
                m.last_used.isoformat(),
                m.substitution_count,
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=mappings_export.csv"},
        )

    return MappingExportResponse(
        mappings=[
            MappingResponse(
                id=m.id,
                original_hash=m.original_hash,
                substitute=m.substitute,
                entity_type=m.entity_type,
                first_seen=m.first_seen,
                last_used=m.last_used,
                substitution_count=m.substitution_count,
            )
            for m in mappings
        ],
        export_params={
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
            "entity_type": entity_type,
        },
        total=len(mappings),
    )


@router.get("/mappings/{mapping_id}", response_model=MappingResponse)
def get_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
) -> MappingResponse:
    """Get a specific mapping by ID."""
    store = MappingStore(db)
    mapping = store.get_by_id(mapping_id)

    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    return MappingResponse(
        id=mapping.id,
        original_hash=mapping.original_hash,
        substitute=mapping.substitute,
        entity_type=mapping.entity_type,
        first_seen=mapping.first_seen,
        last_used=mapping.last_used,
        substitution_count=mapping.substitution_count,
    )


@router.put("/mappings/{mapping_id}", response_model=MappingResponse)
def update_mapping(
    mapping_id: int,
    request: MappingUpdateRequest,
    db: Session = Depends(get_db),
) -> MappingResponse:
    """Update a mapping's substitute value."""
    store = MappingStore(db)
    mapping = store.update_substitute(mapping_id, request.substitute)

    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    db.commit()

    return MappingResponse(
        id=mapping.id,
        original_hash=mapping.original_hash,
        substitute=mapping.substitute,
        entity_type=mapping.entity_type,
        first_seen=mapping.first_seen,
        last_used=mapping.last_used,
        substitution_count=mapping.substitution_count,
    )


@router.delete("/mappings", response_model=DeleteMappingsResponse)
def delete_all_mappings(
    db: Session = Depends(get_db),
) -> DeleteMappingsResponse:
    """Delete all PII mappings. Use with caution!"""
    store = MappingStore(db)
    count = store.delete_all()
    db.commit()

    return DeleteMappingsResponse(
        deleted_count=count,
        message=f"Successfully deleted {count} mappings",
    )


@router.delete("/mappings/{mapping_id}", response_model=DeleteMappingsResponse)
def delete_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
) -> DeleteMappingsResponse:
    """Delete a specific mapping by ID."""
    store = MappingStore(db)
    deleted = store.delete_by_id(mapping_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping not found")

    db.commit()

    return DeleteMappingsResponse(
        deleted_count=1,
        message="Successfully deleted mapping",
    )
