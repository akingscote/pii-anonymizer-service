# Research: Offline PII Anonymizer

**Date**: 2026-01-31
**Feature**: 001-presidio-pii-anonymizer

## Decision Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| PII Detection | Microsoft Presidio AnalyzerEngine | Industry-standard, configurable, supports 50+ entity types |
| Anonymization | Custom Presidio Operator | Enables consistent substitution with mapping lookup |
| Synthetic Data | Faker library | Type-appropriate fake data generation |
| Local Storage | SQLite with SQLAlchemy | Zero dependencies, sufficient for 100k+ mappings |
| API Framework | FastAPI | Modern async Python, automatic OpenAPI docs |
| Frontend | React with Vite | Fast builds, simple SPA suitable for local use |

---

## 1. Presidio AnalyzerEngine Configuration

### Decision
Use Presidio's `AnalyzerEngine` with configurable entity type filtering.

### Rationale
- Supports 50+ built-in entity types (PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, etc.)
- Entity types can be enabled/disabled per request
- Confidence threshold is configurable
- Extensible with custom pattern recognizers if needed later

### Implementation Pattern
```python
from presidio_analyzer import AnalyzerEngine

analyzer = AnalyzerEngine()

# Filter to only configured entity types
results = analyzer.analyze(
    text=input_text,
    entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],  # From config
    language="en",
    score_threshold=0.7  # Configurable confidence
)
```

### Supported Entity Types (Initial Set)
| Entity Type | Description |
|-------------|-------------|
| PERSON | Names |
| EMAIL_ADDRESS | Email addresses |
| PHONE_NUMBER | Phone numbers |
| CREDIT_CARD | Credit card numbers |
| US_SSN | US Social Security Numbers |
| IP_ADDRESS | IP addresses |
| LOCATION | Geographic locations |
| DATE_TIME | Dates and times |

### Alternatives Considered
- **Custom regex-only**: Rejected - less accurate, no NLP context
- **AWS Comprehend**: Rejected - requires cloud connectivity
- **Google DLP**: Rejected - requires cloud connectivity

---

## 2. Consistent Anonymization via Custom Operator

### Decision
Create a custom Presidio `Operator` that checks SQLite mapping store before generating substitutes.

### Rationale
- Presidio's built-in operators don't support persistent mapping
- Custom operator integrates cleanly with Presidio's pipeline
- Mapping lookup happens at anonymization time, ensuring consistency

### Implementation Pattern
```python
from presidio_anonymizer.operators import Operator, OperatorType
from typing import Dict

class ConsistentReplaceOperator(Operator):
    """Replace PII with consistent substitutes from mapping store."""

    def operate(self, text: str, params: Dict = None) -> str:
        mapping_store = params["mapping_store"]
        entity_type = params["entity_type"]

        # Check for existing mapping
        existing = mapping_store.get_substitute(text, entity_type)
        if existing:
            mapping_store.increment_count(text, entity_type)
            return existing

        # Generate new substitute
        generator = params["generator"]
        substitute = generator.generate(entity_type)

        # Store mapping
        mapping_store.create_mapping(text, substitute, entity_type)
        return substitute

    def validate(self, params: Dict = None) -> None:
        required = ["mapping_store", "entity_type", "generator"]
        for key in required:
            if key not in params:
                raise ValueError(f"Missing required parameter: {key}")

    def operator_name(self) -> str:
        return "consistent_replace"

    def operator_type(self) -> OperatorType:
        return OperatorType.Anonymize
```

### Thread Safety Consideration
SQLite with proper transaction handling provides ACID guarantees. For single-user local deployment, this is sufficient. The mapping store will use `BEGIN IMMEDIATE` transactions to prevent race conditions.

### Alternatives Considered
- **In-memory dict only**: Rejected - no persistence across sessions
- **Hash-based substitution**: Rejected - doesn't produce type-appropriate output
- **Presidio's built-in encrypt**: Rejected - reversible, exposes original data risk

---

## 3. Synthetic Data Generation

### Decision
Use Faker library with entity-type-specific generators.

### Rationale
- Produces realistic-looking substitutes (real-looking names, valid email formats)
- Deterministic when seeded - can reproduce same substitutes
- Extensive locale support for international data
- No network calls required

