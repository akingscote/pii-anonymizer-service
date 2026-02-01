"""PII Anonymizer service orchestrating detection and substitution."""

import time
from dataclasses import dataclass, field
from datetime import datetime

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import EngineResult, OperatorConfig, RecognizerResult
from sqlalchemy.orm import Session

from backend.src.generators.synthetic import SyntheticGenerator, get_generator
from backend.src.models import AuditLog
from backend.src.services.detector import DetectionResult, PIIDetector, get_detector
from backend.src.services.mapping_store import MappingStore
from backend.src.services.operators.consistent_replace import ConsistentReplaceOperator


@dataclass
class SubstitutionInfo:
    """Information about a single substitution."""

    start: int
    end: int
    entity_type: str
    original_length: int
    substitute: str


@dataclass
class AnonymizationResult:
    """Result of an anonymization operation."""

    anonymized_text: str
    substitutions: list[SubstitutionInfo] = field(default_factory=list)
    entities_detected: int = 0
    entities_anonymized: int = 0
    new_mappings_created: int = 0
    existing_mappings_used: int = 0
    processing_time_ms: int = 0


class PIIAnonymizer:
    """Service for detecting and anonymizing PII in text.

    Orchestrates the detector, mapping store, and anonymizer engine
    to provide consistent PII substitution.
    """

    def __init__(
        self,
        db: Session,
        detector: PIIDetector | None = None,
        generator: SyntheticGenerator | None = None,
    ):
        """Initialize the anonymizer.

        Args:
            db: SQLAlchemy session for mapping storage
            detector: Optional custom PIIDetector instance
            generator: Optional custom SyntheticGenerator instance
        """
        self._db = db
        self._detector = detector or get_detector()
        self._generator = generator or get_generator()
        self._mapping_store = MappingStore(db)

        # Initialize Presidio anonymizer engine with our custom operator
        self._anonymizer = AnonymizerEngine()
        self._anonymizer.add_anonymizer(ConsistentReplaceOperator)

    def anonymize(
        self,
        text: str,
        entity_types: list[str] | None = None,
        confidence_threshold: float = 0.7,
        log_operation: bool = True,
    ) -> AnonymizationResult:
        """Anonymize PII in text with consistent substitution.

        Args:
            text: The text to anonymize
            entity_types: Optional list of entity types to detect (None = all)
            confidence_threshold: Minimum confidence score for detection
            log_operation: Whether to log this operation to audit log

        Returns:
            AnonymizationResult with anonymized text and metadata
        """
        start_time = time.time()

        # Detect PII
        detections = self._detector.detect(
            text=text,
            entity_types=entity_types,
            score_threshold=confidence_threshold,
        )

        if not detections:
            # No PII found - return original text
            processing_time_ms = int((time.time() - start_time) * 1000)

            if log_operation:
                self._log_operation(
                    operation="anonymize",
                    entity_types=entity_types or [],
                    input_length=len(text),
                    entities_detected=0,
                    entities_anonymized=0,
                    duration_ms=processing_time_ms,
                )

            return AnonymizationResult(
                anonymized_text=text,
                processing_time_ms=processing_time_ms,
            )

        # Convert detections to Presidio RecognizerResult format
        analyzer_results = [
            RecognizerResult(
                entity_type=d.entity_type,
                start=d.start,
                end=d.end,
                score=d.score,
            )
            for d in detections
        ]

        # Track new vs existing mappings
        new_mappings: list[str] = []
        existing_mappings: list[str] = []

        # Build operator config for each entity type
        operators = {}
        for detection in detections:
            if detection.entity_type not in operators:
                operators[detection.entity_type] = OperatorConfig(
                    "consistent_replace",
                    {
                        "mapping_store": self._mapping_store,
                        "generator": self._generator,
                        "entity_type": detection.entity_type,
                        "new_mappings": new_mappings,
                        "existing_mappings": existing_mappings,
                    },
                )

        # Run anonymization
        engine_result: EngineResult = self._anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=operators,
        )

        # Commit mappings to database
        self._db.commit()

        # Build substitution info list using ORIGINAL positions from detections
        # Note: engine_result.items contains positions in the OUTPUT text,
        # but we need positions in the ORIGINAL text for frontend highlighting.

        # Sort detections by start position (they should already be sorted)
        sorted_detections = sorted(detections, key=lambda d: d.start)

        # Sort engine result items by their position in output text
        sorted_items = sorted(engine_result.items, key=lambda i: i.start)

        # Match detections to engine results - they should correspond 1:1
        # Both lists represent the same entities, just with different position references
        substitutions = []
        for detection, item in zip(sorted_detections, sorted_items):
            substitutions.append(
                SubstitutionInfo(
                    start=detection.start,  # Original position in input text
                    end=detection.end,  # Original position in input text
                    entity_type=detection.entity_type,
                    original_length=detection.end - detection.start,
                    substitute=item.text,  # The substitute value from anonymizer
                )
            )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log operation
        if log_operation:
            self._log_operation(
                operation="anonymize",
                entity_types=list(set(d.entity_type for d in detections)),
                input_length=len(text),
                entities_detected=len(detections),
                entities_anonymized=len(substitutions),
                duration_ms=processing_time_ms,
            )

        return AnonymizationResult(
            anonymized_text=engine_result.text,
            substitutions=substitutions,
            entities_detected=len(detections),
            entities_anonymized=len(substitutions),
            new_mappings_created=len(new_mappings),
            existing_mappings_used=len(existing_mappings),
            processing_time_ms=processing_time_ms,
        )

    def anonymize_batch(
        self,
        texts: list[str],
        entity_types: list[str] | None = None,
        confidence_threshold: float = 0.7,
    ) -> tuple[list[AnonymizationResult], int, int]:
        """Anonymize multiple texts in a batch.

        Args:
            texts: List of texts to anonymize
            entity_types: Optional list of entity types to detect
            confidence_threshold: Minimum confidence score for detection

        Returns:
            Tuple of (results list, total entities detected, total processing time ms)
        """
        start_time = time.time()
        results = []
        total_detected = 0

        for text in texts:
            result = self.anonymize(
                text=text,
                entity_types=entity_types,
                confidence_threshold=confidence_threshold,
                log_operation=False,  # Log batch operation instead
            )
            results.append(result)
            total_detected += result.entities_detected

        total_time_ms = int((time.time() - start_time) * 1000)

        # Log batch operation
        self._log_operation(
            operation="batch_anonymize",
            entity_types=entity_types or [],
            input_length=sum(len(t) for t in texts),
            entities_detected=total_detected,
            entities_anonymized=sum(r.entities_anonymized for r in results),
            duration_ms=total_time_ms,
        )

        return results, total_detected, total_time_ms

    def _log_operation(
        self,
        operation: str,
        entity_types: list[str],
        input_length: int,
        entities_detected: int,
        entities_anonymized: int,
        duration_ms: int,
    ) -> None:
        """Log an anonymization operation to the audit log."""
        audit_entry = AuditLog(
            timestamp=datetime.utcnow(),
            operation=operation,
            entity_types_processed=entity_types,
            input_length=input_length,
            entities_detected=entities_detected,
            entities_anonymized=entities_anonymized,
            duration_ms=duration_ms,
        )
        self._db.add(audit_entry)
        self._db.commit()
