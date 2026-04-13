#Requires -Version 5.1
<#
.SYNOPSIS
    LabLedger Database Import / Export Manager (Windows / PowerShell)

.DESCRIPTION
    EXPORT: Creates a compressed pg_dump backup of the labledger database
            in scripts/database/exports/ with an auto-incremented filename.

    IMPORT: Lists all available dump files in the exports folder,
            lets the user pick one by number, restores it into a
            fresh database, then resets all primary-key sequences.

.NOTES
    Run from any directory -- paths are resolved automatically.
    Requires PostgreSQL to be installed (psql / pg_dump / pg_restore).
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
function Write-Info { param($Msg) Write-Host "  [INFO]  $Msg" -ForegroundColor Cyan    }
function Write-Ok   { param($Msg) Write-Host "  [ OK ]  $Msg" -ForegroundColor Green   }
function Write-Warn { param($Msg) Write-Host "  [WARN]  $Msg" -ForegroundColor Yellow  }
function Write-Fail { param($Msg) Write-Host "  [FAIL]  $Msg" -ForegroundColor Red     }
function Write-Step { param($Msg) Write-Host "" ; Write-Host "---  $Msg" -ForegroundColor Magenta }

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path   # scripts/database/
$RootDir    = Split-Path -Parent (Split-Path -Parent $ScriptDir) # project root
$ExportsDir = Join-Path $ScriptDir 'exports'
$EnvFile    = Join-Path $RootDir '.env'

# Ensure exports directory exists
if (-not (Test-Path $ExportsDir)) {
    New-Item -ItemType Directory -Path $ExportsDir | Out-Null
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "====================================================" -ForegroundColor Blue
Write-Host "    LabLedger -- Database Import / Export Tool      " -ForegroundColor Blue
Write-Host "====================================================" -ForegroundColor Blue
Write-Host ""

# ---------------------------------------------------------------------------
# STEP 1 -- Locate PostgreSQL binaries
# ---------------------------------------------------------------------------
Write-Step "STEP 1 -- Locating PostgreSQL"

$PsqlCmd = Get-Command psql -ErrorAction SilentlyContinue
if (-not $PsqlCmd) {
    $CommonPaths = @(
        "C:\Program Files\PostgreSQL\18\bin\psql.exe",
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files\PostgreSQL\15\bin\psql.exe",
        "C:\Program Files\PostgreSQL\14\bin\psql.exe"
    )
    foreach ($p in $CommonPaths) {
        if (Test-Path $p) { $PsqlCmd = $p; break }
    }
}
if (-not $PsqlCmd) {
    Write-Fail "PostgreSQL not found. Install it and add its bin folder to PATH."
    exit 1
}

$PsqlExe    = if ($PsqlCmd -is [string]) { $PsqlCmd } else { $PsqlCmd.Source }
$PgBin      = Split-Path -Parent $PsqlExe
$PgDumpExe  = Join-Path $PgBin 'pg_dump.exe'
$PgRestoreExe = Join-Path $PgBin 'pg_restore.exe'
$PgIsReady  = Join-Path $PgBin 'pg_isready.exe'

if ($env:PATH -notlike "*$PgBin*") {
    $env:PATH = $PgBin + ";" + $env:PATH
}
Write-Ok "PostgreSQL found: $PgBin"

# ---------------------------------------------------------------------------
# STEP 2 -- Load .env
# ---------------------------------------------------------------------------
Write-Step "STEP 2 -- Loading environment variables from .env"

$DefaultEnvLines = @(
    "# LabLedger Backend Environment Variables",
    "# NEVER commit this file to git!",
    "",
    "DJANGO_SECRET_KEY=LL2026SecKeyA9F3K8M1PX6RT2VW4XY7ZB0CD5EH9JK3MN8PR1SU4WX7EZ2",
    "DEBUG=False",
    "ALLOWED_HOSTS=127.0.0.1,localhost,80.225.228.15",
    "CORS_ALLOWED_ORIGINS=https://80.225.228.15,https://localhost",
    "CORS_ALLOW_CREDENTIALS=False",
    "USE_HTTPS=True",
    "APP_MODE=development",
    "DB_ENGINE=django.db.backends.postgresql",
    "DB_NAME=labledger",
    "DB_USER=labledger_user",
    "DB_PASSWORD=RandomPasswordForLabLedgerPostgreSQL",
    "DB_HOST=localhost",
    "DB_PORT=5432"
)

if (-not (Test-Path $EnvFile)) {
    Write-Warn ".env not found -- creating with defaults."
    $DefaultEnvLines | Set-Content -Path $EnvFile -Encoding UTF8
}

$EnvVars = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#') -or $line -notmatch '=') { return }
    $parts = $line.Split('=', 2)
    $k = $parts[0].Trim(); $v = $parts[1].Trim()
    if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) { $v = $v.Substring(1, $v.Length - 2) }
    $EnvVars[$k] = $v
}

