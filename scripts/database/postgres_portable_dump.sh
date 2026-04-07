#!/usr/bin/env bash
set -euo pipefail

# Portable PostgreSQL export/restore helper.
# - export: creates a compressed pg_dump custom-format file (.dump)
# - restore: restores a .dump into a target PostgreSQL database

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
EXPORT_DIR="${ROOT_DIR}/scripts/database/exports"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/database/postgres_portable_dump.sh export [output_file]
  ./scripts/database/postgres_portable_dump.sh restore <dump_file> [target_db]

Behavior:
  - Reads source DB config from .env (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
  - export default output:
      scripts/database/exports/<DB_NAME>_YYYYmmdd_HHMMSS.dump
  - restore target_db defaults to DB_NAME from .env

Examples:
  ./scripts/database/postgres_portable_dump.sh export
  ./scripts/database/postgres_portable_dump.sh export scripts/database/exports/prod_snapshot.dump
  ./scripts/database/postgres_portable_dump.sh restore scripts/database/exports/prod_snapshot.dump other_db
EOF
}

export_db() {
  require_cmd pg_dump
  require_env DB_HOST
  require_env DB_PORT
  require_env DB_NAME
  require_env DB_USER
  require_env DB_PASSWORD

  mkdir -p "${EXPORT_DIR}"

  local output_file="${1:-${EXPORT_DIR}/${DB_NAME}_$(date +%Y%m%d_%H%M%S).dump}"

  export PGPASSWORD="${DB_PASSWORD}"
  pg_dump \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${DB_NAME}" \
    --format=custom \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --verbose \
    --file="${output_file}"

  echo "Export complete: ${output_file}"
  ls -lh "${output_file}"
}

restore_db() {
  require_cmd pg_restore
  require_env DB_HOST
  require_env DB_PORT
  require_env DB_USER
  require_env DB_PASSWORD

  local dump_file="${1:-}"
  local target_db="${2:-${DB_NAME:-}}"

  if [[ -z "${dump_file}" ]]; then
    echo "restore requires <dump_file>" >&2
    usage
    exit 1
  fi

  if [[ ! -f "${dump_file}" ]]; then
    echo "Dump file not found: ${dump_file}" >&2
    exit 1
  fi

  if [[ -z "${target_db}" ]]; then
    echo "Missing target database. Provide [target_db] or set DB_NAME in .env" >&2
    exit 1
  fi

  export PGPASSWORD="${DB_PASSWORD}"
  pg_restore \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --username="${DB_USER}" \
    --dbname="${target_db}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --verbose \
    "${dump_file}"

  echo "Restore complete into database: ${target_db}"
}

main() {
  local action="${1:-}"

  case "${action}" in
    export)
      export_db "${2:-}"
      ;;
    restore)
      restore_db "${2:-}" "${3:-}"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo "Unknown action: ${action}" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
