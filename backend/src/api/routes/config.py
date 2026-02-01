"""Configuration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.src.api.schemas import (
    ConfigResponse,
    ConfigUpdateRequest,
    EntityTypeConfigSchema,
    EntityTypeInfo,
    EntityTypesResponse,
)
from backend.src.database import get_db
from backend.src.services.config_service import ConfigService
from backend.src.services.detector import PIIDetector

router = APIRouter()


def _config_to_response(config) -> ConfigResponse:
    """Convert AnonymizationConfig to API response."""
    return ConfigResponse(
        id=config.id,
        name=config.name,
        confidence_threshold=config.confidence_threshold,
        language=config.language,
        locale=config.locale,
        entity_types=[
            EntityTypeConfigSchema(
                entity_type=ec.entity_type,
                enabled=ec.enabled,
                strategy=ec.strategy,
                strategy_params=ec.strategy_params,
            )
            for ec in config.entity_types
        ],
    )


@router.get("/config", response_model=ConfigResponse)
def get_config(db: Session = Depends(get_db)) -> ConfigResponse:
    """Get the currently active anonymization configuration."""
    service = ConfigService(db)
    config = service.get_active_config()

    if not config:
        raise HTTPException(status_code=404, detail="No active configuration found")

    return _config_to_response(config)


@router.put("/config", response_model=ConfigResponse)
def update_config(
    request: ConfigUpdateRequest,
    db: Session = Depends(get_db),
) -> ConfigResponse:
    """Update the anonymization configuration.

    Changes take effect immediately for subsequent anonymization requests.
    """
    service = ConfigService(db)

    try:
        # Convert entity type updates to list of dicts
        entity_updates = None
        if request.entity_types:
            entity_updates = [
                {
                    "entity_type": et.entity_type,
                    "enabled": et.enabled,
                    "strategy": et.strategy,
                    "strategy_params": et.strategy_params,
                }
                for et in request.entity_types
            ]

        config = service.update_config(
            confidence_threshold=request.confidence_threshold,
            language=request.language,
            locale=request.locale,
            entity_type_updates=entity_updates,
        )

        return _config_to_response(config)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/config/entity-types", response_model=EntityTypesResponse)
def list_entity_types() -> EntityTypesResponse:
    """List all entity types supported by the analyzer."""
    entity_types = PIIDetector.get_supported_entity_types()

    return EntityTypesResponse(
        entity_types=[
            EntityTypeInfo(name=et["name"], description=et["description"])
            for et in entity_types
        ]
    )


@router.get("/config/locales")
def list_locales() -> dict[str, str]:
    """List all supported locales for synthetic data generation."""
    from backend.src.generators.synthetic import SyntheticGenerator

    return SyntheticGenerator.get_supported_locales()
