"""Phase 03 task-scoped agent runtime regression coverage."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))

import database  # noqa: E402
import business_engine as engine  # noqa: E402
from core import agent_runtime  # noqa: E402
from core.roles import ROLES  # noqa: E402


class AgentRuntimeTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="autoprofit-phase03-")
        self.db_path = Path(self.temp.name) / "backend" / "company.db"
        self.db_path.parent.mkdir(parents=True)
        database.DB_PATH = self.db_path
        database.init_db(self.db_path)
        engine.ensure_schema(self.db_path)
        engine.set_engine_control("kill_switch", False, path=self.db_path)
        engine.set_engine_control("paused", False, path=self.db_path)

    def tearDown(self):
        self.temp.cleanup()

    def issue_request(self, **overrides):
        fixture = json.loads((_ROOT / "tests" / "fixtures" / "phase03_public_problem.json").read_text(encoding="utf-8"))
        request = {
            "idempotency_key": f"phase03:{self._testMethodName}",
            "source": fixture["source"],
        }
        request.update(overrides)
        return request


class RegistryTests(AgentRuntimeTestCase):
    def test_all_fifty_logical_roles_map_once_without_fifty_model_instances(self):
        registry = agent_runtime.agent_registry()
        self.assertEqual(len(ROLES), 50)
        self.assertEqual(len(registry), 50)
        self.assertEqual({row["role_id"] for row in registry}, set(ROLES))
        not_implemented = {row["role_id"] for row in registry if row["readiness"] == "NOT_IMPLEMENTED"}
        self.assertEqual(not_implemented, {"DEV_CHROME_EXT_BUILDER", "DEV_SCRAPER_SPECIALIST",
                                           "DEV_TELEGRAM_BOT_CRAFTER", "OPS_VIETQR_ARCHITECT"})
        self.assertEqual(agent_runtime.runtime_profile()["max_active_inference_tasks"], 1)
        essentials = {"EXEC_ORCHESTRATOR", "EXEC_RISK_COMPLIANCE", "EXEC_ZERO_BUDGET",
                      "MKT_TREND_SCOUT", "MKT_COMPETITOR_ANALYST", "MKT_NICHE_EXPLORER",
                      "MKT_OFFER_STRATEGIST", "DEV_SOLUTION_ARCHITECT", "DEV_PYTHON_ENGINEER",
                      "EXEC_QA_DIRECTOR", "MKT_COPYWRITER", "MKT_KEYWORD_RESEARCHER",
                      "MKT_DISTRIBUTION_PLANNER", "MKT_EMAIL_OUTREACH_CRAFTER",
                      "OPS_REVENUE_BOOKKEEPER", "OPS_DELIVERY_DISPATCHER", "OPS_RESOURCE_OPTIMIZER"}
        self.assertTrue(all(agent_runtime.AGENT_REGISTRY[key].readiness.value == "READY" for key in essentials))


class WorkflowTests(AgentRuntimeTestCase):
    def test_five_cross_department_agents_build_a_tested_public_problem_draft(self):
        five_roles = ("MKT_TREND_SCOUT", "MKT_COMPETITOR_ANALYST", "DEV_SOLUTION_ARCHITECT",
                      "DEV_PYTHON_ENGINEER", "EXEC_QA_DIRECTOR")
        result = agent_runtime.run_public_problem_to_completion(self.issue_request(), role_ids=five_roles,
                                                                 path=self.db_path)
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(len(result["steps"]), 5)
        self.assertTrue(all(step["state"] == "DONE" for step in result["steps"]))
        by_role = {step["result"].get("role_id"): step["result"] for step in result["steps"]}
        self.assertEqual(by_role["DEV_PYTHON_ENGINEER"]["status"], "READY")
        self.assertEqual(by_role["EXEC_QA_DIRECTOR"]["result"]["test_status"], "PASS")
        artifact_id = by_role["DEV_PYTHON_ENGINEER"]["result"]["artifact_id"]
        artifact = engine.get_agent_artifact(artifact_id, path=self.db_path)
        self.assertEqual(artifact["status"], "DRAFT")
        self.assertEqual(artifact["source_ids"], [self.issue_request()["source"]["source_id"]])
        self.assertIn("def render_csv", artifact["content"])
        self.assertNotIn("comment to claim", by_role["MKT_TREND_SCOUT"]["result"]["acceptance_criteria"].lower())
        conn = engine.connect(self.db_path)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tool_invocations").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM agent_artifacts WHERE run_id=?", (result["id"],)).fetchone()[0], 1)
            self.assertGreaterEqual(conn.execute("SELECT COUNT(*) FROM task_events WHERE task_id IN (SELECT CAST(id AS TEXT) FROM tasks WHERE run_id=?)", (result["id"],)).fetchone()[0], 2 * len(result["steps"]))
        finally:
            conn.close()

    def test_dashboard_active_status_uses_canonical_live_lease_and_event(self):
        from backend import dashboard_data

        run = agent_runtime.start_public_problem_workflow(
            self.issue_request(), role_ids=("MKT_TREND_SCOUT",), path=self.db_path)
        task = engine.claim_task("phase03-dashboard-check", path=self.db_path, run_id=run["id"])
        self.assertIsNotNone(task)
        active = dashboard_data.active_agent_ids()
        self.assertEqual(active, {"MKT_TREND_SCOUT"})
        role_status = agent_runtime.agent_role_statuses(path=self.db_path)["MKT_TREND_SCOUT"]
        self.assertEqual(role_status["status"], "RUNNING")
        card = next(item for item in agent_runtime.dashboard_agent_registry(path=self.db_path)
                    if item["executor_role_id"] == "MKT_TREND_SCOUT")
        self.assertTrue(card["has_active_flow"])
        self.assertEqual(card["command_status"], "WORKING")

    def test_unavailable_required_llm_blocks_instead_of_fabricating(self):
        from core.llm import ProviderUnavailable
        request = self.issue_request(require_llm=True)
        with mock.patch.object(agent_runtime, "_local_model_router", side_effect=ProviderUnavailable("local_model_unavailable", "unavailable")):
            result = agent_runtime.run_public_problem_to_completion(request, path=self.db_path)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["steps"][0]["result"]["status"], "BLOCKED")
        self.assertEqual(result["steps"][0]["result"]["result"]["reason_code"], "local_model_unavailable")
        self.assertEqual(len(result["execution_outcomes"]), 1)

    def test_contradictory_public_claims_block_the_pipeline(self):
        source_b = {
            "source_id": "github:eyadstein/leaklens:issue:485",
            "uri": "https://github.com/eyadstein/leaklens/issues/485",
            "title": "A second public issue",
            "body": "Public issue snapshot.",
            "license": "MIT",
            "state": "open",
            "claims": {"issue_state": "closed"},
        }
        request = self.issue_request(additional_sources=[source_b])
        result = agent_runtime.run_public_problem_to_completion(request, path=self.db_path)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["steps"][1]["result"]["result"]["reason_code"], "contradictory_research")
        self.assertEqual(len(result["execution_outcomes"]), 2)

    def test_unsafe_side_effects_wait_for_owner_then_still_do_not_execute(self):
        request = self.issue_request(requested_side_effects=["external.contact"])
        waiting = agent_runtime.run_public_problem_to_completion(request, path=self.db_path)
        self.assertEqual(waiting["status"], "WAITING_APPROVAL")
        risk_task = waiting["steps"][1]
        self.assertEqual(risk_task["state"], "WAITING_APPROVAL")
        approved = engine.decide_task_approval(risk_task["id"], "APPROVED", path=self.db_path)
        self.assertEqual(approved["state"], "QUEUED")
        resumed = engine.run_worker_once("phase03-after-owner-approval", path=self.db_path, run_id=waiting["id"])
        self.assertEqual(resumed["state"], "BLOCKED")
        self.assertEqual(resumed["result"]["result"]["reason_code"], "side_effect_executor_not_implemented")
        conn = engine.connect(self.db_path)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tool_invocations").fetchone()[0], 0)
        finally:
            conn.close()

    def test_nonzero_cost_and_unreviewed_effect_pipeline_are_rejected_before_enqueue(self):
        with self.assertRaisesRegex(ValueError, "nonzero cash exposure"):
            agent_runtime.start_public_problem_workflow(self.issue_request(estimated_cost_vnd=1), path=self.db_path)
        with self.assertRaisesRegex(ValueError, "RiskCompliance handoff"):
            agent_runtime.start_public_problem_workflow(
                self.issue_request(requested_side_effects=["external.publish"]),
                role_ids=("MKT_TREND_SCOUT",), path=self.db_path)

    def test_malformed_handler_output_is_persistently_blocked(self):
        class Malformed:
            @staticmethod
            def run(_ctx):
                return {"status": "RUNNING", "untyped": object()}

        run = agent_runtime.start_public_problem_workflow(self.issue_request(), path=self.db_path)
        with mock.patch.dict(agent_runtime.HANDLERS, {"ExecutiveScheduler": Malformed}):
            outcome = engine.run_worker_once("phase03-malformed", path=self.db_path, run_id=run["id"])
        self.assertEqual(outcome["state"], "BLOCKED")
        self.assertEqual(outcome["result"]["status"], "BLOCKED")
        self.assertEqual(outcome["result"]["result"]["reason_code"], "agent_execution_error")
        current = engine.get_workflow_run(run["id"], path=self.db_path)
        self.assertEqual(current["status"], "BLOCKED")

    def test_source_cited_memory_expires_and_can_be_deleted(self):
        run_id = "run-memory-test"
        now = engine.utc_now()
        item_id = engine.save_agent_memory(run_id=run_id, namespace="test", source_id="source-a",
                                           source_uri="https://github.com/example/repo/issues/1",
                                           source_sha256="a" * 64, fact="Cited fact", ttl_days=1,
                                           path=self.db_path)
        self.assertEqual(len(engine.list_agent_memory("test", now=now, path=self.db_path)), 1)
        self.assertEqual(engine.list_agent_memory("test", now=now + timedelta(days=2), path=self.db_path), [])
        item_id = engine.save_agent_memory(run_id=run_id, namespace="test", source_id="source-b",
                                           source_uri="https://github.com/example/repo/issues/2",
                                           source_sha256="b" * 64, fact="Another cited fact", ttl_days=1,
                                           path=self.db_path)
        self.assertTrue(engine.delete_agent_memory(item_id, path=self.db_path))
        self.assertFalse(engine.delete_agent_memory(item_id, path=self.db_path))

    def test_payment_reconciliation_reads_claim_and_verified_ledgers_without_mutation(self):
        result = agent_runtime.PaymentReconciler.run({"db_path": str(self.db_path)})
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["verified_transaction_count"], 0)
        self.assertEqual(result["orphaned_payment_report_transactions"], 0)
        self.assertFalse(result["claims_mutated"])


class AgentApiTests(AgentRuntimeTestCase):
    def test_agent_admin_routes_require_https_and_admin_key(self):
        import main as backend_main
        from fastapi.testclient import TestClient

        api_key = "phase03-test-admin-key-" + "q" * 40
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = api_key
        secure = TestClient(backend_main.app, base_url="https://testserver")
        insecure = TestClient(backend_main.app, base_url="http://testserver")
        self.assertEqual(secure.get("/api/agents/registry").status_code, 403)
        headers = {"X-Admin-Key": api_key}
        registry = secure.get("/api/agents/registry", headers=headers)
        self.assertEqual(registry.status_code, 200, registry.text)
        self.assertEqual(registry.json()["logical_roles"], 50)
        self.assertEqual(insecure.get("/api/agents/status", headers=headers).status_code, 403)
        bad = secure.post("/api/agents/workflows", headers=headers, json={"source": {"url": "http://bad"}})
        self.assertEqual(bad.status_code, 422)
        self.assertIn("/api/agents/workflows/{run_id}", backend_main.app.openapi()["paths"])

    def test_valid_workflow_api_call_persists_owner_reviewable_run(self):
        import main as backend_main
        from fastapi.testclient import TestClient

        api_key = "phase03-create-admin-key-" + "r" * 40
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = api_key
        with mock.patch.dict(os.environ, {"AUTOPROFIT_ENGINE_WORKER": "false"}):
            client = TestClient(backend_main.app, base_url="https://testserver")
            headers = {"X-Admin-Key": api_key}
            response = client.post("/api/agents/workflows", headers=headers,
                                   json=self.issue_request(idempotency_key="phase03-api-create"))
            self.assertEqual(response.status_code, 202, response.text)
            run_id = response.json()["id"]
            detail = client.get(f"/api/agents/workflows/{run_id}", headers=headers)
            self.assertEqual(detail.status_code, 200, detail.text)
            self.assertEqual(detail.json()["status"], "QUEUED")
            self.assertEqual(len(detail.json()["steps"]), len(agent_runtime.DEFAULT_PIPELINE))
            public_dashboard = client.get("/api/dashboard")
            self.assertEqual(public_dashboard.status_code, 200)
            self.assertEqual(len(public_dashboard.json()["agents_registry"]), 9)
            self.assertNotIn("Extract the public problem and acceptance criteria", public_dashboard.text)
            owner_dashboard = client.get("/api/dashboard", headers=headers)
            self.assertIn("Extract the public problem and acceptance criteria", owner_dashboard.text)


if __name__ == "__main__":
    unittest.main()
