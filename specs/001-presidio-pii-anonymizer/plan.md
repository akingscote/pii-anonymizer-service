# Implementation Plan: Offline PII Anonymizer

**Branch**: `001-presidio-pii-anonymizer` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-presidio-pii-anonymizer/spec.md`

## Summary

Build an offline PII detection and anonymization system using Microsoft Presidio that maintains consistent substitution mappings across sessions. The system accepts generic string input, stores PII-to-substitute mappings in a local SQLite database, and provides both a Python library/API interface and a web frontend for configuration and use.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: Microsoft Presidio (presidio-analyzer, presidio-anonymizer), Faker (synthetic data generation), FastAPI (API layer), SQLAlchemy (ORM)
**Storage**: SQLite (local file-based, no cloud dependencies)
**Testing**: pytest with pytest-cov for coverage
**Target Platform**: Local server (Linux/macOS/Windows), offline-capable
**Project Type**: Web application (backend API + frontend)
**Performance Goals**: 100KB text anonymized in <5 seconds, 100,000+ mappings without degradation
**Constraints**: Fully offline after initial setup, no network calls during anonymization
**Scale/Scope**: Single-user/small-team local deployment, millions of potential mappings

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Security by Default | ✅ PASS | PII stored as hashes, no secrets logged, local-only operation |
| II. Code Integrity | ✅ PASS | Deterministic substitution (same input → same output), pinned dependencies |
| III. Honest Behavior | ✅ PASS | Accurate metadata counts, explicit failure on anonymization errors |
| IV. Defense in Depth | ✅ PASS | Input validation, mapping verification, audit logging |
| V. Minimal Attack Surface | ✅ PASS | Local-only API, no external network access, minimal dependencies |

**Security Requirements Alignment**:
- Input Handling: All text input validated before processing
- Output Handling: Anonymized output verified against original
- Error Handling: Generic errors externally, detailed logs internally (no PII in logs)
- Authentication: N/A for initial single-user local deployment (noted in assumptions)
- Audit Trail: All anonymization operations logged with timestamps

## Project Structure

### Documentation (this feature)

```text
specs/001-presidio-pii-anonymizer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI spec)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/          # SQLAlchemy models (PIIMapping, Config)
│   ├── services/        # Core logic (detector, anonymizer, mapping_store)
│   ├── api/             # FastAPI routes
│   └── generators/      # Synthetic data generators per entity type
└── tests/
    ├── unit/            # Unit tests for services
    ├── integration/     # API integration tests
    └── fixtures/        # Test data

frontend/
├── src/
│   ├── components/      # React/Vue components
│   ├── pages/           # Main views (Anonymize, Config, Stats)
│   └── services/        # API client
└── tests/
```

**Structure Decision**: Web application structure selected because the spec requires both a backend API (FR-014) and a web-based frontend (FR-009). The backend handles all PII detection, anonymization, and storage logic while the frontend provides the configuration UI.

## Complexity Tracking

No complexity violations. The web application structure is justified by explicit requirements for both API and frontend interfaces.

---

## Constitution Re-Check (Post Phase 1 Design)

| Principle | Status | Design Validation |
|-----------|--------|-------------------|
| I. Security by Default | ✅ PASS | Data model stores original_hash (SHA-256), never plaintext PII. API validates all inputs via Pydantic. |
| II. Code Integrity | ✅ PASS | Custom Presidio operator ensures deterministic substitution. All dependencies pinned in requirements.txt. |
| III. Honest Behavior | ✅ PASS | API responses include accurate metadata (entities_detected, processing_time_ms). Errors return structured ErrorResponse. |
| IV. Defense in Depth | ✅ PASS | AuditLog entity tracks all operations. Input validation at API layer + service layer. Mapping uniqueness enforced at DB level. |
| V. Minimal Attack Surface | ✅ PASS | Single local endpoint (localhost:8000). No external API calls. Minimal entity exposure in stats endpoints. |

**Phase 1 Artifacts Generated**:
- [research.md](./research.md) - Technology decisions and alternatives
- [data-model.md](./data-model.md) - Entity definitions and API DTOs
- [contracts/api.yaml](./contracts/api.yaml) - OpenAPI 3.0 specification
- [quickstart.md](./quickstart.md) - Setup and usage guide

**Ready for**: `/speckit.tasks` to generate implementation tasks
