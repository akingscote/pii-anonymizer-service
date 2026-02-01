# Tasks: Offline PII Anonymizer

**Input**: Design documents from `/specs/001-presidio-pii-anonymizer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md (backend/src/, frontend/src/)
- [x] T002 Initialize Python project with pyproject.toml and requirements.txt
- [x] T003 [P] Configure ruff linting and formatting in pyproject.toml
- [x] T004 [P] Create backend/src/__init__.py and subpackage __init__.py files
- [x] T005 [P] Initialize frontend React+Vite project in frontend/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create SQLAlchemy database configuration in backend/src/database.py
- [x] T007 Create PIIMapping model in backend/src/models/pii_mapping.py
- [x] T008 [P] Create AnonymizationConfig model in backend/src/models/config.py
- [x] T009 [P] Create EntityTypeConfig model in backend/src/models/entity_type_config.py
- [x] T010 [P] Create AuditLog model in backend/src/models/audit_log.py
- [x] T011 Create database initialization script in backend/src/cli.py
- [x] T012 Implement Presidio AnalyzerEngine wrapper in backend/src/services/detector.py
- [x] T013 [P] Create Pydantic request/response schemas in backend/src/api/schemas.py
- [x] T014 Create FastAPI application instance in backend/src/api/main.py
- [x] T015 [P] Implement health check endpoint GET /health in backend/src/api/routes/health.py
- [x] T016 Seed default configuration on database initialization in backend/src/cli.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Anonymize Text with Consistent Substitution (Priority: P1) 🎯 MVP

**Goal**: Core anonymization with consistent substitution - same PII always maps to same substitute

**Independent Test**: Submit text with repeated PII values, verify identical substitutes are used each time and across sessions

### Implementation for User Story 1

- [x] T017 [US1] Implement MappingStore service with get/create/increment in backend/src/services/mapping_store.py
- [x] T018 [US1] Implement SyntheticGenerator with Faker for type-appropriate substitutes in backend/src/generators/synthetic.py
- [x] T019 [US1] Implement ConsistentReplaceOperator custom Presidio operator in backend/src/services/operators/consistent_replace.py
- [x] T020 [US1] Implement PIIAnonymizer service orchestrating detection+substitution in backend/src/services/anonymizer.py
- [x] T021 [US1] Implement POST /anonymize endpoint in backend/src/api/routes/anonymize.py
- [x] T022 [US1] Implement POST /anonymize/batch endpoint in backend/src/api/routes/anonymize.py
- [x] T023 [US1] Add audit logging to anonymization operations in backend/src/services/anonymizer.py
- [x] T024 [US1] Register anonymize routes in FastAPI app in backend/src/api/main.py

**Checkpoint**: User Story 1 complete - core anonymization with consistent substitution works via API

---

## Phase 4: User Story 2 - Configure Detection and Anonymization Settings (Priority: P2)

**Goal**: Allow users to configure which entity types to detect and anonymization strategies per type

**Independent Test**: Change config to disable PERSON detection, submit text with names, verify names are NOT anonymized

### Implementation for User Story 2

- [x] T025 [US2] Implement ConfigService for get/update operations in backend/src/services/config_service.py
- [x] T026 [US2] Implement GET /config endpoint in backend/src/api/routes/config.py
- [x] T027 [US2] Implement PUT /config endpoint in backend/src/api/routes/config.py
- [x] T028 [US2] Implement GET /config/entity-types endpoint listing supported types in backend/src/api/routes/config.py
- [x] T029 [US2] Update PIIAnonymizer to respect config settings in backend/src/services/anonymizer.py
- [x] T030 [US2] Implement mask strategy operator in backend/src/services/operators/mask.py
- [x] T031 [US2] Implement hash strategy operator in backend/src/services/operators/hash.py
- [x] T032 [US2] Implement redact strategy operator in backend/src/services/operators/redact.py
- [x] T033 [US2] Register config routes in FastAPI app in backend/src/api/main.py

**Checkpoint**: User Story 2 complete - configuration changes affect anonymization behavior

---

## Phase 5: User Story 3 - View Substitution Metadata and Statistics (Priority: P3)

**Goal**: Provide statistics and metadata about substitutions for audit and compliance

**Independent Test**: Anonymize several texts, query /stats, verify counts match actual substitutions

### Implementation for User Story 3

- [x] T034 [US3] Implement StatsService for aggregate statistics in backend/src/services/stats_service.py
- [x] T035 [US3] Implement GET /stats endpoint in backend/src/api/routes/stats.py
- [x] T036 [US3] Implement GET /stats/{entity_type} endpoint in backend/src/api/routes/stats.py
- [x] T037 [US3] Implement GET /stats/export endpoint with CSV/JSON output in backend/src/api/routes/stats.py
- [x] T038 [US3] Register stats routes in FastAPI app in backend/src/api/main.py

**Checkpoint**: User Story 3 complete - statistics available for compliance reporting

---

## Phase 6: User Story 4 - Access via Web Interface (Priority: P4)

**Goal**: Simple web UI for non-technical users to anonymize text and configure settings

**Independent Test**: Open web interface, paste text, click Anonymize, see anonymized output

### Implementation for User Story 4

- [x] T039 [US4] Create API client service in frontend/src/services/api.ts
- [x] T040 [P] [US4] Create TextInput component in frontend/src/components/TextInput.tsx
- [x] T041 [P] [US4] Create TextOutput component in frontend/src/components/TextOutput.tsx
- [x] T042 [P] [US4] Create SubstitutionList component in frontend/src/components/SubstitutionList.tsx
- [x] T043 [US4] Create AnonymizePage with input/output/anonymize button in frontend/src/pages/AnonymizePage.tsx
- [x] T044 [P] [US4] Create EntityTypeToggle component in frontend/src/components/EntityTypeToggle.tsx
- [x] T045 [P] [US4] Create StrategySelector component in frontend/src/components/StrategySelector.tsx
- [x] T046 [P] [US4] Create ThresholdSlider component in frontend/src/components/ThresholdSlider.tsx
- [x] T047 [US4] Create ConfigPage with entity toggles and strategy config in frontend/src/pages/ConfigPage.tsx
- [x] T048 [P] [US4] Create StatsTable component in frontend/src/components/StatsTable.tsx
- [x] T049 [US4] Create StatsPage with statistics display and export button in frontend/src/pages/StatsPage.tsx
- [x] T050 [US4] Create main App component with navigation in frontend/src/App.tsx
- [x] T051 [US4] Configure frontend routing in frontend/src/main.tsx
- [x] T052 [US4] Add CORS middleware to backend for frontend access in backend/src/api/main.py

**Checkpoint**: User Story 4 complete - full web interface available

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T053 [P] Add input validation with max length checks in backend/src/api/schemas.py
- [x] T054 [P] Add structured error handling middleware in backend/src/api/middleware/error_handler.py
- [x] T055 [P] Configure logging without PII exposure in backend/src/logging_config.py
- [x] T056 [P] Add database index verification in backend/src/models/__init__.py
- [x] T057 Run quickstart.md validation to verify setup instructions
- [x] T058 Performance test with 100KB text input to verify <5s response (SC-001)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1's anonymizer but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Reads from PIIMapping created by US1 but independently testable
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Frontend calls backend APIs from US1-3 but independently testable with stubs

### Within Each User Story

- Models before services
- Services before endpoints/UI
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003, T004, T005 can run in parallel

**Phase 2 (Foundational)**:
- T008, T009, T010 can run in parallel (models)
- T013, T015 can run in parallel

**Phase 3 (US1)**: Sequential - each task builds on previous

**Phase 4 (US2)**:
- T030, T031, T032 can run in parallel (strategy operators)

**Phase 5 (US3)**: Sequential - stats service before endpoints

**Phase 6 (US4)**:
- T040, T041, T042 can run in parallel (components)
- T044, T045, T046, T048 can run in parallel (components)

**Phase 7 (Polish)**:
- T053, T054, T055, T056 can run in parallel

---

## Parallel Example: User Story 4

```bash
# Launch independent components together:
Task: "Create TextInput component in frontend/src/components/TextInput.tsx"
Task: "Create TextOutput component in frontend/src/components/TextOutput.tsx"
Task: "Create SubstitutionList component in frontend/src/components/SubstitutionList.tsx"

# Then build pages that use them:
Task: "Create AnonymizePage in frontend/src/pages/AnonymizePage.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test anonymization via curl/API
5. Deploy/demo if ready - core value delivered!

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test API → **MVP Ready!** (core anonymization)
3. Add User Story 2 → Test config changes → Deploy (configurable)
4. Add User Story 3 → Test stats → Deploy (auditable)
5. Add User Story 4 → Test web UI → Deploy (user-friendly)

### Suggested MVP Scope

**Phase 1 + Phase 2 + Phase 3 (User Story 1)** = Minimum Viable Product

This delivers:
- Working API with POST /anonymize and POST /anonymize/batch
- Consistent substitution (same PII → same substitute)
- Local SQLite storage
- No dependencies on US2-4

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Frontend (US4) can be deferred if API-only usage is acceptable
