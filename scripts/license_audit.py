"""Compare installed distribution license declarations to a hash-locked file."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import re
import sys
from pathlib import Path


REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)==([^\\\s;]+)")


def read_lock(path: Path) -> list[tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = REQ_RE.match(line)
        if match:
            name, version = match.groups()
            key = re.sub(r"[-_.]+", "-", name).lower()
            entries[key] = (name, version)
    return sorted(entries.values(), key=lambda item: item[0].lower())


def scan(path: Path, *, strict_installed: bool = False) -> dict:
    locked = read_lock(path)
    installed = {
        re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower(): dist
        for dist in metadata.distributions()
        if dist.metadata.get("Name")
    }
    rows = []
    for name, version in locked:
        dist = installed.get(re.sub(r"[-_.]+", "-", name).lower())
        if dist is None:
            rows.append({"name": name, "locked_version": version, "status": "NOT_INSTALLED"})
            continue
        actual = dist.version
        if actual != version:
            rows.append({"name": name, "locked_version": version, "installed_version": actual,
                         "status": "VERSION_MISMATCH"})
            continue
        headers = dist.metadata
        license_value = (headers.get("License-Expression") or headers.get("License") or "").strip()
        classifiers = [value.removeprefix("License :: ") for value in headers.get_all("Classifier", [])
                       if value.startswith("License :: ")]
        license_files = [value for value in headers.get_all("License-File", []) if value.strip()]
        declared = bool(license_value or classifiers or license_files)
        rows.append({"name": name, "locked_version": version,
                     "license_expression_or_text": license_value or None,
                     "license_classifiers": classifiers,
                     "license_files_declared": license_files,
                     "status": "DECLARED_REVIEW_REQUIRED" if declared else "MISSING_LICENSE_DECLARATION"})
    failures = [row for row in rows if row["status"] in {"VERSION_MISMATCH", "MISSING_LICENSE_DECLARATION"}
                or (strict_installed and row["status"] == "NOT_INSTALLED")]
    return {"status": "PASS" if not failures else "FAIL",
            "lock_file": path.as_posix(),
            "lock_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "locked_distribution_count": len(locked), "strict_installed": strict_installed,
            "manual_legal_review_required": True, "findings": rows, "failure_count": len(failures)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check locked dependencies have matching installed versions and declared license metadata.")
    parser.add_argument("--lock", type=Path, default=Path("requirements-dev.lock.txt"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict-installed", action="store_true",
                        help="fail if a locked package is absent; use after installing the full lock")
    args = parser.parse_args()
    result = scan(args.lock, strict_installed=args.strict_installed)
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
