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
    "DJANGO_SECRET_KEY=LL2026SecKeyA9F3K8M1PX6RT2VW4XY7ZB0CD5EH9JK3MN8PR1SU4WX7EZ2",
    "DEBUG=False",
    "ALLOWED_HOSTS=127.0.0.1,localhost,80.225.228.15",
    "CORS_ALLOWED_ORIGINS=https://80.225.228.15,https://localhost",
    "CORS_ALLOW_CREDENTIALS=False",
    "USE_HTTPS=True",
    "APP_MODE=development",
    "# APP_MODE=production",
    "# Database",
    "DB_ENGINE=django.db.backends.postgresql",
    "DB_NAME=labledger",
    "DB_USER=labledger_user",
    "DB_PASSWORD=RandomPasswordForLabLedgerPostgreSQL",
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

for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    $securePass = Read-Host "  Enter postgres superuser password (attempt $attempt/$maxAttempts)" -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
    )

    # Test the password with a trivial query before proceeding
    $env:PGPASSWORD = $plain
    $testOut = & $PsqlExe -h $DB_HOST -p $DB_PORT -U postgres -d postgres `
                          -tAc "SELECT 1;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $PG_SUPER_PASSWORD_PLAIN = $plain
        Write-Ok "Superuser password accepted."
        break
    } else {
        Write-Warn "Wrong password. $($maxAttempts - $attempt) attempt(s) remaining."
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
    Write-Ok "Role '$DB_USER' already exists -- skipping creation."
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
# STEP 7 -- Reset primary-key sequences
# ---------------------------------------------------------------------------
Write-Step "STEP 7 -- Resetting primary-key sequences"

$Tables = @(
    # Django built-ins (django_session is excluded -- it uses a text PK, no sequence)
    "django_migrations",
    "django_content_type",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "django_admin_log",
    # center_detail app
    "center_detail_subscriptionplan",
    "center_detail_centerdetail",
    "center_detail_activesubscription",
    # authentication app
    "authentication_staffaccount",
    "authentication_staffaccount_groups",
    "authentication_staffaccount_user_permissions",
    # diagnosis app
    "diagnosis_diagnosiscategory",
    "diagnosis_doctor",
    "diagnosis_doctorcategorypercentage",
    "diagnosis_diagnosistype",
    "diagnosis_auditlog",
    "diagnosis_franchisename",
    "diagnosis_bill",
    "diagnosis_billdiagnosistype",
    "diagnosis_patientreport",
    "diagnosis_sampletestreport"
)

$env:PGPASSWORD = $DB_PASSWORD

foreach ($table in $Tables) {
    $seqName = "${table}_id_seq"

    $seqCheck = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
        -tAc "SELECT 1 FROM pg_sequences WHERE sequencename='$seqName';" 2>&1

    if ($seqCheck -match '1') {
        $resetSql = "SELECT setval('$seqName', COALESCE((SELECT MAX(id) FROM `"$table`"), 0) + 1, false);"
        $output   = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
            -tAc $resetSql 2>&1
        Write-Ok "Reset sequence: $seqName  (next value = $($output.Trim()))"
    } else {
        Write-Warn "Sequence not found (table may not exist yet): $seqName"
    }
}

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
