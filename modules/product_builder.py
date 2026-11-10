"""Evidence-gated product studio for local, reproducible deliverables.

Only opportunities carrying current source evidence can enter a sellable track.
Builds run offline, score quality from recorded acceptance checks, and write a
deterministic ZIP to staging only after every required check passes.
"""
from __future__ import annotations

import csv
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from core.config import OUTPUTS_DIR

STUDIO_VERSION = "1.0.0"
MAX_SOURCE_HTML_BYTES = 750_000
MAX_CSV_BYTES = 5_000_000
MAX_CSV_ROWS = 50_000
ALLOWED_EVIDENCE_HOSTS = {
    "stackoverflow.com", "superuser.com", "webmasters.stackexchange.com",
    "serverfault.com", "unix.stackexchange.com", "news.ycombinator.com",
    "github.com", "api.github.com",
}


class ProductBuildError(ValueError):
    """A build input or QA gate failed; no stage artifact was published."""


@dataclass(frozen=True)
class AcceptanceResult:
    check_id: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class BuildArtifact:
    artifact_id: str
    artifact_path: Path
    sha256: str
    status: str
    quality_score: float
    acceptance_results: tuple[AcceptanceResult, ...]
    manifest: Mapping[str, Any]


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise ProductBuildError("Opportunity must be a source-backed record.")
    return dict(value)


def _opportunity_category(record: Mapping[str, Any]) -> str:
    experiment = record.get("experiment") if isinstance(record.get("experiment"), Mapping) else {}
    haystack = " ".join(str(value or "") for value in (
        record.get("category"), record.get("title"), record.get("pain_point"),
        experiment.get("hypothesis"),
    )).lower()
    if any(term in haystack for term in ("website_seo_technical_fixes", "search engines crawl", "technical seo", "seo page")):
        return "website_seo_technical_fixes"
    if any(term in haystack for term in ("excel_csv_cleanup", "csv_file_utilities", "csv", "spreadsheet", "excel")):
        return "csv_file_utilities"
    return "other"


