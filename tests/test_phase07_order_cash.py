"""Phase 07 staging E2E: buyer-to-cash under an isolated SQLite ledger."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import business_engine  # noqa: E402
import database  # noqa: E402
import order_cash  # noqa: E402
import workflow_api  # noqa: E402
from config import OwnerFinanceConfig  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class OrderCashE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="phase07-cash-")
        cls.root = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.db_path = self.root / f"buyer-{uuid.uuid4().hex}.sqlite"
        self.app_dir = self.root / f"apps-{uuid.uuid4().hex}"
        self.app_dir.mkdir()
        self.staging = self.root / f"staging-{uuid.uuid4().hex}"
        self.staging.mkdir()
        self.artifact_id = "staging-package-test-v1"
        artifact_path = self.staging / f"{self.artifact_id}.zip"
        package_file = b"README staging package"
        manifest = {"product_id": self.artifact_id, "status": "STAGING_QA_PASS", "quality_score": 100,
                    "files": {"README.md": __import__("hashlib").sha256(package_file).hexdigest()}}
        with zipfile.ZipFile(artifact_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("README.md", package_file)
            archive.writestr("BUILD_MANIFEST.json", json.dumps(manifest))
        digest = __import__("hashlib").sha256(artifact_path.read_bytes()).hexdigest()
        artifact_path.with_suffix(".zip.sha256").write_text(f"{digest}  {artifact_path.name}\n", encoding="ascii")
        database.init_db(self.db_path)
        self.assertEqual(business_engine.ensure_schema(self.db_path), 13)
        self.original_connection = order_cash.get_connection
        self.original_workflow_connection = workflow_api.get_connection
        self.original_staging_dir = order_cash.STAGING_DIR
        self.original_config = order_cash.CONFIG
        self.original_secret = os.environ.get("AUTOPROFIT_ORDER_TOKEN_SECRET")
        self.original_admin = os.environ.get("AUTOPROFIT_ADMIN_API_KEY")
        self.admin_key = "phase07-admin-key-" + "q" * 40
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = self.admin_key
        os.environ["AUTOPROFIT_ORDER_TOKEN_SECRET"] = "phase07-token-secret-" + "x" * 40
        order_cash.get_connection = lambda: database.get_connection(self.db_path)
        workflow_api.get_connection = lambda: database.get_connection(self.db_path)
        product = workflow_api._products()[0]
        order_cash.STAGING_DIR = self.staging
        order_cash.CONFIG = OwnerFinanceConfig(BANK_NAME="MB", BANK_ACCOUNT_NO="1234567890",
                                               BANK_ACCOUNT_NAME="DEMO OWNER")
        self.app = FastAPI()

        @self.app.middleware("http")
        async def same_origin_mutation_guard(request, call_next):
            origin = request.headers.get("origin")
            if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                if parsed.scheme != request.url.scheme or parsed.netloc.lower() != request.headers.get("host", "").lower():
                    from fastapi.responses import JSONResponse
                    return JSONResponse(status_code=403, content={"detail": "Cross-origin mutation denied"})
            return await call_next(request)

        self.app.include_router(order_cash.router)
        self.client = TestClient(self.app, base_url="https://cash.test")
        self.product = product

    def tearDown(self):
        order_cash.get_connection = self.original_connection
        workflow_api.get_connection = self.original_workflow_connection
        order_cash.STAGING_DIR = self.original_staging_dir
        order_cash.CONFIG = self.original_config
        if self.original_secret is None:
            os.environ.pop("AUTOPROFIT_ORDER_TOKEN_SECRET", None)
        else:
            os.environ["AUTOPROFIT_ORDER_TOKEN_SECRET"] = self.original_secret
        if self.original_admin is None:
            os.environ.pop("AUTOPROFIT_ADMIN_API_KEY", None)
        else:
            os.environ["AUTOPROFIT_ADMIN_API_KEY"] = self.original_admin
        for file in (self.db_path, Path(str(self.db_path) + "-wal"), Path(str(self.db_path) + "-shm")):
            if file.exists():
                file.unlink()

    @property
    def admin_headers(self):
        return {"X-Admin-Key": self.admin_key}

    def buyer_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def lead(self, *, suffix="one", idempotency=None):
        result = self.client.post("/api/cash/leads", headers={"Idempotency-Key": idempotency or f"lead-{suffix}-0001"}, json={
            "product_id": self.product["id"], "email": f"buyer-{suffix}@example.test", "name": "Buyer",
            "contact_consent": True,
        })
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()

    def setup_awaiting_payment(self, *, suffix="one", amount=150_000):
        lead = self.lead(suffix=suffix)
        admin = self.admin_headers
        quote_response = self.client.post(f"/api/cash/admin/leads/{lead['order_id']}/quotes",
            headers={**admin, "Idempotency-Key": f"quote-{suffix}-0001"},
            json={"scope": "Deliver the agreed product customization and a documented install package.",
                  "proposal_minor": amount, "expires_in_days": 7})
        self.assertEqual(quote_response.status_code, 201, quote_response.text)
        quote_id = quote_response.json()["quote_id"]
        approved = self.client.post(f"/api/cash/admin/quotes/{quote_id}/approve", headers=admin)
        self.assertEqual(approved.status_code, 200, approved.text)
        buyer = self.buyer_headers(lead["buyer_access_token"])
        accepted = self.client.post(f"/api/cash/quotes/{quote_id}/accept",
                                    headers={**buyer, "Idempotency-Key": f"accept-{suffix}-0001"})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        return {**lead, "quote_id": quote_id, "buyer_headers": buyer, "order_number": accepted.json()["order_number"]}

    def claim(self, order, amount, reference, suffix):
        response = self.client.post(f"/api/cash/orders/{order['order_id']}/claims",
            headers={**order["buyer_headers"], "Idempotency-Key": f"claim-{suffix}-0001"},
            json={"claimed_minor": amount, "transfer_reference": reference, "note": "Transfer sent"})
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()["claim_id"]

    def verify(self, claim_id, amount, reference, key):
        return self.client.post(f"/api/cash/admin/claims/{claim_id}/verify",
            headers={**self.admin_headers, "Idempotency-Key": key},
            json={"confirm_funds_received": True, "amount_received_minor": amount,
                  "statement_reference": reference, "statement_note": "Seen on receiving account statement."})

    def test_staging_buyer_manual_attestation_partial_payments_once_delivery_refund_and_restore(self):
        order = self.setup_awaiting_payment()
        buyer = order["buyer_headers"]

        unauthorized = self.client.get(f"/api/cash/orders/{order['order_id']}")
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(self.client.get(f"/api/cash/orders/{order['order_id']}", headers={"Authorization": "Bearer wrong"}).status_code, 404)
        self.assertNotIn("1234567890", self.client.get("/api/cash/catalog").text)
        instructions = self.client.get(f"/api/cash/orders/{order['order_id']}/payment-instructions", headers=buyer)
        self.assertEqual(instructions.status_code, 200, instructions.text)
        self.assertIn("1234567890", instructions.text)
        self.assertIn("not proof", instructions.text)

        first_claim = self.claim(order, 100_000, "buyer-ref-0001", "one-a")
        failed = self.client.post(f"/api/cash/admin/claims/{first_claim}/verify",
            headers={**self.admin_headers, "Idempotency-Key": "failed-verify-01"},
            json={"confirm_funds_received": False, "amount_received_minor": 100_000,
                  "statement_reference": "statement-fail-0001"})
        self.assertEqual(failed.status_code, 422)
        wrong_amount = self.verify(first_claim, 99_999, "statement-amount-0001", "wrong-amount-01")
        self.assertEqual(wrong_amount.status_code, 409)

        first = self.verify(first_claim, 100_000, "statement-ref-0001", "verify-one-a-0001")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["state"], "AWAITING_PAYMENT")
        self.assertEqual(first.json()["assurance_level"], "OWNER_MANUAL_ATTESTATION")
        partial_instructions = self.client.get(f"/api/cash/orders/{order['order_id']}/payment-instructions", headers=buyer)
        self.assertEqual(partial_instructions.json()["amount"]["amount_minor"], 50_000)
        replay = self.verify(first_claim, 100_000, "statement-ref-0001", "verify-one-a-0001")
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(first.json()["transaction_id"], replay.json()["transaction_id"])
        changed_retry = self.verify(first_claim, 100_000, "different-statement-0001", "verify-one-a-0001")
        self.assertEqual(changed_retry.status_code, 409)

        second_claim = self.claim(order, 50_000, "buyer-ref-0002", "one-b")
        second = self.verify(second_claim, 50_000, "statement-ref-0002", "verify-one-b-0001")
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["state"], "VERIFIED")
        transactions = self.client.get(f"/api/cash/admin/orders/{order['order_id']}/transactions", headers=self.admin_headers)
        self.assertEqual(transactions.status_code, 200)
        self.assertEqual(len(transactions.json()["receipts"]), 2)
        self.assertEqual(transactions.json()["receipts"][0]["assurance_level"], "OWNER_MANUAL_ATTESTATION")

        fulfill_payload = {"artifact_id": self.artifact_id}
        fulfilled = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/fulfill", headers=self.admin_headers, json=fulfill_payload)
        fulfilled_again = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/fulfill", headers=self.admin_headers, json=fulfill_payload)
        self.assertEqual(fulfilled.status_code, 200, fulfilled.text)
        self.assertEqual(fulfilled.json()["delivery_id"], fulfilled_again.json()["delivery_id"])
        self.assertTrue(fulfilled_again.json()["replayed"])
        different_artifact_retry = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/fulfill",
            headers=self.admin_headers, json={"artifact_id": "different-package-v2"})
        self.assertEqual(different_artifact_retry.status_code, 409)
        conn = database.get_connection(self.db_path)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_deliveries WHERE order_id=?", (order["order_id"],)).fetchone()[0], 1)
        finally:
            conn.close()

        delivery_id = fulfilled.json()["delivery_id"]
        blocked = self.client.get(f"/api/cash/deliveries/{delivery_id}/download")
        self.assertEqual(blocked.status_code, 401)
        downloaded = self.client.get(f"/api/cash/deliveries/{delivery_id}/download", headers=buyer)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.headers["content-type"], "application/zip")
        with zipfile.ZipFile(__import__("io").BytesIO(downloaded.content)) as archive:
            self.assertIn("README.md", archive.namelist())
        with patch.object(order_cash, "_now", return_value=datetime.now(timezone.utc) + timedelta(days=8)):
            expired = self.client.get(f"/api/cash/deliveries/{delivery_id}/download", headers=buyer)
        self.assertEqual(expired.status_code, 410)

        duplicate_order = self.setup_awaiting_payment(suffix="two", amount=100_000)
        duplicate_claim = self.claim(duplicate_order, 100_000, "buyer-other-0001", "two")
        duplicate_report = self.verify(duplicate_claim, 100_000, "statement-ref-0001", "verify-two-0001")
        self.assertEqual(duplicate_report.status_code, 409)

        refund = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/refund",
            headers={**self.admin_headers, "Idempotency-Key": "refund-one-0001"},
            json={"amount_minor": 25_000, "transfer_reference": "refund-ref-0001", "reason": "Buyer cancellation refund."})
        self.assertEqual(refund.status_code, 200, refund.text)
        self.assertEqual(refund.json()["state"], "REFUNDED")
        self.assertEqual(refund.json()["settled_balance"]["amount_minor"], 125_000)
        conflicting_refund_retry = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/refund",
            headers={**self.admin_headers, "Idempotency-Key": "refund-one-0001"},
            json={"amount_minor": 24_000, "transfer_reference": "refund-ref-0001", "reason": "Different amount."})
        self.assertEqual(conflicting_refund_retry.status_code, 409)

        reference_collision_order = self.setup_awaiting_payment(suffix="reference-collision", amount=10_000)
        collision_claim = self.claim(reference_collision_order, 10_000, "buyer-collision-0001", "collision")
        collision = self.verify(collision_claim, 10_000, "refund-ref-0001", "verify-collision-0001")
        self.assertEqual(collision.status_code, 409)
        revoked = self.client.get(f"/api/cash/deliveries/{delivery_id}/download", headers=buyer)
        self.assertEqual(revoked.status_code, 410)

        summary = self.client.get("/api/cash/admin/summary", headers=self.admin_headers)
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["settled_balance_by_currency"], [{
            "currency": "VND", "amount_minor": 125_000, "label": "VERIFIED_RECEIPTS_LESS_REFUNDS_AND_CHARGEBACKS"}])
        self.assertEqual(summary.json()["assurance_label"], "OWNER_MANUAL_ATTESTATION")
        self.assertEqual(summary.json()["fx_conversion"], "none")

        backup = self.root / f"backup-{uuid.uuid4().hex}.sqlite"
        restored = self.root / f"restored-{uuid.uuid4().hex}.sqlite"
        source = sqlite3.connect(str(self.db_path))
        target = sqlite3.connect(str(backup))
        source.backup(target)
        target.close(); source.close()
        backup_conn = sqlite3.connect(str(backup))
        restored_conn = sqlite3.connect(str(restored))
        backup_conn.backup(restored_conn)
        restored_conn.close(); backup_conn.close()
        conn = sqlite3.connect(str(restored))
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_transactions WHERE order_id=?", (order["order_id"],)).fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_events WHERE order_id=?", (order["order_id"],)).fetchone()[0], 13)
        finally:
            conn.close()
        for file in (backup, restored):
            if file.exists(): file.unlink()

    def test_same_origin_consent_idempotency_and_owner_approval_gate(self):
        denied = self.client.post("/api/cash/leads", headers={"Origin": "https://evil.test", "Idempotency-Key": "lead-cross-0001"}, json={
            "product_id": self.product["id"], "email": "x@example.test", "name": "X", "contact_consent": True})
        self.assertEqual(denied.status_code, 403)
        no_consent = self.client.post("/api/cash/leads", headers={"Idempotency-Key": "lead-consent-01"}, json={
            "product_id": self.product["id"], "email": "x@example.test", "name": "X", "contact_consent": False})
        self.assertEqual(no_consent.status_code, 422)
        first = self.lead(suffix="retry", idempotency="lead-retry-0001")
        replay = self.client.post("/api/cash/leads", headers={"Idempotency-Key": "lead-retry-0001"}, json={
            "product_id": self.product["id"], "email": "buyer-retry@example.test", "name": "Buyer", "contact_consent": True})
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(first["order_id"], replay.json()["order_id"])
        mismatch = self.client.post("/api/cash/leads", headers={"Idempotency-Key": "lead-retry-0001"}, json={
            "product_id": self.product["id"], "email": "different@example.test", "name": "Buyer", "contact_consent": True})
        self.assertEqual(mismatch.status_code, 409)
        order = first
        quote = self.client.post(f"/api/cash/admin/leads/{order['order_id']}/quotes",
            headers={**self.admin_headers, "Idempotency-Key": "quote-gate-0001"},
            json={"scope": "A carefully scoped one page implementation and documentation.", "proposal_minor": 125_000})
        self.assertEqual(quote.status_code, 201)
        blocked = self.client.post(f"/api/cash/quotes/{quote.json()['quote_id']}/accept",
                                   headers={**self.buyer_headers(order['buyer_access_token']), "Idempotency-Key": "accept-before-approve"})
        self.assertEqual(blocked.status_code, 409)
        anon_owner = self.client.get("/api/cash/admin/orders")
        self.assertEqual(anon_owner.status_code, 403)

    def test_cancel_and_chargeback_are_separate_manual_adjustments(self):
        lead = self.lead(suffix="cancel")
        cancelled = self.client.post(f"/api/cash/admin/orders/{lead['order_id']}/cancel",
            headers={**self.admin_headers, "Idempotency-Key": "cancel-order-0001"},
            json={"reason": "Buyer withdrew the request."})
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["state"], "CANCELLED")

        order = self.setup_awaiting_payment(suffix="dispute", amount=80_000)
        claim = self.claim(order, 80_000, "buyer-dispute-0001", "dispute")
        verified = self.verify(claim, 80_000, "statement-dispute-0001", "verify-dispute-01")
        self.assertEqual(verified.status_code, 200)
        fulfilled = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/fulfill",
            headers=self.admin_headers, json={"artifact_id": self.artifact_id})
        self.assertEqual(fulfilled.status_code, 200, fulfilled.text)
        chargeback = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/chargeback",
            headers={**self.admin_headers, "Idempotency-Key": "chargeback-0001"},
            json={"amount_minor": 20_000, "reference": "chargeback-ref-001", "reason": "Bank dispute notice received."})
        self.assertEqual(chargeback.status_code, 200, chargeback.text)
        self.assertEqual(chargeback.json()["state"], "DISPUTED")
        resolved = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/dispute/resolve",
            headers={**self.admin_headers, "Idempotency-Key": "dispute-resolve-01"},
            json={"outcome": "WON", "reason": "Bank statement review resolved the dispute."})
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["state"], "FULFILLED")
        resolved_replay = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/dispute/resolve",
            headers={**self.admin_headers, "Idempotency-Key": "dispute-resolve-01"},
            json={"outcome": "WON", "reason": "Bank statement review resolved the dispute."})
        self.assertEqual(resolved_replay.status_code, 200)
        self.assertTrue(resolved_replay.json()["replayed"])
        self.assertEqual(resolved_replay.json()["state"], "FULFILLED")
        self.assertEqual(self.client.get(f"/api/cash/deliveries/{fulfilled.json()['delivery_id']}/download",
                                         headers=order["buyer_headers"]).status_code, 200)

        closed = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/close",
            headers={**self.admin_headers, "Idempotency-Key": "close-chargeback-01"})
        self.assertEqual(closed.status_code, 200, closed.text)
        self.assertEqual(closed.json()["state"], "CLOSED")
        late_chargeback = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/chargeback",
            headers={**self.admin_headers, "Idempotency-Key": "late-chargeback-0001"},
            json={"amount_minor": 10_000, "reference": "chargeback-ref-002", "reason": "A later bank chargeback notice."})
        self.assertEqual(late_chargeback.status_code, 200, late_chargeback.text)
        self.assertEqual(late_chargeback.json()["state"], "DISPUTED")
        lost = self.client.post(f"/api/cash/admin/orders/{order['order_id']}/dispute/resolve",
            headers={**self.admin_headers, "Idempotency-Key": "dispute-resolve-lost-01"},
            json={"outcome": "LOST", "reason": "Bank confirmed the second chargeback."})
        self.assertEqual(lost.status_code, 200, lost.text)
        self.assertEqual(lost.json()["state"], "CLOSED")
        summary = self.client.get("/api/cash/admin/summary", headers=self.admin_headers)
        self.assertEqual(summary.json()["settled_balance_by_currency"], [{
            "currency": "VND", "amount_minor": 70_000,
            "label": "VERIFIED_RECEIPTS_LESS_REFUNDS_AND_CHARGEBACKS"}])
        ledger = self.client.get(f"/api/cash/admin/orders/{order['order_id']}/transactions", headers=self.admin_headers)
        self.assertEqual([item["adjustment_type"] for item in ledger.json()["adjustments"]].count("CHARGEBACK"), 2)
        self.assertEqual([item["adjustment_type"] for item in ledger.json()["adjustments"]].count("CHARGEBACK_REVERSAL"), 1)

    def test_no_bank_or_token_secret_fails_closed(self):
        with patch.object(order_cash, "CONFIG", OwnerFinanceConfig()):
            lead = self.lead(suffix="not-configured")
            quote = self.client.post(f"/api/cash/admin/leads/{lead['order_id']}/quotes",
                headers={**self.admin_headers, "Idempotency-Key": "quote-no-bank-001"},
                json={"scope": "A one page custom product configuration and install guide.", "proposal_minor": 100_000})
            self.assertEqual(quote.status_code, 201, quote.text)
            quote_id = quote.json()["quote_id"]
            self.assertEqual(self.client.post(f"/api/cash/admin/quotes/{quote_id}/approve", headers=self.admin_headers).status_code, 200)
            accept = self.client.post(f"/api/cash/quotes/{quote_id}/accept",
                headers={**self.buyer_headers(lead["buyer_access_token"]), "Idempotency-Key": "accept-no-bank-001"})
            self.assertEqual(accept.status_code, 503)
            # No payment instructions or receiving account are exposed when checkout config is absent.
            instructions = self.client.get(f"/api/cash/orders/{lead['order_id']}/payment-instructions", headers=self.buyer_headers(lead["buyer_access_token"]))
            self.assertEqual(instructions.status_code, 409)
        os.environ.pop("AUTOPROFIT_ORDER_TOKEN_SECRET", None)
        response = self.client.post("/api/cash/leads", headers={"Idempotency-Key": "lead-secret-fail"}, json={
            "product_id": self.product["id"], "email": "secret@example.test", "contact_consent": True})
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
