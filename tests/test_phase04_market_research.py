"""Evidence-first market research policy and persistence regression tests."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import database  # noqa: E402
import business_engine  # noqa: E402
from core import market_research as research  # noqa: E402
from modules.market_scout import MarketScout  # noqa: E402


NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
NOW_ISO = "2026-11-08T12:00:00Z"


def se_item(question_id=991, title="How can I clean duplicate rows in Excel CSV?", **overrides):
    item = {
        "question_id": question_id,
        "title": title,
        "body_markdown": "I receive a weekly CSV with duplicate rows and need a repeatable cleanup step.",
        "link": f"https://stackoverflow.com/questions/{question_id}/clean-duplicate-rows",
        "creation_date": int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp()),
        "last_activity_date": int(datetime(2026, 11, 7, tzinfo=timezone.utc).timestamp()),
        "content_license": "CC BY-SA 4.0",
        "owner": {"display_name": "Public Contributor"},
        "tags": ["excel", "csv"], "score": 2, "answer_count": 0,
    }
    item.update(overrides)
    return item


class ResearchTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="autoprofit-phase04-")
        self.path = Path(self.temp.name) / "company.db"
        database.DB_PATH = self.path
        database.init_db(self.path)
        business_engine.ensure_schema(self.path)

    def tearDown(self):
        self.temp.cleanup()


class SourcePolicyTests(ResearchTestCase):
    def test_templates_never_appear_in_validated_api(self):
        self.assertTrue(all(row["validation_status"] == "UNVALIDATED" for row in MarketScout.get_seed_ideas()))
        self.assertEqual(MarketScout.get_validated_opportunities(), [])

    def test_stackexchange_source_keeps_attributed_quote_and_problem_evidence(self):
        signals = research.normalize_stackexchange({"items": [se_item()]}, captured_at=NOW_ISO, now=NOW)
        self.assertEqual(len(signals), 1)
        signal = signals[0]
        self.assertEqual(signal.source_url, "https://stackoverflow.com/questions/991/clean-duplicate-rows")
        self.assertEqual(signal.quotation, "How can I clean duplicate rows in Excel CSV?")
        self.assertIn("CC BY-SA 4.0", signal.quote_attribution)
        self.assertIn("repeatable cleanup", signal.problem_text)

    def test_rejects_unlicensed_stale_private_contact_and_unsafe_claims(self):
        cases = [
            se_item(content_license=""),
            se_item(creation_date=int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()),
                    last_activity_date=int(datetime(2026, 11, 7, tzinfo=timezone.utc).timestamp())),
            se_item(title="Email me at jane@example.com for Excel cleanup"),
            se_item(title="Need fake ad impressions guaranteed profit for SEO"),
            se_item(title="Build CSV cleanup using a required paid API dependency"),
            se_item(title="Automated trading guaranteed profit through a spreadsheet"),
            se_item(link="https://evil.example/questions/991/not-stackexchange"),
        ]
        for item in cases:
            with self.subTest(title=item.get("title"), link=item.get("link")):
                self.assertEqual(research.normalize_stackexchange({"items": [item]}, now=NOW), [])

    def test_hn_requires_ask_story_and_does_not_quote_unlicensed_body(self):
        timestamp = int(datetime(2026, 11, 7, tzinfo=timezone.utc).timestamp())
        story = {"id": 4321, "title": "Ask HN: How do you clean large CSV exports?", "time": timestamp,
                 "text": "This is not stored as a quotation", "score": 5, "descendants": 2}
        signal = research.normalize_hn_story(story, captured_at=NOW_ISO, now=NOW)
        self.assertIsNotNone(signal)
        self.assertIsNone(signal.quotation)
        self.assertEqual(signal.source_url, "https://news.ycombinator.com/item?id=4321")
        self.assertIsNone(research.normalize_hn_story({**story, "title": "Show HN: My CSV utility"}, now=NOW))

    def test_paid_api_metadata_is_blocked_without_sending_payment(self):
        for response in ({"items": [se_item()], "cost_usd": 0.01},
                         {"items": [se_item()], "billing_required": True},
                         {"items": [se_item()], "status": 402}):
            self.assertEqual(research.normalize_stackexchange(response, now=NOW), [])

    def test_explicit_payment_language_counts_only_as_a_weak_source_signal(self):
        item = se_item(body_markdown="I would pay for a small offline CSV cleanup tool if it preserves formulas.")
        signal = research.normalize_stackexchange({"items": [item]}, now=NOW)[0]
        opportunity = research.build_opportunities([signal], now=NOW)[0]
        self.assertTrue(signal.direct_wtp_signal)
        self.assertIn("I would pay", opportunity.quotation)
        self.assertEqual(opportunity.score_dimensions["direct_willingness_to_pay_signal"], 85)
        self.assertIn("amount, buyer authority", opportunity.willingness_to_pay_hypothesis)

    def test_negated_or_speculative_payment_language_is_not_a_buyer_signal(self):
        for body in ("I am not willing to pay for this tool.", "Would you pay for an offline CSV utility?",
                     "The budget is around $50, but I do not want to pay for software."):
            self.assertFalse(research._has_direct_wtp_signal(body), body)

    def test_personal_email_in_public_display_name_is_not_retained(self):
        item = se_item(owner={"display_name": "person@example.com"})
        self.assertEqual(research.normalize_stackexchange({"items": [item]}, now=NOW), [])

    def test_misleading_profit_claims_are_hard_rejected(self):
        item = se_item(title="How to make guaranteed profit with a fake review bot?")
        self.assertEqual(research.normalize_stackexchange({"items": [item]}, now=NOW), [])


class ScoringAndDedupTests(ResearchTestCase):
    def test_score_is_weighted_and_does_not_invent_willingness_to_pay(self):
        signals = research.normalize_stackexchange({"items": [se_item()]}, captured_at=NOW_ISO, now=NOW)
        opportunities = research.build_opportunities(signals, now=NOW)
        self.assertEqual(len(opportunities), 1)
        item = opportunities[0]
        self.assertEqual(item.validation_status, "VALIDATED_BY_SOURCE")
        self.assertEqual(item.score_dimensions["direct_willingness_to_pay_signal"], 0)
        self.assertIn("HYPOTHESIS", item.willingness_to_pay_hypothesis)
        self.assertIn("NOT_RESEARCHED", item.competition)
        self.assertEqual(item.existing_alternatives, ())
        self.assertEqual(set(item.score_dimensions), set(research.WEIGHTS))
        self.assertAlmostEqual(item.score, round(sum(item.score_dimensions[k] * w for k, w in research.WEIGHTS.items()), 1))

    def test_exact_and_semantic_duplicates_do_not_create_multiple_opportunities(self):
        source_a = research.normalize_stackexchange({"items": [se_item(991)]}, now=NOW)[0]
        source_b = research.normalize_stackexchange({"items": [se_item(992, "How do I clean duplicate rows in Excel CSV?")]}, now=NOW)[0]
        opportunities = research.build_opportunities([source_a, source_a, source_b], now=NOW)
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(len(opportunities[0].evidence), 2)
        self.assertEqual(len({row["source_url"] for row in opportunities[0].evidence}), 2)

    def test_empty_and_out_of_date_sources_yield_no_validated_opportunities(self):
        self.assertEqual(research.normalize_stackexchange({"items": []}, now=NOW), [])
        stale = se_item(creation_date=int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()),
                        last_activity_date=int(datetime(2026, 11, 7, tzinfo=timezone.utc).timestamp()))
        self.assertEqual(research.build_opportunities(research.normalize_stackexchange({"items": [stale]}, now=NOW), now=NOW), [])


class FetchAndPersistenceTests(ResearchTestCase):
    def test_official_feed_fetchers_use_allowlisted_endpoints_and_handle_empty(self):
        calls = []
        def fake_fetch(url):
            calls.append(url)
            return {"items": [], "quota_remaining": 99} if "stackexchange" in url else []
        stack, stack_status = research.fetch_stackexchange(path=self.path, now=NOW, fetch_json=fake_fetch)
        hn, hn_status = research.fetch_hacker_news(path=self.path, now=NOW, fetch_json=fake_fetch)
        self.assertEqual((stack, stack_status), ([], "observed"))
        self.assertEqual((hn, hn_status), ([], "observed"))
        self.assertTrue(all(url.startswith(("https://api.stackexchange.com/", "https://hacker-news.firebaseio.com/")) for url in calls))
        self.assertEqual(sum("api.stackexchange.com" in url for url in calls), 3)

    def test_hn_feed_fetch_calls_official_item_endpoint(self):
        created = int(datetime(2026, 11, 7, tzinfo=timezone.utc).timestamp())
        urls = []
        def fake_fetch(url):
            urls.append(url)
            if url.endswith("askstories.json"):
                return [123]
            return {"id": 123, "title": "Ask HN: Excel CSV cleanup workflow?", "time": created}
        rows, status = research.fetch_hacker_news(path=self.path, now=NOW, fetch_json=fake_fetch)
        self.assertEqual(status, "observed")
        self.assertEqual(len(rows), 1)
        self.assertIn("/v0/item/123.json", urls[-1])

    def test_rate_limited_source_is_not_called_again_until_retry_window(self):
        calls = []
        def fake_fetch(_url):
            calls.append(1)
            raise research.SourceUnavailable("paid_or_rate_limited", status=429, retry_after="600")
        _, status1 = research.fetch_stackexchange(path=self.path, now=NOW, fetch_json=fake_fetch)
        _, status2 = research.fetch_stackexchange(path=self.path, now=NOW, fetch_json=fake_fetch)
        self.assertEqual(status1, "paid_or_rate_limited")
        self.assertEqual(status2, "rate_limited")
        self.assertEqual(len(calls), 1)

    def test_paid_stack_api_error_stops_remaining_queries(self):
        calls = []
        def fake_fetch(url):
            calls.append(url)
            return {"error_id": 402, "error_name": "payment_required", "items": []}
        signals, status = research.fetch_stackexchange(path=self.path, now=NOW, fetch_json=fake_fetch)
        self.assertEqual(signals, [])
        self.assertEqual(status, "paid_source_blocked")
        self.assertEqual(len(calls), 1)

    def test_run_reports_source_cooldown_distinct_from_empty_scan(self):
        def limited(**_kwargs):
            return [], "rate_limited"
        result = research.run_live_research(path=self.path, stackexchange_fetch=limited, hn_fetch=limited, now=NOW)
        self.assertEqual(result["status"], "rate_limited")
        self.assertEqual(result["validated_by_source_count"], 0)

    def test_persistence_is_idempotent_and_writes_evidence_and_experiment(self):
        signal = research.normalize_stackexchange({"items": [se_item()]}, captured_at=NOW_ISO, now=NOW)[0]
        item = research.build_opportunities([signal], now=NOW)[0]
        first = research.persist_opportunities([item], path=self.path)
        second = research.persist_opportunities([item], path=self.path)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        conn = business_engine.connect(self.path)
        try:
            row = conn.execute("SELECT source_uri,captured_at,quote,pain_point,buyer_persona,willingness_to_pay_hypothesis,legal_restrictions,competition,confidence,freshness_days FROM evidence WHERE opportunity_id=?", (item.id,)).fetchone()
            self.assertEqual(row["source_uri"], item.source_url)
            self.assertEqual(row["captured_at"], NOW_ISO)
            self.assertEqual(row["quote"], item.quotation)
            self.assertIn("HYPOTHESIS", row["willingness_to_pay_hypothesis"])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM experiments WHERE opportunity_id=?", (item.id,)).fetchone()[0], 1)
            stored = json.loads(conn.execute("SELECT payload_json FROM workflow_records WHERE id=?", (item.id,)).fetchone()[0])
            self.assertEqual(stored["validation_status"], "VALIDATED_BY_SOURCE")
            self.assertIn("falsification_observation", stored["experiment"])
        finally:
            conn.close()

    def test_new_independent_source_is_attached_to_existing_semantic_opportunity_once(self):
        source_a = research.normalize_stackexchange({"items": [se_item(991)]}, captured_at=NOW_ISO, now=NOW)[0]
        source_b = research.normalize_stackexchange({"items": [se_item(992, "How do I clean duplicate rows in Excel CSV?")]}, captured_at=NOW_ISO, now=NOW)[0]
        first = research.build_opportunities([source_a], now=NOW)[0]
        merged = research.build_opportunities([source_a, source_b], now=NOW)[0]
        self.assertEqual(len(research.persist_opportunities([first], path=self.path)), 1)
        self.assertEqual(len(research.persist_opportunities([merged], path=self.path)), 1)
        self.assertEqual(research.persist_opportunities([merged], path=self.path), [])
        conn = business_engine.connect(self.path)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_records WHERE kind='opportunity'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM evidence WHERE opportunity_id=?", (first.id,)).fetchone()[0], 2)
            payload = json.loads(conn.execute("SELECT payload_json FROM workflow_records WHERE id=?", (first.id,)).fetchone()[0])
            self.assertEqual(payload["evidence_count"], 2)
            self.assertEqual(len({item["source_url"] for item in payload["evidence"]}), 2)
        finally:
            conn.close()

    def test_migration_is_additive_and_idempotent_for_legacy_evidence_rows(self):
        conn = business_engine.connect(self.path)
        try:
            conn.execute("INSERT INTO evidence(id,evidence_type,summary,created_at) VALUES('legacy-e','manual','old evidence',?)", (NOW_ISO,))
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(business_engine.ensure_schema(self.path), 13)
        self.assertEqual(business_engine.ensure_schema(self.path), 13)
        conn = business_engine.connect(self.path)
        try:
            row = conn.execute("SELECT summary,source_uri,captured_at FROM evidence WHERE id='legacy-e'").fetchone()
            self.assertEqual(row["summary"], "old evidence")
            self.assertIsNone(row["source_uri"])
            self.assertIsNone(row["captured_at"])
        finally:
            conn.close()


class ApiHonestyTests(ResearchTestCase):
    def test_public_dashboard_has_no_harvested_contact_cards_or_cold_email_links(self):
        html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("internetHuntedLeadsGrid", html)
        self.assertNotIn("Email thật:", html)
        self.assertNotIn("mailto:", html.lower())
        self.assertIn("public source authors are not contacts", html)

    def test_public_dashboard_does_not_claim_unverified_market_prices(self):
        html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        for claim in ("Rẻ hơn 85%", "85% Off", "Market Price", "$19.00 – $49.00 USD", "135</span> Web App"):
            with self.subTest(claim=claim):
                self.assertNotIn(claim, html)
        self.assertIn("Giá catalog: đang tải", html)
        self.assertIn("Giá bài viết: chưa xác minh", html)

    def test_manual_job_input_remains_unvalidated_without_keyword_fit_or_verified_budget(self):
        import workflow_api
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = "phase04-manual-admin-" + "m" * 40
        request = mock.Mock(url=mock.Mock(scheme="https"), headers={"X-Admin-Key": os.environ["AUTOPROFIT_ADMIN_API_KEY"]})
        with mock.patch.object(workflow_api, "_record", return_value={"id": "manual-1"}) as record:
            result = workflow_api.analyze_freelance_job(request, {"title": "SEO automation Python", "requirements": "Build an SEO tool",
                                                                    "published_budget_usd": "999"})
        self.assertEqual(result["status"], "UNVALIDATED")
        self.assertIsNone(result["fit_score"])
        payload = record.call_args.args[1]
        self.assertEqual(payload["validation_status"], "UNVALIDATED")
        self.assertEqual(payload["user_reported_budget_usd"], 999)
        self.assertNotIn("published_budget_usd", payload)

    def test_manual_brief_mutation_is_admin_and_https_protected(self):
        import workflow_api
        from fastapi import HTTPException
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = "phase04-manual-admin-" + "m" * 40
        payload = {"title": "CSV cleanup", "requirements": "Normalize duplicate rows."}
        insecure = mock.Mock(url=mock.Mock(scheme="http"), headers={"X-Admin-Key": os.environ["AUTOPROFIT_ADMIN_API_KEY"]})
        unauthorized = mock.Mock(url=mock.Mock(scheme="https"), headers={})
        for request in (insecure, unauthorized):
            with self.subTest(scheme=request.url.scheme), self.assertRaises(HTTPException):
                workflow_api.analyze_freelance_job(request, payload)

    def test_manual_brief_rejects_personal_email_unsafe_claims_and_script_urls(self):
        import workflow_api
        from fastapi import HTTPException
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = "phase04-manual-admin-" + "m" * 40
        base = {"title": "CSV cleanup", "requirements": "Normalize duplicate rows."}
        for payload in (
            {**base, "requirements": "Contact owner at person@example.com"},
            {**base, "requirements": "Build fake ad impression views and guarantee profit"},
            {**base, "source_url": "javascript:alert(1)"},
        ):
            with self.subTest(payload=payload), self.assertRaises(HTTPException) as raised:
                request = mock.Mock(url=mock.Mock(scheme="https"), headers={"X-Admin-Key": os.environ.get("AUTOPROFIT_ADMIN_API_KEY", "")})
                workflow_api.analyze_freelance_job(request, payload)
            self.assertEqual(raised.exception.status_code, 422)

    def test_live_scan_requires_owner_auth_and_returns_source_evidence_contract(self):
        import main
        from fastapi.testclient import TestClient
        api_key = "phase04-test-admin-" + "a" * 40
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = api_key
        client = TestClient(main.app, base_url="https://testserver")
        with mock.patch.object(research, "run_live_research", return_value={"status": "observed", "sources": {"Stack Exchange": "observed"},
                                                                              "items": [], "validated_by_source_count": 0,
                                                                              "message": "No evidence."}):
            self.assertEqual(client.post("/api/internet/live-scan").status_code, 403)
            response = client.post("/api/internet/live-scan", headers={"X-Admin-Key": api_key})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("Stack Exchange", response.json()["sources"])
        self.assertEqual(response.json()["validated_by_source_count"], 0)


if __name__ == "__main__":
    unittest.main()
