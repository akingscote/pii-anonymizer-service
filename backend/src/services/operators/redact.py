"""Redact operator for completely removing PII values."""

from typing import Any

from presidio_anonymizer.operators import Operator, OperatorType


class RedactOperator(Operator):
    """Presidio operator that completely removes (redacts) PII values.

    Replaces PII with a placeholder or empty string.
    """

    def operate(self, text: str, params: dict[str, Any] | None = None) -> str:
        """Redact the text.

        Args:
            text: The PII value to redact
            params: Configuration options:
                - placeholder: Text to replace PII with (default: "[REDACTED]")
                - include_type: Include entity type in placeholder (default: False)
                - entity_type: The entity type (used if include_type is True)

        Returns:
            Placeholder text
        """
        if params is None:
            params = {}

        placeholder = params.get("placeholder", "[REDACTED]")
        include_type = params.get("include_type", False)
        entity_type = params.get("entity_type", "PII")

        if include_type:
            return f"[{entity_type}_REDACTED]"

        return placeholder

    def validate(self, params: dict[str, Any] | None = None) -> None:
        """Validate parameters."""
        if params is None:
            return

        if "placeholder" in params:
            placeholder = params["placeholder"]
            if not isinstance(placeholder, str):
                raise ValueError("placeholder must be a string")

    def operator_name(self) -> str:
        """Return the operator name for registration."""
        return "redact"

    def operator_type(self) -> OperatorType:
        """Return the operator type."""
        return OperatorType.Anonymize
