-- LLM provenance and bounded response cache. Prompt bodies and credentials are
-- intentionally not persisted; cache entries contain only validated outputs.
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_kind TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PENDING','SUCCESS','FAILURE','CACHE_HIT','DEGRADED')),
    failure_code TEXT,
    confidence_estimate REAL,
    confidence_label TEXT NOT NULL DEFAULT 'unavailable',
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_usage_provider_day ON llm_usage(provider, created_at);

CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key TEXT PRIMARY KEY,
    task_kind TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    output_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_llm_cache_expiry ON llm_cache(expires_at);