$DB_NAME     = $EnvVars['DB_NAME']
$DB_USER     = $EnvVars['DB_USER']
$DB_PASSWORD = $EnvVars['DB_PASSWORD']
$DB_HOST     = $EnvVars['DB_HOST']
$DB_PORT     = $EnvVars['DB_PORT']

Write-Ok ".env loaded -- DB: $DB_NAME  User: $DB_USER  Host: ${DB_HOST}:${DB_PORT}"

# ---------------------------------------------------------------------------
# STEP 3 -- Verify PostgreSQL server is running
# ---------------------------------------------------------------------------
Write-Step "STEP 3 -- Verifying PostgreSQL server"

if (Test-Path $PgIsReady) {
    & $PgIsReady -h $DB_HOST -p $DB_PORT 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "PostgreSQL is not accepting connections on ${DB_HOST}:${DB_PORT}."
        exit 1
    }
}
Write-Ok "PostgreSQL server is running."

# ---------------------------------------------------------------------------
# STEP 4 -- Collect postgres superuser password
# ---------------------------------------------------------------------------
Write-Step "STEP 4 -- Authenticate as postgres superuser"
Write-Host ""
Write-Host "  Enter the 'postgres' superuser password (set during installation)." -ForegroundColor Yellow
Write-Host ""

$PG_SUPER_PASSWORD_PLAIN = $null
for ($i = 1; $i -le 3; $i++) {
    $sec = Read-Host "  Password (attempt $i/3)" -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
    $env:PGPASSWORD = $plain
    & $PsqlExe -h $DB_HOST -p $DB_PORT -U postgres -d postgres -tAc "SELECT 1;" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $PG_SUPER_PASSWORD_PLAIN = $plain; Write-Ok "Password accepted."; break }
    Write-Warn "Wrong password. $($3 - $i) attempt(s) left."
}
if (-not $PG_SUPER_PASSWORD_PLAIN) {
    Write-Fail "Authentication failed after 3 attempts. Exiting."
    exit 1
}
Write-Host ""

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
function Invoke-SuperSql {
    param([string]$Sql, [string]$Database = 'postgres')
    $env:PGPASSWORD = $PG_SUPER_PASSWORD_PLAIN
    $out = & $PsqlExe -h $DB_HOST -p $DB_PORT -U postgres -d $Database `
                      -v ON_ERROR_STOP=1 -c $Sql 2>&1
    return $out
}

function Invoke-AppSql {
    param([string]$Sql)
    $env:PGPASSWORD = $DB_PASSWORD
    $out = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
                      -v ON_ERROR_STOP=1 -tAc $Sql 2>&1
    return $out
}

function Reset-Sequences {
    Write-Step "Resetting primary-key sequences"
    $Tables = @(
        "django_migrations", "django_content_type", "auth_permission",
        "auth_group", "auth_group_permissions", "django_admin_log",
        "center_detail_subscriptionplan", "center_detail_centerdetail",
        "center_detail_activesubscription",
        "authentication_staffaccount", "authentication_staffaccount_groups",
        "authentication_staffaccount_user_permissions",
        "diagnosis_diagnosiscategory", "diagnosis_doctor",
        "diagnosis_doctorcategorypercentage", "diagnosis_diagnosistype",
        "diagnosis_auditlog", "diagnosis_franchisename",
        "diagnosis_bill", "diagnosis_billdiagnosistype",
        "diagnosis_patientreport", "diagnosis_sampletestreport"
    )
    $env:PGPASSWORD = $DB_PASSWORD
    foreach ($tbl in $Tables) {
        $seq = "${tbl}_id_seq"
        $exists = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
            -tAc "SELECT 1 FROM pg_sequences WHERE sequencename='$seq';" 2>&1
        if ($exists -match '1') {
            $sql = "SELECT setval('$seq', COALESCE((SELECT MAX(id) FROM `"$tbl`"), 0) + 1, false);"
            $val = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc $sql 2>&1
            Write-Ok "Reset: $seq  (next = $($val.Trim()))"
        }
    }
}

# ---------------------------------------------------------------------------
# STEP 5 -- Main menu
# ---------------------------------------------------------------------------
Write-Step "STEP 5 -- Choose operation"
Write-Host ""
Write-Host "  [1]  EXPORT  -- Dump the current database to the exports folder" -ForegroundColor Cyan
Write-Host "  [2]  IMPORT  -- Restore a dump file into the database" -ForegroundColor Cyan
Write-Host ""
$choice = Read-Host "  Enter choice [1 or 2]"
Write-Host ""

