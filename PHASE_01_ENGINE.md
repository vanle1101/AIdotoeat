# AUTOProfit Phase 01 — Durable Business Engine

## Decision and data ownership

The canonical ledger for new Phase 01 work is `backend/data/company.db` (`backend/config.py:15-22`). It already owns checkout claims (`payment_reports`), verified receipts (`transactions`), catalog (`products`), leads (`leads`), persisted dashboard workflows (`workflow_records`, `workflow_events`), telemetry, settings and shared request limits (`backend/database.py:22-195`). New domain tables and engine tasks are added transactionally through `backend/migrations/001_legacy_ledger.sql` to `005_workflow_event_idempotency.sql` and recorded in `schema_migrations`. Phase 02 adds LLM usage/cache tables in migration 006; Phase 03 adds source-cited agent artifacts and expiring memory in migration 007.

`data/company.db` remains the untouched legacy source for the core orchestrator (`core/config.py:8-14`, `core/db.py:16-100`). It owns its legacy tasks, task events, deliverables and owner payout ledger. Dashboard adapters continue to read those legacy rows as read-only and tag task/event sources; new engine tasks/events use the canonical DB. `revenue_ledger` remains in the legacy source because it has no verified transaction provenance and contains a payout destination. It is not converted into revenue or copied into the canonical business ledger. Existing payment claims are read through `payment_claims`; only `transactions` with `PAID_VERIFIED` status appear in `verified_transactions`. Existing orders, opportunities and locked pricing quotes remain the `workflow_records` owner and are exposed through `orders`, `opportunities` and `offers` read projections.

Read-only inventory at the start of Phase 01 found 12 legacy core tasks and 3 deliverables, with no core task events or revenue rows. The backend DB contained one dashboard metadata row; leads, products, transactions, payment reports, workflow records/events, live task cache and telemetry tables were otherwise empty. No customer or payment field values were read into the report.

No database file was copied, reset, deleted, migrated or deployed as part of this change. Schema tests, migration import, rollback and end-to-end runs use temporary SQLite files. The import utility refuses to run without an already-existing backup directory, snapshots both source and target using SQLite's backup API, leaves source files intact, requires a new path for restore, and imports only once by source/table/row key. Legacy running/pending tasks are imported as `BLOCKED`; they are never resumed automatically.

## Inventory and findings

| Severity | Finding / evidence | Phase 01 action |
|---|---|---|
| High | Two competing database owners: `core/db.py:12`, `backend/database.py:15`, `backend/dashboard_data.py:14`. | Canonicalize new ledger writes in backend DB; preserve read-only source and provide explicit backed-up importer. |
| High | Legacy `task_events` is append-like but has no immutable trigger, state version, lease or idempotency (`core/db.py:46-66`). | Add typed task state, guarded transitions, unique keys, lease/retry fields, immutable events and migration versions. |
| High | `workflow_api.py:190-258, 929-1166` mutates payment, order and delivery records outside a unified task engine. | Add one-time idempotency for order create, preserve atomic payment record checks, expose verified payment projections and keep delivery approval-gated. |
| High | `backend/workflow_api.py:703-730` performs one bounded read from a fixed public Hacker News API; public form routes accept user data. | New engine logging redacts content and workflows do not auto-contact, publish, spend or fulfill. Existing endpoint policy remains admin-authenticated where mutation is sensitive and rate/origin limited in `main.py:111-181`. |
| Medium | `backend/main.py:140-182` applies Origin checks and shared rate limits; admin authentication requires high entropy key and HTTPS (`main.py:111-119`). | Keep those protections and require them for every engine route. New API request models reject unknown fields. |
| Medium | Existing dashboard business views are split between `backend/dashboard_data.py:47-58, 183-272` and the core event DB. | Adapt task and activity reads with source labels and a reserved event ID range; legacy source stays read-only. |
| Medium | Payment and product concepts are persisted in JSON workflow records plus legacy tables (`backend/workflow_api.py:86-144`, `backend/database.py:44-112`). | Reuse compatible `products`, `leads`, `transactions`, `payment_reports`, and `workflow_records`; provide typed projections for orders, payment claims, verified transactions and analytics. |
| Medium | `core/orchestrator.py:24-97` is a synchronous CLI workflow, not a recoverable worker. | Add opt-in local Python scheduler and SQLite worker leases. No paid cloud graph/runtime is required. |

### Runtime and configuration inventory

- Entrypoints: `run.py` is the interactive owner CLI; `backend/main.py` provides FastAPI `app` on the internal loopback port; `core/orchestrator.py` runs legacy CLI production tasks.
- Dependencies are pinned in `requirements.txt`: FastAPI, Uvicorn, Segno, python-dotenv, HTTPX and Rich. SQLite is from Python's standard library. LangGraph/LangSmith are not required.
- Financial/provider values remain environment-backed in `backend/config.py`; `.env.example` uses blank placeholders. `AUTOPROFIT_DATA_DIR` and `AUTOPROFIT_APPS_DIR` select backend paths. `AUTOPROFIT_ADMIN_API_KEY` protects admin API routes. `AUTOPROFIT_ENGINE_WORKER` opts into the Python scheduler; `AUTOPROFIT_ENGINE_KILL_SWITCH` defaults on.
- Monetization paths include catalog/downloads, public payment claims, manually verified bank proofs, BSC receipt checks, ad inquiries and donation claims in `backend/workflow_api.py` and `backend/main.py`. Only owner-verified transaction rows are verified revenue. Ad placements/first-party analytics are not automated engagement paths.
- Other background work: `backend/traffic_worker.py` is retired by Phase 00. Phase 01's engine thread is opt-in, bounded to this process, stops on app shutdown, and coordinates leases through SQLite. There is no separate external scheduler dependency.

