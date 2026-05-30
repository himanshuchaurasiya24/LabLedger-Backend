#!/usr/bin/env bash
# =============================================================================
#  LabLedger — Database Setup Script (Linux / macOS)
# =============================================================================
#
#  What this script does:
#    1. Checks if PostgreSQL is installed; prompts user to install if missing.
#    2. Reads DB credentials from the project-root .env file.
#    3. Creates a default .env if it is missing.
#    4. Creates the PostgreSQL role (user) and database if they do not exist.
#    5. Runs Django migrations to build all required tables.
#    6. Resets the primary-key sequences for every model table so new
#       entries can be inserted without ID-sequence conflicts.
#
#  Usage:  bash scripts/setup_database.sh
#          (Run from any directory — the script resolves paths itself.)
# =============================================================================

set -euo pipefail

# ─────────────────────────────────────────────
#  Colour helpers
# ─────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}  [INFO]  ${NC}$*"; }
ok()    { echo -e "${GREEN}  [ OK ]  ${NC}$*"; }
warn()  { echo -e "${YELLOW}  [WARN]  ${NC}$*"; }
fail()  { echo -e "${RED}  [FAIL]  ${NC}$*"; }
step()  { echo -e "\n${MAGENTA}${BOLD}━━━  $* ${NC}"; }

# ─────────────────────────────────────────────
#  Resolve project root (one level up from /scripts)
# ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        LabLedger — Database Setup Script             ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ─────────────────────────────────────────────
#  STEP 1 — Check PostgreSQL installation
# ─────────────────────────────────────────────
step "STEP 1 — Checking PostgreSQL installation"

if ! command -v psql &>/dev/null; then
    fail "PostgreSQL (psql) was NOT found on this system."
    echo ""
    warn "Please install PostgreSQL, then re-run this script."
    echo ""
    # Detect distro and suggest the right install command
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian)
                echo -e "  ${YELLOW}Suggested command:${NC}"
                echo "    sudo apt update && sudo apt install -y postgresql postgresql-contrib"
                ;;
            fedora|rhel|centos|rocky|almalinux)
                echo -e "  ${YELLOW}Suggested command:${NC}"
                echo "    sudo dnf install -y postgresql-server postgresql-contrib"
                echo "    sudo postgresql-setup --initdb"
                echo "    sudo systemctl enable --now postgresql"
                ;;
            arch|manjaro)
                echo -e "  ${YELLOW}Suggested command:${NC}"
                echo "    sudo pacman -S postgresql"
                echo "    sudo -u postgres initdb -D /var/lib/postgres/data"
                echo "    sudo systemctl enable --now postgresql"
                ;;
            *)
                echo -e "  ${YELLOW}Visit:${NC} https://www.postgresql.org/download/linux/"
                ;;
        esac
    elif [[ "$(uname)" == "Darwin" ]]; then
        echo -e "  ${YELLOW}Suggested command (Homebrew):${NC}"
        echo "    brew install postgresql@16"
        echo "    brew services start postgresql@16"
    else
        echo -e "  ${YELLOW}Visit:${NC} https://www.postgresql.org/download/"
    fi
    echo ""
    exit 1
fi

PSQL_BIN="$(dirname "$(command -v psql)")"
ok "PostgreSQL found: $(command -v psql)"

# ─────────────────────────────────────────────
#  STEP 2 — Load / create .env
# ─────────────────────────────────────────────
step "STEP 2 — Loading environment variables from .env"

DEFAULT_ENV_CONTENT='# LabLedger Backend Environment Variables
# NEVER commit this file to git!

# Generate a new key with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DJANGO_SECRET_KEY=change-this-secret-key-before-production
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://127.0.0.1
CORS_ALLOW_CREDENTIALS=False
USE_HTTPS=False
# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=labledger
DB_USER=labledger_user
DB_PASSWORD=your_secure_db_password_here
DB_HOST=localhost
DB_PORT=5432
'

if [ ! -f "$ENV_FILE" ]; then
    warn ".env file not found — creating one with default values at:"
    warn "  $ENV_FILE"
    printf '%s' "$DEFAULT_ENV_CONTENT" > "$ENV_FILE"
    ok ".env file created."
else
    ok ".env file found: $ENV_FILE"
fi

