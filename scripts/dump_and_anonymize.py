#!/usr/bin/env python3
"""
Dump SigninLogs from Azure Log Analytics workspace and anonymize PII fields.

Usage:
    python dump_and_anonymize.py <service_url> [options]

Examples:
    python dump_and_anonymize.py https://pii-anonymizer.example.com
    python dump_and_anonymize.py https://pii-anonymizer.example.com --workspace-id abc123
    python dump_and_anonymize.py https://pii-anonymizer.example.com --timespan 7d --limit 500
"""

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

import requests
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus


# SigninLogs fields that contain PII and should be anonymized
PII_FIELDS = [
    # User identity fields
    "Identity",
    "UserDisplayName",
    "UserPrincipalName",
    "AlternateSignInName",
    "SignInIdentifier",
    # Network fields
    "IPAddress",
    "IPAddressFromResourceProvider",
    # GUIDs that could be used for tracking
    "UserId",
    "SessionId",
    "CorrelationId",
    "Id",
    "OriginalRequestId",
    "UniqueTokenIdentifier",
]

# Fields containing JSON with nested PII
JSON_PII_FIELDS = {
    "LocationDetails": ["city", "state", "latitude", "longitude"],
    "DeviceDetail": ["deviceId", "displayName"],
}


def parse_timespan(timespan_str: str) -> timedelta:
    """Parse a timespan string like '1h', '30m', '7d' into a timedelta."""
    unit = timespan_str[-1].lower()
    value = int(timespan_str[:-1])

    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    else:
        raise ValueError(f"Invalid timespan unit: {unit}. Use 'm' (minutes), 'h' (hours), or 'd' (days)")


def query_signinlogs(workspace_id: str, timespan: timedelta, limit: int) -> list[dict]:
    """Query Azure Log Analytics workspace for SigninLogs."""
    credential = DefaultAzureCredential()
    client = LogsQueryClient(credential)

    query = f"SigninLogs | take {limit}"

    print(f"Querying Log Analytics workspace: {workspace_id}")
    print(f"Query: {query}")
    print(f"Timespan: {timespan}")

    response = client.query_workspace(
        workspace_id=workspace_id,
        query=query,
        timespan=timespan
    )

    if response.status == LogsQueryStatus.PARTIAL:
        print("Warning: Query returned partial results")
        error = response.partial_error
        print(f"Partial error: {error.message}")
    elif response.status == LogsQueryStatus.FAILURE:
        raise Exception(f"Query failed: {response}")

    results = []
    for table in response.tables:
        columns = [col.name if hasattr(col, 'name') else col for col in table.columns]
        for row in table.rows:
            results.append(dict(zip(columns, row)))

    print(f"Retrieved {len(results)} SigninLogs entries")
    return results


def serialize_value(value) -> any:
    """Convert a value to JSON-serializable type."""
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    elif isinstance(value, (str, int, float, bool, type(None))):
        return value
    else:
        return str(value)


def serialize_log_entry(entry: dict) -> dict:
    """Convert log entry values to JSON-serializable types."""
    return {key: serialize_value(value) for key, value in entry.items()}


def extract_pii_values(logs: list[dict]) -> dict[str, list[str]]:
    """Extract PII values from logs, organized by field name."""
    pii_by_field = {field: [] for field in PII_FIELDS}

    for field, nested_keys in JSON_PII_FIELDS.items():
        for key in nested_keys:
            pii_by_field[f"{field}.{key}"] = []

    for log in logs:
        # Extract direct PII fields
        for field in PII_FIELDS:
            value = log.get(field)
            if value and isinstance(value, str) and value.strip():
                pii_by_field[field].append(value)

        # Extract nested PII from JSON fields
        for field, nested_keys in JSON_PII_FIELDS.items():
            json_str = log.get(field)
            if json_str and isinstance(json_str, str):
                try:
                    json_data = json.loads(json_str)
                    # Handle nested geoCoordinates object
                    if "geoCoordinates" in json_data and isinstance(json_data["geoCoordinates"], dict):
                        geo = json_data["geoCoordinates"]
                        for coord_key in ["latitude", "longitude"]:
                            if coord_key in geo and geo[coord_key] is not None:
                                pii_by_field[f"{field}.{coord_key}"].append(str(geo[coord_key]))
                    for key in nested_keys:
                        if key in ["latitude", "longitude"]:
                            continue  # Already handled above
                        value = json_data.get(key)
                        if value and isinstance(value, str) and value.strip() and not value.startswith("{PII"):
                            pii_by_field[f"{field}.{key}"].append(value)
                except json.JSONDecodeError:
                    pass

    return pii_by_field


