from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path

from scripts.phase11_ops import create_backup_bundle


class Phase11BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.backup_parent = self.root / "backups"
        self.backup_parent.mkdir(mode=0o700)
        self.backend = self.root / "backend-company.db"
        self.core = self.root / "core-company.db"

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def make_wal_database(path: Path, value: str) -> None:
        conn = sqlite3.connect(path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE ledger(value TEXT NOT NULL)")
            conn.execute("INSERT INTO ledger(value) VALUES(?)", (value,))
            conn.commit()
        finally:
            conn.close()

    def test_online_wal_backup_restore_and_private_permissions(self):
        self.make_wal_database(self.backend, "backend-row")
        # Keep a writer open so the source remains in WAL mode during backup.
        source = sqlite3.connect(self.backend)
        source.execute("INSERT INTO ledger(value) VALUES('wal-committed-row')")
        source.commit()
        result = create_backup_bundle(backend_source=self.backend, core_source=None,
                                      backup_parent=self.backup_parent, run_id="wal-test")
        source.close()

        backend = result["databases"]["backend"]
        self.assertTrue(backend["source_wal_present"])
        self.assertEqual(backend["source_journal_mode"], "wal")
        if os.name == "posix":
            self.assertEqual(backend["backup_mode"], "0600")
            self.assertEqual(result["bundle_mode"], "0700")
        else:
            self.assertIsNone(backend["backup_mode"])
            self.assertFalse(result["permissions_verifiable"])
        self.assertEqual(backend["backup_integrity"], "ok")
        self.assertEqual(backend["restore_test"]["status"], "PASS")
        self.assertTrue(backend["restore_test"]["row_counts_match"])
        self.assertTrue(backend["restore_test"]["backup_unchanged"])
        manifest = Path(result["bundle_directory"]) / "manifest.json"
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(manifest.stat().st_mode), 0o600)
        self.assertEqual(result["databases"]["core"]["status"], "NOT_PRESENT")
        conn = sqlite3.connect(Path(result["bundle_directory"]) / "backend-company.db")
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 2)
        finally:
            conn.close()

    def test_existing_bundle_is_never_overwritten(self):
        self.make_wal_database(self.backend, "backend-row")
        (self.backup_parent / "autoprofit-phase11-existing").mkdir()
        with self.assertRaises(FileExistsError):
            create_backup_bundle(backend_source=self.backend, core_source=None,
                                 backup_parent=self.backup_parent, run_id="existing")

    def test_core_database_is_backed_up_when_present(self):
        self.make_wal_database(self.backend, "backend-row")
        self.make_wal_database(self.core, "core-row")
        result = create_backup_bundle(backend_source=self.backend, core_source=self.core,
                                      backup_parent=self.backup_parent, run_id="both")
        self.assertEqual(result["databases"]["core"]["status"], "PASS")
        self.assertEqual(result["databases"]["core"]["restore_test"]["status"], "PASS")
        self.assertTrue((Path(result["bundle_directory"]) / "core-company.db").is_file())


class Phase11ReleaseSafetyTests(unittest.TestCase):
    def test_production_unit_template_is_least_privilege_and_fail_closed(self):
        unit = (Path(__file__).resolve().parents[1] /
                "deploy/systemd/autoprofit-backend-phase11.service").read_text(encoding="utf-8")
        self.assertRegex(unit, r"(?m)^User=autoprofit$")
        self.assertRegex(unit, r"(?m)^Group=autoprofit$")
        self.assertRegex(unit, r"(?m)^UMask=0077$")
        self.assertRegex(unit, r"(?m)^ProtectSystem=strict$")
        self.assertRegex(unit, r"(?m)^NoNewPrivileges=true$")
        self.assertRegex(unit, r"(?m)^ReadWritePaths=/var/lib/autoprofit$")
        self.assertRegex(unit, r"(?m)^ReadWritePaths=/var/www/autoprofit/frontend/apps$")
        self.assertRegex(unit, r"(?m)^Environment=AUTOPROFIT_ENGINE_WORKER=false$")
        self.assertRegex(unit, r"(?m)^Environment=AUTOPROFIT_ENGINE_KILL_SWITCH=true$")
        self.assertRegex(unit, r"(?m)^Environment=AUTOPROFIT_BUDGET_KILL_SWITCH=true$")
        self.assertRegex(unit, r"(?m)^Environment=AUTOPROFIT_TEST_MODE_ENABLED=false$")
        self.assertIn("StandardOutput=journal", unit)
        self.assertNotIn("StandardOutput=append:", unit)
        self.assertIn("/var/lib/autoprofit/backend-data", unit)
        self.assertIn("/var/lib/autoprofit/core-data", unit)
        self.assertIn("/var/lib/autoprofit/outputs", unit)
        self.assertIn("AUTOPROFIT_APPS_DIR=/var/www/autoprofit/frontend/apps", unit)

    def test_mutable_outputs_use_state_directory_and_public_html_is_read_only(self):
        root = Path(__file__).resolve().parents[1]
        studio_api = (root / "backend/product_studio_api.py").read_text(encoding="utf-8")
        apps_library = (root / "backend/apps_library.py").read_text(encoding="utf-8")
        self.assertIn("STAGING_DIR = OUTPUTS_DIR / \"staging\"", studio_api)
        self.assertIn("file_path.chmod(0o644)", apps_library)

    def test_repo_traffic_compatibility_worker_has_no_automation_clients(self):
        root = Path(__file__).resolve().parents[1]
        worker = (root / "backend/traffic_worker.py").read_text(encoding="utf-8").lower()
        self.assertNotRegex(worker, r"\b(requests|httpx|aiohttp|playwright|selenium|webdriver)\b")
        self.assertNotRegex(worker, r"https?://|user.?agent|random\.")
        self.assertIn("retired", worker)
        self.assertIn("stop_event", worker)

        autosurf = (root / "frontend/autosurf.html").read_text(encoding="utf-8").lower()
        self.assertIn("auto-surf đã tắt", autosurf)
        self.assertNotRegex(autosurf, r"<iframe|setinterval\s*\(|location\.(?:href|replace)\s*=")
        youtube = (root / "frontend/youtube-booster.html").read_text(encoding="utf-8").lower()
        self.assertNotRegex(youtube, r"youtube\.com/embed|autoplay|watch-and-earn|startyoutube")

    def test_distribution_role_is_a_reviewable_draft_not_a_fake_live_agent(self):
        source = (Path(__file__).resolve().parents[1] /
                  "frontend/autoprofit-core.js").read_text(encoding="utf-8")
        role = source.split("VIRAL_TRAFFIC_AGENT: {", 1)[1].split("TEMPLATE_POD_AGENT:", 1)[0]
        self.assertIn("Owner review required", role)
        self.assertIn("does not publish automatically or generate ad impressions", role)
        self.assertNotIn("24/7 Active", role)


if __name__ == "__main__":
    unittest.main()
