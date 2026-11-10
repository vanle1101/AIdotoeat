"""Phase 11 pre-release SQLite backup and restore verification.

This utility does not stop services, migrate live databases, alter permissions,
or deploy production. SQLite's online backup API takes a consistent snapshot
while the source remains live and includes committed WAL content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import stat
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _readonly_connection(path: Path) -> sqlite3.Connection:
    resolved = path.resolve(strict=True)
    uri = resolved.as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=30)


def _integrity(conn: sqlite3.Connection) -> str:
    rows = conn.execute("PRAGMA integrity_check").fetchall()
    return "ok" if rows == [("ok",)] else ";".join(str(row[0]) for row in rows[:20])


def _schema_fingerprint(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT type,name,tbl_name,COALESCE(sql,'') FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    wire = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(wire).hexdigest()


def _schema_version(conn: sqlite3.Connection) -> int | None:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if not exists:
        return None
    row = conn.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()
    return int(row[0]) if row else 0


def _table_row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    names = [str(row[0]) for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    counts: dict[str, int] = {}
    for name in names:
        quoted_name = name.replace('"', '""')
        counts[name] = int(conn.execute(f'SELECT COUNT(*) FROM "{quoted_name}"').fetchone()[0])
    return counts


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mode(path: Path) -> str | None:
    """Return POSIX mode bits; Windows ACLs need a separate verifier."""
    if os.name != "posix":
        return None
    return f"{stat.S_IMODE(path.stat().st_mode):04o}"


def _metadata(path: Path, *, journal_mode: str | None = None) -> dict[str, Any]:
    conn = _readonly_connection(path)
    try:
        integrity = _integrity(conn)
        return {
            "integrity": integrity,
            "schema_version": _schema_version(conn),
            "schema_fingerprint": _schema_fingerprint(conn),
            "journal_mode": journal_mode or str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
            "table_count": int(conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0]),
            "row_counts": _table_row_counts(conn),
        }
    finally:
        conn.close()


def _backup_database(source: Path, destination: Path) -> dict[str, Any]:
    source = source.resolve(strict=True)
    if not source.is_file():
        raise FileNotFoundError("database source is not a regular file")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("backup destination already exists")

    source_stat = source.stat()
    source_conn = _readonly_connection(source)
    try:
        source_journal = str(source_conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        source_integrity = _integrity(source_conn)
        if source_integrity != "ok":
            raise sqlite3.DatabaseError("source integrity check failed")
        source_schema = _schema_fingerprint(source_conn)
        source_version = _schema_version(source_conn)

        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(destination, 0o600)
        destination_conn = sqlite3.connect(str(destination), timeout=60)
        try:
            source_conn.backup(destination_conn, pages=512, sleep=0.05)
            destination_conn.commit()
            backup_integrity = _integrity(destination_conn)
            backup_schema = _schema_fingerprint(destination_conn)
            backup_version = _schema_version(destination_conn)
            backup_row_counts = _table_row_counts(destination_conn)
        finally:
            destination_conn.close()
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        source_conn.close()

    destination_stat = destination.stat()
    if backup_integrity != "ok" or backup_schema != source_schema or backup_version != source_version:
        destination.unlink(missing_ok=True)
        raise sqlite3.DatabaseError("backup verification did not match the SQLite source snapshot")
    return {
        "status": "PASS",
        "source": str(source),
        "source_mode": f"{stat.S_IMODE(source_stat.st_mode):04o}" if os.name == "posix" else None,
        "source_wal_present": Path(str(source) + "-wal").exists(),
        "source_shm_present": Path(str(source) + "-shm").exists(),
        "source_journal_mode": source_journal,
        "source_integrity": source_integrity,
        "schema_version": source_version,
        "schema_fingerprint": source_schema,
        "table_count": _table_count(destination),
        "backup_file": destination.name,
        "backup_mode": f"{stat.S_IMODE(destination_stat.st_mode):04o}" if os.name == "posix" else None,
        "backup_bytes": destination_stat.st_size,
        "backup_sha256": _sha256(destination),
        "backup_integrity": backup_integrity,
        "schema_matches_source": backup_schema == source_schema,
        "row_counts": backup_row_counts,
    }


def _table_count(path: Path) -> int:
    conn = _readonly_connection(path)
    try:
        return int(conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0])
    finally:
        conn.close()


def _verify_restore(backup_file: Path) -> dict[str, Any]:
    backup_file = backup_file.resolve(strict=True)
    before_hash = _sha256(backup_file)
    source = _metadata(backup_file)
    if source["integrity"] != "ok":
        raise sqlite3.DatabaseError("backup integrity check failed before restore test")

    with tempfile.TemporaryDirectory(prefix="phase11-restore-check-") as temp_dir:
        restored = Path(temp_dir) / "restore-check.sqlite"
        os.chmod(temp_dir, 0o700)
        fd = os.open(restored, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
        src = _readonly_connection(backup_file)
        dst = sqlite3.connect(str(restored), timeout=60)
        try:
            src.backup(dst, pages=512, sleep=0.05)
            dst.commit()
            restored_integrity = _integrity(dst)
            restored_schema = _schema_fingerprint(dst)
            restored_version = _schema_version(dst)
            restored_table_count = int(dst.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0])
            restored_row_counts = _table_row_counts(dst)
        finally:
            dst.close()
            src.close()
        restored_mode = stat.S_IMODE(restored.stat().st_mode)
        if (restored_integrity != "ok" or restored_schema != source["schema_fingerprint"]
                or restored_version != source["schema_version"]
            or restored_table_count != source["table_count"]
            or restored_row_counts != source["row_counts"]
            or (os.name == "posix" and restored_mode != 0o600)):
            raise sqlite3.DatabaseError("isolated restore verification failed")

    after_hash = _sha256(backup_file)
    if before_hash != after_hash:
        raise sqlite3.DatabaseError("restore test changed the protected backup")
    return {
        "status": "PASS",
        "source_backup_sha256": before_hash,
        "restored_integrity": restored_integrity,
        "restored_schema_version": restored_version,
        "restored_table_count": restored_table_count,
        "row_counts_match": restored_row_counts == source["row_counts"],
        "restored_mode": f"{restored_mode:04o}" if os.name == "posix" else None,
        "permissions_verifiable": os.name == "posix",
        "backup_unchanged": True,
        "restore_copy_removed": True,
    }


def create_backup_bundle(*, backend_source: Path, core_source: Path | None,
                         backup_parent: Path, run_id: str | None = None) -> dict[str, Any]:
    """Back up present ledgers online and test restoring each to a temp path."""
    backend_source = backend_source.resolve(strict=True)
    backup_parent = backup_parent.resolve(strict=True)
    if not backup_parent.is_dir() or backup_parent.is_symlink():
        raise ValueError("backup parent must be an existing real directory")
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not run_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("run_id must contain only letters, digits, dash, or underscore")
    bundle = backup_parent / f"autoprofit-phase11-{run_id}"
    bundle.mkdir(mode=0o700, exist_ok=False)
    os.chmod(bundle, 0o700)
    try:
        databases: dict[str, Any] = {
            "backend": _backup_database(backend_source, bundle / "backend-company.db")
        }
        databases["backend"]["restore_test"] = _verify_restore(bundle / "backend-company.db")

        if core_source is None or not core_source.exists():
            databases["core"] = {
                "status": "NOT_PRESENT",
                "configured_path": str(core_source) if core_source is not None else None,
                "note": "No core SQLite file was present at the inspected project core path; no empty database was created.",
            }
        else:
            databases["core"] = _backup_database(core_source, bundle / "core-company.db")
            databases["core"]["restore_test"] = _verify_restore(bundle / "core-company.db")

        manifest: dict[str, Any] = {
        "phase": 11,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "sqlite3.Connection.backup online snapshot; committed WAL is included by SQLite",
        "services_stopped": False,
        "production_database_mutated": False,
        "offsite_copy": False,
        "bundle_directory": str(bundle),
        "bundle_mode": _mode(bundle),
        "databases": databases,
        }
        data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
        manifest_path = bundle / "manifest.json"
        fd = os.open(manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.chmod(manifest_path, 0o600)
        if os.name == "posix":
            dir_fd = os.open(bundle, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        manifest["manifest_file"] = manifest_path.name
        manifest["manifest_sha256"] = _sha256(manifest_path)
        manifest["permissions_verifiable"] = os.name == "posix"
        return manifest
    except Exception:
        # This path was created exclusively by this invocation; remove only its
        # incomplete output, never a pre-existing backup bundle.
        shutil.rmtree(bundle, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup_parser = commands.add_parser("backup", help="online backup and isolated restore test")
    backup_parser.add_argument("--backend-source", type=Path, required=True)
    backup_parser.add_argument("--core-source", type=Path)
    backup_parser.add_argument("--backup-parent", type=Path, default=Path("/var/backups"))
    backup_parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    try:
        result = create_backup_bundle(backend_source=args.backend_source,
                                      core_source=args.core_source,
                                      backup_parent=args.backup_parent,
                                      run_id=args.run_id)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"status": "FAIL", "reason_code": type(exc).__name__}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
