-- Weekly optimization stores read-only metric snapshots and one owner-reviewed
-- hypothesis at a time. It contains no publishing or outreach credentials.
CREATE TABLE IF NOT EXISTS optimization_runs (
    id TEXT PRIMARY KEY,
    run_key TEXT NOT NULL UNIQUE,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    baseline_json TEXT NOT NULL,
    current_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('INSUFFICIENT_BASELINE','NO_CHANGE_PROPOSED','PROPOSAL_CREATED','STOP_RECOMMENDED')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS optimization_proposals (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES optimization_runs(id),
    status TEXT NOT NULL CHECK(status IN ('AWAITING_APPROVAL','APPROVED_FOR_MANUAL_CHANGE','ACTIVE_MANUAL','STOP_RECOMMENDED','STOPPED','REJECTED','COMPLETED')),
    active_slot INTEGER,
    target_stage TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    proposed_change TEXT NOT NULL,
    stop_criteria TEXT NOT NULL,
    baseline_json TEXT NOT NULL,
    owner_decision TEXT,
    owner_decided_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_optimization_single_active
ON optimization_proposals(active_slot) WHERE active_slot=1;
CREATE INDEX IF NOT EXISTS idx_optimization_proposals_status ON optimization_proposals(status,created_at DESC);
