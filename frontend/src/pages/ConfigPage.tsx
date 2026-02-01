import { useState, useEffect } from "react";
import {
  getConfig,
  updateConfig,
  getEntityTypes,
  getLocales,
  type Config,
  type EntityTypeInfo,
  type LocaleMap,
} from "../services/api";

const STRATEGIES = [
  { value: "replace", label: "Replace", description: "Replace with fake but realistic data" },
  { value: "mask", label: "Mask", description: "Partially hide with asterisks" },
  { value: "hash", label: "Hash", description: "Replace with hashed value" },
  { value: "redact", label: "Redact", description: "Remove completely with [REDACTED]" },
];

export function ConfigPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [entityTypeInfos, setEntityTypeInfos] = useState<EntityTypeInfo[]>([]);
  const [locales, setLocales] = useState<LocaleMap>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [configData, entityTypes, localesData] = await Promise.all([
        getConfig(),
        getEntityTypes(),
        getLocales(),
      ]);
      setConfig(configData);
      setEntityTypeInfos(entityTypes);
      setLocales(localesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load configuration");
    } finally {
      setIsLoading(false);
    }
  };

  const handleThresholdChange = (value: number) => {
    if (config) {
      setConfig({ ...config, confidence_threshold: value });
    }
  };

  const handleLocaleChange = (locale: string) => {
    if (config) {
      setConfig({ ...config, locale });
    }
  };

  const handleEntityToggle = (entityType: string, enabled: boolean) => {
    if (!config) return;

    const updatedTypes = config.entity_types.map((et) =>
      et.entity_type === entityType ? { ...et, enabled } : et
    );

    if (!updatedTypes.find((et) => et.entity_type === entityType)) {
      updatedTypes.push({
        entity_type: entityType,
        enabled,
        strategy: "replace",
        strategy_params: null,
      });
    }

    setConfig({ ...config, entity_types: updatedTypes });
  };

  const handleStrategyChange = (entityType: string, strategy: string) => {
    if (!config) return;

    const updatedTypes = config.entity_types.map((et) =>
      et.entity_type === entityType ? { ...et, strategy } : et
    );

    setConfig({ ...config, entity_types: updatedTypes });
  };

  const handleSave = async () => {
    if (!config) return;

    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const updated = await updateConfig({
        confidence_threshold: config.confidence_threshold,
        locale: config.locale,
        entity_types: config.entity_types.map((et) => ({
          entity_type: et.entity_type,
          enabled: et.enabled,
          strategy: et.strategy,
        })),
      });
      setConfig(updated);
      setSuccessMessage("Configuration saved successfully");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save configuration");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <svg
          className="animate-spin h-8 w-8 text-primary-600"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="text-center py-12 text-red-600">
        Failed to load configuration. Please refresh.
      </div>
    );
  }

  const getEntityConfig = (entityType: string) => {
    return config.entity_types.find((et) => et.entity_type === entityType);
  };

  const enabledTypes = config.entity_types.filter((et) => et.enabled);

  // Sort locales by description for better UX
  const sortedLocales = Object.entries(locales).sort((a, b) =>
    a[1].localeCompare(b[1])
  );

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configure PII detection and anonymization behavior
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
          <svg
            className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Success */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start space-x-3">
          <svg
            className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
          <p className="text-green-700">{successMessage}</p>
        </div>
      )}

      {/* Locale Selection */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Locale / Region</h2>
        <p className="text-sm text-gray-500 mb-4">
          Select the locale for generating synthetic data. This affects the format of names,
          phone numbers, addresses, and other generated values to match regional conventions.
        </p>
        <div className="max-w-md">
          <select
            value={config.locale}
            onChange={(e) => handleLocaleChange(e.target.value)}
            className="input-field"
          >
            {sortedLocales.map(([code, description]) => (
              <option key={code} value={code}>
                {description} ({code})
              </option>
            ))}
          </select>
        </div>
        <p className="mt-2 text-xs text-gray-400">
          Current: {locales[config.locale] || config.locale}
        </p>
      </div>

      {/* Detection Threshold */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Detection Threshold</h2>
        <p className="text-sm text-gray-500 mb-4">
          Minimum confidence score for PII detection. Higher values mean fewer false positives
          but may miss some PII.
        </p>
        <div className="space-y-4">
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={config.confidence_threshold}
            onChange={(e) => handleThresholdChange(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
          />
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">0% (Detect more)</span>
            <span className="font-medium text-primary-600">
              {Math.round(config.confidence_threshold * 100)}%
            </span>
            <span className="text-gray-500">100% (Stricter)</span>
          </div>
        </div>
      </div>

      {/* Entity Types */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Entity Types</h2>
        <p className="text-sm text-gray-500 mb-4">
          Enable or disable detection for specific types of personal information.
        </p>
        <div className="space-y-2">
          {entityTypeInfos.map((info) => {
            const entityConfig = getEntityConfig(info.name);
            const isEnabled = entityConfig?.enabled ?? true;
            return (
              <label
                key={info.name}
                className={`flex items-center justify-between p-4 rounded-lg border cursor-pointer transition-colors ${
                  isEnabled
                    ? "bg-primary-50 border-primary-200"
                    : "bg-gray-50 border-gray-200 hover:bg-gray-100"
                }`}
              >
                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={isEnabled}
                    onChange={(e) => handleEntityToggle(info.name, e.target.checked)}
                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  />
                  <div>
                    <p className="font-medium text-gray-900">{info.name}</p>
                    <p className="text-sm text-gray-500">{info.description}</p>
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* Anonymization Strategies */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Anonymization Strategies</h2>
        <p className="text-sm text-gray-500 mb-4">
          Choose how each enabled entity type should be anonymized.
        </p>
        {enabledTypes.length > 0 ? (
          <div className="space-y-4">
            {enabledTypes.map((et) => (
              <div
                key={et.entity_type}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4 p-4 bg-gray-50 rounded-lg"
              >
                <span className="font-medium text-gray-900">{et.entity_type}</span>
                <select
                  value={et.strategy}
                  onChange={(e) => handleStrategyChange(et.entity_type, e.target.value)}
                  className="input-field w-full sm:w-48"
                >
                  {STRATEGIES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label} - {s.description}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            Enable entity types above to configure strategies
          </div>
        )}
      </div>

      {/* Save Button */}
      <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary flex items-center justify-center space-x-2 w-full sm:w-auto"
        >
          {isSaving ? (
            <>
              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>Saving...</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span>Save Configuration</span>
            </>
          )}
        </button>
        <button onClick={loadData} className="btn-secondary w-full sm:w-auto">
          Reset
        </button>
      </div>
    </div>
  );
}
