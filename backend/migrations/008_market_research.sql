-- Durable source rate-limit state for the official public research APIs.
CREATE TABLE IF NOT EXISTS market_research_fetch_state (
    source_name TEXT PRIMARY KEY,
    last_request_at TEXT,
    next_allowed_at TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
