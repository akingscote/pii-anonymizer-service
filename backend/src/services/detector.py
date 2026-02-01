"""PII Detection service wrapping Microsoft Presidio's AnalyzerEngine."""

from dataclasses import dataclass

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerResult


@dataclass
class DetectionResult:
    """Result of PII detection."""

    entity_type: str
    start: int
    end: int
    score: float
    text: str  # The actual PII text detected


def _create_street_address_recognizer() -> PatternRecognizer:
    """Create a custom recognizer for US street addresses with context awareness."""
    # Pattern for common street address formats
    # Matches: 123 Main Street, 456 Oak Ave, 789 Pine Rd., etc.
    patterns = [
        Pattern(
            name="street_address_full",
            regex=r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s*)+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|Lane|Ln\.?|Way|Court|Ct\.?|Place|Pl\.?|Circle|Cir\.?|Trail|Trl\.?|Parkway|Pkwy\.?|Highway|Hwy\.?)\b",
            score=0.6,  # Lower base score, context will boost it
        ),
        Pattern(
            name="street_address_with_unit",
            regex=r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s*)+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|Lane|Ln\.?|Way|Court|Ct\.?|Place|Pl\.?)\s*,?\s*(?:Apt\.?|Suite|Ste\.?|Unit|#)\s*\d+[A-Z]?\b",
            score=0.7,
        ),
    ]

    # Context words that increase confidence when found near the pattern
    context_words = [
        "address", "addr", "location", "located",
        "ship", "shipping", "deliver", "delivery",
        "mail", "mailing", "postal",
        "home", "office", "work", "business",
        "residence", "residential", "billing",
        "live", "lives", "living", "reside", "resides",
        "send", "sending", "sent",
        "street", "avenue", "road", "drive", "lane",
    ]

    return PatternRecognizer(
        supported_entity="STREET_ADDRESS",
        patterns=patterns,
        context=context_words,
        name="StreetAddressRecognizer",
    )


def _create_enhanced_ip_recognizer() -> PatternRecognizer:
    """Create an enhanced IP address recognizer that handles CIDR notation."""
    patterns = [
        # IPv4 with optional CIDR notation
        Pattern(
            name="ipv4_cidr",
            regex=r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:/(?:3[0-2]|[12]?[0-9]))?\b",
            score=0.8,
        ),
    ]

    return PatternRecognizer(
        supported_entity="IP_ADDRESS",
        patterns=patterns,
        name="EnhancedIPRecognizer",
    )


def _create_enhanced_ssn_recognizer() -> PatternRecognizer:
    """Create an enhanced SSN recognizer with context awareness."""
    patterns = [
        # Standard SSN format: XXX-XX-XXXX
        Pattern(
            name="ssn_dashes",
            regex=r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b",
            score=0.5,
        ),
        # SSN without dashes: XXXXXXXXX
        Pattern(
            name="ssn_no_dashes",
            regex=r"\b(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0000)\d{4}\b",
            score=0.3,
        ),
    ]

    # Context words that increase confidence
    context_words = [
        "ssn", "social", "security", "social security",
        "ss#", "ss #", "soc sec",
    ]

    return PatternRecognizer(
        supported_entity="US_SSN",
        patterns=patterns,
        context=context_words,
        name="EnhancedSSNRecognizer",
    )


def _create_enhanced_date_recognizer() -> PatternRecognizer:
    """Create an enhanced date recognizer with context for DOB and important dates."""
    patterns = [
        # MM/DD/YYYY or MM-DD-YYYY
        Pattern(
            name="date_mdy",
            regex=r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",
            score=0.4,
        ),
        # YYYY-MM-DD (ISO format)
        Pattern(
            name="date_iso",
            regex=r"\b(?:19|20)\d{2}-(?:0?[1-9]|1[0-2])-(?:0?[1-9]|[12]\d|3[01])\b",
            score=0.4,
        ),
        # Month DD, YYYY (e.g., January 15, 2024)
        Pattern(
            name="date_long",
            regex=r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            score=0.5,
        ),
    ]

    # Context words that increase confidence for PII-related dates
    context_words = [
        "dob", "date of birth", "birth", "born", "birthday",
        "issued", "expires", "expiration", "exp", "valid",
        "signed", "effective", "terminated",
    ]

    return PatternRecognizer(
        supported_entity="DATE_TIME",
        patterns=patterns,
        context=context_words,
        name="EnhancedDateRecognizer",
    )


