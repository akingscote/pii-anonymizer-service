"""Pydantic schemas for API request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


# === Health ===


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    database_connected: bool
    mappings_count: int


# === Anonymization ===


class AnonymizeRequest(BaseModel):
    """Request to anonymize text."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=1_000_000,
        description="Text to anonymize (max 1MB)",
    )
    entity_types: list[str] | None = Field(
        None, description="Entity types to detect (null = use config)"
    )
    confidence_threshold: float | None = Field(
        None, ge=0.0, le=1.0, description="Minimum confidence score (null = use config)"
    )


class Substitution(BaseModel):
    """Details of a single substitution made."""

    start: int = Field(..., description="Start position in original text")
    end: int = Field(..., description="End position in original text")
    entity_type: str = Field(..., description="Type of PII detected")
    original_length: int = Field(..., description="Length of original PII value")
    substitute: str = Field(..., description="Replacement value used")


class AnonymizeMetadata(BaseModel):
    """Metadata about the anonymization operation."""

    entities_detected: int = Field(..., description="Number of PII entities found")
    entities_anonymized: int = Field(..., description="Number of entities replaced")
    new_mappings_created: int = Field(..., description="New PII values encountered")
    existing_mappings_used: int = Field(..., description="Previously seen PII values")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class AnonymizeResponse(BaseModel):
    """Response from anonymization."""

    anonymized_text: str = Field(..., description="Text with PII replaced")
    substitutions: list[Substitution] = Field(..., description="List of substitutions made")
    metadata: AnonymizeMetadata = Field(..., description="Processing metadata")


class BatchAnonymizeRequest(BaseModel):
    """Request to anonymize multiple texts."""

    texts: list[str] = Field(..., max_length=1000, description="List of texts to anonymize")
    entity_types: list[str] | None = Field(
        None, description="Entity types to detect (null = use config)"
    )
    confidence_threshold: float | None = Field(
        None, ge=0.0, le=1.0, description="Minimum confidence score (null = use config)"
    )


class BatchMetadata(BaseModel):
    """Metadata for batch anonymization."""

    total_texts: int
    total_entities_detected: int
    total_processing_time_ms: int


class BatchAnonymizeResponse(BaseModel):
    """Response from batch anonymization."""

    results: list[AnonymizeResponse]
    batch_metadata: BatchMetadata


# === Configuration ===


class EntityTypeConfigSchema(BaseModel):
    """Entity type configuration."""

    entity_type: str
    enabled: bool
    strategy: str = Field(..., pattern="^(replace|mask|hash|redact)$")
    strategy_params: dict | None = None


class ConfigResponse(BaseModel):
    """Current configuration response."""

    id: int
    name: str
    confidence_threshold: float
    language: str
    locale: str = Field(..., description="Locale for synthetic data generation (e.g., en_US, de_DE)")
    entity_types: list[EntityTypeConfigSchema]


class EntityTypeConfigUpdate(BaseModel):
    """Update for a single entity type config."""

    entity_type: str
    enabled: bool | None = None
    strategy: str | None = Field(None, pattern="^(replace|mask|hash|redact)$")
    strategy_params: dict | None = None


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration."""

    confidence_threshold: float | None = Field(None, ge=0.0, le=1.0)
    language: str | None = Field(None, pattern="^[a-z]{2}$")
    locale: str | None = Field(None, pattern="^[a-z]{2}_[A-Z]{2}$", description="Locale code (e.g., en_US, de_DE)")
    entity_types: list[EntityTypeConfigUpdate] | None = None


class EntityTypeInfo(BaseModel):
    """Information about a supported entity type."""

    name: str
    description: str


class EntityTypesResponse(BaseModel):
    """List of available entity types."""

    entity_types: list[EntityTypeInfo]


# === Statistics ===


class EntityTypeStats(BaseModel):
    """Statistics for a single entity type."""

    entity_type: str
    unique_values: int
    total_substitutions: int


class StatsResponse(BaseModel):
    """Overall statistics response."""

    total_mappings: int = Field(..., description="Total unique PII values tracked")
    total_substitutions: int = Field(..., description="Total substitution operations performed")
    by_entity_type: list[EntityTypeStats]
    oldest_mapping: datetime | None = None
    newest_mapping: datetime | None = None


class SubstituteDetail(BaseModel):
    """Detail for a substitute value in stats."""

    substitute: str
    count: int
    first_seen: datetime


class EntityTypeStatsResponse(BaseModel):
    """Statistics for a specific entity type."""

    entity_type: str
    unique_values: int
    total_substitutions: int
    substitutes: list[SubstituteDetail]


# === Mappings ===


class MappingResponse(BaseModel):
    """A single PII mapping."""

    id: int
    original_hash: str = Field(..., description="SHA-256 hash of original value")
    substitute: str = Field(..., description="Substitute value used")
    entity_type: str = Field(..., description="Type of PII")
    first_seen: datetime
    last_used: datetime = Field(..., description="When this mapping was last used")
    substitution_count: int = Field(..., description="Times this mapping was used")


class MappingsListResponse(BaseModel):
    """List of all mappings."""

    mappings: list[MappingResponse]
    total: int


class MappingUpdateRequest(BaseModel):
    """Request to update a mapping's substitute value."""

    substitute: str = Field(..., min_length=1, max_length=500)


class DeleteMappingsResponse(BaseModel):
    """Response from deleting mappings."""

    deleted_count: int
    message: str


class MappingExportResponse(BaseModel):
    """Response from exporting mappings."""

    mappings: list[MappingResponse]
    export_params: dict = Field(..., description="Parameters used for export")
    total: int


# === Errors ===


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str
    details: dict | None = None