# Parse .env (ignore comments and blank lines)
parse_env() {
    local file="$1"
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%%#*}"          # strip inline comments
        line="${line//[$'\r']}"     # strip CR (Windows line endings)
        line="${line#"${line%%[![:space:]]*}"}"  # ltrim
        line="${line%"${line##*[![:space:]]}"}"  # rtrim
        [[ -z "$line" || "$line" != *=* ]] && continue
        local key="${line%%=*}"
        local val="${line#*=}"
        # Strip surrounding quotes
        if [[ ( "$val" == \"*\" ) || ( "$val" == \'*\' ) ]]; then
            val="${val:1:${#val}-2}"
        fi
        export "$key=$val"
    done < "$file"
}

parse_env "$ENV_FILE"

DB_NAME="${DB_NAME:-labledger}"
DB_USER="${DB_USER:-labledger_user}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

if [ -z "$DB_PASSWORD" ] || [ "$DB_PASSWORD" = "your_secure_db_password_here" ]; then
    fail "DB_PASSWORD is missing or still set to the placeholder value in .env. Update it before running this script."
    exit 1
fi

info "DB_NAME  : $DB_NAME"
info "DB_USER  : $DB_USER"
info "DB_HOST  : $DB_HOST"
info "DB_PORT  : $DB_PORT"

# ─────────────────────────────────────────────
#  STEP 3 — Verify PostgreSQL server is running
# ─────────────────────────────────────────────
step "STEP 3 — Verifying PostgreSQL server is running"

if command -v pg_isready &>/dev/null; then
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; then
        fail "PostgreSQL server is NOT accepting connections on ${DB_HOST}:${DB_PORT}."
        warn "Start PostgreSQL and try again."
        warn "  sudo systemctl start postgresql   # systemd"
        warn "  brew services start postgresql@16  # macOS Homebrew"
        exit 1
    fi
    ok "PostgreSQL server is accepting connections."
else
    warn "pg_isready not found — skipping server readiness check."
fi

# ─────────────────────────────────────────────
#  Superuser authentication mode
# ─────────────────────────────────────────────
step "STEP 4 — Authenticating as PostgreSQL superuser"

SUPER_AUTH_MODE=""
PG_SUPER_PASSWORD=""

if [ -n "${POSTGRES_SUPER_PASSWORD:-}" ] && \
   PGPASSWORD="$POSTGRES_SUPER_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
   -U postgres -d postgres -tAc "SELECT 1;" &>/dev/null; then
    SUPER_AUTH_MODE="password"
    PG_SUPER_PASSWORD="$POSTGRES_SUPER_PASSWORD"
    ok "Authenticated via POSTGRES_SUPER_PASSWORD environment variable."
elif sudo -n -u postgres psql -d postgres -tAc "SELECT 1;" &>/dev/null; then
    SUPER_AUTH_MODE="sudo"
    ok "Authenticated via OS postgres user (sudo, non-interactive)."
elif sudo -u postgres psql -d postgres -tAc "SELECT 1;" &>/dev/null; then
    SUPER_AUTH_MODE="sudo"
    ok "Authenticated via OS postgres user (sudo)."
else
    warn "Sudo/peer auth unavailable. Enter postgres DB superuser password."
    for attempt in 1 2 3; do
        read -r -s -p "  Password (attempt $attempt/3): " PG_SUPER_PASSWORD_TRY
        echo ""
        if PGPASSWORD="$PG_SUPER_PASSWORD_TRY" psql -h "$DB_HOST" -p "$DB_PORT" \
            -U postgres -d postgres -tAc "SELECT 1;" &>/dev/null; then
            SUPER_AUTH_MODE="password"
            PG_SUPER_PASSWORD="$PG_SUPER_PASSWORD_TRY"
            ok "Password accepted."
            break
        else
            remaining=$((3 - attempt))
            warn "Wrong password. $remaining attempt(s) remaining."
        fi
    done
fi

if [ -z "$SUPER_AUTH_MODE" ]; then
    fail "Could not authenticate as postgres superuser. Exiting."
    exit 1
fi

# ─────────────────────────────────────────────
#  Helper: run SQL as the postgres superuser
# ─────────────────────────────────────────────
run_as_super() {
    local sql="$1"
    local db="${2:-postgres}"
    if [ "$SUPER_AUTH_MODE" = "sudo" ]; then
        sudo -u postgres psql -d "$db" -v ON_ERROR_STOP=1 -c "$sql" 2>&1
    else
        PGPASSWORD="$PG_SUPER_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
            -U postgres -d "$db" -v ON_ERROR_STOP=1 -c "$sql" 2>&1
    fi
}

run_as_app_user() {
    local sql="$1"
    local db="${2:-$DB_NAME}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$db" -v ON_ERROR_STOP=1 -tAc "$sql" 2>&1
}

# ─────────────────────────────────────────────
#  STEP 5 — Create role / user
# ─────────────────────────────────────────────
step "STEP 5 — Creating PostgreSQL role '$DB_USER'"

ROLE_EXISTS=$(run_as_super "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" | grep -c '1' || true)
if [ "$ROLE_EXISTS" -ge 1 ]; then
    info "Role '$DB_USER' already exists — syncing password from .env ..."
    run_as_super "ALTER ROLE \"$DB_USER\" WITH LOGIN PASSWORD '$DB_PASSWORD';" > /dev/null
    ok "Role '$DB_USER' password synced."
else
    info "Creating role '$DB_USER' ..."
    run_as_super "CREATE ROLE \"$DB_USER\" WITH LOGIN PASSWORD '$DB_PASSWORD';" > /dev/null
    ok "Role '$DB_USER' created."
fi

# ─────────────────────────────────────────────
#  STEP 6 — Create database
# ─────────────────────────────────────────────
step "STEP 6 — Creating database '$DB_NAME'"

DB_EXISTS=$(run_as_super "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" | grep -c '1' || true)
if [ "$DB_EXISTS" -ge 1 ]; then
    ok "Database '$DB_NAME' already exists — skipping creation."
else
    info "Creating database '$DB_NAME' owned by '$DB_USER' ..."
    run_as_super "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" > /dev/null
    ok "Database '$DB_NAME' created."
fi

run_as_super "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";" > /dev/null
ok "Privileges granted to '$DB_USER' on '$DB_NAME'."

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1;" >/dev/null 2>&1; then
    ok "Verified app user '$DB_USER' can connect to '$DB_NAME'."
else
    fail "App user '$DB_USER' cannot connect to '$DB_NAME' with the current .env credentials."
    exit 1
fi

# ─────────────────────────────────────────────
#  STEP 7 — Run Django migrations
# ─────────────────────────────────────────────
step "STEP 7 — Running Django migrations"

PYTHON_EXE="$ROOT_DIR/venv/bin/python"

if [ ! -f "$PYTHON_EXE" ]; then
    fail "Virtual-environment Python not found at: $PYTHON_EXE"
    warn "Please create the venv first:"
    echo "    cd $ROOT_DIR"
    echo "    python3 -m venv venv"
    echo "    source venv/bin/activate"
    echo "    pip install -r requirements.txt"
    exit 1
fi

cd "$ROOT_DIR"
info "Running: python manage.py migrate"
"$PYTHON_EXE" manage.py migrate
ok "All migrations applied successfully."

# ─────────────────────────────────────────────
#  STEP 8 — Reset primary-key sequences
# ─────────────────────────────────────────────
step "STEP 8 — Resetting primary-key sequences"
export PGPASSWORD="$DB_PASSWORD"

read -r -d '' RESET_SQL <<'SQL' || true
DO $$
DECLARE
    sequence_row record;
    next_value bigint;
    reset_count integer := 0;
BEGIN
    PERFORM set_config('lock_timeout', '5s', true);

    FOR sequence_row IN
        SELECT
            seq_ns.nspname AS sequence_schema,
            seq.relname AS sequence_name,
            tbl_ns.nspname AS table_schema,
            tbl.relname AS table_name,
            att.attname AS column_name
        FROM pg_class seq
        JOIN pg_depend dep
            ON dep.objid = seq.oid
           AND dep.deptype IN ('a', 'i')
        JOIN pg_class tbl
            ON tbl.oid = dep.refobjid
        JOIN pg_namespace tbl_ns
            ON tbl_ns.oid = tbl.relnamespace
        JOIN pg_attribute att
            ON att.attrelid = tbl.oid
           AND att.attnum = dep.refobjsubid
        JOIN pg_namespace seq_ns
            ON seq_ns.oid = seq.relnamespace
        WHERE seq.relkind = 'S'
          AND tbl.relkind IN ('r', 'p')
          AND tbl_ns.nspname NOT IN ('pg_catalog', 'information_schema')
          AND seq_ns.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY tbl_ns.nspname, tbl.relname, att.attname
    LOOP
        EXECUTE format('LOCK TABLE %I.%I IN ACCESS EXCLUSIVE MODE', sequence_row.table_schema, sequence_row.table_name);
        EXECUTE format(
            'SELECT COALESCE(MAX(%I), 0) + 1 FROM %I.%I',
            sequence_row.column_name,
            sequence_row.table_schema,
            sequence_row.table_name
        ) INTO next_value;
        EXECUTE format(
            'SELECT setval(%L, %s, false)',
            format('%I.%I', sequence_row.sequence_schema, sequence_row.sequence_name),
            next_value
        );
        reset_count := reset_count + 1;
    END LOOP;

    RAISE NOTICE 'Reset % sequence(s).', reset_count;
END $$;
SQL

reset_output=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
    -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "$RESET_SQL" 2>&1)

if [ $? -ne 0 ]; then
    fail "Failed to reset primary-key sequences dynamically."
    printf '%s\n' "$reset_output"
    exit 1
fi

if [ -n "$reset_output" ]; then
    printf '%s\n' "$reset_output"
fi

ok "Primary-key sequences reset dynamically for all sequence-backed tables."

# ─────────────────────────────────────────────
#  Done
# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║   ✅  Database setup completed successfully!         ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
info "Database : $DB_NAME"
info "User     : $DB_USER"
info "Host     : $DB_HOST:$DB_PORT"
echo ""