def _create_compound_location_recognizer() -> PatternRecognizer:
    """Create a recognizer for compound place names (e.g., Stockton-On-Tees, Newcastle upon Tyne)."""
    # Note: Presidio uses case-insensitive matching, so we use (?-i) to force case-sensitivity
    # where capital letters are required
    patterns = [
        # X-On-Y, X-Upon-Y, X-By-Y, X-In-Y patterns (UK style with hyphens)
        # Requires capital letter at start and after hyphen-preposition-hyphen
        Pattern(
            name="compound_location_hyphen",
            regex=r"(?-i)\b[A-Z][a-z]+(?:-(?:On|Upon|By|In|Under|Over|Le|La|The|Of|At|Near)-[A-Z][a-z]+)+\b",
            score=0.9,
        ),
        # X upon Y, X on Y patterns (spaced) - requires capitals at start and end
        Pattern(
            name="compound_location_spaced",
            regex=r"(?-i)\b[A-Z][a-z]+\s+(?:upon|on|by|in|under|over|near)\s+[A-Z][a-z]+\b",
            score=0.85,
        ),
    ]

    return PatternRecognizer(
        supported_entity="LOCATION",
        patterns=patterns,
        name="CompoundLocationRecognizer",
    )


def _create_guid_recognizer() -> PatternRecognizer:
    """Create a recognizer for GUIDs/UUIDs (globally unique identifiers)."""
    patterns = [
        # Standard GUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        Pattern(
            name="guid_standard",
            regex=r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            score=0.85,
        ),
    ]

    # Context words that increase confidence
    context_words = [
        "guid", "uuid", "id", "identifier", "user", "tenant", "resource",
        "object", "session", "correlation", "request", "transaction",
    ]

    return PatternRecognizer(
        supported_entity="GUID",
        patterns=patterns,
        context=context_words,
        name="GUIDRecognizer",
    )


def _create_coordinate_recognizer() -> PatternRecognizer:
    """Create a recognizer for geographic coordinates (latitude/longitude)."""
    patterns = [
        # Decimal degrees with high precision (likely GPS coordinates)
        # Latitude: -90 to 90, Longitude: -180 to 180
        # Matches values like 51.500789642333984 or -0.584630012512207
        # High precision (6+ decimals) is almost certainly GPS data
        Pattern(
            name="coordinate_decimal",
            regex=r"-?\d{1,3}\.\d{6,}",
            score=0.85,  # High score - 6+ decimal precision is very likely GPS
        ),
    ]

    # Context words that increase confidence
    context_words = [
        "latitude", "lat", "longitude", "lng", "long", "lon",
        "coordinates", "coord", "coords", "geo", "geoCoordinates",
        "location", "position", "gps",
    ]

    return PatternRecognizer(
        supported_entity="COORDINATE",
        patterns=patterns,
        context=context_words,
        name="CoordinateRecognizer",
    )


def _create_enhanced_phone_recognizer() -> PatternRecognizer:
    """Create an enhanced phone recognizer with context awareness for better detection."""
    patterns = [
        # US phone formats: (555) 123-4567, 555-123-4567, 555.123.4567, 5551234567
        Pattern(
            name="us_phone_parens",
            regex=r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}",
            score=0.75,  # High score - parentheses format is very likely a phone
        ),
        Pattern(
            name="us_phone_dashes",
            regex=r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
            score=0.65,  # Moderate score, context will boost above threshold
        ),
        Pattern(
            name="us_phone_10digit",
            regex=r"\b\d{10}\b",
            score=0.4,  # Low without context - 10 digits could be many things
        ),
    ]

    # Context words that increase confidence
    context_words = [
        "call", "phone", "telephone", "tel", "mobile", "cell",
        "contact", "reach", "dial", "ring", "text", "sms",
        "number", "ext", "extension", "fax",
        "at",  # "call me at", "reach me at"
    ]

    return PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        patterns=patterns,
        context=context_words,
        name="EnhancedPhoneRecognizer",
    )


