# Phase 07 — Order-to-cash

## Scope and assurance

The order ledger is additive in the canonical backend SQLite database. Migrations 010 and 011 add the order workflow and cross-ledger bank-reference uniqueness. Existing `payment_reports`, `transactions`, and workflow records remain historical data; they are not imported as verified cash and cannot authorize new downloads.

There is no bank API or payment-provider integration. The only configured payment route is a direct bank transfer, which adds no mandatory provider fee. A submitted screenshot, QR, buyer-entered reference, or browser POST is only a claim. A receipt enters `cash_transactions` only after an owner confirms that the corresponding funds appear in the receiving account. Its assurance and provenance are recorded as `OWNER_MANUAL_ATTESTATION` and `owner_checked_account_statement_and_attested_receipt`. No independent statement import is implemented.

## Lifecycle

`LEAD → QUOTE_DRAFT → QUOTE_APPROVED → ORDER_PLACED → AWAITING_PAYMENT → CLAIM_SUBMITTED → PAYMENT_EVIDENCE_REVIEW → VERIFIED → FULFILLED → CLOSED`

An owner may cancel an unpaid order. A verified, fulfilled, refunded, or closed order may be partially refunded or disputed when funds remain; those adjustments are append-only and require their own manual attestation. A successful dispute resolution records a reversal entry and restores the prior order state. A lost dispute closes the order with the chargeback retained. Refunding or opening a chargeback revokes active delivery access; a won dispute reactivates access only when the prior state was fulfilled and the original link has not expired. Closing ends current work, while later bank adjustments can reopen the order into refund or dispute handling.

Financial amounts remain separate:

- `estimated_value`: catalog estimate in USD, explicitly not a quote and never converted for reporting.
- `proposal_amount`: owner-authored VND quote, not revenue.
- `invoice_total` and `pending_invoice`: issued VND invoice and its remaining balance.
- `latest_claim`: buyer-reported amount and reference, not proof.
- `owner_confirmed_receipts`: manually attested VND receipts.
- `settled_balance`: verified receipts less refunds and chargebacks, with reversals added back.

Reference uniqueness is scoped to a hash of the receiving bank and account. Migration 011 also blocks reuse between receipt and adjustment tables. Receipt and adjustment rows and order events have update/delete protection in SQLite. Idempotent replays must match the original payload.

## Buyer access and paid files

Create an order at `/checkout.html`. A random buyer bearer token is held in that tab's `sessionStorage`, and buyer endpoints do not return customer PII beyond the buyer's own order. The owner sees customer details only on authenticated cash-admin routes. Bank details appear only on an authorized buyer's payment-instructions request and only after bank configuration is complete.

Paid archives are staged outside the public frontend. Fulfillment requires a matching QA-passed manifest, package hash, and a fully verified order. The server issues one delivery authorization per order; downloads require the buyer token and expire after seven days. A refund, chargeback, expiry, or revoke blocks further downloads. Legacy download and verification routes return HTTP 410. Static `/apps/*.html` remain free demos, not paid archives.

## Owner configuration

Set these values in the process environment before enabling checkout:

- `AUTOPROFIT_BANK_NAME`
- `AUTOPROFIT_BANK_ACCOUNT_NO`
- `AUTOPROFIT_BANK_ACCOUNT_NAME`
- `AUTOPROFIT_ORDER_TOKEN_SECRET` — at least 32 random bytes, used to sign buyer access tokens
- `AUTOPROFIT_ADMIN_API_KEY` — the existing owner/admin credential used by cash-admin routes

The repository's `.env.example` contains blank placeholders only. For local development, use a private `.env` excluded from Git. For systemd, use an owner-controlled `EnvironmentFile` readable only by the service account (for example mode `0600` where appropriate). Never put these values in frontend files, a public API response, shell history, or a checked-in config. Restart the backend after changing them. Checkout remains unavailable if the bank or token secret is missing.

## Owner endpoints

All `/api/cash/admin/*` routes require the existing admin key over HTTPS.

- `GET /api/cash/admin/orders` and `/claims`: review orders and buyer reports.
- `POST /api/cash/admin/leads/{order_id}/quotes`, then `POST /api/cash/admin/quotes/{quote_id}/approve`.
- `POST /api/cash/admin/claims/{claim_id}/verify`: confirm actual account receipt, exact VND amount, and statement reference. Use a fresh `Idempotency-Key` for each distinct receipt.
- `POST /api/cash/admin/claims/{claim_id}/reject`: reject an unsupported claim.
- `POST /api/cash/admin/orders/{order_id}/fulfill`: authorize a staged artifact after QA and payment verification.
- `POST /api/cash/admin/orders/{order_id}/refund`, `/chargeback`, `/dispute/resolve`, `/cancel`, and `/close` for the named lifecycle action.
- `GET /api/cash/admin/orders/{order_id}/transactions` and `/events`: inspect immutable receipt/adjustment provenance and the event history.
- `GET /api/cash/admin/summary`: settled balances by currency, labeled as manual owner attestation. No FX conversion is performed.

## Migration, backup, and restore

Migrations are additive and recorded in `schema_migrations`; they do not replace either legacy database. Migration 011 only adds SQLite triggers enforcing transfer-reference uniqueness across both cash ledgers. Production migration/deployment was not run for this change.

Before a future deployment, stop or quiesce writes and take an SQLite online backup of `backend/data/company.db` with Python's `sqlite3.Connection.backup()` (or the SQLite backup API); do not copy only the main file while WAL writes are active. Keep the backup outside the public web root with restricted permissions. Record the deployed code revision and protect the environment file separately. Start the new version, confirm migrations 10 and 11 and health, then exercise a small owner-controlled staging order. For rollback, stop the new service, restore the pre-migration database backup and prior code revision together, then start the old service. Never restore an old database over live writes without first stopping the service and preserving the newer database for reconciliation.

The E2E test creates and removes temporary SQLite databases and uses SQLite's online backup API to restore a copy. It does not back up or modify a production database.

## Staging verification

Run from the repository root:

```powershell
python -B -m unittest tests.test_phase07_order_cash -v
```

The staging suite covers lead consent and idempotency, quote approval, unauthorized buyer/admin/download access, failed and mismatched verification, manual receipt provenance, partial payments, duplicate transfer references, once-only fulfillment, expiring/revoked delivery, refund, chargeback reversal, and database backup/restore. It uses a test bank config and a QA fixture artifact in temporary directories; it makes no real transfer, public post, or production write.

## Limitations

- A manual receipt is an owner attestation, not bank-originated verification. The operator must inspect the receiving-account statement before confirming.
- Admin authorization uses the existing shared owner key; the ledger records the owner actor, not a distinct human identity or MFA assertion.
- Buyer access tokens expire after one year. Delivery links expire after seven days and are bound to the buyer token.
- Product catalog amounts in USD are estimates only. No fixed-rate conversion is used for cash reporting.
- A successful dispute reversal is a manual ledger attestation. Reconcile it against the bank's final dispute result before selecting `WON`.
- This branch has not been deployed to production.
