"""Verified dashboard reads from first-party telemetry and task/payment ledgers."""
from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from database import get_connection as get_backend_connection

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORE_DB_PATH = PROJECT_ROOT / "data" / "company.db"
LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
VERIFIED_PAYMENT_STATUSES = {
    "CONFIRMED_BY_OWNER", "CONFIRMED", "SETTLED", "PAID", "RECEIVED_BY_OWNER"
}


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
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
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
        return {"value": None, "status": "not_connected", "source": "core.tasks"}
    return {"value": len(active_roles), "status": "observed", "source": "core.tasks", "as_of": _iso(now)}


def active_agent_ids(now: Optional[datetime] = None) -> Optional[set[str]]:
    now = now or utc_now()
    conn = _get_core_connection()
    if conn is None:
        return None
    try:
        if not _table_exists(conn, "tasks"):
            return None
        if not _table_exists(conn, "task_events"):
            # A task table without lifecycle events cannot prove current agent state.
            return None
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        timestamp_column = "updated_at" if "updated_at" in columns else "created_at"
        rows = conn.execute(
            f"""SELECT assigned_role_id, {timestamp_column} AS seen_at FROM tasks
                WHERE UPPER(status)='RUNNING'
                  AND EXISTS (SELECT 1 FROM task_events e WHERE e.task_id=CAST(tasks.id AS TEXT))"""
        ).fetchall()
        cutoff = now - timedelta(minutes=2)
        roles = {
            row["assigned_role_id"] for row in rows
            if row["assigned_role_id"] and _parse_datetime(row["seen_at"])
            and _parse_datetime(row["seen_at"]) >= cutoff
        }
        return roles
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _verified_revenue() -> dict[str, Any]:
    conn = get_backend_connection()
    try:
        if not _table_exists(conn, "transactions"):
            return {"value_usd": None, "count": None, "status": "not_connected", "source": "transactions"}
        placeholders = ",".join("?" for _ in VERIFIED_PAYMENT_STATUSES)
        rows = conn.execute(
            f"SELECT amount_usd FROM transactions WHERE UPPER(COALESCE(status,'')) IN ({placeholders})",
            tuple(sorted(VERIFIED_PAYMENT_STATUSES)),
        ).fetchall()
        if not rows:
            return {"value_usd": None, "count": 0, "status": "no_verified_records", "source": "transactions"}
        values = [float(row[0]) for row in rows if row[0] is not None]
        if not values:
            return {"value_usd": None, "count": len(rows), "status": "no_verified_amounts", "source": "transactions"}
        return {"value_usd": round(sum(values), 2), "count": len(values), "status": "verified", "source": "transactions"}
    except (sqlite3.Error, TypeError, ValueError):
        return {"value_usd": None, "count": None, "status": "error", "source": "transactions"}
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


def list_activity(limit: int = 25, before_id: Optional[int] = None) -> dict[str, Any]:
    conn = _get_core_connection()
    if conn is None:
        return {"items": [], "next_before_id": None, "status": "not_connected"}
    try:
        if not _table_exists(conn, "task_events"):
            return {"items": [], "next_before_id": None, "status": "not_connected"}
        params: list[Any] = []
        before_clause = ""
        if before_id is not None:
            before_clause = " AND e.event_id < ?"
            params.append(before_id)
        params.append(max(1, min(limit, 100)))
        rows = conn.execute(
            f"""SELECT e.event_id, e.timestamp, e.agent_id, e.task_id, e.run_id,
                       e.event_type, e.status, e.title, e.description,
                       e.duration_ms, t.started_at, t.finished_at
                FROM task_events e
                LEFT JOIN tasks t ON CAST(t.id AS TEXT)=e.task_id
                WHERE e.event_id IN (
                    SELECT MAX(event_id) FROM task_events GROUP BY task_id
                ){before_clause}
                ORDER BY e.event_id DESC LIMIT ?""",
            tuple(params),
        ).fetchall()
        items = [dict(row) for row in rows]
        return {
            "items": items,
            "next_before_id": items[-1]["event_id"] if len(items) == max(1, min(limit, 100)) else None,
            "status": "observed" if items else "no_data",
        }
    except sqlite3.Error:
        return {"items": [], "next_before_id": None, "status": "error"}
    finally:
        conn.close()


def task_event_by_id(event_id: int, include_sensitive: bool = False) -> Optional[dict[str, Any]]:
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
    conn = _get_core_connection()
    if conn is None:
        return []
    try:
        if not _table_exists(conn, "tasks"):
            return []
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
        items = []
        for row in rows:
            item = dict(row)
            item["task_name"] = item.pop("title")
            item["role"] = item.pop("assigned_role_id")
            item["task_id"] = f"TASK-{item['id']}"
            item["id"] = item["task_id"]
            item["progress_pct"] = item["progress_pct"] if item["progress_pct"] is not None else (100 if item["status"] == "DONE" else None)
            item["result_preview"] = None
            items.append(item)
        return items
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def events_after(event_id: int, limit: int = 100) -> list[dict[str, Any]]:
    conn = _get_core_connection()
    if conn is None:
        return []
    try:
        if not _table_exists(conn, "task_events"):
            return []
        return [dict(row) for row in conn.execute(
            """SELECT event_id, timestamp, agent_id, task_id, run_id, event_type,
                      status, title, description, duration_ms
               FROM task_events WHERE event_id > ? ORDER BY event_id ASC LIMIT ?""",
            (max(0, event_id), max(1, min(limit, 500))),
        ).fetchall()]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def current_max_event_id() -> int:
    conn = _get_core_connection()
    if conn is None:
        return 0
    try:
        if not _table_exists(conn, "task_events"):
            return 0
        row = conn.execute("SELECT COALESCE(MAX(event_id),0) FROM task_events").fetchone()
        return int(row[0])
    finally:
        conn.close()
