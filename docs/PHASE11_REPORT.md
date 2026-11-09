# PHASE 11 — Production Security Remediation and Safe Release

**Release decision: NO-GO for production.** Milestone 1 is complete: live preflight, code/config patches, an authorized online SQLite backup with isolated restore verification, and dry-run checks. The production traffic worker and backend remain untouched. Milestone 2 requires one explicit owner approval before any production service, filesystem permission, Nginx, or deployment change.

Phase 11 implementation commit: `0cd8d36c2bfde50212449bb627a37b50d5f5ad22` on PR #1. Both required `verify` CI jobs passed on this commit: [job 1](https://github.com/vanle1101/AIdotoeat/actions/runs/42665753947/job/129328827811) and [job 2](https://github.com/vanle1101/AIdotoeat/actions/runs/42665761253/job/129328850403). The report/evidence finalization commit contains no runtime code changes.

Evidence is in [vps-preflight.json](evidence/phase11/vps-preflight.json). The Phase 10 baseline is [PHASE10_VPS_REPORT.md](PHASE10_VPS_REPORT.md). This report never includes bank/account identifiers, admin keys, or secret values.

## A. Fresh preflight

The Phase 10 report was read and the live VPS was checked again over the configured SSH key on 2026-11-09 UTC. PR #1 was open on `codex/autoprofit-phase-09-production-readiness` at preflight HEAD `49c815d514a0659fb368ce3a9ddb403d2652096b`. Both CI jobs passed at that HEAD before Phase 11 edits; CI will be rerun for the resulting commit.

The host is Ubuntu 24.04 with 6 vCPU, 5.79 GiB RAM, about 1.69 GiB available, 3.33 GiB of 4 GiB swap used, and about 34 GiB free on the root disk. `vmstat` sampled three one-second intervals without generating load. This is an observation, not a stress test. No Ollama/llama.cpp runtime or model file was found in the checked paths; no model was installed or downloaded.

The production API is still behind HTTP Nginx on `:8888`: `/` and `/api/health` returned 200, while `/api/ready` returned 404. The current admin payment-report route returned 403 without credentials, but the configured owner credential was absent and valid owner authentication was not verified. The canary on loopback `8451/8889` remains active but disabled at boot; its `/api/ready` returned 200, worker was false, and both kill switches were true.

`nginx -t` passed. It emitted existing duplicate TLS-option warnings from shared virtual hosts; no Nginx file was changed or reloaded. Host UFW is absent, `iptables` INPUT policy is ACCEPT, and the provider-level firewall was not verified. Port 8000 remains loopback-bound and was not touched. Existing journald use was 311.9 MiB against a configured 300 MiB limit; logs were not read because they may contain customer data.

## B. Emergency traffic

The production `autoprofit-traffic` unit is **active, enabled at boot, and running as root** with `Restart=always`. Its deployed worker is 2,501 bytes and has a different SHA-256 from the retired worker in the PR. A static signature scan found user-agent/randomization markers, external URL literals, browser markers, and ad/video terms. The live `autosurf.html` has iframe, timer, and ad-network markers. These are risk indicators; no impressions, page automation, or traffic were triggered to test them.

The current PR worker is an inert compatibility process; its `autosurf.html` and `youtube-booster.html` say those paths are disabled. The production copy is stale and does not match those files. The unit has **not** been stopped, disabled, or masked because the owner has not approved Milestone 2.

The interface role for distribution was also corrected. It now describes owner-reviewed drafts and no automatic posting or ad impressions, rather than claiming that it syndicates content to drive ad impressions.

## C. Backup and restore

At 2026-11-09 16:57:17 UTC, `/var/www/autoprofit/backend/data/company.db` was backed up from the live WAL database with SQLite's online backup API while services remained up. The source was not modified. Backup folder mode is `0700`; database and manifest are `0600`. Integrity was `ok`; the restore-copy integrity, schema, table count, mode, and hash checks passed. A separate read-only recheck found source and backup table row counts equal. The online backup included committed WAL content.

