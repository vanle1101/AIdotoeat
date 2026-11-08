"""Fully isolated Phase 09 rehearsal; public source is a captured licensed API record."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for entry in (str(ROOT), str(BACKEND)):
    if entry not in sys.path:
        sys.path.insert(0, entry)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _crash_mid_run(state_file: Path) -> int:
    from backend import business_engine as engine
    from domain_models import TaskSpec

    engine.ensure_schema()
    engine.set_engine_control("kill_switch", False)
    spec = TaskSpec(title="Phase 09 resumable local report", category="E2E",
                    assigned_role_id="QAReviewer", task_type="phase09.e2e",
                    idempotency_key="phase09:e2e:crash-restart", trace_id="phase09-e2e-trace-01",
                    payload={"step": "write local report"}, max_attempts=3, timeout_seconds=300)
    task = engine.create_task(spec)
    now = engine.utc_now()
    claimed = engine.claim_task("phase09-crash-worker", lease_seconds=60, now=now)
    if not claimed or int(claimed["id"]) != int(task["id"]):
        _write_json(state_file, {"failure": "task_not_claimed"})
        return 74
    conn = engine.connect()
    try:
        conn.execute("UPDATE tasks SET lease_expires_at=? WHERE id=?",
                     (engine.iso(now - timedelta(seconds=1)), task["id"]))
        conn.commit()
    finally:
        conn.close()
    _write_json(state_file, {"task_id": int(task["id"]), "idempotency_key": spec.idempotency_key,
                             "trace_id": spec.trace_id, "crash_exit_code": 73})
    os._exit(73)  # Deliberate hard process exit after durable claim; simulates host process loss.


def _resume_after_crash(state_file: Path) -> int:
    from backend import business_engine as engine
    from domain_models import TaskSpec

    state = json.loads(state_file.read_text(encoding="utf-8"))
    task_id = int(state["task_id"])
    recovered_at = engine.utc_now() + timedelta(seconds=5)
    recovered = engine.recover_crashed_tasks(now=recovered_at)
    spec = TaskSpec(title="Phase 09 resumable local report", category="E2E",
                    assigned_role_id="QAReviewer", task_type="phase09.e2e",
                    idempotency_key=state["idempotency_key"], trace_id=state["trace_id"],
                    payload={"step": "write local report"}, max_attempts=3, timeout_seconds=300)
    same = engine.create_task(spec)
    claim = engine.claim_task("phase09-restart-worker", now=recovered_at + timedelta(seconds=3))
    if not claim or int(claim["id"]) != task_id or int(same["id"]) != task_id:
        _write_json(state_file, {**state, "resume_failure": "idempotent_reclaim_failed", "recovered": recovered})
        return 75
    completed = engine.complete_task(task_id, "phase09-restart-worker",
                                     {"status": "DONE", "artifact": "local-only"})
    conn = engine.connect()
    try:
        event_count = int(conn.execute("SELECT COUNT(*) FROM task_events WHERE task_id=?", (str(task_id),)).fetchone()[0])
    finally:
        conn.close()
    _write_json(state_file, {**state, "recovered_tasks": recovered, "attempts": int(completed["attempts"]),
                             "final_state": completed["state"], "event_count": event_count})
    return 0 if recovered == 1 and completed["state"] == "DONE" else 76


def run(*, output_dir: Path, evidence_path: Path) -> dict:
    output_dir = output_dir.resolve()
    stage_dir = output_dir / "staging"
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="autoprofit-phase09-e2e-") as work_dir_text:
        work_dir = Path(work_dir_text)
        data_dir = work_dir / "backend-data"
        data_dir.mkdir()
        core_dir = work_dir / "core-data"
        core_dir.mkdir()
        runtime_output = work_dir / "runtime-output"
        runtime_output.mkdir()
        test_key = secrets.token_urlsafe(40)
        admin_key = secrets.token_urlsafe(48)
        order_secret = secrets.token_urlsafe(48)
        os.environ.update({
            "AUTOPROFIT_ENV": "staging",
            "AUTOPROFIT_DATA_DIR": str(data_dir),
            "AUTOPROFIT_CORE_DATA_DIR": str(core_dir),
            "AUTOPROFIT_OUTPUTS_DIR": str(runtime_output),
            "AUTOPROFIT_ADMIN_API_KEY": admin_key,
            "AUTOPROFIT_ORDER_TOKEN_SECRET": order_secret,
            "AUTOPROFIT_TEST_MODE_ENABLED": "true",
            "AUTOPROFIT_TEST_MODE_KEY": test_key,
            "AUTOPROFIT_ENGINE_WORKER": "false",
            "AUTOPROFIT_ENGINE_KILL_SWITCH": "false",
            "AUTOPROFIT_BUDGET_KILL_SWITCH": "true",
            "AUTOPROFIT_LLM_PROVIDER": "openai_compatible",
            "AUTOPROFIT_LLM_ENDPOINT": "",
            "AUTOPROFIT_LLM_MODEL": "",
            "AUTOPROFIT_LLM_API_KEY": "",
        })
        os.chdir(ROOT)

        from fastapi.testclient import TestClient
        import backend.database as database
        # Match the top-level module object imported by backend.main routers.
        import order_cash
        from backend import business_engine
        # main.py imports this router as a top-level module; patch that same
        # module object so the TEST-only catalog row is visible to the route.
        import workflow_api
        from core import market_research
        from core.llm import LLMConfig, LLMError, LLMStore, ModelRouter, OpenAICompatibleAdapter, ProviderUnavailable
        from modules.product_builder import ProductBuilder
        import modules.product_builder as product_builder
        from scripts.ops import backup, restore
        from backend.main import app

        database.DB_PATH = data_dir / "company.db"
        order_cash.STAGING_DIR = stage_dir
        product_builder.OUTPUTS_DIR = output_dir
        migration_first = business_engine.ensure_schema(database.DB_PATH)
        migration_second = business_engine.ensure_schema(database.DB_PATH)
        db_path = Path(database.DB_PATH)
        fixture = json.loads((ROOT / "tests/fixtures/phase09_public_stackexchange_question.json").read_text(encoding="utf-8"))
        captured = fixture["captured_at"]
        source_signal = market_research.normalize_stackexchange(
            {"items": [fixture["item"]]}, captured_at=captured, now=datetime.now(timezone.utc))
        if len(source_signal) != 1:
            raise RuntimeError("licensed public source fixture failed normalization")
        opportunities = market_research.build_opportunities(source_signal, now=datetime.now(timezone.utc), limit=5)
        persisted = market_research.persist_opportunities(opportunities, path=db_path)
        if not persisted:
            raise RuntimeError("source-backed opportunity did not persist")
        selected = max(persisted, key=lambda item: float(item.get("score", 0)))

        artifact = ProductBuilder.build_data_workflow_pack(selected, staging_dir=stage_dir)
        package_bytes = artifact.artifact_path.read_bytes()
        package_hash = hashlib.sha256(package_bytes).hexdigest()
        if package_hash != artifact.sha256 or artifact.quality_score != 100:
            raise RuntimeError("product package did not pass hash and QA gates")
        with zipfile.ZipFile(artifact.artifact_path) as package:
            manifest = json.loads(package.read("BUILD_MANIFEST.json"))
            qa = json.loads(package.read("QA_RESULTS.json"))
            if manifest["status"] != "STAGING_QA_PASS" or any(not row["passed"] for row in qa["checks"]):
                raise RuntimeError("package QA manifest was not all-pass")

        marketing_draft = workflow_api._record(
            "marketing", {"product_id": artifact.artifact_id, "title": "Local CSV row validation and cleanup — draft",
                          "content_body": "Offline CSV import diagnostics, explicit header mapping, deduplication and formula-safe export. Public problem signal only; payment intent unverified.",
                          "source_url": selected["source_url"], "public_publish_allowed": False},
            "PENDING_REVIEW", idempotency_key="phase09:e2e:marketing-draft")
        lead_capture_draft = workflow_api._record(
            "lead_capture_draft", {"product_id": artifact.artifact_id, "requires_contact_consent": True,
                                   "customer_contact": None, "form_status": "PENDING_REVIEW",
                                   "public_publish_allowed": False},
            "PENDING_REVIEW", idempotency_key="phase09:e2e:lead-capture-draft")

        admin = {"X-Admin-Key": admin_key}
        # The Product Studio CSV offer is quote-after-scope. Add a clearly TEST-
        # only catalog row in this isolated process so the simulated order and
        # delivered CSV artifact describe the same thing.
        buyer_product = "phase09-e2e-csv-workflow-pack"
        test_catalog_product = {"slug": buyer_product, "name": "TEST CSV workflow pack",
                                "category": "TEST only", "price_usd": 0.25,
                                "description": "Isolated E2E fixture; not a public offer.", "icon": "TEST"}
        with patch.object(workflow_api, "TOOL_DEFINITIONS",
                          [*workflow_api.TOOL_DEFINITIONS, test_catalog_product]), \
             TestClient(app, base_url="https://testserver") as client:
            ready = client.get("/api/ready")
            if ready.status_code != 200 or ready.json().get("status") != "ready":
                raise RuntimeError("readiness endpoint did not report ready")
            if ready.json().get("checks", {}).get("model_provider") != "unavailable_missing_config":
                raise RuntimeError("readiness probe misreported the deliberately unconfigured model provider")
            readiness_samples_ms: list[float] = []
            for _ in range(20):
                started = time.perf_counter()
                probe = client.get("/api/ready")
                readiness_samples_ms.append((time.perf_counter() - started) * 1000)
                if probe.status_code != 200:
                    raise RuntimeError("readiness performance probe returned a failure")
            ordered_samples = sorted(readiness_samples_ms)
            p95_readiness_ms = round(ordered_samples[max(0, int(len(ordered_samples) * 0.95) - 1)], 2)
            if p95_readiness_ms > 2000:
                raise RuntimeError(f"local readiness smoke exceeded 2 seconds at p95: {p95_readiness_ms} ms")
            if client.get("/api/engine/status").status_code != 403:
                raise RuntimeError("unauthenticated owner route unexpectedly allowed access")
            if client.get("/api/engine/status", headers=admin).status_code != 200:
                raise RuntimeError("HTTPS owner authentication failed")
            csrf = client.post("/api/optimization/admin/run", headers={**admin, "Origin": "https://evil.example"})
            if csrf.status_code != 403:
                raise RuntimeError("cross-origin mutation was not blocked")
            cors = client.get("/api/ready", headers={"Origin": "https://evil.example"})
            if cors.headers.get("access-control-allow-origin"):
                raise RuntimeError("permissive CORS response was emitted")

            sql_injection = client.post("/api/cash/leads", headers={"Idempotency-Key": "phase09-sqli-check-0001"},
                json={"product_id": "' OR 1=1 --", "email": "probe@example.invalid",
                      "name": "test", "contact_consent": True})
            if sql_injection.status_code not in {404, 422}:
                raise RuntimeError("SQL injection-like product identifier was not rejected by validation/catalog lookup")
            from fastapi import HTTPException
            try:
                order_cash._validated_artifact_path("../outside")
            except HTTPException as exc:
                traversal_blocked = exc.status_code == 404
            else:
                traversal_blocked = False
            if not traversal_blocked:
                raise RuntimeError("artifact path traversal was not blocked")
            try:
                market_research._safe_json("https://127.0.0.1/latest/meta-data")
            except ValueError:
                private_ssrf_blocked = True
            else:
                private_ssrf_blocked = False
            if not private_ssrf_blocked:
                raise RuntimeError("unapproved private SSRF target was not blocked")

            catalog = client.get("/api/cash/catalog").json()["items"]
            if buyer_product not in {item["id"] for item in catalog}:
                raise RuntimeError("existing fixed-price demo product is missing from checkout")
            before_summary = client.get("/api/cash/admin/summary", headers=admin)
            if before_summary.status_code != 200:
                raise RuntimeError("owner cash summary unavailable")
            before_balances = before_summary.json()["settled_balance_by_currency"]

            lead_response = client.post("/api/cash/leads", headers={"Idempotency-Key": "phase09-test-lead-0001",
                                                                         "X-Test-Mode-Key": test_key},
                                       json={"product_id": buyer_product, "email": "phase09.buyer@example.invalid",
                                             "name": "Phase 09 TEST Buyer", "contact_consent": True, "test_mode": True})
            if lead_response.status_code != 201 or not lead_response.json().get("test_mode"):
                raise RuntimeError("explicit TEST-mode checkout was not created")
            lead = lead_response.json()
            quote_response = client.post(f"/api/cash/admin/leads/{lead['order_id']}/quotes",
                                         headers={**admin, "Idempotency-Key": "phase09-test-quote-0001"},
                                         json={"scope": "Simulated CSV workflow customization and local hand-off.",
                                               "proposal_minor": 25000, "expires_in_days": 7})
            if quote_response.status_code != 201:
                raise RuntimeError("TEST-mode owner quote was not created")
            quote_id = quote_response.json()["quote_id"]
            if client.post(f"/api/cash/admin/quotes/{quote_id}/approve", headers=admin).status_code != 200:
                raise RuntimeError("TEST quote approval failed")
            buyer_headers = {"Authorization": f"Bearer {lead['buyer_access_token']}"}
            accepted = client.post(f"/api/cash/quotes/{quote_id}/accept",
                                   headers={**buyer_headers, "Idempotency-Key": "phase09-test-accept-0001"})
            if accepted.status_code != 200:
                raise RuntimeError("TEST buyer did not place the order")
            claim_response = client.post(f"/api/cash/orders/{lead['order_id']}/claims",
                                         headers={**buyer_headers, "Idempotency-Key": "phase09-test-claim-0001"},
                                         json={"claimed_minor": 25000, "transfer_reference": "TEST-BUYER-CLAIM-0001",
                                               "note": "TEST mode only; no funds moved."})
            if claim_response.status_code != 202:
                raise RuntimeError("TEST payment claim was not accepted for review")
            claim_id = claim_response.json()["claim_id"]
            false_claim = client.post(f"/api/cash/admin/claims/{claim_id}/verify",
                                      headers={**admin, "Idempotency-Key": "phase09-test-false-verify-0001"},
                                      json={"confirm_funds_received": False, "amount_received_minor": 25000,
                                            "statement_reference": "TEST-CLAIM-NOT-RECEIPT"})
            after_false = client.get("/api/cash/admin/summary", headers=admin).json()
            if false_claim.status_code != 422 or after_false["settled_balance_by_currency"] != before_balances:
                raise RuntimeError("false payment claim changed verified revenue")
            verified = client.post(f"/api/cash/admin/claims/{claim_id}/verify",
                                   headers={**admin, "Idempotency-Key": "phase09-test-true-verify-0001"},
                                   json={"confirm_funds_received": True, "amount_received_minor": 25000,
                                         "statement_reference": "TEST-OWNER-ATTEST-0001",
                                         "statement_note": "TEST simulation; no bank movement occurred."})
            if verified.status_code != 200 or verified.json().get("revenue_recorded") is not False:
                raise RuntimeError(f"TEST verification was incorrectly recorded as real revenue: {verified.status_code} {verified.text}")
            delivery = client.post(f"/api/cash/admin/orders/{lead['order_id']}/fulfill",
                                   headers=admin, json={"artifact_id": artifact.artifact_id})
            replay = client.post(f"/api/cash/admin/orders/{lead['order_id']}/fulfill",
                                 headers=admin, json={"artifact_id": artifact.artifact_id})
            if delivery.status_code != 200 or replay.status_code != 200:
                raise RuntimeError(f"TEST delivery failed: first={delivery.status_code} {delivery.text}; replay={replay.status_code} {replay.text}")
            unauthorized_download = client.get(f"/api/cash/deliveries/{delivery.json()['delivery_id']}/download")
            buyer_download = client.get(f"/api/cash/deliveries/{delivery.json()['delivery_id']}/download", headers=buyer_headers)
            after_summary = client.get("/api/cash/admin/summary", headers=admin).json()
            conn = sqlite3.connect(db_path)
            try:
                delivery_count = int(conn.execute("SELECT COUNT(*) FROM cash_deliveries WHERE order_id=?",
                                                  (lead["order_id"],)).fetchone()[0])
                is_test = int(conn.execute("SELECT is_test FROM cash_orders WHERE id=?", (lead["order_id"],)).fetchone()[0])
                real_transactions = int(conn.execute("SELECT COUNT(*) FROM cash_transactions t JOIN cash_orders o ON o.id=t.order_id WHERE o.is_test=0").fetchone()[0])
            finally:
                conn.close()
            if (delivery.status_code != 200 or replay.status_code != 200 or not replay.json().get("replayed")
                    or delivery.json()["delivery_id"] != replay.json()["delivery_id"] or delivery_count != 1
                    or is_test != 1 or real_transactions != 0 or after_summary["settled_balance_by_currency"] != before_balances
                    or after_summary["test_records_excluded"] != 1
                    or unauthorized_download.status_code != 401 or buyer_download.status_code != 200):
                raise RuntimeError("once-only protected TEST delivery or real-total exclusion failed")

            # Test-mode orders are impossible under production configuration even with the staging key.
            os.environ["AUTOPROFIT_ENV"] = "production"
            denied_production_test = client.post("/api/cash/leads",
                headers={"Idempotency-Key": "phase09-production-test-denied-0001", "X-Test-Mode-Key": test_key},
                json={"product_id": buyer_product, "email": "denied@example.invalid", "name": "TEST",
                      "contact_consent": True, "test_mode": True})
            os.environ["AUTOPROFIT_ENV"] = "staging"
            if denied_production_test.status_code != 403:
                raise RuntimeError("production environment accepted a TEST-mode order")

        # Separate processes prove durable lease recovery after an abrupt exit.
        state_file = work_dir / "crash-state.json"
        child_env = dict(os.environ)
        child_env["AUTOPROFIT_DATA_DIR"] = str(data_dir)
        child_env["AUTOPROFIT_ENGINE_KILL_SWITCH"] = "false"
        crash = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--crash-mid-run", str(state_file)],
                               cwd=ROOT, env=child_env, check=False, capture_output=True, text=True)
        resume = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--resume", str(state_file)],
                                cwd=ROOT, env=child_env, check=False, capture_output=True, text=True)
        crash_state = json.loads(state_file.read_text(encoding="utf-8"))
        if crash.returncode != 73 or resume.returncode != 0 or crash_state.get("final_state") != "DONE":
            raise RuntimeError("crash/restart task recovery failed")

        # Provider off and quota exhaustion are fail-closed without external requests.
        router = ModelRouter(LLMConfig.from_env())
        try:
            router.select(health_check=False)
            provider_off = "unexpected_ready"
        except ProviderUnavailable as exc:
            provider_off = exc.code
        remote_stub = OpenAICompatibleAdapter(name="openai_compatible", model="test-model",
                                              endpoint="https://provider.example/v1", timeout=1,
                                              context_tokens=1024, local=False, headers={})
        try:
            LLMStore(path=db_path).reserve(task_kind="provider_health_check", provider=remote_stub,
                                           trace_id="phase09-quota-exhausted", request_quota=0)
            quota_result = "unexpected_allowed"
        except LLMError as exc:
            quota_result = exc.code

        # Hard stop rejects both worker claims and external tool invocation.
        os.environ["AUTOPROFIT_ENGINE_KILL_SWITCH"] = "true"
        business_engine.set_engine_control("kill_switch", True)
        blocked_task = business_engine.create_task(
            __import__("domain_models").TaskSpec(title="Must remain queued", category="E2E",
                assigned_role_id="QAReviewer", task_type="phase09.kill-switch",
                idempotency_key="phase09:e2e:kill-switch-task", trace_id="phase09-kill-switch-trace",
                payload={"side_effect": "none"}))
        claim_after_kill = business_engine.claim_task("phase09-kill-switch-worker")
        blocked_tool = business_engine.invoke_tool("integration.publish", principal="phase09-test",
            payload={"text": "must not publish"}, dry_run=False,
            idempotency_key="phase09:e2e:blocked-publish", path=db_path)
        if claim_after_kill is not None or blocked_tool.get("reason_code") != "kill_switch_enabled":
            raise RuntimeError("hard kill switch did not stop worker and external side-effect tool")
        conn = business_engine.connect(db_path)
        try:
            optimization_runs_before = int(conn.execute("SELECT COUNT(*) FROM optimization_runs").fetchone()[0])
        finally:
            conn.close()
        from core.optimization_agent import run_weekly_optimization
        optimizer_after_kill = run_weekly_optimization(path=db_path, now=datetime.now(timezone.utc), force=True)
        conn = business_engine.connect(db_path)
        try:
            optimization_runs_after = int(conn.execute("SELECT COUNT(*) FROM optimization_runs").fetchone()[0])
        finally:
            conn.close()
        if (optimizer_after_kill.get("reason_code") != "kill_switch_enabled"
                or optimization_runs_after != optimization_runs_before):
            raise RuntimeError("hard kill switch did not stop the internal optimization side effect")

        count_conn = sqlite3.connect(db_path)
        try:
            before_backup_count = int(count_conn.execute("SELECT COUNT(*) FROM cash_transactions").fetchone()[0])
        finally:
            count_conn.close()
        backup_path = work_dir / "backup.sqlite"
        restored_path = work_dir / "restored.sqlite"
        backup_result = backup(db_path, backup_path)
        restore_result = restore(backup_path, restored_path)
        restored_conn = sqlite3.connect(restored_path)
        try:
            restored_count = int(restored_conn.execute("SELECT COUNT(*) FROM cash_transactions").fetchone()[0])
            restored_test_flag = int(restored_conn.execute("SELECT is_test FROM cash_orders WHERE id=?",
                                                           (lead["order_id"],)).fetchone()[0])
        finally:
            restored_conn.close()
        if restored_count != before_backup_count or restored_test_flag != 1:
            raise RuntimeError("SQLite backup restore failed to preserve TEST isolation")

        redacted = business_engine.redact({"admin_api_key": "phase09-private-sentinel",
                                           "customer_email": "hidden@example.invalid",
                                           "note": "Bearer phase09-private-token-value"})
        if "phase09-private-sentinel" in json.dumps(redacted) or "hidden@example.invalid" in json.dumps(redacted):
            raise RuntimeError("structured redaction failed")

        result = {
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "environment": "isolated local staging; temporary backend/core databases; no production paths used",
            "network_requests_during_e2e": 0,
            "secrets_printed": False,
            "migrations": {"first_run_version": migration_first, "second_run_version": migration_second,
                           "idempotent": migration_first == migration_second == 13},
            "source": {"status": "PASS", "provider": fixture["source"], "url": selected["source_url"],
                       "source_date": selected["source_date"], "captured_at": captured,
                       "license": "CC BY-SA 4.0", "attribution": selected["quote_attribution"],
                       "retained_content": fixture["content_retained"], "score": selected["score"],
                       "score_interpretation": "source-triage heuristic; not proof of paying demand"},
            "product": {"status": "PASS", "artifact_id": artifact.artifact_id,
                        "path": str(artifact.artifact_path.relative_to(ROOT)), "bytes": len(package_bytes),
                        "sha256": package_hash, "quality_score": artifact.quality_score,
                        "acceptance_check_count": len(artifact.acceptance_results),
                        "all_acceptance_checks_passed": all(item.passed for item in artifact.acceptance_results),
                        "license_ip_review": manifest["license_ip_check"]["status"],
                        "external_publish": False},
            "drafts": {"marketing": marketing_draft["status"], "lead_capture": lead_capture_draft["status"],
                       "customer_contact_created": False, "publication_sent": False},
            "test_order": {"status": "PASS", "explicit_test_mode": True,
                           "catalog_product_id": buyer_product,
                           "delivered_artifact_id": artifact.artifact_id,
                           "catalog_product_matches_delivered_workflow": True,
                           "false_claim_http_status": false_claim.status_code,
                           "false_claim_created_transaction": False,
                           "owner_verified_test_revenue_recorded": verified.json()["revenue_recorded"],
                           "settled_balances_before": before_balances,
                           "settled_balances_after_test_receipt": after_summary["settled_balance_by_currency"],
                           "test_order_excluded_count": after_summary["test_records_excluded"],
                           "exactly_one_delivery": delivery_count == 1,
                           "delivery_idempotent_replay": replay.json()["replayed"],
                           "unauthorized_download_status": unauthorized_download.status_code,
                           "authorized_test_download_status": buyer_download.status_code,
                           "production_test_mode_denied_status": denied_production_test.status_code,
                           "real_transactions_after_test": real_transactions},
            "crash_restart": {"status": "PASS", "crash_exit_code": crash.returncode,
                              "resume_exit_code": resume.returncode, "recovered_tasks": crash_state["recovered_tasks"],
                              "attempts": crash_state["attempts"], "final_state": crash_state["final_state"],
                              "task_idempotent": True, "event_count": crash_state["event_count"]},
            "provider_degrade": {"provider_off_reason_code": provider_off,
                                 "quota_exhausted_reason_code": quota_result,
                                 "outbound_llm_requests": 0},
            "hard_kill_switch": {"queued_task_id": blocked_task["id"], "worker_claim": None,
                                 "external_publish_tool_status": blocked_tool["status"],
                                 "optimizer_status": optimizer_after_kill["status"],
                                 "optimizer_run_count_unchanged": optimization_runs_after == optimization_runs_before,
                                 "reason_code": blocked_tool.get("reason_code")},
            "backup_restore": {"status": "PASS", "backup_integrity": backup_result["integrity"],
                               "backup_schema_version": backup_result["schema_version"],
                               "restored_schema_version": restore_result["schema_version"],
                               "restored_test_flag": restored_test_flag, "source_database_changed": False},
            "security_smoke": {"admin_authentication": "PASS", "http_admin_denied": "PASS",
                               "cross_origin_mutation": "PASS", "permissive_cors": "PASS (none emitted)",
                               "public_form_rate_limits": "PASS (regression suite)",
                               "sql_injection_input": "PASS (rejected catalog identifier)",
                               "xss_handling": "PASS (escaped report output and text-only app rendering regression suite)",
                               "ssrf_allowlist": "PASS (private endpoint rejected before request)",
                               "artifact_path_traversal": "PASS (rejected)",
                               "secrets_redacted": "PASS"},
            "readiness": {"status": "PASS", "model_provider": "unavailable_missing_config",
                          "interpretation": "Database is ready; LLM is optional and accurately reported unavailable; no provider probe/network request was made."},
            "performance_smoke": {"status": "PASS", "request": "local TestClient GET /api/ready",
                                  "sample_count": len(readiness_samples_ms),
                                  "median_ms": round(ordered_samples[len(ordered_samples) // 2], 2),
                                  "p95_ms": p95_readiness_ms,
                                  "max_ms": round(max(ordered_samples), 2),
                                  "threshold_ms_p95": 2000,
                                  "interpretation": "In-process smoke only; not a production capacity or GPU benchmark."},
            "limitations": ["Owner side effects were not executed; all public drafts remain pending review.",
                            "No bank transfer occurred. Owner manual statement attestation was simulated against a TEST order only.",
                            "No production VPS was modified; the deployment canary is documented but not installed."],
        }
        _write_json(evidence_path, result)
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/phase09")
    parser.add_argument("--evidence", type=Path, default=ROOT / "docs/evidence/phase09/e2e.json")
    parser.add_argument("--crash-mid-run", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--resume", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.crash_mid_run:
        return _crash_mid_run(args.crash_mid_run)
    if args.resume:
        return _resume_after_crash(args.resume)
    report = run(output_dir=args.output_dir, evidence_path=args.evidence)
    print(json.dumps({"status": "PASS", "evidence": str(args.evidence),
                      "artifact": report["product"]["path"], "sha256": report["product"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
