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
    "DJANGO_SECRET_KEY=change-this-secret-key-before-production",
    "DEBUG=False",
    "ALLOWED_HOSTS=127.0.0.1,localhost",
    "CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://127.0.0.1",
    "CORS_ALLOW_CREDENTIALS=False",
    "USE_HTTPS=False",
    "DB_ENGINE=django.db.backends.postgresql",
    "DB_NAME=labledger",
    "DB_USER=labledger_user",
    "DB_PASSWORD=your_secure_db_password_here",
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

if ([string]::IsNullOrWhiteSpace($DB_PASSWORD) -or $DB_PASSWORD -eq 'your_secure_db_password_here') {
    Write-Fail "DB_PASSWORD is missing or still set to the placeholder value in .env. Update it before running this script."
    exit 1
}

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

for ($i = 1; $i -le 3; $i++) {
    if ($PG_SUPER_PASSWORD_PLAIN) { break }
    $sec = Read-Host "  Password (attempt $i/3)" -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
    $env:PGPASSWORD = $plain
    & $PsqlExe -h $DB_HOST -p $DB_PORT -U postgres -d postgres -tAc "SELECT 1;" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $PG_SUPER_PASSWORD_PLAIN = $plain; Write-Ok "Password accepted."; break }
    Write-Warn "Wrong password. $(3 - $i) attempt(s) left."
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

function Sync-AppAccess {
    Write-Step "STEP 5 -- Validating app DB credentials"

    $env:PGPASSWORD = $DB_PASSWORD
    & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT 1;" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "App user '$DB_USER' can connect to '$DB_NAME'."
        return
    }

    Write-Warn "App user connection failed. Attempting to sync role/database from .env ..."

    $roleExists = Invoke-SuperSql -Sql "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';"
    if ($roleExists -match '1') {
        Invoke-SuperSql -Sql "ALTER ROLE `"$DB_USER`" WITH LOGIN PASSWORD '$DB_PASSWORD';" | Out-Null
        Write-Ok "Role '$DB_USER' password synced."
    } else {
        Invoke-SuperSql -Sql "CREATE ROLE `"$DB_USER`" WITH LOGIN PASSWORD '$DB_PASSWORD';" | Out-Null
        Write-Ok "Role '$DB_USER' created."
    }

    $dbExists = Invoke-SuperSql -Sql "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';"
    if ($dbExists -notmatch '1') {
        Invoke-SuperSql -Sql "CREATE DATABASE `"$DB_NAME`" OWNER `"$DB_USER`";" | Out-Null
        Write-Ok "Database '$DB_NAME' created."
    }

    Invoke-SuperSql -Sql "GRANT ALL PRIVILEGES ON DATABASE `"$DB_NAME`" TO `"$DB_USER`";" | Out-Null

    $env:PGPASSWORD = $DB_PASSWORD
    & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT 1;" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "App user connectivity restored."
    } else {
        Write-Fail "Unable to connect as '$DB_USER' to '$DB_NAME' after auto-fix."
        exit 1
    }
}

Sync-AppAccess