- Backup: `/var/backups/autoprofit-phase11-20261109T165717Z/backend-company.db`
- SHA-256: `79ff557f6a5eeb653768e337db86ad7406c07cd4448b1c6e5e56aab95db3d778`
- Manifest SHA-256: `4253bf27a320cceca05dc9ad1130fb4f2b1be9fb5b291aca06eb7e6178dfe712`
- Core database: not present at its configured default path; no empty database was created.
- Offsite copy: not confirmed. The verified backup is on the same VPS.

## D. Least privilege

Production backend still runs as root with two Uvicorn workers and `UMask=0022`. Its SQLite file is `root:root`, mode `0666`; the `backend/data` directory is `0755`. The production `frontend/autosurf.html` is also `0666`. There is no `autoprofit` user/group or `/var/lib/autoprofit` state directory yet. No ownership or permission was changed.

The new review-only systemd template [autoprofit-backend-phase11.service](../deploy/systemd/autoprofit-backend-phase11.service) uses a dedicated `autoprofit` identity, one worker, `UMask=0077`, journald, strict filesystem protection, fail-closed worker/kill-switch settings, and write access only to `/var/lib/autoprofit` plus the app catalog directory. Database/core data and product outputs move under `/var/lib/autoprofit`; generated public HTML explicitly receives mode `0644` so Nginx can read it while other users cannot write it. Product staging now follows `AUTOPROFIT_OUTPUTS_DIR` instead of writing beneath the source checkout.

The template passed `systemd-analyze verify` without a template error. The host printed an unrelated existing syntax warning for `/etc/systemd/system/codex-lb.service`; it was not modified. Account creation, path preparation, read/write tests under the new account, and service switch remain for Milestone 2.

## E. HTTPS and Nginx

The user-facing AUTOProfit entrypoint is plain HTTP at `:8888`; TLS on `:8888` fails. The `160.22.107.108.sslip.io` host did not negotiate TLS. `gpt.vorte.me` has a currently valid certificate whose SAN is only `gpt.vorte.me`, but the existing vhost proxies to `127.0.0.1:3000`, a different application. It must not be repointed. No production TLS vhost was changed.

Milestone 2 must use a separate hostname with a certificate that actually covers it, add an isolated vhost, run `nginx -t`, and then reload Nginx only after the owner approves. HTTP redirect and HTTPS-only owner routes must be verified at that entrypoint. No paid domain or certificate purchase is part of the plan.

## F. API, configuration, and current behavior

- **CORS:** production OPTIONS reflected `https://untrusted.example` and returned `Access-Control-Allow-Credentials: true`. The Phase 10 canary did not reflect that origin. The current branch has same-origin mutation checks and no permissive CORS middleware; a regression test now asserts that untrusted preflight does not receive allow-origin/credentials headers. This production finding remains open until the corrected release is deployed.
- **Admin:** anonymous GET was rejected with 403. No admin key or order secret was present in the backend process/environment files checked, so owner authentication is not verified. Do not treat 403 alone as proof the owner can authenticate.
- **Payments:** no payment/admin environment flags were present in the live process. The deployed legacy `backend/config.py` still contains hardcoded payee identifiers; they are not API credentials, but the production source has not yet adopted the PR's environment-based configuration. No claim, verification, transaction, or payment action was sent.
- **Worker/kill switch:** production worker and kill-switch environment flags were absent. The new service template defaults the worker off, kill switches on, and TEST mode off.
- **Readiness/revenue:** production `/api/ready` is missing and live revenue semantics were not revalidated against the stale deployed code. The current branch's Phase 07/10 tests cover verified-only revenue and test-cash exclusion; this is not a production PASS.
- **CORS, payment, and UI:** no API with a paid plan was called; no ad impressions, ad clicks, outreach, external publishing, or payment was created. Cost remained 0 VND.

## G. Git history

The current branch and reachable refs were scanned for high-confidence private-key/API-token patterns; none matched. Payee/account and affiliate/referral identifiers did appear in the public base history (`1424d3355616`) and were removed from current source configuration in Phase 00. These identifiers are payment destinations/tracking IDs, not authentication secrets. No Git history was rewritten and no rotation is recommended for these values as credentials; review bank activity for fraud using the owner's normal process.

## H. Rollback and Milestone 2 sequence

The canary code rollback was exercised in Phase 10, but no production rollback was executed. Before any production change, Milestone 2 must:

