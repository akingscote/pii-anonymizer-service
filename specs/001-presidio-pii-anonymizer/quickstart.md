# Quickstart: Offline PII Anonymizer

**Feature**: 001-presidio-pii-anonymizer
**Date**: 2026-01-31

## Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- 2GB disk space (for NLP models)

## Installation

### 1. Clone and Setup Backend

```bash
# Clone repository
cd pii-anonymizer-msft-sentinel

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy NLP model
python -m spacy download en_core_web_lg
```

### 2. Initialize Database

```bash
# Create SQLite database with initial schema
python -m backend.src.cli init-db

# (Optional) Seed with default configuration
python -m backend.src.cli seed-config
```

### 3. Start Backend Server

```bash
# Development mode
uvicorn backend.src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn backend.src.api.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 4. Setup Frontend (Optional)

```bash
cd frontend
npm install
npm run dev  # Development server at http://localhost:5173
```

## Quick Test

### Using cURL

```bash
# Anonymize text
curl -X POST http://localhost:8000/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text": "John Smith can be reached at john.smith@example.com"}'

# Response:
# {
#   "anonymized_text": "Jane Doe can be reached at user_abc123@anon.local",
#   "substitutions": [...],
#   "metadata": {"entities_detected": 2, ...}
# }
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/anonymize",
    json={"text": "Call Jane at 555-123-4567"}
)
print(response.json()["anonymized_text"])
```

### Using the Library Directly

```python
from backend.src.services.anonymizer import PIIAnonymizer

anonymizer = PIIAnonymizer()

# Single text
result = anonymizer.anonymize("Contact john@example.com for details")
print(result.anonymized_text)

# Batch processing
results = anonymizer.anonymize_batch([
    "Email: jane@example.com",
    "Phone: 555-0123",
    "Name: Bob Smith"
])
```

## Verify Consistent Substitution

```bash
# First request
curl -X POST http://localhost:8000/anonymize \
  -d '{"text": "John Smith"}' -H "Content-Type: application/json"
# Returns: "Jane Doe"

# Second request with same PII
curl -X POST http://localhost:8000/anonymize \
  -d '{"text": "Contact John Smith at john@example.com"}' \
  -H "Content-Type: application/json"
# Returns: "Contact Jane Doe at user_xyz@anon.local"
# Note: "John Smith" → "Jane Doe" is consistent!
```

## Configuration

### View Current Config

```bash
curl http://localhost:8000/config
```

### Update Entity Types

```bash
curl -X PUT http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "entity_types": [
      {"entity_type": "PERSON", "enabled": true, "strategy": "replace"},
      {"entity_type": "EMAIL_ADDRESS", "enabled": true, "strategy": "replace"},
      {"entity_type": "PHONE_NUMBER", "enabled": false}
    ]
  }'
```

### Adjust Confidence Threshold

```bash
curl -X PUT http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"confidence_threshold": 0.8}'
```

## View Statistics

```bash
# All statistics
curl http://localhost:8000/stats

# By entity type
curl http://localhost:8000/stats/PERSON

# Export for compliance
curl "http://localhost:8000/stats/export?format=csv" > report.csv
```

## Troubleshooting

### "Model not found" error
```bash
python -m spacy download en_core_web_lg
```

### Database locked error
Ensure only one instance is running, or use WAL mode:
```python
# In database config
engine = create_engine("sqlite:///data.db?mode=wal")
```

### Slow first request
The NLP model loads on first use. Subsequent requests are faster.

## Next Steps

1. Open http://localhost:5173 for the web interface
2. Configure entity types in Settings
3. Test with your sample data
4. Review statistics for verification
