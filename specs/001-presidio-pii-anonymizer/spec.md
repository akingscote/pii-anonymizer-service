# Feature Specification: Offline PII Anonymizer

**Feature Branch**: `001-presidio-pii-anonymizer`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "Offline PII anonymizer using Microsoft Presidio. Core requirements: (1) Uses Presidio's analyzer for detection and anonymizer for substitution, (2) Frontend for configuring which PII entities to detect and anonymization strategies, (3) Accepts generic string input so callers can parse their own formats (parquet/csv/json/etc), (4) Consistent substitution - maintains a local mapping store so the same detected PII value always gets the same substitute across all occurrences, (5) Tracks metadata including total substitution count per original value, (6) Local SQLite or similar data store for mappings - no cloud dependencies, (7) Designed as a library/service that can later integrate with Microsoft Sentinel database dumps in a separate project"

## User Scenarios & Testing

### User Story 1 - Anonymize Text with Consistent Substitution (Priority: P1)

A data analyst needs to anonymize sensitive data before sharing it with external teams. They provide text strings containing PII (names, emails, phone numbers, etc.) and receive anonymized output where each unique PII value is consistently replaced with the same substitute across all occurrences.

**Why this priority**: This is the core value proposition - ensuring data integrity through consistent substitution. Without this, the anonymized data would be unusable for analysis as relationships between records would be broken.

**Independent Test**: Can be tested by submitting text with repeated PII values and verifying the same substitute is used each time, delivering immediately usable anonymized data.

**Acceptance Scenarios**:

1. **Given** a text string containing the email "john.doe@example.com" appearing 3 times, **When** the user submits for anonymization, **Then** all 3 occurrences are replaced with the identical substitute email.
2. **Given** a previously anonymized value "john.doe@example.com" → "user_a1b2c3@anon.local", **When** new text containing "john.doe@example.com" is submitted, **Then** the same substitute "user_a1b2c3@anon.local" is used.
3. **Given** text with multiple PII types (email, phone, name), **When** submitted for anonymization, **Then** each PII type is detected and replaced with type-appropriate substitutes.

---

### User Story 2 - Configure Detection and Anonymization Settings (Priority: P2)

An administrator needs to configure which PII entities the system should detect (e.g., only emails and phone numbers, not names) and select anonymization strategies (e.g., replacement with fake data, masking, or hashing).

**Why this priority**: Configuration enables users to tailor the system to their specific compliance requirements and use cases. Essential for production use but the system can work with sensible defaults.

**Independent Test**: Can be tested by changing configuration settings and verifying only selected entity types are detected and the chosen anonymization strategy is applied.

**Acceptance Scenarios**:

1. **Given** detection configured for only EMAIL and PHONE_NUMBER entities, **When** text containing names, emails, and phone numbers is submitted, **Then** only emails and phone numbers are anonymized while names remain unchanged.
2. **Given** anonymization strategy set to "mask" for credit cards, **When** text with "4111-1111-1111-1111" is submitted, **Then** the output shows "****-****-****-1111" (last 4 digits visible).
3. **Given** anonymization strategy set to "replace" for emails, **When** text with emails is submitted, **Then** realistic-looking substitute emails are generated.

---

### User Story 3 - View Substitution Metadata and Statistics (Priority: P3)

A compliance officer needs to review what PII was detected and how many times each value was substituted, for audit purposes and to verify the anonymization process worked correctly.

**Why this priority**: Metadata tracking provides transparency and auditability. Important for compliance but not required for basic anonymization functionality.

**Independent Test**: Can be tested by anonymizing text and then querying metadata to see substitution counts and mappings (without revealing original values inappropriately).

**Acceptance Scenarios**:

1. **Given** text has been anonymized containing 5 occurrences of one email and 3 of another, **When** the user views substitution statistics, **Then** they see each substitute with its occurrence count (5 and 3 respectively).
2. **Given** multiple anonymization sessions have occurred, **When** the user requests total statistics, **Then** they see aggregate counts per entity type (e.g., "Emails: 47 total substitutions across 12 unique values").
3. **Given** a specific substitute value, **When** the user queries its metadata, **Then** they see the entity type, first seen timestamp, and total substitution count.

---

### User Story 4 - Access via Web Interface (Priority: P4)

A non-technical user needs a simple web interface to paste text, configure basic settings, and receive anonymized output without needing to use command-line tools or write code.

**Why this priority**: The frontend improves accessibility but the core library can function without it. Power users may prefer API/CLI access.

**Independent Test**: Can be tested by opening the web interface, pasting text, and verifying anonymized output is displayed.

**Acceptance Scenarios**:

