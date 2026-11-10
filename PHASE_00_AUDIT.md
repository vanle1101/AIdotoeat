# AUTOProfit AI — Phase 00 Safety Audit

## Repository state

- Checkout: `codex/autoprofit-phase-00-safety`
- Base/current parent at audit start: `1424d3355616bbded9a9398fb832b9fcfd206bb` (`origin/main`)
- The branch already contained uncommitted Phase 00 work from the interrupted run. The working tree had no separate known user edits; this audit continues those changes and adds the remaining fixes.
- No production host, ad network, Nginx configuration, systemd unit, or live database was changed.

## Inventory

### Entrypoints and runtime

| Area | Entry point | Notes |
|---|---|---|
| Interactive CLI | `run.py` (`main_menu`, `__main__`) | Calls the local orchestrator; budget gate applies before registered operations. |
| API | `backend/main.py` (`app`) | FastAPI app, includes `backend/workflow_api.py`; direct execution now binds `127.0.0.1:8450`. |
| Static dashboard | `frontend/index.html` | Loads core UI, Three.js scene, reference dashboard/command center, safety guard, and first-party telemetry. |
| Tool generator | `backend/apps_library.py` / `build_all_tools()` | Generates the 12 public standalone tool pages. Generated pages no longer embed owner payout destinations. |
| Traffic worker | `backend/traffic_worker.py` | Retained as an inert compatibility entrypoint; it does not fetch pages, ad URLs, or video URLs. |
| YouTube page | `frontend/youtube-booster.html` | Replaced with a disabled notice; the dashboard retains a manual metadata/thumbnail analyzer. |
| Auto-surf page | `frontend/autosurf.html` | Now a manual list of first-party tools. It does not navigate automatically or load hidden ad frames. |

The repository has no package manager/build script for the static frontend and no checked-in cron, Celery, APScheduler, or systemd definitions. The supplied VPS services are external to this checkout. Browser timers that remain are for dashboard polling, market-price refresh, and first-party telemetry; the retired worker and YouTube engagement flows do not use them to generate visits or clicks.

### Dependencies

`requirements.txt` pins the direct Python runtime/test dependencies already present in the environment: FastAPI 0.136.1, Uvicorn 0.47.0, Segno 1.6.6, python-dotenv 1.2.1, HTTPX 0.28.1, and Rich 14.3.2. Three.js, GLTFLoader, and SkeletonUtils are served from local files; there is no npm manifest.

`pip check` reports conflicts in the shared Python environment involving unrelated installed tools (including aider-chat, patchright, SciPy, and Selenium, plus a `typing-extensions` constraint). No dependency was installed or upgraded for this task. The project test suite and the pinned direct dependencies run successfully in that environment.

### API inventory

`backend/main.py` and `backend/workflow_api.py` expose the following route groups. “Public path” does not mean every handler returns data without owner authentication: the inquiries and donations listing routes return no records unless `_admin` succeeds.

