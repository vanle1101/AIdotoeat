"""Read-only validation and source-citation helpers for public GitHub issues."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit


ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}


def validate_source(source: Mapping[str, Any]) -> dict[str, Any]:
    source_id = str(source.get("source_id", ""))
    uri = str(source.get("uri", ""))
    title = str(source.get("title", ""))
    body = str(source.get("body", ""))
    license_id = str(source.get("license", ""))
    parts = urlsplit(uri)
    segments = [part for part in parts.path.split("/") if part]
    if (parts.scheme != "https" or parts.hostname != "github.com" or parts.username or parts.password
            or parts.query or parts.fragment or len(segments) != 4 or segments[2] != "issues"
            or not segments[3].isdigit()):
        raise ValueError("source must be a canonical public GitHub issue URL")
    if license_id not in ALLOWED_LICENSES:
        raise ValueError("source repository license is not in the permitted allowlist")
    if not source_id or len(source_id) > 120 or not title.strip() or len(title) > 240 or len(body) > 6000:
        raise ValueError("source snapshot exceeds its identity or size limits")
    if re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", f"{title}\n{body}", re.I):
        raise ValueError("source snapshot contains a personal email address")
    if re.search(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)", f"{title}\n{body}"):
        raise ValueError("source snapshot may contain a personal phone number")
    canonical = {"source_id": source_id, "uri": uri, "title": title.strip(), "body": body,
                 "license": license_id, "state": str(source.get("state", "unknown")).lower(),
                 "claims": dict(source.get("claims", {}))}
    canonical["sha256"] = hashlib.sha256((title + "\n" + body).encode("utf-8")).hexdigest()
    return canonical


def verify_sources(sources: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not 1 <= len(sources) <= 5:
        return {"status": "BLOCKED", "reason_code": "source_count_out_of_bounds", "verified_sources": []}
    try:
        normalized = [validate_source(item) for item in sources]
    except (TypeError, ValueError) as exc:
        return {"status": "BLOCKED", "reason_code": "source_validation_failed",
                "detail": str(exc), "verified_sources": []}
    seen_ids = set()
    claim_values: dict[str, set[str]] = {}
    for source in normalized:
        if source["source_id"] in seen_ids:
            return {"status": "BLOCKED", "reason_code": "duplicate_source_id", "verified_sources": []}
        seen_ids.add(source["source_id"])
        for claim, value in source["claims"].items():
            if not isinstance(claim, str) or not isinstance(value, (str, int, float, bool)):
                return {"status": "BLOCKED", "reason_code": "invalid_source_claim", "verified_sources": []}
            claim_values.setdefault(claim.strip().lower(), set()).add(str(value).strip().lower())
    conflicts = sorted(key for key, values in claim_values.items() if len(values) > 1)
    if conflicts:
        return {"status": "BLOCKED", "reason_code": "contradictory_research",
                "conflicting_claims": conflicts, "verified_sources": normalized}
    quotes = []
    for source in normalized:
        quotes.append({"source_id": source["source_id"], "source_uri": source["uri"],
                       "source_sha256": source["sha256"], "quote": source["title"]})
    return {"status": "READY", "verified_sources": normalized, "verified_quotes": quotes,
            "conflicting_claims": []}
