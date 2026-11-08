"""Durable, local-first business workflow engine backed by SQLite.

The backend database is canonical for new work. Existing core/data/company.db
data is read-only until an operator explicitly runs migrate_core_legacy.py.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

import database as backend_database
from domain_models import TaskSpec, TaskState


_LOG = logging.getLogger("autoprofit.engine")
MIGRATION_DIR = Path(__file__).resolve().parent / "migrations"
TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.CREATED: {TaskState.QUEUED, TaskState.BLOCKED, TaskState.CANCELLED},
    TaskState.QUEUED: {TaskState.RUNNING, TaskState.BLOCKED, TaskState.CANCELLED},
    TaskState.RUNNING: {TaskState.WAITING_APPROVAL, TaskState.RETRY_PENDING, TaskState.BLOCKED,
                        TaskState.DONE, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.WAITING_APPROVAL: {TaskState.QUEUED, TaskState.BLOCKED, TaskState.CANCELLED},
    TaskState.RETRY_PENDING: {TaskState.QUEUED, TaskState.BLOCKED, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.BLOCKED: {TaskState.QUEUED, TaskState.CANCELLED},
    TaskState.DONE: set(),
    TaskState.FAILED: set(),
    TaskState.CANCELLED: set(),
}
TERMINAL_STATES = {TaskState.DONE.value, TaskState.FAILED.value, TaskState.CANCELLED.value}

TASK_COLUMNS: dict[str, str] = {
    "task_type": "TEXT NOT NULL DEFAULT 'legacy.import'",
    "state": "TEXT NOT NULL DEFAULT 'BLOCKED'",
    "state_version": "INTEGER NOT NULL DEFAULT 0",
    "idempotency_key": "TEXT",
    "trace_id": "TEXT",
    "attempts": "INTEGER NOT NULL DEFAULT 0",
    "max_attempts": "INTEGER NOT NULL DEFAULT 3",
    "available_at": "TEXT",
    "lease_owner": "TEXT",
    "lease_expires_at": "TEXT",
    "timeout_seconds": "INTEGER NOT NULL DEFAULT 300",
    "last_error": "TEXT",
    "payload_json": "TEXT NOT NULL DEFAULT '{}'",
    "result_json": "TEXT",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value: Optional[datetime] = None) -> str:
    return (value or utc_now()).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def connect(path: Optional[Path | str] = None) -> sqlite3.Connection:
    target = Path(path) if path is not None else Path(backend_database.DB_PATH)
    conn = sqlite3.connect(str(target), timeout=15, isolation_level="DEFERRED")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _script_statements(script: str):
    pending = ""
    for line in script.splitlines():
        pending += line + "\n"
        if sqlite3.complete_statement(pending):
            if pending.strip():
                yield pending
            pending = ""
    if pending.strip():
        raise ValueError("Incomplete SQLite migration statement")


def _apply_script(conn: sqlite3.Connection, script: str) -> None:
    for statement in _script_statements(script):
        match = re.match(r"\s*CREATE\s+VIEW\s+IF\s+NOT\s+EXISTS\s+([\w]+)", statement, re.I)
        if match:
            present = conn.execute(
                "SELECT type FROM sqlite_master WHERE name=?", (match.group(1),)
            ).fetchone()
            if present:
                continue  # preserve a prior compatible table or view
        conn.execute(statement)


def _add_missing_task_columns(conn: sqlite3.Connection) -> None:
    known = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    for name, definition in TASK_COLUMNS.items():
        if name not in known:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_engine_tasks_idempotency ON tasks(idempotency_key) WHERE idempotency_key IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_engine_tasks_queue ON tasks(state, available_at, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_engine_tasks_run ON tasks(run_id, id)")


def _add_missing_event_columns(conn: sqlite3.Connection) -> None:
    known = {row[1] for row in conn.execute("PRAGMA table_info(task_events)")}
    for name, definition in {"trace_id": "TEXT", "idempotency_key": "TEXT"}.items():
        if name not in known:
            conn.execute(f"ALTER TABLE task_events ADD COLUMN {name} {definition}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_engine_event_idempotency ON task_events(idempotency_key) WHERE idempotency_key IS NOT NULL")


def _add_missing_workflow_columns(conn: sqlite3.Connection) -> None:
    known = {row[1] for row in conn.execute("PRAGMA table_info(workflow_records)")}
    for name, definition in {"idempotency_key": "TEXT", "idempotency_hash": "TEXT"}.items():
        if name not in known:
            conn.execute(f"ALTER TABLE workflow_records ADD COLUMN {name} {definition}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_records_idempotency ON workflow_records(idempotency_key) WHERE idempotency_key IS NOT NULL")


def _add_market_research_columns(conn: sqlite3.Connection) -> None:
    """Extend compatible evidence rows without replacing prior ledger data."""
    known = {row[1] for row in conn.execute("PRAGMA table_info(evidence)")}
    columns = {
        "captured_at": "TEXT", "quote": "TEXT", "quote_attribution": "TEXT",
        "pain_point": "TEXT", "buyer_persona": "TEXT",
        "alternatives_json": "TEXT NOT NULL DEFAULT '[]'",
        "skills_resources_json": "TEXT NOT NULL DEFAULT '[]'",
        "willingness_to_pay_hypothesis": "TEXT", "legal_restrictions": "TEXT",
        "competition": "TEXT", "confidence": "REAL",
        "freshness_days": "INTEGER", "source_dedupe_key": "TEXT",
        "opportunity_dedupe_key": "TEXT", "source_type": "TEXT",
    }
    for name, definition in columns.items():
        if name not in known:
            conn.execute(f"ALTER TABLE evidence ADD COLUMN {name} {definition}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_source_dedupe ON evidence(source_dedupe_key) WHERE source_dedupe_key IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_opportunity_source ON evidence(opportunity_id, captured_at DESC)")


def _add_gtm_columns(conn: sqlite3.Connection) -> None:
    """Add opt-in and suppression controls to the existing CRM leads table."""
    known = {row[1] for row in conn.execute("PRAGMA table_info(leads)")}
    columns = {
        "gtm_consent_status": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
        "gtm_consent_at": "TEXT",
        "gtm_consent_version": "TEXT",
        "gtm_contact_provenance": "TEXT NOT NULL DEFAULT 'legacy_unknown'",
        "gtm_permission_evidence": "TEXT",
        "gtm_campaign_id": "TEXT",
        "gtm_suppressed": "INTEGER NOT NULL DEFAULT 0",
        "gtm_suppressed_at": "TEXT",
        "gtm_owner_approved_at": "TEXT",
        "gtm_approved_proposal_hash": "TEXT",
        "gtm_last_outreach_at": "TEXT",
        "gtm_outreach_count": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, definition in columns.items():
        if name not in known:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {name} {definition}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_gtm_permission ON leads(gtm_consent_status,gtm_suppressed,gtm_campaign_id)")


def ensure_schema(path: Optional[Path | str] = None) -> int:
    """Apply additive, transactional migrations against the canonical backend DB."""
    target = Path(path) if path is not None else Path(backend_database.DB_PATH)
    conn = connect(target)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
        conn.commit()
        applied = {int(row[0]) for row in conn.execute("SELECT version FROM schema_migrations")}
        migrations = [
            (1, "001_legacy_ledger.sql", None),
            (2, "002_task_events.sql", lambda conn: (_add_missing_task_columns(conn), _add_missing_workflow_columns(conn))),
            (3, "003_legacy_projections.sql", _add_missing_event_columns),
            (4, "004_invocation_payload_hash.sql", None),
            (5, "005_workflow_event_idempotency.sql", None),
            (6, "006_llm_runtime.sql", None),
            (7, "007_agent_runtime.sql", None),
            (8, "008_market_research.sql", _add_market_research_columns),
            (9, "009_gtm_crm_analytics.sql", _add_gtm_columns),
            (10, "010_order_to_cash.sql", None),
            (11, "011_cash_reference_uniqueness.sql", None),
            (12, "012_test_mode_orders.sql", None),
            (13, "013_optimization_agent.sql", None),
        ]
        for version, filename, callback in migrations:
            if version in applied:
                continue
            script = (MIGRATION_DIR / filename).read_text(encoding="utf-8")
            conn.execute("BEGIN IMMEDIATE")
            try:
                _apply_script(conn, script)
                if callback:
                    callback(conn)
                conn.execute(
                    "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                    (version, filename, iso()),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        conn.execute(
            "INSERT OR IGNORE INTO workflow_schedules(schedule_id,enabled,updated_at) VALUES('daily_business_cycle',1,?)",
            (iso(),),
        )
        conn.commit()
        return 13
    finally:
        conn.close()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _loads(value: Optional[str], fallback: Any = None) -> Any:
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def redact(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[MAX_DEPTH]"
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            name = str(key)
            if re.search(r"(?i)(password|secret|token|api[_-]?key|authorization|credential|email|phone|account|wallet)", name):
                result[name] = "[REDACTED]"
            else:
                result[name] = redact(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [redact(item, depth + 1) for item in value[:100]]
    if isinstance(value, str):
        value = re.sub(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/-]{8,}", r"\1[REDACTED]", value)
        value = re.sub(
            r"(?i)\b(api[_-]?key|access[_-]?token|secret|password|authorization|credential)\b\s*[:=]\s*[\"']?[^\s,;\"'}\]]+",
            r"\1=[REDACTED]", value,
        )
        value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", value)
        value = re.sub(r"(?<!\d)\d{8,18}(?!\d)", "[REDACTED_NUMBER]", value)
        return value[:1000]
    return value if value is None or isinstance(value, (bool, int, float)) else redact(str(value), depth + 1)


def structured_log(action: str, *, trace_id: Optional[str] = None, **fields: Any) -> None:
    record = {"timestamp": iso(), "level": "INFO", "event": action,
              "trace_id": trace_id, "fields": redact(fields)}
    _LOG.info(_json(record))


def _insert_event(
    conn: sqlite3.Connection,
    task_id: int | str,
    event_type: str,
    state: str,
    title: str,
    *,
    trace_id: str,
    details: Optional[Mapping[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO task_events
           (timestamp, task_id, event_type, status, title, description, source,
            metadata_json, trace_id, idempotency_key)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (iso(), str(task_id), event_type, state, str(redact(title))[:240], None, "business_engine",
         _json(redact(details or {})), trace_id, idempotency_key),
    )


def record_task_event(task_id: int, event_type: str, state: TaskState | str, title: str,
                      *, trace_id: str, idempotency_key: str,
                      details: Optional[Mapping[str, Any]] = None,
                      path: Optional[Path | str] = None) -> int:
    ensure_schema(path)
    if not idempotency_key or len(idempotency_key) > 240:
        raise ValueError("event idempotency key is required")
    target_state = TaskState(state).value
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        if not _task_row(conn, task_id):
            raise KeyError("task not found")
        _insert_event(conn, task_id, event_type, target_state, title,
                      trace_id=trace_id, details=details, idempotency_key=idempotency_key)
        row = conn.execute("SELECT event_id FROM task_events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        conn.commit()
        return int(row[0])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _task_row(conn: sqlite3.Connection, task_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()


def _validate_task_state(row: sqlite3.Row, target: TaskState, expected_version: Optional[int]) -> None:
    current = TaskState(row["state"])
    if expected_version is not None and int(row["state_version"]) != expected_version:
        raise RuntimeError("task version conflict")
    if target not in TRANSITIONS[current]:
        raise ValueError(f"invalid task transition {current.value} -> {target.value}")


def create_task(spec: TaskSpec, *, enqueue: bool = True, path: Optional[Path | str] = None) -> dict[str, Any]:
    ensure_schema(path)
    now = iso()
    task_id_key = spec.idempotency_key.strip() or str(uuid.uuid4())
    trace_id = spec.trace_id.strip() or str(uuid.uuid4())
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        previous = conn.execute("SELECT * FROM tasks WHERE idempotency_key=?", (task_id_key,)).fetchone()
        if previous:
            if (previous["title"] != spec.title or previous["task_type"] != spec.task_type
                    or previous["payload_json"] != _json(spec.payload)):
                raise ValueError("idempotency key was already used for a different task")
            conn.commit()
            return dict(previous)
        cursor = conn.execute(
            """INSERT INTO tasks
               (title,category,assigned_role_id,status,cost_vnd,input_data,created_at,updated_at,
                run_id,task_type,state,state_version,idempotency_key,trace_id,attempts,max_attempts,
                available_at,timeout_seconds,payload_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(redact(spec.title)), str(redact(spec.category)), str(redact(spec.assigned_role_id)), "CREATED", 0.0, _json(redact(spec.payload)), now, now,
             None, spec.task_type, "CREATED", 0, task_id_key, trace_id, 0, spec.max_attempts,
             now, spec.timeout_seconds, _json(spec.payload)),
        )
        task_id = int(cursor.lastrowid)
        _insert_event(conn, task_id, "task_created", "CREATED", spec.title, trace_id=trace_id,
                      details={"category": spec.category, "task_type": spec.task_type},
                      idempotency_key=f"{task_id_key}:created")
        if enqueue:
            conn.execute("UPDATE tasks SET state='QUEUED', status='QUEUED', state_version=1, updated_at=? WHERE id=?", (now, task_id))
            _insert_event(conn, task_id, "task_queued", "QUEUED", spec.title, trace_id=trace_id,
                          idempotency_key=f"{task_id_key}:queued")
        conn.commit()
        row = _task_row(conn, task_id)
        result = dict(row)
        structured_log("task.created", trace_id=trace_id, task_id=task_id, task_type=spec.task_type)
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def transition_task(
    task_id: int,
    target: TaskState | str,
    *,
    expected_version: Optional[int] = None,
    result: Optional[Mapping[str, Any]] = None,
    reason_code: Optional[str] = None,
    path: Optional[Path | str] = None,
) -> dict[str, Any]:
    target = TaskState(target)
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _task_row(conn, task_id)
        if not row:
            raise KeyError("task not found")
        _validate_task_state(row, target, expected_version)
        now = iso()
        trace = row["trace_id"] or str(uuid.uuid4())
        serialized = _json(result) if result is not None else row["result_json"]
        finished = now if target in TERMINAL_STATES else row["finished_at"]
        conn.execute(
            """UPDATE tasks SET state=?,status=?,state_version=state_version+1,updated_at=?,
               finished_at=?,result_json=?,output_data=?,last_error=?,
               lease_owner=CASE WHEN ? IN ('DONE','FAILED','CANCELLED','BLOCKED','WAITING_APPROVAL','RETRY_PENDING') THEN NULL ELSE lease_owner END,
               lease_expires_at=CASE WHEN ? IN ('DONE','FAILED','CANCELLED','BLOCKED','WAITING_APPROVAL','RETRY_PENDING') THEN NULL ELSE lease_expires_at END
               WHERE id=?""",
            (target.value, target.value, now, finished, serialized, serialized,
             reason_code[:120] if reason_code else row["last_error"], target.value, target.value, task_id),
        )
        _insert_event(conn, task_id, "task_state_changed", target.value, row["title"], trace_id=trace,
                      details={"from": row["state"], "to": target.value, "reason_code": reason_code},
                      idempotency_key=f"{row['idempotency_key']}:v{int(row['state_version']) + 1}")
        if row["run_id"]:
            _refresh_run(conn, row["run_id"])
        conn.commit()
        return dict(_task_row(conn, task_id))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _dead_letter(conn: sqlite3.Connection, row: sqlite3.Row, reason: str, now: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO task_dead_letters(task_id,reason,attempts,moved_at) VALUES(?,?,?,?)",
        (row["id"], reason, row["attempts"], now),
    )