1. **Given** the web interface is running, **When** a user pastes text into the input field and clicks "Anonymize", **Then** anonymized text appears in the output field.
2. **Given** the configuration panel is open, **When** the user toggles entity types on/off, **Then** subsequent anonymization respects these settings.
3. **Given** anonymization has completed, **When** the user clicks "View Statistics", **Then** a summary of detected entities and substitution counts is displayed.

---

### Edge Cases

- What happens when the same text value could be multiple PII types (e.g., "Jordan" could be a name or location)? The system uses Presidio's confidence scoring and configurable thresholds to resolve ambiguity.
- How does the system handle PII that spans multiple lines or has unusual formatting? The detection operates on the full text input, handling multi-line content.
- What happens when the mapping database becomes very large? The local database should handle millions of mappings efficiently through proper indexing.
- How does the system handle non-English PII? Presidio supports multiple languages; the system should allow language configuration.
- What happens if the same substitute is accidentally generated for two different original values? The system must ensure unique substitutes per original value through uniqueness constraints.

## Requirements

### Functional Requirements

- **FR-001**: System MUST detect PII entities using Microsoft Presidio's analyzer with configurable entity types.
- **FR-002**: System MUST anonymize detected PII using Microsoft Presidio's anonymizer with configurable strategies (replace, mask, hash, redact).
- **FR-003**: System MUST accept text input as strings, remaining format-agnostic to support any upstream parsing (CSV, JSON, Parquet, etc.).
- **FR-004**: System MUST maintain a persistent local mapping store that maps original PII values to their substitutes.
- **FR-005**: System MUST check the mapping store before generating new substitutes, reusing existing mappings for consistent anonymization.
- **FR-006**: System MUST generate type-appropriate substitute values (e.g., fake emails for emails, realistic names for names).
- **FR-007**: System MUST track metadata for each mapping including: entity type, first seen timestamp, and total substitution count.
- **FR-008**: System MUST increment the substitution count each time a mapping is reused.
- **FR-009**: System MUST provide a web-based frontend for configuration and text anonymization.
- **FR-010**: System MUST allow configuration of which PII entity types to detect (enable/disable per type).
- **FR-011**: System MUST allow configuration of anonymization strategy per entity type.
- **FR-012**: System MUST allow configuration of detection confidence threshold.
- **FR-013**: System MUST store all mappings and configuration locally with no cloud dependencies.
- **FR-014**: System MUST provide an API/library interface for programmatic access (in addition to the frontend).
- **FR-015**: System MUST support batch processing of multiple text strings in a single request.
- **FR-016**: System MUST return anonymization results including the anonymized text and metadata about substitutions made.

### Key Entities

- **PIIMapping**: Represents a mapping from original PII value to substitute. Attributes: original value hash (for secure storage), substitute value, entity type, first seen timestamp, substitution count.
- **AnonymizationConfig**: User's current configuration. Attributes: enabled entity types, anonymization strategy per type, confidence threshold, language setting.
- **AnonymizationResult**: Output of an anonymization operation. Attributes: anonymized text, list of substitutions made (position, entity type, substitute used), processing metadata.
- **SubstitutionRecord**: Individual substitution within a result. Attributes: start/end position, entity type, original length, substitute value.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can anonymize a text document and receive results within 5 seconds for documents up to 100KB.
- **SC-002**: 100% of identical PII values within a session and across sessions receive identical substitutes.
- **SC-003**: Users can configure entity types and strategies through the frontend in under 1 minute.
- **SC-004**: The system operates fully offline after initial setup with no network requests during anonymization.
- **SC-005**: Substitution metadata accurately reflects actual substitution counts with zero discrepancy.
- **SC-006**: The system can handle mapping stores with 100,000+ unique entries without noticeable performance degradation.
- **SC-007**: Users can export anonymization statistics for compliance reporting.

## Assumptions

- Users will parse their source data (CSV, JSON, Parquet, etc.) into text strings before submitting to this system.
- The local SQLite database provides sufficient performance and reliability for the expected mapping volume.
- Presidio's default entity recognizers cover the required PII types; custom recognizers are out of scope for initial release.
- The frontend will be a simple single-page web application suitable for local use.
- Original PII values will be stored as secure hashes in the mapping database to minimize exposure risk.
- The system is designed for single-user or small-team local use, not multi-tenant deployment.

## Out of Scope

- Direct integration with Microsoft Sentinel (planned for future separate project).
- Parsing of specific file formats (CSV, JSON, Parquet) - callers handle this upstream.
- Multi-user authentication and authorization.
- Cloud deployment and scaling.
- De-anonymization / reverse lookup functionality.
- Custom PII recognizer development.
