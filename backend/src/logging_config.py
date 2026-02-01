"""Logging configuration that ensures no PII is logged."""

import logging
import sys


class PIISafeFormatter(logging.Formatter):
    """Custom formatter that ensures no PII patterns are logged.

    Note: This is a basic implementation. In production, consider
    using more sophisticated PII detection in logs.
    """

    # Patterns that might indicate PII (very basic)
    SENSITIVE_KEYS = {"email", "phone", "ssn", "name", "address", "password", "token"}

    def format(self, record: logging.LogRecord) -> str:
        # Filter out sensitive data from extra fields
        if hasattr(record, "__dict__"):
            for key in list(record.__dict__.keys()):
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                    setattr(record, key, "[REDACTED]")

        return super().format(record)


def configure_logging(level: str = "INFO") -> None:
    """Configure application logging with PII-safe formatting.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create formatter
    formatter = PIISafeFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
