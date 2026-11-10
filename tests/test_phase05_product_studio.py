"""Phase 05 product studio end-to-end and policy tests."""
from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from modules.product_builder import ProductBuilder, ProductBuildError, SAMPLE_HTML, SAMPLE_CSV, validate_opportunity  # noqa: E402
import modules.product_builder as product_builder_module  # noqa: E402
import apps_library  # noqa: E402
import product_studio_api  # noqa: E402
import workflow_api  # noqa: E402


CAPTURED = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def opportunity(category: str, title: str, source_url: str, suffix: str) -> dict:
    return {
        "id": f"opp_{suffix}", "title": title, "validation_status": "VALIDATED_BY_SOURCE",
        "category": category, "source_url": source_url, "captured_at": CAPTURED,
        "willingness_to_pay_hypothesis": "HYPOTHESIS: payment intent not verified.",
        "experiment": {"hypothesis": f"Test {category} with opt-in participants."},
        "evidence": [{"id": f"ev_{suffix}", "source_url": source_url, "captured_at": CAPTURED,
                      "source_date": "2026-10-28T04:45:34Z",
                      "quote": title, "quote_attribution": "Example Stack Overflow contributor; CC BY-SA 4.0",
                      "license": "CC BY-SA 4.0"}],
    }


SEO_OPPORTUNITY = opportunity(
    "website_seo_technical_fixes", "Search engines cannot see dynamic content without JavaScript",
    "https://stackoverflow.com/questions/80013003/how-can-search-engines-crawl-dynamic-page-content-when-javascript-is-disabled", "seo",
)
CSV_OPPORTUNITY = opportunity(
    "csv_file_utilities", "CSV import and column transformation workflow problem",
    "https://stackoverflow.com/questions/80013333/modify-column-structure-for-several-open-tabs-csv-docs-at-once-emeditor", "csv",
)


class OpportunityGateTests(unittest.TestCase):
    def test_only_current_allowlisted_validated_evidence_is_accepted(self):
        self.assertEqual(validate_opportunity(SEO_OPPORTUNITY)["category"], "website_seo_technical_fixes")
        for invalid in (
            {**SEO_OPPORTUNITY, "validation_status": "UNVALIDATED"},
            {**SEO_OPPORTUNITY, "evidence": [{**SEO_OPPORTUNITY["evidence"][0], "source_url": "http://stackoverflow.com/questions/1/x"}]},
            {**SEO_OPPORTUNITY, "evidence": [{**SEO_OPPORTUNITY["evidence"][0], "source_url": "https://evil.example/questions/1/x"}]},
        ):
            with self.subTest(status=invalid.get("validation_status")):
                with self.assertRaises(ProductBuildError):
                    validate_opportunity(invalid)

    def test_expired_or_unattributed_quoted_source_is_rejected(self):
        old = {**SEO_OPPORTUNITY, "evidence": [{**SEO_OPPORTUNITY["evidence"][0], "captured_at": "2024-01-01T00:00:00Z"}]}
        no_attribution = {**CSV_OPPORTUNITY, "evidence": [{**CSV_OPPORTUNITY["evidence"][0], "quote_attribution": None}]}
        unlicensed = {**CSV_OPPORTUNITY, "evidence": [{**CSV_OPPORTUNITY["evidence"][0], "license": "MIT"}]}
        for invalid in (old, no_attribution, unlicensed):
            with self.assertRaises(ProductBuildError):
                validate_opportunity(invalid)


