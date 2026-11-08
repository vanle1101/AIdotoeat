"""Verified dashboard reads from first-party telemetry and task/payment ledgers."""
from __future__ import annotations

import sqlite3
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from database import get_connection as get_backend_connection

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORE_DATA_DIR = Path(os.getenv("AUTOPROFIT_CORE_DATA_DIR", "").strip() or str(PROJECT_ROOT / "data")).resolve()
CORE_DB_PATH = Path(os.getenv("AUTOPROFIT_CORE_DB_PATH", "").strip() or str(CORE_DATA_DIR / "company.db")).resolve()
LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
ENGINE_EVENT_OFFSET = 1_000_000_000


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,)
    ).fetchone() is not None


def _get_core_connection() -> Optional[sqlite3.Connection]:
    if not CORE_DB_PATH.is_file():
        return None
    try:
        conn = sqlite3.connect(str(CORE_DB_PATH), timeout=3)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        return conn
    except sqlite3.Error:
        return None


def _imported_core_ids(source_table: str) -> set[str]:
    """Return source row IDs already represented by canonical imported rows."""
    try:
        conn = get_backend_connection()
        try:
            if not _table_exists(conn, "legacy_imports"):
                return set()
            source_id = str(CORE_DB_PATH.resolve())
            return {str(row[0]) for row in conn.execute(
                "SELECT source_pk FROM legacy_imports WHERE source_db=? AND source_table=?",
                (source_id, source_table),
            )}
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return set()


def _analytics_start(conn: sqlite3.Connection) -> Optional[datetime]:
    if not _table_exists(conn, "dashboard_meta"):
        return None
    row = conn.execute(
        "SELECT value FROM dashboard_meta WHERE key='analytics_started_at'"
    ).fetchone()
    return _parse_datetime(row[0]) if row else None


def _period_start(days: int, now_local: datetime) -> datetime:
    return (now_local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1))


