#!/usr/bin/env bash
set -euo pipefail

# Provision PostgreSQL from values in .env (idempotent).
# Intended for Linux cloud servers where the app and PostgreSQL run on the same host.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing .env file at ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

sql_literal_escape() {
  # Escapes single quotes for SQL string literals.
  local s="$1"
  s="${s//\'/\'\'}"
  printf "%s" "$s"
}

sql_ident_escape() {
  # Escapes double quotes for SQL identifiers.
  local s="$1"
  s="${s//\"/\"\"}"
  printf "%s" "$s"
}

is_local_host() {
  local host="$1"
  [[ -z "$host" || "$host" == "localhost" || "$host" == "127.0.0.1" ]]
}

require_env DB_NAME
require_env DB_USER
require_env DB_PASSWORD
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

if ! command -v psql >/dev/null 2>&1; then
  echo "psql not found. Installing PostgreSQL..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y postgresql postgresql-contrib
  else
    echo "apt-get is not available. Install PostgreSQL manually, then rerun this script." >&2
    exit 1
  fi
fi

if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl enable --now postgresql
fi

if ! is_local_host "$DB_HOST"; then
  echo "DB_HOST is set to ${DB_HOST}."
  echo "Skipping local role/database provisioning because host is non-local."
  echo "Testing remote connectivity with provided credentials..."
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT current_database(), current_user;"
  echo "Remote connectivity check passed."
  exit 0
fi

DB_USER_IDENT="$(sql_ident_escape "$DB_USER")"
DB_NAME_IDENT="$(sql_ident_escape "$DB_NAME")"
DB_USER_SQL="$(sql_literal_escape "$DB_USER")"
DB_NAME_SQL="$(sql_literal_escape "$DB_NAME")"
DB_PASSWORD_SQL="$(sql_literal_escape "$DB_PASSWORD")"

echo "Ensuring PostgreSQL role exists and password is set..."
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER_SQL}') THEN
        CREATE ROLE "${DB_USER_IDENT}" LOGIN PASSWORD '${DB_PASSWORD_SQL}';
    ELSE
        ALTER ROLE "${DB_USER_IDENT}" WITH LOGIN PASSWORD '${DB_PASSWORD_SQL}';
    END IF;
END
\$\$;
SQL

echo "Ensuring database exists..."
DB_EXISTS="$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME_SQL}'" | tr -d '[:space:]')"
if [[ "$DB_EXISTS" != "1" ]]; then
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"${DB_NAME_IDENT}\" OWNER \"${DB_USER_IDENT}\";"
fi

echo "Granting privileges..."
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE \"${DB_NAME_IDENT}\" TO \"${DB_USER_IDENT}\";"

echo "Testing app credentials from .env..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT current_database(), current_user;"

echo "PostgreSQL setup complete for database ${DB_NAME} and user ${DB_USER}."