class ProductStudioE2ETests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phase05-studio-")
        self.staging = Path(self.temp.name) / "staging"
        self.original_outputs = product_builder_module.OUTPUTS_DIR
        product_builder_module.OUTPUTS_DIR = Path(self.temp.name) / "outputs"

    def tearDown(self):
        product_builder_module.OUTPUTS_DIR = self.original_outputs
        self.temp.cleanup()

    def _assert_integrity(self, artifact):
        self.assertTrue(artifact.artifact_path.is_file())
        digest = hashlib.sha256(artifact.artifact_path.read_bytes()).hexdigest()
        self.assertEqual(digest, artifact.sha256)
        self.assertIn(digest, artifact.artifact_path.with_suffix(".zip.sha256").read_text(encoding="ascii"))
        with zipfile.ZipFile(artifact.artifact_path) as package:
            manifest = json.loads(package.read("BUILD_MANIFEST.json"))
            qa = json.loads(package.read("QA_RESULTS.json"))
            self.assertEqual(manifest["status"], "STAGING_QA_PASS")
            self.assertEqual(manifest["quality_score"], 100.0)
            self.assertTrue(all(result["passed"] for result in qa["checks"]))
            for name, file_hash in manifest["files"].items():
                self.assertEqual(hashlib.sha256(package.read(name)).hexdigest(), file_hash)
        self.assertEqual(artifact.status, "STAGING_QA_PASS")
        self.assertEqual(artifact.quality_score, 100.0)

    def test_track_a_builds_owner_authorized_snapshot_report_and_real_screenshot(self):
        source = SAMPLE_HTML.replace("Owner-provided public-page fixture.", "Public test page with contact test.person@example.org")
        with self.assertRaises(ProductBuildError):
            ProductBuilder.build_service_pack(SEO_OPPORTUNITY, source, staging_dir=self.staging)
        self.assertFalse(self.staging.exists())
        artifact = ProductBuilder.build_service_pack(SEO_OPPORTUNITY, source,
            owner_permission_confirmed=True, staging_dir=self.staging)
        self._assert_integrity(artifact)
        repeated = ProductBuilder.build_service_pack(SEO_OPPORTUNITY, source,
            owner_permission_confirmed=True, staging_dir=self.staging)
        self.assertEqual(artifact.sha256, repeated.sha256,
                         "Identical service inputs must produce byte-identical ZIPs.")
        with zipfile.ZipFile(artifact.artifact_path) as package:
            screenshot = package.read("evidence/site-preview.png")
            self.assertTrue(screenshot.startswith(b"\x89PNG\r\n\x1a\n"))
            report = json.loads(package.read("audit-report.json"))
            check_ids = {issue["check_id"] for issue in report["issues"]}
            self.assertIn("seo.title.missing", check_ids)
            self.assertIn("accessibility.images.alt_missing", check_ids)
            self.assertIn("NOT_MEASURED", report["measurements"]["performance_timing"])
            self.assertNotIn(b"test.person@example.org", screenshot)
            self.assertNotIn("test.person@example.org", package.namelist())

    def test_track_b_executes_packaged_python_script_and_blocks_formula_injection(self):
        artifact = ProductBuilder.build_data_workflow_pack(CSV_OPPORTUNITY, staging_dir=self.staging)
        self._assert_integrity(artifact)
        repeated = ProductBuilder.build_data_workflow_pack(CSV_OPPORTUNITY, staging_dir=self.staging)
        self.assertEqual(artifact.sha256, repeated.sha256, "Identical inputs must produce byte-identical ZIPs.")
        with zipfile.ZipFile(artifact.artifact_path) as package:
            script = package.read("csv_workbench.py").decode("utf-8")
            sample_output = package.read("sample_output.csv").decode("utf-8-sig")
            report = json.loads(package.read("sample_report.json"))
            self.assertIn("'=HYPERLINK", sample_output)
            self.assertEqual(report["duplicate_rows_removed"], 1)
            self.assertEqual(report["formula_cells_escaped"], 1)
            self.assertTrue(any(row["check_id"] == "mapped_formula_headers_are_neutralized" for row in json.loads(package.read("QA_RESULTS.json"))["checks"]))
            self.assertIn("landing-page.html", package.namelist())
            self.assertIn("REQUIREMENTS.md", package.namelist())
            self.assertIn("owner-reviewed-offer.md", package.namelist())
            self.assertNotIn("import requests", script)
            self.assertNotIn("eval(", script)

    def test_track_c_runs_two_existing_apps_in_chromium_end_to_end(self):
        artifact = ProductBuilder.build_microtool_bundle([SEO_OPPORTUNITY, CSV_OPPORTUNITY], staging_dir=self.staging)
        self._assert_integrity(artifact)
        repeated = ProductBuilder.build_microtool_bundle([SEO_OPPORTUNITY, CSV_OPPORTUNITY], staging_dir=self.staging)
        self.assertEqual(artifact.sha256, repeated.sha256,
                         "Identical microtool inputs must produce byte-identical ZIPs.")
        with zipfile.ZipFile(artifact.artifact_path) as package:
            names = package.namelist()
            self.assertIn("apps/papaparse-csv-to-json-cleaner.html", names)
            self.assertIn("apps/seo-opengraph-meta-generator.html", names)
            self.assertEqual(sum(name.startswith("apps/") and name.endswith(".html") for name in names), 2)
            csv_page = package.read("apps/papaparse-csv-to-json-cleaner.html").decode("utf-8")
            seo_page = package.read("apps/seo-opengraph-meta-generator.html").decode("utf-8")
            manifest = json.loads(package.read("BUILD_MANIFEST.json"))
            license_check = manifest["license_ip_check"]
            self.assertEqual(license_check["status"], "PROJECT_AUTHORED_CODE_WITH_SOURCE_LINKED_EVIDENCE")
            self.assertTrue(license_check["third_party_text_evidence"])
            landing = package.read("landing-page.html").decode("utf-8")
            self.assertIn("CC BY-SA 4.0", landing)
            self.assertIn("Example Stack Overflow contributor", landing)
            self.assertIn("REQUIREMENTS.md", names)
            for page in (csv_page, seo_page):
                self.assertNotIn("site-telemetry", page)
                self.assertNotIn("fetch(", page)
                self.assertNotIn("<iframe", page)
                self.assertNotIn("innerHTML", page)