def _recover_expired(conn: sqlite3.Connection, now_dt: datetime) -> int:
    now = iso(now_dt)
    running = conn.execute(
        "SELECT * FROM tasks WHERE state='RUNNING'",
    ).fetchall()
    changed = 0
    for row in running:
        start = parse_time(row["started_at"]) if row["started_at"] else now_dt
        lease_expired = bool(row["lease_expires_at"] and row["lease_expires_at"] <= now)
        timed_out = (now_dt - start).total_seconds() >= int(row["timeout_seconds"] or 300)
        if not lease_expired and not timed_out:
            continue
        reason = "task_timeout" if timed_out else "worker_lease_expired"
        attempts = int(row["attempts"])
        if attempts < int(row["max_attempts"]):
            delay = min(3600, 2 ** max(0, attempts - 1))
            available = iso(now_dt + timedelta(seconds=delay))
            state = TaskState.RETRY_PENDING.value
            conn.execute(
                "UPDATE tasks SET state=?,status=?,state_version=state_version+1,updated_at=?,available_at=?,lease_owner=NULL,lease_expires_at=NULL,last_error=? WHERE id=? AND state='RUNNING'",
                (state, state, now, available, reason, row["id"]),
            )
        else:
            state = TaskState.FAILED.value
            conn.execute(
                "UPDATE tasks SET state=?,status=?,state_version=state_version+1,updated_at=?,finished_at=?,lease_owner=NULL,lease_expires_at=NULL,last_error=? WHERE id=? AND state='RUNNING'",
                (state, state, now, now, reason, row["id"]),
            )
            _dead_letter(conn, row, reason, now)
        _insert_event(conn, row["id"], reason, state, row["title"], trace_id=row["trace_id"] or "",
                      details={"attempts": attempts, "reason_code": reason},
                      idempotency_key=f"{row['idempotency_key']}:{reason}:{row['state_version']}")
        if row["run_id"]:
            _refresh_run(conn, row["run_id"])
        changed += 1
    return changed


