/**
 * API client service for communicating with the PII Anonymizer backend.
 */

// Use relative path - works for both dev (proxy) and production (same origin)
const API_BASE = import.meta.env.DEV ? "http://localhost:8000" : "";

// Types
export interface Substitution {
  start: number;
  end: number;
  entity_type: string;
  original_length: number;
  substitute: string;
}

export interface AnonymizeMetadata {
  entities_detected: number;
  entities_anonymized: number;
  new_mappings_created: number;
  existing_mappings_used: number;
  processing_time_ms: number;
}

export interface AnonymizeResponse {
  anonymized_text: string;
  substitutions: Substitution[];
  metadata: AnonymizeMetadata;
}

export interface EntityTypeConfig {
  entity_type: string;
  enabled: boolean;
  strategy: string;
  strategy_params: Record<string, unknown> | null;
}

export interface Config {
  id: number;
  name: string;
  confidence_threshold: number;
  language: string;
  locale: string;
  entity_types: EntityTypeConfig[];
}

export interface LocaleMap {
  [key: string]: string;
}

export interface EntityTypeInfo {
  name: string;
  description: string;
}

export interface EntityTypeStats {
  entity_type: string;
  unique_values: number;
  total_substitutions: number;
}

export interface Stats {
  total_mappings: number;
  total_substitutions: number;
  by_entity_type: EntityTypeStats[];
  oldest_mapping: string | null;
  newest_mapping: string | null;
}

export interface Mapping {
  id: number;
  original_hash: string;
  substitute: string;
  entity_type: string;
  first_seen: string;
  last_used: string;
  substitution_count: number;
}

export interface MappingExportResponse {
  mappings: Mapping[];
  export_params: {
    since: string | null;
    until: string | null;
    entity_type: string | null;
  };
  total: number;
}

export interface MappingsResponse {
  mappings: Mapping[];
  total: number;
}

// API Functions

export async function anonymizeText(
  text: string,
  entityTypes?: string[],
  confidenceThreshold?: number
): Promise<AnonymizeResponse> {
  const response = await fetch(`${API_BASE}/anonymize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      entity_types: entityTypes,
      confidence_threshold: confidenceThreshold,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Anonymization failed");
  }

  return response.json();
}

export async function getConfig(): Promise<Config> {
  const response = await fetch(`${API_BASE}/config`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get config");
  }

  return response.json();
}

export async function updateConfig(updates: {
  confidence_threshold?: number;
  language?: string;
  locale?: string;
  entity_types?: Array<{
    entity_type: string;
    enabled?: boolean;
    strategy?: string;
    strategy_params?: Record<string, unknown>;
  }>;
}): Promise<Config> {
  const response = await fetch(`${API_BASE}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update config");
  }

  return response.json();
}

export async function getEntityTypes(): Promise<EntityTypeInfo[]> {
  const response = await fetch(`${API_BASE}/config/entity-types`);

  if (!response.ok) {
    throw new Error("Failed to get entity types");
  }

  const data = await response.json();
  return data.entity_types;
}

export async function getLocales(): Promise<LocaleMap> {
  const response = await fetch(`${API_BASE}/config/locales`);

  if (!response.ok) {
    throw new Error("Failed to get locales");
  }

  return response.json();
}

export async function getStats(): Promise<Stats> {
  const response = await fetch(`${API_BASE}/stats`);

  if (!response.ok) {
    throw new Error("Failed to get stats");
  }

  return response.json();
}

export async function exportStats(format: "csv" | "json" = "csv"): Promise<string | Stats> {
  const response = await fetch(`${API_BASE}/stats/export?format=${format}`);

  if (!response.ok) {
    throw new Error("Failed to export stats");
  }

  if (format === "csv") {
    return response.text();
  }

  return response.json();
}

export async function checkHealth(): Promise<{
  status: string;
  version: string;
  database_connected: boolean;
  mappings_count: number;
}> {
  const response = await fetch(`${API_BASE}/health`);

  if (!response.ok) {
    throw new Error("Health check failed");
  }

  return response.json();
}

// Mappings API

export async function getMappings(limit = 100, offset = 0): Promise<MappingsResponse> {
  const response = await fetch(`${API_BASE}/mappings?limit=${limit}&offset=${offset}`);

  if (!response.ok) {
    throw new Error("Failed to get mappings");
  }

  return response.json();
}

export async function updateMapping(id: number, substitute: string): Promise<Mapping> {
  const response = await fetch(`${API_BASE}/mappings/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ substitute }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update mapping");
  }

  return response.json();
}

export async function deleteMapping(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/mappings/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete mapping");
  }
}

export async function deleteAllMappings(): Promise<{ deleted_count: number }> {
  const response = await fetch(`${API_BASE}/mappings`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to delete mappings");
  }

  return response.json();
}

export async function exportMappings(
  since?: string,
  until?: string,
  entityType?: string,
  format: "json" | "csv" = "json"
): Promise<MappingExportResponse | string> {
  const params = new URLSearchParams();
  if (since) params.append("since", since);
  if (until) params.append("until", until);
  if (entityType) params.append("entity_type", entityType);
  params.append("format", format);

  const response = await fetch(`${API_BASE}/mappings/export?${params.toString()}`);

  if (!response.ok) {
    throw new Error("Failed to export mappings");
  }

  if (format === "csv") {
    return response.text();
  }

  return response.json();
}
