#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-}"
shift || true
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
VENV="${AUTOPROFIT_VENV:-$ROOT/.venv}"
PY="$VENV/bin/python"

case "$ACTION" in
  install)
    WITH_BROWSER=false
    for arg in "$@"; do
      if [[ "$arg" == "--with-browser" ]]; then WITH_BROWSER=true; else
        echo "Unknown install option: $arg" >&2
        exit 2
      fi
    done
    if [[ ! -x "$PY" ]]; then "$PYTHON_BIN" -m venv "$VENV"; fi
    if [[ -n "${AUTOPROFIT_WHEELHOUSE:-}" ]]; then
      "$PY" -m pip install --require-hashes --no-index --find-links "$AUTOPROFIT_WHEELHOUSE" -r "$ROOT/requirements-dev.lock.txt"
    else
      "$PY" -m pip install --require-hashes -r "$ROOT/requirements-dev.lock.txt"
    fi
    if [[ ! -e "$ROOT/.env" ]]; then
      cp "$ROOT/.env.example" "$ROOT/.env"
      chmod 600 "$ROOT/.env"
      echo "Created .env from placeholders; existing .env files are never overwritten."
    fi
    if [[ "$WITH_BROWSER" == true ]]; then "$PY" -m playwright install chromium; fi
    ;;
  start)
    exec "$PY" -m uvicorn main:app --app-dir "$ROOT/backend" --host 127.0.0.1 --port 8450 --workers 1
    ;;
  check)
    exec "$PY" "$ROOT/scripts/ops.py" check "${1:---url}" "${2:-http://127.0.0.1:8450}"
    ;;
  migrate)
    exec "$PY" "$ROOT/scripts/ops.py" migrate "$@"
    ;;
  backup)
    exec "$PY" "$ROOT/scripts/ops.py" backup "$@"
    ;;
  restore)
    exec "$PY" "$ROOT/scripts/ops.py" restore "$@"
    ;;
  rollback)
    exec "$PY" "$ROOT/scripts/ops.py" rollback "$@"
    ;;
  *)
    echo "Usage: bash scripts/manage.sh {install [--with-browser]|start|check|migrate|backup|restore|rollback} [options]" >&2
    exit 2
    ;;
esac
