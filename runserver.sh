#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "error: missing .env file at $ENV_FILE" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "error: expected virtualenv python at $PYTHON_BIN" >&2
  exit 2
fi

cd "$ROOT_DIR"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  echo "error: DJANGO_SECRET_KEY is not set after loading .env" >&2
  exit 3
fi

HOST="${RUNSERVER_HOST:-0.0.0.0}"
PORT="${RUNSERVER_PORT:-8000}"

echo "Starting Django server at http://${HOST}:${PORT}/"
exec "$PYTHON_BIN" manage.py runserver "${HOST}:${PORT}"
