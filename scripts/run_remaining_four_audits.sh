#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "error: expected virtualenv python at $PYTHON_BIN" >&2
  exit 2
fi

cd "$ROOT_DIR"

# Use sqlite by default for low-friction local audits.
# Set AUDIT_USE_PROD_DB=1 to use DB_* values from the environment/.env.
if [[ "${AUDIT_USE_PROD_DB:-0}" != "1" ]]; then
  export DB_ENGINE="django.db.backends.sqlite3"
  export DB_NAME="db.sqlite3"
fi

"$PYTHON_BIN" "$ROOT_DIR/scripts/remaining_four_audits.py"