def anonymize_texts(service_url: str, texts: list[str], batch_size: int = 100) -> dict[str, str]:
    """Send texts to the PII anonymizer service and return mapping of original to anonymized."""
    if not texts:
        return {}

    service_url = service_url.rstrip('/')
    endpoint = f"{service_url}/anonymize/batch"

    unique_texts = list(set(texts))
    all_results = []
    total_batches = (len(unique_texts) + batch_size - 1) // batch_size

    for i in range(0, len(unique_texts), batch_size):
        batch = unique_texts[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} texts)...")

        try:
            response = requests.post(
                endpoint,
                json={"texts": batch},
                headers={"Content-Type": "application/json"},
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            all_results.extend(result.get("results", []))
        except requests.exceptions.RequestException as e:
            print(f"  Error processing batch {batch_num}: {e}")
            for text in batch:
                all_results.append({"anonymized_text": text})

    return {
        text: result.get("anonymized_text", text)
        for text, result in zip(unique_texts, all_results)
    }


def apply_anonymization(logs: list[dict], anonymization_map: dict[str, str]) -> list[dict]:
    """Apply anonymization mapping to logs."""
    anonymized_logs = []

    for log in logs:
        anonymized_log = serialize_log_entry(log.copy())

        # Anonymize direct PII fields
        for field in PII_FIELDS:
            value = log.get(field)
            if value and isinstance(value, str) and value in anonymization_map:
                anonymized_log[field] = anonymization_map[value]

        # Anonymize nested JSON fields
        for field, nested_keys in JSON_PII_FIELDS.items():
            json_str = log.get(field)
            if json_str and isinstance(json_str, str):
                try:
                    json_data = json.loads(json_str)
                    modified = False
                    # Handle nested geoCoordinates
                    if "geoCoordinates" in json_data and isinstance(json_data["geoCoordinates"], dict):
                        geo = json_data["geoCoordinates"]
                        for coord_key in ["latitude", "longitude"]:
                            if coord_key in geo and geo[coord_key] is not None:
                                str_val = str(geo[coord_key])
                                if str_val in anonymization_map:
                                    # Try to preserve numeric type
                                    new_val = anonymization_map[str_val]
                                    try:
                                        geo[coord_key] = float(new_val)
                                    except (ValueError, TypeError):
                                        geo[coord_key] = new_val
                                    modified = True
                    for key in nested_keys:
                        if key in ["latitude", "longitude"]:
                            continue  # Already handled above
                        value = json_data.get(key)
                        if value and isinstance(value, str) and value in anonymization_map:
                            json_data[key] = anonymization_map[value]
                            modified = True
                    if modified:
                        anonymized_log[field] = json.dumps(json_data)
                except json.JSONDecodeError:
                    pass

        anonymized_logs.append(anonymized_log)

    return anonymized_logs


def main():
    parser = argparse.ArgumentParser(
        description="Dump SigninLogs from Azure Log Analytics and anonymize PII"
    )
    parser.add_argument(
        "service_url",
        help="URL of the PII anonymizer service"
    )
    parser.add_argument(
        "--workspace-id",
        required=False,
        help="Log Analytics workspace ID (or set LOG_ANALYTICS_WORKSPACE_ID env var)",
        default=None
    )
    parser.add_argument(
        "--timespan",
        default="24h",
        help="Timespan for the query, e.g., '1h', '30m', '7d' (default: '24h')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of log entries to retrieve (default: 100)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for anonymization requests (default: 100)"
    )

    args = parser.parse_args()

    import os
    workspace_id = args.workspace_id or os.environ.get("LOG_ANALYTICS_WORKSPACE_ID")
    if not workspace_id:
        print("Error: Workspace ID must be provided via --workspace-id or LOG_ANALYTICS_WORKSPACE_ID env var")
        sys.exit(1)

    # Query SigninLogs
    timespan = parse_timespan(args.timespan)
    logs = query_signinlogs(workspace_id, timespan, args.limit)

    if not logs:
        print("No logs retrieved. Exiting.")
        sys.exit(0)

    # Save original logs
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)

    original_file = data_dir / "SigninLogs.json"
    serialized_logs = [serialize_log_entry(log) for log in logs]
    with open(original_file, "w", encoding="utf-8") as f:
        json.dump(serialized_logs, f, indent=2, ensure_ascii=False)
    print(f"Saved original logs to: {original_file}")

    # Extract and anonymize PII
    print("\nExtracting PII fields...")
    pii_by_field = extract_pii_values(logs)

    # Collect all unique PII values
    all_pii_values = []
    for field, values in pii_by_field.items():
        unique_values = list(set(values))
        if unique_values:
            print(f"  {field}: {len(unique_values)} unique values")
            all_pii_values.extend(unique_values)

    all_pii_values = list(set(all_pii_values))
    print(f"\nTotal unique PII values to anonymize: {len(all_pii_values)}")

    if all_pii_values:
        print("\nAnonymizing PII...")
        anonymization_map = anonymize_texts(args.service_url, all_pii_values, args.batch_size)
        anonymized_logs = apply_anonymization(logs, anonymization_map)
    else:
        anonymized_logs = serialized_logs

    # Save anonymized logs
    clean_file = data_dir / "SigninLogs_clean.json"
    with open(clean_file, "w", encoding="utf-8") as f:
        json.dump(anonymized_logs, f, indent=2, ensure_ascii=False)
    print(f"Saved anonymized logs to: {clean_file}")

    # Summary
    substitutions_made = sum(
        1 for orig, anon in anonymization_map.items() if orig != anon
    ) if all_pii_values else 0

    print(f"\nSummary:")
    print(f"  - Total log entries: {len(logs)}")
    print(f"  - Unique PII values processed: {len(all_pii_values)}")
    print(f"  - PII values anonymized: {substitutions_made}")


if __name__ == "__main__":
    main()
