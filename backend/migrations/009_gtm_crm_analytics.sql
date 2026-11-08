-- Add first-party go-to-market events and explicit CRM contact controls.
-- Existing leads remain the canonical CRM table; old rows default to unknown consent.

CREATE TABLE IF NOT EXISTS gtm_analytics_events (
    event_id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL CHECK(event_name IN (
        'landing_view','demo_start','contact_submit','qualified_inquiry',
        'proposal_sent','customer_reply','accepted_quote','verified_payment'
    )),
    campaign_id TEXT NOT NULL,
    session_id TEXT,
    page_path TEXT NOT NULL,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_content TEXT,
    lead_id INTEGER,
    transaction_id INTEGER,
    source TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    internal_test INTEGER NOT NULL DEFAULT 0 CHECK(internal_test IN (0,1)),
    dedupe_key TEXT UNIQUE,
    FOREIGN KEY(lead_id) REFERENCES leads(id),
    FOREIGN KEY(transaction_id) REFERENCES transactions(id)
);

CREATE INDEX IF NOT EXISTS idx_gtm_events_campaign_time
    ON gtm_analytics_events(campaign_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_gtm_events_name_time
    ON gtm_analytics_events(event_name, occurred_at DESC);

CREATE TABLE IF NOT EXISTS gtm_publication_queue (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    draft_key TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    draft_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING_REVIEW'
        CHECK(status IN ('PENDING_REVIEW','APPROVED_FOR_MANUAL_POST','REJECTED','BLOCKED')),
    policy_url TEXT NOT NULL,
    policy_checked_date TEXT NOT NULL,
    human_rewritten INTEGER NOT NULL DEFAULT 0 CHECK(human_rewritten IN (0,1)),
    community_rules_rechecked INTEGER NOT NULL DEFAULT 0 CHECK(community_rules_rechecked IN (0,1)),
    owner_requested_at TEXT NOT NULL,
    owner_decided_at TEXT,
    owner_decision_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(campaign_id,channel,draft_hash)
);
