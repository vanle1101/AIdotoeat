-- Source-cited local agent artifacts and memory with explicit TTL/deletion.
CREATE TABLE IF NOT EXISTS agent_artifacts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    task_id INTEGER NOT NULL,
    role_id TEXT NOT NULL,
    title TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    source_ids_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','REVIEWED','REJECTED','DELETED')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_artifacts_run ON agent_artifacts(run_id, task_id);

CREATE TABLE IF NOT EXISTS agent_memory (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    namespace TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    fact TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_memory_ttl ON agent_memory(namespace, expires_at, deleted_at);
