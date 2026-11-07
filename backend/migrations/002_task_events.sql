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
    error_details TEXT,
    trace_id TEXT,
    idempotency_key TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_engine_task_events_time ON task_events(timestamp, event_id);
CREATE INDEX IF NOT EXISTS idx_engine_task_events_task ON task_events(task_id, event_id);

CREATE TRIGGER IF NOT EXISTS trg_task_events_no_update
BEFORE UPDATE ON task_events BEGIN
    SELECT RAISE(ABORT, 'task_events are immutable');
END;
CREATE TRIGGER IF NOT EXISTS trg_task_events_no_delete
BEFORE DELETE ON task_events BEGIN
    SELECT RAISE(ABORT, 'task_events are immutable');
END;
