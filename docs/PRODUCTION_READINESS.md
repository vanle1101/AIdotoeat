# Phase 09 production readiness

This report distinguishes local evidence from VPS verification. The current production host was not contacted or changed. No production deploy, merge, or public post was performed.

## Verification status

| Area | Status | Evidence and limits |
|---|---|---|
| End-to-end workflow | **PASS** | [E2E evidence](evidence/phase09/e2e.json): source ingestion, opportunity scoring, QA package, review-only drafts, explicit TEST checkout, false claim rejected, owner-attested TEST payment excluded from real revenue, once-only delivery, crash recovery, provider unavailable/quota full, and hard kill switch. Uses temporary databases; no outbound model or payment request. |
| Migration and backup | **PASS** | The E2E evidence verifies schema version 13 is idempotent and SQLite backup/restore runs to new paths without changing the source DB. Operational helpers are in [scripts/ops.py](../scripts/ops.py). |
| Automated tests | **PASS locally; Linux check pending CI** | `python -m pytest -q -p no:cacheprovider`: 139 passed, 1 skipped, 70 subtests passed. The skipped rollback case is Linux/POSIX-specific; the Ubuntu CI workflow is configured to run it, and its result remains pending until pushed. See [checks.json](evidence/phase09/checks.json). |
| Python and shell syntax | **PASS** | `compileall`, Bash parser, and PowerShell parser are recorded in [checks.json](evidence/phase09/checks.json). Windows cannot execute `nginx -t` or `systemd-analyze`; those commands remain required on Debian before enabling the canary. |
| Dependency vulnerabilities | **PASS/FAIL from scan** | [pip-audit evidence](evidence/phase09/pip-audit.json) scans the pinned, hash-locked development/runtime set. Any remaining advisory must be resolved or explicitly accepted before deployment. |
| Dependency licenses | **PASS/FAIL with human review noted** | [license evidence](evidence/phase09/licenses.json) compares locked and installed package versions and declared license metadata. A declaration check is not legal approval; product-specific review remains required. |
| Security smoke tests | **PASS** | E2E checks HTTPS-only owner auth, cross-origin mutation rejection, no permissive CORS, SQL-injection-like catalog input, private-address SSRF denial, artifact path traversal, secret redaction, and the hard stop. Existing Phase 00 tests cover public-form rate limiting and protected admin routes; Phase 05 tests cover escaped output, inert imports, and formula injection. |
| Performance smoke | **PASS** | E2E measures 20 in-process readiness probes and records median/p95/max. This is a local smoke threshold, not a production load test, browser FPS measurement, or GPU benchmark. VPS CPU/RAM/disk and external provider quota remain unverified. |
| Terms of service | **PARTIAL** | [Source terms audit](evidence/phase09/tos-audit.md): Stack Exchange attribution requirements were checked; official HN API terms and Stack Exchange quota documentation were unavailable or returned 504/404 during this audit. Existing low fetch caps/backoff remain mandatory. |
| Canary deployment | **NOT RUN** | [Canary systemd](../deploy/systemd/autoprofit-canary.service), [Nginx](../deploy/nginx/autoprofit-canary.conf), and [log rotation](../deploy/logrotate/autoprofit-canary) are separate from the live vhost and use loopback ports 8451/8889. The Windows workspace cannot validate Debian syntax or host permissions. |
| HTTPS / browser check on VPS | **NOT RUN** | Current host TLS/VHost ownership was not inspected in this Phase 09 run. Reuse a certificate and TLS termination already controlled by the owner, or add the hostname to the existing ACME webroot flow after confirming that host’s port 80/443 routing. No paid domain is required for a free Let’s Encrypt certificate, but no certificate issuance or listener change was attempted. Do not expose owner routes through the canary’s HTTP-only loopback listener. |
| External publishing and real money | **NOT RUN by design** | No public post, outreach, bank transfer, or live payment was made. TEST records are excluded from summaries and the E2E evidence confirms zero test cash in real totals. |

## Reproducible Windows development

Run from PowerShell in the repository root:

```powershell
.\scripts\manage.ps1 -Action install -WithBrowser
.\scripts\manage.ps1 -Action migrate -Destination .\local-backup-before-migration.sqlite
.\scripts\manage.ps1 -Action start
```

In another PowerShell window:

```powershell
.\scripts\manage.ps1 -Action check -Url http://127.0.0.1:8450
python -m pytest -q
python scripts\phase09_e2e.py
```

The install script requires Python 3.12, installs only from `requirements-dev.lock.txt` with hashes, and creates `.env` only if it does not already exist. `-WithBrowser` downloads Chromium (over 100 MB) for screenshot-backed builds and browser tests; that download is separate from the Python lock. Set owner credentials locally; placeholder values keep external integrations off. To back up, use `-Action backup -Destination <new-file>`. Restore is copy-only: `-Action restore -Source <backup> -Destination <new-path>` never overwrites an existing DB.

