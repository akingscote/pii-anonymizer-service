# Data Model: Offline PII Anonymizer

**Date**: 2026-01-31
**Feature**: 001-presidio-pii-anonymizer

## Entity Relationship Diagram

```
┌─────────────────────────────────────┐
│           PIIMapping                │
├─────────────────────────────────────┤
│ PK  id: INTEGER                     │
│     original_hash: VARCHAR(64)      │──┐
│     substitute: VARCHAR(500)        │  │
│ FK  entity_type: VARCHAR(50)        │──┼──┐
│     first_seen: DATETIME            │  │  │
│     substitution_count: INTEGER     │  │  │
└─────────────────────────────────────┘  │  │
         │                               │  │
         │ UNIQUE(original_hash,         │  │
         │        entity_type)           │  │
         └───────────────────────────────┘  │
                                            │
┌─────────────────────────────────────┐     │
│       AnonymizationConfig           │     │
├─────────────────────────────────────┤     │
│ PK  id: INTEGER                     │     │
│     name: VARCHAR(100)              │     │
│     is_active: BOOLEAN              │     │
│     confidence_threshold: FLOAT     │     │
│     language: VARCHAR(10)           │     │
│     created_at: DATETIME            │     │
│     updated_at: DATETIME            │     │
└─────────────────────────────────────┘     │
         │                                  │
         │ 1:N                              │
         ▼                                  │
┌─────────────────────────────────────┐     │
│       EntityTypeConfig              │     │
├─────────────────────────────────────┤     │
│ PK  id: INTEGER                     │     │
│ FK  config_id: INTEGER              │     │
│     entity_type: VARCHAR(50)        │─────┘
│     enabled: BOOLEAN                │
│     strategy: VARCHAR(20)           │
│     strategy_params: JSON           │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         AuditLog                    │
├─────────────────────────────────────┤
│ PK  id: INTEGER                     │
│     timestamp: DATETIME             │
│     operation: VARCHAR(50)          │
│     entity_types_processed: JSON    │
│     input_length: INTEGER           │
│     entities_detected: INTEGER      │
│     entities_anonymized: INTEGER    │
│     duration_ms: INTEGER            │
└─────────────────────────────────────┘
```

## Entity Definitions

### PIIMapping

Stores the mapping between original PII values (as hashes) and their consistent substitutes.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Unique identifier |
| original_hash | VARCHAR(64) | NOT NULL | SHA-256 hash of original PII value |
| substitute | VARCHAR(500) | NOT NULL | Generated substitute value |
| entity_type | VARCHAR(50) | NOT NULL | Presidio entity type (e.g., PERSON, EMAIL_ADDRESS) |
| first_seen | DATETIME | NOT NULL | When this PII was first encountered |
| substitution_count | INTEGER | NOT NULL, DEFAULT 1 | Total times this mapping was used |

**Indexes**:
- `idx_lookup` UNIQUE (original_hash, entity_type) - Primary lookup path
- `idx_entity_type` (entity_type) - For statistics queries

**Business Rules**:
- Original PII is NEVER stored in plaintext
- Hash is computed as SHA-256(original_value + entity_type) to prevent rainbow table attacks
- Substitute must be unique within entity_type to prevent collisions

---

### AnonymizationConfig

Stores the user's anonymization configuration settings.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Unique identifier |
| name | VARCHAR(100) | NOT NULL | Configuration name (e.g., "default") |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Whether this config is currently active |
| confidence_threshold | FLOAT | NOT NULL, DEFAULT 0.7 | Minimum confidence score for detection (0.0-1.0) |
| language | VARCHAR(10) | NOT NULL, DEFAULT "en" | Language code for NLP processing |
| created_at | DATETIME | NOT NULL | Creation timestamp |
| updated_at | DATETIME | NOT NULL | Last modification timestamp |

**Business Rules**:
- Only one config can have `is_active=TRUE` at a time
- Confidence threshold must be between 0.0 and 1.0

---

### EntityTypeConfig

Stores per-entity-type configuration within a parent AnonymizationConfig.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Unique identifier |
| config_id | INTEGER | FK → AnonymizationConfig.id | Parent configuration |
| entity_type | VARCHAR(50) | NOT NULL | Presidio entity type |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | Whether to detect this entity type |
| strategy | VARCHAR(20) | NOT NULL, DEFAULT "replace" | Anonymization strategy |
| strategy_params | JSON | NULLABLE | Strategy-specific parameters |

**Valid Strategies**:
| Strategy | Description | Example Params |
|----------|-------------|----------------|
| replace | Replace with fake data | `{}` |
| mask | Partial masking | `{"chars_to_mask": 8, "from_end": true}` |
| hash | SHA-256 hash | `{"hash_type": "sha256"}` |
| redact | Remove entirely | `{}` |

