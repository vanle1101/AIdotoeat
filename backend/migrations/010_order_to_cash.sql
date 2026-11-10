-- Phase 07: append-only order-to-cash ledger. This is additive; legacy
-- workflow_records/payment_reports/transactions stay available as history.
CREATE TABLE IF NOT EXISTS cash_orders (
    id TEXT PRIMARY KEY,
    order_number TEXT UNIQUE,
    state TEXT NOT NULL CHECK(state IN (
        'LEAD','QUOTE_DRAFT','QUOTE_APPROVED','ORDER_PLACED','AWAITING_PAYMENT',
        'CLAIM_SUBMITTED','PAYMENT_EVIDENCE_REVIEW','VERIFIED','FULFILLED',
        'CLOSED','REFUNDED','DISPUTED','CANCELLED'
    )),
    product_slug TEXT,
    product_name TEXT,
    customer_name TEXT,
    customer_email TEXT NOT NULL,
    contact_consent INTEGER NOT NULL CHECK(contact_consent IN (0,1)),
    estimate_minor INTEGER,
    estimate_currency TEXT,
    proposal_minor INTEGER,
    proposal_currency TEXT,
    invoice_minor INTEGER,
    invoice_currency TEXT,
    paid_minor INTEGER NOT NULL DEFAULT 0 CHECK(paid_minor >= 0),
    refunded_minor INTEGER NOT NULL DEFAULT 0 CHECK(refunded_minor >= 0),
    charged_back_minor INTEGER NOT NULL DEFAULT 0 CHECK(charged_back_minor >= 0),
    buyer_nonce TEXT NOT NULL,
    buyer_token_expires_at TEXT NOT NULL,
    current_quote_id TEXT,
    cancel_reason TEXT,
    trace_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    idempotency_hash TEXT NOT NULL,
    acceptance_key TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cash_quotes (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES cash_orders(id),
    version INTEGER NOT NULL CHECK(version > 0),
    scope TEXT NOT NULL,
    proposal_minor INTEGER NOT NULL CHECK(proposal_minor > 0),
    currency TEXT NOT NULL CHECK(currency='VND'),
    status TEXT NOT NULL CHECK(status IN ('DRAFT','APPROVED','ACCEPTED','EXPIRED','SUPERSEDED')),
    expires_at TEXT NOT NULL,
    approved_by TEXT,
    approved_at TEXT,
    accepted_at TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(order_id, version)
);

CREATE TABLE IF NOT EXISTS cash_claims (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES cash_orders(id),
    claimed_minor INTEGER NOT NULL CHECK(claimed_minor > 0),
    currency TEXT NOT NULL CHECK(currency='VND'),
    submitted_reference TEXT,
    buyer_note TEXT,
    status TEXT NOT NULL CHECK(status IN ('CLAIM_SUBMITTED','IN_REVIEW','REJECTED','VERIFIED')),
    payload_hash TEXT NOT NULL,
    rejection_reason TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cash_transactions (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES cash_orders(id),
    claim_id TEXT NOT NULL REFERENCES cash_claims(id),
    amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
    currency TEXT NOT NULL CHECK(currency='VND'),
    payment_method TEXT NOT NULL CHECK(payment_method='BANK_TRANSFER'),
    reference_scope TEXT NOT NULL,
    reference_normalized TEXT NOT NULL,
    assurance_level TEXT NOT NULL CHECK(assurance_level IN ('OWNER_MANUAL_ATTESTATION','INDEPENDENT_STATEMENT_IMPORT')),
    provenance TEXT NOT NULL,
    verified_by TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(payment_method, reference_scope, reference_normalized)
);

CREATE TABLE IF NOT EXISTS cash_adjustments (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES cash_orders(id),
    adjustment_type TEXT NOT NULL CHECK(adjustment_type IN ('REFUND','CHARGEBACK','CHARGEBACK_REVERSAL')),
    amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
    currency TEXT NOT NULL CHECK(currency='VND'),
    reference_scope TEXT NOT NULL,
    reference_normalized TEXT NOT NULL,
    assurance_level TEXT NOT NULL CHECK(assurance_level='OWNER_MANUAL_ATTESTATION'),
    provenance TEXT NOT NULL,
    reason TEXT NOT NULL,
    reverses_adjustment_id TEXT UNIQUE REFERENCES cash_adjustments(id),
    verified_by TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(adjustment_type, reference_scope, reference_normalized)
);

CREATE TABLE IF NOT EXISTS cash_deliveries (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL UNIQUE REFERENCES cash_orders(id),
    product_slug TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE','REVOKED','EXPIRED')),
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    download_count INTEGER NOT NULL DEFAULT 0 CHECK(download_count >= 0),
    idempotency_key TEXT NOT NULL UNIQUE,
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cash_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES cash_orders(id),
    from_state TEXT,
    to_state TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    assurance_level TEXT,
    provenance TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT NOT NULL UNIQUE,
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cash_orders_state_time ON cash_orders(state, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_cash_orders_customer ON cash_orders(customer_email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cash_claims_order_time ON cash_claims(order_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cash_transactions_order_time ON cash_transactions(order_id, verified_at);
CREATE INDEX IF NOT EXISTS idx_cash_adjustments_order_time ON cash_adjustments(order_id, occurred_at);

CREATE TRIGGER IF NOT EXISTS trg_cash_order_state_valid
BEFORE UPDATE OF state ON cash_orders
WHEN NEW.state != OLD.state AND NOT (
    (OLD.state='LEAD' AND NEW.state IN ('QUOTE_DRAFT','CANCELLED')) OR
    (OLD.state='QUOTE_DRAFT' AND NEW.state IN ('QUOTE_APPROVED','CANCELLED')) OR
    (OLD.state='QUOTE_APPROVED' AND NEW.state IN ('QUOTE_DRAFT','ORDER_PLACED','CANCELLED')) OR
    (OLD.state='ORDER_PLACED' AND NEW.state IN ('AWAITING_PAYMENT','CANCELLED')) OR
    (OLD.state='AWAITING_PAYMENT' AND NEW.state IN ('CLAIM_SUBMITTED','CANCELLED')) OR
    (OLD.state='CLAIM_SUBMITTED' AND NEW.state IN ('PAYMENT_EVIDENCE_REVIEW','AWAITING_PAYMENT','CANCELLED')) OR
    (OLD.state='PAYMENT_EVIDENCE_REVIEW' AND NEW.state IN ('VERIFIED','AWAITING_PAYMENT','CANCELLED')) OR
    (OLD.state='VERIFIED' AND NEW.state IN ('FULFILLED','CLOSED','REFUNDED','DISPUTED')) OR
    (OLD.state='FULFILLED' AND NEW.state IN ('CLOSED','REFUNDED','DISPUTED')) OR
    (OLD.state='REFUNDED' AND NEW.state IN ('CLOSED','DISPUTED')) OR
    (OLD.state='DISPUTED' AND NEW.state IN ('VERIFIED','REFUNDED','CLOSED'))
)
BEGIN
    SELECT RAISE(ABORT, 'invalid cash order state transition');
END;

CREATE TRIGGER IF NOT EXISTS trg_cash_events_no_update
BEFORE UPDATE ON cash_events BEGIN SELECT RAISE(ABORT, 'cash_events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS trg_cash_events_no_delete
BEFORE DELETE ON cash_events BEGIN SELECT RAISE(ABORT, 'cash_events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS trg_cash_transactions_no_update
BEFORE UPDATE ON cash_transactions BEGIN SELECT RAISE(ABORT, 'cash_transactions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS trg_cash_transactions_no_delete
BEFORE DELETE ON cash_transactions BEGIN SELECT RAISE(ABORT, 'cash_transactions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS trg_cash_adjustments_no_update
BEFORE UPDATE ON cash_adjustments BEGIN SELECT RAISE(ABORT, 'cash_adjustments are immutable'); END;
CREATE TRIGGER IF NOT EXISTS trg_cash_adjustments_no_delete
BEFORE DELETE ON cash_adjustments BEGIN SELECT RAISE(ABORT, 'cash_adjustments are immutable'); END;
