"""Configuration service for managing anonymization settings."""

from datetime import datetime

from sqlalchemy.orm import Session

from backend.src.models import AnonymizationConfig, EntityTypeConfig


class ConfigService:
    """Service for managing anonymization configuration."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self._db = db

    def get_active_config(self) -> AnonymizationConfig | None:
        """Get the currently active configuration."""
        return (
            self._db.query(AnonymizationConfig)
            .filter(AnonymizationConfig.is_active == True)  # noqa: E712
            .first()
        )

    def get_config_by_id(self, config_id: int) -> AnonymizationConfig | None:
        """Get a configuration by ID."""
        return self._db.query(AnonymizationConfig).filter_by(id=config_id).first()

    def update_config(
        self,
        confidence_threshold: float | None = None,
        language: str | None = None,
        locale: str | None = None,
        entity_type_updates: list[dict] | None = None,
    ) -> AnonymizationConfig:
        """Update the active configuration.

        Args:
            confidence_threshold: New confidence threshold (0.0-1.0)
            language: New language code
            locale: New locale code for Faker (e.g., "en_US", "de_DE")
            entity_type_updates: List of entity type configuration updates

        Returns:
            The updated configuration
        """
        config = self.get_active_config()
        if not config:
            raise ValueError("No active configuration found")

        # Update scalar fields
        if confidence_threshold is not None:
            if not 0.0 <= confidence_threshold <= 1.0:
                raise ValueError("confidence_threshold must be between 0.0 and 1.0")
            config.confidence_threshold = confidence_threshold

        if language is not None:
            config.language = language

        if locale is not None:
            config.locale = locale
            # Reset the generator singleton to pick up new locale
            from backend.src.generators.synthetic import reset_generator
            reset_generator()

        # Update entity type configurations
        if entity_type_updates:
            for update in entity_type_updates:
                entity_type = update.get("entity_type")
                if not entity_type:
                    continue

                # Find existing entity config
                entity_config = next(
                    (ec for ec in config.entity_types if ec.entity_type == entity_type),
                    None,
                )

                if entity_config:
                    # Update existing
                    if "enabled" in update:
                        entity_config.enabled = update["enabled"]
                    if "strategy" in update:
                        entity_config.strategy = update["strategy"]
                    if "strategy_params" in update:
                        entity_config.strategy_params = update["strategy_params"]
                else:
                    # Create new entity config
                    new_config = EntityTypeConfig(
                        config_id=config.id,
                        entity_type=entity_type,
                        enabled=update.get("enabled", True),
                        strategy=update.get("strategy", "replace"),
                        strategy_params=update.get("strategy_params"),
                    )
                    self._db.add(new_config)
                    config.entity_types.append(new_config)

        config.updated_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(config)

        return config

    def get_enabled_entity_types(self) -> list[str]:
        """Get list of currently enabled entity types."""
        config = self.get_active_config()
        if not config:
            return []

        return [ec.entity_type for ec in config.entity_types if ec.enabled]

    def get_entity_strategy(self, entity_type: str) -> tuple[str, dict | None]:
        """Get the strategy and params for an entity type.

        Returns:
            Tuple of (strategy_name, strategy_params) or ("replace", None) as default
        """
        config = self.get_active_config()
        if not config:
            return "replace", None

        entity_config = next(
            (ec for ec in config.entity_types if ec.entity_type == entity_type),
            None,
        )

        if entity_config and entity_config.enabled:
            return entity_config.strategy, entity_config.strategy_params

        return "replace", None