| Access | Routes |
|---|---|
| Public reads | `GET /api/health`, `/api/dashboard`, `/api/dashboard/summary`, `/api/pricing/catalog`, `/api/products`, `/api/products/{slug}/download`, `/api/public/aads-config`, `/api/public/aads-live-telemetry`, `/api/llm/token-ledger`, `/api/github-web-factory/apps`, `/api/github-web-factory/apps/{slug}/live`, `/api/github-web-factory/apps/{slug}/download`, `/api/public/donations/health` |
| Public reads requiring owner key | `GET /api/public/advertising-inquiries`, `/api/public/donations`, `/api/leads` |
| Public submissions / calculations | `POST /api/telemetry/pageview`, `/api/telemetry/heartbeat`, `/api/public/payment-reports`, `/api/public/payment-reports/status`, `/api/public/advertising-inquiries`, `/api/public/donations`, `/api/employees/propose` (pending review; auto-approval requires owner key), `/api/public/notebook/interact`, `/api/opportunities/analyze-freelance-job`, `/api/internet/live-scan`, `/api/products/live-audit-demo`, `/api/pricing/quote`, `/api/payments/submit-mbbank-proof`, `/api/public/orders/verify-bsc-tx` |
| Owner/admin reads | `GET /api/admin/payment-reports`, `/api/audit-logs`, `/api/opportunities`, `/api/marketing`, `/api/employees`, `/api/settings/budgets`, `/api/payout-policies`, `/api/pricing/history`, `/api/pricing/recommendations`, `/api/orders`, `/api/tasks`, `/api/transactions`, `/api/wallet/binance-usdt`, `/api/dashboard/activity`, `/api/dashboard/activity/stream`, `/api/dashboard/activity/{event_id}` |
| Owner/admin writes | `POST /api/admin/auth/verify`, `/api/admin/payment-reports/{report_id}/verify`, `/api/admin/advertising-inquiries/{inquiry_id}/verify`, `/api/admin/donations/{donation_id}/verify`, `/api/marketing/generate/{product_id}`, `/api/employees/{employee_id}/approve`, `/api/employees/{employee_id}/retire`, `/api/leads/auto-approve-all`, `/api/leads/{lead_id}/approve-proposal`, `/api/public/aads-config`, `/api/pricing/recommendations/generate`, `/api/pricing/recommendations/{recommendation_id}/review`, `/api/payments/verify-mbbank-tx`, `/api/payments/verify-bsc-tx`, `/api/orders`, `/api/orders/{order_id}/deliver`, `/api/tasks/{task_id}/approve`, `/api/system/pause`, `/api/system/resume`, `/api/system/emergency-stop`, `/api/agents/run-cycle`, `/api/github-web-factory/auto-harvest`, `/api/github-web-factory/scan-and-build` |
| Owner/admin updates | `PUT /api/products/{product_id}`, `/api/settings/budgets`, `/api/payout-policies`, `/api/pricing/catalog/{product_id}`, `/api/employees/{employee_id}/appearance` |

`GET /api/pricing/catalog` is registered both by the workflow router and the legacy main module. Both return the product catalog; the duplicate is an API maintenance issue, not an observed authorization bypass.

### Configuration, monetization, and data stores

- `backend/config.py` loads `.env` without overriding process environment values. Owner bank, Binance Pay, affiliate, ad-unit, and RPC settings are environment-backed and validated; `.env.example` contains empty placeholders.
- `core/config.py` defaults the zero-cost kill switch to enabled.
- Legitimate ad placement slots remain in generated tool HTML and use configured placement identifiers. No automated ad-click or impression generator remains. First-party pageview/heartbeat telemetry remains enabled and can mark internal tests for exclusion.
- Manual bank proofs remain pending until an owner verifies them. BSC payments are checked against the configured RPC, token contract, destination wallet, receipt, and transaction replay state. There is no inbound payment-provider webhook route.
- Two SQLite stores are used: `backend/data/company.db` (`backend/config.py:21`) for workflow/payment/telemetry records, and `data/company.db` (`core/config.py:12`, `backend/dashboard_data.py:14`) for the local task/event ledger. Tests redirect both stores to temporary directories; no existing database was copied, reset, or deleted.

## Findings and changes

