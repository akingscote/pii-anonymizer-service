"""Mask operator for partial masking of PII values."""

from typing import Any

from presidio_anonymizer.operators import Operator, OperatorType


class MaskOperator(Operator):
    """Presidio operator that masks part of a PII value.

    Example: "4111-1111-1111-1111" -> "****-****-****-1111"
    """

    def operate(self, text: str, params: dict[str, Any] | None = None) -> str:
        """Mask part of the text.

        Args:
            text: The PII value to mask
            params: Configuration options:
                - masking_char: Character to use for masking (default: "*")
                - chars_to_mask: Number of characters to mask (default: len(text) - 4)
                - from_end: If True, mask from end; if False, mask from start (default: False)

        Returns:
            Masked text
        """
        if params is None:
            params = {}

        masking_char = params.get("masking_char", "*")
        from_end = params.get("from_end", False)

        # Default to masking all but last 4 characters
        default_mask_count = max(0, len(text) - 4)
        chars_to_mask = params.get("chars_to_mask", default_mask_count)

        # Ensure we don't mask more than the text length
        chars_to_mask = min(chars_to_mask, len(text))

        if chars_to_mask == 0:
            return text

        if from_end:
            # Mask last N characters
            visible_part = text[:-chars_to_mask]
            masked_part = masking_char * chars_to_mask
            return visible_part + masked_part
        else:
            # Mask first N characters
            masked_part = masking_char * chars_to_mask
            visible_part = text[chars_to_mask:]
            return masked_part + visible_part

    def validate(self, params: dict[str, Any] | None = None) -> None:
        """Validate parameters."""
        if params is None:
            return

        if "chars_to_mask" in params:
            chars_to_mask = params["chars_to_mask"]
            if not isinstance(chars_to_mask, int) or chars_to_mask < 0:
                raise ValueError("chars_to_mask must be a non-negative integer")

        if "masking_char" in params:
            masking_char = params["masking_char"]
            if not isinstance(masking_char, str) or len(masking_char) != 1:
                raise ValueError("masking_char must be a single character")

    def operator_name(self) -> str:
        """Return the operator name for registration."""
        return "mask"

    def operator_type(self) -> OperatorType:
        """Return the operator type."""
        return OperatorType.Anonymize