1. Capture the current deployed unit and release identity, then take and verify a fresh online SQLite backup. Keep the current database untouched as the rollback source.
2. Create the dedicated service user and state directories. Restore the backup to a new state path, migrate only that copy, and verify integrity, row counts, permissions, and read/write behavior using the new account before switching the service.
3. Stop, disable, and mask the legacy traffic unit; confirm its process is gone. This is the first production action because the deployed code has markers consistent with generated traffic; no impression test was performed.
4. Install the reviewed systemd unit, initially keep engine/payment/external actions fail-closed, and start one backend worker on loopback. Do not enable automation.
5. Add only an additive AUTOProfit HTTPS vhost for a certificate-covered hostname. Run `nginx -t`; preserve all shared vhosts and reload only after success.
6. Keep writes gated during smoke checks. Require `/api/ready` 200, anonymous admin rejection, valid owner auth over HTTPS, no CORS reflection, worker stopped, kill switch effective, payment/test flags safe, and a browser check that makes no third-party ad requests. If a check fails before writes resume, restore the prior unit and untouched database and remove only the new vhost.

This plan is not authorization to run those steps.

## I. Tests and changes

Changes prepared on the PR branch:

- [phase11_ops.py](../scripts/phase11_ops.py): SQLite online backup, checksum, schema/row-count verification, restrictive POSIX modes, and isolated restore checks. It never overwrites an existing bundle.
- [autoprofit-backend-phase11.service](../deploy/systemd/autoprofit-backend-phase11.service): uninstalled least-privilege template for review.
- [product_studio_api.py](../backend/product_studio_api.py) and [apps_library.py](../backend/apps_library.py): persistent writable output path and public HTML file mode for the hardened service.
- [autoprofit-core.js](../frontend/autoprofit-core.js): accurate distribution-role readiness and behavior.
- [test_phase00_safety.py](../tests/test_phase00_safety.py) and [test_phase11_security.py](../tests/test_phase11_security.py): CORS regression, retired traffic paths, artifact permissions, service policy, and backup/restore.

The final local full suite passed: **153 passed, 1 skipped, 70 subtests passed**. The sole skip is the POSIX-only systemd release-symlink rollback test on Windows. `py_compile`, `git diff --check`, the systemd template dry-run, Nginx syntax check, and both PR CI jobs passed; see [test-output.txt](evidence/phase11/test-output.txt). No tests create ad impressions or use paid APIs.

## J. Acceptance and decision

| Acceptance | Current evidence | Result |
|---|---|---|
| No artificial traffic path active | Legacy traffic service active/root; deployed files differ from retired PR source | **FAIL** |
| Backend not running as root | Production unit is root; `autoprofit` identity absent | **FAIL** |
| No world-writable database | Production DB remains mode `0666` | **FAIL** |
| Backup and restore | Online WAL backup, hash, integrity, isolated restore, and row-count comparison pass | **PASS for backend DB only** |
| Core DB backup | No core DB exists at configured path | **NOT APPLICABLE / confirm ownership** |
| HTTPS at user entrypoint | AUTOProfit on HTTP `:8888`; available TLS vhost belongs to another app | **FAIL** |
| `/api/ready` | Production 404; canary 200 | **FAIL production** |
| Admin protected | Anonymous route returns 403; owner auth not configured/verified; CORS reflects arbitrary origin | **FAIL release gate** |
| Production payment/revenue truth | Legacy deploy has hardcoded payee values; production semantics not verified | **FAIL / unverified** |
| No data loss / no side effects during audit | Source DB unchanged; no service, Nginx, payment, ad, or firewall change | **PASS** |
| Test and code checks | Full suite and local dry-runs pass; both PR verify jobs pass on implementation commit | **PASS** |

**Production remains NO-GO.** Only Milestone 2 maintenance approval is outstanding. The owner must explicitly approve the one controlled change set described above: stop/disable/mask the legacy traffic unit, migrate the backend to the dedicated service user and protected state directories, and add a separate HTTPS vhost after a covering certificate is available. Until that approval arrives, production remains as observed and no service, database permission, Nginx, firewall, merge, or deploy action will be taken.