| Severity | Before | After / status | Evidence |
|---|---|---|---|
| **High — owner payout destinations exposed in Git history** | The base commit contains owner bank/Pay identifiers and an affiliate identifier in `backend/config.py:19-35`, `backend/apps_library.py:729-737`, and the generated `frontend/apps/*.html` checkout blocks (12 pages, around lines 266-271). | Removed from the current tree; config is environment-backed (`backend/config.py:48-123`). Generated standalone pages intentionally show payment as unconfigured and do not embed owner details (`backend/apps_library.py:455-458`). The historical commit remains reachable on `origin/main`; this branch does not rewrite history. | Historical contents are deliberately not repeated here. The high-confidence credential scan found no private keys or common provider access tokens. These historical values are payment/referral destinations, not authentication credentials; replace them with new destinations only if the owner wants to revoke public discoverability. Remove historical blobs only through a separately coordinated repository-history rewrite. |
| **High — artificial ad and video engagement** | The old traffic worker and dashboard included automatic navigation, monetized bridges, YouTube view/watch flows, and synthetic workforce/branch activity. | Worker is inert (`backend/traffic_worker.py:1-20`); Auto-surf is a manual first-party tool list; the YouTube booster page is disabled. Thirty-eight monetized `/go/bridge.html` article links were replaced with direct article URLs, browser-local affiliate click counters and YouTube view/watch reward workstation profiles were removed, and the false 30-second/$1,000 reward panel was relabeled as disabled. Manual user-supplied YouTube SEO analysis remains. Affiliate cards are labeled as unverified examples (`frontend/index.html:1038`, `frontend/index.html:3532-3630`). Ad placements and first-party telemetry remain. | Regression tests assert no monetized bridge anchors, browser-local click counters, YouTube reward workstation profiles, embeds or auto-surf behavior remain (`tests/test_phase00_safety.py`). No production deploy was performed; the VPS keeps its current code until separately deployed. |
| **High — fabricated live metrics and ratings** | Dashboard defaults and local scripts supplied claimed revenue, views, ratings, agent counts, campaign counts, and “LIVE” states without verified sources. | Revenue/profit/provider metrics use `—` until verified; public dashboard APIs suppress revenue; unknown profiles are marked demo; no app star count is seeded. Branch, visitor, campaign, and ad telemetry placeholders now state when data is unavailable. | `backend/main.py:450-458,518-588`; `frontend/autoprofit-core.js:1980-2160`; `frontend/site-telemetry.js`; `backend/apps_library.py` (catalog definitions). Regression tests in `tests/test_phase00_safety.py`. |
| **High — unauthenticated admin/payment operations** | Admin/payment mutation and owner-data routes required consistent threat modeling. | Sensitive route handlers require a configured key of at least 32 characters over HTTPS, compared with `hmac.compare_digest` (`backend/workflow_api.py:31-57`, `backend/main.py:111-119`). Public mutations reject mismatched `Origin` and are rate-limited (`backend/main.py:120-174`; limits stored by `backend/database.py:197-224`). Payment status remains pending until owner review; BSC receipt reuse is rejected (`backend/workflow_api.py:1040-1150`). | Route tests assert protected admin/payment endpoints deny missing keys and accept a valid test key only over HTTPS. No real payment was submitted. |
| **High — admin key sent over HTTP / client-only unlock** | The browser could attach a key from session storage to an HTTP request; the hidden logo PIN path could mark the client UI as owner without server verification. | The client sends admin credentials only for same-origin HTTPS targets (`frontend/autoprofit-core.js:1548-1578,1684-1694`); it no longer puts the key in a request body. The reference activity view also suppresses the key on HTTP (`frontend/reference-dashboard.js:555-562`). The client-only PIN unlock was removed; the shortcut now calls the server-backed login flow (`frontend/autoprofit-3d.js`). | A static regression test verifies the transport guard and absence of the local PIN bypass. |
| **High — unsafe direct API bind** | Running `python backend/main.py` bound the app to `0.0.0.0:8000` with reload enabled. | Direct startup now binds `127.0.0.1:8450` without reload, avoiding the separately used port 8000 and public interface (`backend/main.py:735-737`). | Regression test asserts the internal bind. The VPS systemd and Nginx files were not changed. |
| **Medium — zero-cost policy trusted caller claims** | The previous keyword loop accepted a caller-supplied zero cost without verifying the provider/action. | `BudgetAuditor` now allows only registered local operations and provider identities, rejects unknown cost/provider/action or paid exposure, and checks the default-on kill switch (`core/budget_auditor.py:21-83`, `core/config.py:40-43`). | Unit tests cover declared zero, unknown action, unverified provider, paid cost, callable spoofing, and kill-switch cases. |
| **Medium — cross-origin abuse and public form flooding** | Public form routes had no uniform origin/rate controls. | Same-origin checks and per-route limits cover public forms, including the pending employee proposal form (`backend/main.py:120-143`); a generic cap covers other API mutations. Internal test telemetry is excluded from both pageview and heartbeat records (`backend/main.py:86-88,120-174,195-230`). | Regression tests exercise cross-origin rejection, 429 behavior, and excluded test telemetry. |
| **Medium — SSRF / webhook spoofing** | The old client included external integrations and a banking notification listener that was not a provider-authenticated webhook. | No user-controlled URL fetch route was confirmed in the current backend. `/api/internet/live-scan` calls a fixed public Hacker News API endpoint (`backend/workflow_api.py:703-729`); the HTML audit accepts supplied HTML rather than crawling a URL. The notification listener is absent, and bank proof remains manual. The BSC RPC URL is environment-configured and rejects non-HTTPS or literal private/local targets (`backend/config.py:30-45`). | No live external verification was run. RPC DNS results are not pinned to a public IP, so a maliciously configured DNS name remains a deployment-level SSRF risk; use a trusted RPC hostname. |
| **Medium — public data exposure / XSS** | Public pages and API responses could mix financial values with unverified UI state. | Public dashboard revenue is nulled without owner auth; inquiry/donation lists return no records without owner auth. Dynamic activity views escape inserted values (`frontend/reference-dashboard.js`). No permissive CORS middleware is registered; mutating requests with a foreign `Origin` are rejected. | No exploitable XSS was confirmed by the Phase 00 static pass. Session-storage keys remain readable to same-origin JavaScript; protect against future XSS and use a high-entropy admin key. |

