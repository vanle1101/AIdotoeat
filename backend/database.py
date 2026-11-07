"""
AUTOProfit AI SQLite Database Manager (WAL Mode)
High-concurrency, zero-lock, persistent storage.
"""
import sqlite3
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from config import DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # System State & KPIs
    c.execute("""
    CREATE TABLE IF NOT EXISTS system_state (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tasks
    c.execute("""
    CREATE TABLE IF NOT EXISTS live_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT UNIQUE,
        title TEXT,
        role TEXT,
        category TEXT,
        status TEXT,
        progress_pct INTEGER DEFAULT 0,
        result_preview TEXT,
        cost_usd REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Leads & Outreach
    c.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        company TEXT,
        source TEXT,
        need TEXT,
        stage TEXT,
        fit_score INTEGER,
        proposal_text TEXT,
        country TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Products & Apps
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE,
        name TEXT,
        category TEXT,
        price_usd REAL,
        description TEXT,
        demo_url TEXT,
        download_count INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1
    )
    """)

    # Transactions & Payments
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tx_hash TEXT,
        source TEXT,
        amount_usd REAL,
        amount_vnd REAL,
        payment_method TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Public checkout reports stay separate from verified transactions.
    c.execute("""
    CREATE TABLE IF NOT EXISTS payment_reports (
        id TEXT PRIMARY KEY,
        product_slug TEXT NOT NULL,
        product_name TEXT NOT NULL,
        amount_usd REAL NOT NULL,
        amount_vnd INTEGER NOT NULL,
        payment_method TEXT NOT NULL CHECK(payment_method IN ('BANK_TRANSFER', 'BINANCE_PAY')),
        customer_email TEXT,
        reference TEXT,
        status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
        created_at TEXT NOT NULL
    )
    """)
    payment_report_columns = {row[1] for row in c.execute("PRAGMA table_info(payment_reports)").fetchall()}
    if "customer_email" not in payment_report_columns:
        c.execute("ALTER TABLE payment_reports ADD COLUMN customer_email TEXT")
    if "verified_by" not in payment_report_columns:
        c.execute("ALTER TABLE payment_reports ADD COLUMN verified_by TEXT")
    if "verified_at" not in payment_report_columns:
        c.execute("ALTER TABLE payment_reports ADD COLUMN verified_at TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payment_reports_status_time ON payment_reports(status, created_at)")

    # First-party analytics. Session IDs are random browser identifiers; no IP,
    # email, user-agent string, or query string is retained.
    c.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_sessions (
        session_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_pageviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        path TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        FOREIGN KEY(session_id) REFERENCES telemetry_sessions(session_id)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_pageviews_time ON telemetry_pageviews(occurred_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_pageviews_session ON telemetry_pageviews(session_id, occurred_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_sessions_seen ON telemetry_sessions(last_seen_at)")

    # Durable workflow records for dashboard operations that need review or
    # configuration. Pending records are kept separate from verified revenue.
    c.execute("""
    CREATE TABLE IF NOT EXISTS workflow_records (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        status TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_workflow_records_kind_time ON workflow_records(kind, created_at DESC)")
    c.execute("""
    CREATE TABLE IF NOT EXISTS workflow_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        record_kind TEXT,
        record_id TEXT,
        actor TEXT NOT NULL DEFAULT 'system',
        details_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_time ON workflow_events(created_at DESC)")

    # Shared fixed-window rate limits prevent two Uvicorn workers from each
    # granting a separate allowance. The table contains hashes, never raw IPs.
    c.execute("""
    CREATE TABLE IF NOT EXISTS request_rate_limits (
        bucket_id TEXT PRIMARY KEY,
        scope_hash TEXT NOT NULL,
        window_start INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        hits INTEGER NOT NULL
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_request_rate_limits_expiry ON request_rate_limits(expires_at)")

    c.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    c.execute(
        "INSERT OR IGNORE INTO dashboard_meta(key, value) VALUES('analytics_started_at', ?)",
        (datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),)
    )

    conn.commit()
    conn.close()


def consume_rate_limit(scope: str, limit: int, window_seconds: int) -> bool:
    """Atomically reserve one request slot in a shared SQLite time bucket."""
    if limit < 1 or window_seconds < 1:
        raise ValueError("Rate limit and window must be positive")
    now = int(time.time())
    window_start = (now // window_seconds) * window_seconds
    scope_hash = hashlib.sha256(scope.encode("utf-8", errors="replace")).hexdigest()
    bucket_id = hashlib.sha256(f"{scope_hash}:{window_seconds}:{window_start}".encode()).hexdigest()
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM request_rate_limits WHERE expires_at < ?", (now,))
        row = conn.execute("SELECT hits FROM request_rate_limits WHERE bucket_id=?", (bucket_id,)).fetchone()
        if row and int(row["hits"]) >= limit:
            conn.rollback()
            return False
        conn.execute(
            "INSERT INTO request_rate_limits(bucket_id, scope_hash, window_start, expires_at, hits) "
            "VALUES(?, ?, ?, ?, 1) ON CONFLICT(bucket_id) DO UPDATE SET hits=hits+1",
            (bucket_id, scope_hash, window_start, window_start + window_seconds,)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
