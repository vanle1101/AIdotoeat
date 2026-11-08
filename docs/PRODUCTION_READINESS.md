# Phase 09 production readiness

> This is the Phase 09 baseline snapshot. Its VPS and canary rows were superseded by the Phase 10 host verification in [the Phase 10 report](PHASE10_VPS_REPORT.md) and [machine-readable evidence](evidence/phase10/report.json).

This report distinguishes local evidence from VPS verification. The current production host was not contacted or changed. No production deploy, merge, or public post was performed.

## Verification status

| Area | Status | Evidence and limits |
|---|---|---|
| End-to-end workflow | **PASS** | [E2E evidence](evidence/phase09/e2e.json): source ingestion, opportunity scoring, QA package, review-only drafts, explicit TEST checkout, false claim rejected, owner-attested TEST payment excluded from real revenue, once-only delivery, crash recovery, provider unavailable/quota full, and hard kill switch. Uses temporary databases; no outbound model or payment request. |
| Migration and backup | **PASS** | The E2E evidence verifies schema version 13 is idempotent and SQLite backup/restore runs to new paths without changing the source DB. Operational helpers are in [scripts/ops.py](../scripts/ops.py). |
| Automated tests | **PASS locally and on Ubuntu CI** | Local `python -m pytest -q -p no:cacheprovider`: 140 passed, 1 skipped, 70 subtests passed; the five-agent workflow passed 20 consecutive runs. Ubuntu CI passed tests, dependency/license audits, and isolated E2E on commit `d6a644f`; see [GitHub Actions run 42479142872](https://github.com/vanle1101/AIdotoeat/actions/runs/42479142872) and [checks.json](evidence/phase09/checks.json). The skip is the Windows-only POSIX symlink test; Ubuntu CI covered it. |
| Python and shell syntax | **PASS** | `compileall`, Bash parser, and PowerShell parser are recorded in [checks.json](evidence/phase09/checks.json). Windows cannot execute `nginx -t` or `systemd-analyze`; those commands remain required on Debian before enabling the canary. |
| Dependency vulnerabilities | **PASS** | `pip-audit` checked 50 distributions from the pinned, hash-locked set and found 0 known vulnerabilities; pip and packaging are excluded by pip-audit defaults. See [pip-audit evidence](evidence/phase09/pip-audit.json). |
| Dependency licenses | **PASS; human review still required** | The metadata audit checked 52 locked distributions with no version/license metadata findings. Declared metadata is not legal approval; product-specific review remains required. See [license evidence](evidence/phase09/licenses.json). |
| Security smoke tests | **PASS** | E2E checks HTTPS-only owner auth, cross-origin mutation rejection, no permissive CORS, SQL-injection-like catalog input, private-address SSRF denial, artifact path traversal, secret redaction, and the hard stop. Existing Phase 00 tests cover public-form rate limiting and protected admin routes; Phase 05 tests cover escaped output, inert imports, and formula injection. |
| Performance smoke | **PASS** | E2E measures 20 in-process readiness probes and records median/p95/max. This is a local smoke threshold, not a production load test, browser FPS measurement, or GPU benchmark. VPS CPU/RAM/disk and external provider quota remain unverified. |
| Terms of service | **PARTIAL** | [Source terms audit](evidence/phase09/tos-audit.md): Stack Exchange attribution requirements were checked; official HN API terms and Stack Exchange quota documentation were unavailable or returned 504/404 during this audit. Existing low fetch caps/backoff remain mandatory. |
| Canary deployment | **NOT RUN in Phase 09** | [Canary systemd](../deploy/systemd/autoprofit-canary.service) and [Nginx](../deploy/nginx/autoprofit-canary.conf) were prepared but not deployed in this Phase 09 snapshot. Phase 10 results are linked above. |
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

The canary uses `/var/www/autoprofit-canary`, `/var/lib/autoprofit-canary`, API port 8451, and loopback-only web port 8889. Its standalone Nginx instance reads only the canary config; it does not reload the host Nginx service or touch listeners 8888, 80, 443, or 8000. It runs with a separate system account and empty payment/LLM credentials, worker disabled, both kill switches enabled, and TEST mode disabled.

1. Extract the exact, checksum-verified release to `/var/www/autoprofit-canary/releases/<commit-sha>`; never replace the live checkout. Create the Python 3.12 venv and install `requirements-dev.lock.txt` with `--require-hashes`. A browser binary is not needed on the VPS: run `scripts/phase10_browser.py` from a workstation through an SSH tunnel. Installing Playwright Chromium downloads more than 100 MB and is optional.
2. Create a dedicated `autoprofit-canary` system account and `/etc/autoprofit-canary.env` with mode `0640`, owned by `root:autoprofit-canary`. Leave payment destinations, order-token secret, remote LLM credentials, and TEST-mode key empty. Do not put credentials in the release directory.
3. Before writing, verify both unit files and environment file are new. Install only these canary-specific units:

   ```sh
   test ! -e /etc/systemd/system/autoprofit-canary.service
   test ! -e /etc/systemd/system/autoprofit-canary-nginx.service
   test ! -e /etc/autoprofit-canary.env
   install -o root -g root -m 0644 deploy/systemd/autoprofit-canary.service /etc/systemd/system/autoprofit-canary.service
   install -o root -g root -m 0644 deploy/systemd/autoprofit-canary-nginx.service /etc/systemd/system/autoprofit-canary-nginx.service
   systemd-analyze verify /etc/systemd/system/autoprofit-canary.service /etc/systemd/system/autoprofit-canary-nginx.service
   systemctl daemon-reload
   systemctl start autoprofit-canary.service autoprofit-canary-nginx.service
   curl --fail http://127.0.0.1:8451/api/ready
   curl --fail http://127.0.0.1:8889/api/ready
   ```

   Nginx validates the standalone config in `ExecStartPre`; its `listen` is bound to `127.0.0.1`. Do not enable the units at boot for a temporary test. If any destination already exists, stop and inspect it instead of overwriting it.
4. Run `ssh -N -L 18889:127.0.0.1:8889 root@<host>` from the workstation, then use `python scripts/phase10_browser.py --url http://127.0.0.1:18889/ --output-dir <new-evidence-directory>`. Owner routes correctly reject HTTP, even through the encrypted SSH tunnel; exercise authenticated HTTPS owner routes in the HTTPS integration tests, not by weakening this canary boundary.
5. Application and proxy output goes to systemd journal, which follows the host’s journald retention/rotation settings: `journalctl -u autoprofit-canary -u autoprofit-canary-nginx`. Check `journalctl --disk-usage` and the host’s `journald.conf` before extending log retention.
6. Roll back by stopping both units, restoring a verified SQLite backup to a new path if needed, and using `python scripts/ops.py rollback --releases-root /var/www/autoprofit-canary/releases --current-link /var/www/autoprofit-canary/current --target <previous-release-name>` to switch code. Never point canary at production databases. For a one-release verification, stop the canary and remove only the new canary units/config/state after collecting evidence; production files and services are not part of rollback.

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