### Implementation Pattern
```python
from faker import Faker
import hashlib

class SyntheticGenerator:
    def __init__(self, seed: str = None):
        self.fake = Faker()
        if seed:
            Faker.seed(seed)

    def generate(self, entity_type: str, original_hash: str = None) -> str:
        """Generate type-appropriate substitute."""
        # Use hash of original to seed for determinism
        if original_hash:
            seed = int(hashlib.md5(original_hash.encode()).hexdigest()[:8], 16)
            self.fake.seed_instance(seed)

        generators = {
            "PERSON": self.fake.name,
            "EMAIL_ADDRESS": self.fake.email,
            "PHONE_NUMBER": self.fake.phone_number,
            "CREDIT_CARD": lambda: self.fake.credit_card_number(card_type="visa"),
            "US_SSN": self.fake.ssn,
            "IP_ADDRESS": self.fake.ipv4,
            "LOCATION": self.fake.city,
            "DATE_TIME": lambda: self.fake.date(),
        }

        gen_func = generators.get(entity_type, lambda: f"<{entity_type}>")
        return gen_func()
```

### Alternatives Considered
- **UUID-based**: Rejected - not human-readable, loses semantic meaning
- **Sequential numbering**: Rejected - reveals ordering information
- **Mimesis library**: Viable alternative but Faker has broader adoption

---

## 4. SQLite Mapping Store Design

### Decision
SQLite with SQLAlchemy ORM, storing original PII as SHA-256 hashes.

### Rationale
- Zero external dependencies (SQLite is built into Python)
- ACID compliance for consistency guarantees
- Handles 100k+ records efficiently with proper indexing
- Hash storage prevents accidental PII exposure in database

### Schema Design
```python
from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PIIMapping(Base):
    __tablename__ = "pii_mappings"

    id = Column(Integer, primary_key=True)
    original_hash = Column(String(64), nullable=False)  # SHA-256
    substitute = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=False)
    first_seen = Column(DateTime, nullable=False)
    substitution_count = Column(Integer, default=1)

    __table_args__ = (
        Index("idx_lookup", "original_hash", "entity_type", unique=True),
        Index("idx_entity_type", "entity_type"),
    )
```

### Performance Considerations
- Composite index on (original_hash, entity_type) for O(log n) lookups
- Entity type index for statistics queries
- WAL mode enabled for better concurrent read performance

### Alternatives Considered
- **PostgreSQL**: Rejected - external dependency, overkill for local use
- **Redis**: Rejected - external dependency, memory-based
- **JSON file**: Rejected - no ACID, poor query performance at scale

---

## 5. API Design Decisions

### Decision
FastAPI with async endpoints, automatic OpenAPI documentation.

### Rationale
- Modern Python async support for I/O-bound operations
- Automatic OpenAPI/Swagger UI for testing and documentation
- Pydantic models for request/response validation
- Easy to add future features (auth, rate limiting)

### Key Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | /anonymize | Single text anonymization |
| POST | /anonymize/batch | Batch text anonymization |
| GET | /config | Get current configuration |
| PUT | /config | Update configuration |
| GET | /stats | Get substitution statistics |
| GET | /stats/{entity_type} | Get stats for specific type |

### Alternatives Considered
- **Flask**: Viable but lacks native async and auto-documentation
- **Django**: Overkill for this use case, heavier weight
- **Direct library only**: Rejected - spec requires API interface (FR-014)

---

## 6. Frontend Technology

### Decision
React with Vite build tooling, minimal dependencies.

### Rationale
- Simple SPA suitable for local configuration UI
- Vite provides fast development builds
- React ecosystem has strong component libraries
- Can be served as static files from the backend

### Core Views
1. **Anonymize**: Text input/output with real-time preview
2. **Configure**: Entity type toggles, strategy selection, threshold slider
3. **Statistics**: Substitution counts table, export functionality

### Alternatives Considered
- **Vue.js**: Viable alternative, slightly smaller but less ecosystem
- **Svelte**: Newer, smaller team familiarity concerns
- **Server-rendered (Jinja2)**: Viable but less interactive for configuration UI

---

## 7. NLP Model Selection

### Decision
Use `en_core_web_md` (medium) spaCy model by default with option to configure.

### Rationale
- Balance between accuracy and performance
- 100KB documents in <5 seconds achievable (SC-001)
- Can downgrade to `en_core_web_sm` for faster processing if needed

### Model Comparison
| Model | Size | Load Time | Accuracy |
|-------|------|-----------|----------|
| en_core_web_sm | 12MB | ~1s | Good |
| en_core_web_md | 40MB | ~2s | Better |
| en_core_web_lg | 560MB | ~5s | Best |

### Alternatives Considered
- **transformers models**: Rejected - too heavy for offline local use
- **Small model only**: Rejected - accuracy concerns for names/locations
