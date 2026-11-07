"""Regression coverage for the Phase 00 security and integrity fixes.

The API app initializes its SQLite database and generated app files at import
time. Route tests redirect those paths into a temporary directory so neither
repository database nor existing generated files are touched.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


_repo_root = Path(__file__).resolve().parent.parent
_temporary_root = tempfile.TemporaryDirectory(prefix="autoprofit-phase00-")
_temporary_path = Path(_temporary_root.name)
os.environ["AUTOPROFIT_DATA_DIR"] = str(_temporary_path / "backend-data")
os.environ["AUTOPROFIT_APPS_DIR"] = str(_temporary_path / "generated-apps")
os.environ["AUTOPROFIT_ADMIN_API_KEY"] = "phase00-test-key-" + ("x" * 40)
os.environ["AUTOPROFIT_BUDGET_KILL_SWITCH"] = "false"
sys.path.insert(0, str(_repo_root / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import main as backend_main  # noqa: E402
import workflow_api  # noqa: E402
import apps_library  # noqa: E402
from core.budget_auditor import BudgetAuditor, BudgetViolationError  # noqa: E402
from database import get_connection  # noqa: E402
from modules.product_builder import ProductBuilder  # noqa: E402
from config import OwnerFinanceConfig  # noqa: E402


class TestFailClosedBudgetPolicy(unittest.TestCase):
    def test_registered_local_action_with_zero_cost_is_allowed(self):
        with mock.patch.dict(os.environ, {"AUTOPROFIT_BUDGET_KILL_SWITCH": "false"}):
            allowed, _ = BudgetAuditor.audit_action(
                "local.file_generation",
                {"provider": "offline_rule_based", "estimated_cost_vnd": 0,
                 "operation": ProductBuilder.build_chrome_extension},
            )
        self.assertTrue(allowed)

    def test_registry_not_caller_estimate_authorizes_zero_cost(self):
        with mock.patch.dict(os.environ, {"AUTOPROFIT_BUDGET_KILL_SWITCH": "false"}):
            allowed, _ = BudgetAuditor.audit_action(
                "local.file_generation",
                {"provider": "offline_rule_based", "operation": ProductBuilder.build_chrome_extension},
            )
        self.assertTrue(allowed)

    def test_zero_cost_claim_does_not_allow_unknown_action(self):
        with mock.patch.dict(os.environ, {"AUTOPROFIT_BUDGET_KILL_SWITCH": "false"}):
            with self.assertRaises(BudgetViolationError):
                BudgetAuditor.audit_action(
                    "unknown.paid_action",
                    {"provider": "offline_rule_based", "estimated_cost_vnd": 0},
                )

    def test_missing_cost_provider_and_unverified_free_tier_are_blocked(self):
        cases = [
            ("local.file_generation", {"provider": "offline_rule_based"}),
            ("local.file_generation", {"estimated_cost_vnd": 0,
                                        "operation": ProductBuilder.build_chrome_extension}),
            ("local.file_generation", {"provider": "groq_free", "estimated_cost_vnd": 0,
                                        "operation": ProductBuilder.build_chrome_extension}),
            ("local.file_generation", {"provider": "offline_rule_based", "estimated_cost_vnd": 0,
                                        "operation": lambda: None}),
        ]
        with mock.patch.dict(os.environ, {"AUTOPROFIT_BUDGET_KILL_SWITCH": "false"}):
            for action, parameters in cases:
                with self.subTest(action=action, parameters=parameters):
                    with self.assertRaises(BudgetViolationError):
                        BudgetAuditor.audit_action(action, parameters)

    def test_declared_local_action_cannot_wrap_an_unregistered_callable(self):
        with mock.patch.dict(os.environ, {"AUTOPROFIT_BUDGET_KILL_SWITCH": "false"}):
            with self.assertRaises(BudgetViolationError):
                BudgetAuditor.audit_action(
                    "local.file_generation",
                    {"provider": "offline_rule_based", "estimated_cost_vnd": 0,
                     "operation": lambda: __import__("urllib.request").request.urlopen("https://example.invalid")},
                )

    def test_paid_cost_and_kill_switch_block_actions(self):
        with mock.patch.dict(os.environ, {"AUTOPROFIT_BUDGET_KILL_SWITCH": "false"}):
            with self.assertRaises(BudgetViolationError):
                BudgetAuditor.audit_action(
                    "local.file_generation",
                    {"provider": "offline_rule_based", "estimated_cost_vnd": 1,
                     "operation": ProductBuilder.build_chrome_extension},
                )
        with mock.patch.dict(os.environ, {"AUTOPROFIT_BUDGET_KILL_SWITCH": "true"}):
            with self.assertRaises(BudgetViolationError):
                BudgetAuditor.audit_action(
                    "local.file_generation",
                    {"provider": "offline_rule_based", "estimated_cost_vnd": 0,
                     "operation": ProductBuilder.build_chrome_extension},
                )


class TestProtectedApiAndAbuseControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.https_client = TestClient(backend_main.app, base_url="https://testserver")
        cls.http_client = TestClient(backend_main.app, base_url="http://testserver")

    def setUp(self):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM request_rate_limits")
            conn.commit()
        finally:
            conn.close()

    def test_sensitive_admin_and_financial_routes_require_admin(self):
        routes = [
            ("GET", "/api/admin/payment-reports"),
            ("POST", "/api/admin/payment-reports/missing/verify"),
            ("GET", "/api/audit-logs"),
            ("GET", "/api/opportunities"),
            ("GET", "/api/marketing"),
            ("GET", "/api/employees"),
            ("GET", "/api/settings/budgets"),
            ("GET", "/api/payout-policies"),
            ("GET", "/api/pricing/history"),
            ("GET", "/api/pricing/recommendations"),
            ("GET", "/api/transactions"),
            ("GET", "/api/wallet/binance-usdt"),
            ("GET", "/api/orders"),
            ("GET", "/api/tasks"),
            ("GET", "/api/dashboard/activity"),
            ("GET", "/api/dashboard/activity/stream"),
            ("GET", "/api/dashboard/activity/1"),
            ("POST", "/api/github-web-factory/scan-and-build"),
            ("POST", "/api/github-web-factory/auto-harvest"),
            ("POST", "/api/marketing/generate/missing"),
            ("POST", "/api/employees/missing/approve"),
            ("POST", "/api/employees/missing/retire"),
            ("PUT", "/api/employees/missing/appearance"),
            ("POST", "/api/leads/auto-approve-all"),
            ("POST", "/api/leads/missing/approve-proposal"),
            ("POST", "/api/admin/advertising-inquiries/missing/verify"),
            ("POST", "/api/admin/donations/missing/verify"),
            ("POST", "/api/system/pause"),
            ("POST", "/api/system/resume"),
            ("POST", "/api/system/emergency-stop"),
            ("POST", "/api/agents/run-cycle"),
            ("POST", "/api/orders"),
            ("POST", "/api/tasks/missing/approve"),
            ("POST", "/api/public/aads-config"),
            ("PUT", "/api/settings/budgets"),
            ("PUT", "/api/payout-policies"),
            ("PUT", "/api/pricing/catalog/missing"),
            ("POST", "/api/pricing/recommendations/generate"),
            ("POST", "/api/pricing/recommendations/missing/review"),
        ]
        for method, path in routes:
            with self.subTest(path=path):
                response = self.https_client.request(
                    method, path, json={} if method != "GET" else None
                )
                self.assertIn(response.status_code, {401, 403})

    def test_admin_key_is_rejected_over_plain_http_and_accepted_over_https(self):
        headers = {"X-Admin-Key": os.environ["AUTOPROFIT_ADMIN_API_KEY"]}
        self.assertEqual(self.http_client.get("/api/admin/payment-reports", headers=headers).status_code, 403)
        self.assertEqual(self.https_client.get("/api/admin/payment-reports", headers=headers).status_code, 200)

    def test_frontend_never_sends_admin_key_from_plain_http(self):
        core_js = (_repo_root / "frontend" / "autoprofit-core.js").read_text(encoding="utf-8")
        dashboard_js = (_repo_root / "frontend" / "reference-dashboard.js").read_text(encoding="utf-8")
        scene_js = (_repo_root / "frontend" / "autoprofit-3d.js").read_text(encoding="utf-8")
        self.assertTrue("function isSecureAdminOrigin(targetBase = API_BASE)" in core_js, "Secure-origin guard is missing")
        self.assertTrue("window.location.protocol !== 'https:'" in core_js, "Admin transport must require HTTPS")
        self.assertTrue("target.origin === window.location.origin" in core_js, "Admin key must stay same-origin")
        self.assertTrue("getAdminHeaders(Boolean(options.body), options.headers || {}, targetBase)" in core_js,
                        "The API target must be checked before attaching the admin key")
        self.assertNotIn("admin_key: entered.trim()", core_js)
        self.assertTrue("window.location.protocol === 'https:'" in dashboard_js, "Dashboard details must not send keys over HTTP")
        self.assertFalse("window.__verifyOwnerPinHash(pin)" in scene_js, "Client-only PIN unlock must not authorize admin UI")

    def test_direct_backend_entrypoint_uses_loopback_8450(self):
        main_source = (_repo_root / "backend" / "main.py").read_text(encoding="utf-8")
        self.assertTrue(
            'uvicorn.run("main:app", host="127.0.0.1", port=8450, reload=False)' in main_source,
            "Direct backend startup must stay on the internal service port",
        )

    def test_cross_origin_public_mutation_is_rejected(self):
        response = self.https_client.post(
            "/api/public/notebook/interact",
            headers={"Origin": "https://attacker.invalid"},
            json={"question": "hello"},
        )
        self.assertEqual(response.status_code, 403)

    def test_public_form_rate_limit_is_enforced(self):
        responses = [
            self.https_client.post("/api/public/notebook/interact", json={"question": "hello"})
            for _ in range(35)
        ]
        self.assertTrue(any(response.status_code == 429 for response in responses))

    def test_public_employee_proposals_are_limited_and_cannot_auto_approve(self):
        payload = {"role_code": "TEST_ROLE", "full_name_vi": "Test Owner Review",
                   "job_title_vi": "Test proposal"}
        for _ in range(11):
            response = self.https_client.post("/api/employees/propose", json=payload)
        self.assertEqual(response.status_code, 429)

        conn = get_connection()
        try:
            conn.execute("DELETE FROM request_rate_limits")
            conn.commit()
        finally:
            conn.close()
        payload["auto_approve"] = True
        response = self.https_client.post("/api/employees/propose", json=payload)
        self.assertEqual(response.status_code, 403)

    def test_internal_test_telemetry_is_ignored(self):
        session_id = "123e4567-e89b-42d3-a456-426614174001"
        response = self.https_client.post(
            "/api/telemetry/pageview",
            json={"session_id": session_id, "path": "/?internal_test=1", "internal_test": True},
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "internal_test_ignored")
        conn = get_connection()
        try:
            self.assertIsNone(conn.execute(
                "SELECT 1 FROM telemetry_sessions WHERE session_id=?", (session_id,)
            ).fetchone())
        finally:
            conn.close()

    def test_payment_mutations_cannot_be_called_without_admin(self):
        cases = [
            ("POST", "/api/payments/verify-mbbank-tx", {"order_id": "missing", "statement_reference": "test-1234"}),
            ("POST", "/api/payments/verify-bsc-tx", {"order_id": "missing", "tx_hash": "0x" + "a" * 64}),
            ("POST", "/api/admin/payment-reports/missing/verify", {"reference": "test-1234"}),
            ("POST", "/api/system/emergency-stop", {"reason": "test"}),
        ]
        for method, path, payload in cases:
            with self.subTest(path=path):
                response = self.https_client.request(method, path, json=payload)
                self.assertIn(response.status_code, {401, 403})

    def test_public_dashboard_does_not_expose_verified_revenue(self):
        snapshot = {
            "status": "ok",
            "metrics": {"revenue_usd": {"value_usd": 123.45, "status": "observed"}},
        }
        with mock.patch.object(backend_main, "dashboard_summary", return_value=snapshot):
            response = self.https_client.get("/api/dashboard/summary?window=today")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["metrics"]["revenue_usd"]["value_usd"])

    def test_llm_token_ledger_reads_only_real_usage_rows(self):
        import business_engine as engine
        engine.ensure_schema()
        conn = engine.connect()
        try:
            conn.execute("DELETE FROM llm_usage")
            conn.execute(
                """INSERT INTO llm_usage(task_kind,provider,model,prompt_tokens,completion_tokens,latency_ms,
                   status,confidence_estimate,confidence_label,trace_id,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                ("niche_classification", "ollama_local", "test-model", 23, 11, 87,
                 "SUCCESS", 0.6, "model_estimate_unvalidated", "trace-test",
                 "2026-11-08T00:00:00Z"),
            )
            conn.commit()
        finally:
            conn.close()
        response = self.https_client.get("/api/llm/token-ledger?limit=25")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["source"], "canonical_llm_usage_ledger")
        self.assertEqual(data["summary"]["total_requests"], 1)
        self.assertEqual(data["recent_calls"][0]["prompt_tokens"], 23)
        self.assertEqual(data["recent_calls"][0]["total_tokens"], 34)
        self.assertNotIn("prompt_text", data["recent_calls"][0])
        self.assertNotIn("response_text", data["recent_calls"][0])

    def test_public_owner_record_lists_return_no_private_records_without_admin(self):
        for path in ("/api/public/donations", "/api/public/advertising-inquiries", "/api/leads"):
            with self.subTest(path=path):
                response = self.https_client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["items"], [])
                self.assertIsNone(response.json()["total"])

    def test_legacy_dashboard_does_not_expose_verified_revenue(self):
        snapshot = {
            "status": "ok",
            "metrics": {"revenue_usd": {"value_usd": 9876.5, "status": "observed"}},
        }
        with mock.patch.object(backend_main, "dashboard_summary", return_value=snapshot):
            response = self.https_client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["kpis_real_verified"]["verified_revenue_usd"])
        self.assertIsNone(response.json()["dashboard_data"]["metrics"]["revenue_usd"]["value_usd"])

    def test_financial_configuration_rejects_private_rpc_and_invalid_owner_values(self):
        with self.assertRaises(ValueError):
            OwnerFinanceConfig(BSC_RPC_URL="https://127.0.0.1/rpc")
        with self.assertRaises(ValueError):
            OwnerFinanceConfig(BANK_NAME="MB", BANK_ACCOUNT_NO="123", BANK_ACCOUNT_NAME="Owner")
        env_example = (_repo_root / ".env.example").read_text(encoding="utf-8")
        self.assertRegex(env_example, r"(?m)^AUTOPROFIT_BANK_ACCOUNT_NO=$")
        self.assertRegex(env_example, r"(?m)^AUTOPROFIT_BINANCE_PAY_ID=$")

    def test_retired_worker_has_no_traffic_behavior(self):
        import threading
        import traffic_worker

        stop_event = threading.Event()
        stop_event.set()
        self.assertFalse(traffic_worker.run_traffic_cycle(stop_event))

        autosurf = (_repo_root / "frontend" / "autosurf.html").read_text(encoding="utf-8").lower()
        youtube = (_repo_root / "frontend" / "youtube-booster.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("acceptable.a-ads.com", autosurf)
        self.assertNotIn("youtube.com/embed", youtube)
        self.assertNotIn("autoplay", youtube)

    def test_no_prefilled_live_revenue_or_app_rating_claims(self):
        index = (_repo_root / "frontend" / "index.html").read_text(encoding="utf-8")
        library = (_repo_root / "backend" / "apps_library.py").read_text(encoding="utf-8")
        self.assertNotIn("$12.286", index)
        self.assertNotIn("65.704 views", index)
        self.assertNotIn('"stars":', library)
        core = (_repo_root / "frontend" / "autoprofit-core.js").read_text(encoding="utf-8")
        self.assertNotIn("realImps = realViews * 2", core)
        self.assertNotIn("TOP #${idx + 1} ĂN QUẢNG CÁO", core)
        self.assertNotIn("watch-to-earn.html", core)
        self.assertNotIn("LOCAL_OWNER_VERIFIED", core)
        scene = (_repo_root / "frontend" / "autoprofit-3d.js").read_text(encoding="utf-8")
        self.assertNotIn("3314", scene)
        self.assertNotIn("statVisitorsToday')?.textContent?.trim() || '446", scene)
        self.assertNotIn('"completed_count":', core)
        self.assertIn("const formatFinanceValue", core)
        self.assertIn("if (value === null || value === undefined || value === '') return null", core)
        self.assertIn("No verified data", core)
        telemetry = (_repo_root / "frontend" / "site-telemetry.js").read_text(encoding="utf-8")
        self.assertIn("internal_test", telemetry)
        self.assertIn("navigator.webdriver", telemetry)
        scene = (_repo_root / "frontend" / "autoprofit-3d.js").read_text(encoding="utf-8")
        self.assertNotIn("isOffline = false; STATE.online = true", scene)
        self.assertIn("Backend connected; AI runtime is idle.", scene)
        self.assertIn("is_demo_profile: !hasVerifiedRegistry", core)

    def test_youtube_automation_is_removed_but_manual_seo_remains(self):
        index = (_repo_root / "frontend" / "index.html").read_text(encoding="utf-8")
        scene = (_repo_root / "frontend" / "autoprofit-3d.js").read_text(encoding="utf-8")
        core = (_repo_root / "frontend" / "autoprofit-core.js").read_text(encoding="utf-8")
        self.assertFalse("requestLaunchYoutubeCampaignWithPaymentGate()" in index,
                         "The UI must not expose a YouTube campaign launcher")
        self.assertFalse("28–64 luồng song song" in index, "Unverified view capacity must not be shown")
        self.assertFalse("1.045+ Web App" in index, "Unverified automated campaign distribution must not be shown")
        self.assertFalse("AUTONOMOUS_HR_NEW_RECRUITS_POOL" in scene,
                         "Synthetic live workforce profiles must not remain in the scene")
        self.assertTrue("analyzeYoutubeSeoAndThumbnails()" in index,
                        "The manual metadata and thumbnail analyzer should remain available")
        self.assertTrue("Affiliate examples only" in index,
                        "Unverified affiliate activity must be labeled as examples")
        for retired_role in ("YOUTUBE_TRAFFIC_AGENT", "YOUTUBE_MULTILANG_SEO_AGENT",
                             "YOUTUBE_RETENTION_AGENT", "YOUTUBE_SHORTS_HOOK_AGENT"):
            self.assertNotIn(retired_role, scene)
            self.assertNotIn(retired_role, core)

    def test_monetized_bridge_clicks_and_unverified_affiliate_counters_are_removed(self):
        index = (_repo_root / "frontend" / "index.html").read_text(encoding="utf-8")
        scene = (_repo_root / "frontend" / "autoprofit-3d.js").read_text(encoding="utf-8")
        core = (_repo_root / "frontend" / "autoprofit-core.js").read_text(encoding="utf-8")
        self.assertNotIn("/go/bridge.html", index,
                         "Affiliate article links must not pass through an ad-impression bridge")
        self.assertNotIn("clicksCount", scene,
                         "Unverified browser-local affiliate click counts must not be presented")
        self.assertNotIn("Rạp Chiếu 30 Giây", index)
        self.assertNotIn("WatchTime 30s", scene + core)
        youtube = (_repo_root / "frontend" / "youtube-booster.html").read_text(encoding="utf-8").lower()
        self.assertIn("đã tắt", youtube)
        self.assertNotIn("youtube.com/embed", youtube)

    def test_generated_apps_never_embed_owner_payment_destinations(self):
        test_config = OwnerFinanceConfig(
            BANK_NAME="MB", BANK_ACCOUNT_NO="111111", BANK_ACCOUNT_NAME="Demo Owner",
            BINANCE_ID="87654321",
        )
        with mock.patch.object(apps_library, "CONFIG", test_config):
            html = apps_library.generate_tool_html(apps_library.TOOL_DEFINITIONS[0])
        self.assertFalse("Demo Owner" in html, "Owner name leaked into generated public HTML")
        self.assertFalse("111111" in html, "Owner bank account leaked into generated public HTML")
        self.assertFalse("87654321" in html, "Owner payment ID leaked into generated public HTML")
        self.assertTrue("Thanh toán chưa được cấu hình" in html,
                        "Standalone app checkout should stay disabled without a safe payment flow")

    def test_unconnected_runtime_is_not_reported_as_running(self):
        workflow_api._set_system_status("RUNNING")
        response = self.https_client.get("/api/dashboard")
        self.assertEqual(response.json()["system"]["system_status"], "IDLE")

    def test_bank_proof_cannot_be_replaced_after_submission(self):
        order_id = "phase00-proof-order"
        workflow_api._record(
            "order",
            {"net_amount_vnd": 100_000, "net_amount_usd": 4.0, "order_number": "TEST-ORDER"},
            "PENDING_PAYMENT",
            order_id,
        )
        first = self.https_client.post(
            "/api/payments/submit-mbbank-proof",
            json={"order_id": order_id, "bank_tx_ref": "bank-ref-0001", "amount_vnd": 100_000},
        )
        second = self.https_client.post(
            "/api/payments/submit-mbbank-proof",
            json={"order_id": order_id, "bank_tx_ref": "bank-ref-0002", "amount_vnd": 100_000},
        )
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 409)

    def test_public_bsc_payment_cannot_reuse_a_transaction(self):
        product = workflow_api._products()[0]
        tx_hash = "0x" + ("a" * 64)
        with mock.patch.object(workflow_api, "_verify_bsc_receipt", side_effect=lambda _tx, amount: amount):
            first = self.https_client.post(
                "/api/public/orders/verify-bsc-tx",
                json={"item_slug": product["slug"], "buyer_email": "buyer@example.test", "tx_hash": tx_hash},
            )
            second = self.https_client.post(
                "/api/public/orders/verify-bsc-tx",
                json={"item_slug": product["slug"], "buyer_email": "buyer@example.test", "tx_hash": tx_hash},
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)


if __name__ == "__main__":
    unittest.main()
