#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"
VENV_DIR="$ROOT_DIR/venv"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "error: missing .env file at $ENV_FILE" >&2
  exit 1
fi

cd "$ROOT_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Creating virtual environment in $VENV_DIR ..."
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$VENV_DIR"
  elif command -v python >/dev/null 2>&1; then
    python -m venv "$VENV_DIR"
  else
    echo "error: python/python3 is not installed" >&2
    exit 2
  fi
fi

echo "Installing/upgrading Python dependencies..."
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
if ! "$PYTHON_BIN" -m pip install -r requirements.txt; then
  echo "First dependency install attempt failed. Retrying once..."
  "$PYTHON_BIN" -m pip cache purge || true
  "$PYTHON_BIN" -m pip install -r requirements.txt
fi

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
