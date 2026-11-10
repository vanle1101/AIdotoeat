"""Offline duplicate-pair CSV exporter draft, skill contract version 1."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Mapping


SKILL_ID = "duplicate-csv-export@1"
FIELDS = ("file_a", "file_b", "reason")


def render_csv(pairs: Iterable[Mapping[str, Any]]) -> str:
    """Render stable CSV for duplicate file pairs; pair order is canonicalized."""
    normalized: set[tuple[str, str, str]] = set()
    for item in pairs:
        if not isinstance(item, Mapping):
            raise ValueError("each duplicate pair must be an object")
        left, right = str(item.get("file_a", "")).strip(), str(item.get("file_b", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if not left or not right or left == right or len(left) > 1024 or len(right) > 1024 or len(reason) > 500:
            raise ValueError("duplicate pair fields are invalid")
        file_a, file_b = sorted((left, right), key=str.casefold)
        normalized.add((file_a, file_b, reason))
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for file_a, file_b, reason in sorted(normalized, key=lambda row: (row[0].casefold(), row[1].casefold(), row[2].casefold())):
        writer.writerow({"file_a": file_a, "file_b": file_b, "reason": reason})
    return buffer.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export duplicate file pairs from JSON to CSV")
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input_json.read_text(encoding="utf-8"))
        pairs = payload.get("duplicates") if isinstance(payload, dict) else None
        if not isinstance(pairs, list):
            raise ValueError("input JSON must contain a duplicates array")
        csv_text = render_csv(pairs)
        args.output_csv.write_text(csv_text, encoding="utf-8-sig", newline="")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"duplicate CSV export failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    return 0


def run_contract_tests() -> dict[str, Any]:
    """Bounded in-process QA of the exact function shipped in the draft artifact."""
    import csv

    pairs = [
        {"file_a": "資料/a.csv", "file_b": "資料/b.csv", "reason": "same hash, exact"},
        {"file_a": "資料/b.csv", "file_b": "資料/a.csv", "reason": "same hash, exact"},
    ]
    rendered = render_csv(pairs)
    rows = list(csv.DictReader(StringIO(rendered, newline="")))
    checks = {
        "header_and_unicode": rendered.startswith("file_a,file_b,reason\n") and rows[0]["file_a"] == "資料/a.csv",
        "stable_unordered_pairs": len(rows) == 1,
        "csv_quoting": rows[0]["reason"] == "same hash, exact",
    }
    try:
        render_csv([{"file_a": "same", "file_b": "same"}])
        checks["invalid_pair_rejected"] = False
    except ValueError:
        checks["invalid_pair_rejected"] = True
    return {"passed": all(checks.values()), "checks": checks, "row_count": len(rows)}


if __name__ == "__main__":
    raise SystemExit(main())
