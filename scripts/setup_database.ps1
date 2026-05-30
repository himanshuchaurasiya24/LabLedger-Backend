#Requires -Version 5.1
<#
.SYNOPSIS
    LabLedger Database Setup Script (Windows / PowerShell)

.DESCRIPTION
    1. Checks if PostgreSQL is installed; prompts user to install if not.
    2. Reads DB credentials from the project-root .env file.
    3. Creates .env with default values if it is missing.
    4. Creates the PostgreSQL role (user) and database if they do not exist.
    5. Runs Django migrations to create all required tables.
    6. Resets the primary-key sequences for every table so new entries
       can be created without conflicts.

.NOTES
    Run this script from any directory - it resolves paths automatically.
    You may need to run PowerShell as Administrator if psql is not in PATH.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
function Write-Info { param($Msg) Write-Host "  [INFO]  $Msg" -ForegroundColor Cyan    }
function Write-Ok   { param($Msg) Write-Host "  [ OK ]  $Msg" -ForegroundColor Green   }
function Write-Warn { param($Msg) Write-Host "  [WARN]  $Msg" -ForegroundColor Yellow  }
function Write-Fail { param($Msg) Write-Host "  [FAIL]  $Msg" -ForegroundColor Red     }
function Write-Step { param($Msg) Write-Host "" ; Write-Host "---  $Msg" -ForegroundColor Magenta }

# ---------------------------------------------------------------------------
# Resolve project root (one level up from /scripts)
# ---------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
$EnvFile   = Join-Path $RootDir '.env'

Write-Host ""
Write-Host "====================================================" -ForegroundColor Blue
Write-Host "     LabLedger -- Database Setup Script             " -ForegroundColor Blue
Write-Host "====================================================" -ForegroundColor Blue
Write-Host ""

# ---------------------------------------------------------------------------
# STEP 1 -- Check PostgreSQL installation
# ---------------------------------------------------------------------------
Write-Step "STEP 1 -- Checking PostgreSQL installation"

$PsqlCmd = Get-Command psql -ErrorAction SilentlyContinue

if (-not $PsqlCmd) {
    # Scan common PostgreSQL installation directories (newest first)
    $CommonPaths = @(
        "C:\Program Files\PostgreSQL\18\bin\psql.exe",
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files\PostgreSQL\15\bin\psql.exe",
        "C:\Program Files\PostgreSQL\14\bin\psql.exe",
        "C:\Program Files\PostgreSQL\13\bin\psql.exe"
    )
    foreach ($p in $CommonPaths) {
        if (Test-Path $p) { $PsqlCmd = $p; break }
    }
}

if (-not $PsqlCmd) {
    Write-Fail "PostgreSQL (psql) was NOT found on this system."
    Write-Host ""
    Write-Host "  Please install PostgreSQL before continuing:" -ForegroundColor Yellow
    Write-Host "  -> https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  After installation, make sure the PostgreSQL bin directory" -ForegroundColor Yellow
    Write-Host "  is added to your PATH, then re-run this script." -ForegroundColor Yellow
    Write-Host ""
    $Answer = Read-Host "  Open the download page in your browser? [Y/n]"
    if ($Answer -eq '' -or $Answer -match '^[Yy]') {
        Start-Process "https://www.postgresql.org/download/windows/"
    }
    exit 1
}

$PsqlExe = if ($PsqlCmd -is [string]) { $PsqlCmd } else { $PsqlCmd.Source }
Write-Ok "PostgreSQL found: $PsqlExe"

$PgBin     = Split-Path -Parent $PsqlExe
$PgIsReady = Join-Path $PgBin 'pg_isready.exe'

# Ensure the PostgreSQL bin folder is on the current process PATH
# so helper functions and child processes can also resolve psql/pg_isready.
if ($env:PATH -notlike "*$PgBin*") {
    $env:PATH = $PgBin + ";" + $env:PATH
    Write-Info "Added PostgreSQL bin to PATH for this session: $PgBin"
}

# ---------------------------------------------------------------------------
# STEP 2 -- Load / create .env
# ---------------------------------------------------------------------------
Write-Step "STEP 2 -- Loading environment variables from .env"

