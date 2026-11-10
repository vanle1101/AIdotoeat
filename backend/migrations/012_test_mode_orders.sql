-- Explicit test orders remain auditable but never enter production totals.
ALTER TABLE cash_orders ADD COLUMN is_test INTEGER NOT NULL DEFAULT 0 CHECK(is_test IN (0,1));
CREATE INDEX IF NOT EXISTS idx_cash_orders_test_state ON cash_orders(is_test,state,updated_at DESC);