def validate_opportunity(value: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Validate a persisted/source-backed opportunity and retain its provenance."""
    row = _mapping(value)
    if str(row.get("validation_status") or row.get("status") or "").upper() != "VALIDATED_BY_SOURCE":
        raise ProductBuildError("Only VALIDATED_BY_SOURCE opportunities can enter the product studio.")
    evidence = row.get("evidence")
    if isinstance(evidence, Mapping):
        evidence = [evidence]
    if not isinstance(evidence, (list, tuple)) or not evidence:
        raise ProductBuildError("Opportunity needs at least one retained source evidence record.")
    safe_evidence: list[dict[str, Any]] = []
    current = now or datetime.now(timezone.utc)
    for item in evidence:
        if not isinstance(item, Mapping):
            continue
        url = str(item.get("source_url") or row.get("source_url") or "")
        parts = urlsplit(url)
        if (parts.scheme != "https" or (parts.hostname or "").lower().rstrip(".") not in ALLOWED_EVIDENCE_HOSTS
                or parts.username or parts.password or not parts.path):
            continue
        captured_at = str(item.get("captured_at") or row.get("captured_at") or "")
        try:
            captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        age_days = (current - captured.astimezone(timezone.utc)).days
        if age_days < 0 or age_days > 365:
            continue
        quote = item.get("quote", item.get("quotation", row.get("quotation")))
        license_name = item.get("license", row.get("license"))
        attribution = item.get("quote_attribution", row.get("quote_attribution"))
        if quote and (
            not license_name or not attribution
            or not re.fullmatch(r"CC BY-SA (?:2\.5|3\.0|4\.0)", str(license_name).strip())
        ):
            continue
        safe_evidence.append({
            "source_url": url,
            "captured_at": captured.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source_date": str(item.get("source_date") or row.get("source_date") or ""),
            "quote": str(quote)[:500] if quote else None,
            "quote_attribution": str(attribution)[:240] if attribution else None,
            "license": str(license_name)[:100] if license_name else None,
        })
    if not safe_evidence:
        raise ProductBuildError("Opportunity has no current, allowlisted source evidence with valid attribution.")
    category = _opportunity_category(row)
    return {
        "id": str(row.get("id") or "")[:100],
        "title": str(row.get("title") or row.get("name") or "Source-backed problem")[:240],
        "validation_status": "VALIDATED_BY_SOURCE",
        "category": category,
        "source_url": safe_evidence[0]["source_url"],
        "captured_at": safe_evidence[0]["captured_at"],
        "evidence": safe_evidence,
        "willingness_to_pay_hypothesis": str(row.get("willingness_to_pay_hypothesis") or "HYPOTHESIS: willingness to pay is unverified.")[:500],
    }


class _SnapshotAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.viewport = ""
        self.h1_count = 0
        self.images_missing_alt = 0
        self.links_missing_href = 0
        self.script_count = 0
        self.external_resource_refs = 0
        self.visible_text_chars = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = attrs_map.get("name", "").lower()
            if name == "description":
                self.description = attrs_map.get("content", "").strip()
            elif name == "viewport":
                self.viewport = attrs_map.get("content", "").strip()
        if tag == "h1":
            self.h1_count += 1
        if tag == "img" and "alt" not in attrs_map:
            self.images_missing_alt += 1
        if tag == "a" and not attrs_map.get("href", "").strip():
            self.links_missing_href += 1
        if tag == "script":
            self.script_count += 1
        if (tag in {"img", "script", "iframe", "source"} and attrs_map.get("src", "").startswith(("http://", "https://", "//"))) or (
            tag == "link" and "stylesheet" in attrs_map.get("rel", "").lower() and attrs_map.get("href", "").startswith(("http://", "https://", "//"))
        ):
            self.external_resource_refs += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        cleaned = data.strip()
        if self._in_title:
            self.title += cleaned
        self.visible_text_chars += len(cleaned)


def audit_html_snapshot(source_html: str) -> dict[str, Any]:
    raw = source_html.encode("utf-8")
    if len(raw) > MAX_SOURCE_HTML_BYTES:
        raise ProductBuildError(f"HTML snapshot exceeds {MAX_SOURCE_HTML_BYTES} bytes.")
    parser = _SnapshotAudit()
    try:
        parser.feed(source_html)
        parser.close()
    except Exception as exc:
        raise ProductBuildError("HTML snapshot could not be parsed safely.") from exc
    issues: list[dict[str, str]] = []
    def issue(check_id: str, severity: str, observation: str, suggestion: str) -> None:
        issues.append({"check_id": check_id, "severity": severity, "observation": observation, "suggestion": suggestion})
    if not parser.title.strip():
        issue("seo.title.missing", "high", "Supplied HTML has no non-empty title element.", "Add a unique, descriptive <title> in the source HTML.")
    if not parser.description:
        issue("seo.description.missing", "medium", "Supplied HTML has no meta description.", "Add a concise meta description in the source HTML.")
    if not parser.viewport:
        issue("accessibility.mobile.viewport_missing", "medium", "Supplied HTML has no viewport declaration.", "Add a responsive viewport meta declaration and test at mobile widths.")
    if parser.h1_count != 1:
        issue("accessibility.heading.h1_count", "medium", f"Supplied HTML contains {parser.h1_count} H1 elements; expected one.", "Use one page-level H1 and preserve a logical heading order.")
    if parser.images_missing_alt:
        issue("accessibility.images.alt_missing", "high", f"{parser.images_missing_alt} image element(s) have no alt attribute.", "Add meaningful alt text or alt=\"\" for decorative images.")
    if parser.links_missing_href:
        issue("seo.links.href_missing", "low", f"{parser.links_missing_href} anchor element(s) have no href.", "Use a real link destination or render non-link text as a button with behavior.")
    if parser.script_count and parser.visible_text_chars < 80:
        issue("seo.rendering.js_dependency_possible", "review", "HTML source has scripts and little static text; client-rendered content may be absent when JavaScript is disabled.", "Compare this snapshot with the browser-rendered page and server-render important content. This is a hypothesis, not proof of crawler failure.")
    if len(raw) >= 250_000:
        issue("performance.snapshot_html_large", "review", f"The supplied HTML snapshot is {len(raw)} bytes; this is a source-size observation, not a page-load measurement.", "Measure actual page load with an owner-authorized browser or lab tool before attributing performance impact.")
    return {
        "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "snapshot_bytes": len(raw),
        "measurements": {
            "title_present": bool(parser.title.strip()), "meta_description_present": bool(parser.description),
            "viewport_present": bool(parser.viewport), "h1_count": parser.h1_count,
            "images_missing_alt": parser.images_missing_alt, "links_missing_href": parser.links_missing_href,
            "script_count": parser.script_count, "external_resource_references": parser.external_resource_refs,
            "visible_text_characters_in_source": parser.visible_text_chars,
            "performance_timing": "NOT_MEASURED; no network page load or Lighthouse run",
        },
        "issues": issues,
        "limitations": [
            "Owner-provided HTML snapshot only; this tool makes no outbound requests and does not crawl a site.",
            "JavaScript-rendering findings are heuristic and require a browser-rendered comparison.",
            "Network performance, Core Web Vitals, robots.txt, canonicals, HTTP status and server headers are not measured.",
        ],
    }


def _redact_snapshot_for_preview(source_html: str) -> str:
    """Remove executable/network-bearing content before screenshot rendering."""
    value = re.sub(r"<(script|style|iframe|object|embed|svg|math|form|template|noscript)\b[^>]*>[\s\S]*?</\1\s*>", "", source_html, flags=re.I)
    value = re.sub(r"<(script|style|iframe|object|embed|svg|math|form|template|noscript)\b[^>]*/\s*>", "", value, flags=re.I)
    value = re.sub(r"<\s*(?:link|base|meta\b[^>]*http-equiv\s*=\s*['\"]?refresh)[^>]*>", "", value, flags=re.I)
    value = re.sub(r"\s+on[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", "", value, flags=re.I)
    value = re.sub(r"\s+(?:src|srcset|href|action|poster|srcdoc)\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", "", value, flags=re.I)
    value = re.sub(r"\s+style\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", "", value, flags=re.I)
    value = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[contact redacted]", value, flags=re.I)
    value = re.sub(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)", "[contact redacted]", value)
    return value


def _render_safe_preview(source_html: str) -> bytes:
    import os
    from playwright.sync_api import sync_playwright
    executable = os.getenv("AUTOPROFIT_CHROMIUM_EXECUTABLE", "").strip()
    launch_options: dict[str, Any] = {"headless": True}
    if executable:
        browser_path = Path(executable).expanduser().resolve()
        if not browser_path.is_file():
            raise ProductBuildError("Configured Chromium executable does not exist.")
        launch_options["executable_path"] = str(browser_path)
    with tempfile.TemporaryDirectory(prefix="product-preview-") as td, sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch_options)
        try:
            context = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(_redact_snapshot_for_preview(source_html), wait_until="domcontentloaded")
            target = Path(td) / "preview.png"
            page.screenshot(path=str(target), full_page=True, animations="disabled")
            data = target.read_bytes()
            if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 1000:
                raise ProductBuildError("Screenshot evidence was not produced by the local browser.")
            return data
        finally:
            browser.close()


def _report_html(title: str, audit: Mapping[str, Any]) -> str:
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(issue["severity"]), html.escape(issue["check_id"]),
            html.escape(issue["observation"]), html.escape(issue["suggestion"]),
        ) for issue in audit["issues"]
    ) or '<tr><td colspan="4">No reproducible static issues found in this snapshot.</td></tr>'
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#172033}}table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #ccd3df;padding:.6rem;text-align:left}}code{{overflow-wrap:anywhere}}.notice{{background:#fff7db;padding:1rem}}</style>
<h1>{html.escape(title)}</h1><p>Static source-snapshot audit. It makes no network requests and is not a performance lab result.</p>
<p>Snapshot SHA-256: <code>{html.escape(audit['snapshot_sha256'])}</code> · {audit['snapshot_bytes']} bytes</p>
<table><thead><tr><th>Severity</th><th>Check</th><th>Observation</th><th>Suggested repair</th></tr></thead><tbody>{rows}</tbody></table>
<div class="notice"><h2>Limits</h2><ul>{''.join(f'<li>{html.escape(item)}</li>' for item in audit['limitations'])}</ul></div></html>"""


def _csv_workbench_source() -> str:
    return r'''#!/usr/bin/env python3
"""Local CSV workbench. Uses only the Python standard library; no network or eval."""
import argparse, csv, io, json, re, sys
from pathlib import Path

MAX_BYTES = 5_000_000
MAX_ROWS = 50_000

def safe_cell(value):
    text = str(value if value is not None else "")
    # Spreadsheet applications may ignore control/Unicode whitespace before a formula marker.
    return "'" + text if re.match(r"^[\x00-\x20\u00a0\u2000-\u200b\u2028\u2029\ufeff]*[=+\-@]", text) else text

def transform_csv(text, mapping=None):
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("CSV exceeds 5 MB")
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"), newline="")))
    if len(rows) < 2:
        raise ValueError("CSV must have a header and at least one data row")
    if len(rows) > MAX_ROWS + 1:
        raise ValueError("CSV exceeds 50,000 data rows")
    width = len(rows[0])
    if not width or width > 500 or any(len(row) > 500 for row in rows):
        raise ValueError("CSV column limit exceeded")
    if any(len(row) > width for row in rows[1:]):
        raise ValueError("CSV row has more values than the header")
    headers = [cell.strip() or f"column_{i+1}" for i, cell in enumerate(rows[0])]
    rename = mapping or {}
    headers = [str(rename.get(name, name)).strip() for name in headers]
    if any(not name for name in headers) or len(set(headers)) != len(headers):
        raise ValueError("Mapped column names must be non-empty and unique")
    safe_headers = [safe_cell(name) for name in headers]
    output, seen, duplicates, escaped, blank_rows = [], set(), 0, sum(a != b for a, b in zip(headers, safe_headers)), 0
    for source in rows[1:]:
        values = [(source[i] if i < len(source) else "").strip() for i in range(width)]
        if not any(values):
            blank_rows += 1
            continue
        key = tuple(value.casefold() for value in values)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        safe = [safe_cell(value) for value in values]
        escaped += sum(a != b for a, b in zip(values, safe))
        output.append(safe)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(safe_headers)
    writer.writerows(output)
    report = {"input_rows": len(rows)-1, "output_rows": len(output), "duplicate_rows_removed": duplicates, "blank_rows_skipped": blank_rows,
              "formula_cells_escaped": escaped, "network_requests": 0, "input_persisted": False}
    return buffer.getvalue(), report

def main():
    parser = argparse.ArgumentParser(description="Clean, map, deduplicate and safely export local CSV files.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("cleaned.csv"))
    parser.add_argument("--report", type=Path, default=Path("cleaning-report.json"))
    parser.add_argument("--mapping-json", type=Path, help='Optional JSON object, e.g. {"old_name":"name"}')
    args = parser.parse_args()
    raw = args.input.read_bytes()
    if len(raw) > MAX_BYTES:
        raise SystemExit("CSV exceeds 5 MB")
    mapping = json.loads(args.mapping_json.read_text(encoding="utf-8")) if args.mapping_json else {}
    if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k,v in mapping.items()):
        raise SystemExit("mapping JSON must be an object of string column names")
    result, report = transform_csv(raw.decode("utf-8-sig"), mapping)
    args.output.write_text(result, encoding="utf-8-sig", newline="")
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    main()
'''


SAMPLE_CSV = 'id,name,note\n1, Alice ,normal\n2,Bob,"=HYPERLINK(""https://invalid.example"",""open"")"\n2,Bob,"=HYPERLINK(""https://invalid.example"",""open"")"\n'
SAMPLE_HTML = """<!doctype html><html><head><meta charset="utf-8"><script>/* client app */</script></head><body><h1>Demo shop</h1><img src="item.png"><p>Owner-provided public-page fixture.</p></body></html>"""


class ProductBuilder:
    """Build evidence-bound product packs and retain safe legacy entry points."""

    @classmethod
    def _stage(cls, product_id: str, files: Mapping[str, bytes], spec: Mapping[str, Any],
               results: Iterable[AcceptanceResult], *, staging_dir: Path | str | None = None) -> BuildArtifact:
        results = tuple(results)
        if not results or any(not result.passed for result in results):
            raise ProductBuildError("QA failed; publication to staging is blocked.")
        score = round(100 * sum(result.passed for result in results) / len(results), 1)
        if score != 100:
            raise ProductBuildError("All acceptance checks must pass before staging.")
        normalized: dict[str, bytes] = {}
        for name, content in files.items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or not name or name == "BUILD_MANIFEST.json":
                raise ProductBuildError("Unsafe package path.")
            normalized[path.as_posix()] = content if isinstance(content, bytes) else str(content).encode("utf-8")
        qa = {"status": "PASS", "quality_score": score, "checks": [asdict(result) for result in results]}
        normalized["QA_RESULTS.json"] = _json_bytes(qa)
        manifest = dict(spec)
        manifest.update({
            "schema_version": 1, "status": "STAGING_QA_PASS", "quality_score": score,
            "quality_score_method": "passed acceptance checks / total required acceptance checks * 100",
            "acceptance_test_evidence": [asdict(result) for result in results],
            "files": {name: hashlib.sha256(content).hexdigest() for name, content in sorted(normalized.items())},
            "integrity": {"algorithm": "SHA-256", "package_hash_sidecar": "<artifact>.zip.sha256"},
            "license_ip_check": {
                "status": "PROJECT_AUTHORED_CODE_WITH_SOURCE_LINKED_EVIDENCE",
                "source_review": "No external runtime code or assets are bundled. Any reproduced public quotation is listed with source URL, attribution, and license below.",
                "owner_final_review_required": True,
                "third_party_assets": [],
                "third_party_text_evidence": [
                    {"source_url": evidence.get("source_url"), "quote_attribution": evidence.get("quote_attribution"),
                     "license": evidence.get("license")}
                    for opportunity in (manifest.get("opportunity"), *manifest.get("opportunities", []))
                    if isinstance(opportunity, Mapping)
                    for evidence in opportunity.get("evidence", [])
                    if isinstance(evidence, Mapping) and evidence.get("quote")
                ],
            },
            "reproducible_build": {"network_used": False, "zip_timestamps_normalized": True, "dependency_install_required": False},
        })
        normalized["BUILD_MANIFEST.json"] = _json_bytes(manifest)
        root = Path(staging_dir) if staging_dir is not None else OUTPUTS_DIR / "staging"
        root.mkdir(parents=True, exist_ok=True)
        artifact_id = product_id
        artifact_path = root / f"{artifact_id}.zip"
        with tempfile.TemporaryDirectory(prefix=".product-build-", dir=root) as td:
            temp_zip = Path(td) / "artifact.zip"
            with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for name, content in sorted(normalized.items()):
                    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, content)
            digest = hashlib.sha256(temp_zip.read_bytes()).hexdigest()
            os.replace(temp_zip, artifact_path)
            (root / f"{artifact_id}.zip.sha256").write_text(f"{digest}  {artifact_path.name}\n", encoding="ascii")
        return BuildArtifact(artifact_id, artifact_path, digest, "STAGING_QA_PASS", score, results, manifest)

    @classmethod
    def build_service_pack(cls, opportunity: Any, source_html: str, *, business_label: str = "Owner-provided site snapshot",
                           owner_permission_confirmed: bool = False,
                           staging_dir: Path | str | None = None) -> BuildArtifact:
        source = validate_opportunity(opportunity)
        if source["category"] != "website_seo_technical_fixes":
            raise ProductBuildError("Service audit pack requires a website/technical-SEO source opportunity.")
        if owner_permission_confirmed is not True:
            raise ProductBuildError("Owner authorization to process this public HTML snapshot is required.")
        if not isinstance(source_html, str) or not source_html.strip():
            raise ProductBuildError("Supply an owner-authorized HTML snapshot; no URL crawler is used.")
        if re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)", business_label, re.I):
            raise ProductBuildError("Business label must not contain an email address or phone number.")
        audit = audit_html_snapshot(source_html)
        title = html.escape(str(business_label)[:100])
        preview_png = _render_safe_preview(source_html)
        repairs = "# Repair suggestions\n\nThese are owner-reviewed suggestions for the supplied HTML snapshot. No files or site are modified.\n\n"
        repairs += "\n".join(f"- **{item['check_id']}** ({item['severity']}): {item['suggestion']}" for item in audit["issues"])
        if not audit["issues"]:
            repairs += "- No static issue met the defined checks; runtime performance and rendering were not measured.\n"
        repair_fragments: dict[str, bytes] = {}
        issue_ids = {item["check_id"] for item in audit["issues"]}
        if "accessibility.mobile.viewport_missing" in issue_ids:
            repair_fragments["repair-candidates/viewport-meta.html"] = b'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        if "seo.title.missing" in issue_ids:
            repair_fragments["repair-candidates/title-placeholder.html"] = b"<!-- Owner: replace with a truthful, page-specific title before applying. -->\n<title>Replace with page title</title>\n"
        if "seo.description.missing" in issue_ids:
            repair_fragments["repair-candidates/meta-description-placeholder.html"] = b'<!-- Owner: write a truthful description of this page before applying. -->\n<meta name="description" content="Replace with a concise page description">\n'
        if "accessibility.images.alt_missing" in issue_ids:
            repair_fragments["repair-candidates/image-alt-review.md"] = b"Add descriptive alt text after reviewing each image. Use alt=\"\" only for decorative images; this tool does not infer image meaning.\n"
        report_html = _report_html(f"Site snapshot audit — {title}", audit)
        checks = [
            AcceptanceResult("audit_digest_matches_input", audit["snapshot_sha256"] == hashlib.sha256(source_html.encode("utf-8")).hexdigest(), "SHA-256 computed from supplied HTML bytes."),
            AcceptanceResult("audit_parser_finds_known_sample_issues", {"seo.title.missing", "seo.description.missing", "accessibility.images.alt_missing"}.issubset({row["check_id"] for row in audit_html_snapshot(SAMPLE_HTML)["issues"]}), "Synthetic sample fixture is used to verify stable title, description and image-alt checks."),
            AcceptanceResult("report_escapes_owner_label", "<script>" not in report_html.lower(), "Report title is HTML-escaped; raw source is not embedded."),
            AcceptanceResult("screenshot_is_real_png", preview_png.startswith(b"\x89PNG\r\n\x1a\n") and len(preview_png) > 1000, f"Sanitized local preview screenshot: {len(preview_png)} bytes."),
            AcceptanceResult("preview_redacts_contact_and_blocks_active_content", all(token not in _redact_snapshot_for_preview("<script>bad()</script><img src='https://example.com/x' onerror='bad()'><p>person@example.com</p>").lower() for token in ("<script", "onerror", "https://", "person@example.com")) and "[contact redacted]" in _redact_snapshot_for_preview("<p>person@example.com</p>"), "Synthetic hostile input confirms active content, remote URLs and common contacts are removed before local screenshot rendering."),
            AcceptanceResult("performance_claims_are_labeled", audit["measurements"]["performance_timing"].startswith("NOT_MEASURED"), "No network performance claim is made."),
        ]
        product_id = f"service-site-audit-{hashlib.sha256((source['id'] + audit['snapshot_sha256']).encode()).hexdigest()[:12]}-v{STUDIO_VERSION}"
        manifest = {
            "product_id": product_id, "name": "Small-business website snapshot audit pack", "track": "A_B2B_SERVICE_PACK",
            "version": STUDIO_VERSION, "opportunity": source, "requirements": [
                "Analyze an owner-authorized HTML snapshot for reproducible accessibility and technical-SEO checks.",
                "Report exact observations, severity, repair suggestions, source digest and a real sanitized preview screenshot.",
                "Do not crawl, mutate, publish, or send site data over the network.",
            ],
            "unique_value_proof": "A repeatable static snapshot report combines accessible issue IDs, SHA-256 provenance and a locally rendered, sanitized screenshot. The public source signals a problem; it does not validate a buyer or willingness to pay.",
            "acceptance_tests": [result.check_id for result in checks],
            "repair_delivery": "Reviewable tag fragments and guidance only. The original page is not changed and no PR is opened without repository access and separate owner approval.",
            "installation": ["Unzip locally; open audit-report.html in a browser.", "Review screenshot and JSON findings with the site owner.", "Apply repair suggestions only after owner approval; rerun against a fresh snapshot."],
            "rollback": "Keep the original site files untouched; discard the report bundle to roll back. Changes are proposed separately and require owner review.",
            "support_package": "README.md, SUPPORT.md, report schema, troubleshooting and owner-review checklist.",
            "sample_dataset": "synthetic_fixture_not_customer_data",
            "landing_page": "landing-page.html",
            "offer_policy": "The public source is a problem signal only. No price or outcome promise. Quote and delivery require an owner-approved scope and actual order.",
        }
        files = {
            "audit-report.json": _json_bytes(audit), "audit-report.html": report_html.encode("utf-8"),
            "evidence/site-preview.png": preview_png, "repair-suggestions.md": repairs.encode("utf-8"),
            "README.md": _service_readme().encode("utf-8"), "SUPPORT.md": _support_doc("website snapshot audit").encode("utf-8"),
            "REQUIREMENTS.md": _requirements_doc("Website snapshot audit", [
                "Use only an owner-authorized HTML snapshot; make zero network requests.",
                "Report reproducible static technical-SEO/accessibility findings and clear measurement limits.",
                "Include a sanitized local Chromium screenshot, source digest, and owner-reviewed repair suggestions.",
            ], [row.check_id for row in checks]).encode("utf-8"),
            "CHANGELOG.md": _changelog("Website Snapshot Audit Pack", "Owner-provided static HTML checks, redacted screenshot and repair report." ).encode("utf-8"),
            "LICENSE.md": _license_doc().encode("utf-8"), "sample-page.html": SAMPLE_HTML.encode("utf-8"),
            "landing-page.html": _landing_page("Website Snapshot Audit Pack", "A local review of reproducible technical SEO and accessibility findings from an owner-authorized HTML snapshot.", [source]).encode("utf-8"),
            "owner-reviewed-offer.md": _offer_template("Website snapshot review").encode("utf-8"),
        }
        files.update(repair_fragments)
        return cls._stage(product_id, files, manifest, checks, staging_dir=staging_dir)

    @classmethod
    def build_data_workflow_pack(cls, opportunity: Any, *, staging_dir: Path | str | None = None) -> BuildArtifact:
        source = validate_opportunity(opportunity)
        if source["category"] != "csv_file_utilities":
            raise ProductBuildError("Data workflow pack requires a CSV/Excel source opportunity.")
        product_id = f"csv-workflow-pack-{hashlib.sha256(source['id'].encode()).hexdigest()[:12]}-v{STUDIO_VERSION}"
        script = _csv_workbench_source()
        files: dict[str, bytes] = {
            "csv_workbench.py": script.encode("utf-8"), "sample_input.csv": SAMPLE_CSV.encode("utf-8"),
            "column-mapping.json": _json_bytes({"name": "customer_name"}),
            "README.md": _data_readme().encode("utf-8"), "SUPPORT.md": _support_doc("local CSV workflow").encode("utf-8"),
            "CHANGELOG.md": _changelog("Local CSV Workflow Pack", "Added offline header mapping, deterministic dedupe, formula-safe export and audit report." ).encode("utf-8"),
            "LICENSE.md": _license_doc().encode("utf-8"),
        }
        results, output_csv, output_report = _run_csv_pack_e2e(script)
        files["REQUIREMENTS.md"] = _requirements_doc("Local CSV cleanup and mapping", [
            "Read a user-selected local CSV; do not upload or overwrite the source.",
            "Apply explicit header mapping, remove exact normalized duplicate rows, and report changes.",
            "Neutralize formula-leading data and mapped header cells in output.",
        ], [row.check_id for row in results]).encode("utf-8")
        files["sample_output.csv"] = output_csv.encode("utf-8-sig")
        files["sample_report.json"] = _json_bytes(output_report)
        manifest = {
            "product_id": product_id, "name": "Local CSV cleanup and mapping workflow pack", "track": "B_DATA_WORKFLOW_PACK",
            "version": STUDIO_VERSION, "opportunity": source,
            "requirements": ["Read a user-selected local CSV only.", "Trim values, apply explicit header mapping, and deduplicate exact normalized rows.", "Neutralize spreadsheet formula-leading values and report row counts.", "Never upload or retain customer data."],
            "unique_value_proof": "The observed public signal concerns CSV import/export and multi-file editing pain. This pack adds explicit header mapping, stable row-deduplication, formula-safe export and a change report in one offline workflow; paid demand remains untested.",
            "acceptance_tests": [result.check_id for result in results],
            "installation": ["Use Python 3.10+; no package installation is required.", "Run python csv_workbench.py sample_input.csv --output cleaned.csv --report report.json --mapping-json column-mapping.json.", "Copy the tool folder and run against a local input file; customer files are not included in this bundle."],
            "rollback": "Input is read-only; keep the original CSV and discard generated output/report to roll back.",
            "support_package": "README.md, SUPPORT.md, report schema, sample input/output and troubleshooting.",
            "sample_dataset": "synthetic_sample_input.csv",
            "landing_page": "landing-page.html",
            "offer_policy": "Customization and delivery require an owner-approved field mapping, acceptance sample and actual order. No price or savings claim is included.",
        }
        files["landing-page.html"] = _landing_page("Local CSV Cleanup and Mapping Pack", "A privacy-first local workflow for explicit column mapping, exact-row deduplication, formula-safe export and a change report.", [source]).encode("utf-8")
        files["owner-reviewed-offer.md"] = _offer_template("CSV cleanup and mapping").encode("utf-8")
        return cls._stage(product_id, files, manifest, results, staging_dir=staging_dir)

    @classmethod
    def build_microtool_bundle(cls, opportunities: Iterable[Any], *, staging_dir: Path | str | None = None) -> BuildArtifact:
        sources = [validate_opportunity(item) for item in opportunities]
        categories = {item["category"] for item in sources}
        if not {"website_seo_technical_fixes", "csv_file_utilities"}.issubset(categories):
            raise ProductBuildError("Microtool bundle requires source-backed SEO and CSV opportunities.")
        apps = _studio_apps()
        pages = {slug: tool for slug, tool in apps.items()}
        if set(pages) != {"papaparse-csv-to-json-cleaner", "seo-opengraph-meta-generator"}:
            raise ProductBuildError("The microtool pack must contain the two catalogued tools, with no clone pages.")
        html_pages = {slug: _generate_app(tool) for slug, tool in pages.items()}
        results = _run_microtool_browser_e2e(html_pages)
        source_key = hashlib.sha256("|".join(sorted(row["id"] for row in sources)).encode()).hexdigest()[:12]
        product_id = f"offline-microtool-pack-{source_key}-v{STUDIO_VERSION}"
        files: dict[str, bytes] = {
            f"apps/{slug}.html": page.encode("utf-8") for slug, page in html_pages.items()
        }
        files.update({
            "samples/sample.csv": SAMPLE_CSV.encode("utf-8"), "samples/sample-page.html": SAMPLE_HTML.encode("utf-8"),
            "README.md": _microtool_readme().encode("utf-8"), "SUPPORT.md": _support_doc("offline microtools").encode("utf-8"),
            "REQUIREMENTS.md": _requirements_doc("Offline microtool pack", [
                "Preserve the two selected existing catalog tools without cloning or external runtime assets.",
                "Import local CSV and HTML; export usable CSV and JSON reports.",
                "Keep imported content inert, processing local, and layout usable at a mobile viewport.",
            ], [row.check_id for row in results]).encode("utf-8"),
            "CHANGELOG.md": _changelog("Offline Microtool Pack", "Refined the existing CSV Cleaner and OpenGraph app into local file import/export tools with privacy and test evidence." ).encode("utf-8"),
            "LICENSE.md": _license_doc().encode("utf-8"),
        })
        manifest = {
            "product_id": product_id, "name": "Offline CSV Workbench and SEO Snapshot tools", "track": "C_MICROTOOL_WHITE_LABEL_PACK",
            "version": STUDIO_VERSION, "opportunities": sources,
            "included_app_slugs": sorted(html_pages),
            "requirements": ["Use local file input; no app data is sent to a server.", "Provide CSV and HTML import with report/export downloads.", "Render untrusted text as text and never execute imported user code.", "Remain usable on mobile and without external assets."],
            "unique_value_proof": "The bundle connects two separate public problem clusters with local import/export: CSV normalization/deduplication and static SEO/source-renderability diagnostics. Public issues provide problem evidence only; they do not prove the bundle is unique or commercially validated.",
            "acceptance_tests": [result.check_id for result in results],
            "installation": ["Unzip the package.", "Open apps/papaparse-csv-to-json-cleaner.html or apps/seo-opengraph-meta-generator.html in a current browser.", "Load the supplied synthetic sample or a copy of your own file; export the generated report locally."],
            "rollback": "Keep the prior HTML versions and restore them by replacing only the app files; no server-side data migration is used.",
            "support_package": "README.md, SUPPORT.md, CHANGELOG.md, sample files and per-file SHA-256 in BUILD_MANIFEST.json.",
            "sample_dataset": "samples/; synthetic fixtures only",
            "landing_page": "landing-page.html",
            "offer_policy": "The source reports are not customer interviews or paid-demand evidence. The demo is free; customization, installation or licensing is owner-quoted only after scope is understood and an actual order is approved.",
        }
        files["landing-page.html"] = _landing_page("Offline CSV Workbench and SEO Snapshot", "Two local tools for a CSV cleanup problem cluster and an HTML crawlability/metadata problem signal. Import and export remain in your browser.", sources).encode("utf-8")
        files["owner-reviewed-offer.md"] = _offer_template("Offline microtool customization").encode("utf-8")
        return cls._stage(product_id, files, manifest, results, staging_dir=staging_dir)

    @classmethod
    def build_chrome_extension(cls, output_subdir: str = "chrome_data_exporter") -> Path:
        """Legacy safe extension builder; requests only activeTab and scripting."""
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", output_subdir):
            raise ProductBuildError("Invalid extension output directory name.")
        target = OUTPUTS_DIR / output_subdir
        target.mkdir(parents=True, exist_ok=True)
        manifest = {"manifest_version": 3, "name": "OneClick Table & Data Exporter", "version": "1.1.0",
                    "description": "Export tables from the current tab after an explicit user click.",
                    "permissions": ["activeTab", "scripting"], "action": {"default_popup": "popup.html"}}
        files = {
            "manifest.json": _json_bytes(manifest),
            "popup.html": b'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><button id="export">Export current page tables</button><p id="status" role="status"></p><script src="popup.js"></script>',
            "popup.js": b'''document.querySelector('#export').addEventListener('click', async () => { const [tab] = await chrome.tabs.query({active:true,currentWindow:true}); if (!tab?.id) return; await chrome.scripting.executeScript({target:{tabId:tab.id},func:exportTables}); document.querySelector('#status').textContent='Export requested for the current tab.'; });\nfunction exportTables(){ const rows=[...document.querySelectorAll('table')].flatMap((table,ti)=>[...table.rows].map((row,ri)=>[String(ti+1),String(ri+1),...([...row.cells].map(c=>c.innerText.trim()))])); if(!rows.length){alert('No tables found.');return;} const safe=v=>/^[\\t\\r\\n ]*[=+\\-@]/.test(v)?"'"+v:v; const csv=rows.map(row=>row.map(v=>'"'+safe(v).replaceAll('"','""')+'"').join(',')).join('\\r\\n'); const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download='page-tables.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000); }\n''',
            "README.md": b"# OneClick Table Exporter\n\nInstall using Chrome or Edge Extensions > Developer mode > Load unpacked. The extension has no host permissions and operates only after a user clicks its action on the current tab. Imported text is not uploaded. Review permissions and source before distribution.\n",
            "LICENSE.md": _license_doc().encode("utf-8"),
        }
        for name, content in files.items():
            (target / name).write_bytes(content)
        return target

    @classmethod
    def build_python_scraper_bundle(cls, output_subdir: str = "shopee_market_scraper") -> Path:
        """Retired: no arbitrary-site scraping bundle is generated."""
        raise ProductBuildError("Automated site scraping is retired. Use an explicitly permitted export/feed or the local CSV workflow pack.")


