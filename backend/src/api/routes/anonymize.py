"""Anonymization API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.src.api.schemas import (
    AnonymizeMetadata,
    AnonymizeRequest,
    AnonymizeResponse,
    BatchAnonymizeRequest,
    BatchAnonymizeResponse,
    BatchMetadata,
    Substitution,
)
from backend.src.database import get_db
from backend.src.services.anonymizer import PIIAnonymizer
from backend.src.services.config_service import ConfigService

router = APIRouter()


def _get_config_defaults(db: Session) -> tuple[list[str] | None, float, str]:
    """Get default entity types, threshold, and locale from active config."""
    service = ConfigService(db)
    config = service.get_active_config()

    if config:
        enabled_types = service.get_enabled_entity_types()
        return enabled_types if enabled_types else None, config.confidence_threshold, config.locale

    return None, 0.7, "en_US"


def _convert_result_to_response(result) -> AnonymizeResponse:
    """Convert AnonymizationResult to API response."""
    return AnonymizeResponse(
        anonymized_text=result.anonymized_text,
        substitutions=[
            Substitution(
                start=s.start,
                end=s.end,
                entity_type=s.entity_type,
                original_length=s.original_length,
                substitute=s.substitute,
            )
            for s in result.substitutions
        ],
        metadata=AnonymizeMetadata(
            entities_detected=result.entities_detected,
            entities_anonymized=result.entities_anonymized,
            new_mappings_created=result.new_mappings_created,
            existing_mappings_used=result.existing_mappings_used,
            processing_time_ms=result.processing_time_ms,
        ),
    )


@router.post("/anonymize", response_model=AnonymizeResponse)
def anonymize_text(
    request: AnonymizeRequest,
    db: Session = Depends(get_db),
) -> AnonymizeResponse:
    """Detect and anonymize PII in text.

    Uses consistent substitution - the same PII value always maps to the same substitute.
    If entity_types or confidence_threshold are not specified, uses values from active config.
    """
    from backend.src.generators.synthetic import get_generator

    try:
        # Get defaults from config if not specified in request
        default_types, default_threshold, locale = _get_config_defaults(db)

        entity_types = request.entity_types if request.entity_types is not None else default_types
        threshold = request.confidence_threshold if request.confidence_threshold is not None else default_threshold

        # Ensure generator uses the configured locale
        generator = get_generator(locale=locale)
        generator.set_locale(locale)

        anonymizer = PIIAnonymizer(db=db, generator=generator)
        result = anonymizer.anonymize(
            text=request.text,
            entity_types=entity_types,
            confidence_threshold=threshold,
        )
        return _convert_result_to_response(result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anonymization failed: {str(e)}")


@router.post("/anonymize/batch", response_model=BatchAnonymizeResponse)
def batch_anonymize_texts(
    request: BatchAnonymizeRequest,
    db: Session = Depends(get_db),
) -> BatchAnonymizeResponse:
    """Anonymize multiple texts in a single request.

    More efficient than multiple single requests due to reduced overhead.
    If entity_types or confidence_threshold are not specified, uses values from active config.
    """
    from backend.src.generators.synthetic import get_generator

    if not request.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")

    if len(request.texts) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 texts per batch")

    try:
        # Get defaults from config if not specified in request
        default_types, default_threshold, locale = _get_config_defaults(db)

        entity_types = request.entity_types if request.entity_types is not None else default_types
        threshold = request.confidence_threshold if request.confidence_threshold is not None else default_threshold

        # Ensure generator uses the configured locale
        generator = get_generator(locale=locale)
        generator.set_locale(locale)

        anonymizer = PIIAnonymizer(db=db, generator=generator)
        results, total_detected, total_time = anonymizer.anonymize_batch(
            texts=request.texts,
            entity_types=entity_types,
            confidence_threshold=threshold,
        )

        return BatchAnonymizeResponse(
            results=[_convert_result_to_response(r) for r in results],
            batch_metadata=BatchMetadata(
                total_texts=len(request.texts),
                total_entities_detected=total_detected,
                total_processing_time_ms=total_time,
            ),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch anonymization failed: {str(e)}")