function Reset-Sequences {
    Write-Step "Resetting primary-key sequences"
    $env:PGPASSWORD = $DB_PASSWORD

    $resetSql = @'
DO $$
DECLARE
    sequence_row record;
    next_value bigint;
    reset_count integer := 0;
BEGIN
    PERFORM set_config(''lock_timeout'', ''5s'', true);

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
           AND dep.deptype IN (''a'', ''i'')
        JOIN pg_class tbl
            ON tbl.oid = dep.refobjid
        JOIN pg_namespace tbl_ns
            ON tbl_ns.oid = tbl.relnamespace
        JOIN pg_attribute att
            ON att.attrelid = tbl.oid
           AND att.attnum = dep.refobjsubid
        JOIN pg_namespace seq_ns
            ON seq_ns.oid = seq.relnamespace
        WHERE seq.relkind = ''S''
          AND tbl.relkind IN (''r'', ''p'')
          AND tbl_ns.nspname NOT IN (''pg_catalog'', ''information_schema'')
          AND seq_ns.nspname NOT IN (''pg_catalog'', ''information_schema'')
        ORDER BY tbl_ns.nspname, tbl.relname, att.attname
    LOOP
        EXECUTE format(''LOCK TABLE %I.%I IN ACCESS EXCLUSIVE MODE'', sequence_row.table_schema, sequence_row.table_name);
        EXECUTE format(
            ''SELECT COALESCE(MAX(%I), 0) + 1 FROM %I.%I'',
            sequence_row.column_name,
            sequence_row.table_schema,
            sequence_row.table_name
        ) INTO next_value;
        EXECUTE format(
            ''SELECT setval(%L, %s, false)'',
            format(''%I.%I'', sequence_row.sequence_schema, sequence_row.sequence_name),
            next_value
        );
        reset_count := reset_count + 1;
    END LOOP;

    RAISE NOTICE ''Reset % sequence(s).'', reset_count;
END $$;
'@

    # Write SQL to a temp file and run psql with -f to avoid argument splitting
    $sqlFile = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), ([System.IO.Path]::GetRandomFileName() + '.sql'))
    Set-Content -Path $sqlFile -Value $resetSql -Encoding UTF8

    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()
    $argList = @('-h', $DB_HOST, '-p', $DB_PORT, '-U', $DB_USER, '-d', $DB_NAME, '-v', 'ON_ERROR_STOP=1', '-f', $sqlFile)
    $proc = Start-Process -FilePath $PsqlExe -ArgumentList $argList -RedirectStandardOutput $outFile -RedirectStandardError $errFile -NoNewWindow -Wait -PassThru
    $exitCode = $proc.ExitCode
    $outText = ''
    $errText = ''
    try { $outText = Get-Content -Raw -Path $outFile -ErrorAction SilentlyContinue } catch { }
    try { $errText = Get-Content -Raw -Path $errFile -ErrorAction SilentlyContinue } catch { }
    $resetOutput = @()
    if ($outText) { $resetOutput += $outText -split "`n" }
    if ($errText) { $resetOutput += $errText -split "`n" }
    Remove-Item -Path $outFile,$errFile -ErrorAction SilentlyContinue
    Remove-Item -Path $sqlFile -ErrorAction SilentlyContinue

    if ($exitCode -ne 0) {
        Write-Fail "Failed to reset primary-key sequences dynamically."
        if ($resetOutput) { $resetOutput | ForEach-Object { Write-Host $_ } }
        exit 1
    }

    if ($resetOutput) { $resetOutput | ForEach-Object { Write-Host $_ } }

    Write-Ok "Primary-key sequences reset dynamically for all sequence-backed tables."
}

