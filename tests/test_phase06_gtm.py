"""Phase 06 GTM staging, compliant CRM, attribution, and policy tests."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import database  # noqa: E402
import business_engine  # noqa: E402
import gtm_api  # noqa: E402
import main as backend_main  # noqa: E402
from modules.gtm_studio import (  # noqa: E402
    CAMPAIGN_ID, COMMUNITY_POLICIES, EXPERIMENT, STAGING_PACKAGE,
    build_staging_bundle, can_approve_community_draft, parse_utm,
)


class GTMBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phase06-gtm-build-")
        self.staging = Path(self.temp.name) / "staging"

    def tearDown(self):
        self.temp.cleanup()

    def test_one_ranked_niche_experiment_and_zero_cash_plan(self):
        self.assertEqual(EXPERIMENT["selected_niche"], "website_seo_technical_fixes")
        self.assertGreater(EXPERIMENT["selection_score"], EXPERIMENT["runner_up_score"])
        self.assertEqual(EXPERIMENT["experiment_window_days"], 14)
        self.assertEqual(EXPERIMENT["cash_budget_usd"], 0)
        self.assertEqual(EXPERIMENT["primary_distribution_channel"].split(" ")[0], "One")
        self.assertEqual(len(EXPERIMENT["weekly_plan"]), 2)
        self.assertIn("no direct", EXPERIMENT["source"]["willingness_to_pay"])

    def test_build_has_reproducible_hash_real_preview_seo_and_accessibility_evidence(self):
        first = build_staging_bundle(staging_dir=self.staging)
        second = build_staging_bundle(staging_dir=self.staging)
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(first["manifest"]["status"], "STAGING_QA_PASS_NO_PUBLICATION")
        self.assertEqual(first["manifest"]["quality_score"], 100.0)
        self.assertFalse(first["manifest"]["publication_gate"]["public_publish_performed"])
        digest = hashlib.sha256(first["path"].read_bytes()).hexdigest()
        self.assertEqual(digest, first["sha256"])
        self.assertIn(digest, first["path"].with_suffix(first["path"].suffix + ".sha256").read_text(encoding="ascii"))
        checks = {row["check_id"]: row for row in first["manifest"]["checks"]}
        for check_id in (
            "contact_fields_have_labels", "keyboard_skip_link", "mobile_375px_no_horizontal_overflow",
            "desktop_1440px_no_horizontal_overflow", "local_landing_dom_ready_under_5_seconds",
            "primary_cta_meets_touch_target", "analytics_requires_separate_opt_in",
            "contact_submission_requires_explicit_consent", "contact_opt_out_form_submits",
            "internal_links_resolve", "structured_data_is_valid_json", "sitemap_robots_are_staging_safe",
        ):
            self.assertTrue(checks[check_id]["passed"], check_id)
        with zipfile.ZipFile(first["path"]) as archive:
            names = set(archive.namelist())
            self.assertTrue({"landing.html", "tutorial.html", "case-study.html", "assets/sample-page-preview.png",
                             "demo/seo-opengraph-meta-generator.html", "portfolio-report.json", "robots.txt",
                             "sitemap.xml", "COMMUNITY_RULES.json", "drafts/community-drafts.json"}.issubset(names))
            landing = archive.read("landing.html").decode("utf-8")
            self.assertIn('content="noindex,nofollow"', landing)
            self.assertIn("example.invalid", landing)
            self.assertIn("Giả thuyết giá", landing)
            self.assertNotIn("testimonial", landing.lower())
            report = json.loads(archive.read("portfolio-report.json"))
            self.assertGreaterEqual(len(report["issues"]), 1)
            self.assertTrue(archive.read("assets/sample-page-preview.png").startswith(b"\x89PNG\r\n\x1a\n"))


class UTMTests(unittest.TestCase):
    def test_utm_parser_keeps_only_bounded_known_fields_and_drops_pii(self):
        value = parse_utm("https://example.test/?utm_source=indie_hackers&utm_medium=community&utm_campaign=gtm-06&utm_content=post-1&email=private@example.test&token=secret")
        self.assertEqual(value, {"utm_source": "indie_hackers", "utm_medium": "community",
                                 "utm_campaign": "gtm-06", "utm_content": "post-1"})
        oversized = parse_utm({"utm_source": "x" * 200, "email": "person@example.test", "ref": "arbitrary"})
        self.assertEqual(len(oversized["utm_source"]), 80)
        self.assertNotIn("email", oversized)
        self.assertNotIn("ref", oversized)


class GTMApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="phase06-gtm-api-")
        cls.root = Path(cls.temp.name)
        cls.staging = cls.root / "staging"
        build_staging_bundle(staging_dir=cls.staging)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        self.db_path = self.root / ("gtm-test-" + uuid.uuid4().hex + ".sqlite")
        database.init_db(self.db_path)
        legacy = database.get_connection(self.db_path)
        try:
            legacy.execute("INSERT INTO leads(name,email,source,need,stage,created_at) VALUES('Legacy','legacy@example.test','old_import','unknown','NEW','2026-01-01')")
            legacy.commit()
        finally:
            legacy.close()
        self.assertEqual(business_engine.ensure_schema(self.db_path), 13)
        self.original_get_connection = gtm_api.get_connection
        self.original_staging = gtm_api.STAGING_DIR
        self.original_admin_key = os.environ.get("AUTOPROFIT_ADMIN_API_KEY")
        self.original_consume_rate_limit = backend_main.consume_rate_limit
        gtm_api.get_connection = lambda: business_engine.connect(self.db_path)
        gtm_api.STAGING_DIR = self.staging
        self.rate_hits: dict[str, int] = {}

        def consume(scope: str, limit: int, window: int) -> bool:
            self.rate_hits[scope] = self.rate_hits.get(scope, 0) + 1
            return self.rate_hits[scope] <= limit

        backend_main.consume_rate_limit = consume
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = "phase06-admin-test-key-" + "m" * 40
        app = FastAPI()
        app.middleware("http")(backend_main.enforce_same_origin_and_rate_limits)
        app.include_router(gtm_api.router)
        self.client = TestClient(app, base_url="https://gtm.test", client=("203.0.113.9", 41000))

    def tearDown(self):
        gtm_api.get_connection = self.original_get_connection
        gtm_api.STAGING_DIR = self.original_staging
        backend_main.consume_rate_limit = self.original_consume_rate_limit
        if self.original_admin_key is None:
            os.environ.pop("AUTOPROFIT_ADMIN_API_KEY", None)
        else:
            os.environ["AUTOPROFIT_ADMIN_API_KEY"] = self.original_admin_key
        for candidate in (self.db_path, Path(str(self.db_path) + "-wal"), Path(str(self.db_path) + "-shm")):
            if candidate.exists():
                candidate.unlink()

    @property
    def admin_headers(self):
        return {"X-Admin-Key": os.environ["AUTOPROFIT_ADMIN_API_KEY"]}

    def contact(self, **overrides):
        payload = {
            "name": "Opt-in Visitor", "email": "buyer@example.test", "company": "Example Co",
            "need": "Please review the HTML snapshot behavior on my small business site.",
            "website": "", "contact_consent": True, "analytics_consent": False,
            "campaign_id": CAMPAIGN_ID, "session_id": str(uuid.uuid4()),
            "utm": {"utm_source": "indie_hackers", "utm_medium": "community", "email": "leak@example.test"},
        }
        payload.update(overrides)
        return self.client.post("/api/gtm/leads", json=payload)

    def test_migration_is_additive_idempotent_and_legacy_contacts_stay_unknown(self):
        self.assertEqual(business_engine.ensure_schema(self.db_path), 13)
        conn = business_engine.connect(self.db_path)
        try:
            legacy = conn.execute("SELECT email,gtm_consent_status,gtm_contact_provenance FROM leads WHERE email='legacy@example.test'").fetchone()
            self.assertEqual(legacy["email"], "legacy@example.test")
            self.assertEqual(legacy["gtm_consent_status"], "UNKNOWN")
            self.assertEqual(legacy["gtm_contact_provenance"], "legacy_unknown")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM gtm_analytics_events").fetchone()[0], 0)
        finally:
            conn.close()

    def test_inbound_contact_requires_permission_and_utm_requires_analytics_consent(self):
        denied = self.contact(contact_consent=False)
        self.assertEqual(denied.status_code, 422)
        response = self.contact(analytics_consent=False)
        self.assertEqual(response.status_code, 202, response.text)
        self.assertFalse(response.json()["email_sent"])
        conn = business_engine.connect(self.db_path)
        try:
            lead = conn.execute("SELECT * FROM leads WHERE gtm_campaign_id=?", (CAMPAIGN_ID,)).fetchone()
            self.assertEqual(lead["gtm_consent_status"], "OPTED_IN")
            self.assertEqual(lead["gtm_contact_provenance"], "self_submitted_inbound")
            event = conn.execute("SELECT * FROM gtm_analytics_events WHERE event_name='contact_submit'").fetchone()
            self.assertIsNone(event["session_id"])
            self.assertIsNone(event["utm_source"])
            self.assertEqual(event["source"], "inbound_contact_form")
        finally:
            conn.close()
        consented = self.contact(email="second@example.test", analytics_consent=True,
                                 session_id=str(uuid.uuid4()), utm={"utm_source": "indie_hackers", "email": "private@example.test"})
        self.assertEqual(consented.status_code, 202, consented.text)
        conn = business_engine.connect(self.db_path)
        try:
            event = conn.execute("SELECT session_id,utm_source FROM gtm_analytics_events WHERE lead_id=(SELECT MAX(id) FROM leads)").fetchone()
            self.assertTrue(event["session_id"])
            self.assertEqual(event["utm_source"], "indie_hackers")
        finally:
            conn.close()

    def test_opt_out_suppresses_and_revokes_contact_permission_with_neutral_response(self):
        self.assertEqual(self.contact().status_code, 202)
        response = self.client.post("/api/gtm/opt-out", json={"email": "buyer@example.test"})
        absent = self.client.post("/api/gtm/opt-out", json={"email": "absent@example.test"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), absent.json())
        conn = business_engine.connect(self.db_path)
        try:
            row = conn.execute("SELECT gtm_suppressed,gtm_consent_status,gtm_owner_approved_at FROM leads WHERE email='buyer@example.test'").fetchone()
            self.assertEqual(row["gtm_suppressed"], 1)
            self.assertEqual(row["gtm_consent_status"], "REVOKED")
            self.assertIsNone(row["gtm_owner_approved_at"])
        finally:
            conn.close()

    def test_bot_internal_and_invalid_events_are_excluded(self):
        payload = {"event_name": "landing_view", "event_id": str(uuid.uuid4()), "campaign_id": CAMPAIGN_ID,
                   "page_path": "/offers/website-snapshot-audit/", "session_id": str(uuid.uuid4()),
                   "analytics_consent": True, "utm": {"utm_source": "test"}}
        internal = self.client.post("/api/gtm/events", json={**payload, "internal_test": True})
        self.assertFalse(internal.json()["accepted"])
        bot = self.client.post("/api/gtm/events", json={**payload, "event_id": str(uuid.uuid4())}, headers={"User-Agent": "Googlebot/2.1"})
        self.assertFalse(bot.json()["accepted"])
        invalid_path = self.client.post("/api/gtm/events", json={**payload, "event_id": str(uuid.uuid4()), "page_path": "/?email=a@example.test"})
        self.assertEqual(invalid_path.status_code, 422)
        conn = business_engine.connect(self.db_path)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM gtm_analytics_events").fetchone()[0], 0)
        finally:
            conn.close()
        valid = self.client.post("/api/gtm/events", json=payload)
        duplicate = self.client.post("/api/gtm/events", json=payload)
        self.assertTrue(valid.json()["accepted"])
        self.assertEqual(duplicate.json()["status"], "duplicate_ignored")

    def test_actual_public_contact_rate_limit_is_applied_by_api_middleware(self):
        payload = {"name": "A", "email": "rate@example.test", "need": "A sufficiently long inquiry", "contact_consent": False, "campaign_id": CAMPAIGN_ID}
        results = [self.client.post("/api/gtm/leads", json=payload) for _ in range(4)]
        self.assertEqual([row.status_code for row in results], [422, 422, 422, 429])
        self.assertIn((3, 3600), backend_main._PUBLIC_RATE_LIMITS.values())

    def test_publication_queue_requires_human_rewrite_rules_recheck_and_never_posts(self):
        drafts = self.client.get("/api/gtm/admin/drafts", headers=self.admin_headers)
        self.assertEqual(drafts.status_code, 200, drafts.text)
        self.assertFalse(drafts.json()["publication_gate"]["public_publish_performed"])
        queued = self.client.post("/api/gtm/admin/publication-queue", headers=self.admin_headers,
                                  json={"channel": "hacker_news_show_hn"})
        self.assertEqual(queued.status_code, 200, queued.text)
        queue_id = queued.json()["item"]["id"]
        original = drafts.json()["drafts"]["hacker_news_show_hn"]
        blocked = self.client.post(f"/api/gtm/admin/publication-queue/{queue_id}/review", headers=self.admin_headers,
                                   json={"title": original["title"], "body": original["body"], "owner_approved": True,
                                         "human_rewrite_attested": True,
                                         "community_rules_rechecked": True})
        self.assertEqual(blocked.json()["status"], "BLOCKED")
        rewritten = self.client.post(f"/api/gtm/admin/publication-queue/{queue_id}/review", headers=self.admin_headers,
                                     json={"title": "My own working demo for offline HTML checks",
                                           "body": "I wrote this description myself after testing the local tool. " + "It checks a supplied synthetic HTML file and records static observations without network access. " * 4,
                                           "owner_approved": True, "human_rewrite_attested": True,
                                           "community_rules_rechecked": True})
        self.assertEqual(rewritten.status_code, 200, rewritten.text)
        self.assertEqual(rewritten.json()["status"], "APPROVED_FOR_MANUAL_POST")
        posted = self.client.post(f"/api/gtm/admin/publication-queue/{queue_id}/publish", headers=self.admin_headers)
        self.assertEqual(posted.status_code, 409)
        self.assertFalse(posted.json().get("published", True))

    def test_stale_community_policy_blocks_approval(self):
        self.assertFalse(can_approve_community_draft({"channel": "hacker_news_show_hn", "human_rewritten": True,
                                                      "community_rules_rechecked": True}, now=date(2027, 1, 1))[0])
        self.assertFalse(can_approve_community_draft({"channel": "unknown", "human_rewritten": True}, now=date.today())[0])

    def test_owner_approval_suppression_and_bounded_manual_outreach(self):
        created = self.contact().json()
        lead_id = self.client.get("/api/gtm/admin/leads", headers=self.admin_headers).json()["items"][0]["id"]
        qualified = self.client.post(f"/api/gtm/admin/leads/{lead_id}/qualify", headers=self.admin_headers,
                                     json={"owner_confirmed_problem": True})
        self.assertEqual(qualified.status_code, 200)
        proposal = "Hi, based on the HTML snapshot issue you described, I can review one authorized file and return a static report. " * 2
        saved = self.client.put(f"/api/gtm/admin/leads/{lead_id}/proposal", headers=self.admin_headers,
                                json={"proposal": proposal})
        self.assertEqual(saved.status_code, 200)
        unapproved = self.client.post(f"/api/gtm/admin/leads/{lead_id}/record-proposal-sent", headers=self.admin_headers,
                                      json={"owner_attests_manually_sent": True})
        self.assertEqual(unapproved.status_code, 409)
        approved = self.client.post(f"/api/gtm/admin/leads/{lead_id}/approve-proposal", headers=self.admin_headers, json={})
        self.assertEqual(approved.status_code, 200)
        sent = self.client.post(f"/api/gtm/admin/leads/{lead_id}/record-proposal-sent", headers=self.admin_headers,
                                json={"owner_attests_manually_sent": True, "channel": "owner_manually_sent"})
        self.assertEqual(sent.status_code, 200)
        second = self.client.put(f"/api/gtm/admin/leads/{lead_id}/proposal", headers=self.admin_headers, json={"proposal": proposal + "A separate follow-up."})
        self.assertEqual(second.status_code, 200)
        cadence_blocked = self.client.post(f"/api/gtm/admin/leads/{lead_id}/approve-proposal", headers=self.admin_headers, json={})
        self.assertEqual(cadence_blocked.status_code, 429)
        self.client.post("/api/gtm/opt-out", json={"email": "buyer@example.test"})
        suppressed = self.client.put(f"/api/gtm/admin/leads/{lead_id}/proposal", headers=self.admin_headers, json={"proposal": proposal})
        self.assertEqual(suppressed.status_code, 409)
        conn = business_engine.connect(self.db_path)
        try:
            count = conn.execute("SELECT gtm_outreach_count FROM leads WHERE id=?", (lead_id,)).fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            conn.close()

    def test_quote_and_payment_events_require_owner_attestation_and_verified_ledger(self):
        self.contact()
        lead_id = self.client.get("/api/gtm/admin/leads", headers=self.admin_headers).json()["items"][0]["id"]
        denied = self.client.post(f"/api/gtm/admin/leads/{lead_id}/accepted-quote", headers=self.admin_headers,
                                  json={"owner_confirms_customer_acceptance": False})
        self.assertEqual(denied.status_code, 422)
        accepted = self.client.post(f"/api/gtm/admin/leads/{lead_id}/accepted-quote", headers=self.admin_headers,
                                    json={"owner_confirms_customer_acceptance": True})
        self.assertEqual(accepted.status_code, 200)
        conn = business_engine.connect(self.db_path)
        try:
            conn.execute("INSERT INTO transactions(tx_hash,source,amount_usd,amount_vnd,payment_method,status,created_at) VALUES('tx-verified','gtm',29,0,'BANK_TRANSFER','PAID_VERIFIED','2026-11-08T00:00:00Z')")
            conn.execute("INSERT INTO transactions(tx_hash,source,amount_usd,amount_vnd,payment_method,status,created_at) VALUES('tx-pending','gtm',29,0,'BANK_TRANSFER','PENDING','2026-11-08T00:00:00Z')")
            conn.commit()
            verified_id = conn.execute("SELECT id FROM transactions WHERE tx_hash='tx-verified'").fetchone()[0]
            pending_id = conn.execute("SELECT id FROM transactions WHERE tx_hash='tx-pending'").fetchone()[0]
        finally:
            conn.close()
        pending = self.client.post(f"/api/gtm/admin/leads/{lead_id}/verified-payment", headers=self.admin_headers, json={"transaction_id": pending_id})
        self.assertEqual(pending.status_code, 409)
        result = self.client.post(f"/api/gtm/admin/leads/{lead_id}/verified-payment", headers=self.admin_headers, json={"transaction_id": verified_id})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIsNone(result.json()["channel_roi"])
        kpis = self.client.get("/api/gtm/admin/kpis", headers=self.admin_headers).json()
        self.assertIsNone(kpis["channel_roi"])
        self.assertEqual(kpis["roi_status"], "not_claimed_until_verified_transaction_and_channel_attribution_are_both_supported")
        self.assertIn("unverified", kpis["utm_attribution"])


if __name__ == "__main__":
    unittest.main()
