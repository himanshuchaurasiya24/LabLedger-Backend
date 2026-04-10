#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "error: expected virtualenv python at $PYTHON_BIN" >&2
  exit 2
fi

cd "$ROOT_DIR"

# Load environment settings if available.
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

# Use sqlite only when explicitly requested.
if [[ "${AUDIT_USE_SQLITE:-0}" == "1" ]]; then
  export DB_ENGINE="django.db.backends.sqlite3"
  export DB_NAME="db.sqlite3"
fi

"$PYTHON_BIN" "$ROOT_DIR/scripts/data_quality_audit.py"
