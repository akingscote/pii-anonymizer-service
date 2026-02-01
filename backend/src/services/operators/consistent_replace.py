"""Custom Presidio operator for consistent replacement with mapping lookup."""

from typing import Any

from presidio_anonymizer.operators import Operator, OperatorType

from backend.src.generators.synthetic import SyntheticGenerator
from backend.src.services.mapping_store import MappingStore


class ConsistentReplaceOperator(Operator):
    """Presidio operator that replaces PII with consistent substitutes.

    Uses the MappingStore to look up existing mappings before generating
    new substitutes, ensuring the same PII always maps to the same value.
    """

    def operate(self, text: str, params: dict[str, Any] | None = None) -> str:
        """Replace PII text with a consistent substitute.

        Args:
            text: The PII value to replace
            params: Must contain:
                - mapping_store: MappingStore instance
                - generator: SyntheticGenerator instance
                - entity_type: The entity type being processed

        Returns:
            The substitute value
        """
        if params is None:
            params = {}

        mapping_store: MappingStore = params["mapping_store"]
        generator: SyntheticGenerator = params["generator"]
        entity_type: str = params["entity_type"]

        # Create a generator function that passes original_value for smart substitution
        def generate_with_original(etype: str, original_value: str) -> str:
            return generator.generate(etype, original_value=original_value)

        # Get or create substitute
        substitute, is_new = mapping_store.get_or_create(
            original_value=text,
            entity_type=entity_type,
            generator_func=generate_with_original,
        )

        # Track whether this was a new mapping (for metadata)
        if "new_mappings" in params:
            if is_new:
                params["new_mappings"].append(entity_type)
            else:
                params["existing_mappings"].append(entity_type)

        return substitute

    def validate(self, params: dict[str, Any] | None = None) -> None:
        """Validate that required parameters are present.

        Args:
            params: Parameters to validate

        Raises:
            ValueError: If required parameters are missing
        """
        if params is None:
            raise ValueError("params cannot be None")

        required = ["mapping_store", "generator", "entity_type"]
        for key in required:
            if key not in params:
                raise ValueError(f"Missing required parameter: {key}")

        if not isinstance(params["mapping_store"], MappingStore):
            raise ValueError("mapping_store must be a MappingStore instance")

        if not isinstance(params["generator"], SyntheticGenerator):
            raise ValueError("generator must be a SyntheticGenerator instance")

    def operator_name(self) -> str:
        """Return the operator name for registration."""
        return "consistent_replace"

    def operator_type(self) -> OperatorType:
        """Return the operator type."""
        return OperatorType.Anonymize
