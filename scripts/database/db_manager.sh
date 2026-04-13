#!/usr/bin/env bash
# =============================================================================
#  LabLedger -- Database Import / Export Manager (Linux / macOS)
# =============================================================================
#
#  EXPORT: Creates a compressed pg_dump backup in scripts/database/exports/
#          with an auto-incremented sequential filename.
#
#  IMPORT: Lists all dump files in the exports folder, lets the user pick
#          one by number, restores it into a fresh database, then resets
#          all primary-key sequences.
#
#  Usage:  bash scripts/database/db_manager.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}  [INFO]  ${NC}$*"; }
ok()    { echo -e "${GREEN}  [ OK ]  ${NC}$*"; }
warn()  { echo -e "${YELLOW}  [WARN]  ${NC}$*"; }
fail()  { echo -e "${RED}  [FAIL]  ${NC}$*"; }
step()  { echo "" ; echo -e "${MAGENTA}${BOLD}---  $* ${NC}"; }

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"  # scripts/database/
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"             # project root
EXPORTS_DIR="$SCRIPT_DIR/exports"
ENV_FILE="$ROOT_DIR/.env"

mkdir -p "$EXPORTS_DIR"

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}====================================================${NC}"
echo -e "${BOLD}    LabLedger -- Database Import / Export Tool      ${NC}"
echo -e "${BOLD}====================================================${NC}"
echo ""

# ---------------------------------------------------------------------------
# STEP 1 -- Locate PostgreSQL binaries
# ---------------------------------------------------------------------------
step "STEP 1 -- Locating PostgreSQL"

if ! command -v psql &>/dev/null; then
    fail "PostgreSQL (psql) not found. Install PostgreSQL and try again."
    exit 1
fi

PSQL_BIN="$(dirname "$(command -v psql)")"
PSQL_EXE="$(command -v psql)"
PG_DUMP_EXE="$PSQL_BIN/pg_dump"
PG_RESTORE_EXE="$PSQL_BIN/pg_restore"
ok "PostgreSQL found: $PSQL_BIN"

# ---------------------------------------------------------------------------
# STEP 2 -- Load .env
# ---------------------------------------------------------------------------
step "STEP 2 -- Loading environment variables from .env"

DEFAULT_ENV='DJANGO_SECRET_KEY=LL2026SecKeyA9F3K8M1PX6RT2VW4XY7ZB0CD5EH9JK3MN8PR1SU4WX7EZ2
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=https://localhost
CORS_ALLOW_CREDENTIALS=False
USE_HTTPS=True
APP_MODE=development
DB_ENGINE=django.db.backends.postgresql
DB_NAME=labledger
DB_USER=labledger_user
DB_PASSWORD=RandomPasswordForLabLedgerPostgreSQL
DB_HOST=localhost
DB_PORT=5432'

if [ ! -f "$ENV_FILE" ]; then
    warn ".env not found -- creating with defaults at: $ENV_FILE"
    printf '%s\n' "$DEFAULT_ENV" > "$ENV_FILE"
fi

