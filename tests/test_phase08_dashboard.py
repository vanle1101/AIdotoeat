"""Data-truth coverage for the Phase 08 owner dashboard aggregates."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import business_api  # noqa: E402
import business_engine  # noqa: E402
import dashboard_data  # noqa: E402
import database  # noqa: E402
import main as backend_main  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class Phase08DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phase08-dashboard-")
        self.db_path = Path(self.temp.name) / "company.db"
        self._previous_db_path = database.DB_PATH
        database.DB_PATH = self.db_path
        database.init_db()
        business_engine.ensure_schema(path=self.db_path)
        self.conn = business_engine.connect(self.db_path)

    def tearDown(self):
        self.conn.close()
        database.DB_PATH = self._previous_db_path
        self.temp.cleanup()

    def test_aggregate_reports_only_verified_cash_and_source_valid_opportunities(self):
        self.conn.execute(
            "INSERT INTO leads(id,name,email,stage,gtm_consent_status,gtm_suppressed) VALUES(1,'Private Buyer','buyer@example.test','QUALIFIED_INQUIRY','GRANTED',0)"
        )
        self.conn.execute(
            "INSERT INTO gtm_analytics_events(event_id,event_name,campaign_id,session_id,page_path,source,occurred_at,internal_test) "
            "VALUES('event-landing-0001','landing_view','website_snapshot_audit_v1','session-12345678901234567890123456789012','/offer','test','2026-11-08T12:00:00Z',0)"
        )
        self.conn.execute(
            "INSERT INTO cash_orders(id,state,customer_email,contact_consent,buyer_nonce,buyer_token_expires_at,trace_id,idempotency_key,idempotency_hash,created_at,updated_at) "
            "VALUES('order-1','FULFILLED','buyer@example.test',1,'nonce','2030-01-01T00:00:00Z','trace-1','idem-order-1','hash','2026-11-08T12:00:00Z','2026-11-08T12:00:00Z')"
        )
        self.conn.execute(
            "INSERT INTO cash_claims(id,order_id,claimed_minor,currency,status,payload_hash,idempotency_key,created_at,updated_at) "
            "VALUES('claim-1','order-1',250000,'VND','VERIFIED','hash','idem-claim-1','2026-11-08T12:01:00Z','2026-11-08T12:01:00Z')"
        )
        self.conn.execute(
            "INSERT INTO cash_transactions(id,order_id,claim_id,amount_minor,currency,payment_method,reference_scope,reference_normalized,assurance_level,provenance,verified_by,verified_at,idempotency_key,trace_id,created_at) "
            "VALUES('tx-1','order-1','claim-1',250000,'VND','BANK_TRANSFER','bank:owner','reference-1','OWNER_MANUAL_ATTESTATION','manual statement','owner','2026-11-08T12:02:00Z','idem-tx-1','trace-1','2026-11-08T12:02:00Z')"
        )
        self.conn.execute(
            "INSERT INTO cost_exposures(id,tool_name,provider,action,estimated_minor,currency,status,reason_code,trace_id,created_at) "
            "VALUES('exposure-1','remote_call','unknown','invoke',9900,'VND','BLOCKED','unknown-cost','trace-2','2026-11-08T12:03:00Z')"
        )
        valid_payload = {"id": "opp-valid", "title": "CSV cleanup request", "validation_status": "VALIDATED_BY_SOURCE",
                         "score": 72.5, "pain_point": "Teams need reliable CSV dedupe", "source_url": "https://example.test/issues/1",
                         "evidence_count": 1, "willingness_to_pay_hypothesis": "HYPOTHESIS: test a paid customization offer"}
        invalid_payload = {"id": "opp-template", "title": "Template only", "validation_status": "UNVALIDATED",
                           "score": 99, "source_url": "https://example.test/template"}
        for item_id, payload, status in (("opp-valid", valid_payload, "VALIDATED_BY_SOURCE"),
                                          ("opp-template", invalid_payload, "UNVALIDATED")):
            self.conn.execute(
                "INSERT INTO workflow_records(id,kind,status,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (item_id, "opportunity", status, json.dumps(payload), "2026-11-08T12:00:00Z", "2026-11-08T12:00:00Z"),
            )
        self.conn.commit()

        result = dashboard_data.dashboard_operations_summary(path=self.db_path)
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["executive"]["cash"]["settled_balance_by_currency"][0]["amount_minor"], 250000)
        self.assertEqual(result["executive"]["cash"]["assurance_label"], "OWNER_MANUAL_ATTESTATION")
        self.assertEqual(result["executive"]["cost_exposures"]["blocked_count"], 1)
        self.assertEqual([item["id"] for item in result["opportunity_lab"]["items"]], ["opp-valid"])
        self.assertEqual(result["agents"]["logical_roles"], 50)
        self.assertNotIn("buyer@example.test", serialized)
        self.assertNotIn("BANK_ACCOUNT", serialized)
        self.assertEqual(result["risk"]["duplicate_claim_attempts"]["status"], "not_instrumented")
        self.assertEqual(result["risk"]["unauthorized_attempts"]["status"], "not_instrumented")
        self.assertIsNone(result["risk"]["provider_quota"]["requests_today"])

    def test_task_cancel_route_is_owner_guarded_and_returns_canonical_state(self):
        app = FastAPI()
        app.include_router(business_api.router)
        client = TestClient(app, base_url="https://testserver")
        expected_key = "phase08-owner-test-key-" + "x" * 32
        previous_key = os.environ.get("AUTOPROFIT_ADMIN_API_KEY")
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = expected_key
        try:
            with patch.object(business_api.engine, "cancel_task", return_value={"state": "CANCELLED", "state_version": 3}) as cancel:
                response = client.post("/api/engine/tasks/17/cancel", headers={"X-Admin-Key": expected_key})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"task_id": 17, "state": "CANCELLED", "state_version": 3})
            cancel.assert_called_once_with(17)
            http_response = TestClient(app, base_url="http://testserver").post(
                "/api/engine/tasks/17/cancel", headers={"X-Admin-Key": expected_key}
            )
            self.assertEqual(http_response.status_code, 403)
        finally:
            if previous_key is None:
                os.environ.pop("AUTOPROFIT_ADMIN_API_KEY", None)
            else:
                os.environ["AUTOPROFIT_ADMIN_API_KEY"] = previous_key

    def test_operations_endpoint_requires_owner_key_and_https(self):
        client = TestClient(backend_main.app, base_url="https://testserver")
        http_client = TestClient(backend_main.app, base_url="http://testserver")
        key = "phase08-operations-test-key-" + "y" * 32
        previous_key = os.environ.get("AUTOPROFIT_ADMIN_API_KEY")
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = key
        try:
            self.assertEqual(client.get("/api/dashboard/operations").status_code, 403)
            self.assertEqual(http_client.get("/api/dashboard/operations", headers={"X-Admin-Key": key}).status_code, 403)
            self.assertEqual(client.get("/api/dashboard/operations", headers={"X-Admin-Key": key}).status_code, 200)
        finally:
            if previous_key is None:
                os.environ.pop("AUTOPROFIT_ADMIN_API_KEY", None)
            else:
                os.environ["AUTOPROFIT_ADMIN_API_KEY"] = previous_key

    def test_dashboard_uses_explicit_unknowns_and_does_not_fabricate_agent_chat(self):
        index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        core = (ROOT / "frontend" / "autoprofit-core.js").read_text(encoding="utf-8")
        dashboard = (ROOT / "frontend" / "reference-dashboard.js").read_text(encoding="utf-8")
        ops = (ROOT / "frontend" / "reference-ops-panels.js").read_text(encoding="utf-8")
        command_center = (ROOT / "frontend" / "reference-command-center.js").read_text(encoding="utf-8")
        self.assertNotIn('id="kpi-packaged-webapps-count" style="color:#fbbf24;">12 apps', index)
        self.assertNotIn("91.4%", core)
        self.assertNotIn("startup-client.io", core)
        self.assertNotIn("new EventSource", dashboard)
        self.assertIn("window.location.protocol !== 'https:'", dashboard)
        self.assertIn("value == null || value === ''", ops)
        self.assertIn("No verified data", ops)
        self.assertIn("if (!reducedMotion && activeTaskCount > 0)", command_center)
        self.assertIn("if ((!reducedMotion && activeTaskCount > 0) || cameraTransition) requestRender()", command_center)
        self.assertNotIn("animated.push({ kind: 'beacon'", command_center)



if __name__ == "__main__":
    unittest.main()
