ALTER TABLE workflow_events ADD COLUMN idempotency_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_event_idempotency ON workflow_events(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS trg_workflow_events_no_update
BEFORE UPDATE ON workflow_events BEGIN
    SELECT RAISE(ABORT, 'workflow_events are immutable');
END;
CREATE TRIGGER IF NOT EXISTS trg_workflow_events_no_delete
BEFORE DELETE ON workflow_events BEGIN
    SELECT RAISE(ABORT, 'workflow_events are immutable');
END;
CREATE TRIGGER IF NOT EXISTS trg_engine_audit_no_update
BEFORE UPDATE ON engine_audit_events BEGIN
    SELECT RAISE(ABORT, 'engine_audit_events are immutable');
END;
CREATE TRIGGER IF NOT EXISTS trg_engine_audit_no_delete
BEFORE DELETE ON engine_audit_events BEGIN
    SELECT RAISE(ABORT, 'engine_audit_events are immutable');
END;