def _traffic_series(conn: sqlite3.Connection, collection_start: datetime, window: str, now: datetime) -> list[dict[str, Any]]:
    now_local = now.astimezone(LOCAL_TZ)
    if window == "realtime":
        start = now - timedelta(minutes=60)
        bucket_seconds = 60
        count = 60
    elif window == "7d":
        start = _period_start(7, now_local).astimezone(timezone.utc)
        bucket_seconds = 86400
        count = 7
    elif window == "30d":
        start = _period_start(30, now_local).astimezone(timezone.utc)
        bucket_seconds = 86400
        count = 30
    else:
        start = now_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        bucket_seconds = 3600
        count = 24

    start_epoch = int(start.timestamp())
    counts = [0] * count
    rows = conn.execute(
        "SELECT occurred_at FROM telemetry_pageviews WHERE occurred_at >= ? AND occurred_at <= ?",
        (_iso(start), _iso(now)),
    ).fetchall()
    for row in rows:
        occurred = _parse_datetime(row[0])
        if not occurred or occurred < collection_start:
            continue
        index = int((occurred.timestamp() - start_epoch) // bucket_seconds)
        if 0 <= index < count:
            counts[index] += 1

    series = []
    for index, value in enumerate(counts):
        bucket_start = start + timedelta(seconds=bucket_seconds * index)
        bucket_end = bucket_start + timedelta(seconds=bucket_seconds)
        observed = bucket_end > collection_start and bucket_start <= now
        series.append({
            "timestamp": _iso(bucket_start),
            "end": _iso(min(bucket_end, now)),
            "value": value if observed else None,
            "status": "observed" if observed else "not_collected",
        })
    return series


def _count_pageviews(conn: sqlite3.Connection, start: datetime, now: datetime, collection_start: datetime) -> dict[str, Any]:
    actual_start = max(start, collection_start)
    row = conn.execute(
        "SELECT COUNT(*) AS views FROM telemetry_pageviews WHERE occurred_at >= ? AND occurred_at <= ?",
        (_iso(actual_start), _iso(now)),
    ).fetchone()
    return {
        "value": int(row["views"]),
        "coverage_start": _iso(actual_start),
        "status": "observed" if actual_start <= start else "partial_coverage",
    }


def _count_sessions(conn: sqlite3.Connection, start: datetime, now: datetime, collection_start: datetime) -> dict[str, Any]:
    actual_start = max(start, collection_start)
    row = conn.execute(
        "SELECT COUNT(DISTINCT session_id) AS sessions FROM telemetry_pageviews WHERE occurred_at >= ? AND occurred_at <= ?",
        (_iso(actual_start), _iso(now)),
    ).fetchone()
    return {
        "value": int(row["sessions"]),
        "coverage_start": _iso(actual_start),
        "status": "observed" if actual_start <= start else "partial_coverage",
    }


def _active_agents(now: datetime) -> dict[str, Any]:
    active_roles = active_agent_ids(now)
    if active_roles is None:
        return {"value": None, "status": "not_connected", "source": "canonical.agent_executor_leases"}
    return {"value": len(active_roles), "status": "observed", "source": "canonical.agent_executor_leases", "as_of": _iso(now)}


def active_agent_ids(now: Optional[datetime] = None) -> Optional[set[str]]:
    now = now or utc_now()
    # Phase 01 made backend/data/company.db the canonical ledger. The legacy
    # core DB remains read-only and cannot establish live executor activity.
    conn = get_backend_connection()
    try:
        if not _table_exists(conn, "tasks") or not _table_exists(conn, "task_events"):
            return None
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        if not {"state", "lease_expires_at", "task_type", "assigned_role_id"}.issubset(columns):
            # A legacy task row without an active lease cannot prove execution.
            return None
        rows = conn.execute(
            """SELECT assigned_role_id FROM tasks
                WHERE state='RUNNING' AND task_type='agent.execute'
                  AND lease_expires_at>?
                  AND EXISTS (SELECT 1 FROM task_events e WHERE e.task_id=CAST(tasks.id AS TEXT))""",
            (_iso(now),),
        ).fetchall()
        return {row["assigned_role_id"] for row in rows if row["assigned_role_id"]}
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _verified_revenue() -> dict[str, Any]:
    conn = get_backend_connection()
    try:
        if not _table_exists(conn, "cash_transactions") or not _table_exists(conn, "cash_adjustments"):
            return {"value_usd": None, "count": 0, "status": "cash_ledger_not_initialized",
                    "source": "phase07_cash_ledger", "settled_balance_by_currency": [],
                    "legacy_transactions_excluded": True}
        inbound = conn.execute(
            "SELECT t.currency,SUM(t.amount_minor) AS amount,COUNT(*) AS count "
            "FROM cash_transactions t JOIN cash_orders o ON o.id=t.order_id "
            "WHERE COALESCE(o.is_test,0)=0 GROUP BY t.currency"
        ).fetchall()
        adjustments = conn.execute(
            "SELECT a.currency,SUM(a.amount_minor) AS amount,a.adjustment_type "
            "FROM cash_adjustments a JOIN cash_orders o ON o.id=a.order_id "
            "WHERE COALESCE(o.is_test,0)=0 GROUP BY a.currency,a.adjustment_type"
        ).fetchall()
        balances = {str(row["currency"]): int(row["amount"] or 0) for row in inbound}
        for row in adjustments:
            currency = str(row["currency"])
            direction = 1 if row["adjustment_type"] == "CHARGEBACK_REVERSAL" else -1
            balances[currency] = balances.get(currency, 0) + direction * int(row["amount"] or 0)
        count = sum(int(row["count"] or 0) for row in inbound)
        return {"value_usd": None, "count": count,
                "status": "owner_manual_attested_receipts_vnd_only" if count else "no_verified_cash_receipts",
                "source": "cash_transactions_and_immutable_adjustments",
                "settled_balance_by_currency": [{"currency": currency, "amount_minor": amount,
                    "label": "VERIFIED_RECEIPTS_LESS_REFUNDS_AND_CHARGEBACKS"}
                    for currency, amount in sorted(balances.items())],
                "assurance_label": "OWNER_MANUAL_ATTESTATION", "fx_conversion": "none",
                "legacy_transactions_excluded": True}
    except (sqlite3.Error, TypeError, ValueError):
        return {"value_usd": None, "count": None, "status": "error",
                "source": "phase07_cash_ledger", "settled_balance_by_currency": [],
                "legacy_transactions_excluded": True}
    finally:
        conn.close()


def dashboard_summary(window: str = "today") -> dict[str, Any]:
    now = utc_now()
    now_local = now.astimezone(LOCAL_TZ)
    conn = get_backend_connection()
    try:
        collection_start = _analytics_start(conn)
        if collection_start is None:
            return {"status": "error", "error": "analytics_not_initialized", "updated_at": _iso(now)}

        online_cutoff = _iso(now - timedelta(seconds=90))
        online_row = conn.execute(
            "SELECT COUNT(*) AS count FROM telemetry_sessions WHERE last_seen_at >= ?",
            (online_cutoff,),
        ).fetchone()
        daily_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        today = _count_pageviews(conn, daily_start, now, collection_start)
        week_start = _period_start(7, now_local).astimezone(timezone.utc)
        month_start = _period_start(30, now_local).astimezone(timezone.utc)
        week = _count_pageviews(conn, week_start, now, collection_start)
        month = _count_pageviews(conn, month_start, now, collection_start)
        if week["status"] == "partial_coverage":
            week.update(value=None, status="insufficient_coverage")
        if month["status"] == "partial_coverage":
            month.update(value=None, status="insufficient_coverage")
        sessions_today = _count_sessions(conn, daily_start, now, collection_start)
        sessions_week = _count_sessions(conn, week_start, now, collection_start)
        sessions_month = _count_sessions(conn, month_start, now, collection_start)
        if sessions_week["status"] == "partial_coverage":
            sessions_week.update(value=None, status="insufficient_coverage")
        if sessions_month["status"] == "partial_coverage":
            sessions_month.update(value=None, status="insufficient_coverage")
        series_window = window if window in {"realtime", "today", "7d", "30d"} else "today"
        series = _traffic_series(conn, collection_start, series_window, now)
        collection_start_text = _iso(collection_start)
    except sqlite3.Error:
        return {"status": "error", "error": "analytics_query_failed", "updated_at": _iso(now)}
    finally:
        conn.close()

    revenue = _verified_revenue()
    agents = _active_agents(now)
    return {
        "status": "ok",
        "updated_at": _iso(now),
        "collection_started_at": collection_start_text,
        "window": series_window,
        "metrics": {
            "revenue_usd": revenue,
            "settled_balance_by_currency": revenue.get("settled_balance_by_currency", []),
            "ad_revenue_usd": {"value_usd": None, "status": "not_connected", "source": None},
            "ai_token_cost_usd": {"value_usd": None, "status": "not_connected", "source": None},
            "active_agents": agents,
            "monetized_views": {"value": None, "status": "not_connected", "source": None},
            "international_pageviews": {"value": None, "status": "not_connected", "source": None},
            "online_sessions": {
                "value": int(online_row["count"]), "status": "observed",
                "source": "telemetry_sessions", "online_window_seconds": 90,
            },
            "pageviews_today": today,
            "sessions_today": {**sessions_today, "source": "telemetry_pageviews"},
            "sessions_7d": {**sessions_week, "source": "telemetry_pageviews"},
            "sessions_30d": {**sessions_month, "source": "telemetry_pageviews"},
            "pageviews_7d": week,
            "pageviews_30d": month,
            "countries": {"items": None, "status": "not_connected", "source": None},
        },
        "series": {"metric": "browser_pageviews", "unit": "pageviews", "source": "telemetry_pageviews", "points": series},
    }


def _operations_connection(path: Optional[Path | str] = None) -> sqlite3.Connection:
    if path is None:
        return get_backend_connection()
    conn = sqlite3.connect(str(path), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _table_state(conn: sqlite3.Connection, name: str) -> str:
    return "observed" if _table_exists(conn, name) else "not_connected"


def _cash_ledger_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(conn, "cash_transactions"):
        return {"status": "not_connected", "settled_balance_by_currency": [],
                "verified_receipts": 0, "paid_orders": None, "last_sale": None,
                "assurance_label": None}
    rows = conn.execute(
        "SELECT t.currency,SUM(t.amount_minor) AS amount,COUNT(*) AS count,MAX(t.verified_at) AS latest "
        "FROM cash_transactions t JOIN cash_orders o ON o.id=t.order_id "
        "WHERE COALESCE(o.is_test,0)=0 GROUP BY t.currency"
    ).fetchall()
    receipts = {str(row["currency"]): int(row["amount"] or 0) for row in rows}
    receipt_count = sum(int(row["count"] or 0) for row in rows)
    latest = conn.execute(
        "SELECT t.amount_minor,t.currency,t.verified_at,t.assurance_level FROM cash_transactions t "
        "JOIN cash_orders o ON o.id=t.order_id WHERE COALESCE(o.is_test,0)=0 "
        "ORDER BY t.verified_at DESC,t.id DESC LIMIT 1"
    ).fetchone()
    if _table_exists(conn, "cash_adjustments"):
        adjustments = conn.execute(
            "SELECT a.currency,a.adjustment_type,SUM(a.amount_minor) AS amount "
            "FROM cash_adjustments a JOIN cash_orders o ON o.id=a.order_id "
            "WHERE COALESCE(o.is_test,0)=0 GROUP BY a.currency,a.adjustment_type"
        ).fetchall()
        for row in adjustments:
            currency = str(row["currency"])
            direction = 1 if row["adjustment_type"] == "CHARGEBACK_REVERSAL" else -1
            receipts[currency] = receipts.get(currency, 0) + direction * int(row["amount"] or 0)
    paid_orders = None
    if _table_exists(conn, "cash_transactions"):
        paid_orders = int(conn.execute("SELECT COUNT(DISTINCT t.order_id) FROM cash_transactions t "
                                       "JOIN cash_orders o ON o.id=t.order_id WHERE COALESCE(o.is_test,0)=0").fetchone()[0])
    return {
        "status": "observed" if receipt_count else "no_verified_data",
        "settled_balance_by_currency": [
            {"currency": currency, "amount_minor": amount,
             "assurance_label": "VERIFIED_RECEIPTS_LESS_ADJUSTMENTS"}
            for currency, amount in sorted(receipts.items())
        ],
        "verified_receipts": receipt_count,
        "paid_orders": paid_orders,
        "last_sale": ({"amount_minor": int(latest["amount_minor"]), "currency": str(latest["currency"]),
                       "verified_at": latest["verified_at"], "assurance_label": latest["assurance_level"]}
                      if latest else None),
        "assurance_label": "OWNER_MANUAL_ATTESTATION" if receipt_count else None,
        "fx_conversion": "none",
    }


def _sanitize_runtime_title(value: Any) -> Optional[str]:
    if not value:
        return None
    text = re.sub(r"[^\s@]+@[^\s@]+\.[^\s@]+", "[redacted]", str(value))
    text = re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[redacted]", text)
    return text[:140]


def dashboard_operations_summary(*, path: Optional[Path | str] = None) -> dict[str, Any]:
    """Owner-only aggregate dashboard payload; never returns customer records or payment destinations."""
    now = utc_now()
    conn = _operations_connection(path)
    try:
        cash = _cash_ledger_summary(conn)

        if _table_exists(conn, "cash_orders"):
            order_states = {str(row["state"]): int(row["count"]) for row in conn.execute(
            "SELECT state,COUNT(*) AS count FROM cash_orders WHERE COALESCE(is_test,0)=0 GROUP BY state")}
            closed_states = {"CLOSED", "CANCELLED", "REFUNDED"}
            orders = {"status": "observed" if order_states else "no_data",
                      "open_count": sum(count for state, count in order_states.items() if state not in closed_states),
                      "state_counts": order_states}
        else:
            orders = {"status": "not_connected", "open_count": None, "state_counts": {}}

        if _table_exists(conn, "cost_exposures"):
            exposure_rows = conn.execute(
                "SELECT currency,status,COUNT(*) AS count,SUM(estimated_minor) AS estimate "
                "FROM cost_exposures GROUP BY currency,status"
            ).fetchall()
            exposure_totals: dict[str, int] = {}
            exposure_count = blocked_count = 0
            for row in exposure_rows:
                currency = str(row["currency"])
                amount = int(row["estimate"] or 0)
                exposure_totals[currency] = exposure_totals.get(currency, 0) + amount
                exposure_count += int(row["count"] or 0)
                if row["status"] == "BLOCKED":
                    blocked_count += int(row["count"] or 0)
            exposures = {"status": "observed" if exposure_count else "no_data",
                         "count": exposure_count, "blocked_count": blocked_count,
                         "estimated_exposure_by_currency": [
                             {"currency": key, "amount_minor": value} for key, value in sorted(exposure_totals.items())
                         ], "label": "ESTIMATED_EXPOSURE_NOT_ACTUAL_COST"}
        else:
            exposures = {"status": "not_connected", "count": None, "blocked_count": None,
                         "estimated_exposure_by_currency": [], "label": "ESTIMATED_EXPOSURE_NOT_ACTUAL_COST"}

        pipeline = {"status": _table_state(conn, "leads"), "lead_count": None,
                    "qualified_count": None, "quote_count": None}
        if pipeline["status"] == "observed":
            pipeline["lead_count"] = int(conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0])
            pipeline["qualified_count"] = int(conn.execute(
                "SELECT COUNT(*) FROM leads WHERE stage IN ('QUALIFIED_INQUIRY','PROPOSAL_DRAFT','PROPOSAL_APPROVED','CONTACTED','QUOTE_ACCEPTED')"
            ).fetchone()[0])
            pipeline["quote_count"] = int(conn.execute(
                "SELECT COUNT(*) FROM leads WHERE stage IN ('PROPOSAL_APPROVED','QUOTE_ACCEPTED')"
            ).fetchone()[0])

        if _table_exists(conn, "evidence"):
            columns = {row[1] for row in conn.execute("PRAGMA table_info(evidence)")}
            freshness_column = "captured_at" if "captured_at" in columns else "created_at"
            freshness_row = conn.execute(
                f"SELECT COUNT(*) AS count,MAX({freshness_column}) AS latest FROM evidence WHERE verified=1"
            ).fetchone()
            captured = _parse_datetime(freshness_row["latest"])
            freshness = {"status": "observed" if freshness_row["count"] else "no_data",
                         "verified_evidence_count": int(freshness_row["count"] or 0),
                         "latest_captured_at": freshness_row["latest"],
                         "age_days": max(0, (now - captured).days) if captured else None,
                         "freshness_window_days": 30}
        else:
            freshness = {"status": "not_connected", "verified_evidence_count": None,
                         "latest_captured_at": None, "age_days": None, "freshness_window_days": 30}

        opportunities = []
        opportunity_status = _table_state(conn, "workflow_records")
        if opportunity_status == "observed":
            rows = conn.execute(
                "SELECT id,status,payload_json,updated_at FROM workflow_records "
                "WHERE kind='opportunity' ORDER BY updated_at DESC LIMIT 300"
            ).fetchall()
            for row in rows:
                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except (ValueError, TypeError):
                    continue
                if not isinstance(payload, dict) or payload.get("validation_status", row["status"]) != "VALIDATED_BY_SOURCE":
                    continue
                evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
                source_url = payload.get("source_url")
                if not source_url:
                    source_url = next((item.get("source_url") for item in evidence
                                       if isinstance(item, dict) and item.get("source_url")), None)
                experiment = None
                if _table_exists(conn, "experiments"):
                    exp_row = conn.execute(
                        "SELECT name,hypothesis,status,updated_at FROM experiments WHERE opportunity_id=? ORDER BY updated_at DESC LIMIT 1",
                        (row["id"],),
                    ).fetchone()
                    if exp_row:
                        experiment = dict(exp_row)
                score = payload.get("score")
                opportunities.append({
                    "id": str(row["id"]), "title": str(payload.get("title") or payload.get("name") or "Cơ hội từ nguồn công khai")[:180],
                    "score": float(score) if isinstance(score, (int, float)) else None,
                    "pain_point": str(payload.get("pain_point") or "")[:500],
                    "buyer_persona": str(payload.get("buyer_persona") or "")[:180],
                    "willingness_to_pay_hypothesis": str(payload.get("willingness_to_pay_hypothesis") or "HYPOTHESIS · chưa xác minh thanh toán")[:300],
                    "source_url": str(source_url)[:800] if source_url else None,
                    "captured_at": payload.get("captured_at") or row["updated_at"],
                    "evidence_count": int(payload.get("evidence_count") or len(evidence)),
                    "experiment": experiment,
                })
            opportunities.sort(key=lambda item: (item["score"] is not None, item["score"] or -1), reverse=True)
            opportunities = opportunities[:5]

        if _table_exists(conn, "products"):
            products = {"status": "observed", "count": int(conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]),
                        "active_count": int(conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0])}
        else:
            products = {"status": "not_connected", "count": None, "active_count": None}
        if _table_exists(conn, "assets"):
            products["asset_count"] = int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
            products["asset_status_counts"] = {str(row["status"]): int(row["count"]) for row in conn.execute(
                "SELECT status,COUNT(*) AS count FROM assets GROUP BY status")}
        else:
            products["asset_count"] = None
            products["asset_status_counts"] = None
        if _table_exists(conn, "cash_deliveries"):
            products["active_delivery_count"] = int(conn.execute(
                "SELECT COUNT(*) FROM cash_deliveries WHERE status='ACTIVE'"
            ).fetchone()[0])
            products["delivery_source"] = "cash_delivery_authorizations"
        else:
            products["active_delivery_count"] = None
            products["delivery_source"] = "not_connected"

        gtm_status = _table_state(conn, "gtm_analytics_events")
        funnel_counts: dict[str, Optional[int]] = {"visits": None, "opted_in_leads": None,
                                                    "qualified_quotes": None, "paid_orders": cash.get("paid_orders")}
        funnel_sources: dict[str, str] = {"visits": gtm_status, "opted_in_leads": _table_state(conn, "leads"),
                                          "qualified_quotes": gtm_status, "paid_orders": cash["status"]}
        if gtm_status == "observed":
            funnel_counts["visits"] = int(conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM gtm_analytics_events "
                "WHERE internal_test=0 AND event_name='landing_view' AND session_id IS NOT NULL"
            ).fetchone()[0])
            funnel_counts["qualified_quotes"] = int(conn.execute(
                "SELECT COUNT(DISTINCT lead_id) FROM gtm_analytics_events "
                "WHERE internal_test=0 AND event_name='proposal_sent' AND lead_id IS NOT NULL"
            ).fetchone()[0])
        if funnel_sources["opted_in_leads"] == "observed":
            lead_columns = {row[1] for row in conn.execute("PRAGMA table_info(leads)")}
            if "gtm_consent_status" in lead_columns and "gtm_suppressed" in lead_columns:
                funnel_counts["opted_in_leads"] = int(conn.execute(
                    "SELECT COUNT(*) FROM leads WHERE gtm_consent_status='GRANTED' AND gtm_suppressed=0"
                ).fetchone()[0])
            else:
                funnel_sources["opted_in_leads"] = "not_instrumented"

        approvals: list[dict[str, Any]] = []
        approval_status = _table_state(conn, "approval_requests")
        if approval_status == "observed":
            approval_rows = conn.execute(
                "SELECT id,tool_name,permission,status,trace_id,expires_at,created_at FROM approval_requests "
                "WHERE status='PENDING' AND expires_at>? ORDER BY created_at DESC LIMIT 50", (_iso(now),)
            ).fetchall()
            approvals = [dict(row) for row in approval_rows]

        if _table_exists(conn, "cash_claims"):
            claim_count = int(conn.execute("SELECT COUNT(*) FROM cash_claims WHERE status IN ('CLAIM_SUBMITTED','IN_REVIEW')").fetchone()[0])
            claim_status = "pending_review" if claim_count else "observed"
        else:
            claim_count, claim_status = None, "not_connected"

        quota: dict[str, Any] = {"status": "not_connected", "provider": None, "model": None,
                                 "requests_today": None, "daily_quota": None, "quota_source": None}
        if _table_exists(conn, "llm_usage"):
            day_start = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
            usage = conn.execute(
                "SELECT provider,model,COUNT(*) AS count FROM llm_usage WHERE created_at>=? "
                "GROUP BY provider,model ORDER BY MAX(created_at) DESC LIMIT 5", (day_start,)
            ).fetchall()
            provider_setting = os.getenv("AUTOPROFIT_LLM_PROVIDER", "auto").strip().lower()
            if usage:
                quota.update(status="observed", requests_today=sum(int(row["count"]) for row in usage),
                             providers=[{"provider": str(row["provider"])[:60], "model": str(row["model"])[:100],
                                         "requests_today": int(row["count"])} for row in usage],
                             quota_source="llm_usage")
            elif provider_setting == "template":
                quota.update(status="degraded_demo", provider="template", model=None,
                             quota_source="configuration_only")
            else:
                quota["status"] = "not_connected"
            if provider_setting == "openai_compatible":
                try:
                    daily_quota = int(os.getenv("AUTOPROFIT_LLM_REQUEST_QUOTA", "0").strip() or "0")
                except ValueError:
                    daily_quota = 0
                if daily_quota > 0:
                    quota["daily_quota"] = daily_quota
                    quota["quota_source"] = "owner_configured_cap"

        try:
            from core.agent_runtime import AGENT_REGISTRY, agent_role_statuses
            role_states = agent_role_statuses(path=path)
            agents = []
            buckets = {"active": 0, "idle": 0, "degraded": 0, "disabled": 0}
            for role_id, spec in AGENT_REGISTRY.items():
                record = role_states.get(role_id, {})
                task = record.get("latest_task") or {}
                state = str(record.get("status") or "UNKNOWN")
                readiness = str(record.get("readiness") or "NOT_IMPLEMENTED")
                if readiness == "NOT_IMPLEMENTED":
                    readiness_state = "disabled"
                elif state in {"QUEUED", "RUNNING", "WAITING_APPROVAL", "RETRY_PENDING"}:
                    readiness_state = "active"
                elif state in {"FAILED", "BLOCKED", "STALE", "UNKNOWN"}:
                    readiness_state = "degraded" if task else "idle"
                else:
                    readiness_state = "idle"
                buckets[readiness_state] += 1
                agents.append({"role_id": role_id, "name": spec.name, "department": spec.department,
                               "readiness": readiness, "readiness_state": readiness_state,
                               "task_state": state, "task_id": task.get("id"),
                               "job": _sanitize_runtime_title(task.get("title")),
                               "trace_id": task.get("trace_id"),
                               "updated_at": task.get("updated_at")})
            agent_data = {"status": "observed", "logical_roles": len(agents), "counts": buckets,
                          "status_source": "canonical_task_events_and_leases", "items": agents}
        except (sqlite3.Error, ImportError, KeyError, AttributeError):
            agent_data = {"status": "error", "logical_roles": None,
                          "counts": {"active": None, "idle": None, "degraded": None, "disabled": None},
                          "status_source": "canonical_task_events_and_leases", "items": []}

        return {
            "status": "observed",
            "updated_at": _iso(now),
            "privacy": "aggregate_only_no_customer_or_payment_destination_fields",
            "executive": {"cash": cash, "cost_exposures": exposures, "orders": orders,
                          "pipeline": pipeline, "evidence_freshness": freshness},
            "opportunity_lab": {"status": "observed" if opportunities else ("no_data" if opportunity_status == "observed" else opportunity_status),
                                "items": opportunities, "validation_filter": "VALIDATED_BY_SOURCE_ONLY"},
            "agents": agent_data,
            "production": {"products": products,
                           "artifacts_source": "authenticated_product_studio_artifact_endpoint"},
            "sales_funnel": {"status": "observed" if any(value is not None for value in funnel_counts.values()) else "no_data",
                             "stages": funnel_counts, "stage_sources": funnel_sources,
                             "revenue": {"status": cash["status"],
                                         "settled_balance_by_currency": cash["settled_balance_by_currency"],
                                         "assurance_label": cash.get("assurance_label"),
                                         "fx_conversion": "none"}},
            "risk": {"pending_approvals": {"status": "pending_review" if approvals else approval_status,
                                            "count": len(approvals) if approval_status == "observed" else None,
                                            "items": approvals},
                     "payment_claims_pending": {"status": claim_status, "count": claim_count},
                     "duplicate_claim_attempts": {"status": "not_instrumented", "count": None},
                     "known_policy_blocks": {"status": exposures["status"], "count": exposures.get("blocked_count")},
                     "unauthorized_attempts": {"status": "not_instrumented", "count": None},
                     "provider_quota": quota,
                     "security_findings": {"status": "partial_instrumentation",
                                           "known_policy_blocks": exposures.get("blocked_count"),
                                           "unauthorized_attempts": "not_instrumented"}},
        }
    finally:
        conn.close()