$DefaultEnvLines = @(
    "# LabLedger Backend Environment Variables",
    "# NEVER commit this file to git!",
    "",
    "# Generate a new key with: python -c `"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())`"",
    "DJANGO_SECRET_KEY=change-this-secret-key-before-production",
    "DEBUG=False",
    "ALLOWED_HOSTS=127.0.0.1,localhost",
    "CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://127.0.0.1",
    "CORS_ALLOW_CREDENTIALS=False",
    "USE_HTTPS=False",
    "# Database",
    "DB_ENGINE=django.db.backends.postgresql",
    "DB_NAME=labledger",
    "DB_USER=labledger_user",
    "DB_PASSWORD=your_secure_db_password_here",
    "DB_HOST=localhost",
    "DB_PORT=5432"
)

if (-not (Test-Path $EnvFile)) {
    Write-Warn ".env file not found -- creating one with default values at:"
    Write-Warn "  $EnvFile"
    $DefaultEnvLines | Set-Content -Path $EnvFile -Encoding UTF8
    Write-Ok ".env file created."
} else {
    Write-Ok ".env file found: $EnvFile"
}

# Parse .env into a hashtable
$EnvVars = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ([string]::IsNullOrWhiteSpace($line)) { return }
    if ($line.StartsWith('#'))               { return }
    if ($line -notmatch '=')                { return }

    $parts = $line.Split('=', 2)
    $key   = $parts[0].Trim()
    $val   = $parts[1].Trim()

    if (($val.StartsWith('"') -and $val.EndsWith('"')) -or
        ($val.StartsWith("'") -and $val.EndsWith("'"))) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    $EnvVars[$key] = $val
    [Environment]::SetEnvironmentVariable($key, $val, 'Process')
}

$DB_NAME     = $EnvVars['DB_NAME']
$DB_USER     = $EnvVars['DB_USER']
$DB_PASSWORD = $EnvVars['DB_PASSWORD']
$DB_HOST     = $EnvVars['DB_HOST']
$DB_PORT     = $EnvVars['DB_PORT']

if ([string]::IsNullOrWhiteSpace($DB_PASSWORD) -or $DB_PASSWORD -eq 'your_secure_db_password_here') {
    Write-Fail "DB_PASSWORD is missing or still set to the placeholder value in .env. Update it before running this script."
    exit 1
}

Write-Info "DB_NAME  : $DB_NAME"
Write-Info "DB_USER  : $DB_USER"
Write-Info "DB_HOST  : $DB_HOST"
Write-Info "DB_PORT  : $DB_PORT"

# ---------------------------------------------------------------------------
# STEP 3 -- Verify PostgreSQL server is running
# ---------------------------------------------------------------------------
Write-Step "STEP 3 -- Verifying PostgreSQL server is running"

if (Test-Path $PgIsReady) {
    & $PgIsReady -h $DB_HOST -p $DB_PORT 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "PostgreSQL server is NOT accepting connections on ${DB_HOST}:${DB_PORT}."
        Write-Warn "Make sure the PostgreSQL service is running and try again."
        exit 1
    }
    Write-Ok "PostgreSQL server is accepting connections."
} else {
    Write-Warn "pg_isready not found -- skipping server readiness check."
}

# ---------------------------------------------------------------------------
# Prompt for the PostgreSQL superuser password -- with retry and validation
# (the password you set when installing PostgreSQL, NOT the .env password)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "  The script needs the 'postgres' superuser password." -ForegroundColor Yellow
Write-Host "  This is the password you set during the PostgreSQL" -ForegroundColor Yellow
Write-Host "  installation wizard (NOT the password in .env)." -ForegroundColor Yellow
Write-Host ""

$PG_SUPER_PASSWORD_PLAIN = $null
$maxAttempts = 3

if ($env:POSTGRES_SUPER_PASSWORD) {
    $env:PGPASSWORD = $env:POSTGRES_SUPER_PASSWORD
    & $PsqlExe -h $DB_HOST -p $DB_PORT -U postgres -d postgres -tAc "SELECT 1;" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $PG_SUPER_PASSWORD_PLAIN = $env:POSTGRES_SUPER_PASSWORD
        Write-Ok "Superuser password loaded from POSTGRES_SUPER_PASSWORD."
    } else {
        Write-Warn "POSTGRES_SUPER_PASSWORD is set but authentication failed; falling back to prompt."
    }
}

if (-not $PG_SUPER_PASSWORD_PLAIN) {
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        $securePass = Read-Host "  Enter postgres superuser password (attempt $attempt/$maxAttempts)" -AsSecureString
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
        )

        $env:PGPASSWORD = $plain
        & $PsqlExe -h $DB_HOST -p $DB_PORT -U postgres -d postgres `
                      -tAc "SELECT 1;" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $PG_SUPER_PASSWORD_PLAIN = $plain
            Write-Ok "Superuser password accepted."
            break
        } else {
            Write-Warn "Wrong password. $($maxAttempts - $attempt) attempt(s) remaining."
        }
    }
}

