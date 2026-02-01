#!/usr/bin/env python3
"""
Compare original log data with anonymized (cleaned) data to verify PII removal.

Usage:
    python compare_logs.py <original_file> <clean_file>

Examples:
    python compare_logs.py logs.json logs_clean.json
    python compare_logs.py logs.json logs_clean.json --show-samples 5
"""

import argparse
import json
import re
import sys
from collections import Counter
from difflib import unified_diff
from pathlib import Path


PII_PATTERNS = {
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone": re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b'),
    "ip_address": re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
    "credit_card": re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
    "ssn": re.compile(r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b'),
    "date": re.compile(r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12][0-9]|3[01])[/-](?:19|20)?[0-9]{2}\b'),
}


def load_json_file(filepath: Path) -> list[dict]:
    """Load a JSON file containing a list of log entries."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        raise ValueError(f"Unexpected JSON structure in {filepath}")


def extract_all_text_values(obj, prefix="") -> list[tuple[str, str]]:
    """Recursively extract all string values from a nested structure."""
    results = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            results.extend(extract_all_text_values(value, path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            path = f"{prefix}[{i}]"
            results.extend(extract_all_text_values(item, path))
    elif isinstance(obj, str) and obj:
        results.append((prefix, obj))

    return results


def find_pii_matches(text: str) -> dict[str, list[str]]:
    """Find potential PII matches in text using regex patterns."""
    matches = {}
    for pii_type, pattern in PII_PATTERNS.items():
        found = pattern.findall(text)
        if found:
            matches[pii_type] = found
    return matches


def compute_diff_stats(original: list[dict], clean: list[dict]) -> dict:
    """Compute statistics about differences between original and clean data."""
    stats = {
        "total_entries": len(original),
        "modified_entries": 0,
        "unchanged_entries": 0,
        "field_changes": Counter(),
        "total_changes": 0,
        "pii_in_original": Counter(),
        "pii_in_clean": Counter(),
        "sample_changes": [],
    }

    for i, (orig_entry, clean_entry) in enumerate(zip(original, clean)):
        orig_values = dict(extract_all_text_values(orig_entry))
        clean_values = dict(extract_all_text_values(clean_entry))

        entry_modified = False

        for path, orig_text in orig_values.items():
            clean_text = clean_values.get(path, "")

            for pii_type, matches in find_pii_matches(orig_text).items():
                stats["pii_in_original"][pii_type] += len(matches)

            for pii_type, matches in find_pii_matches(clean_text).items():
                stats["pii_in_clean"][pii_type] += len(matches)

            if orig_text != clean_text:
                entry_modified = True
                stats["total_changes"] += 1
                field_name = path.split(".")[0] if "." in path else path.split("[")[0]
                stats["field_changes"][field_name] += 1

                if len(stats["sample_changes"]) < 20:
                    stats["sample_changes"].append({
                        "entry_index": i,
                        "field": path,
                        "original": orig_text[:200] + ("..." if len(orig_text) > 200 else ""),
                        "cleaned": clean_text[:200] + ("..." if len(clean_text) > 200 else ""),
                    })

        if entry_modified:
            stats["modified_entries"] += 1
        else:
            stats["unchanged_entries"] += 1

    return stats


def generate_detailed_diff(original: list[dict], clean: list[dict], max_entries: int = 5) -> list[str]:
    """Generate unified diff for a sample of entries."""
    diffs = []

    count = 0
    for i, (orig, cleaned) in enumerate(zip(original, clean)):
        orig_json = json.dumps(orig, indent=2, ensure_ascii=False, sort_keys=True)
        clean_json = json.dumps(cleaned, indent=2, ensure_ascii=False, sort_keys=True)

        if orig_json != clean_json:
            diff = list(unified_diff(
                orig_json.splitlines(),
                clean_json.splitlines(),
                fromfile=f"entry[{i}] original",
                tofile=f"entry[{i}] cleaned",
                lineterm=""
            ))
            if diff:
                diffs.append("\n".join(diff))
                count += 1
                if count >= max_entries:
                    break

    return diffs


def generate_markdown_report(stats: dict, output_path: Path):
    """Generate a markdown report with diff table."""
    lines = [
        "# SigninLogs Anonymization Report",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total log entries | {stats['total_entries']} |",
        f"| Modified entries | {stats['modified_entries']} ({100*stats['modified_entries']/max(stats['total_entries'],1):.1f}%) |",
        f"| Unchanged entries | {stats['unchanged_entries']} |",
        f"| Total field changes | {stats['total_changes']} |",
        "",
        "## Changes by Field",
        "",
        "| Field | Changes |",
        "|-------|---------|",
    ]

    for field, count in stats['field_changes'].most_common():
        lines.append(f"| {field} | {count} |")

    lines.extend([
        "",
        "## Anonymization Details",
        "",
        "| Entry | Field | Original | Anonymized |",
        "|-------|-------|----------|------------|",
    ])

    for change in stats['sample_changes']:
        # Escape pipe characters and truncate for table readability
        orig = change['original'].replace('|', '\\|')[:80]
        clean = change['cleaned'].replace('|', '\\|')[:80]
        if len(change['original']) > 80:
            orig += "..."
        if len(change['cleaned']) > 80:
            clean += "..."
        lines.append(f"| {change['entry_index']} | {change['field']} | `{orig}` | `{clean}` |")

    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def print_report(stats: dict, show_samples: int = 3):
    """Print a formatted comparison report."""
    print("=" * 70)
    print("LOG COMPARISON REPORT")
    print("=" * 70)

    print("\n## Summary")
    print(f"  Total log entries: {stats['total_entries']}")
    print(f"  Modified entries:  {stats['modified_entries']} ({100*stats['modified_entries']/max(stats['total_entries'],1):.1f}%)")
    print(f"  Unchanged entries: {stats['unchanged_entries']}")
    print(f"  Total field changes: {stats['total_changes']}")

    print("\n## PII Detection (Regex-based)")
    print("  Original data:")
    if stats['pii_in_original']:
        for pii_type, count in stats['pii_in_original'].most_common():
            print(f"    - {pii_type}: {count} potential matches")
    else:
        print("    - No common PII patterns detected")

    print("  Cleaned data:")
    if stats['pii_in_clean']:
        for pii_type, count in stats['pii_in_clean'].most_common():
            print(f"    - {pii_type}: {count} potential matches")
    else:
        print("    - No common PII patterns detected")

    pii_removed = sum(stats['pii_in_original'].values()) - sum(stats['pii_in_clean'].values())
    if pii_removed > 0:
        print(f"  \u2713 Reduced potential PII matches by {pii_removed}")
    elif pii_removed < 0:
        print(f"  \u26a0 Warning: More PII patterns in cleaned data ({-pii_removed} more)")

    if stats['field_changes']:
        print("\n## Changes by Field")
        for field, count in stats['field_changes'].most_common(10):
            print(f"    - {field}: {count} changes")

    if show_samples > 0 and stats['sample_changes']:
        print(f"\n## Sample Changes (showing {min(show_samples, len(stats['sample_changes']))})")
        for i, change in enumerate(stats['sample_changes'][:show_samples]):
            print(f"\n  [{i+1}] Entry {change['entry_index']}, Field: {change['field']}")
            print(f"      Original: {change['original']}")
            print(f"      Cleaned:  {change['cleaned']}")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Compare original and anonymized log files"
    )
    parser.add_argument(
        "original_file",
        type=Path,
        help="Path to the original log file (JSON)"
    )
    parser.add_argument(
        "clean_file",
        type=Path,
        help="Path to the anonymized/cleaned log file (JSON)"
    )
    parser.add_argument(
        "--show-samples",
        type=int,
        default=3,
        help="Number of sample changes to display (default: 3)"
    )
    parser.add_argument(
        "--show-diff",
        type=int,
        default=0,
        help="Number of entries to show unified diff for (default: 0)"
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=None,
        help="Save the comparison report to a JSON file"
    )

    args = parser.parse_args()

    if not args.original_file.exists():
        print(f"Error: Original file not found: {args.original_file}")
        sys.exit(1)

    if not args.clean_file.exists():
        print(f"Error: Clean file not found: {args.clean_file}")
        sys.exit(1)

    print(f"Loading original file: {args.original_file}")
    original = load_json_file(args.original_file)

    print(f"Loading clean file: {args.clean_file}")
    clean = load_json_file(args.clean_file)

    if len(original) != len(clean):
        print(f"Warning: File lengths differ - original: {len(original)}, clean: {len(clean)}")
        min_len = min(len(original), len(clean))
        original = original[:min_len]
        clean = clean[:min_len]

    print("Computing comparison statistics...")
    stats = compute_diff_stats(original, clean)

    print_report(stats, args.show_samples)

    # Generate markdown report
    data_dir = Path(__file__).parent / "data"
    md_report_path = data_dir / "SigninLogs_diff.md"
    generate_markdown_report(stats, md_report_path)
    print(f"\nMarkdown report saved to: {md_report_path}")

    if args.show_diff > 0:
        print("\n## Unified Diff (sample entries)")
        diffs = generate_detailed_diff(original, clean, args.show_diff)
        for diff in diffs:
            print(diff)
            print()

    if args.output_report:
        report = {
            "summary": {
                "total_entries": stats["total_entries"],
                "modified_entries": stats["modified_entries"],
                "unchanged_entries": stats["unchanged_entries"],
                "total_changes": stats["total_changes"],
            },
            "pii_detection": {
                "original": dict(stats["pii_in_original"]),
                "clean": dict(stats["pii_in_clean"]),
            },
            "field_changes": dict(stats["field_changes"]),
            "sample_changes": stats["sample_changes"],
        }
        with open(args.output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to: {args.output_report}")


if __name__ == "__main__":
    main()