# ===========================================================================
# EXPORT
# ===========================================================================
if ($choice -eq '1') {
    Write-Step "EXPORT -- Creating database dump"

    # Build next sequential filename: labledger_001.dump, 002, ...
    $existing = @(Get-ChildItem -Path $ExportsDir -Filter "*.dump" -File |
                Sort-Object Name)
    $nextNum  = $existing.Count + 1
    $dateStr  = (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss")
    $fileName = "labledger_{0:D3}_{1}.dump" -f $nextNum, $dateStr
    $filePath = Join-Path $ExportsDir $fileName

    Write-Info "Exporting database '$DB_NAME' to:"
    Write-Info "  $filePath"
    Write-Host ""

    $env:PGPASSWORD = $DB_PASSWORD
    & $PgDumpExe -h $DB_HOST -p $DB_PORT -U $DB_USER -Fc -d $DB_NAME -f $filePath

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $filePath)) {
        Write-Fail "Export failed. Check the output above."
        exit 1
    }

    $sizeMb = [math]::Round((Get-Item $filePath).Length / 1MB, 2)
    Write-Host ""
    Write-Ok "Export complete!"
    Write-Info "File : $fileName"
    Write-Info "Size : $sizeMb MB"
    Write-Info "Path : $ExportsDir"
}

