-- Additive domain tables for the canonical backend/data/company.db ledger.
-- Existing leads/products/payment_reports/transactions/workflow_records stay
-- authoritative; compatibility views are installed by migration 002.
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT,
    evidence_type TEXT NOT NULL,
    source_uri TEXT,
    content_hash TEXT,
    summary TEXT NOT NULL DEFAULT '',
    verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT,
    name TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    email TEXT,
    display_name TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    uri TEXT,
    content_hash TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    workflow TEXT NOT NULL,
    status TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    trace_id TEXT NOT NULL,
    scheduled_for TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_requests (
    id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    permission TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','APPROVED','REJECTED','EXPIRED','REVOKED')),
    idempotency_key TEXT NOT NULL UNIQUE,
    trace_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    decision_by TEXT,
    decision_reason TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    consumed_at TEXT
);

CREATE TABLE IF NOT EXISTS tool_invocations (
    idempotency_key TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    permission TEXT NOT NULL,
    principal TEXT NOT NULL,
    approval_id TEXT,
    status TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cost_exposures (
    id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    action TEXT NOT NULL,
    estimated_minor INTEGER,
    currency TEXT NOT NULL DEFAULT 'VND',
    status TEXT NOT NULL CHECK(status IN ('ALLOWED','BLOCKED','APPROVAL_REQUIRED','DRY_RUN')),
    reason_code TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Keep the compatible core task columns for legacy dashboard projections.
-- Migration 002 adds the engine's state, lease, retry, and idempotency fields.
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    assigned_role_id TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    cost_vnd REAL DEFAULT 0.0,
    input_data TEXT,
    output_data TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    run_id TEXT,
    started_at TEXT,
    finished_at TEXT,
    progress_pct INTEGER,
    artifact_refs TEXT
);

CREATE TABLE IF NOT EXISTS deliveries (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    asset_id TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    delivered_at TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engine_audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    subject_type TEXT,
    subject_id TEXT,
    trace_id TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engine_control (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_schedules (
    schedule_id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
    last_run_date TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_dead_letters (
    task_id INTEGER PRIMARY KEY,
    reason TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    moved_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS tool_grants (
    principal TEXT NOT NULL,
    permission TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    granted_at TEXT NOT NULL,
    revoked_at TEXT,
    PRIMARY KEY(principal, permission)
);

CREATE TABLE IF NOT EXISTS legacy_imports (
    source_db TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_pk TEXT NOT NULL,
    target_id TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    PRIMARY KEY(source_db, source_table, source_pk)
);

CREATE INDEX IF NOT EXISTS idx_evidence_opportunity ON evidence(opportunity_id, created_at);
CREATE INDEX IF NOT EXISTS idx_experiments_opportunity ON experiments(opportunity_id, created_at);
CREATE INDEX IF NOT EXISTS idx_approval_status_expiry ON approval_requests(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_agent_runs_time ON agent_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_engine_audit_time ON engine_audit_events(id DESC);
CREATE INDEX IF NOT EXISTS idx_deliveries_order ON deliveries(order_id, created_at);