# ---------------------------------------------------------------------------
# STEP 5 -- Main menu
# ---------------------------------------------------------------------------
Write-Step "STEP 6 -- Choose operation"
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

    # (removed post-export sequence reset — sequences are reset after imports/setup only)
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
    $parsedSel = 0
    if (-not [int]::TryParse($sel, [ref]$parsedSel)) {
        Write-Fail "Invalid selection '$sel'. Enter a number."
        exit 1
    }
    $idx = $parsedSel - 1

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

            # -- Pre-merge compatibility check --
            Write-Info "Step 1.5/4 -- Checking column compatibility between staging and main DB..."
            $env:PGPASSWORD = $DB_PASSWORD

            # Query main DB column metadata via a temp SQL file to avoid here-string parsing issues
            $mainSqlLines = @(
                "SELECT table_schema || '|' || table_name || '|' || column_name || '|' || is_nullable || '|' || coalesce(column_default,'')",
                "FROM information_schema.columns",
                "WHERE table_schema NOT IN ('pg_catalog','information_schema')",
                "ORDER BY table_schema, table_name, ordinal_position;"
            )
            $mainSqlFile = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), ([System.IO.Path]::GetRandomFileName() + '.sql'))
            Set-Content -Path $mainSqlFile -Value $mainSqlLines -Encoding UTF8

            $outFile = [System.IO.Path]::GetTempFileName()
            $errFile = [System.IO.Path]::GetTempFileName()
            $argList = @('-h', $DB_HOST, '-p', $DB_PORT, '-U', $DB_USER, '-d', $DB_NAME, '-tA', '-F', '|', '-f', $mainSqlFile)
            $proc = Start-Process -FilePath $PsqlExe -ArgumentList $argList -RedirectStandardOutput $outFile -RedirectStandardError $errFile -NoNewWindow -Wait -PassThru
            $mainCols = ''
            try { $mainCols = Get-Content -Raw -Path $outFile -ErrorAction SilentlyContinue } catch {}
            try { $err = Get-Content -Raw -Path $errFile -ErrorAction SilentlyContinue; if ($err) { $mainCols += "`n" + $err } } catch {}
            Remove-Item -Path $mainSqlFile,$outFile,$errFile -ErrorAction SilentlyContinue

            # Query staging DB column metadata similarly
            $stgSqlLines = @(
                "SELECT table_schema || '|' || table_name || '|' || column_name",
                "FROM information_schema.columns",
                "WHERE table_schema NOT IN ('pg_catalog','information_schema')",
                "ORDER BY table_schema, table_name, ordinal_position;"
            )
            $stgSqlFile = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), ([System.IO.Path]::GetRandomFileName() + '.sql'))
            Set-Content -Path $stgSqlFile -Value $stgSqlLines -Encoding UTF8

            $outFile = [System.IO.Path]::GetTempFileName()
            $errFile = [System.IO.Path]::GetTempFileName()
            $argList = @('-h', $DB_HOST, '-p', $DB_PORT, '-U', $DB_USER, '-d', $tempDb, '-tA', '-F', '|', '-f', $stgSqlFile)
            $proc = Start-Process -FilePath $PsqlExe -ArgumentList $argList -RedirectStandardOutput $outFile -RedirectStandardError $errFile -NoNewWindow -Wait -PassThru
            $stagingCols = ''
            try { $stagingCols = Get-Content -Raw -Path $outFile -ErrorAction SilentlyContinue } catch {}
            try { $err = Get-Content -Raw -Path $errFile -ErrorAction SilentlyContinue; if ($err) { $stagingCols += "`n" + $err } } catch {}
            Remove-Item -Path $stgSqlFile,$outFile,$errFile -ErrorAction SilentlyContinue

            $mainMap = @{}
            foreach ($ln in ($mainCols -split "`n")) {
                if ([string]::IsNullOrWhiteSpace($ln)) { continue }
                $parts = $ln -split '\|',5
                if ($parts.Count -lt 3) { continue }
                $tbl = "$($parts[0]).$($parts[1])"
                $col = $parts[2]
                $isNullable = if ($parts.Count -ge 4) { $parts[3] } else { 'YES' }
                $default = if ($parts.Count -ge 5) { $parts[4] } else { '' }
                if (-not $mainMap.ContainsKey($tbl)) { $mainMap[$tbl] = @{} }
                $mainMap[$tbl][$col] = @{ nullable = $isNullable; default = $default }
            }

            $stagingMap = @{}
            foreach ($ln in ($stagingCols -split "`n")) {
                if ([string]::IsNullOrWhiteSpace($ln)) { continue }
                $parts = $ln -split '\|',3
                if ($parts.Count -lt 3) { continue }
                $tbl = "$($parts[0]).$($parts[1])"
                $col = $parts[2]
                if (-not $stagingMap.ContainsKey($tbl)) { $stagingMap[$tbl] = @{} }
                $stagingMap[$tbl][$col] = $true
            }

            $problemFound = $false
            foreach ($tbl in $mainMap.Keys) {
                $mainColsForTbl = $mainMap[$tbl].Keys
                $stagingColsForTbl = if ($stagingMap.ContainsKey($tbl)) { $stagingMap[$tbl].Keys } else { @() }
                $missing = $mainColsForTbl | Where-Object { $stagingColsForTbl -notcontains $_ }
                if ($missing.Count -gt 0) {
                    foreach ($col in $missing) {
                        $meta = $mainMap[$tbl][$col]
                        if ($meta.nullable -eq 'NO' -and [string]::IsNullOrWhiteSpace($meta.default)) {
                            Write-Warn "POTENTIAL MISMATCH: $tbl missing required column '$col' (NOT NULL, no default)"
                            $problemFound = $true
                        } else {
                            Write-Info "Info: $tbl missing column '$col' (nullable=$($meta.nullable), default present?=$(-not [string]::IsNullOrWhiteSpace($meta.default)))"
                        }
                    }
                }
            }

            if ($problemFound) {
                Write-Warn "One or more tables have required columns in main DB that are missing in the staging DB. Merge may fail for these tables."
            } else {
                Write-Ok "Pre-merge compatibility check passed (no missing NOT NULL/no-default columns detected)."
            }

        # -- Step 2: Export staging data as plain INSERT SQL --
        Write-Info "Step 2/4 -- Exporting staging data as INSERT statements ..."
        $env:PGPASSWORD = $DB_PASSWORD
        & $PgDumpExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $tempDb `
                 --data-only --inserts --column-inserts -f $tempSql 2>&1 | Out-Null

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
        $mergeOutput = & $PsqlExe -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
                              -v ON_ERROR_STOP=0 -f $tempSql 2>&1

        $mergeOutput | ForEach-Object {
            if ($_ -match '^ERROR') { Write-Warn $_.ToString() }
        }

        $insertedCount = @($mergeOutput | Where-Object { $_ -match '^INSERT 0 1$' }).Count
        $skippedCount  = @($mergeOutput | Where-Object { $_ -match '^INSERT 0 0$' }).Count
        $attemptedCount = $insertedCount + $skippedCount

        Write-Host ""
        Write-Ok "MERGE summary"
        Write-Info "Rows attempted : $attemptedCount"
        Write-Info "Rows inserted  : $insertedCount"
        Write-Info "Rows skipped   : $skippedCount (conflict/duplicate)"

        # -- Cleanup --
        Remove-Item $tempSql -ErrorAction SilentlyContinue
        Invoke-SuperSql -Sql "DROP DATABASE IF EXISTS `"$tempDb`";" | Out-Null
        Write-Ok "Merge completed. Staging database removed."
    }

    # Reset sequences (both import modes)
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
