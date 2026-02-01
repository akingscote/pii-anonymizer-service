# Log Anonymization Scripts

Scripts for dumping logs from Azure Log Analytics and anonymizing PII using the PII Anonymizer Service.

## Setup

```bash
# Create virtual environment
cd scripts
uv venv

# Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Authenticate with Azure
az login
```

## Scripts

### dump_and_anonymize.py

Dumps logs from an Azure Log Analytics workspace and sends them through the PII anonymizer service.

**Usage:**
```bash
python dump_and_anonymize.py <service_url> [options]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `service_url` | URL of the PII anonymizer service (required) |
| `--workspace-id` | Log Analytics workspace ID (or set `LOG_ANALYTICS_WORKSPACE_ID` env var) |
| `--query` | KQL query to execute (default: `SigninLogs \| take 100`) |
| `--timespan` | Time range: `1h`, `30m`, `7d`, etc. (default: `24h`) |
| `--output` | Output filename prefix (default: `SigninLogs`) |
| `--batch-size` | Batch size for API calls (default: `100`) |

**Examples:**
```bash
# Basic usage
python dump_and_anonymize.py https://pii-anonymizer.whitebay-fc2657b5.uksouth.azurecontainerapps.io \
    --workspace-id "12345678-1234-1234-1234-123456789abc"

# Custom query and timespan
python dump_and_anonymize.py https://pii-anonymizer.whitebay-fc2657b5.uksouth.azurecontainerapps.io \
    --workspace-id "12345678-1234-1234-1234-123456789abc" \
    --query "SigninLogs | where ResultType != '0' | take 500" \
    --timespan 7d \
    --output FailedSignins

# Using environment variable for workspace ID
export LOG_ANALYTICS_WORKSPACE_ID="12345678-1234-1234-1234-123456789abc"
python dump_and_anonymize.py https://pii-anonymizer.whitebay-fc2657b5.uksouth.azurecontainerapps.io
```

**Output Files** (written to `scripts/data/`):
- `<output>.json` - Original logs
- `<output>_clean.json` - Anonymized logs

Default output: `data/SigninLogs.json` and `data/SigninLogs_clean.json`

### compare_logs.py

Compares original and anonymized log files to verify PII removal and show what changed.

**Usage:**
```bash
python compare_logs.py <original_file> <clean_file> [options]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `original_file` | Path to the original log file (JSON) |
| `clean_file` | Path to the anonymized log file (JSON) |
| `--show-samples` | Number of sample changes to display (default: `3`) |
| `--show-diff` | Number of entries to show unified diff for (default: `0`) |
| `--output-report` | Save comparison report to a JSON file |

**Examples:**
```bash
# Basic comparison
python compare_logs.py data/SigninLogs.json data/SigninLogs_clean.json

# Show more samples and unified diff
python compare_logs.py data/SigninLogs.json data/SigninLogs_clean.json \
    --show-samples 10 \
    --show-diff 5

# Export report to JSON
python compare_logs.py data/SigninLogs.json data/SigninLogs_clean.json \
    --output-report comparison_report.json
```

**Report Contents:**
- Summary statistics (total entries, modified/unchanged counts)
- PII pattern detection in both original and cleaned data (emails, phones, IPs, SSNs, credit cards)
- Changes grouped by field name
- Sample before/after comparisons

## Typical Workflow

```bash
# 1. Set up environment
cd scripts
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
az login

# 2. Dump and anonymize logs
export LOG_ANALYTICS_WORKSPACE_ID="your-workspace-id"
python dump_and_anonymize.py https://pii-anonymizer.whitebay-fc2657b5.uksouth.azurecontainerapps.io

# 3. Compare results
python compare_logs.py data/SigninLogs.json data/SigninLogs_clean.json --show-samples 5
```

## Finding Your Workspace ID

You can find your Log Analytics workspace ID in the Azure Portal:
1. Navigate to your Log Analytics workspace
2. Go to **Settings** > **Properties**
3. Copy the **Workspace ID** (GUID format)

Or via Azure CLI:
```bash
az monitor log-analytics workspace show \
    --resource-group <resource-group> \
    --workspace-name <workspace-name> \
    --query customerId -o tsv
```