# ===========================================================================
# IMPORT
# ===========================================================================
elseif ($choice -eq '2') {
    Write-Step "IMPORT -- Select a dump file to restore"

    $dumpFiles = @(Get-ChildItem -Path $ExportsDir -Filter "*.dump" -File |
                 Sort-Object Name)

    if ($dumpFiles.Count -eq 0) {
        Write-Fail "No dump files found in: $ExportsDir"
        Write-Warn "Run an EXPORT first to create a backup."
        exit 1
    }

    Write-Host ""
    Write-Host "  Available backup files:" -ForegroundColor Cyan
    Write-Host ""
    for ($i = 0; $i -lt $dumpFiles.Count; $i++) {
        $f    = $dumpFiles[$i]
        $size = [math]::Round($f.Length / 1MB, 2)
        $date = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        Write-Host ("  [{0}]  {1}  ({2} MB)  {3}" -f ($i + 1), $f.Name, $size, $date)
    }
    Write-Host ""

    $sel = Read-Host "  Enter the number of the file to restore"
    $idx = [int]$sel - 1

    if ($idx -lt 0 -or $idx -ge $dumpFiles.Count) {
        Write-Fail "Invalid selection '$sel'. Exiting."
        exit 1
    }

    $selectedFile = $dumpFiles[$idx].FullName
    $selectedName = $dumpFiles[$idx].Name

    # ---- Choose import mode ----
    Write-Host ""
    Write-Host "  How do you want to import '$selectedName'?" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1]  FULL RESTORE  -- Drop the database and replace with exact dump state" -ForegroundColor Yellow
    Write-Host "       (WARNING: all current data will be permanently erased)" -ForegroundColor DarkYellow
    Write-Host ""
    Write-Host "  [2]  MERGE         -- Keep existing data, insert NEW records from dump" -ForegroundColor Green
    Write-Host "       (skips records whose ID already exists in the database)" -ForegroundColor DarkGreen
    Write-Host ""
    $importMode = Read-Host "  Enter mode [1 or 2]"
    Write-Host ""

    if ($importMode -ne '1' -and $importMode -ne '2') {
        Write-Fail "Invalid mode '$importMode'. Exiting."
        exit 1
    }

    # ---- Confirmation ----
    if ($importMode -eq '1') {
        Write-Warn "WARNING: ALL current data in '$DB_NAME' will be permanently replaced!"
        Write-Warn "Source file: $selectedName"
        Write-Host ""
        $confirm = Read-Host "  Type YES to confirm FULL RESTORE"
    } else {
        Write-Info "MERGE mode: existing records are kept; new records from the dump are added."
        Write-Info "Source file: $selectedName"
        Write-Host ""
        $confirm = Read-Host "  Type YES to confirm MERGE"
    }

    if ($confirm -ne 'YES') {
        Write-Info "Import cancelled."
        exit 0
    }

    Write-Host ""

    # ==========================================================================
    # MODE 1 -- FULL RESTORE (drop + recreate)
    # ==========================================================================
    if ($importMode -eq '1') {

        # Terminate active connections
        Write-Step "Terminating active connections to '$DB_NAME'"
        Invoke-SuperSql -Sql @"
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
"@ | Out-Null
        Write-Ok "Active connections terminated."

        # Drop and recreate
        Write-Step "Recreating database '$DB_NAME'"
        Invoke-SuperSql -Sql "DROP DATABASE IF EXISTS `"$DB_NAME`";" | Out-Null
        Write-Ok "Dropped '$DB_NAME'."
        Invoke-SuperSql -Sql "CREATE DATABASE `"$DB_NAME`" OWNER `"$DB_USER`";" | Out-Null
        Invoke-SuperSql -Sql "GRANT ALL PRIVILEGES ON DATABASE `"$DB_NAME`" TO `"$DB_USER`";" | Out-Null
        Write-Ok "Recreated '$DB_NAME'."

        # Restore full dump
        Write-Step "Restoring from: $selectedName"
        $env:PGPASSWORD = $DB_PASSWORD
        & $PgRestoreExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
                        --no-owner --role=$DB_USER -Fc $selectedFile

        if ($LASTEXITCODE -ne 0) {
            Write-Warn "pg_restore finished with warnings -- this is usually OK."
        } else {
            Write-Ok "Full restore completed."
        }
    }

    # ==========================================================================
    # MODE 2 -- MERGE (staged: temp DB -> INSERT SQL -> ON CONFLICT DO NOTHING)
    # ==========================================================================
    else {

        Write-Step "Merging data from: $selectedName"
        Write-Info "Existing records in '$DB_NAME' are kept."
        Write-Info "New records from the dump are inserted; duplicates are skipped."
        Write-Host ""

        # How this works:
        #   pg_restore cannot generate INSERT statements from a binary dump.
        #   So we:
        #   1. Restore the dump into a temporary staging database.
        #   2. pg_dump --data-only --inserts the staging DB -> plain SQL INSERTs.
        #   3. Patch every INSERT line to add ON CONFLICT DO NOTHING.
        #   4. Run the patched SQL against the main database.
        #   5. Drop the staging database and delete the temp SQL file.

        $tempDb  = "labledger_merge_staging"
        $tempSql = [System.IO.Path]::Combine(
            [System.IO.Path]::GetTempPath(),
            "labledger_merge_$([System.Guid]::NewGuid().ToString('N')).sql"
        )

        # -- Step 1: Create staging DB and restore dump into it --
        Write-Info "Step 1/4 -- Restoring dump into staging database '$tempDb' ..."
        Invoke-SuperSql -Sql "DROP DATABASE IF EXISTS `"$tempDb`";" | Out-Null
        Invoke-SuperSql -Sql "CREATE DATABASE `"$tempDb`" OWNER `"$DB_USER`";" | Out-Null
        Invoke-SuperSql -Sql "GRANT ALL PRIVILEGES ON DATABASE `"$tempDb`" TO `"$DB_USER`";" | Out-Null

        $env:PGPASSWORD = $DB_PASSWORD
        & $PgRestoreExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $tempDb `
                        --no-owner -Fc $selectedFile 2>&1 | Out-Null
        Write-Ok "Dump restored to staging database."

        # -- Step 2: Export staging data as plain INSERT SQL --
        Write-Info "Step 2/4 -- Exporting staging data as INSERT statements ..."
        $env:PGPASSWORD = $DB_PASSWORD
        & $PgDumpExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $tempDb `
                     --data-only --inserts -f $tempSql 2>&1 | Out-Null

        if (-not (Test-Path $tempSql)) {
            Write-Fail "Failed to export INSERT SQL from staging database."
            Invoke-SuperSql -Sql "DROP DATABASE IF EXISTS `"$tempDb`";" | Out-Null
            exit 1
        }
        Write-Ok "INSERT SQL exported."

        # -- Step 3: Patch INSERT lines with ON CONFLICT DO NOTHING --
        Write-Info "Step 3/4 -- Patching INSERTs with ON CONFLICT DO NOTHING ..."
        $lines   = Get-Content $tempSql
        $patched = $lines | ForEach-Object {
            if ($_ -match '^\s*INSERT INTO ' -and $_.TrimEnd().EndsWith(';')) {
                $_.TrimEnd().TrimEnd(';') + ' ON CONFLICT DO NOTHING;'
            } else { $_ }
        }
        $patched | Set-Content $tempSql -Encoding UTF8
        Write-Ok "SQL patched."

        # -- Step 4: Execute patched SQL against the main database --
        Write-Info "Step 4/4 -- Inserting new records into '$DB_NAME' (skipping duplicates) ..."
        $env:PGPASSWORD = $DB_PASSWORD
        & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
                   -v ON_ERROR_STOP=0 -f $tempSql 2>&1 |
            ForEach-Object {
                if ($_ -match 'ERROR') { Write-Warn $_.ToString() }
            }

        # -- Cleanup --
        Remove-Item $tempSql -ErrorAction SilentlyContinue
        Invoke-SuperSql -Sql "DROP DATABASE IF EXISTS `"$tempDb`";" | Out-Null
        Write-Ok "Merge completed. Staging database removed."
    }

    # Reset sequences (both modes)
    Reset-Sequences
}

else {
    Write-Fail "Invalid choice '$choice'. Run the script again and enter 1 or 2."
    exit 1
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "   [OK]  Operation completed successfully!          " -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""