**Business Rules**:
- Each (config_id, entity_type) pair must be unique
- Strategy must be one of: replace, mask, hash, redact

---

### AuditLog

Records each anonymization operation for compliance and debugging.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Unique identifier |
| timestamp | DATETIME | NOT NULL | When operation occurred |
| operation | VARCHAR(50) | NOT NULL | Operation type (e.g., "anonymize", "batch_anonymize") |
| entity_types_processed | JSON | NOT NULL | List of entity types that were checked |
| input_length | INTEGER | NOT NULL | Character count of input text |
| entities_detected | INTEGER | NOT NULL | Number of PII entities found |
| entities_anonymized | INTEGER | NOT NULL | Number of entities replaced |
| duration_ms | INTEGER | NOT NULL | Processing time in milliseconds |

**Business Rules**:
- NEVER log actual PII values or substitutes
- Log entries are append-only (no updates or deletes)

---

## API Data Transfer Objects

### AnonymizeRequest
```json
{
  "text": "string (required)",
  "entity_types": ["PERSON", "EMAIL_ADDRESS"],  // optional, null = use config
  "confidence_threshold": 0.7  // optional, null = use config
}
```

### AnonymizeResponse
```json
{
  "anonymized_text": "string",
  "substitutions": [
    {
      "start": 0,
      "end": 10,
      "entity_type": "PERSON",
      "original_length": 10,
      "substitute": "Jane Smith"
    }
  ],
  "metadata": {
    "entities_detected": 5,
    "entities_anonymized": 5,
    "new_mappings_created": 2,
    "existing_mappings_used": 3,
    "processing_time_ms": 150
  }
}
```

### BatchAnonymizeRequest
```json
{
  "texts": ["string1", "string2", "..."],
  "entity_types": ["PERSON", "EMAIL_ADDRESS"],
  "confidence_threshold": 0.7
}
```

### BatchAnonymizeResponse
```json
{
  "results": [
    { /* AnonymizeResponse */ },
    { /* AnonymizeResponse */ }
  ],
  "batch_metadata": {
    "total_texts": 10,
    "total_entities_detected": 47,
    "total_processing_time_ms": 1250
  }
}
```

### ConfigResponse
```json
{
  "id": 1,
  "name": "default",
  "confidence_threshold": 0.7,
  "language": "en",
  "entity_types": [
    {
      "entity_type": "PERSON",
      "enabled": true,
      "strategy": "replace",
      "strategy_params": {}
    },
    {
      "entity_type": "EMAIL_ADDRESS",
      "enabled": true,
      "strategy": "replace",
      "strategy_params": {}
    }
  ]
}
```

### StatsResponse
```json
{
  "total_mappings": 1250,
  "total_substitutions": 8430,
  "by_entity_type": [
    {
      "entity_type": "PERSON",
      "unique_values": 450,
      "total_substitutions": 3200
    },
    {
      "entity_type": "EMAIL_ADDRESS",
      "unique_values": 800,
      "total_substitutions": 5230
    }
  ],
  "oldest_mapping": "2026-01-15T10:30:00Z",
  "newest_mapping": "2026-01-31T14:22:00Z"
}
```

---

## State Transitions

### PIIMapping Lifecycle

```
[New PII Detected]
       │
       ▼
┌──────────────┐
│   Created    │ ─── substitution_count = 1
└──────────────┘     first_seen = now()
       │
       │ (same PII detected again)
       ▼
┌──────────────┐
│   Updated    │ ─── substitution_count += 1
└──────────────┘
       │
       │ (mapping persists indefinitely)
       ▼
┌──────────────┐
│  Permanent   │ ─── no deletion in normal operation
└──────────────┘
```

**Note**: Mappings are never deleted in normal operation to maintain consistency. A separate admin function could be provided for database maintenance if needed.

---

## Validation Rules

| Entity | Field | Rule |
|--------|-------|------|
| PIIMapping | original_hash | Must be 64 characters (SHA-256 hex) |
| PIIMapping | substitute | Max 500 characters, must be non-empty |
| PIIMapping | entity_type | Must be valid Presidio entity type |
| AnonymizationConfig | confidence_threshold | Must be 0.0 ≤ value ≤ 1.0 |
| AnonymizationConfig | language | Must be valid ISO 639-1 code |
| EntityTypeConfig | strategy | Must be one of: replace, mask, hash, redact |
| EntityTypeConfig | strategy_params | Must be valid JSON matching strategy schema |