def list_activity(limit: int = 25, before_id: Optional[int] = None) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    engine_items: list[dict[str, Any]] = []
    try:
        from business_engine import list_task_events
        engine_events = list_task_events(0, 500)
        latest_by_task: dict[str, dict[str, Any]] = {}
        for row in engine_events:
            latest_by_task[row["task_id"]] = row
        engine_items = [{"event_id": ENGINE_EVENT_OFFSET + int(row["event_id"]), "timestamp": row["timestamp"],
                         "agent_id": None, "task_id": row["task_id"], "run_id": row["run_id"],
                         "event_type": row["event_type"], "status": row["status"], "title": row["title"],
                         "description": None, "duration_ms": None, "trace_id": row.get("trace_id"),
                         "event_source": "business_engine"}
                        for row in latest_by_task.values()
                        if before_id is None or before_id > ENGINE_EVENT_OFFSET
                        and ENGINE_EVENT_OFFSET + int(row["event_id"]) < before_id]
    except (sqlite3.Error, ImportError):
        engine_items = []
    conn = _get_core_connection()
    legacy_items: list[dict[str, Any]] = []
    imported_ids = _imported_core_ids("task_events")
    if conn is None:
        legacy_status = "not_connected"
    else:
        try:
            if not _table_exists(conn, "task_events"):
                legacy_status = "not_connected"
            else:
                params: list[Any] = []
                before_clause = ""
                if before_id is not None and before_id < ENGINE_EVENT_OFFSET:
                    before_clause = " AND e.event_id < ?"
                    params.append(before_id)
                params.append(500)
                rows = conn.execute(
                    f"""SELECT e.event_id, e.timestamp, e.agent_id, e.task_id, e.run_id,
                               e.event_type, e.status, e.title, e.description,
                               e.duration_ms, t.started_at, t.finished_at
                        FROM task_events e
                        LEFT JOIN tasks t ON CAST(t.id AS TEXT)=e.task_id
                        WHERE e.event_id IN (SELECT MAX(event_id) FROM task_events GROUP BY task_id)
                        {before_clause} ORDER BY e.event_id DESC LIMIT ?""",
                    tuple(params),
                ).fetchall()
                legacy_items = [dict(row, event_source="legacy_core") for row in rows
                                if str(row["event_id"]) not in imported_ids]
                legacy_status = "observed" if legacy_items else "no_data"
        except sqlite3.Error:
            legacy_status = "error"
        finally:
            conn.close()
    items = sorted(engine_items + legacy_items, key=lambda item: item["event_id"], reverse=True)[:safe_limit]
    connected = legacy_status != "not_connected" or engine_items
    return {"items": items, "next_before_id": items[-1]["event_id"] if len(items) == safe_limit else None,
            "status": "observed" if items else "no_data" if connected else "not_connected"}


