#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f "manage.py" ]]; then
  echo "Error: manage.py not found in $PROJECT_ROOT" >&2
  exit 1
fi

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

PYTHON_BIN="python3"
if [[ -x "$PROJECT_ROOT/venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"
fi

DRY_RUN="false"
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN="true"
fi

export RESET_PK_DRY_RUN="$DRY_RUN"

"$PYTHON_BIN" manage.py shell <<'PYCODE'
import os
from django.apps import apps
from django.db import connection

dry_run = os.environ.get("RESET_PK_DRY_RUN", "false").lower() == "true"
vendor = connection.vendor
print(f"Vendor: {vendor}")

if vendor != "postgresql":
  raise SystemExit("This script supports PostgreSQL only.")

reset_count = 0
skipped = 0

with connection.cursor() as cursor:
  for model in apps.get_models():
    table = model._meta.db_table
    pk = model._meta.pk

    if not pk or getattr(pk, "column", None) != "id":
      skipped += 1
      continue

    cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
    row = cursor.fetchone()
    seq = row[0] if row else None

    if not seq:
      skipped += 1
      continue

    if dry_run:
      print(f"[DRY RUN] {table} -> {seq}")
      continue

    cursor.execute(
      f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
    )
    reset_count += 1

print(f"Reset sequences: {reset_count}, skipped: {skipped}")
PYCODE