def recover_crashed_tasks(*, now: Optional[datetime] = None, path: Optional[Path | str] = None) -> int:
    ensure_schema(path)
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        changed = _recover_expired(conn, now or utc_now())
        conn.commit()
        return changed
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def claim_task(worker_id: str, *, lease_seconds: int = 60, now: Optional[datetime] = None,
               path: Optional[Path | str] = None, run_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    if not worker_id or len(worker_id) > 120 or not 1 <= lease_seconds <= 3600:
        raise ValueError("invalid worker lease")
    ensure_schema(path)
    now_dt = now or utc_now()
    now_s = iso(now_dt)
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        _recover_expired(conn, now_dt)
        controls = {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM engine_control")}
        if (controls.get("paused", "0") == "1" or controls.get("shutdown", "0") == "1"
                or _kill_switch_enabled(conn, controls)):
            conn.commit()
            return None
        row = conn.execute(
            """SELECT t.* FROM tasks t WHERE t.state IN ('QUEUED','RETRY_PENDING')
               AND COALESCE(t.available_at,t.created_at)<=?
               AND (? IS NULL OR t.run_id=?)
               AND (t.run_id IS NULL OR EXISTS(SELECT 1 FROM agent_runs r WHERE r.id=t.run_id AND r.status NOT IN ('PAUSED','CANCELLED','DONE','FAILED')))
               AND (t.run_id IS NULL OR NOT EXISTS(SELECT 1 FROM tasks prev WHERE prev.run_id=t.run_id AND prev.id<t.id AND prev.state!='DONE'))
               ORDER BY t.created_at,t.id LIMIT 1""",
            (now_s, run_id, run_id),
        ).fetchone()
        if not row:
            conn.commit()
            return None
        if row["state"] == TaskState.RETRY_PENDING.value:
            conn.execute("UPDATE tasks SET state='QUEUED',status='QUEUED',state_version=state_version+1,updated_at=? WHERE id=? AND state='RETRY_PENDING'",
                         (now_s, row["id"]))
            _insert_event(conn, row["id"], "task_retry_ready", "QUEUED", row["title"],
                          trace_id=row["trace_id"] or "",
                          idempotency_key=f"{row['idempotency_key']}:retry-ready:{row['state_version']}")
            row = _task_row(conn, int(row["id"]))
        lease_expiry = iso(now_dt + timedelta(seconds=lease_seconds))
        cursor = conn.execute(
            """UPDATE tasks SET state='RUNNING',status='RUNNING',state_version=state_version+1,
               attempts=attempts+1,started_at=?,updated_at=?,lease_owner=?,lease_expires_at=?
               WHERE id=? AND state=? AND state_version=?""",
            (now_s, now_s, worker_id, lease_expiry, row["id"], row["state"], row["state_version"]),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return None
        _insert_event(conn, row["id"], "task_claimed", "RUNNING", row["title"], trace_id=row["trace_id"] or "",
                      details={"worker": worker_id, "attempt": int(row["attempts"]) + 1},
                      idempotency_key=f"{row['idempotency_key']}:claim:{int(row['attempts']) + 1}")
        if row["run_id"]:
            conn.execute("UPDATE agent_runs SET status='RUNNING',started_at=COALESCE(started_at,?),updated_at=? WHERE id=? AND status IN ('QUEUED','RUNNING')",
                         (now_s, now_s, row["run_id"]))
        conn.commit()
        return dict(_task_row(conn, int(row["id"])))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def heartbeat_task(task_id: int, worker_id: str, *, lease_seconds: int = 60,
                   now: Optional[datetime] = None, path: Optional[Path | str] = None) -> bool:
    if not 1 <= lease_seconds <= 3600:
        raise ValueError("lease_seconds must be between 1 and 3600")
    conn = connect(path)
    try:
        current = now or utc_now()
        cursor = conn.execute(
            "UPDATE tasks SET lease_expires_at=?,updated_at=? WHERE id=? AND state='RUNNING' AND lease_owner=? AND lease_expires_at>?",
            (iso(current + timedelta(seconds=lease_seconds)), iso(current), task_id, worker_id, iso(current)),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def complete_task(task_id: int, worker_id: str, result: Mapping[str, Any], *,
                  path: Optional[Path | str] = None) -> dict[str, Any]:
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _task_row(conn, task_id)
        if not row or row["state"] != "RUNNING" or row["lease_owner"] != worker_id:
            raise RuntimeError("worker does not own this task lease")
        safe_result = redact(result)
        now = iso()
        conn.execute(
            "UPDATE tasks SET state='DONE',status='DONE',state_version=state_version+1,updated_at=?,finished_at=?,result_json=?,output_data=?,lease_owner=NULL,lease_expires_at=NULL WHERE id=?",
            (now, now, _json(safe_result), _json(safe_result), task_id),
        )
        _insert_event(conn, task_id, "task_completed", "DONE", row["title"], trace_id=row["trace_id"] or "",
                      details={"result": safe_result}, idempotency_key=f"{row['idempotency_key']}:done")
        if row["run_id"]:
            _refresh_run(conn, row["run_id"])
        conn.commit()
        return dict(_task_row(conn, task_id))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fail_task(task_id: int, worker_id: str, reason_code: str, *, retryable: bool = True,
              now: Optional[datetime] = None, path: Optional[Path | str] = None) -> dict[str, Any]:
    now_dt = now or utc_now()
    now_s = iso(now_dt)
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _task_row(conn, task_id)
        if not row or row["state"] != "RUNNING" or row["lease_owner"] != worker_id:
            raise RuntimeError("worker does not own this task lease")
        can_retry = retryable and int(row["attempts"]) < int(row["max_attempts"])
        if can_retry:
            state = TaskState.RETRY_PENDING.value
            delay = min(3600, 2 ** max(0, int(row["attempts"]) - 1))
            available = iso(now_dt + timedelta(seconds=delay))
            conn.execute(
                "UPDATE tasks SET state=?,status=?,state_version=state_version+1,updated_at=?,available_at=?,last_error=?,lease_owner=NULL,lease_expires_at=NULL WHERE id=?",
                (state, state, now_s, available, reason_code[:120], task_id),
            )
        else:
            state = TaskState.FAILED.value
            conn.execute(
                "UPDATE tasks SET state=?,status=?,state_version=state_version+1,updated_at=?,finished_at=?,last_error=?,lease_owner=NULL,lease_expires_at=NULL WHERE id=?",
                (state, state, now_s, now_s, reason_code[:120], task_id),
            )
            _dead_letter(conn, row, reason_code[:120], now_s)
        _insert_event(conn, task_id, "task_failed" if state == "FAILED" else "task_retry_scheduled", state,
                      row["title"], trace_id=row["trace_id"] or "",
                      details={"reason_code": reason_code[:120], "attempts": row["attempts"]},
                      idempotency_key=f"{row['idempotency_key']}:failure:{row['state_version']}")
        if row["run_id"]:
            _refresh_run(conn, row["run_id"])
        conn.commit()
        return dict(_task_row(conn, task_id))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cancel_task(task_id: int, *, path: Optional[Path | str] = None) -> dict[str, Any]:
    return transition_task(task_id, TaskState.CANCELLED, path=path)


def decide_task_approval(task_id: int, decision: str, *, actor: str = "owner",
                         path: Optional[Path | str] = None) -> dict[str, Any]:
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("decision must be APPROVED or REJECTED")
    if decision == "APPROVED":
        return transition_task(task_id, TaskState.QUEUED, reason_code="owner_approved", path=path)
    return transition_task(task_id, TaskState.BLOCKED, reason_code="owner_rejected", path=path)


def list_tasks(*, state: Optional[str] = None, limit: int = 100, path: Optional[Path | str] = None) -> list[dict[str, Any]]:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    conn = connect(path)
    try:
        if state:
            TaskState(state)
            rows = conn.execute("SELECT * FROM tasks WHERE state=? ORDER BY id DESC LIMIT ?", (state, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_task_events(after_id: int = 0, limit: int = 100, *, path: Optional[Path | str] = None) -> list[dict[str, Any]]:
    conn = connect(path)
    try:
        rows = conn.execute(
            "SELECT event_id,timestamp,task_id,run_id,event_type,status,title,source,trace_id,metadata_json FROM task_events WHERE event_id>? ORDER BY event_id LIMIT ?",
            (max(0, after_id), max(1, min(limit, 500))),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["details"] = _loads(item.pop("metadata_json"), {})
            result.append(item)
        return result
    finally:
        conn.close()


WORKFLOW_STEPS = (
    ("research", "RESEARCH"),
    ("build", "BUILD"),
    ("quality", "QUALITY"),
    ("publish_draft", "PUBLISH_DRAFT"),
    ("convert", "CONVERT"),
    ("fulfill", "FULFILL"),
)


def _start_workflow_tx(
    conn: sqlite3.Connection,
    *,
    workflow: str,
    idempotency_key: str,
    payload: Mapping[str, Any],
    scheduled_for: Optional[str] = None,
) -> dict[str, Any]:
    existing = conn.execute("SELECT * FROM agent_runs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    if existing:
        return dict(existing)
    now = iso()
    run_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO agent_runs(id,workflow,status,idempotency_key,trace_id,scheduled_for,payload_json,result_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (run_id, workflow, "QUEUED", idempotency_key, trace_id, scheduled_for, _json(redact(payload)), "{}", now, now),
    )
    for step, label in WORKFLOW_STEPS:
        task_key = f"{idempotency_key}:{step}"
        title = f"{label}: {workflow.replace('_', ' ')}"
        task_payload = {"run_id": run_id, "workflow": workflow, "step": step}
        cursor = conn.execute(
            """INSERT INTO tasks(title,category,assigned_role_id,status,cost_vnd,input_data,
                created_at,updated_at,run_id,task_type,state,state_version,idempotency_key,trace_id,
                attempts,max_attempts,available_at,timeout_seconds,payload_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (title, label, "SYSTEM", "QUEUED", 0.0, _json(task_payload), now, now, run_id,
             f"workflow.{step}", "QUEUED", 1, task_key, trace_id, 0, 3, now, 300, _json(task_payload)),
        )
        _insert_event(conn, int(cursor.lastrowid), "task_created", "CREATED", title,
                      trace_id=trace_id, details={"workflow": workflow, "step": step},
                      idempotency_key=f"{task_key}:created")
        _insert_event(conn, int(cursor.lastrowid), "task_queued", "QUEUED", title,
                      trace_id=trace_id, idempotency_key=f"{task_key}:queued")
    conn.execute(
        "INSERT INTO workflow_events(action,record_kind,record_id,actor,details_json,created_at) VALUES(?,?,?,?,?,?)",
        ("engine_run_created", "agent_run", run_id, "owner", _json({"workflow": workflow}), now),
    )
    return dict(conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone())


def start_agent_workflow(*, idempotency_key: str, payload: Mapping[str, Any],
                         steps: list[Mapping[str, str]], path: Optional[Path | str] = None) -> dict[str, Any]:
    """Create an idempotent, sequential role workflow with real queued tasks."""
    ensure_schema(path)
    key = (idempotency_key or "").strip()
    if not key or len(key) > 180 or not isinstance(payload, Mapping):
        raise ValueError("agent workflow requires an idempotency key and object payload")
    if not 1 <= len(steps) <= 20:
        raise ValueError("agent workflow must contain 1-20 bounded steps")
    normalized = []
    for item in steps:
        role_id = str(item.get("role_id", ""))
        title = str(item.get("title", ""))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", role_id) or not title.strip() or len(title) > 180:
            raise ValueError("agent workflow step is invalid")
        normalized.append((role_id, title))
    safe_payload = redact(payload)
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT * FROM agent_runs WHERE idempotency_key=?", (key,)).fetchone()
        if existing:
            existing_steps = conn.execute(
                "SELECT assigned_role_id,title FROM tasks WHERE run_id=? ORDER BY id", (existing["id"],)
            ).fetchall()
            requested_steps = [(role_id, title) for role_id, title in normalized]
            stored_steps = [(row["assigned_role_id"], row["title"]) for row in existing_steps]
            if (existing["workflow"] != "agent_pipeline" or existing["payload_json"] != _json(safe_payload)
                    or stored_steps != requested_steps):
                raise ValueError("idempotency key was reused for a different agent workflow")
            conn.commit()
            return dict(existing)
        now = iso()
        run_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO agent_runs(id,workflow,status,idempotency_key,trace_id,payload_json,result_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (run_id, "agent_pipeline", "QUEUED", key, trace_id, _json(safe_payload), "{}", now, now),
        )
        for index, (role_id, title) in enumerate(normalized):
            task_key = f"{key}:agent:{index}:{role_id.lower()}"
            task_payload = {"run_id": run_id, "role_id": role_id, "step_index": index, "depth": 0}
            cursor = conn.execute(
                """INSERT INTO tasks(title,category,assigned_role_id,status,cost_vnd,input_data,
                    created_at,updated_at,run_id,task_type,state,state_version,idempotency_key,trace_id,
                    attempts,max_attempts,available_at,timeout_seconds,payload_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (title, "AGENT", role_id, "QUEUED", 0.0, _json(task_payload), now, now, run_id,
                 "agent.execute", "QUEUED", 1, task_key, trace_id, 0, 1, now, 30, _json(task_payload)),
            )
            task_id = int(cursor.lastrowid)
            _insert_event(conn, task_id, "agent.task_created", "CREATED", title, trace_id=trace_id,
                          details={"role_id": role_id, "step_index": index},
                          idempotency_key=f"{task_key}:created")
            _insert_event(conn, task_id, "agent.task_queued", "QUEUED", title, trace_id=trace_id,
                          idempotency_key=f"{task_key}:queued")
        conn.execute(
            "INSERT INTO workflow_events(action,record_kind,record_id,actor,details_json,created_at) VALUES(?,?,?,?,?,?)",
            ("agent_pipeline_created", "agent_run", run_id, "owner", _json({"step_count": len(normalized)}), now),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_agent_artifact(*, run_id: str, task_id: int, role_id: str, title: str,
                        artifact_type: str, mime_type: str, content: str,
                        source_ids: list[str], path: Optional[Path | str] = None) -> dict[str, Any]:
    """Persist a bounded draft artifact and its content hash in the canonical ledger."""
    if not content or len(content.encode("utf-8")) > 100_000 or len(title) > 180:
        raise ValueError("agent artifact must be non-empty and at most 100 KB")
    if not source_ids or len(source_ids) > 20:
        raise ValueError("agent artifact requires 1-20 source references")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    artifact_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{task_id}:{digest}"))
    conn = connect(path)
    try:
        now = iso()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """INSERT OR IGNORE INTO agent_artifacts
               (id,run_id,task_id,role_id,title,artifact_type,mime_type,content,content_sha256,source_ids_json,status,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (artifact_id, run_id, task_id, role_id, redact(title), artifact_type, mime_type,
             content, digest, _json(sorted(set(source_ids))), "DRAFT", now),
        )
        row = conn.execute("SELECT id,run_id,task_id,role_id,title,artifact_type,mime_type,content_sha256,source_ids_json,status,created_at FROM agent_artifacts WHERE id=?", (artifact_id,)).fetchone()
        conn.commit()
        result = dict(row)
        result["source_ids"] = _loads(result.pop("source_ids_json"), [])
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_agent_artifact(artifact_id: str, *, path: Optional[Path | str] = None) -> Optional[dict[str, Any]]:
    conn = connect(path)
    try:
        row = conn.execute("SELECT * FROM agent_artifacts WHERE id=?", (artifact_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["source_ids"] = _loads(result.pop("source_ids_json"), [])
        return result
    finally:
        conn.close()


def save_agent_memory(*, run_id: str, namespace: str, source_id: str, source_uri: str,
                      source_sha256: str, fact: str, ttl_days: int = 30,
                      path: Optional[Path | str] = None) -> str:
    """Store a source-cited fact with bounded TTL; never store uncited memory."""
    if not all((run_id, namespace, source_id, source_uri, source_sha256, fact.strip())):
        raise ValueError("agent memory requires a fact and complete source citation")
    if not 1 <= ttl_days <= 365 or len(fact) > 800:
        raise ValueError("agent memory TTL or fact length is outside limits")
    memory_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{namespace}:{source_id}:{hashlib.sha256(fact.encode()).hexdigest()}"))
    now = utc_now()
    conn = connect(path)
    try:
        conn.execute("INSERT OR IGNORE INTO agent_memory(id,run_id,namespace,source_id,source_uri,source_sha256,fact,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?)",
                     (memory_id, run_id, namespace, source_id, source_uri, source_sha256, redact(fact),
                      iso(now), iso(now + timedelta(days=ttl_days))))
        conn.commit()
        return memory_id
    finally:
        conn.close()


def list_agent_memory(namespace: str, *, now: Optional[datetime] = None,
                      path: Optional[Path | str] = None) -> list[dict[str, Any]]:
    current = iso(now or utc_now())
    conn = connect(path)
    try:
        conn.execute("DELETE FROM agent_memory WHERE expires_at<=? OR deleted_at IS NOT NULL", (current,))
        conn.commit()
        rows = conn.execute("SELECT id,run_id,namespace,source_id,source_uri,source_sha256,fact,created_at,expires_at FROM agent_memory WHERE namespace=? AND deleted_at IS NULL AND expires_at>? ORDER BY created_at DESC LIMIT 200", (namespace, current)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_agent_memory(memory_id: str, *, now: Optional[datetime] = None,
                        path: Optional[Path | str] = None) -> bool:
    conn = connect(path)
    try:
        cursor = conn.execute("DELETE FROM agent_memory WHERE id=?", (memory_id,))
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def start_workflow(
    workflow: str = "daily_business_cycle",
    *,
    idempotency_key: Optional[str] = None,
    payload: Optional[Mapping[str, Any]] = None,
    path: Optional[Path | str] = None,
) -> dict[str, Any]:
    ensure_schema(path)
    if workflow != "daily_business_cycle":
        raise ValueError("unknown workflow")
    key = (idempotency_key or f"manual:{uuid.uuid4()}").strip()
    if not key or len(key) > 180:
        raise ValueError("idempotency_key must contain 1-180 characters")
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        run = _start_workflow_tx(conn, workflow=workflow, idempotency_key=key, payload=payload or {})
        conn.commit()
        structured_log("workflow.created", trace_id=run["trace_id"], run_id=run["id"], workflow=workflow)
        return run
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def schedule_daily_workflow(*, now: Optional[datetime] = None,
                            path: Optional[Path | str] = None) -> Optional[dict[str, Any]]:
    ensure_schema(path)
    current = now or utc_now()
    day = current.date().isoformat()
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        control = conn.execute("SELECT value FROM engine_control WHERE key='paused'").fetchone()
        shutdown = conn.execute("SELECT value FROM engine_control WHERE key='shutdown'").fetchone()
        schedule = conn.execute("SELECT enabled,last_run_date FROM workflow_schedules WHERE schedule_id='daily_business_cycle'").fetchone()
        controls = {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM engine_control")}
        if ((control and control[0] == "1") or (shutdown and shutdown[0] == "1")
                or _kill_switch_enabled(conn, controls) or not schedule
                or not schedule["enabled"] or schedule["last_run_date"] == day):
            conn.commit()
            return None
        run = _start_workflow_tx(
            conn,
            workflow="daily_business_cycle",
            idempotency_key=f"daily:{day}",
            payload={"trigger": "daily_scheduler"},
            scheduled_for=day,
        )
        conn.execute("UPDATE workflow_schedules SET last_run_date=?,updated_at=? WHERE schedule_id='daily_business_cycle'", (day, iso(current)))
        conn.commit()
        return run
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _refresh_run(conn: sqlite3.Connection, run_id: str) -> None:
    run = conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
    if not run or run["status"] in {"CANCELLED", "PAUSED"}:
        return
    rows = conn.execute("SELECT state,task_type,assigned_role_id,result_json FROM tasks WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
    if not rows:
        return
    states = {row["state"] for row in rows}
    if states <= {"DONE"}:
        status = "DONE"
        result = {
            (row["assigned_role_id"] if row["task_type"] == "agent.execute"
             else row["task_type"].removeprefix("workflow.")): _loads(row["result_json"], {})
            for row in rows
        }
        finished = iso()
    elif "FAILED" in states:
        status, result, finished = "FAILED", {"reason_code": "workflow_step_failed"}, iso()
    elif "WAITING_APPROVAL" in states:
        status, result, finished = "WAITING_APPROVAL", {}, None
    elif "BLOCKED" in states:
        status, result, finished = "BLOCKED", {}, None
    elif states <= {"CANCELLED"}:
        status, result, finished = "CANCELLED", {}, iso()
    elif "RUNNING" in states:
        status, result, finished = "RUNNING", {}, None
    else:
        status, result, finished = "QUEUED", {}, None
    conn.execute("UPDATE agent_runs SET status=?,result_json=?,finished_at=COALESCE(?,finished_at),updated_at=? WHERE id=?",
                 (status, _json(redact(result)), finished, iso(), run_id))


def get_workflow_run(run_id: str, *, path: Optional[Path | str] = None) -> Optional[dict[str, Any]]:
    conn = connect(path)
    try:
        row = conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["payload"] = _loads(result.pop("payload_json"), {})
        result["result"] = _loads(result.pop("result_json"), {})
        result["steps"] = [
            {"id": task["id"], "title": task["title"], "task_type": task["task_type"],
             "state": task["state"], "state_version": task["state_version"],
             "attempts": task["attempts"], "last_error": task["last_error"],
             "result": _loads(task["result_json"], {})}
            for task in conn.execute("SELECT * FROM tasks WHERE run_id=? ORDER BY id", (run_id,))
        ]
        return result
    finally:
        conn.close()


def list_workflow_runs(limit: int = 100, *, path: Optional[Path | str] = None) -> list[dict[str, Any]]:
    conn = connect(path)
    try:
        rows = conn.execute("SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
        return [{**dict(row), "payload": _loads(row["payload_json"], {}), "result": _loads(row["result_json"], {})} for row in rows]
    finally:
        conn.close()


def pause_workflow(run_id: str, *, path: Optional[Path | str] = None) -> bool:
    conn = connect(path)
    try:
        cursor = conn.execute("UPDATE agent_runs SET status='PAUSED',updated_at=? WHERE id=? AND status IN ('QUEUED','RUNNING','WAITING_APPROVAL')", (iso(), run_id))
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def resume_workflow(run_id: str, *, path: Optional[Path | str] = None) -> bool:
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute("UPDATE agent_runs SET status='QUEUED',updated_at=? WHERE id=? AND status IN ('PAUSED','BLOCKED')", (iso(), run_id))
        if cursor.rowcount == 1:
            now = iso()
            blocked = conn.execute("SELECT * FROM tasks WHERE run_id=? AND state='BLOCKED'", (run_id,)).fetchall()
            for task in blocked:
                conn.execute("UPDATE tasks SET state='QUEUED',status='QUEUED',state_version=state_version+1,updated_at=?,available_at=? WHERE id=? AND state='BLOCKED'",
                             (now, now, task["id"]))
                _insert_event(conn, task["id"], "task_unblocked_for_resume", "QUEUED", task["title"],
                              trace_id=task["trace_id"] or "",
                              idempotency_key=f"{task['idempotency_key']}:resume:{task['state_version']}")
            _refresh_run(conn, run_id)
        conn.commit()
        return cursor.rowcount == 1
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cancel_workflow(run_id: str, *, path: Optional[Path | str] = None) -> bool:
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        run = conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
        if not run or run["status"] in {"DONE", "FAILED", "CANCELLED"}:
            conn.commit()
            return False
        now = iso()
        tasks = conn.execute("SELECT * FROM tasks WHERE run_id=? AND state NOT IN ('DONE','FAILED','CANCELLED')", (run_id,)).fetchall()
        for task in tasks:
            conn.execute("UPDATE tasks SET state='CANCELLED',status='CANCELLED',state_version=state_version+1,updated_at=?,finished_at=?,lease_owner=NULL,lease_expires_at=NULL WHERE id=?", (now, now, task["id"]))
            _insert_event(conn, task["id"], "task_cancelled", "CANCELLED", task["title"], trace_id=task["trace_id"] or "",
                          idempotency_key=f"{task['idempotency_key']}:cancel:{task['state_version']}")
        conn.execute("UPDATE agent_runs SET status='CANCELLED',finished_at=?,updated_at=? WHERE id=?", (now, now, run_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def set_engine_control(key: str, enabled: bool, *, path: Optional[Path | str] = None) -> None:
    if key not in {"paused", "shutdown", "kill_switch"}:
        raise ValueError("unknown engine control")
    if key == "paused" and not enabled:
        conn = connect(path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("INSERT INTO engine_control(key,value,updated_at) VALUES('shutdown','0',?) ON CONFLICT(key) DO UPDATE SET value='0',updated_at=excluded.updated_at", (iso(),))
            conn.execute("INSERT INTO engine_control(key,value,updated_at) VALUES('paused','0',?) ON CONFLICT(key) DO UPDATE SET value='0',updated_at=excluded.updated_at", (iso(),))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return
    conn = connect(path)
    try:
        conn.execute("INSERT INTO engine_control(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                     (key, "1" if enabled else "0", iso()))
        if key == "shutdown" and enabled:
            conn.execute("INSERT INTO engine_control(key,value,updated_at) VALUES('paused','1',?) ON CONFLICT(key) DO UPDATE SET value='1',updated_at=excluded.updated_at", (iso(),))
        conn.commit()
    finally:
        conn.close()


def engine_status(*, path: Optional[Path | str] = None) -> dict[str, Any]:
    conn = connect(path)
    try:
        controls = {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM engine_control")}
        counts = {row["state"]: int(row["n"]) for row in conn.execute("SELECT state,COUNT(*) AS n FROM tasks GROUP BY state")}
        return {"paused": controls.get("paused", "0") == "1",
                "shutdown": controls.get("shutdown", "0") == "1",
                "kill_switch": _kill_switch_enabled(conn, controls),
                "queue": counts}
    finally:
        conn.close()


def _workflow_step_result(task: Mapping[str, Any], *, path: Optional[Path | str] = None) -> dict[str, Any]:
    """Run only local, read-only diagnostics for the persisted daily workflow."""
    payload = _loads(task.get("payload_json"), {}) or {}
    step = str(payload.get("step", ""))
    conn = connect(path)
    try:
        if step == "research":
            count = int(conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0])
            return {"step": step, "status": "observed" if count else "no_verified_data", "opportunities": count}
        if step == "build":
            products = int(conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0])
            assets = int(conn.execute("SELECT COUNT(*) FROM assets WHERE status IN ('READY','PUBLISHED')").fetchone()[0])
            return {"step": step, "status": "observed" if products or assets else "no_ready_product_or_asset",
                    "active_products": products, "ready_assets": assets}
        if step == "quality":
            columns = {row[1] for row in conn.execute("PRAGMA table_info(products)")}
            if not {"slug", "name", "active"}.issubset(columns):
                return {"step": step, "status": "blocked", "reason_code": "product_schema_unavailable"}
            invalid = int(conn.execute("SELECT COUNT(*) FROM products WHERE active=1 AND (slug IS NULL OR trim(slug)='' OR name IS NULL OR trim(name)='')").fetchone()[0])
            active = int(conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0])
            return {"step": step, "status": "checks_complete", "checked_products": active,
                    "invalid_products": invalid, "quality_pass": invalid == 0 and active > 0}
        if step == "publish_draft":
            run_id = str(payload.get("run_id", ""))
            run = conn.execute("SELECT trace_id FROM agent_runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                return {"step": step, "status": "blocked", "reason_code": "workflow_run_missing"}
            opportunity_count = int(conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0])
            product_count = int(conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0])
            draft_payload = {"draft_type": "daily_business_summary", "run_id": run_id,
                             "source_counts": {"opportunities": opportunity_count, "active_products": product_count},
                             "publish_allowed": False, "requires_owner_approval": True}
            key = f"engine:{run_id}:publish-draft"
            serialized = _json(redact(draft_payload))
            fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            now = iso()
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO workflow_records(id,kind,status,payload_json,created_at,updated_at,idempotency_key,idempotency_hash) VALUES(?, 'publish_draft','DRAFT',?,?,?,?,?)",
                    (str(uuid.uuid4()), serialized, now, now, key, fingerprint),
                )
                draft = conn.execute("SELECT id,status FROM workflow_records WHERE idempotency_key=?", (key,)).fetchone()
                conn.execute("INSERT OR IGNORE INTO workflow_events(idempotency_key,action,record_kind,record_id,actor,details_json,created_at) VALUES(?, 'engine_publish_draft_created','publish_draft',?,'system',?,?)",
                             (f"{key}:event", draft["id"], _json({"run_id": run_id, "publish_allowed": False}), now))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return {"step": step, "status": "draft_only", "draft_id": draft["id"],
                    "published": False, "requires_owner_approval": True,
                    "reason_code": "publishing_requires_explicit_approval"}
        if step == "convert":
            count = int(conn.execute("SELECT COUNT(*) FROM verified_transactions").fetchone()[0])
            return {"step": step, "status": "observed" if count else "no_verified_conversions",
                    "verified_transactions": count}
        if step == "fulfill":
            paid = int(conn.execute("SELECT COUNT(*) FROM orders WHERE status IN ('PAID_VERIFIED','FULFILLED')").fetchone()[0])
            pending = int(conn.execute("SELECT COUNT(*) FROM orders WHERE status='PAID_VERIFIED'").fetchone()[0])
            return {"step": step, "status": "owner_review_required" if pending else "no_paid_orders",
                    "verified_orders": paid, "awaiting_delivery": pending, "delivered": 0}
        return {"step": step or "unknown", "status": "blocked", "reason_code": "unknown_workflow_step"}
    finally:
        conn.close()


def run_worker_once(worker_id: str, *, lease_seconds: int = 60,
                    path: Optional[Path | str] = None,
                    run_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    task = claim_task(worker_id, lease_seconds=lease_seconds, path=path, run_id=run_id)
    if not task:
        return None
    task_id = int(task["id"])
    if task["task_type"] == "agent.execute":
        try:
            from core.agent_runtime import execute_agent_task
            result = execute_agent_task(task, path=path)
            output_state = result.get("status")
            if output_state == "WAITING_APPROVAL":
                final = transition_task(task_id, TaskState.WAITING_APPROVAL, result=result,
                                        reason_code="owner_approval_required", path=path)
            elif output_state in {"BLOCKED", "NOT_IMPLEMENTED"}:
                reason = result.get("result", {}).get("reason_code", "agent_task_blocked")
                final = transition_task(task_id, TaskState.BLOCKED, result=result,
                                        reason_code=reason, path=path)
            else:
                final = complete_task(task_id, worker_id, result, path=path)
            return {"task_id": task_id, "state": final["state"], "result": result}
        except Exception as exc:
            reason = f"agent_step_error:{type(exc).__name__}"
            failed = fail_task(task_id, worker_id, reason, retryable=False, path=path)
            structured_log("agent.task_failed", trace_id=task.get("trace_id"), task_id=task_id,
                           role_id=task.get("assigned_role_id"), reason_code=reason)
            return {"task_id": task_id, "state": failed["state"], "reason_code": reason}
    if not str(task["task_type"]).startswith("workflow."):
        fail_task(task_id, worker_id, "unregistered_task_type", retryable=False, path=path)
        return {"task_id": task_id, "state": "FAILED", "reason_code": "unregistered_task_type"}
    try:
        result = _workflow_step_result(task, path=path)
        if task["task_type"] == "workflow.quality" and not result.get("quality_pass"):
            blocked = transition_task(task_id, TaskState.BLOCKED, result=result,
                                      reason_code="quality_gate_failed", path=path)
            structured_log("task.blocked", trace_id=task.get("trace_id"), task_id=task_id,
                           reason_code="quality_gate_failed")
            return {"task_id": task_id, "state": blocked["state"], "result": result}
        final = complete_task(task_id, worker_id, result, path=path)
        if final.get("run_id"):
            conn = connect(path)
            try:
                conn.execute("BEGIN IMMEDIATE")
                _refresh_run(conn, final["run_id"])
                conn.commit()
            finally:
                conn.close()
        return {"task_id": task_id, "state": final["state"], "result": result}
    except Exception as exc:
        reason = f"internal_step_error:{type(exc).__name__}"
        failed = fail_task(task_id, worker_id, reason, retryable=True, path=path)
        structured_log("task.failed", trace_id=task.get("trace_id"), task_id=task_id,
                       reason_code=reason, state=failed["state"])
        return {"task_id": task_id, "state": failed["state"], "reason_code": reason}


def record_analytics_event(session_id: str, path_name: str, *, internal_test: bool = False,
                           occurred_at: Optional[str] = None,
                           path: Optional[Path | str] = None) -> bool:
    """Record first-party analytics only; explicitly marked test traffic is dropped."""
    if internal_test:
        return False
    ensure_schema(path)
    try:
        uuid.UUID(session_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("session_id must be a UUID") from exc
    cleaned = path_name.split("?", 1)[0].split("#", 1)[0]
    if not cleaned.startswith("/") or cleaned.startswith("/api/") or len(cleaned) > 200:
        raise ValueError("invalid analytics path")
    now = occurred_at or iso()
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO telemetry_sessions(session_id,created_at,last_seen_at) VALUES(?,?,?) ON CONFLICT(session_id) DO UPDATE SET last_seen_at=excluded.last_seen_at",
                     (session_id, now, now))
        conn.execute("INSERT INTO telemetry_pageviews(session_id,path,occurred_at) VALUES(?,?,?)",
                     (session_id, cleaned, now))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fulfill_verified_order(order_id: str, asset_id: Optional[str], *, path: Optional[Path | str] = None) -> dict[str, Any]:
    ensure_schema(path)
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM workflow_records WHERE kind='order' AND id=?", (order_id,)).fetchone()
        if not row:
            raise KeyError("order not found")
        if row["status"] not in {"PAID_VERIFIED", "FULFILLED"}:
            raise PermissionError("order payment is not verified")
        key = f"delivery:{order_id}:download"
        existing = conn.execute("SELECT * FROM deliveries WHERE idempotency_key=?", (key,)).fetchone()
        if existing:
            conn.commit()
            return dict(existing)
        now = iso()
        delivery_id = str(uuid.uuid4())
        conn.execute("INSERT INTO deliveries(id,order_id,asset_id,status,delivered_at,idempotency_key,trace_id,created_at,updated_at) VALUES(?,?,?,'FULFILLED',?,?,?,?,?)",
                     (delivery_id, order_id, asset_id, now, key, str(uuid.uuid4()), now, now))
        payload = _loads(row["payload_json"], {}) or {}
        payload.update({"status": "FULFILLED", "delivered_at": now})
        conn.execute("UPDATE workflow_records SET status='FULFILLED',payload_json=?,updated_at=? WHERE kind='order' AND id=? AND status IN ('PAID_VERIFIED','FULFILLED')",
                     (_json(redact(payload)), now, order_id))
        conn.execute("INSERT OR IGNORE INTO workflow_events(idempotency_key,action,record_kind,record_id,actor,details_json,created_at) VALUES(?, 'order_delivery_unlocked','order',?,'owner',?,?)",
                     (f"{key}:event", order_id, _json({"asset_id": asset_id}), now))
        conn.commit()
        return dict(conn.execute("SELECT * FROM deliveries WHERE id=?", (delivery_id,)).fetchone())
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    permission: str
    provider: str
    action: str
    estimated_cost_minor: Optional[int]
    offline: bool
    handler: Optional[Callable[[Mapping[str, Any]], Any]] = None


_TOOL_REGISTRY: dict[str, ToolDefinition] = {}


def register_tool(definition: ToolDefinition) -> None:
    if (not definition.name or not definition.permission or not definition.action or not definition.provider
            or "*" in definition.name or "*" in definition.permission
            or definition.estimated_cost_minor is not None
            and (not isinstance(definition.estimated_cost_minor, int) or isinstance(definition.estimated_cost_minor, bool)
                 or definition.estimated_cost_minor < 0)):
        raise ValueError("tool definition requires exact name, permission, action, provider, and nonnegative cost")
    current = _TOOL_REGISTRY.get(definition.name)
    if current and current != definition:
        raise ValueError("tool name is already registered with a different policy")
    _TOOL_REGISTRY[definition.name] = definition


def tool_registry() -> list[dict[str, Any]]:
    return [{"name": item.name, "permission": item.permission, "provider": item.provider,
             "action": item.action, "estimated_cost_minor": item.estimated_cost_minor,
             "offline": item.offline, "dry_run_default": not item.offline}
            for item in sorted(_TOOL_REGISTRY.values(), key=lambda tool: tool.name)]


register_tool(ToolDefinition("local.inspect_ledger", "ledger.read", "local_sqlite", "read_summary", 0, True,
                             lambda payload: {"status": "observed", "queue": engine_status()["queue"]}))


def _create_internal_draft(payload: Mapping[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title", "")).strip()
    if not title or len(title) > 200:
        raise ValueError("draft title must contain 1-200 characters")
    invocation_key = str(payload.get("_engine_idempotency_key", "")).strip()
    if not invocation_key:
        raise ValueError("engine idempotency key is missing")
    content = str(payload.get("content", ""))[:10000]
    safe_payload = redact({"title": title, "content": content})
    serialized = _json(safe_payload)
    fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    key = f"tool-draft:{invocation_key}"
    now = iso()
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT OR IGNORE INTO workflow_records(id,kind,status,payload_json,created_at,updated_at,idempotency_key,idempotency_hash) VALUES(?, 'internal_draft','DRAFT',?,?,?,?,?)",
                     (str(uuid.uuid4()), serialized, now, now, key, fingerprint))
        row = conn.execute("SELECT id,status FROM workflow_records WHERE idempotency_key=?", (key,)).fetchone()
        conn.execute("INSERT OR IGNORE INTO workflow_events(idempotency_key,action,record_kind,record_id,actor,details_json,created_at) VALUES(?, 'internal_draft_created','internal_draft',?,'tool',?,?)",
                     (f"{key}:event", row["id"], _json({"payload_hash": fingerprint}), now))
        conn.commit()
        return {"draft_id": row["id"], "status": row["status"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


register_tool(ToolDefinition("local.create_draft", "ledger.draft.write", "local_sqlite", "create_draft", 0, True,
                             _create_internal_draft))
register_tool(ToolDefinition("integration.publish", "external.publish", "unverified_external", "publish_content", None, False))
register_tool(ToolDefinition("integration.contact", "external.contact", "unverified_external", "send_message", None, False))


class PolicyDenied(RuntimeError):
    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _kill_switch_enabled(conn: sqlite3.Connection, controls: Optional[Mapping[str, str]] = None) -> bool:
    controls = controls or {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM engine_control")}
    if "kill_switch" in controls:
        return controls["kill_switch"] == "1"
    return os.getenv("AUTOPROFIT_ENGINE_KILL_SWITCH", "true").strip().lower() not in {"0", "false", "no", "off"}


def grant_privilege(principal: str, permission: str, *, actor: str = "owner",
                    path: Optional[Path | str] = None) -> None:
    ensure_schema(path)
    if not principal or not permission or len(principal) > 120 or len(permission) > 120 or "*" in permission:
        raise ValueError("exact principal and permission are required")
    conn = connect(path)
    try:
        conn.execute("INSERT INTO tool_grants(principal,permission,granted_by,granted_at,revoked_at) VALUES(?,?,?,?,NULL) ON CONFLICT(principal,permission) DO UPDATE SET granted_by=excluded.granted_by,granted_at=excluded.granted_at,revoked_at=NULL",
                     (principal, permission, actor, iso()))
        conn.commit()
    finally:
        conn.close()


def revoke_privilege(principal: str, permission: str, *, actor: str = "owner",
                     path: Optional[Path | str] = None) -> bool:
    ensure_schema(path)
    conn = connect(path)
    try:
        cursor = conn.execute("UPDATE tool_grants SET revoked_at=? WHERE principal=? AND permission=? AND revoked_at IS NULL",
                              (iso(), principal, permission))
        conn.execute("INSERT INTO engine_audit_events(actor,action,subject_type,subject_id,trace_id,details_json,created_at) VALUES(?,?,?,?,?,?,?)",
                     (actor, "tool_privilege_revoked", "permission", permission, str(uuid.uuid4()), _json({"principal": principal}), iso()))
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def request_approval(tool_name: str, principal: str, payload: Mapping[str, Any], *,
                     idempotency_key: Optional[str] = None, expires_in_seconds: int = 3600,
                     path: Optional[Path | str] = None) -> dict[str, Any]:
    ensure_schema(path)
    tool = _TOOL_REGISTRY.get(tool_name)
    if not tool:
        raise ValueError("unknown tool")
    if not isinstance(payload, Mapping) or not principal or len(principal) > 120:
        raise ValueError("approval requires a principal and object payload")
    if not 60 <= expires_in_seconds <= 72 * 3600:
        raise ValueError("approval expiry must be 60 seconds to 72 hours")
    key = idempotency_key or str(uuid.uuid4())
    if not key or len(key) > 180:
        raise ValueError("approval idempotency key must contain 1-180 characters")
    body_hash = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
    trace = str(uuid.uuid4())
    now = utc_now()
    expires = iso(now + timedelta(seconds=expires_in_seconds))
    request_payload = {"payload_sha256": body_hash}
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT * FROM approval_requests WHERE idempotency_key=?", (key,)).fetchone()
        if existing:
            if existing["tool_name"] != tool_name or existing["requested_by"] != principal or existing["payload_json"] != _json(request_payload):
                raise ValueError("approval idempotency key was reused for a different request")
            conn.commit()
            return dict(existing)
        approval_id = str(uuid.uuid4())
        conn.execute("INSERT INTO approval_requests(id,tool_name,permission,requested_by,status,idempotency_key,trace_id,payload_json,expires_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                     (approval_id, tool_name, tool.permission, principal, "PENDING", key, trace,
                      _json(request_payload), expires, iso(now)))
        conn.execute("INSERT INTO engine_audit_events(actor,action,subject_type,subject_id,trace_id,details_json,created_at) VALUES(?,?,?,?,?,?,?)",
                     (principal, "approval_requested", "approval_request", approval_id, trace,
                      _json({"tool_name": tool_name, "permission": tool.permission, "payload_hash": body_hash}), iso(now)))
        conn.commit()
        return dict(conn.execute("SELECT * FROM approval_requests WHERE id=?", (approval_id,)).fetchone())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def decide_approval(approval_id: str, decision: str, *, actor: str = "owner", reason: str = "",
                    now: Optional[datetime] = None, path: Optional[Path | str] = None) -> dict[str, Any]:
    ensure_schema(path)
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("decision must be APPROVED or REJECTED")
    current = now or utc_now()
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM approval_requests WHERE id=?", (approval_id,)).fetchone()
        if not row:
            raise KeyError("approval request not found")
        if row["status"] != "PENDING":
            raise ValueError("approval request is no longer pending")
        if parse_time(row["expires_at"]) <= current:
            conn.execute("UPDATE approval_requests SET status='EXPIRED',decided_at=?,decision_by='system',decision_reason='expired' WHERE id=? AND status='PENDING'",
                         (iso(current), approval_id))
            conn.commit()
            raise TimeoutError("approval request expired")
        conn.execute("UPDATE approval_requests SET status=?,decision_by=?,decision_reason=?,decided_at=? WHERE id=? AND status='PENDING'",
                     (decision, actor, reason[:240], iso(current), approval_id))
        conn.execute("INSERT INTO engine_audit_events(actor,action,subject_type,subject_id,trace_id,details_json,created_at) VALUES(?,?,?,?,?,?,?)",
                     (actor, "approval_decided", "approval_request", approval_id, row["trace_id"], _json({"decision": decision}), iso(current)))
        conn.commit()
        return dict(conn.execute("SELECT * FROM approval_requests WHERE id=?", (approval_id,)).fetchone())
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def list_approvals(limit: int = 100, *, path: Optional[Path | str] = None) -> list[dict[str, Any]]:
    ensure_schema(path)
    conn = connect(path)
    try:
        now = iso()
        conn.execute("UPDATE approval_requests SET status='EXPIRED',decided_at=?,decision_by='system',decision_reason='expired' WHERE status='PENDING' AND expires_at<=?", (now, now))
        conn.commit()
        return [dict(row) for row in conn.execute("SELECT * FROM approval_requests ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),))]
    finally:
        conn.close()


def _exposure(conn: sqlite3.Connection, tool: ToolDefinition, status: str, reason: str,
              trace_id: str, *, estimated: Optional[int]) -> str:
    exposure_id = str(uuid.uuid4())
    conn.execute("INSERT INTO cost_exposures(id,tool_name,provider,action,estimated_minor,currency,status,reason_code,trace_id,created_at) VALUES(?,?,?,?,?,'VND',?,?,?,?)",
                 (exposure_id, tool.name, tool.provider, tool.action, estimated, status, reason, trace_id, iso()))
    return exposure_id


def invoke_tool(tool_name: str, principal: str, payload: Mapping[str, Any], *, dry_run: bool = True,
                approval_id: Optional[str] = None, idempotency_key: Optional[str] = None,
                path: Optional[Path | str] = None) -> dict[str, Any]:
    ensure_schema(path)
    tool = _TOOL_REGISTRY.get(tool_name)
    if not tool:
        raise PolicyDenied("unknown_tool")
    if not isinstance(payload, Mapping) or not principal or len(principal) > 120:
        raise ValueError("principal and object payload are required")
    key = (idempotency_key or str(uuid.uuid4())).strip()
    if not key or len(key) > 180:
        raise ValueError("invalid idempotency key")
    trace_id = str(uuid.uuid4())
    now = iso()
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT * FROM tool_invocations WHERE idempotency_key=?", (key,)).fetchone()
        if existing:
            incoming_hash = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
            if (existing["tool_name"] != tool_name or existing["principal"] != principal
                    or existing["permission"] != tool.permission or existing["payload_hash"] != incoming_hash):
                conn.commit()
                return {"status": "BLOCKED", "reason_code": "idempotency_key_payload_conflict"}
            conn.commit()
            if existing["status"] in {"DONE", "FAILED", "DRY_RUN", "BLOCKED"}:
                return {"status": existing["status"], "result": _loads(existing["result_json"], {}),
                        "trace_id": existing["trace_id"]}
            return {"status": existing["status"], "reason_code": "idempotency_key_already_in_use"}
        controls = {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM engine_control")}
        cost = tool.estimated_cost_minor
        payload_hash = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
        if _kill_switch_enabled(conn, controls):
            _exposure(conn, tool, "BLOCKED", "kill_switch_enabled", trace_id, estimated=cost)
            conn.commit()
            return {"status": "BLOCKED", "reason_code": "kill_switch_enabled", "trace_id": trace_id}
        if cost is not None and cost > 0:
            _exposure(conn, tool, "BLOCKED", "paid_exposure_forbidden", trace_id, estimated=cost)
            conn.commit()
            return {"status": "BLOCKED", "reason_code": "paid_exposure_forbidden", "trace_id": trace_id}
        if cost is None:
            status, reason = ("DRY_RUN", "unverified_cost_dry_run") if dry_run else ("BLOCKED", "unknown_cost_or_provider")
            _exposure(conn, tool, status, reason, trace_id, estimated=None)
            result = {"status": status, "reason_code": reason, "tool": tool_name, "dry_run": dry_run}
            conn.execute("INSERT INTO tool_invocations(idempotency_key,tool_name,permission,principal,approval_id,status,trace_id,result_json,created_at,updated_at,payload_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (key, tool_name, tool.permission, principal, approval_id, status, trace_id, _json(result), now, now, payload_hash))
            conn.commit()
            return result
        if not tool.offline and dry_run:
            _exposure(conn, tool, "DRY_RUN", "untrusted_integration_dry_run", trace_id, estimated=cost)
            result = {"status": "DRY_RUN", "reason_code": "untrusted_integration_dry_run", "tool": tool_name,
                      "permission": tool.permission, "action": tool.action, "provider": tool.provider}
            conn.execute("INSERT INTO tool_invocations(idempotency_key,tool_name,permission,principal,approval_id,status,trace_id,result_json,created_at,updated_at,payload_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (key, tool_name, tool.permission, principal, approval_id, "DRY_RUN", trace_id, _json(result), now, now, payload_hash))
            conn.commit()
            return result
        if not tool.offline:
            grant = conn.execute("SELECT 1 FROM tool_grants WHERE principal=? AND permission=? AND revoked_at IS NULL",
                                 (principal, tool.permission)).fetchone()
            if not grant:
                _exposure(conn, tool, "BLOCKED", "exact_privilege_missing_or_revoked", trace_id, estimated=cost)
                conn.commit()
                return {"status": "BLOCKED", "reason_code": "exact_privilege_missing_or_revoked", "trace_id": trace_id}
            approval = conn.execute("SELECT * FROM approval_requests WHERE id=?", (approval_id,)).fetchone() if approval_id else None
            payload_hash = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
            approved_payload = _loads(approval["payload_json"], {}) if approval else {}
            if (not approval or approval["tool_name"] != tool.name or approval["permission"] != tool.permission
                    or approval["requested_by"] != principal or approval["status"] != "APPROVED"
                    or approval["consumed_at"] or parse_time(approval["expires_at"]) <= utc_now()
                    or approved_payload.get("payload_sha256") != payload_hash):
                _exposure(conn, tool, "APPROVAL_REQUIRED", "matching_approval_required", trace_id, estimated=cost)
                conn.commit()
                return {"status": "BLOCKED", "reason_code": "matching_approval_required", "trace_id": trace_id}
            if tool.handler is None:
                _exposure(conn, tool, "BLOCKED", "tool_handler_unavailable", trace_id, estimated=cost)
                conn.commit()
                return {"status": "BLOCKED", "reason_code": "tool_handler_unavailable", "trace_id": trace_id}
            updated = conn.execute("UPDATE approval_requests SET consumed_at=? WHERE id=? AND consumed_at IS NULL AND status='APPROVED'",
                                   (now, approval_id))
            if updated.rowcount != 1:
                conn.commit()
                return {"status": "BLOCKED", "reason_code": "approval_already_consumed", "trace_id": trace_id}
        elif tool.provider != "local_sqlite" or cost != 0:
            _exposure(conn, tool, "BLOCKED", "offline_policy_mismatch", trace_id, estimated=cost)
            conn.commit()
            return {"status": "BLOCKED", "reason_code": "offline_policy_mismatch", "trace_id": trace_id}
        _exposure(conn, tool, "ALLOWED", "approved_exact_action" if not tool.offline else "verified_offline_action",
                  trace_id, estimated=cost)
        if tool.handler is None:
            _exposure(conn, tool, "BLOCKED", "tool_handler_unavailable", trace_id, estimated=cost)
            conn.commit()
            return {"status": "BLOCKED", "reason_code": "tool_handler_unavailable", "trace_id": trace_id}
        conn.execute("INSERT INTO tool_invocations(idempotency_key,tool_name,permission,principal,approval_id,status,trace_id,result_json,created_at,updated_at,payload_hash) VALUES(?,?,?,?,?,'RUNNING',?,'{}',?,?,?)",
                     (key, tool_name, tool.permission, principal, approval_id, trace_id, now, now, payload_hash))
        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()

    try:
        handler_payload = {**payload, "_engine_idempotency_key": key, "_engine_trace_id": trace_id}
        result = tool.handler(handler_payload) if tool.handler else {"status": "BLOCKED", "reason_code": "tool_handler_unavailable"}
        result = redact(result)
        final_status = "DONE" if isinstance(result, Mapping) else "DONE"
    except Exception as exc:
        result = {"status": "FAILED", "reason_code": f"tool_error:{type(exc).__name__}"}
        final_status = "FAILED"
    conn = connect(path)
    try:
        conn.execute("UPDATE tool_invocations SET status=?,result_json=?,updated_at=? WHERE idempotency_key=?",
                     (final_status, _json(result), iso(), key))
        conn.commit()
    finally:
        conn.close()
    structured_log("tool.invoked", trace_id=trace_id, tool=tool_name, permission=tool.permission, status=final_status)
    return {"status": final_status, "result": result, "trace_id": trace_id}


def list_engine_audit(limit: int = 100, *, path: Optional[Path | str] = None) -> list[dict[str, Any]]:
    conn = connect(path)
    try:
        count = max(1, min(limit, 500))
        events = [{"id": row["id"], "actor": row["actor"], "action": row["action"],
                   "subject_type": row["subject_type"], "subject_id": row["subject_id"],
                   "trace_id": row["trace_id"], "details": redact(_loads(row["details_json"], {})),
                   "created_at": row["created_at"]}
                  for row in conn.execute("SELECT id,actor,action,subject_type,subject_id,trace_id,details_json,created_at FROM engine_audit_events ORDER BY id DESC LIMIT ?", (count,))]
        for row in conn.execute("SELECT id,tool_name,provider,action,status,reason_code,estimated_minor,currency,trace_id,created_at FROM cost_exposures ORDER BY created_at DESC LIMIT ?", (count,)):
            events.append({"id": f"cost:{row['id']}", "actor": "policy_engine", "action": "cost_exposure_decision",
                           "subject_type": "tool", "subject_id": row["tool_name"], "trace_id": row["trace_id"],
                           "details": {"provider": row["provider"], "tool_action": row["action"],
                                       "status": row["status"], "reason_code": row["reason_code"],
                                       "estimated_minor": row["estimated_minor"], "currency": row["currency"]},
                           "created_at": row["created_at"]})
        for row in conn.execute("SELECT idempotency_key,tool_name,permission,status,trace_id,created_at FROM tool_invocations ORDER BY created_at DESC LIMIT ?", (count,)):
            events.append({"id": f"tool:{hashlib.sha256(row['idempotency_key'].encode()).hexdigest()[:16]}",
                           "actor": "tool_registry", "action": "tool_invocation", "subject_type": "tool",
                           "subject_id": row["tool_name"], "trace_id": row["trace_id"],
                           "details": {"permission": row["permission"], "status": row["status"]},
                           "created_at": row["created_at"]})
        events.sort(key=lambda item: (item.get("created_at") or "", str(item["id"])), reverse=True)
        return events[:count]
    finally:
        conn.close()


class EngineRuntime:
    """Single local scheduler/worker loop; multiple API workers coordinate via SQLite leases."""

    def __init__(self, *, poll_seconds: float = 1.0):
        self.poll_seconds = max(0.1, min(poll_seconds, 30.0))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.worker_id = f"{os.getpid()}:{uuid.uuid4()}"

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="autoprofit-engine", daemon=True)
        self._thread.start()
        return True

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                if engine_status()["shutdown"]:
                    return
                schedule_daily_workflow()
                result = run_worker_once(self.worker_id)
                if result is None:
                    self._stop.wait(self.poll_seconds)
            except sqlite3.Error as exc:
                structured_log("engine.storage_error", reason_code=type(exc).__name__)
                self._stop.wait(min(5.0, self.poll_seconds * 2))
            except Exception as exc:
                structured_log("engine.worker_error", reason_code=type(exc).__name__)
                self._stop.wait(min(5.0, self.poll_seconds * 2))

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(max(0.1, min(timeout, 30.0)))


def runtime_enabled() -> bool:
    return os.getenv("AUTOPROFIT_ENGINE_WORKER", "false").strip().lower() in {"1", "true", "yes", "on"}


def ensure_runtime_started() -> bool:
    """Restart the opt-in local worker after an owner clears shutdown."""
    if not runtime_enabled():
        return False
    try:
        import main as backend_main
    except ImportError:
        return False
    runtime = getattr(backend_main, "_engine_runtime", None)
    if runtime and runtime._thread and runtime._thread.is_alive():
        return False
    runtime = EngineRuntime()
    backend_main._engine_runtime = runtime
    runtime.start()
    return True