parse_env() {
    local file="$1"
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%%#*}"
        line="${line//[$'\r']}"
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" || "$line" != *=* ]] && continue
        local key="${line%%=*}" val="${line#*=}"
        [[ ( "$val" == \"*\" ) || ( "$val" == \'*\' ) ]] && val="${val:1:${#val}-2}"
        export "$key=$val"
    done < "$file"
}
parse_env "$ENV_FILE"

DB_NAME="${DB_NAME:-labledger}"
DB_USER="${DB_USER:-labledger_user}"
DB_PASSWORD="${DB_PASSWORD:-RandomPasswordForLabLedgerPostgreSQL}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

ok ".env loaded -- DB: $DB_NAME  User: $DB_USER  Host: ${DB_HOST}:${DB_PORT}"

# ---------------------------------------------------------------------------
# STEP 3 -- Verify PostgreSQL is running
# ---------------------------------------------------------------------------
step "STEP 3 -- Verifying PostgreSQL server"

if command -v pg_isready &>/dev/null; then
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; then
        fail "PostgreSQL is not accepting connections on ${DB_HOST}:${DB_PORT}."
        exit 1
    fi
fi
ok "PostgreSQL server is running."

# ---------------------------------------------------------------------------
# STEP 4 -- postgres superuser password (with retry)
# ---------------------------------------------------------------------------
step "STEP 4 -- Authenticate as postgres superuser"
echo ""
echo -e "  ${YELLOW}Enter the 'postgres' superuser password (set during installation).${NC}"
echo ""

PG_SUPER_PASSWORD=""
for attempt in 1 2 3; do
    # Read password without echo
    read -r -s -p "  Password (attempt $attempt/3): " PG_SUPER_PASSWORD_TRY
    echo ""
    export PGPASSWORD="$PG_SUPER_PASSWORD_TRY"
    if psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d postgres -tAc "SELECT 1;" &>/dev/null; then
        PG_SUPER_PASSWORD="$PG_SUPER_PASSWORD_TRY"
        ok "Password accepted."
        break
    else
        remaining=$((3 - attempt))
        warn "Wrong password. $remaining attempt(s) remaining."
    fi
done

if [ -z "$PG_SUPER_PASSWORD" ]; then
    fail "Authentication failed after 3 attempts. Exiting."
    exit 1
fi
echo ""

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
run_super_sql() {
    local sql="$1"
    local db="${2:-postgres}"
    PGPASSWORD="$PG_SUPER_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
        -U postgres -d "$db" -v ON_ERROR_STOP=1 -c "$sql" 2>&1
}

run_app_sql() {
    local sql="$1"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -tAc "$sql" 2>&1
}

reset_sequences() {
    step "Resetting primary-key sequences"
    local tables=(
        "django_migrations" "django_content_type" "auth_permission"
        "auth_group" "auth_group_permissions" "django_admin_log"
        "center_detail_subscriptionplan" "center_detail_centerdetail"
        "center_detail_activesubscription"
        "authentication_staffaccount" "authentication_staffaccount_groups"
        "authentication_staffaccount_user_permissions"
        "diagnosis_diagnosiscategory" "diagnosis_doctor"
        "diagnosis_doctorcategorypercentage" "diagnosis_diagnosistype"
        "diagnosis_auditlog" "diagnosis_franchisename"
        "diagnosis_bill" "diagnosis_billdiagnosistype"
        "diagnosis_patientreport" "diagnosis_sampletestreport"
    )
    export PGPASSWORD="$DB_PASSWORD"
    for tbl in "${tables[@]}"; do
        local seq="${tbl}_id_seq"
        local exists
        exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -tAc "SELECT 1 FROM pg_sequences WHERE sequencename='$seq';" 2>/dev/null || true)
        if [ "$exists" = "1" ]; then
            local next_val
            next_val=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
                -tAc "SELECT setval('$seq', COALESCE((SELECT MAX(id) FROM \"$tbl\"), 0) + 1, false);" \
                2>/dev/null | tr -d '[:space:]')
            ok "Reset: $seq  (next = $next_val)"
        fi
    done
}

# ---------------------------------------------------------------------------
# STEP 5 -- Main menu
# ---------------------------------------------------------------------------
step "STEP 5 -- Choose operation"
echo ""
echo -e "  ${CYAN}[1]  EXPORT  -- Dump current database to the exports folder${NC}"
echo -e "  ${CYAN}[2]  IMPORT  -- Restore a dump file into the database${NC}"
echo ""
read -r -p "  Enter choice [1 or 2]: " choice
echo ""

# ===========================================================================
# EXPORT
# ===========================================================================
if [ "$choice" = "1" ]; then
    step "EXPORT -- Creating database dump"

    # Count existing .dump files to determine the next sequential number
    existing_count=$(find "$EXPORTS_DIR" -maxdepth 1 -name "*.dump" | wc -l | tr -d '[:space:]')
    next_num=$(( existing_count + 1 ))
    date_str=$(date '+%Y-%m-%d_%H-%M-%S')
    file_name="labledger_backup_$(printf '%03d' "$next_num")_${date_str}.dump"
    file_path="$EXPORTS_DIR/$file_name"

    info "Exporting database '$DB_NAME' ..."
    info "Target: $file_path"
    echo ""

    export PGPASSWORD="$DB_PASSWORD"
    "$PG_DUMP_EXE" -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -Fc -d "$DB_NAME" -f "$file_path"

    if [ ! -f "$file_path" ]; then
        fail "Export failed -- output file not created."
        exit 1
    fi

    size_bytes=$(wc -c < "$file_path" | tr -d '[:space:]')
    size_mb=$(echo "scale=2; $size_bytes / 1048576" | bc)
    echo ""
    ok "Export complete!"
    info "File : $file_name"
    info "Size : ${size_mb} MB"
    info "Path : $EXPORTS_DIR"

# ===========================================================================
# IMPORT
# ===========================================================================
elif [ "$choice" = "2" ]; then
    step "IMPORT -- Select a dump file to restore"

    # Collect dump files sorted by name
    mapfile -t dump_files < <(find "$EXPORTS_DIR" -maxdepth 1 -name "*.dump" | sort)

    if [ "${#dump_files[@]}" -eq 0 ]; then
        fail "No dump files found in: $EXPORTS_DIR"
        warn "Run an EXPORT first to create a backup."
        exit 1
    fi

    echo ""
    echo -e "  ${CYAN}Available backup files:${NC}"
    echo ""
    for i in "${!dump_files[@]}"; do
        f="${dump_files[$i]}"
        fname="$(basename "$f")"
        size_bytes=$(wc -c < "$f" | tr -d '[:space:]')
        size_mb=$(echo "scale=2; $size_bytes / 1048576" | bc)
        mod_date=$(date -r "$f" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || stat -c '%y' "$f" 2>/dev/null | cut -d'.' -f1)
        printf "  [%d]  %s  (%.2f MB)  %s\n" "$((i + 1))" "$fname" "$size_mb" "$mod_date"
    done
    echo ""

    read -r -p "  Enter the number of the file to restore: " sel
    idx=$(( sel - 1 ))

    if [ "$idx" -lt 0 ] || [ "$idx" -ge "${#dump_files[@]}" ]; then
        fail "Invalid selection '$sel'. Exiting."
        exit 1
    fi

    selected_file="${dump_files[$idx]}"
    selected_name="$(basename "$selected_file")"

    # ---- Choose import mode ----
    echo ""
    echo -e "  ${CYAN}How do you want to import '$selected_name'?${NC}"
    echo ""
    echo -e "  ${YELLOW}[1]  FULL RESTORE  -- Drop the database and replace with exact dump state${NC}"
    echo -e "       (WARNING: all current data will be permanently erased)"
    echo ""
    echo -e "  ${GREEN}[2]  MERGE         -- Keep existing data, insert NEW records from dump${NC}"
    echo -e "       (skips records whose ID already exists in the database)"
    echo ""
    read -r -p "  Enter mode [1 or 2]: " import_mode
    echo ""

    if [ "$import_mode" != "1" ] && [ "$import_mode" != "2" ]; then
        fail "Invalid mode '$import_mode'. Exiting."
        exit 1
    fi

    # ---- Confirmation ----
    if [ "$import_mode" = "1" ]; then
        warn "WARNING: ALL current data in '$DB_NAME' will be permanently replaced!"
        warn "Source file: $selected_name"
        echo ""
        read -r -p "  Type YES to confirm FULL RESTORE: " confirm
    else
        info "MERGE mode: existing records are kept; new records from the dump are added."
        info "Source file: $selected_name"
        echo ""
        read -r -p "  Type YES to confirm MERGE: " confirm
    fi

    if [ "$confirm" != "YES" ]; then
        info "Import cancelled."
        exit 0
    fi
    echo ""

    # ==========================================================================
    # MODE 1 -- FULL RESTORE (drop + recreate)
    # ==========================================================================
    if [ "$import_mode" = "1" ]; then

        # Terminate active connections
        step "Terminating active connections to '$DB_NAME'"
        run_super_sql "SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" > /dev/null || true
        ok "Active connections terminated."

        # Drop and recreate database
        step "Recreating database '$DB_NAME'"
        run_super_sql "DROP DATABASE IF EXISTS \"$DB_NAME\";" > /dev/null
        ok "Dropped '$DB_NAME'."
        run_super_sql "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" > /dev/null
        run_super_sql "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";" > /dev/null
        ok "Recreated '$DB_NAME'."

        # Restore full dump
        step "Restoring from: $selected_name"
        export PGPASSWORD="$DB_PASSWORD"
        "$PG_RESTORE_EXE" -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            --no-owner --role="$DB_USER" -Fc "$selected_file" || true
        ok "Full restore completed."

    # ==========================================================================
    # MODE 2 -- MERGE (data only, ON CONFLICT DO NOTHING)
    # ==========================================================================
    else

        step "Merging data from: $selected_name"
        info "Existing records in '$DB_NAME' are kept."
        info "New records from the dump are inserted; duplicates are skipped."
        echo ""

        # How this works:
        #   pg_restore cannot generate INSERT statements from a binary dump.
        #   So we:
        #   1. Restore the dump into a temporary staging database.
        #   2. pg_dump --data-only --inserts the staging DB -> plain SQL INSERTs.
        #   3. sed patches every INSERT line to add ON CONFLICT DO NOTHING.
        #   4. Run the patched SQL against the main database.
        #   5. Drop the staging database, delete the temp SQL file.

        temp_db="labledger_merge_staging"
        temp_sql="/tmp/labledger_merge_$$.sql"

        # Step 1: Create staging DB and restore dump
        info "Step 1/4 -- Restoring dump into staging database '$temp_db' ..."
        run_super_sql "DROP DATABASE IF EXISTS \"$temp_db\";" > /dev/null || true
        run_super_sql "CREATE DATABASE \"$temp_db\" OWNER \"$DB_USER\";" > /dev/null
        run_super_sql "GRANT ALL PRIVILEGES ON DATABASE \"$temp_db\" TO \"$DB_USER\";" > /dev/null

        export PGPASSWORD="$DB_PASSWORD"
        "$PG_RESTORE_EXE" -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$temp_db" \
                          --no-owner -Fc "$selected_file" 2>/dev/null || true
        ok "Dump restored to staging database."

        # Step 2: Export staging data as plain INSERT SQL
        info "Step 2/4 -- Exporting staging data as INSERT statements ..."
        export PGPASSWORD="$DB_PASSWORD"
        "$PG_DUMP_EXE" -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$temp_db" \
                       --data-only --inserts -f "$temp_sql" 2>/dev/null

        if [ ! -f "$temp_sql" ]; then
            fail "Failed to export INSERT SQL from staging database."
            run_super_sql "DROP DATABASE IF EXISTS \"$temp_db\";" > /dev/null || true
            exit 1
        fi
        ok "INSERT SQL exported."

        # Step 3: Patch every INSERT line with ON CONFLICT DO NOTHING
        info "Step 3/4 -- Patching INSERTs with ON CONFLICT DO NOTHING ..."
        sed -i -E 's/^(INSERT INTO .+);$/\1 ON CONFLICT DO NOTHING;/' "$temp_sql"
        ok "SQL patched."

        # Step 4: Execute patched SQL against the main database
        info "Step 4/4 -- Inserting new records into '$DB_NAME' (skipping duplicates) ..."
        export PGPASSWORD="$DB_PASSWORD"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
             -v ON_ERROR_STOP=0 -f "$temp_sql" 2>&1 | \
             grep -i 'ERROR' | while read -r line; do warn "$line"; done || true

        # Cleanup
        rm -f "$temp_sql"
        run_super_sql "DROP DATABASE IF EXISTS \"$temp_db\";" > /dev/null || true
        ok "Merge completed. Staging database removed."
    fi

    # Reset sequences (both modes)
    reset_sequences

else
    fail "Invalid choice '$choice'. Run the script again and enter 1 or 2."
    exit 1
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}====================================================${NC}"
echo -e "${GREEN}${BOLD}   [OK]  Operation completed successfully!          ${NC}"
echo -e "${GREEN}${BOLD}====================================================${NC}"
echo ""