if (-not $PG_SUPER_PASSWORD_PLAIN) {
    Write-Fail "Could not authenticate as postgres after $maxAttempts attempts."
    Write-Host ""
    Write-Host "  If you forgot the postgres superuser password, reset it:" -ForegroundColor Yellow
    Write-Host "  1. Open pgAdmin -> right-click server -> Properties -> Connection" -ForegroundColor Yellow
    Write-Host "  2. OR run in CMD as admin:" -ForegroundColor Yellow
    Write-Host '     net stop postgresql-x64-18' -ForegroundColor Cyan
    Write-Host '     "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "C:\Program Files\PostgreSQL\18\data" start -o "--auth=trust"' -ForegroundColor Cyan
    Write-Host '     psql -U postgres -c "ALTER USER postgres PASSWORD ''NewPassword'';"' -ForegroundColor Cyan
    Write-Host '     net start postgresql-x64-18' -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""

# ---------------------------------------------------------------------------
# Helper: run SQL as the postgres superuser
# ---------------------------------------------------------------------------
function Invoke-Psql {
    param(
        [string]$Sql,
        [string]$SuperUser = 'postgres',
        [string]$Database  = 'postgres'
    )
    $env:PGPASSWORD = $PG_SUPER_PASSWORD_PLAIN
    $result = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $SuperUser -d $Database `
                         -v ON_ERROR_STOP=1 -c $Sql 2>&1
    return $result
}

function Invoke-PsqlAsAppUser {
    param(
        [string]$Sql,
        [string]$Database
    )
    $env:PGPASSWORD = $DB_PASSWORD
    $result = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $Database `
                         -v ON_ERROR_STOP=1 -tAc $Sql 2>&1
    return $result
}

# ---------------------------------------------------------------------------
# STEP 4 -- Create role / user
# ---------------------------------------------------------------------------
Write-Step "STEP 4 -- Creating PostgreSQL role '$DB_USER'"

$RoleExists = Invoke-Psql -Sql "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';"
if ($RoleExists -match '1') {
    Write-Info "Role '$DB_USER' already exists -- syncing password from .env ..."
    Invoke-Psql -Sql "ALTER ROLE `"$DB_USER`" WITH LOGIN PASSWORD '$DB_PASSWORD';" | Out-Null
    Write-Ok "Role '$DB_USER' password synced."
} else {
    Write-Info "Creating role '$DB_USER' ..."
    Invoke-Psql -Sql "CREATE ROLE `"$DB_USER`" WITH LOGIN PASSWORD '$DB_PASSWORD';" | Out-Null
    Write-Ok "Role '$DB_USER' created."
}

# ---------------------------------------------------------------------------
# STEP 5 -- Create database
# ---------------------------------------------------------------------------
Write-Step "STEP 5 -- Creating database '$DB_NAME'"

$DbExists = Invoke-Psql -Sql "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';"
if ($DbExists -match '1') {
    Write-Ok "Database '$DB_NAME' already exists -- skipping creation."
} else {
    Write-Info "Creating database '$DB_NAME' owned by '$DB_USER' ..."
    Invoke-Psql -Sql "CREATE DATABASE `"$DB_NAME`" OWNER `"$DB_USER`";" | Out-Null
    Write-Ok "Database '$DB_NAME' created."
}

Invoke-Psql -Sql "GRANT ALL PRIVILEGES ON DATABASE `"$DB_NAME`" TO `"$DB_USER`";" | Out-Null
Write-Ok "Privileges granted to '$DB_USER' on '$DB_NAME'."

$env:PGPASSWORD = $DB_PASSWORD
& $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT 1;" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Ok "Verified app user '$DB_USER' can connect to '$DB_NAME'."
} else {
    Write-Fail "App user '$DB_USER' cannot connect to '$DB_NAME' with the current .env credentials."
    exit 1
}

# ---------------------------------------------------------------------------
# STEP 6 -- Run Django migrations
# ---------------------------------------------------------------------------
Write-Step "STEP 6 -- Running Django migrations"

$VenvDir   = Join-Path $RootDir 'venv'
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'

if (-not (Test-Path $PythonExe)) {
    Write-Fail "Virtual-environment Python not found at: $PythonExe"
    Write-Warn "Please create the venv first (run runserver.ps1 once, or: python -m venv venv)"
    exit 1
}

Set-Location $RootDir
Write-Info "Running: python manage.py migrate"
& $PythonExe manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Django migration failed. Check the output above."
    exit 1
}
Write-Ok "All migrations applied successfully."

# ---------------------------------------------------------------------------
# STEP 7 -- Reset primary-key sequences (dynamic)
# ---------------------------------------------------------------------------
Write-Step "STEP 7 -- Resetting primary-key sequences"

$env:PGPASSWORD = $DB_PASSWORD

$resetSql = @'
DO $$
DECLARE
    sequence_row record;
    next_value bigint;
    reset_count integer := 0;
BEGIN
    -- short lock timeout to avoid hanging in busy DBs
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
        -- lock the table to avoid races while computing MAX(id)
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
'@

$resetOutput = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
    -v ON_ERROR_STOP=1 -c $resetSql 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Fail "Failed to reset primary-key sequences dynamically."
    $resetOutput | ForEach-Object { Write-Host $_ }
    exit 1
}

if ($resetOutput) {
    $resetOutput | ForEach-Object { Write-Host $_ }
}

Write-Ok "Primary-key sequences reset dynamically for all sequence-backed tables."

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "   [OK]  Database setup completed successfully!     " -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""
Write-Info "Database : $DB_NAME"
Write-Info "User     : $DB_USER"
$hostPort = $DB_HOST + ":" + $DB_PORT
Write-Info "Host     : $hostPort"
Write-Host ""
