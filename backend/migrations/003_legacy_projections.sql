-- Read projections keep the previous dashboard/API records available while
-- exposing domain-typed names. Writes continue through their existing owner.
CREATE VIEW IF NOT EXISTS opportunities AS
    SELECT id, kind, status, payload_json, created_at, updated_at
    FROM workflow_records WHERE kind='opportunity';

CREATE VIEW IF NOT EXISTS offers AS
    SELECT id, kind, status, payload_json, created_at, updated_at
    FROM workflow_records WHERE kind='pricing_quote';

CREATE VIEW IF NOT EXISTS orders AS
    SELECT id, status, payload_json, created_at, updated_at
    FROM workflow_records WHERE kind='order';

CREATE VIEW IF NOT EXISTS payment_claims AS
    SELECT id, product_slug, product_name, amount_usd, amount_vnd,
           payment_method, customer_email, reference, status, created_at,
           verified_by, verified_at
    FROM payment_reports;

CREATE VIEW IF NOT EXISTS verified_transactions AS
    SELECT id, tx_hash, source, amount_usd, amount_vnd, payment_method, status, created_at
    FROM transactions WHERE status='PAID_VERIFIED';

CREATE VIEW IF NOT EXISTS analytics_events AS
    SELECT p.id, p.session_id, 'pageview' AS event_type, p.path AS event_name,
           p.occurred_at, 0 AS internal_test, 'first_party_telemetry' AS source
    FROM telemetry_pageviews p
    JOIN telemetry_sessions s ON s.session_id=p.session_id;

CREATE TRIGGER IF NOT EXISTS trg_tasks_valid_state_insert
BEFORE INSERT ON tasks
WHEN NEW.state NOT IN ('CREATED','QUEUED','RUNNING','WAITING_APPROVAL','RETRY_PENDING','BLOCKED','DONE','FAILED','CANCELLED')
BEGIN
    SELECT RAISE(ABORT, 'invalid task state');
END;

CREATE TRIGGER IF NOT EXISTS trg_tasks_valid_state_transition
BEFORE UPDATE OF state ON tasks
WHEN NEW.state != OLD.state AND NOT (
    (OLD.state='CREATED' AND NEW.state IN ('QUEUED','BLOCKED','CANCELLED')) OR
    (OLD.state='QUEUED' AND NEW.state IN ('RUNNING','BLOCKED','CANCELLED')) OR
    (OLD.state='RUNNING' AND NEW.state IN ('WAITING_APPROVAL','RETRY_PENDING','BLOCKED','DONE','FAILED','CANCELLED')) OR
    (OLD.state='WAITING_APPROVAL' AND NEW.state IN ('QUEUED','BLOCKED','CANCELLED')) OR
    (OLD.state='RETRY_PENDING' AND NEW.state IN ('QUEUED','BLOCKED','FAILED','CANCELLED')) OR
    (OLD.state='BLOCKED' AND NEW.state IN ('QUEUED','CANCELLED'))
)
BEGIN
    SELECT RAISE(ABORT, 'invalid task state transition');
END;
