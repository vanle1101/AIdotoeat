"""Production-readiness regressions for runtime health and metric-only optimization."""
from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import business_engine  # noqa: E402
import database  # noqa: E402
import main as backend_main  # noqa: E402
from core.optimization_agent import decide_optimization_proposal, run_weekly_optimization  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from scripts.ops import rollback_release  # noqa: E402


class Phase09ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phase09-production-")
        self.db_path = Path(self.temp.name) / "company.db"
        database.init_db(self.db_path)
        self.assertEqual(business_engine.ensure_schema(self.db_path), 13)
        business_engine.set_engine_control("kill_switch", False, path=self.db_path)

    def tearDown(self):
        self.temp.cleanup()

    def _add_event(self, conn, *, event_id, event_name, occurred_at, internal_test=0):
        conn.execute(
            """INSERT INTO gtm_analytics_events
               (event_id,event_name,campaign_id,session_id,page_path,source,occurred_at,internal_test)
               VALUES(?,?, 'test-campaign', NULL, '/offer', 'test-fixture', ?, ?)""",
            (event_id, event_name, occurred_at, internal_test),
        )

    def test_optimizer_uses_real_non_test_metrics_and_never_publishes(self):
        now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        current_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
        baseline_start = current_start - timedelta(days=7)
        conn = business_engine.connect(self.db_path)
        try:
            for window, base in ((baseline_start, "baseline"), (current_start, "current")):
                for index in range(12):
                    occurred = business_engine.iso(window + timedelta(hours=index))
                    self._add_event(conn, event_id=f"{base}-view-{index}", event_name="landing_view",
                                    occurred_at=occurred)
                for index in range(4):
                    self._add_event(conn, event_id=f"{base}-demo-{index}", event_name="demo_start",
                                    occurred_at=business_engine.iso(window + timedelta(hours=20 + index)))
                self._add_event(conn, event_id=f"{base}-internal", event_name="contact_submit",
                                occurred_at=business_engine.iso(window + timedelta(hours=30)), internal_test=1)
            conn.commit()
        finally:
            conn.close()

        result = run_weekly_optimization(path=self.db_path, now=now)
        self.assertEqual(result["status"], "proposal_created")
        self.assertFalse(result["public_change_applied"])
        proposal_id = result["proposal"]["id"]
        replay = run_weekly_optimization(path=self.db_path, now=now)
        self.assertEqual(replay["status"], "already_ran")
        self.assertFalse(replay["public_change_applied"])

        conn = business_engine.connect(self.db_path)
        try:
            rows = conn.execute("SELECT * FROM optimization_proposals").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "AWAITING_APPROVAL")
            self.assertNotIn('"contact_submit": 1', rows[0]["baseline_json"])
        finally:
            conn.close()

        approved = decide_optimization_proposal(proposal_id, "approve", path=self.db_path, now=now)
        self.assertEqual(approved["status"], "APPROVED_FOR_MANUAL_CHANGE")
        self.assertFalse(approved["public_change_applied"])

    def test_readiness_is_database_only_and_does_not_leak_paths(self):
        with patch.dict(os.environ, {"AUTOPROFIT_LLM_PROVIDER": "auto"}, clear=False), \
             patch.object(backend_main, "get_connection", lambda: database.get_connection(self.db_path)):
            client = TestClient(backend_main.app, base_url="https://readiness.test")
            response = client.get("/api/ready")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "ready")
        self.assertEqual(response.json()["checks"]["model_provider"], "not_health_checked_optional")
        self.assertNotIn(str(self.db_path), response.text)

    def test_optimizer_admin_routes_reject_anonymous_requests(self):
        key = "phase09-admin-gate-test-key-" + "x" * 40
        client = TestClient(backend_main.app, base_url="https://admin-gate.test")
        with patch.dict(os.environ, {"AUTOPROFIT_ADMIN_API_KEY": key}, clear=False):
            self.assertIn(client.post("/api/optimization/admin/run", json={"force": True}).status_code, {403, 503})
            self.assertIn(client.get("/api/optimization/admin/proposals").status_code, {403, 503})
            self.assertIn(client.post("/api/optimization/admin/proposals/missing/decision",
                                      json={"decision": "approve"}).status_code, {403, 503})

    def test_optimizer_kill_switch_blocks_snapshot_writes(self):
        business_engine.set_engine_control("kill_switch", True, path=self.db_path)
        result = run_weekly_optimization(path=self.db_path, now=datetime(2026, 11, 8, tzinfo=timezone.utc))
        self.assertEqual(result["reason_code"], "kill_switch_enabled")
        self.assertFalse(result["public_change_applied"])
        conn = business_engine.connect(self.db_path)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM optimization_runs").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM optimization_proposals").fetchone()[0], 0)
        finally:
            conn.close()

    def test_test_mode_helper_requires_staging_and_separate_key(self):
        from fastapi import HTTPException, Request
        import order_cash

        key = "phase09-separate-test-key-" + "x" * 40
        request = Request({
            "type": "http", "http_version": "1.1", "method": "POST", "scheme": "https",
            "path": "/api/cash/leads", "raw_path": b"/api/cash/leads", "query_string": b"",
            "headers": [(b"x-test-mode-key", key.encode())], "server": ("localhost", 443),
            "client": ("127.0.0.1", 1),
        })
        settings = {"AUTOPROFIT_ENV": "staging", "AUTOPROFIT_TEST_MODE_ENABLED": "true",
                    "AUTOPROFIT_TEST_MODE_KEY": key}
        with patch.dict(os.environ, settings, clear=False):
            self.assertTrue(order_cash._test_mode_requested(request, True))
        with patch.dict(os.environ, {**settings, "AUTOPROFIT_ENV": "production"}, clear=False):
            with self.assertRaises(HTTPException) as denied:
                order_cash._test_mode_requested(request, True)
            self.assertEqual(denied.exception.status_code, 403)

    def test_ops_migrate_cli_imports_core_from_a_repository_checkout(self):
        data_dir = Path(self.temp.name) / "migration-data"
        data_dir.mkdir()
        source_db = data_dir / "company.db"
        database.init_db(source_db)
        backup_path = Path(self.temp.name) / "before-migration.sqlite"
        env = os.environ.copy()
        env.update({
            "AUTOPROFIT_DATA_DIR": str(data_dir),
            "AUTOPROFIT_CORE_DATA_DIR": str(Path(self.temp.name) / "core-data"),
            "AUTOPROFIT_OUTPUTS_DIR": str(Path(self.temp.name) / "outputs"),
            "AUTOPROFIT_ENGINE_WORKER": "false",
            "AUTOPROFIT_ENGINE_KILL_SWITCH": "true",
            "AUTOPROFIT_BUDGET_KILL_SWITCH": "true",
            "AUTOPROFIT_TEST_MODE_ENABLED": "false",
        })
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "ops.py"), "migrate", "--backup", str(backup_path)],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["schema_version"], 13)
        self.assertEqual(result["integrity"], "ok")
        self.assertTrue(backup_path.is_file())

    def test_canary_configs_are_loopback_only_and_side_effects_default_off(self):
        service = (ROOT / "deploy/systemd/autoprofit-canary.service").read_text(encoding="utf-8")
        nginx = (ROOT / "deploy/nginx/autoprofit-canary.conf").read_text(encoding="utf-8")
        https_nginx = (ROOT / "deploy/nginx/autoprofit-canary-https.optional.conf").read_text(encoding="utf-8")
        self.assertIn("--host 127.0.0.1 --port 8451", service)
        self.assertIn("AUTOPROFIT_ENGINE_KILL_SWITCH=true", service)
        self.assertIn("AUTOPROFIT_BUDGET_KILL_SWITCH=true", service)
        self.assertIn("AUTOPROFIT_TEST_MODE_ENABLED=false", service)
        self.assertIn("IPAddressDeny=any", service)
        self.assertIn("IPAddressAllow=localhost", service)
        self.assertIn("listen 127.0.0.1:8889", nginx)
        self.assertIn("proxy_pass http://127.0.0.1:8451", nginx)
        self.assertNotRegex(nginx, r"listen\s+(?:[^;]*:)?(?:80|443|8888)\b")
        self.assertIn("listen 443 ssl", https_nginx)
        self.assertIn("X-Forwarded-Proto https", https_nginx)
        self.assertIn("canary.160.22.107.108.sslip.io", https_nginx)

    @unittest.skipUnless(os.name == "posix", "systemd release symlink rollback is Linux/POSIX-only")
    def test_rollback_switches_only_to_an_existing_release(self):
        releases = Path(self.temp.name) / "releases"
        releases.mkdir()
        (releases / "old-release").mkdir()
        (releases / "new-release").mkdir()
        current = Path(self.temp.name) / "current"
        current.symlink_to(Path("releases/new-release"), target_is_directory=True)
        switched = rollback_release(releases, current, "old-release")
        self.assertEqual(switched["status"], "release_symlink_switched")
        self.assertEqual(current.resolve(), (releases / "old-release").resolve())
        self.assertTrue(switched["database_untouched"])
        with self.assertRaises(ValueError):
            rollback_release(releases, current, "../outside")


if __name__ == "__main__":
    unittest.main()