### API surface

Existing APIs remain in `backend/main.py` and `backend/workflow_api.py`: public health, first-party telemetry, payment claims, public notebook/forms, app/catalog download, owner dashboard, payment/order review, finance/settings, employees, opportunities, pricing, system controls and task APIs. Sensitive owner reads/mutations require HTTPS plus `X-Admin-Key`; existing public submissions remain rate limited and same-origin protected. Existing webhook/provider callbacks are not trusted as verified payment without the owner/bounded BSC receipt checks.

The new admin-only engine API in `backend/business_api.py` provides:

- `GET /api/engine/status`, `/runs`, `/runs/{id}`, `/tasks`, `/queue`, `/events` (SSE), `/audit`, `/tools`, `/approvals`.
- `POST /api/engine/runs` (manual/idempotent trigger), run `pause`, `resume`, `cancel` routes.
- `POST /api/engine/control/pause|resume|shutdown|kill-switch`.
- Tool approval request/decision, exact grant/revoke, and invocation routes under `/api/engine/tools`, `/api/engine/approvals`, and `/api/engine/grants`.

Admin routes inherit `_require_admin`: minimum 32-character configured key, HTTPS only and constant-time key comparison. The app's Origin middleware applies to mutating API requests. SSE checks the same admin auth. No broad CORS policy was added.

## Engine behavior

Task states are `CREATED → QUEUED → RUNNING → WAITING_APPROVAL / RETRY_PENDING / BLOCKED / DONE / FAILED / CANCELLED`; allowed edges are declared in `backend/business_engine.py`. State changes increment `state_version` under `BEGIN IMMEDIATE`; each transition emits an append-only, idempotent event. Atomic claims include worker ID and expiring lease; heartbeat only renews the current live owner. Crash recovery applies bounded exponential delay, timeout detection and a dead-letter row after max attempts.

`daily_business_cycle` is persisted as six ordered local steps: research, build, quality, publish draft, convert, fulfill. The queue will not claim a later step until the preceding step is `DONE`; a failed quality gate blocks the run until an owner fixes the catalog and resumes it. Steps inspect local SQLite data only. Publish remains draft-only, conversions count only verified transactions, and fulfill reports verified orders awaiting manual delivery; no public post, ad, contact, payment, purchase or delivery side effect is run automatically. `AUTOPROFIT_ENGINE_WORKER=true` opts into scheduling; it is off by default. Manual runs persist even while the worker is off, and can be resumed/cancelled after restart. Shutdown exits the worker loop; clearing shutdown restarts it when the opt-in worker setting is enabled.

The registry uses exact tool names, permissions, providers and actions. Missing/unknown cost/provider blocks execution; positive cost is always blocked by the zero-cost policy. External tools default to dry-run and have no handler until explicitly implemented. A non-dry-run call requires a non-revoked exact permission, an unexpired one-use approval for the exact payload hash and available handler. The default-on kill switch blocks tool execution, queue claims and daily scheduling.

Structured engine log lines are JSON and omit request bodies; common credentials, email, phone/account-like numbers and secret assignments are redacted. Approval rows store a payload hash, not the submitted payload. Events and tool invocation results use the same redaction pass.

## Backup, migration and rollback

First rehearse in a staging copy. Create the backup directory yourself before migration; the importer intentionally will not create or overwrite one. Example from the repository root (replace `existing-backups` with a separately provisioned, access-controlled directory):

```powershell
New-Item -ItemType Directory -Path .\existing-backups
python -B backend\migrate_core_legacy.py `
  --source .\data\company.db `
  --target .\backend\data\company.db `
  --backup-dir .\existing-backups
```

The command emits backup paths and row counts only. It snapshots both DBs before import, checks snapshot integrity, and preserves the source revenue ledger. To rollback, stop the app and restore the desired snapshot to a **new** file, check `PRAGMA integrity_check`, then perform an operator-reviewed file switch only after confirming both code release and database pairing. The command will refuse to write an existing destination:

```powershell
python -B backend\migrate_core_legacy.py `
  --restore-backup .\existing-backups\backend-db-<timestamp>-<suffix>.sqlite `
  --target .\backend\data\company.rollback.sqlite
```

Do not point `--target` at a live file for rollback. Do not copy a WAL database using a raw file copy while writers are active; the script's SQLite backup API includes committed WAL state.

## Reproducible verification

Run from repository root with the already-installed pinned environment:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest tests.test_phase01_engine -v
python -B -m unittest discover -v
```

`tests/test_phase01_engine.py` creates independent temporary core/backend DBs, runs migrations twice, imports a sample legacy DB, verifies backups/rollback into a new path, exercises crash/timeout recovery, duplicate event/order keys, two competing workers, daily workflow E2E, kill switch, rejection/expiry/revocation and an authenticated API request. No production deployment or mutation of the checked-in user databases is part of this phase.

## Limits

- Current workflow actions intentionally perform local diagnostics and drafts only. There are no real agents, paid providers, ad telemetry, automatic contact/publish integration or fulfillment handler connected.
- `workflow_records` remains JSON-backed for existing products, opportunities and orders to preserve API compatibility; the migration adds typed supporting tables/projections without rewriting historical records.
- Legacy revenue rows are not counted in verified revenue. Reconcile/retire them through an owner-reviewed future migration only.
- SQLite WAL and `BEGIN IMMEDIATE` suit the requested lightweight local workload. For multiple hosts or sustained high write volume, move the queue to a server database before horizontal scaling.
- No production migration, VPS deploy, third-party network verification or external side-effect test was run.
