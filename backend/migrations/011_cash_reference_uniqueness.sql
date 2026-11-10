-- A single bank statement reference must not be credited or adjusted twice,
-- including across inbound receipts and outgoing refunds/chargebacks.
DROP TRIGGER IF EXISTS trg_cash_order_state_valid;
CREATE TRIGGER trg_cash_order_state_valid
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
    (OLD.state='DISPUTED' AND NEW.state IN ('VERIFIED','REFUNDED','CLOSED','FULFILLED')) OR
    (OLD.state='CLOSED' AND NEW.state IN ('REFUNDED','DISPUTED'))
)
BEGIN
    SELECT RAISE(ABORT, 'invalid cash order state transition');
END;

CREATE TRIGGER IF NOT EXISTS trg_cash_transaction_reference_unique_across_ledger
BEFORE INSERT ON cash_transactions
WHEN EXISTS (
    SELECT 1 FROM cash_adjustments
    WHERE reference_scope=NEW.reference_scope
      AND reference_normalized=NEW.reference_normalized
)
BEGIN
    SELECT RAISE(ABORT, 'bank reference already exists in cash adjustment ledger');
END;

CREATE TRIGGER IF NOT EXISTS trg_cash_adjustment_reference_unique_across_ledger
BEFORE INSERT ON cash_adjustments
WHEN EXISTS (
    SELECT 1 FROM cash_transactions
    WHERE reference_scope=NEW.reference_scope
      AND reference_normalized=NEW.reference_normalized
) OR EXISTS (
    SELECT 1 FROM cash_adjustments
    WHERE reference_scope=NEW.reference_scope
      AND reference_normalized=NEW.reference_normalized
)
BEGIN
    SELECT RAISE(ABORT, 'bank reference already exists in cash ledger');
END;
