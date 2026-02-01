"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.src.api.schemas import HealthResponse
from backend.src.database import get_db
from backend.src.models import PIIMapping

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Check service health and database connectivity."""
    try:
        # Test database connection and get mappings count
        mappings_count = db.query(func.count(PIIMapping.id)).scalar() or 0
        database_connected = True
    except Exception:
        mappings_count = 0
        database_connected = False

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database_connected=database_connected,
        mappings_count=mappings_count,
    )
