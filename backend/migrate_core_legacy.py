"""Explicit, backed-up import of the old core SQLite ledger.

This command never deletes or modifies the source database. Restore always
writes to a new destination so rollback cannot silently replace a live file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import business_engine as engine


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _readonly(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def _snapshot(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError("backup destination already exists")
    src = _readonly(source)
    dst = sqlite3.connect(str(destination))
    try:
        src.backup(dst)
        result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise sqlite3.DatabaseError("backup integrity check failed")
        dst.commit()
    finally:
        dst.close()
        src.close()


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _legacy_state(value: Any) -> str:
    status = str(value or "").upper()
    if status in {"DONE", "COMPLETED", "SUCCESS"}:
        return "DONE"
    if status in {"FAILED", "ERROR"}:
        return "FAILED"
    # Historical PENDING/RUNNING/WAITING rows are not replayed after import.
    return "BLOCKED"


def migrate(source: Path, target: Path, backup_dir: Path) -> dict[str, Any]:
    source, target, backup_dir = source.resolve(), target.resolve(), backup_dir.resolve()
    if not source.is_file() or not target.is_file():
        raise FileNotFoundError("source and canonical target databases must already exist")
    if source == target:
        raise ValueError("source and canonical target must be different files")
    if not backup_dir.is_dir():
        raise FileNotFoundError("backup directory must exist; it will not be created automatically")
    stamp = _utc_stamp() + "-" + uuid.uuid4().hex[:8]
    source_backup = backup_dir / f"core-db-{stamp}.sqlite"
    target_backup = backup_dir / f"backend-db-{stamp}.sqlite"
    _snapshot(source, source_backup)
    try:
        _snapshot(target, target_backup)
    except Exception:
        source_backup.unlink(missing_ok=True)
        raise

    engine.ensure_schema(target)
    frozen_source = _readonly(source_backup)
    tables = _tables(frozen_source)
    if "tasks" not in tables:
        frozen_source.close()
        raise ValueError("source database has no tasks table")
    source_identity = str(source)
    source_tag = hashlib.sha256(source_identity.encode("utf-8")).hexdigest()[:16]
    canonical = engine.connect(target)
    imported = {"tasks": 0, "task_events": 0, "deliverables": 0, "revenue_ledger": "preserved_in_source"}
    task_map: dict[str, int] = {}
    try:
        canonical.execute("BEGIN IMMEDIATE")
        task_columns = _columns(frozen_source, "tasks")
        for old in frozen_source.execute("SELECT * FROM tasks ORDER BY id"):
            old = dict(old)
            source_pk = str(old.get("id"))
            mapped = canonical.execute("SELECT target_id FROM legacy_imports WHERE source_db=? AND source_table='tasks' AND source_pk=?",
                                       (source_identity, source_pk)).fetchone()
            if mapped:
                task_map[source_pk] = int(mapped[0])
                continue
            state = _legacy_state(old.get("status"))
            trace_id = str(old.get("run_id") or uuid.uuid4())
            idem = f"legacy:{source_tag}:tasks:{source_pk}"
            details = {"legacy_source": "core/data/company.db", "legacy_task_id": source_pk,
                       "legacy_status": old.get("status"),
                       "legacy_input_present": old.get("input_data") is not None,
                       "legacy_output_present": old.get("output_data") is not None}
            now = engine.iso()
            legacy_title = str(engine.redact(old.get("title") or "Imported legacy task"))[:240]
            legacy_category = str(engine.redact(old.get("category") or "LEGACY"))[:80]
            legacy_role = str(engine.redact(old.get("assigned_role_id") or "LEGACY"))[:80]
            cursor = canonical.execute(
                """INSERT INTO tasks(title,category,assigned_role_id,status,cost_vnd,input_data,output_data,
                   created_at,updated_at,run_id,started_at,finished_at,progress_pct,artifact_refs,task_type,
                   state,state_version,idempotency_key,trace_id,attempts,max_attempts,available_at,
                   timeout_seconds,payload_json,result_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (legacy_title, legacy_category, legacy_role, state, old.get("cost_vnd", 0),
                 None, None, old.get("created_at") or now,
                 old.get("updated_at") or now, old.get("run_id"), old.get("started_at"), old.get("finished_at"),
                 old.get("progress_pct"), old.get("artifact_refs"), "legacy.import", state, 0, idem, trace_id,
                 0, 3, now, 300, json.dumps(engine.redact(details), ensure_ascii=False, default=str),
                 json.dumps({"legacy_output_present": old.get("output_data") is not None}, ensure_ascii=False)),
            )
            new_id = int(cursor.lastrowid)
            task_map[source_pk] = new_id
            canonical.execute("INSERT INTO legacy_imports(source_db,source_table,source_pk,target_id,imported_at) VALUES(?,?,?,?,?)",
                              (source_identity, "tasks", source_pk, str(new_id), now))
            imported["tasks"] += 1

        if "task_events" in tables:
            event_columns = _columns(frozen_source, "task_events")
            order = "event_id" if "event_id" in event_columns else "rowid"
            for old in frozen_source.execute(f"SELECT * FROM task_events ORDER BY {order}"):
                old = dict(old)
                source_pk = str(old.get("event_id", old.get("rowid", "")))
                if not source_pk:
                    continue
                if canonical.execute("SELECT 1 FROM legacy_imports WHERE source_db=? AND source_table='task_events' AND source_pk=?",
                                     (source_identity, source_pk)).fetchone():
                    continue
                source_task_id = str(old.get("task_id", ""))
                target_task_id = task_map.get(source_task_id)
                if target_task_id is None:
                    continue
                trace_id = str(old.get("run_id") or uuid.uuid4())
                event_key = f"legacy:{source_tag}:task_events:{source_pk}"
                canonical.execute(
                    """INSERT OR IGNORE INTO task_events(timestamp,agent_id,task_id,run_id,event_type,status,title,
                       description,source,result,duration_ms,metadata_json,artifact_refs_json,error_details,trace_id,idempotency_key)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (old.get("timestamp") or engine.iso(), engine.redact(old.get("agent_id")), str(target_task_id),
                     old.get("run_id"), str(engine.redact(old.get("event_type") or "legacy_event"))[:80],
                     str(engine.redact(old.get("status") or "UNKNOWN"))[:40], str(engine.redact(old.get("title") or "Legacy event"))[:240],
                     engine.redact(old.get("description")), "legacy_import", engine.redact(old.get("result")),
                     old.get("duration_ms"), json.dumps(engine.redact(old.get("metadata_json") or "{}"), ensure_ascii=False),
                     json.dumps(engine.redact(old.get("artifact_refs_json") or "[]"), ensure_ascii=False),
                     engine.redact(old.get("error_details")), trace_id, event_key),
                )
                canonical.execute("INSERT INTO legacy_imports(source_db,source_table,source_pk,target_id,imported_at) VALUES(?,?,?,?,?)",
                                  (source_identity, "task_events", source_pk, event_key, engine.iso()))
                imported["task_events"] += 1

        if "deliverables" in tables:
            for old in frozen_source.execute("SELECT * FROM deliverables ORDER BY id"):
                old = dict(old)
                source_pk = str(old.get("id"))
                if canonical.execute("SELECT 1 FROM legacy_imports WHERE source_db=? AND source_table='deliverables' AND source_pk=?",
                                     (source_identity, source_pk)).fetchone():
                    continue
                asset_id = f"legacy:deliverables:{source_pk}"
                now = old.get("created_at") or engine.iso()
                canonical.execute(
                    "INSERT OR IGNORE INTO assets(id,name,asset_type,uri,status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (asset_id, str(engine.redact(old.get("name") or "Imported deliverable"))[:240],
                     str(engine.redact(old.get("deliverable_type") or "LEGACY"))[:80], None,
                     str(engine.redact(old.get("owner_status") or "DRAFT"))[:40], json.dumps(engine.redact({
                         "legacy_file_path_present": old.get("file_path") is not None,
                         "legacy_content_preview_present": old.get("content_preview") is not None,
                         "estimated_market_value_vnd": old.get("estimated_market_value_vnd")}), ensure_ascii=False), now, now),
                )
                canonical.execute("INSERT INTO legacy_imports(source_db,source_table,source_pk,target_id,imported_at) VALUES(?,?,?,?,?)",
                                  (source_identity, "deliverables", source_pk, asset_id, engine.iso()))
                imported["deliverables"] += 1
        if "revenue_ledger" in tables:
            imported["revenue_ledger_rows_kept_in_source"] = int(frozen_source.execute("SELECT COUNT(*) FROM revenue_ledger").fetchone()[0])
        canonical.commit()
    except Exception:
        canonical.rollback()
        raise
    finally:
        canonical.close()
        frozen_source.close()
    return {"status": "imported", "source_backup": str(source_backup), "target_backup": str(target_backup),
            "counts": imported, "rollback_output_must_be_new_file": True}


def restore_to_new_file(backup: Path, destination: Path) -> None:
    backup, destination = backup.resolve(), destination.resolve()
    if not backup.is_file():
        raise FileNotFoundError("backup file does not exist")
    if destination.exists():
        raise FileExistsError("restore destination exists; choose a new path")
    destination.parent.mkdir(parents=False, exist_ok=True)
    _snapshot(backup, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument("--source", type=Path, help="legacy core/data/company.db")
    commands.add_argument("--restore-backup", type=Path, help="verified SQLite snapshot to restore")
    parser.add_argument("--target", type=Path, required=True, help="canonical backend SQLite file (or new restore path)")
    parser.add_argument("--backup-dir", type=Path, help="existing directory for pre-migration snapshots")
    args = parser.parse_args()
    if args.restore_backup:
        restore_to_new_file(args.restore_backup, args.target)
        print(json.dumps({"status": "restored_to_new_file", "target": str(args.target.resolve())}))
        return 0
    if not args.backup_dir:
        parser.error("--backup-dir is required for migration")
    result = migrate(args.source, args.target, args.backup_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
