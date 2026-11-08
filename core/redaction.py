"""Small privacy helpers that preserve opaque identifiers while masking direct numbers."""
from __future__ import annotations

import re


_UUID_VALUE_RE = re.compile(r"(?i)\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b")
_HEX_DIGEST_RE = re.compile(r"(?i)(?<![0-9a-f])(?:[0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}|[0-9a-f]{96}|[0-9a-f]{128})(?![0-9a-f])")
_LONG_NUMBER_RE = re.compile(r"(?<!\d)\d{8,18}(?!\d)")


def redact_long_numbers_preserving_ids(value: str) -> str:
    """Mask account-like number runs without corrupting UUIDs or hex digests."""
    if _HEX_DIGEST_RE.fullmatch(value):
        return value
    preserved: dict[str, str] = {}

    def stash(match: re.Match[str]) -> str:
        marker = f"\ue000{len(preserved)}\ue001"
        preserved[marker] = match.group(0)
        return marker

    value = _UUID_VALUE_RE.sub(stash, value)
    value = _HEX_DIGEST_RE.sub(stash, value)
    value = _LONG_NUMBER_RE.sub("[REDACTED_NUMBER]", value)
    for marker, original in preserved.items():
        value = value.replace(marker, original)
    return value
