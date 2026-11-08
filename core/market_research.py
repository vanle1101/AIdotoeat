"""Evidence-first market research using a small allowlist of public APIs.

This module records sourced problem observations. It does not establish market
size, demand at scale, or willingness to pay. No source page is crawled.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional
from urllib.parse import urlsplit


UTC = timezone.utc
MAX_RESPONSE_BYTES = 2_000_000
MAX_SOURCES_PER_RUN = 5
MAX_SOURCE_AGE_DAYS = 365
SOURCE_INTERVAL_SECONDS = 300
ALLOWED_STACKEXCHANGE_HOSTS = {"stackoverflow.com", "superuser.com", "webmasters.stackexchange.com",
                               "serverfault.com", "unix.stackexchange.com"}
HARD_REJECT_PATTERNS = (
    r"\bspam(?:ming)?\b", r"fake\s+(?:ad|advert|impression|view|click|review|rating)",
    r"(?:ad|advertisement|youtube)\s+(?:impression|view|click)\s*farms?",
    r"\bguaranteed?\s+(?:profit|return|income|earnings?)\b", r"\brisk[- ]free\s+(?:profit|return|income)\b",
    r"\btrading\b.{0,60}\bguaranteed\s+(?:profit|return|income)\b",
    r"\b(?:captcha|paywall)\s+bypass\b", r"\b(?:harvest|scrape)\s+(?:personal\s+)?emails?\b",
    r"\blinkedin\s+scrap(?:e|ing)\b", r"\b(?:fake|fabricated)\s+(?:review|testimonial|interview)\b",
    r"\bpaid\s+(?:api|dependency|service|plan)\b", r"\brequires?\s+(?:a\s+)?paid\s+(?:api|service|plan|subscription)\b",
)
PAYMENT_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)")


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> Optional[datetime]:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), UTC)
        if isinstance(value, str) and value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except (ValueError, OverflowError, OSError):
        return None
    return None


def _clean_text(value: Any, limit: int = 6000) -> str:
    if not isinstance(value, str):
        return ""
    text = html.unescape(re.sub(r"<[^>]*>", " ", value))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _has_sensitive_contact(text: str) -> bool:
    return bool(PAYMENT_EMAIL_RE.search(text) or PHONE_RE.search(text))


def _looks_unsafe(text: str) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in HARD_REJECT_PATTERNS)


@dataclass(frozen=True)
class ResearchSignal:
    source_id: str
    source_type: str
    source_url: str
    captured_at: str
    source_date: str
    title: str
    problem_text: str
    quotation: Optional[str]
    quote_attribution: Optional[str]
    license: Optional[str]
    last_activity_at: Optional[str] = None
    tags: tuple[str, ...] = ()
    engagement: Mapping[str, int] = field(default_factory=dict)
    legal_restrictions: str = "Read-only access through the official public API; no contact or page crawl."
    direct_wtp_signal: bool = False


@dataclass(frozen=True)
class Opportunity:
    id: str
    title: str
    validation_status: str
    source_url: str
    source_type: str
    captured_at: str
    source_date: str
    quotation: Optional[str]
    quote_attribution: Optional[str]
    pain_point: str
    buyer_persona: str
    existing_alternatives: tuple[str, ...]
    alternatives_status: str
    estimated_skills_resources: tuple[str, ...]
    willingness_to_pay_hypothesis: str
    legal_restrictions: str
    competition: str
    confidence: float
    freshness_days: int
    score: float
    score_dimensions: Mapping[str, float]
    experiment: Mapping[str, str]
    evidence: tuple[Mapping[str, Any], ...]
    dedupe_key: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_stackexchange_url(uri: Any) -> Optional[str]:
    if not isinstance(uri, str) or len(uri) > 1000:
        return None
    parts = urlsplit(uri)
    host = (parts.hostname or "").lower().rstrip(".")
    if (parts.scheme != "https" or host not in ALLOWED_STACKEXCHANGE_HOSTS or parts.username or parts.password
            or not re.match(r"^/questions/\d+(?:/|$)", parts.path) or parts.fragment):
        return None
    return urllib.parse.urlunsplit(("https", host, parts.path.rstrip("/"), "", ""))


def normalize_stackexchange(payload: Mapping[str, Any], *, captured_at: Optional[str] = None,
                            now: Optional[datetime] = None) -> list[ResearchSignal]:
    """Accept only free public API results with an explicit reusable license."""
    if _paid_response(payload):
        return []
    captured = captured_at or now_iso()
    current = now or datetime.now(UTC)
    results = payload.get("items", [])
    if not isinstance(results, list):
        return []
    signals: list[ResearchSignal] = []
    for item in results[:30]:
        if not isinstance(item, Mapping):
            continue
        url = _canonical_stackexchange_url(item.get("link"))
        title = _clean_text(item.get("title"), 300)
        body = _clean_text(item.get("body_markdown") or item.get("body"), 1600)
        if not url or not title or _has_sensitive_contact(title + " " + body) or _looks_unsafe(title + " " + body):
            continue
        question_id = str(item.get("question_id", ""))
        url_question_id = re.search(r"/questions/(\d+)(?:/|$)", urlsplit(url).path)
        if not question_id.isdigit() or not url_question_id or question_id != url_question_id.group(1):
            continue
        license_id = str(item.get("content_license", ""))
        if not re.fullmatch(r"CC BY-SA (?:2\.5|3\.0|4\.0)", license_id):
            continue
        source_dt = _parse_timestamp(item.get("creation_date"))
        activity_dt = _parse_timestamp(item.get("last_activity_date"))
        if source_dt is None:
            continue
        age_days = (current - source_dt).days
        if age_days < 0 or age_days > MAX_SOURCE_AGE_DAYS:
            continue
        author = item.get("owner", {})
        display_name = _clean_text(author.get("display_name"), 120) if isinstance(author, Mapping) else ""
        if _has_sensitive_contact(display_name):
            continue
        if not display_name:
            continue
        raw_tags = item.get("tags", [])
        if not isinstance(raw_tags, list):
            raw_tags = []
        tags = tuple(str(tag)[:60].lower() for tag in raw_tags[:12] if isinstance(tag, str))
        pay_text = title + " " + body
        direct_wtp = _has_direct_wtp_signal(pay_text)
        quote = title[:240]
        if direct_wtp:
            sentence = next((part.strip() for part in re.split(r"(?<=[.!?])\s+", body)
                             if _has_direct_wtp_signal(part)), "")
            if sentence:
                quote = sentence[:240]
        source_id = f"stackexchange:{urlsplit(url).hostname}:{question_id}"
        score = item.get("score", 0)
        answer_count = item.get("answer_count", 0)
        signals.append(ResearchSignal(
            source_id=source_id[:180], source_type="stackexchange_public_question", source_url=url,
            captured_at=captured, source_date=source_dt.isoformat().replace("+00:00", "Z"),
            title=title, problem_text=body, quotation=quote[:240] if display_name else None,
            quote_attribution=f"{display_name} on {urlsplit(url).hostname}; {license_id}" if display_name else None,
            license=license_id,
            last_activity_at=activity_dt.isoformat().replace("+00:00", "Z") if activity_dt else None,
            tags=tags,
            engagement={"score": _bounded_int(score), "answer_count": _bounded_int(answer_count)},
            legal_restrictions=f"Official Stack Exchange API; content license {license_id}; attribution and share-alike apply. No personal contact data retained.",
            direct_wtp_signal=direct_wtp,
        ))
    return signals


def normalize_hn_story(item: Mapping[str, Any], *, captured_at: Optional[str] = None,
                       now: Optional[datetime] = None) -> Optional[ResearchSignal]:
    """Classify Ask HN topic metadata without reproducing unlicensed story text."""
    if _paid_response(item):
        return None
    source_title = _clean_text(item.get("title"), 300)
    if not source_title.lower().startswith("ask hn:") or _looks_unsafe(source_title):
        return None
    topics = (
        ("spreadsheet or CSV workflow", ("excel", "csv", "spreadsheet")),
        ("technical website or SEO behavior", ("seo", "website", "webpage", "html")),
        ("offline utility", ("offline", "without internet", "local-first")),
        ("custom automation", ("automation", "automate", "workflow", "repetitive")),
        ("browser extension", ("extension", "plugin", "browser addon")),
    )
    topic = next((label for label, needles in topics if any(needle in source_title.lower() for needle in needles)), None)
    if not topic:
        return None
    # HN item text has no reuse license here. Store only a coarse paraphrase,
    # never the story title or body as a quotation.
    problem_summary = f"Public Ask HN question about {topic}; exact story wording not retained."
    story_id = str(item.get("id", ""))
    if not story_id.isdigit():
        return None
    source_dt = _parse_timestamp(item.get("time"))
    current = now or datetime.now(UTC)
    if source_dt is None or (current - source_dt).days < 0 or (current - source_dt).days > MAX_SOURCE_AGE_DAYS:
        return None
    if _has_sensitive_contact(source_title):
        return None
    url = f"https://news.ycombinator.com/item?id={story_id}"
    return ResearchSignal(
        source_id=f"hackernews:{story_id}", source_type="hacker_news_ask_story", source_url=url,
        captured_at=captured_at or now_iso(), source_date=source_dt.isoformat().replace("+00:00", "Z"),
        title=problem_summary, problem_text=problem_summary, quotation=None, quote_attribution=None, license=None,
        engagement={"score": _bounded_int(item.get("score", 0)), "answer_count": _bounded_int(item.get("descendants", 0))},
        legal_restrictions="Official Hacker News Firebase API; item metadata and coarse paraphrase only; story wording/body are not retained or quoted.",
        direct_wtp_signal=_has_direct_wtp_signal(source_title),
    )


def _bounded_int(value: Any) -> int:
    try:
        return max(0, min(int(value), 1_000_000))
    except (TypeError, ValueError, OverflowError):
        return 0


def _has_direct_wtp_signal(text: str) -> bool:
    # Explicit first-person positive payment language only. Questions about
    # what someone else might pay, budget mentions, and negated claims are not
    # treated as a buyer signal.
    if re.search(r"\b(?:not willing to pay|not happy to pay|would not pay|wouldn't pay|"
                 r"will not pay|won't pay|do not want to pay|don't want to pay)\b", text, re.I):
        return False
    return bool(re.search(r"\b(?:i(?:'|’)d pay|i would pay|i(?:'m| am) willing to pay|"
                          r"we would pay|we(?:'re| are) willing to pay|"
                          r"i(?:'m| am) happy to pay|we(?:'re| are) happy to pay)\b", text, re.I))


def _paid_response(payload: Mapping[str, Any]) -> bool:
    """Reject responses that signal paid access/cost; never send a payment request."""
    if payload.get("status") in {402, "402", "payment_required", "PAYMENT_REQUIRED"}:
        return True
    if _bounded_int(payload.get("error_id", 0)) == 402 or str(payload.get("error_name", "")).lower() in {
        "payment_required", "billing_required", "insufficient_balance", "paid_plan_required"
    }:
        return True
    if payload.get("billing_required") is True or payload.get("requires_payment") is True:
        return True
    if payload.get("paid") is True:
        return True
    for key in ("cost", "cost_usd", "price_usd", "billing_amount"):
        value = payload.get(key)
        try:
            if value is not None and float(value) > 0:
                return True
        except (TypeError, ValueError):
            return True
    return False


def _category(signal: ResearchSignal) -> Optional[str]:
    text = f"{signal.title} {signal.problem_text} {' '.join(signal.tags)}".lower()
    has = lambda words: any(re.search(r"\b" + re.escape(word) + r"\w*\b", text) for word in words)
    if has(("automation", "automate", "workflow", "repetitive")):
        return "custom_automation"
    csv_problem = has(("csv", "excel", "spreadsheet", "xlsx"))
    cleanup_operation = has(("clean", "duplicate", "deduplicate", "normalize", "standardize", "trim"))
    file_operation = has(("parse", "quote", "delimiter", "encoding", "convert", "import", "export", "download", "open"))
    if csv_problem and (file_operation or cleanup_operation):
        return "excel_csv_cleanup" if cleanup_operation else "csv_file_utilities"
    rules = (
        ("website_seo_technical_fixes", ("seo", "website", "webpage", "html", "meta description", "core web vitals")),
        ("offline_utilities", ("offline", "local-first", "without internet", "no internet")),
        ("custom_automation", ("automation", "automate", "workflow", "repetitive", "batch processing")),
        ("white_label_extensions", ("extension", "plugin", "white label", "white-label", "browser addon")),
    )
    for name, needles in rules:
        if any(needle in text for needle in needles):
            return name
    return None


def _normalize_for_dedupe(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", text.lower())
    stop = {"how", "can", "does", "need", "help", "for", "the", "with", "from", "want", "looking", "question"}
    return {token for token in tokens if token not in stop}


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(1, len(left | right))


def _score(signal: ResearchSignal, category: str, freshness_days: int, *, evidence_count: int = 1,
           direct_wtp_signal: Optional[bool] = None) -> tuple[float, dict[str, float]]:
    # Values are explicit rubric judgments; none are market statistics.
    direct_signal = signal.direct_wtp_signal if direct_wtp_signal is None else direct_wtp_signal
    unresolved_recent = not signal.engagement.get("answer_count", 0) and freshness_days <= 30
    dimensions = {
        "evidence_quality": min(90.0, 70.0 + 5.0 * max(0, evidence_count - 1)),
        "urgency": 55.0 if unresolved_recent else 25.0,
        "direct_willingness_to_pay_signal": 85.0 if direct_signal else 0.0,
        "local_feasibility": 78.0,
        "distribution_reachability": 38.0,
        "time_to_first_value": 76.0,
        "owner_constraints_fit": 50.0,
        "competition_attractiveness": 40.0,
        "freshness": max(0.0, 100.0 * (1 - freshness_days / MAX_SOURCE_AGE_DAYS)),
    }
    weights = {"evidence_quality": .20, "urgency": .15,
               "direct_willingness_to_pay_signal": .15, "local_feasibility": .14,
               "distribution_reachability": .10, "time_to_first_value": .10,
               "owner_constraints_fit": .08, "competition_attractiveness": .04,
               "freshness": .04}
    # The source demonstrates one observed question, not paying demand.
    dimensions["local_feasibility"] = dimensions["local_feasibility"] if category in {
        "excel_csv_cleanup", "csv_file_utilities", "website_seo_technical_fixes", "offline_utilities", "custom_automation", "white_label_extensions"
    } else 40.0
    return round(sum(dimensions[key] * weight for key, weight in weights.items()), 1), dimensions


def build_opportunities(signals: Iterable[ResearchSignal], *, now: Optional[datetime] = None,
                        limit: int = MAX_SOURCES_PER_RUN) -> list[Opportunity]:
    current = now or datetime.now(UTC)
    groups: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for signal in signals:
        if signal.source_url in seen_urls:
            continue
        parts = urlsplit(signal.source_url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            continue
        source_dt = _parse_timestamp(signal.source_date)
        if source_dt is None:
            continue
        age = (current - source_dt).days
        if age < 0 or age > MAX_SOURCE_AGE_DAYS or _looks_unsafe(signal.title + " " + signal.problem_text):
            continue
        category = _category(signal)
        if not category:
            continue
        tokens = _normalize_for_dedupe(signal.title + " " + " ".join(signal.tags))
        seen_urls.add(signal.source_url)
        match = next((group for group in groups if group["category"] == category and (
            _jaccard(tokens, group["tokens"]) >= .72
            or SequenceMatcher(None, " ".join(sorted(tokens)), " ".join(sorted(group["tokens"]))).ratio() >= .88
        )), None)
        if match:
            match["signals"].append((signal, age))
            match["tokens"].update(tokens)
        else:
            groups.append({"category": category, "signals": [(signal, age)], "tokens": set(tokens)})

    opportunities: list[Opportunity] = []
    for group in groups:
        category = group["category"]
        source_rows = group["signals"]
        signal, age = source_rows[0]
        evidence_count = len(source_rows)
        direct_wtp = any(source.direct_wtp_signal for source, _ in source_rows)
        score, dimensions = _score(signal, category, age, evidence_count=evidence_count,
                                   direct_wtp_signal=direct_wtp)
        dedupe_key = hashlib.sha256((category + ":" + " ".join(sorted(_normalize_for_dedupe(signal.title)))).encode()).hexdigest()
        persona = {
            "excel_csv_cleanup": "Person who prepares or reconciles spreadsheet/CSV data (role not independently verified)",
            "csv_file_utilities": "Person working through a CSV import, parsing, conversion, or export issue (role not independently verified)",
            "website_seo_technical_fixes": "Website owner or developer facing a technical web issue (role not independently verified)",
            "offline_utilities": "Person asking for an offline-capable utility (role not independently verified)",
            "custom_automation": "Person describing a repeated workflow (role not independently verified)",
            "white_label_extensions": "Extension or plugin user/builder (role not independently verified)",
        }[category]
        resources = {
            "excel_csv_cleanup": ("Python or spreadsheet tooling", "Small anonymized sample and acceptance checks"),
            "csv_file_utilities": ("Python CSV parsing or spreadsheet tooling", "Small anonymized file fixture and expected output"),
            "website_seo_technical_fixes": ("HTML/CSS and basic HTTP inspection", "Owner-provided test page or local fixture"),
            "offline_utilities": ("Local Python/JavaScript implementation", "Offline test fixture"),
            "custom_automation": ("Python scripting", "A bounded sample workflow and local test data"),
            "white_label_extensions": ("Browser extension or plugin API knowledge", "Local test fixture and explicit distribution rights"),
        }[category]
        experiment = {
            "hypothesis": f"A small fixed-scope {category.replace('_', ' ')} prototype resolves the publicly reported problem cluster.",
            "falsification_observation": "No person who explicitly opts into a test can reproduce the reported problem, or the draft fails the stated acceptance check.",
            "stop_criteria": "Stop after 5 opt-in test participants or 14 days if no one confirms the problem; stop immediately if consent, rights, or zero-cash constraints fail.",
            "success_observation": "At least 2 independent opt-in participants confirm the same problem and complete the prototype task; this still does not prove willingness to pay.",
        }
        evidence_rows = tuple({
            "id": hashlib.sha256(source.source_url.encode("utf-8")).hexdigest(),
            "source_id": source.source_id, "source_url": source.source_url,
            "captured_at": source.captured_at, "source_date": source.source_date,
            "last_activity_at": source.last_activity_at, "quote": source.quotation,
            "quote_attribution": source.quote_attribution, "license": source.license,
            "source_type": source.source_type, "legal_restrictions": source.legal_restrictions,
            "observed_problem": source.title, "engagement": dict(source.engagement),
            "direct_wtp_signal": source.direct_wtp_signal,
        } for source, _ in source_rows)
        opportunity = Opportunity(
            id="opp_" + dedupe_key[:20], title=signal.title,
            validation_status="VALIDATED_BY_SOURCE", source_url=signal.source_url,
            source_type=signal.source_type, captured_at=signal.captured_at, source_date=signal.source_date,
            quotation=signal.quotation, quote_attribution=signal.quote_attribution,
            pain_point=signal.title, buyer_persona=persona,
            existing_alternatives=(), alternatives_status="NOT_RESEARCHED",
            estimated_skills_resources=resources,
            willingness_to_pay_hypothesis=(
                "HYPOTHESIS: the source contains explicit willingness-to-pay or hiring language; amount, buyer authority, and actual payment remain unverified."
                if direct_wtp else
                "HYPOTHESIS: no direct willingness-to-pay statement was established by this source; pricing must be tested with an opt-in buyer."
            ),
            legal_restrictions=signal.legal_restrictions,
            competition="NOT_RESEARCHED: competitor count and market share have not been measured.",
            confidence=min(.75, (.50 if signal.license else .35) + .05 * (evidence_count - 1)), freshness_days=age,
            score=score, score_dimensions=dimensions, experiment=experiment,
            evidence=evidence_rows,
            dedupe_key=dedupe_key,
        )
        opportunities.append(opportunity)
    opportunities.sort(key=lambda item: (-item.score, -item.confidence, item.freshness_days, item.dedupe_key))
    return opportunities[:max(0, min(int(limit), 5))]


def _safe_json(url: str, *, timeout: float = 8, opener: Optional[Callable[..., Any]] = None) -> Any:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in {"hacker-news.firebaseio.com", "api.stackexchange.com"}:
        raise ValueError("research endpoint is not on the allowlist")
    request = urllib.request.Request(url, headers={"User-Agent": "AUTOProfitEthicalResearch/1.0 (read-only; contact owner through repository metadata)",
                                                    "Accept": "application/json"})
    open_url = opener or urllib.request.urlopen
    try:
        with open_url(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status in (402, 429):
                raise SourceUnavailable("paid_or_rate_limited", status=status,
                                        retry_after=response.headers.get("Retry-After"))
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in (402, 429):
            raise SourceUnavailable("paid_or_rate_limited", status=exc.code,
                                    retry_after=exc.headers.get("Retry-After")) from None
        raise SourceUnavailable("source_http_error", status=exc.code) from None
    except (TimeoutError, OSError, urllib.error.URLError):
        raise SourceUnavailable("source_unavailable") from None
    if len(body) > MAX_RESPONSE_BYTES:
        raise SourceUnavailable("source_response_too_large")
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise SourceUnavailable("source_invalid_json") from None
    if not isinstance(value, (Mapping, list)):
        raise SourceUnavailable("source_invalid_shape")
    if isinstance(value, Mapping) and _paid_response(value):
        raise SourceUnavailable("paid_source_blocked", status=402)
    return value


class SourceUnavailable(RuntimeError):
    def __init__(self, reason_code: str, *, status: Optional[int] = None, retry_after: Optional[str] = None):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.status = status
        self.retry_after = retry_after


def _db_connect(path: Optional[Path | str] = None) -> sqlite3.Connection:
    from backend import business_engine
    return business_engine.connect(path)


def _source_allowed(source_name: str, *, path: Optional[Path | str], now: datetime,
                    interval: int = SOURCE_INTERVAL_SECONDS) -> bool:
    from backend import business_engine
    business_engine.ensure_schema(path)
    conn = _db_connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT next_allowed_at FROM market_research_fetch_state WHERE source_name=?", (source_name,)).fetchone()
        if row and row[0] and (_parse_timestamp(row[0]) or now) > now:
            conn.rollback()
            return False
        next_at = now.timestamp() + interval
        next_iso = datetime.fromtimestamp(next_at, UTC).isoformat().replace("+00:00", "Z")
        now_text = now.isoformat().replace("+00:00", "Z")
        conn.execute("INSERT INTO market_research_fetch_state(source_name,last_request_at,next_allowed_at,consecutive_failures,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(source_name) DO UPDATE SET last_request_at=excluded.last_request_at,next_allowed_at=excluded.next_allowed_at,updated_at=excluded.updated_at",
                     (source_name, now_text, next_iso, 0, now_text))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _mark_source_failure(source_name: str, *, path: Optional[Path | str], now: datetime,
                         retry_seconds: int) -> None:
    conn = _db_connect(path)
    try:
        now_text = now.isoformat().replace("+00:00", "Z")
        next_text = datetime.fromtimestamp(now.timestamp() + max(30, min(retry_seconds, 86400)), UTC).isoformat().replace("+00:00", "Z")
        conn.execute("INSERT INTO market_research_fetch_state(source_name,last_request_at,next_allowed_at,consecutive_failures,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(source_name) DO UPDATE SET next_allowed_at=excluded.next_allowed_at,consecutive_failures=market_research_fetch_state.consecutive_failures+1,updated_at=excluded.updated_at",
                     (source_name, now_text, next_text, 1, now_text))
        conn.commit()
    finally:
        conn.close()


def fetch_stackexchange(*, path: Optional[Path | str] = None, now: Optional[datetime] = None,
                        fetch_json: Callable[..., Mapping[str, Any]] = _safe_json) -> tuple[list[ResearchSignal], str]:
    current = now or datetime.now(UTC)
    if not _source_allowed("stackexchange", path=path, now=current):
        return [], "rate_limited"
    queries = ("csv", "website seo", "power automate")
    signals: list[ResearchSignal] = []
    for query in queries:
        since = int(current.timestamp()) - MAX_SOURCE_AGE_DAYS * 24 * 60 * 60
        params = urllib.parse.urlencode({"order": "desc", "sort": "creation", "site": "stackoverflow",
                                         "q": query, "pagesize": "15", "fromdate": str(since),
                                         "filter": "withbody"})
        try:
            result = fetch_json("https://api.stackexchange.com/2.3/search/advanced?" + params)
            if not isinstance(result, Mapping) or _paid_response(result):
                raise SourceUnavailable("paid_source_blocked", status=402)
            if result.get("error_id"):
                raise SourceUnavailable("source_api_error", status=_bounded_int(result.get("error_id")))
            signals.extend(normalize_stackexchange(result, now=current))
            backoff = _bounded_int(result.get("backoff", 0))
            if backoff:
                _mark_source_failure("stackexchange", path=path, now=current, retry_seconds=backoff)
                break
        except SourceUnavailable as exc:
            retry_after = _bounded_int(exc.retry_after or 0)
            _mark_source_failure("stackexchange", path=path, now=current, retry_seconds=max(retry_after, 60))
            return signals, exc.reason_code
    return signals, "observed"


def fetch_hacker_news(*, path: Optional[Path | str] = None, now: Optional[datetime] = None,
                      fetch_json: Callable[..., Mapping[str, Any]] = _safe_json,
                      max_items: int = 5) -> tuple[list[ResearchSignal], str]:
    current = now or datetime.now(UTC)
    if not _source_allowed("hacker_news", path=path, now=current):
        return [], "rate_limited"
    try:
        ids = fetch_json("https://hacker-news.firebaseio.com/v0/askstories.json")
        # The official Firebase endpoint returns an array; adapters/mocks may wrap it.
        story_ids = ids.get("ids") if isinstance(ids, Mapping) else ids
        if not isinstance(story_ids, list):
            return [], "source_invalid_shape"
        signals = []
        for story_id in story_ids[:max(0, min(max_items, 10))]:
            if not isinstance(story_id, int) or story_id < 1:
                continue
            item = fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            signal = normalize_hn_story(item, now=current)
            if signal:
                signals.append(signal)
        return signals, "observed"
    except SourceUnavailable as exc:
        retry_after = _bounded_int(exc.retry_after or 0)
        _mark_source_failure("hacker_news", path=path, now=current, retry_seconds=max(retry_after, 60))
        return [], exc.reason_code


def persist_opportunities(opportunities: Iterable[Opportunity], *, path: Optional[Path | str] = None) -> list[dict[str, Any]]:
    """Atomically save opportunity projections, evidence, and falsifiable experiments."""
    from backend import business_engine
    business_engine.ensure_schema(path)
    conn = _db_connect(path)
    saved: list[dict[str, Any]] = []

    def insert_evidence(opportunity_id: str, opportunity: Opportunity,
                        evidence: Mapping[str, Any]) -> bool:
        source_key = str(evidence.get("id", ""))
        if not source_key or conn.execute("SELECT 1 FROM evidence WHERE source_dedupe_key=?", (source_key,)).fetchone():
            return False
        observed_problem = str(evidence.get("observed_problem") or opportunity.pain_point)
        quote = evidence.get("quote")
        conn.execute("INSERT INTO evidence(id,opportunity_id,evidence_type,source_uri,content_hash,summary,verified,created_at,captured_at,quote,quote_attribution,pain_point,buyer_persona,alternatives_json,skills_resources_json,willingness_to_pay_hypothesis,legal_restrictions,competition,confidence,freshness_days,source_dedupe_key,opportunity_dedupe_key,source_type) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (source_key, opportunity_id, evidence.get("source_type", opportunity.source_type), evidence.get("source_url"),
                      hashlib.sha256((quote or observed_problem).encode()).hexdigest(), observed_problem, 1,
                      evidence.get("captured_at", opportunity.captured_at), evidence.get("captured_at"), quote,
                      evidence.get("quote_attribution"), observed_problem, opportunity.buyer_persona,
                      json.dumps(list(opportunity.existing_alternatives), ensure_ascii=False),
                      json.dumps(list(opportunity.estimated_skills_resources), ensure_ascii=False),
                      opportunity.willingness_to_pay_hypothesis, evidence.get("legal_restrictions", opportunity.legal_restrictions),
                      opportunity.competition, opportunity.confidence, opportunity.freshness_days,
                      source_key, opportunity.dedupe_key, evidence.get("source_type", opportunity.source_type)))
        return True

    try:
        conn.execute("BEGIN IMMEDIATE")
        for opportunity in opportunities:
            payload = opportunity.to_dict()
            idem = "market-research:" + opportunity.dedupe_key
            prior = conn.execute("SELECT id,payload_json FROM workflow_records WHERE idempotency_key=?", (idem,)).fetchone()
            if prior:
                try:
                    existing_payload = json.loads(prior["payload_json"] or "{}")
                except (TypeError, ValueError):
                    existing_payload = {}
                if not isinstance(existing_payload, dict):
                    existing_payload = {}
                existing_evidence = list(existing_payload.get("evidence", []))
                known_sources = {row.get("id") for row in existing_evidence if isinstance(row, Mapping)}
                additions = []
                for evidence in opportunity.evidence:
                    if evidence.get("id") in known_sources:
                        continue
                    if insert_evidence(prior["id"], opportunity, evidence):
                        additions.append(dict(evidence))
                if additions:
                    existing_payload["evidence"] = existing_evidence + additions
                    evidence_count = len(existing_payload["evidence"])
                    existing_payload["evidence_count"] = evidence_count
                    existing_payload["confidence"] = min(.75, float(existing_payload.get("confidence", .35)) + .05 * len(additions))
                    dimensions = dict(existing_payload.get("score_dimensions", {}))
                    dimensions["evidence_quality"] = min(90.0, 70.0 + 5.0 * max(0, evidence_count - 1))
                    if any(row.get("direct_wtp_signal") for row in additions):
                        dimensions["direct_willingness_to_pay_signal"] = 85.0
                        existing_payload["willingness_to_pay_hypothesis"] = (
                            "HYPOTHESIS: at least one source contains explicit willingness-to-pay or hiring language; amount, buyer authority, and actual payment remain unverified."
                        )
                    existing_payload["score_dimensions"] = dimensions
                    existing_payload["score"] = round(sum(dimensions.get(key, 0) * weight for key, weight in WEIGHTS.items()), 1)
                    now_text = opportunity.captured_at
                    payload_json = json.dumps(existing_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
                    conn.execute("UPDATE workflow_records SET payload_json=?,updated_at=?,idempotency_hash=? WHERE id=?",
                                 (payload_json, now_text, payload_hash, prior["id"]))
                    saved.append(existing_payload)
                continue
            new_evidence = [dict(evidence) for evidence in opportunity.evidence
                            if not conn.execute("SELECT 1 FROM evidence WHERE source_dedupe_key=?", (evidence["id"],)).fetchone()]
            if not new_evidence:
                continue
            record_id = opportunity.id
            now_text = opportunity.captured_at
            payload["id"] = record_id
            payload["name"] = opportunity.title
            payload["status"] = opportunity.validation_status
            payload["evidence"] = new_evidence
            payload["evidence_count"] = len(new_evidence)
            idem_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            conn.execute("INSERT INTO workflow_records(id,kind,status,payload_json,created_at,updated_at,idempotency_key,idempotency_hash) VALUES(?,?,?,?,?,?,?,?)",
                         (record_id, "opportunity", opportunity.validation_status,
                          json.dumps(payload, ensure_ascii=False, sort_keys=True), now_text, now_text, idem, idem_hash))
            for evidence in new_evidence:
                insert_evidence(record_id, opportunity, evidence)
            exp_id = "exp_" + opportunity.dedupe_key[:20]
            conn.execute("INSERT OR IGNORE INTO experiments(id,opportunity_id,name,hypothesis,status,result_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                         (exp_id, record_id, "Opt-in problem verification", opportunity.experiment["hypothesis"],
                          "DRAFT", json.dumps(dict(opportunity.experiment), ensure_ascii=False, sort_keys=True), now_text, now_text))
            saved.append(payload)
        conn.commit()
        return saved
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_live_research(*, path: Optional[Path | str] = None,
                      stackexchange_fetch: Callable[..., tuple[list[ResearchSignal], str]] = fetch_stackexchange,
                      hn_fetch: Callable[..., tuple[list[ResearchSignal], str]] = fetch_hacker_news,
                      now: Optional[datetime] = None) -> dict[str, Any]:
    current = now or datetime.now(UTC)
    sources: dict[str, str] = {}
    signals: list[ResearchSignal] = []
    for name, fetcher in (("Stack Exchange", stackexchange_fetch), ("Hacker News", hn_fetch)):
        try:
            items, status = fetcher(path=path, now=current)
        except TypeError:
            items, status = fetcher()
        sources[name] = status
        signals.extend(items)
    opportunities = build_opportunities(signals, now=current, limit=5)
    saved = persist_opportunities(opportunities, path=path) if opportunities else []
    if sources and any(value == "observed" for value in sources.values()):
        status = "observed"
    elif sources and all(value == "rate_limited" for value in sources.values()):
        status = "rate_limited"
    else:
        status = "source_unavailable"
    return {"status": status, "sources": sources, "items": saved,
            "validated_by_source_count": len(saved),
            "message": (f"{len(saved)} cơ hội có nguồn vấn đề công khai; chưa xác minh nhu cầu trả tiền."
                        if saved else "Không tìm thấy tín hiệu phù hợp đủ mới để ghi nhận; không tạo cơ hội giả.")}


WEIGHTS = {
    "evidence_quality": .20, "urgency": .15, "direct_willingness_to_pay_signal": .15,
    "local_feasibility": .14, "distribution_reachability": .10, "time_to_first_value": .10,
    "owner_constraints_fit": .08, "competition_attractiveness": .04, "freshness": .04,
}
