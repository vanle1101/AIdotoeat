"""Portable migration, SQLite backup/restore, and HTTP readiness commands."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _json_print(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _readonly_connection(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=30)


def _db_path() -> Path:
    import database
    return Path(database.DB_PATH).resolve()


def _integrity(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "missing_result"


def backup(source: Path, destination: Path) -> dict:
    source, destination = source.resolve(), destination.resolve()
    if not source.is_file():
        raise FileNotFoundError("source database does not exist")
    if source == destination:
        raise ValueError("backup destination must differ from source")
    if destination.exists():
        raise FileExistsError("backup destination already exists; choose a new path")
    if not destination.parent.is_dir():
        raise FileNotFoundError("backup directory must already exist")
    src = _readonly_connection(source)
    dst = sqlite3.connect(str(destination), timeout=30)
    try:
        src.backup(dst)
        result = _integrity(dst)
        if result != "ok":
            raise sqlite3.DatabaseError("backup integrity check failed")
        dst.commit()
    except Exception:
        dst.close()
        src.close()
        destination.unlink(missing_ok=True)
        raise
    finally:
        try:
            dst.close()
        finally:
            src.close()
    try:
        os.chmod(destination, 0o600)
    except OSError:
        pass
    check = sqlite3.connect(f"file:{destination.as_posix()}?mode=ro", uri=True)
    try:
        version = check.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()[0]
    except sqlite3.Error:
        version = 0
    finally:
        check.close()
    return {"status": "backup_verified", "path": str(destination), "integrity": result,
            "schema_version": int(version), "bytes": destination.stat().st_size}


def restore(source: Path, destination: Path) -> dict:
    source, destination = source.resolve(), destination.resolve()
    if not source.is_file():
        raise FileNotFoundError("backup source does not exist")
    if source == destination:
        raise ValueError("restore destination must differ from backup")
    if destination.exists():
        raise FileExistsError("restore destination already exists; restore never overwrites a database")
    if not destination.parent.is_dir():
        raise FileNotFoundError("restore destination directory must already exist")
    src = _readonly_connection(source)
    dst = sqlite3.connect(str(destination), timeout=30)
    try:
        src.backup(dst)
        result = _integrity(dst)
        if result != "ok":
            raise sqlite3.DatabaseError("restored database integrity check failed")
        dst.commit()
    except Exception:
        dst.close()
        src.close()
        destination.unlink(missing_ok=True)
        raise
    finally:
        try:
            dst.close()
        finally:
            src.close()
    try:
        os.chmod(destination, 0o600)
    except OSError:
        pass
    restored = sqlite3.connect(f"file:{destination.as_posix()}?mode=ro", uri=True)
    try:
        version = restored.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()[0]
    except sqlite3.Error:
        version = 0
    finally:
        restored.close()
    return {"status": "restored_to_new_path", "path": str(destination),
            "integrity": result, "schema_version": int(version), "source_unchanged": True}


def migrate(backup_path: Path | None) -> dict:
    source = _db_path()
    if source.exists():
        if backup_path is None:
            raise ValueError("existing database migration requires --backup to a new destination")
        backup_result = backup(source, backup_path)
    else:
        backup_result = None
    import database
    import business_engine
    database.init_db()
    version = business_engine.ensure_schema()
    conn = business_engine.connect()
    try:
        integrity = _integrity(conn)
    finally:
        conn.close()
    if integrity != "ok":
        raise sqlite3.DatabaseError("post-migration database integrity check failed")
    return {"status": "migrated", "schema_version": version, "integrity": integrity,
            "backup": backup_result}


def rollback_release(releases_root: Path, current_link: Path, target_name: str) -> dict:
    """Atomically repoint a Linux release symlink without touching database files."""
    if os.name != "posix":
        raise OSError("release symlink rollback is supported on Linux/POSIX only")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", target_name):
        raise ValueError("target must be one release directory name")
    root = releases_root.resolve(strict=True)
    link = current_link.absolute()
    if link.parent.resolve(strict=True) != root.parent:
        raise ValueError("current symlink must be a sibling of the releases directory")
    if not link.is_symlink():
        raise ValueError("current path must already be a symlink; refusing to replace a directory or file")
    target = (root / target_name).resolve(strict=True)
    if target.parent != root or not target.is_dir():
        raise ValueError("target must be an existing immediate child directory of releases_root")
    previous = os.readlink(link)
    temp_link = link.with_name(f".{link.name}.rollback-{os.getpid()}")
    if temp_link.exists() or temp_link.is_symlink():
        raise FileExistsError("temporary rollback link already exists")
    try:
        os.symlink(os.path.relpath(target, link.parent), temp_link, target_is_directory=True)
        os.replace(temp_link, link)
    finally:
        if temp_link.is_symlink() or temp_link.exists():
            temp_link.unlink()
    return {"status": "release_symlink_switched", "previous_target": previous,
            "current_target": os.readlink(link), "service_restart_required": True,
            "database_untouched": True}


def check(base_url: str) -> int:
    result: dict[str, object] = {"base_url": base_url.rstrip("/"), "health": "unavailable", "readiness": "unavailable"}
    ok = True
    for name, endpoint in (("health", "/api/health"), ("readiness", "/api/ready")):
        request = urllib.request.Request(base_url.rstrip("/") + endpoint, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=6) as response:
                payload = json.loads(response.read(64_000).decode("utf-8"))
                value = str(payload.get("status", "unknown"))
                result[name] = value
                if response.status != 200 or (name == "readiness" and value != "ready"):
                    ok = False
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
            result[name] = "unavailable"
            ok = False
    _json_print(result)
    return 0 if ok else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Safe AUTOProfit database and health operations")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="back up an existing DB, then apply additive migrations")\
        .add_argument("--backup", type=Path, help="new backup destination; required if the DB already exists")
    backup_parser = commands.add_parser("backup", help="create and integrity-check a consistent SQLite backup")
    backup_parser.add_argument("--destination", type=Path, required=True)
    restore_parser = commands.add_parser("restore", help="restore to a new path without overwriting an existing DB")
    restore_parser.add_argument("--source", type=Path, required=True)
    restore_parser.add_argument("--destination", type=Path, required=True)
    check_parser = commands.add_parser("check", help="check liveness and readiness without using admin credentials")
    check_parser.add_argument("--url", default="http://127.0.0.1:8450")
    rollback_parser = commands.add_parser("rollback", help="atomically switch a Linux current symlink to an existing release")
    rollback_parser.add_argument("--releases-root", type=Path, required=True)
    rollback_parser.add_argument("--current-link", type=Path, required=True)
    rollback_parser.add_argument("--target", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "migrate":
            _json_print(migrate(args.backup))
        elif args.command == "backup":
            _json_print(backup(_db_path(), args.destination))
        elif args.command == "restore":
            _json_print(restore(args.source, args.destination))
        elif args.command == "check":
            return check(args.url)
        elif args.command == "rollback":
            _json_print(rollback_release(args.releases_root, args.current_link, args.target))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        _json_print({"status": "failed", "reason_code": type(exc).__name__})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