## Backup, migration, and rollback plan

No backup file or production release was created for this task. Before a later deployment:

1. Quiesce the backend services or take SQLite snapshots with Python's SQLite backup API so WAL state is included. Snapshot both `backend/data/company.db` and `data/company.db` and record timestamps/byte sizes; do not copy only the main database file while writers are active.
2. Run `PRAGMA integrity_check` on each snapshot and restore both into an isolated staging copy. Compare table names and row counts without exposing customer or payment contents.
3. Keep migrations additive and transactional. Record the schema version before applying changes; do not delete or rewrite transaction rows. Validate application startup and payment/report read paths against the staged copies.
4. Deploy code as a separate release directory or atomic symlink switch, preserve the existing `.env`, venv, and both databases, and keep the current release available for code rollback. Do not alter the Nginx port-8888 vhost or the separate port-8000 service.
5. If a migration is not backward-compatible, stop both services and restore the matching pair of database snapshots before switching back to the prior release. Test that rollback procedure on staging first.

The supplied production URL is HTTP on port 8888. Because admin routes now require HTTPS, owner/admin actions will remain unavailable through that URL until TLS is configured. This change was intentionally not deployed or worked around by sending the key over HTTP.

## Verification results

- `python -B -m unittest discover -v`: **32 tests passed**.
- Python AST parse: **20 Python files passed**.
- `node --check`: **six application JavaScript files passed**.
- Inline JavaScript compile check: **15 scripts passed**.
- Python HTML parser: **18 frontend pages parsed**.
- `git diff --check`: passed.
- `pip check`: **failed on pre-existing conflicts in the shared Python environment** (aider-chat, patchright, SciPy, Selenium, and typing-extensions); no packages were installed or changed.
- No frontend bundler/build command exists in this repository. No screenshot/browser smoke test or production deploy was claimed or performed.

## Changed files

The exact Phase 00 changed-file list below is derived from the branch diff. Generated standalone pages are regenerated from `backend/apps_library.py`; only generated files with source changes are included.

- `.env.example`
- `PHASE_00_AUDIT.md`
- `README.md`
- `backend/apps_library.py`
- `backend/config.py`
- `backend/database.py`
- `backend/main.py`
- `backend/traffic_worker.py`
- `backend/workflow_api.py`
- `core/budget_auditor.py`
- `core/config.py`
- `core/orchestrator.py`
- `frontend/apps/ai-prompt-markdown-converter.html`
- `frontend/apps/crypto-arbitrage-spread-scanner.html`
- `frontend/apps/css-glassmorphism-card-builder.html`
- `frontend/apps/defi-staking-yield-compounder.html`
- `frontend/apps/json-schema-seo-studio.html`
- `frontend/apps/openai-tiktoken-cost-estimator.html`
- `frontend/apps/papaparse-csv-to-json-cleaner.html`
- `frontend/apps/password-hash-security-auditor.html`
- `frontend/apps/saas-roi-pomodoro-calculator.html`
- `frontend/apps/seo-opengraph-meta-generator.html`
- `frontend/apps/vietqr-crypto-payment-generator.html`
- `frontend/apps/web3-airdrop-testnet-quest-tracker.html`
- `frontend/autoprofit-3d.js`
- `frontend/autoprofit-core.js`
- `frontend/autosurf.html`
- `frontend/feed.xml`
- `frontend/index.html`
- `frontend/phase00-safety.js`
- `frontend/reference-dashboard.js`
- `frontend/site-telemetry.js`
- `frontend/youtube-booster.html`
- `modules/qr_vault.py`
- `requirements.txt`
- `run.py`
- `tests/__init__.py`
- `tests/test_engine.py`
- `tests/test_phase00_safety.py`
