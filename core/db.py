"""
Local SQLite Database Engine
Zero cloud cost, zero hosting, fully persistent.
"""
import sqlite3
import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from core.config import DB_PATH
from core.redaction import redact_long_numbers_preserving_ids

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        assigned_role_id TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',  -- PENDING, RUNNING, DONE, FAILED, WAITING_OWNER
        cost_vnd REAL DEFAULT 0.0,
        input_data TEXT,
        output_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Task lifecycle events are written by the executor, never synthesized by
    # the dashboard. Columns are added idempotently for existing databases.
    task_columns = {row[1] for row in cursor.execute("PRAGMA table_info(tasks)")}
    for name, sql_type in (
        ("run_id", "TEXT"),
        ("started_at", "TEXT"),
        ("finished_at", "TEXT"),
        ("progress_pct", "INTEGER"),
        ("artifact_refs", "TEXT"),
    ):
        if name not in task_columns:
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {name} {sql_type}")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        agent_id TEXT,
        task_id TEXT NOT NULL,
        run_id TEXT,
        event_type TEXT NOT NULL,
        status TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        source TEXT NOT NULL,
        result TEXT,
        duration_ms INTEGER,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        artifact_refs_json TEXT NOT NULL DEFAULT '[]',
        error_details TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, event_id)")

    # Deliverables Table (Finished assets ready for monetization)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deliverables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        deliverable_type TEXT NOT NULL, -- SCRIPT, EXTENSION, TEMPLATE, PROPOSAL, QR_LINK
        file_path TEXT,
        content_preview TEXT,
        estimated_market_value_vnd REAL DEFAULT 0.0,
        owner_status TEXT DEFAULT 'DRAFT', -- DRAFT, APPROVED, PUBLISHED
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Revenue Ledger (Owner controlled only)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS revenue_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        amount_vnd REAL NOT NULL,
        status TEXT DEFAULT 'PENDING_OWNER_CONFIRMATION', -- PENDING, RECEIVED_BY_OWNER
        payout_destination TEXT NOT NULL, -- Owner's bank details
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def record_task_event(
    task_id: str,
    event_type: str,
    status: str,
    title: str,
    *,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    description: Optional[str] = None,
    result: Optional[str] = None,
    duration_ms: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    artifact_refs: Optional[List[str]] = None,
    error_details: Optional[str] = None,
    source: str = "core.orchestrator",
) -> int:
    """Persist an event emitted by a real task execution lifecycle."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    safe = sanitize_text
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO task_events
               (timestamp, agent_id, task_id, run_id, event_type, status, title,
                description, source, result, duration_ms, metadata_json,
                artifact_refs_json, error_details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                timestamp,
                agent_id,
                str(task_id),
                run_id,
                event_type,
                status,
                safe(title, 240),
                safe(description, 500) if description else None,
                source,
                safe(result, 1200) if result else None,
                duration_ms,
                json.dumps(_sanitize_metadata(metadata or {}), ensure_ascii=False, separators=(",", ":")),
                json.dumps([safe(item, 500) for item in artifact_refs or []], ensure_ascii=False, separators=(",", ":")),
                safe(error_details, 1200) if error_details else None,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def sanitize_text(value: Any, max_length: int = 1200) -> str:
    """Redact common credentials and direct identifiers before persisting logs."""
    text = str(value or "")
    text = re.sub(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/-]{8,}", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)\b(api[_-]?key|access[_-]?token|secret|password|authorization)\b\s*[:=]\s*[\"']?[^\s,;\"'}\]]+",
        r"\1=[REDACTED]",
        text,
    )
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    text = redact_long_numbers_preserving_ids(text)
    return text[:max_length]


def _sanitize_metadata(value: Any, depth: int = 0) -> Any:
    """Keep structured metadata while redacting secret-like keys and string values."""
    if depth > 6:
        return "[MAX_DEPTH]"
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            safe_key = sanitize_text(key, 100)
            if re.search(r"(?i)(api[_-]?key|access[_-]?token|secret|password|authorization|credential)", safe_key):
                sanitized[safe_key] = "[REDACTED]"
            else:
                sanitized[safe_key] = _sanitize_metadata(item, depth + 1)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_metadata(item, depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return sanitize_text(value, 500)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize_text(value, 500)

init_db()
