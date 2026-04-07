param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("setup", "export", "import")]
    [string]$Action,

    [string]$EnvFile = ".env",
    [string]$DumpFile,
    [string]$TargetDatabase,
    [string]$SuperUser = "postgres",
    [string]$SuperPassword = "",
    [string]$SuperHost = "localhost",
    [int]$SuperPort = 5432
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Read-EnvFile {
    param([string]$Path)

    if (-not (Test-Path -Path $Path)) {
        throw "Env file not found: $Path"
    }

    $map = @{}
    $lines = Get-Content -Path $Path
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed.StartsWith("#")) { continue }
        $idx = $trimmed.IndexOf("=")
        if ($idx -lt 1) { continue }

        $key = $trimmed.Substring(0, $idx).Trim()
        $value = $trimmed.Substring($idx + 1).Trim()

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $map[$key] = $value
    }

    return $map
}

function Require-Command {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        throw "Required command not found in PATH: $Name"
    }
    return $cmd.Source
}

function Get-Value {
    param(
        [hashtable]$Map,
        [string]$Key,
        [string]$Default = "",
        [bool]$Required = $true
    )

    if ($Map.ContainsKey($Key) -and -not [string]::IsNullOrWhiteSpace($Map[$Key])) {
        return $Map[$Key]
    }

    if ($Required -and [string]::IsNullOrWhiteSpace($Default)) {
        throw "Missing required env variable: $Key"
    }

    return $Default
}

function Run-Command {
    param(
        [string]$Exe,
        [string[]]$Args,
        [hashtable]$ExtraEnv = @{}
    )

    $backup = @{}
    foreach ($k in $ExtraEnv.Keys) {
        $backup[$k] = [Environment]::GetEnvironmentVariable($k, "Process")
        [Environment]::SetEnvironmentVariable($k, [string]$ExtraEnv[$k], "Process")
    }

    try {
        & $Exe @Args
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed ($LASTEXITCODE): $Exe $($Args -join ' ')"
        }
    }
    finally {
        foreach ($k in $ExtraEnv.Keys) {
            [Environment]::SetEnvironmentVariable($k, $backup[$k], "Process")
        }
    }
}

function SqlLiteral {
    param([string]$Value)
    return $Value.Replace("'", "''")
}

function SqlIdentifier {
    param([string]$Value)
    return '"' + $Value.Replace('"', '""') + '"'
}

$envMap = Read-EnvFile -Path $EnvFile

$dbEngine = Get-Value -Map $envMap -Key "DB_ENGINE" -Default "django.db.backends.postgresql" -Required $false
$dbName = Get-Value -Map $envMap -Key "DB_NAME"
$dbUser = Get-Value -Map $envMap -Key "DB_USER"
$dbPassword = Get-Value -Map $envMap -Key "DB_PASSWORD"
$dbHost = Get-Value -Map $envMap -Key "DB_HOST" -Default "localhost" -Required $false
$dbPort = [int](Get-Value -Map $envMap -Key "DB_PORT" -Default "5432" -Required $false)

if ($dbEngine -notlike "*postgresql*") {
    throw "DB_ENGINE from .env is not PostgreSQL: $dbEngine"
}

$psql = Require-Command -Name "psql"
$pgDump = Require-Command -Name "pg_dump"
$pgRestore = Require-Command -Name "pg_restore"

$exportDir = Join-Path $repoRoot "scripts/database/exports"
if (-not (Test-Path -Path $exportDir)) {
    New-Item -ItemType Directory -Path $exportDir | Out-Null
}

switch ($Action) {
    "setup" {
        Write-Step "Setting up PostgreSQL role/database from .env"

        $superConnEnv = @{}
        if (-not [string]::IsNullOrWhiteSpace($SuperPassword)) {
            $superConnEnv["PGPASSWORD"] = $SuperPassword
        }

        $dbUserSql = SqlLiteral -Value $dbUser
        $dbPasswordSql = SqlLiteral -Value $dbPassword
        $dbNameSql = SqlLiteral -Value $dbName
        $dbUserIdent = SqlIdentifier -Value $dbUser
        $dbNameIdent = SqlIdentifier -Value $dbName

        $doBlock = @"
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$dbUserSql') THEN
        CREATE ROLE $dbUserIdent LOGIN PASSWORD '$dbPasswordSql';
    ELSE
        ALTER ROLE $dbUserIdent WITH LOGIN PASSWORD '$dbPasswordSql';
    END IF;
END
$$;
"@

        Run-Command -Exe $psql -Args @("-h", $SuperHost, "-p", "$SuperPort", "-U", $SuperUser, "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", $doBlock) -ExtraEnv $superConnEnv

        $existsResult = & $psql -h $SuperHost -p $SuperPort -U $SuperUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$dbNameSql';"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed checking database existence with superuser."
        }

        if (($existsResult | Out-String).Trim() -ne "1") {
            Run-Command -Exe $psql -Args @("-h", $SuperHost, "-p", "$SuperPort", "-U", $SuperUser, "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "CREATE DATABASE $dbNameIdent OWNER $dbUserIdent;") -ExtraEnv $superConnEnv
        }

        Run-Command -Exe $psql -Args @("-h", $SuperHost, "-p", "$SuperPort", "-U", $SuperUser, "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "GRANT ALL PRIVILEGES ON DATABASE $dbNameIdent TO $dbUserIdent;") -ExtraEnv $superConnEnv

        Write-Step "Verifying app credentials from .env"
        Run-Command -Exe $psql -Args @("-h", $dbHost, "-p", "$dbPort", "-U", $dbUser, "-d", $dbName, "-tAc", "SELECT current_database(), current_user;") -ExtraEnv @{ PGPASSWORD = $dbPassword }

        Write-Host "Setup completed successfully." -ForegroundColor Green
    }
    "export" {
        Write-Step "Exporting PostgreSQL database"

        if ([string]::IsNullOrWhiteSpace($DumpFile)) {
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $DumpFile = Join-Path $exportDir "$($dbName)_$timestamp.dump"
        }

        Run-Command -Exe $pgDump -Args @(
            "-h", $dbHost,
            "-p", "$dbPort",
            "-U", $dbUser,
            "-d", $dbName,
            "-F", "c",
            "-Z", "9",
            "--no-owner",
            "--no-privileges",
            "-v",
            "-f", $DumpFile
        ) -ExtraEnv @{ PGPASSWORD = $dbPassword }

        Write-Host "Export created: $DumpFile" -ForegroundColor Green
    }
    "import" {
        Write-Step "Importing PostgreSQL database"

        if ([string]::IsNullOrWhiteSpace($DumpFile)) {
            throw "-DumpFile is required for import action."
        }

        if (-not (Test-Path -Path $DumpFile)) {
            throw "Dump file not found: $DumpFile"
        }

        $targetDbName = if ([string]::IsNullOrWhiteSpace($TargetDatabase)) { $dbName } else { $TargetDatabase }

        Run-Command -Exe $pgRestore -Args @(
            "-h", $dbHost,
            "-p", "$dbPort",
            "-U", $dbUser,
            "-d", $targetDbName,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "-v",
            $DumpFile
        ) -ExtraEnv @{ PGPASSWORD = $dbPassword }

        Write-Host "Import completed into database: $targetDbName" -ForegroundColor Green
    }
    default {
        throw "Unsupported action: $Action"
    }
}