def task_event_by_id(event_id: int, include_sensitive: bool = False) -> Optional[dict[str, Any]]:
    if event_id >= ENGINE_EVENT_OFFSET:
        canonical_id = event_id - ENGINE_EVENT_OFFSET
        try:
            from business_engine import connect as engine_connect
            conn = engine_connect()
            try:
                row = conn.execute("SELECT * FROM task_events WHERE event_id=?", (canonical_id,)).fetchone()
                if row:
                    event = {key: row[key] for key in row.keys()}
                    event["event_id"] = event_id
                    event["event_source"] = "business_engine"
                    if include_sensitive:
                        event["metadata"] = json.loads(event.pop("metadata_json", "{}") or "{}")
                        event["artifact_refs"] = json.loads(event.pop("artifact_refs_json", "[]") or "[]")
                    else:
                        for key in ("metadata_json", "artifact_refs_json", "result", "error_details"):
                            event.pop(key, None)
                    return event
            finally:
                conn.close()
        except (sqlite3.Error, ImportError):
            return None
    conn = _get_core_connection()
    if conn is None:
        return None
    try:
        sensitive_columns = ", result, error_details, metadata_json, artifact_refs_json" if include_sensitive else ""
        row = conn.execute(
            f"""SELECT event_id, timestamp, agent_id, task_id, run_id, event_type,
                       status, title, description, duration_ms{sensitive_columns}
                FROM task_events WHERE event_id=?""",
            (event_id,),
        ).fetchone()
        if not row:
            return None
        event = dict(row)
        event["steps"] = [dict(step) for step in conn.execute(
            """SELECT event_id, timestamp, event_type, status, title, duration_ms
               FROM task_events WHERE task_id=? ORDER BY event_id ASC""",
            (event["task_id"],),
        ).fetchall()]
        if include_sensitive:
            event["artifact_refs"] = json.loads(event.pop("artifact_refs_json") or "[]")
            event["metadata"] = json.loads(event.pop("metadata_json") or "{}")
        return event
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def list_core_tasks(limit: int = 100) -> list[dict[str, Any]]:
    canonical_items: list[dict[str, Any]] = []
    imported_task_ids = _imported_core_ids("tasks")
    try:
        from business_engine import list_tasks
        rows = list_tasks(limit=max(1, min(limit, 500)))
        for row in rows:
            if not row.get("idempotency_key"):
                continue
            canonical_items.append({"task_id": f"TASK-ENGINE-{row['id']}", "id": f"TASK-ENGINE-{row['id']}",
                          "title": row["title"], "task_name": row["title"],
                          "role": row["assigned_role_id"], "status": row["state"],
                          "created_at": row["created_at"], "updated_at": row["updated_at"],
                          "started_at": row["started_at"], "finished_at": row["finished_at"],
                          "progress_pct": 100 if row["state"] == "DONE" else 0 if row["state"] in {"CREATED", "QUEUED"} else None,
                          "run_id": row["run_id"], "latest_event_id": None, "result_preview": None,
                          "state_version": row["state_version"], "trace_id": row["trace_id"],
                          "task_source": "business_engine"})
    except (sqlite3.Error, ImportError):
        pass
    conn = _get_core_connection()
    if conn is None:
        return canonical_items[:max(1, min(limit, 500))]
    try:
        if not _table_exists(conn, "tasks"):
            return canonical_items[:max(1, min(limit, 500))]
        rows = conn.execute(
            """SELECT id, title, assigned_role_id, status, cost_vnd, created_at,
                      updated_at, started_at, finished_at, progress_pct, run_id,
                      (SELECT MAX(event_id) FROM task_events e
                       WHERE e.task_id=CAST(tasks.id AS TEXT)) AS latest_event_id
               FROM tasks
               WHERE EXISTS (SELECT 1 FROM task_events e WHERE e.task_id=CAST(tasks.id AS TEXT))
               ORDER BY id DESC LIMIT ?""",
            (max(1, min(limit, 500)),),
        ).fetchall()
        legacy_items = []
        for row in rows:
            if str(row["id"]) in imported_task_ids:
                continue
            item = dict(row)
            item["task_name"] = item.pop("title")
            item["role"] = item.pop("assigned_role_id")
            item["task_id"] = f"TASK-LEGACY-{item['id']}"
            item["id"] = item["task_id"]
            item["task_source"] = "legacy_core"
            item["progress_pct"] = item["progress_pct"] if item["progress_pct"] is not None else (100 if item["status"] == "DONE" else None)
            item["result_preview"] = None
            legacy_items.append(item)
        combined = sorted(canonical_items + legacy_items, key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return combined[:max(1, min(limit, 500))]
    except sqlite3.Error:
        return canonical_items[:max(1, min(limit, 500))]
    finally:
        conn.close()


def events_after(event_id: int, limit: int = 100) -> list[dict[str, Any]]:
    canonical_items: list[dict[str, Any]] = []
    try:
        from business_engine import list_task_events
        canonical_cursor = max(0, event_id - ENGINE_EVENT_OFFSET) if event_id >= ENGINE_EVENT_OFFSET else 0
        canonical_items = [{**item, "event_id": ENGINE_EVENT_OFFSET + int(item["event_id"]),
                            "event_source": "business_engine"}
                           for item in list_task_events(canonical_cursor, max(1, min(limit, 500)))]
    except (sqlite3.Error, ImportError):
        canonical_items = []
    conn = _get_core_connection()
    if conn is None:
        return sorted(canonical_items, key=lambda item: item["event_id"])[:max(1, min(limit, 500))]
    try:
        if not _table_exists(conn, "task_events"):
            return sorted(canonical_items, key=lambda item: item["event_id"])[:max(1, min(limit, 500))]
        legacy_items = []
        if event_id < ENGINE_EVENT_OFFSET:
            imported_ids = _imported_core_ids("task_events")
            legacy_items = [dict(row, event_source="legacy_core") for row in conn.execute(
                """SELECT event_id, timestamp, agent_id, task_id, run_id, event_type,
                          status, title, description, duration_ms
                   FROM task_events WHERE event_id > ? ORDER BY event_id ASC LIMIT ?""",
                (max(0, event_id), max(1, min(limit, 500))),
            ).fetchall() if str(row["event_id"]) not in imported_ids]
        combined = sorted(canonical_items + legacy_items, key=lambda item: item["event_id"])
        return combined[:max(1, min(limit, 500))]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def current_max_event_id() -> int:
    canonical_max = 0
    try:
        conn = get_backend_connection()
        try:
            canonical_max = int(conn.execute("SELECT COALESCE(MAX(event_id),0) FROM task_events").fetchone()[0])
        finally:
            conn.close()
    except sqlite3.Error:
        pass
    conn = _get_core_connection()
    if conn is None:
        return ENGINE_EVENT_OFFSET + canonical_max if canonical_max else 0
    try:
        if not _table_exists(conn, "task_events"):
            return ENGINE_EVENT_OFFSET + canonical_max if canonical_max else 0
        row = conn.execute("SELECT COALESCE(MAX(event_id),0) FROM task_events").fetchone()
        legacy_max = int(row[0])
        return ENGINE_EVENT_OFFSET + canonical_max if canonical_max else legacy_max
    finally:
        conn.close()