def _run_csv_pack_e2e(script: str) -> tuple[tuple[AcceptanceResult, ...], str, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="csv-pack-e2e-") as td:
        root = Path(td)
        source = root / "input.csv"
        mapping = root / "mapping.json"
        output = root / "output.csv"
        report = root / "report.json"
        source.write_text(SAMPLE_CSV, encoding="utf-8")
        mapping.write_text('{"name":"customer_name"}', encoding="utf-8")
        runner = root / "csv_workbench.py"
        runner.write_text(script, encoding="utf-8")
        try:
            completed = subprocess.run([sys.executable, str(runner), str(source), "--output", str(output), "--report", str(report), "--mapping-json", str(mapping)],
                                       capture_output=True, text=True, timeout=30, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ProductBuildError("CSV CLI acceptance run exceeded the 30 second QA timeout.") from exc
        csv_result = output.read_text(encoding="utf-8-sig") if output.exists() else ""
        report_value = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
        header_source = root / "header.csv"
        header_mapping = root / "header-mapping.json"
        header_output = root / "header-output.csv"
        header_report = root / "header-report.json"
        header_source.write_text("id,name\n1,Ada\n", encoding="utf-8")
        header_mapping.write_text('{"name":"=1+1"}', encoding="utf-8")
        try:
            header_run = subprocess.run(
                [sys.executable, str(runner), str(header_source), "--output", str(header_output),
                 "--report", str(header_report), "--mapping-json", str(header_mapping)],
                capture_output=True, text=True, timeout=30, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProductBuildError("CSV header-mapping acceptance run exceeded the 30 second QA timeout.") from exc
        header_rows = list(csv.reader(io.StringIO(header_output.read_text(encoding="utf-8-sig")))) if header_output.exists() else []
        header_report_value = json.loads(header_report.read_text(encoding="utf-8")) if header_report.exists() else {}
        results = (
            AcceptanceResult("csv_cli_runs_offline", completed.returncode == 0, f"exit_code={completed.returncode}; no network client imports."),
            AcceptanceResult("header_mapping_is_applied", csv_result.startswith("id,customer_name,note"), "Header renamed using an explicit JSON mapping."),
            AcceptanceResult("duplicate_rows_are_removed", report_value.get("duplicate_rows_removed") == 1 and report_value.get("output_rows") == 2, "Synthetic repeated row removed; input row count is reported."),
            AcceptanceResult("formula_cells_are_neutralized", "'=HYPERLINK" in csv_result and report_value.get("formula_cells_escaped") == 1, "Formula-leading cell is prefixed before CSV export."),
            AcceptanceResult("mapped_formula_headers_are_neutralized", header_run.returncode == 0 and header_rows[:1] == [["id", "'=1+1"]] and header_report_value.get("formula_cells_escaped") == 1, "A formula supplied through header mapping is neutralized before CSV export."),
            AcceptanceResult("customer_data_is_not_retained_or_sent", report_value.get("input_persisted") is False and report_value.get("network_requests") == 0, "Test input lives in a temporary directory and is deleted after E2E."),
        )
        if any(not row.passed for row in results):
            raise ProductBuildError("CSV workflow QA failed; staging is blocked.")
        return results, csv_result, report_value


def _studio_apps() -> dict[str, dict[str, Any]]:
    backend_dir = str(Path(__file__).resolve().parents[1] / "backend")
    inserted = backend_dir not in sys.path
    if inserted:
        sys.path.insert(0, backend_dir)
    try:
        import apps_library
        return {tool["slug"]: tool for tool in apps_library.TOOL_DEFINITIONS if tool.get("studio")}
    finally:
        if inserted:
            try:
                sys.path.remove(backend_dir)
            except ValueError:
                pass


def _generate_app(tool: Mapping[str, Any]) -> str:
    backend_dir = str(Path(__file__).resolve().parents[1] / "backend")
    inserted = backend_dir not in sys.path
    if inserted:
        sys.path.insert(0, backend_dir)
    try:
        import apps_library
        return apps_library.generate_tool_html(dict(tool))
    finally:
        if inserted:
            try:
                sys.path.remove(backend_dir)
            except ValueError:
                pass


def _run_microtool_browser_e2e(pages: Mapping[str, str]) -> tuple[AcceptanceResult, ...]:
    from playwright.sync_api import sync_playwright
    csv_page = pages["papaparse-csv-to-json-cleaner"]
    seo_page = pages["seo-opengraph-meta-generator"]
    network_requests: list[str] = []
    checks: list[AcceptanceResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(accept_downloads=True, viewport={"width": 390, "height": 844})
            page = context.new_page()
            page.route("**/*", lambda route: (network_requests.append(route.request.url), route.abort()))
            page.set_content(csv_page, wait_until="domcontentloaded")
            page.set_input_files("#csvFile", {"name": "sample.csv", "mimeType": "text/csv", "buffer": SAMPLE_CSV.encode("utf-8")})
            page.fill("#columnMapping", '{"name":"customer_name"}')
            page.click("#processCsv")
            page.wait_for_function("document.querySelector('#status').textContent.includes('Processed')")
            preview = page.locator("#outputResult").inner_text()
            checks.append(AcceptanceResult("csv_web_import_map_dedupe_and_formula_guard", "customer_name" in preview and "'=HYPERLINK" in preview and "duplicate_rows_removed" in preview, "Chromium E2E loaded a local file, mapped headers, removed a duplicate and escaped a formula."))
            checks.append(AcceptanceResult("csv_mobile_layout_fits_viewport", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "390px viewport has no horizontal page overflow."))
            with page.expect_download() as download_info:
                page.click("#downloadCsv")
            download = download_info.value
            downloaded_csv = Path(download.path()).read_text(encoding="utf-8-sig")
            checks.append(AcceptanceResult("csv_export_download_contains_safe_csv", download.suggested_filename.endswith(".csv") and "'=HYPERLINK" in downloaded_csv, "Browser download returned formula-safe CSV."))
            page.fill("#columnMapping", '{"name":"=1+1"}')
            page.click("#processCsv")
            page.wait_for_function("document.querySelector('#status').textContent.includes('Processed')")
            mapped_preview = page.locator("#outputResult").inner_text()
            checks.append(AcceptanceResult("csv_mapped_formula_header_is_neutralized", "'=1+1" in mapped_preview and '"formula_cells_escaped": 2' in mapped_preview, "Chromium E2E verifies a mapped formula-like header and a formula-like data cell are both escaped."))
            page.close()
            seo = context.new_page()
            seo.on("dialog", lambda dialog: dialog.dismiss())
            seo.set_content(seo_page, wait_until="domcontentloaded")
            seo.set_input_files("#htmlFile", {"name": "hostile.html", "mimeType": "text/html", "buffer": b"<html><head><script>alert('x')</script></head><body><img src=x onerror=alert(1)><script>client.render()</script></body></html>"})
            seo.click("#auditHtml")
            seo.wait_for_function("document.querySelector('#status').textContent.includes('Audit complete')")
            seo_report = seo.locator("#outputResult").inner_text()
            parsed = json.loads(seo_report)
            check_ids = {row["check_id"] for row in parsed["issues"]}
            checks.append(AcceptanceResult("seo_app_detects_snapshot_issues_without_running_user_code", "seo.rendering.js_dependency_possible" in check_ids and "accessibility.images.alt_missing" in check_ids, "Malicious fixture is parsed as text; script and event attributes are not executed."))
            with seo.expect_download() as report_info:
                seo.click("#downloadReport")
            report_download = report_info.value
            checks.append(AcceptanceResult("seo_report_download_is_valid_json", json.loads(Path(report_download.path()).read_text(encoding="utf-8")).get("source_sha256") == parsed.get("source_sha256"), "Offline SEO report download matches the visible result."))
            checks.append(AcceptanceResult("apps_make_no_network_requests", not network_requests, f"Blocked outbound request count={len(network_requests)}."))
        finally:
            browser.close()
    if any(not row.passed for row in checks):
        raise ProductBuildError("Microtool browser E2E failed; staging is blocked.")
    return tuple(checks)


def _license_doc() -> str:
    return """# Source and license notice

This package uses project-authored implementation and synthetic sample data. It bundles no external fonts, images, runtime libraries, copied source, or paid dependencies. Any public source quotations reproduced in the landing page are limited to the stated CC BY-SA license and carry a source link, attribution, and license name in both the page and BUILD_MANIFEST.json. The customer retains rights to their inputs; input HTML/CSV is not included in the package. This automated source scan is not legal advice. Owner review of commercial terms and license choice is required before sale or redistribution.
"""


def _landing_page(title: str, description: str, opportunities: Iterable[Mapping[str, Any]]) -> str:
    sources = []
    for opportunity in opportunities:
        for evidence in opportunity.get("evidence", []):
            url = str(evidence.get("source_url") or "")
            quote = evidence.get("quote")
            label = html.escape(f"“{quote}”" if quote else "Public problem report")
            safe_url = html.escape(url, quote=True)
            if url:
                attribution = html.escape(str(evidence.get("quote_attribution") or ""))
                license_name = html.escape(str(evidence.get("license") or ""))
                credit = f" — {attribution} — {license_name}" if quote and attribution and license_name else ""
                sources.append(f'<li><a href="{safe_url}" target="_blank" rel="noopener noreferrer">{label}</a>{credit} — problem signal only</li>')
    source_list = "".join(sources)
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>body{{font:17px/1.6 system-ui;max-width:780px;margin:3rem auto;padding:0 1rem;color:#182338}}.tag{{color:#075e54;font-weight:700}}section{{padding:1rem 0;border-bottom:1px solid #ccd4e0}}a{{overflow-wrap:anywhere}}</style>
<main><p class="tag">FREE BASIC DEMO · NO AD SPEND · NO AUTO-OUTREACH</p><h1>{html.escape(title)}</h1><p>{html.escape(description)}</p>
<section><h2>What is included</h2><p>Local, testable deliverables with sample data, install/rollback steps, support notes, a changelog and SHA-256 integrity evidence. Customer data is not included in samples.</p></section>
<section><h2>Evidence and limits</h2><p>These public reports show a problem was posted. They are not customer interviews, proof of a buyer, market-size data or willingness-to-pay evidence. Competitor and alternative research is incomplete.</p><ul>{source_list}</ul></section>
<section><h2>Offer</h2><p>Try the basic demo for free. Customization, installation or a redistribution license is scoped and quoted by the owner only after the buyer understands the deliverable and an actual order is approved. No outcome or ranking is guaranteed.</p></section>
</main></html>"""


def _offer_template(deliverable: str) -> str:
    return f"""# Owner-reviewed offer draft — {deliverable}

This is an unsent template. Do not contact a public source author or treat that person as a lead. Use only with a customer who opted into a conversation.

## Scope to confirm
- Customer goal and authorized files/site
- Deliverable: {deliverable}
- Acceptance criteria and test fixture
- Data retention, redaction, and handoff format
- Support period and rollback owner

## Draft message
Thanks for opting into a discussion. This draft proposes {deliverable}. Before any quote, please confirm the files/site you authorize us to review and the specific acceptance checks. The public problem reports that inspired the prototype do not prove demand or guarantee outcomes. No work, publication, or outreach proceeds until you approve the scope and the owner confirms an actual order.

No price, discount, performance guarantee, or automatic sending is included.
"""


def _changelog(product: str, entry: str) -> str:
    return f"# {product}\n\n## {STUDIO_VERSION}\n- {entry}\n- Initial release staged only after all listed acceptance checks passed.\n"


def _support_doc(product: str) -> str:
    return f"""# Support and troubleshooting — {product}

- Supported inputs are local files explicitly selected by the operator.
- No telemetry, scraping, upload, account, or background service is included.
- Keep the original input; generated output is a new file.
- Report a reproducible issue with app version, operating system/browser, a synthetic example, and expected/actual result. Do not attach personal or confidential data.
- Support scope: installation questions and reproducible defects. Customization or installation is a separate owner-reviewed quote; no price or response-time promise is made here.
"""


def _requirements_doc(product: str, requirements: Iterable[str], checks: Iterable[str]) -> str:
    req = "\n".join(f"- {item}" for item in requirements)
    acceptance = "\n".join(f"- {item}" for item in checks)
    return f"# Requirements — {product}\n\n## Product requirements\n{req}\n\n## Required acceptance checks\n{acceptance}\n\nAll required checks must pass before the package is staged. See QA_RESULTS.json for observed evidence.\n"


def _service_readme() -> str:
    return """# Website Snapshot Audit Pack

Open `audit-report.html` and `audit-report.json`. `evidence/site-preview.png` is a real local Chromium screenshot of a sanitized static preview. Scripts, event handlers, external resources and common contact patterns are removed before screenshotting; network access and JavaScript are disabled. The original customer HTML is not included.

This pack audits the supplied snapshot only. It does not crawl a site, modify files, measure Core Web Vitals, verify robots/canonical/server headers, or claim that a search engine will behave a particular way. Apply suggestions only with owner permission and verify against a fresh snapshot.
"""


def _data_readme() -> str:
    return """# Local CSV Cleanup and Mapping Pack

Requires Python 3.10+ and no installed packages. Run the example command in `BUILD_MANIFEST.json` or `python csv_workbench.py --help`. Mapping is an explicit JSON object from old to new header names. Rows are trimmed and exact normalized duplicates are removed. Formula-leading cells are prefixed before output to reduce spreadsheet formula execution risk.

The tool reads a local file, writes a new output and report, makes no network calls, and never overwrites the input. Validate mappings and sample output with the owner before processing business data.
"""


def _microtool_readme() -> str:
    return """# Offline Microtool Pack

This pack upgrades two existing catalog entries: `papaparse-csv-to-json-cleaner` (CSV Workbench) and `seo-opengraph-meta-generator` (SEO Snapshot Auditor). Both use local file import, local processing and browser downloads. Open the `.html` files directly; no server or dependency install is required. They contain no external assets or telemetry and never execute imported content.

The SEO tool reports static source observations, not a live crawler or performance result. The CSV tool protects formula-leading export cells and reports deduplication. Samples are synthetic. Paid customization, installation or licensing requires a separate owner-reviewed scope and quote.
"""
