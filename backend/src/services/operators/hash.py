"""Hash operator for hashing PII values."""

import hashlib
from typing import Any

from presidio_anonymizer.operators import Operator, OperatorType


class HashOperator(Operator):
    """Presidio operator that hashes PII values.

    Note: Hash-based anonymization is NOT consistent by default unless
    the same salt is used. For consistent hashing, use this operator
    with a fixed salt value.
    """

    SUPPORTED_HASH_TYPES = ["sha256", "sha512", "md5"]

    def operate(self, text: str, params: dict[str, Any] | None = None) -> str:
        """Hash the text.

        Args:
            text: The PII value to hash
            params: Configuration options:
                - hash_type: Hash algorithm to use (default: "sha256")
                - truncate: Optional number of characters to keep (default: None = full hash)

        Returns:
            Hashed text
        """
        if params is None:
            params = {}

        hash_type = params.get("hash_type", "sha256")
        truncate = params.get("truncate")

        # Get the hash function
        if hash_type == "sha256":
            hash_func = hashlib.sha256
        elif hash_type == "sha512":
            hash_func = hashlib.sha512
        elif hash_type == "md5":
            hash_func = hashlib.md5
        else:
            hash_func = hashlib.sha256

        # Compute hash
        hash_value = hash_func(text.encode("utf-8")).hexdigest()

        # Truncate if requested
        if truncate and isinstance(truncate, int) and truncate > 0:
            hash_value = hash_value[:truncate]

        return hash_value

    def validate(self, params: dict[str, Any] | None = None) -> None:
        """Validate parameters."""
        if params is None:
            return

        if "hash_type" in params:
            hash_type = params["hash_type"]
            if hash_type not in self.SUPPORTED_HASH_TYPES:
                raise ValueError(
                    f"hash_type must be one of: {', '.join(self.SUPPORTED_HASH_TYPES)}"
                )

        if "truncate" in params:
            truncate = params["truncate"]
            if truncate is not None and (not isinstance(truncate, int) or truncate <= 0):
                raise ValueError("truncate must be a positive integer or None")

    def operator_name(self) -> str:
        """Return the operator name for registration."""
        return "hash"

    def operator_type(self) -> OperatorType:
        """Return the operator type."""
        return OperatorType.Anonymize