class ProductStudioApiE2ETests(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        self.temp = tempfile.TemporaryDirectory(prefix="phase05-api-")
        self.root = Path(self.temp.name)
        self.db_path = self.root / "studio.db"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE workflow_records(id TEXT PRIMARY KEY,kind TEXT,status TEXT,payload_json TEXT)")
            conn.execute("INSERT INTO workflow_records VALUES(?,?,?,?)", (
                "opp_seo", "opportunity", "VALIDATED_BY_SOURCE", json.dumps(SEO_OPPORTUNITY)))
            conn.execute("INSERT INTO workflow_records VALUES(?,?,?,?)", (
                "opp_unvalidated", "opportunity", "UNVALIDATED", json.dumps({**SEO_OPPORTUNITY, "validation_status": "UNVALIDATED"})))
        conn.close()
        self.original_connection = product_studio_api.get_connection
        self.original_staging = product_studio_api.STAGING_DIR
        self.original_outputs = product_builder_module.OUTPUTS_DIR
        self.original_admin_key = os.environ.get("AUTOPROFIT_ADMIN_API_KEY")
        product_studio_api.get_connection = lambda: self._connect()
        product_studio_api.STAGING_DIR = self.root / "staging"
        product_builder_module.OUTPUTS_DIR = self.root / "outputs"
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = "phase05-product-studio-admin-" + ("x" * 40)
        app = FastAPI()
        app.include_router(product_studio_api.router)
        self.client = TestClient(app, base_url="https://testserver")

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def tearDown(self):
        product_studio_api.get_connection = self.original_connection
        product_studio_api.STAGING_DIR = self.original_staging
        product_builder_module.OUTPUTS_DIR = self.original_outputs
        if self.original_admin_key is None:
            os.environ.pop("AUTOPROFIT_ADMIN_API_KEY", None)
        else:
            os.environ["AUTOPROFIT_ADMIN_API_KEY"] = self.original_admin_key
        self.temp.cleanup()

    def test_api_requires_admin_and_downloads_only_qa_pass_artifacts(self):
        request = {"track": "A", "opportunity_ids": ["opp_seo"], "owner_permission_confirmed": True, "source_html": SAMPLE_HTML}
        unauthorized = self.client.post("/api/product-studio/build", json=request)
        self.assertEqual(unauthorized.status_code, 403)
        headers = {"X-Admin-Key": os.environ["AUTOPROFIT_ADMIN_API_KEY"]}
        invalid = self.client.post("/api/product-studio/build", json={**request, "opportunity_ids": ["opp_unvalidated"]}, headers=headers)
        self.assertEqual(invalid.status_code, 409)
        built = self.client.post("/api/product-studio/build", json=request, headers=headers)
        self.assertEqual(built.status_code, 200, built.text)
        result = built.json()
        self.assertEqual(result["status"], "STAGING_QA_PASS")
        self.assertEqual(result["quality_score"], 100.0)
        listed = self.client.get("/api/product-studio/artifacts", headers=headers).json()
        self.assertEqual(listed["total"], 1)
        downloaded = self.client.get(result["download_url"], headers=headers)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.headers["x-artifact-sha256"], result["sha256"])
        with zipfile.ZipFile(io.BytesIO(downloaded.content)) as package:
            self.assertEqual(json.loads(package.read("BUILD_MANIFEST.json"))["status"], "STAGING_QA_PASS")

    def test_catalog_keeps_twelve_tools_and_does_not_award_unbuilt_quality(self):
        catalog = apps_library.product_studio_catalog()
        self.assertEqual(catalog["total"], 12)
        ready = [item for item in catalog["items"] if item["studio"].get("app_type")]
        self.assertEqual({item["slug"] for item in ready}, {"papaparse-csv-to-json-cleaner", "seo-opengraph-meta-generator"})
        self.assertTrue(all(item["studio"]["quality_score"] is None for item in ready))
        self.assertTrue(all(item["studio"]["quality_status"] == "NOT_BUILT" for item in ready))
        self.assertTrue(all(item["price_usd"] is None and "quote" in item["pricing_model"] for item in ready))
        for tool in apps_library.TOOL_DEFINITIONS:
            if tool.get("studio"):
                self.assertTrue(apps_library.requires_owner_quote(tool))
                self.assertIsNone(tool["price_usd"])
                page = apps_library.generate_tool_html(tool)
                self.assertIn("Free basic demo", page)
                self.assertIn("owner-reviewed scope and quote", page)

    def test_fixed_price_catalog_count_excludes_quote_only_studio_demos(self):
        from unittest.mock import patch
        with patch.object(workflow_api, "_setting", return_value={}):
            catalog = workflow_api.pricing_catalog()
        slugs = {item["slug"] for item in catalog["items"]}
        self.assertEqual(catalog["total"], len(catalog["items"]))
        self.assertEqual(catalog["total"], 10)
        self.assertNotIn("papaparse-csv-to-json-cleaner", slugs)
        self.assertNotIn("seo-opengraph-meta-generator", slugs)

    def test_extension_has_minimum_permissions_and_scraper_is_retired(self):
        extension = ProductBuilder.build_chrome_extension("safe_extension_test")
        manifest = json.loads((extension / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["permissions"]), {"activeTab", "scripting"})
        self.assertNotIn("host_permissions", manifest)
        with self.assertRaises(ProductBuildError):
            ProductBuilder.build_python_scraper_bundle()


if __name__ == "__main__":
    unittest.main()
