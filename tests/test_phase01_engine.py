"""Temporary-database coverage for the durable Phase 01 engine."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import threading
import unittest
import atexit
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))
_BOOTSTRAP_TEMP = tempfile.TemporaryDirectory(prefix="autoprofit-phase01-bootstrap-")
os.environ["AUTOPROFIT_DATA_DIR"] = str(Path(_BOOTSTRAP_TEMP.name) / "backend-data")
os.environ["AUTOPROFIT_APPS_DIR"] = str(Path(_BOOTSTRAP_TEMP.name) / "generated-apps")
os.environ.setdefault("AUTOPROFIT_ADMIN_API_KEY", "phase01-bootstrap-key-" + "x" * 40)
atexit.register(_BOOTSTRAP_TEMP.cleanup)

import database
import business_engine as engine
from domain_models import TaskSpec, TaskState
from migrate_core_legacy import migrate, restore_to_new_file


class EngineTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="autoprofit-phase01-")
        self.root = Path(self.temp.name)
        database.DB_PATH = self.root / "backend" / "company.db"
        database.DB_PATH.parent.mkdir(parents=True)
        database.init_db()
        engine.ensure_schema()
        engine.set_engine_control("kill_switch", False)
        engine.set_engine_control("paused", False)
        os.environ["AUTOPROFIT_ADMIN_API_KEY"] = "phase01-admin-test-key-" + "z" * 40

    def tearDown(self):
        self.temp.cleanup()


class MigrationTests(EngineTestCase):
    def test_migrations_are_idempotent_and_all_domain_projections_exist(self):
        self.assertEqual(engine.ensure_schema(), 13)
        self.assertEqual(engine.ensure_schema(), 13)
        conn = engine.connect()
        try:
            versions = [row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
            self.assertEqual(versions, list(range(1, 14)))
            objects = {row["name"]: row["type"] for row in conn.execute("SELECT name,type FROM sqlite_master")}
            for name in ("opportunities", "evidence", "experiments", "customers", "leads", "offers", "products",
                         "assets", "tasks", "task_events", "agent_runs", "approval_requests", "orders",
                         "payment_claims", "verified_transactions", "deliveries", "cost_exposures", "analytics_events"):
                self.assertIn(name, objects, name)
            self.assertEqual(objects["leads"], "table")
            self.assertEqual(objects["products"], "table")
            self.assertEqual(objects["orders"], "view")
            self.assertEqual(objects["offers"], "view")
            self.assertEqual(objects["payment_claims"], "view")
            self.assertEqual(objects["llm_usage"], "table")
            self.assertEqual(objects["llm_cache"], "table")
            self.assertEqual(objects["market_research_fetch_state"], "table")
            self.assertEqual(objects["gtm_analytics_events"], "table")
            self.assertEqual(objects["gtm_publication_queue"], "table")
            for name in ("cash_orders", "cash_quotes", "cash_claims", "cash_transactions",
                         "cash_adjustments", "cash_deliveries", "cash_events"):
                self.assertEqual(objects[name], "table")
        finally:
            conn.close()

    def test_import_is_backed_up_idempotent_and_rollback_restores_copy(self):
        source = self.root / "core-source.sqlite"
        target = database.DB_PATH
        conn = sqlite3.connect(source)
        conn.executescript("""
            CREATE TABLE tasks(id INTEGER PRIMARY KEY,title TEXT,category TEXT,assigned_role_id TEXT,status TEXT,
              cost_vnd REAL,input_data TEXT,output_data TEXT,created_at TEXT,updated_at TEXT,run_id TEXT,
              started_at TEXT,finished_at TEXT,progress_pct INTEGER,artifact_refs TEXT);
            CREATE TABLE task_events(event_id INTEGER PRIMARY KEY,timestamp TEXT,agent_id TEXT,task_id TEXT,run_id TEXT,
              event_type TEXT,status TEXT,title TEXT,description TEXT,source TEXT,result TEXT,duration_ms INTEGER,
              metadata_json TEXT,artifact_refs_json TEXT,error_details TEXT);
            CREATE TABLE deliverables(id INTEGER PRIMARY KEY,name TEXT,deliverable_type TEXT,file_path TEXT,
              content_preview TEXT,estimated_market_value_vnd REAL,owner_status TEXT,created_at TEXT);
            CREATE TABLE revenue_ledger(id INTEGER PRIMARY KEY,source TEXT,amount_vnd REAL,status TEXT,payout_destination TEXT,logged_at TEXT);
            INSERT INTO tasks VALUES(1,'old task','legacy','OPS','PENDING',0,'{}',NULL,'2025-01-01','2025-01-01',NULL,NULL,NULL,0,NULL);
            INSERT INTO tasks VALUES(2,'done task','legacy','OPS','DONE',0,NULL,'ok','2025-01-01','2025-01-01','r1',NULL,'2025-01-01',100,NULL);
            INSERT INTO task_events VALUES(1,'2025-01-01','OPS','2','r1','done','DONE','done event',NULL,'test','ok',1,'{}','[]',NULL);
            INSERT INTO deliverables VALUES(1,'asset','HTML','/tmp/asset.html','preview',0,'DRAFT','2025-01-01');
            INSERT INTO revenue_ledger VALUES(1,'legacy',500,'PENDING_OWNER_CONFIRMATION','private-destination','2025-01-01');
        """)
        conn.commit()
        conn.close()
        backup_dir = self.root / "backups"
        backup_dir.mkdir()

        first = migrate(source, target, backup_dir)
        self.assertEqual(first["counts"]["tasks"], 2)
        self.assertEqual(first["counts"]["task_events"], 1)
        self.assertEqual(first["counts"]["deliverables"], 1)
        self.assertTrue(Path(first["source_backup"]).is_file())
        self.assertTrue(Path(first["target_backup"]).is_file())
        second = migrate(source, target, backup_dir)
        self.assertEqual(second["counts"]["tasks"], 0)
        self.assertEqual(second["counts"]["task_events"], 0)
        conn = engine.connect(target)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks WHERE task_type='legacy.import'").fetchone()[0], 2)
            old_pending = conn.execute("SELECT state FROM tasks WHERE title='old task'").fetchone()[0]
            self.assertEqual(old_pending, "BLOCKED")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM verified_transactions").fetchone()[0], 0)
            self.assertNotIn("revenue_ledger", {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")})
        finally:
            conn.close()
        legacy_conn = sqlite3.connect(source)
        try:
            self.assertEqual(legacy_conn.execute("SELECT COUNT(*) FROM revenue_ledger").fetchone()[0], 1)
        finally:
            legacy_conn.close()

        import dashboard_data
        old_core_path = dashboard_data.CORE_DB_PATH
        dashboard_data.CORE_DB_PATH = source
        try:
            tasks = dashboard_data.list_core_tasks()
            self.assertEqual(len(tasks), 2)
            self.assertTrue(all(item["task_source"] == "business_engine" for item in tasks))
            activity = dashboard_data.list_activity(limit=10)
            self.assertEqual(len(activity["items"]), 1)
            event_id = activity["items"][0]["event_id"]
            self.assertGreater(event_id, dashboard_data.ENGINE_EVENT_OFFSET)
            self.assertEqual(dashboard_data.task_event_by_id(event_id)["event_source"], "business_engine")
        finally:
            dashboard_data.CORE_DB_PATH = old_core_path

        restored = self.root / "rollback-copy.sqlite"
        restore_to_new_file(Path(first["target_backup"]), restored)
        restored_conn = sqlite3.connect(restored)
        try:
            names = {row[0] for row in restored_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("workflow_records", names)
            self.assertEqual(restored_conn.execute("SELECT COUNT(*) FROM tasks WHERE task_type='legacy.import'").fetchone()[0], 0)
            self.assertEqual(restored_conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            restored_conn.close()
        with self.assertRaises(FileExistsError):
            restore_to_new_file(Path(first["target_backup"]), restored)

    def test_legacy_dashboard_adapter_keeps_unimported_rows_read_only(self):
        import dashboard_data
        legacy = self.root / "legacy-core.sqlite"
        conn = sqlite3.connect(legacy)
        conn.executescript("""
            CREATE TABLE tasks(id INTEGER PRIMARY KEY,title TEXT,assigned_role_id TEXT,status TEXT,cost_vnd REAL,
              created_at TEXT,updated_at TEXT,started_at TEXT,finished_at TEXT,progress_pct INTEGER,run_id TEXT);
            CREATE TABLE task_events(event_id INTEGER PRIMARY KEY,timestamp TEXT,agent_id TEXT,task_id TEXT,
              run_id TEXT,event_type TEXT,status TEXT,title TEXT,description TEXT,duration_ms INTEGER,
              result TEXT,error_details TEXT,metadata_json TEXT,artifact_refs_json TEXT);
            INSERT INTO tasks VALUES(7,'Legacy task','OPS','DONE',0,'2025-01-01','2025-01-01',NULL,'2025-01-01',100,'legacy-run');
            INSERT INTO task_events VALUES(9,'2025-01-01','OPS','7','legacy-run','done','DONE','Legacy event',NULL,1,'ok',NULL,'{}','[]');
        """)
        conn.commit()
        conn.close()
        old = dashboard_data.CORE_DB_PATH
        dashboard_data.CORE_DB_PATH = legacy
        try:
            task = dashboard_data.list_core_tasks()[0]
            self.assertEqual(task["id"], "TASK-LEGACY-7")
            self.assertEqual(task["task_source"], "legacy_core")
            activity = dashboard_data.list_activity()
            self.assertEqual(activity["items"][0]["event_id"], 9)
            self.assertEqual(activity["items"][0]["event_source"], "legacy_core")
            self.assertEqual(dashboard_data.task_event_by_id(9)["task_id"], "7")
            self.assertEqual(dashboard_data.events_after(0)[0]["event_id"], 9)
            self.assertEqual(dashboard_data.current_max_event_id(), 9)
        finally:
            dashboard_data.CORE_DB_PATH = old


class TaskLifecycleTests(EngineTestCase):
    def test_idempotent_creation_immutable_events_and_transition_validation(self):
        spec = TaskSpec(title="Inspect catalog", category="QUALITY", task_type="workflow.quality",
                        payload={"source": "local"}, idempotency_key="same-task-key")
        first = engine.create_task(spec)
        second = engine.create_task(spec)
        self.assertEqual(first["id"], second["id"])
        event_a = engine.record_task_event(first["id"], "diagnostic", TaskState.QUEUED, "safe event",
                                           trace_id=first["trace_id"], idempotency_key="same-event-key")
        event_b = engine.record_task_event(first["id"], "diagnostic", TaskState.QUEUED, "safe event",
                                           trace_id=first["trace_id"], idempotency_key="same-event-key")
        self.assertEqual(event_a, event_b)
        with self.assertRaises(ValueError):
            engine.create_task(TaskSpec(title="Different task", category="QUALITY", task_type="workflow.quality",
                                        idempotency_key="same-task-key"))
        conn = engine.connect()
        try:
            count = conn.execute("SELECT COUNT(*) FROM task_events WHERE task_id=?", (str(first["id"]),)).fetchone()[0]
            self.assertEqual(count, 3)
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE task_events SET title='tampered' WHERE task_id=?", (str(first["id"]),))
            conn.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE tasks SET state='DONE' WHERE id=?", (first["id"],))
            conn.rollback()
        finally:
            conn.close()
        with self.assertRaises(ValueError):
            engine.transition_task(first["id"], TaskState.DONE)

    def test_crash_recovery_lease_heartbeat_and_bounded_timeout(self):
        row = engine.create_task(TaskSpec(title="Recover me", category="BUILD", task_type="workflow.build",
                                         idempotency_key="crash-recovery"))
        # Claim time must be sampled after task creation; otherwise a second
        # boundary can make the queue item not yet available in this test.
        start = engine.utc_now()
        claimed = engine.claim_task("worker-a", lease_seconds=5, now=start)
        self.assertEqual(claimed["id"], row["id"])
        self.assertFalse(engine.heartbeat_task(row["id"], "worker-b", now=start))
        self.assertTrue(engine.heartbeat_task(row["id"], "worker-a", lease_seconds=5, now=start))
        self.assertEqual(engine.recover_crashed_tasks(now=start + timedelta(seconds=6)), 1)
        pending = engine.list_tasks(state="RETRY_PENDING")[0]
        self.assertEqual(pending["last_error"], "worker_lease_expired")
        reclaimed = engine.claim_task("worker-b", lease_seconds=5, now=start + timedelta(seconds=7))
        self.assertEqual(reclaimed["attempts"], 2)
        self.assertEqual(engine.fail_task(row["id"], "worker-b", "timed_out", now=start + timedelta(seconds=8))["state"], "RETRY_PENDING")

        timeout = engine.create_task(TaskSpec(title="Timeout once", category="TEST", task_type="workflow.quality",
                                              max_attempts=1, timeout_seconds=2, idempotency_key="timeout-once"))
        engine.claim_task("worker-c", lease_seconds=30, now=start)
        # Claim in FIFO order above belongs to the oldest available task; isolate the timeout task directly.
        timeout_id = timeout["id"]
        conn = engine.connect()
        try:
            conn.execute("UPDATE tasks SET state='RUNNING',status='RUNNING',attempts=1,started_at=?,lease_owner='worker-timeout',lease_expires_at=? WHERE id=?",
                         (engine.iso(start), engine.iso(start + timedelta(seconds=30)), timeout_id))
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(engine.recover_crashed_tasks(now=start + timedelta(seconds=3)), 1)
        conn = engine.connect()
        try:
            self.assertEqual(conn.execute("SELECT state FROM tasks WHERE id=?", (timeout_id,)).fetchone()[0], "FAILED")
            self.assertEqual(conn.execute("SELECT reason FROM task_dead_letters WHERE task_id=?", (timeout_id,)).fetchone()[0], "task_timeout")
        finally:
            conn.close()

    def test_two_workers_cannot_claim_one_task(self):
        row = engine.create_task(TaskSpec(title="Race", category="BUILD", task_type="workflow.build",
                                         idempotency_key="race-task"))
        barrier = threading.Barrier(3)

        def claim(worker):
            barrier.wait()
            return engine.claim_task(worker)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(claim, "worker-a"), pool.submit(claim, "worker-b")]
            barrier.wait()
            claimed = [future.result(timeout=10) for future in futures]
        winners = [task for task in claimed if task is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0]["id"], row["id"])

    def test_daily_workflow_persists_steps_and_runs_only_verified_local_checks(self):
        conn = engine.connect()
        try:
            conn.execute("INSERT INTO products(slug,name,category,price_usd,description,demo_url,download_count,active) VALUES('test-internal-tool','Test internal tool','INTERNAL_TEST',0.0,'fixture only','/test',0,1)")
            conn.commit()
        finally:
            conn.close()
        first = engine.start_workflow(idempotency_key="manual-run-1")
        repeat = engine.start_workflow(idempotency_key="manual-run-1")
        self.assertEqual(first["id"], repeat["id"])
        for _ in range(6):
            result = engine.run_worker_once("test-worker")
            self.assertIsNotNone(result)
            self.assertEqual(result["state"], "DONE")
        run = engine.get_workflow_run(first["id"])
        self.assertEqual(run["status"], "DONE")
        self.assertEqual(len(run["steps"]), 6)
        self.assertFalse(run["result"]["publish_draft"]["published"])
        self.assertTrue(run["result"]["publish_draft"]["draft_id"])
        self.assertEqual(run["result"]["convert"]["verified_transactions"], 0)
        self.assertEqual(run["result"]["fulfill"]["delivered"], 0)
        conn = engine.connect()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_records WHERE kind='publish_draft'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_events WHERE action='engine_publish_draft_created'").fetchone()[0], 1)
        finally:
            conn.close()

    def test_quality_gate_blocks_then_resumes_after_catalog_fix(self):
        run = engine.start_workflow(idempotency_key="quality-gate-run")
        states = [engine.run_worker_once("quality-worker")["state"] for _ in range(3)]
        self.assertEqual(states, ["DONE", "DONE", "BLOCKED"])
        self.assertEqual(engine.get_workflow_run(run["id"])["status"], "BLOCKED")
        conn = engine.connect()
        try:
            conn.execute("INSERT INTO products(slug,name,category,price_usd,description,demo_url,download_count,active) VALUES('repaired-tool','Repaired tool','INTERNAL_TEST',0.0,'test fixture','/test',0,1)")
            conn.commit()
        finally:
            conn.close()
        self.assertTrue(engine.resume_workflow(run["id"]))
        for _ in range(4):
            self.assertEqual(engine.run_worker_once("quality-worker")["state"], "DONE")
        self.assertEqual(engine.get_workflow_run(run["id"])["status"], "DONE")

    def test_verified_order_delivery_is_transactional_and_idempotent(self):
        conn = engine.connect()
        try:
            now = engine.iso()
            order_id = "verified-order"
            conn.execute("INSERT INTO workflow_records(id,kind,status,payload_json,created_at,updated_at) VALUES(?, 'order','PAID_VERIFIED',?,?,?)",
                         (order_id, '{"product_id":"demo"}', now, now))
            conn.commit()
        finally:
            conn.close()
        first = engine.fulfill_verified_order("verified-order", "demo")
        second = engine.fulfill_verified_order("verified-order", "demo")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["status"], "FULFILLED")
        conn = engine.connect()
        try:
            self.assertEqual(conn.execute("SELECT status FROM orders WHERE id='verified-order'").fetchone()[0], "FULFILLED")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM deliveries WHERE order_id='verified-order'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_events WHERE action='order_delivery_unlocked'").fetchone()[0], 1)
            conn.execute("INSERT INTO workflow_records(id,kind,status,payload_json,created_at,updated_at) VALUES('unpaid-order','order','PENDING_PAYMENT','{}',?,?)",
                         (engine.iso(), engine.iso()))
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(PermissionError):
            engine.fulfill_verified_order("unpaid-order", "demo")

    def test_task_approval_transition_survives_restart(self):
        row = engine.create_task(TaskSpec(title="Needs review", category="PUBLISH", idempotency_key="needs-approval"))
        engine.claim_task("approval-worker")
        running = engine.list_tasks(state="RUNNING")[0]
        engine.transition_task(running["id"], TaskState.WAITING_APPROVAL)
        approved = engine.decide_task_approval(running["id"], "APPROVED")
        self.assertEqual(approved["state"], "QUEUED")
        self.assertEqual(engine.list_tasks(state="QUEUED")[0]["id"], row["id"])
        engine.cancel_task(row["id"])
        rejected = engine.create_task(TaskSpec(title="Reject review", category="PUBLISH", idempotency_key="reject-approval"))
        engine.claim_task("approval-worker-2")
        current = engine.list_tasks(state="RUNNING")[0]
        engine.transition_task(current["id"], TaskState.WAITING_APPROVAL)
        denied = engine.decide_task_approval(current["id"], "REJECTED")
        self.assertEqual(denied["state"], "BLOCKED")
        self.assertNotEqual(rejected["id"], row["id"])

    def test_pause_resume_cancel_and_daily_schedule_idempotency(self):
        day = engine.utc_now()
        run = engine.schedule_daily_workflow(now=day)
        self.assertIsNotNone(run)
        self.assertIsNone(engine.schedule_daily_workflow(now=day))
        engine.pause_workflow(run["id"])
        self.assertIsNone(engine.claim_task("worker-pause"))
        self.assertTrue(engine.resume_workflow(run["id"]))
        self.assertIsNotNone(engine.claim_task("worker-resume"))
        other = engine.start_workflow(idempotency_key="cancel-me")
        self.assertTrue(engine.cancel_workflow(other["id"]))
        self.assertEqual(engine.get_workflow_run(other["id"])["status"], "CANCELLED")


class PolicyAndAnalyticsTests(EngineTestCase):
    def test_unverified_cost_stays_dry_run_and_kill_switch_blocks(self):
        dry_run = engine.invoke_tool("integration.publish", "owner", {"content": "demo"}, dry_run=True)
        self.assertEqual(dry_run["status"], "DRY_RUN")
        blocked = engine.invoke_tool("integration.publish", "owner", {"content": "demo"}, dry_run=False)
        self.assertEqual(blocked["reason_code"], "unknown_cost_or_provider")
        engine.set_engine_control("kill_switch", True)
        blocked = engine.invoke_tool("local.create_draft", "owner", {"title": "draft"}, dry_run=False)
        self.assertEqual(blocked["reason_code"], "kill_switch_enabled")

        paid_tool = "test.paid.action"
        engine.register_tool(engine.ToolDefinition(paid_tool, "test.paid.permission", "provider", "paid_action", 1, False,
                                                   lambda body: {"should_not_run": True}))
        engine.set_engine_control("kill_switch", False)
        engine.grant_privilege("owner", "test.paid.permission")
        approval = engine.request_approval(paid_tool, "owner", {"action": "x"}, idempotency_key="paid-approval")
        engine.decide_approval(approval["id"], "APPROVED")
        paid = engine.invoke_tool(paid_tool, "owner", {"action": "x"}, dry_run=False,
                                  approval_id=approval["id"], idempotency_key="paid-invoke")
        self.assertEqual(paid["reason_code"], "paid_exposure_forbidden")

    def test_internal_offline_draft_tool_is_durable_and_idempotent(self):
        first = engine.invoke_tool("local.create_draft", "owner", {"title": "Review this draft", "content": "Local text"},
                                   dry_run=False, idempotency_key="local-draft-1")
        second = engine.invoke_tool("local.create_draft", "owner", {"title": "Review this draft", "content": "Local text"},
                                    dry_run=False, idempotency_key="local-draft-1")
        self.assertEqual(first["status"], "DONE")
        self.assertEqual(first["result"]["draft_id"], second["result"]["draft_id"])
        conn = engine.connect()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_records WHERE kind='internal_draft'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_events WHERE action='internal_draft_created'").fetchone()[0], 1)
        finally:
            conn.close()

    def test_kill_switch_stops_queue_claim_and_daily_scheduler(self):
        row = engine.create_task(TaskSpec(title="Stopped", category="OPS", idempotency_key="kill-queue"))
        engine.set_engine_control("kill_switch", True)
        self.assertIsNone(engine.claim_task("blocked-worker"))
        self.assertEqual(engine.schedule_daily_workflow(now=engine.utc_now()), None)
        self.assertEqual(engine.list_tasks(state="QUEUED")[0]["id"], row["id"])

    def test_rejected_expired_approval_and_revoked_privilege_are_enforced(self):
        payload = {"content": "approved exact content"}
        rejected_tool = "test.external.rejected"
        engine.register_tool(engine.ToolDefinition(rejected_tool, "test.reject.permission", "verified_provider",
                                                   "test_action", 0, False, lambda body: {"ok": True}))
        engine.grant_privilege("operator", "test.reject.permission")
        rejected = engine.request_approval(rejected_tool, "operator", payload, idempotency_key="approval-reject")
        engine.decide_approval(rejected["id"], "REJECTED")
        result = engine.invoke_tool(rejected_tool, "operator", payload, dry_run=False,
                                    approval_id=rejected["id"], idempotency_key="reject-invoke")
        self.assertEqual(result["reason_code"], "matching_approval_required")

        expiring = engine.request_approval("integration.publish", "operator", payload, idempotency_key="approval-expire")
        with self.assertRaises(TimeoutError):
            engine.decide_approval(expiring["id"], "APPROVED", now=engine.utc_now() + timedelta(hours=2))
        row = next(row for row in engine.list_approvals() if row["id"] == expiring["id"])
        self.assertEqual(row["status"], "EXPIRED")

        called = []
        name = "test.external.zero_cost"
        engine.register_tool(engine.ToolDefinition(name, "test.external.execute", "verified_provider",
                                                   "test_action", 0, False,
                                                   lambda body: called.append(body) or {"ok": True}))
        engine.grant_privilege("operator", "test.external.execute")
        approval = engine.request_approval(name, "operator", payload, idempotency_key="approval-revoke")
        engine.decide_approval(approval["id"], "APPROVED")
        engine.revoke_privilege("operator", "test.external.execute")
        result = engine.invoke_tool(name, "operator", payload, dry_run=False, approval_id=approval["id"],
                                    idempotency_key="revoked-invoke")
        self.assertEqual(result["reason_code"], "exact_privilege_missing_or_revoked")
        self.assertEqual(called, [])

    def test_approved_exact_action_consumes_approval_once_and_checks_payload_hash(self):
        called = []
        name = "test.external.exact"
        engine.register_tool(engine.ToolDefinition(name, "test.exact.permission", "verified_provider",
                                                   "test_action", 0, False,
                                                   lambda body: called.append(dict(body)) or {"accepted": True}))
        engine.grant_privilege("owner", "test.exact.permission")
        payload = {"value": "same"}
        approval = engine.request_approval(name, "owner", payload, idempotency_key="approval-exact")
        engine.decide_approval(approval["id"], "APPROVED")
        mismatched = engine.invoke_tool(name, "owner", {"value": "changed"}, dry_run=False,
                                        approval_id=approval["id"], idempotency_key="changed-payload")
        self.assertEqual(mismatched["reason_code"], "matching_approval_required")
        done = engine.invoke_tool(name, "owner", payload, dry_run=False, approval_id=approval["id"],
                                  idempotency_key="approved-invoke")
        self.assertEqual(done["status"], "DONE")
        self.assertEqual(len(called), 1)
        replay = engine.invoke_tool(name, "owner", payload, dry_run=False, approval_id=approval["id"],
                                    idempotency_key="another-invoke")
        self.assertEqual(replay["reason_code"], "matching_approval_required")
        self.assertEqual(len(called), 1)
        replay_conflict = engine.invoke_tool(name, "owner", {"value": "changed"}, dry_run=False,
                                             approval_id=approval["id"], idempotency_key="approved-invoke")
        self.assertEqual(replay_conflict["reason_code"], "idempotency_key_payload_conflict")

    def test_internal_test_analytics_is_excluded(self):
        session_id = "123e4567-e89b-42d3-a456-426614174020"
        self.assertFalse(engine.record_analytics_event(session_id, "/internal", internal_test=True))
        conn = engine.connect()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM analytics_events WHERE session_id=?", (session_id,)).fetchone()[0], 0)
        finally:
            conn.close()
        self.assertTrue(engine.record_analytics_event(session_id, "/dashboard?secret=query"))
        conn = engine.connect()
        try:
            row = conn.execute("SELECT event_name,internal_test FROM analytics_events WHERE session_id=?", (session_id,)).fetchone()
            self.assertEqual((row[0], row[1]), ("/dashboard", 0))
        finally:
            conn.close()

    def test_schema_validation_and_admin_api_surface(self):
        with self.assertRaises(ValueError):
            TaskSpec(title="", category="OPS")

        import main as backend_main
        from fastapi.testclient import TestClient
        client = TestClient(backend_main.app, base_url="https://testserver")
        self.assertIn(client.get("/api/engine/status").status_code, {401, 403})
        headers = {"X-Admin-Key": os.environ.get("AUTOPROFIT_ADMIN_API_KEY", "")}
        if len(headers["X-Admin-Key"]) < 32:
            headers["X-Admin-Key"] = "phase01-test-key-" + "z" * 40
            os.environ["AUTOPROFIT_ADMIN_API_KEY"] = headers["X-Admin-Key"]
        self.assertEqual(client.get("/api/engine/status", headers=headers).status_code, 200)
        response = client.post("/api/engine/runs", headers=headers, json={"idempotency_key": "api-run-unique", "unexpected": True})
        self.assertEqual(response.status_code, 422)
        response = client.post("/api/engine/runs", headers=headers, json={"idempotency_key": "api-run-unique"})
        self.assertEqual(response.status_code, 202)
        self.assertIn("get", backend_main.app.openapi()["paths"]["/api/engine/events"])
        self.assertEqual(client.post("/api/engine/control/shutdown", headers=headers).status_code, 200)


class OrderIdempotencyTests(EngineTestCase):
    def test_admin_order_retries_return_the_same_order(self):
        import main as backend_main
        from fastapi.testclient import TestClient
        from apps_library import TOOL_DEFINITIONS

        client = TestClient(backend_main.app, base_url="https://testserver")
        headers = {"X-Admin-Key": os.environ["AUTOPROFIT_ADMIN_API_KEY"], "Idempotency-Key": "order-retry-0001"}
        payload = {"customer_id": "customer-test", "product_id": TOOL_DEFINITIONS[0]["slug"],
                   "quantity_units": 1, "discount_usd": 0}
        first = client.post("/api/orders", headers=headers, json=payload)
        second = client.post("/api/orders", headers=headers, json=payload)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(first.json()["order_id"], second.json()["order_id"])
        conflict = client.post("/api/orders", headers=headers,
                               json={**payload, "customer_id": "another-customer"})
        self.assertEqual(conflict.status_code, 409)
        conn = engine.connect()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_events WHERE action='order_created'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM customers WHERE id='customer-test'").fetchone()[0], 1)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