class PIIDetector:
    """Wrapper around Presidio's AnalyzerEngine for PII detection.

    This class is thread-safe and can be shared across requests.
    """

    # Supported entity types from Presidio plus custom ones
    SUPPORTED_ENTITY_TYPES = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "CREDIT_CARD",
        "US_SSN",
        "US_BANK_NUMBER",
        "US_DRIVER_LICENSE",
        "US_ITIN",
        "US_PASSPORT",
        "IP_ADDRESS",
        "LOCATION",
        "STREET_ADDRESS",  # Custom recognizer
        "DATE_TIME",
        "NRP",  # Nationality, Religious, Political
        "MEDICAL_LICENSE",
        "URL",
        "IBAN_CODE",
        "CRYPTO",
        "GUID",  # Custom recognizer for GUIDs/UUIDs
        "COORDINATE",  # Custom recognizer for lat/long coordinates
    ]

    def __init__(self, language: str = "en"):
        """Initialize the detector with specified language.

        Args:
            language: Language code for NLP processing (default: "en")
        """
        self._language = language
        self._analyzer = AnalyzerEngine()

        # Add custom recognizers
        self._analyzer.registry.add_recognizer(_create_street_address_recognizer())
        self._analyzer.registry.add_recognizer(_create_enhanced_ip_recognizer())
        self._analyzer.registry.add_recognizer(_create_enhanced_phone_recognizer())
        self._analyzer.registry.add_recognizer(_create_enhanced_ssn_recognizer())
        self._analyzer.registry.add_recognizer(_create_enhanced_date_recognizer())
        self._analyzer.registry.add_recognizer(_create_guid_recognizer())
        self._analyzer.registry.add_recognizer(_create_compound_location_recognizer())
        self._analyzer.registry.add_recognizer(_create_coordinate_recognizer())

    @property
    def language(self) -> str:
        """Get the current language."""
        return self._language

    def detect(
        self,
        text: str,
        entity_types: list[str] | None = None,
        score_threshold: float = 0.7,
    ) -> list[DetectionResult]:
        """Detect PII entities in text.

        Args:
            text: The text to analyze
            entity_types: Optional list of entity types to detect (None = all supported)
            score_threshold: Minimum confidence score for detection (0.0-1.0)

        Returns:
            List of DetectionResult objects sorted by start position
        """
        # Use all supported types if none specified
        entities_to_detect = entity_types or self.SUPPORTED_ENTITY_TYPES

        # Filter to only supported types
        entities_to_detect = [e for e in entities_to_detect if e in self.SUPPORTED_ENTITY_TYPES]

        # Analyze text
        results: list[RecognizerResult] = self._analyzer.analyze(
            text=text,
            entities=entities_to_detect,
            language=self._language,
            score_threshold=score_threshold,
        )

        # Convert to DetectionResult and extract actual text
        detection_results = []
        for result in results:
            detection_results.append(
                DetectionResult(
                    entity_type=result.entity_type,
                    start=result.start,
                    end=result.end,
                    score=result.score,
                    text=text[result.start : result.end],
                )
            )

        # Sort by start position
        detection_results.sort(key=lambda r: r.start)

        return detection_results

    @classmethod
    def get_supported_entity_types(cls) -> list[dict[str, str]]:
        """Get list of supported entity types with descriptions."""
        descriptions = {
            "PERSON": "Names of people",
            "EMAIL_ADDRESS": "Email addresses",
            "PHONE_NUMBER": "Phone numbers",
            "CREDIT_CARD": "Credit card numbers",
            "US_SSN": "US Social Security Numbers",
            "US_BANK_NUMBER": "US Bank account numbers",
            "US_DRIVER_LICENSE": "US Driver's license numbers",
            "US_ITIN": "US Individual Taxpayer ID Numbers",
            "US_PASSPORT": "US Passport numbers",
            "IP_ADDRESS": "IP addresses (v4 and v6) with optional CIDR",
            "LOCATION": "Geographic locations (cities, countries)",
            "STREET_ADDRESS": "Street addresses (e.g., 123 Main Street)",
            "DATE_TIME": "Dates and times",
            "NRP": "Nationality, Religious, Political groups",
            "MEDICAL_LICENSE": "Medical license numbers",
            "URL": "URLs and web addresses",
            "IBAN_CODE": "International Bank Account Numbers",
            "CRYPTO": "Cryptocurrency addresses",
            "GUID": "Globally Unique Identifiers (GUIDs/UUIDs)",
            "COORDINATE": "Geographic coordinates (latitude/longitude)",
        }

        return [
            {"name": entity_type, "description": descriptions.get(entity_type, entity_type)}
            for entity_type in cls.SUPPORTED_ENTITY_TYPES
        ]


# Singleton instance for reuse
_detector_instance: PIIDetector | None = None


def get_detector(language: str = "en") -> PIIDetector:
    """Get or create a PIIDetector instance.

    Uses a singleton pattern to avoid repeatedly loading the NLP model.
    """
    global _detector_instance
    if _detector_instance is None or _detector_instance.language != language:
        _detector_instance = PIIDetector(language=language)
    return _detector_instance


def reset_detector() -> None:
    """Reset the singleton detector instance."""
    global _detector_instance
    _detector_instance = None