## Debian canary procedure

The canary is additive and binds only to loopback. It does not use or reload ports 8888, 80, 443, 8000, or the current live service.

1. Prepare a separate checkout at `/var/www/autoprofit-canary/releases/<commit-sha>`, create the `.venv` with `bash scripts/manage.sh install --with-browser`, install Chromium runtime libraries according to the Debian release, and point `/var/www/autoprofit-canary/current` to that release. The Chromium download exceeds 100 MB. Do not replace the current live checkout.
   The screenshot renderer can use the pre-installed Chromium path when an operator sets `AUTOPROFIT_CHROMIUM_EXECUTABLE`; the process does not download browser weights at runtime.
2. Create a dedicated `autoprofit-canary` system account and `/etc/autoprofit-canary.env` with mode `0640`, owned by `root:autoprofit-canary`. Keep secrets out of the checkout. Leave payment settings empty, the LLM disabled, worker disabled, hard kill switch enabled, and TEST mode disabled. Install Chromium under the service state directory as that account:

   ```sh
   install -d -o autoprofit-canary -g autoprofit-canary -m 0700 /var/lib/autoprofit-canary/ms-playwright
   sudo -u autoprofit-canary env PLAYWRIGHT_BROWSERS_PATH=/var/lib/autoprofit-canary/ms-playwright /var/www/autoprofit-canary/current/.venv/bin/python -m playwright install chromium
   ```
3. Install only new, previously absent config names. Check every destination before writing:

   ```sh
   id autoprofit-canary || adduser --system --group --no-create-home autoprofit-canary
   test ! -e /etc/systemd/system/autoprofit-canary.service
   install -o root -g root -m 0644 deploy/systemd/autoprofit-canary.service /etc/systemd/system/autoprofit-canary.service
   test ! -e /etc/nginx/sites-available/autoprofit-canary.conf
   install -o root -g root -m 0644 deploy/nginx/autoprofit-canary.conf /etc/nginx/sites-available/autoprofit-canary.conf
   test ! -e /etc/logrotate.d/autoprofit-canary
   install -o root -g root -m 0644 deploy/logrotate/autoprofit-canary /etc/logrotate.d/autoprofit-canary
   ln -s /etc/nginx/sites-available/autoprofit-canary.conf /etc/nginx/sites-enabled/autoprofit-canary.conf
   nginx -t
   systemctl daemon-reload
   systemctl enable --now autoprofit-canary
   systemctl reload nginx
   curl --fail http://127.0.0.1:8889/api/ready
   ```

   If any `test ! -e` fails, stop and inspect the existing file. Do not overwrite it. Confirm that the host’s Nginx `sites-enabled` directory is included before adding the symlink.
4. To review the page from a browser, use an owner-controlled existing TLS reverse proxy or SSH access to the machine. The provided loopback listener is deliberately HTTP-only, so protected owner routes reject it. Do not open a public plain-HTTP canary or change another site’s TLS vhost as part of this procedure.
5. For a future authorized code release, keep the prior release directory and use `python scripts/ops.py rollback --releases-root /var/www/autoprofit-canary/releases --current-link /var/www/autoprofit-canary/current --target <previous-release-name>` to atomically switch the canary symlink. Restart its service after switching. Database rollback is separate: restore a verified backup to a new path, verify it, then explicitly update the canary environment file.

The optional weekly optimizer units are [service](../deploy/systemd/autoprofit-weekly-optimizer.service) and [timer](../deploy/systemd/autoprofit-weekly-optimizer.timer). The job reads only first-party aggregate metrics, stores at most one review proposal per experiment slot, applies no public changes, and returns without writing if the hard kill switch is active. Do not enable it until its service account has only the required database access.

## Reproducible Debian operations

```sh
bash scripts/manage.sh install
bash scripts/manage.sh check --url http://127.0.0.1:8450
python scripts/ops.py migrate --backup /var/backups/autoprofit/company-before-phase09.sqlite
python scripts/ops.py backup --destination /var/backups/autoprofit/company-manual.sqlite
python scripts/ops.py restore --source /var/backups/autoprofit/company-manual.sqlite --destination /var/lib/autoprofit/restore-review.sqlite
```

The production service must be stopped or coordinated with SQLite’s backup API before a manual restore is switched in. Restore never overwrites. The canary creates its own data directory and should not point at production databases.

## Branch and release gate

The change is on `codex/autoprofit-phase-09-production-readiness`. CI must install the hash-locked requirements, pass the test and E2E suites, dependency audit, license declaration check, and config checks before a PR is created. A PR does not deploy or merge the code. Production changes require the owner’s explicitly authorized workflow and a host-verified canary first.
