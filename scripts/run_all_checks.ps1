param(
    [switch]$SkipDbSetup,
    [switch]$SkipDbExport,
    [string]$DumpFile = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @()
    )

    Write-Host "`n==> $Name" -ForegroundColor Cyan
    Write-Host "Command: $FilePath $($Arguments -join ' ')" -ForegroundColor DarkGray

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }

    Write-Host "[PASS] $Name" -ForegroundColor Green
}

function Resolve-Python {
    $candidates = @(
        (Join-Path $rootDir "venv/Scripts/python.exe"),
        (Join-Path $rootDir "venv/bin/python"),
        "python",
        "python3"
    )

    foreach ($candidate in $candidates) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $cmd) {
            return $cmd.Source
        }
    }

    throw "Python executable not found."
}

$bash = Get-Command bash -ErrorAction SilentlyContinue
if ($null -eq $bash) {
    throw "bash is required to run existing .sh scripts. Install Git Bash/WSL and ensure bash is on PATH."
}

$python = Resolve-Python

Write-Host "Running all backend checks (audits + database tasks)..." -ForegroundColor Yellow
Write-Host "Root: $rootDir" -ForegroundColor DarkGray
Write-Host "Python: $python" -ForegroundColor DarkGray
Write-Host "Bash: $($bash.Source)" -ForegroundColor DarkGray

# 1) Full audit suite
Invoke-Step -Name "Release Gate Audits" -FilePath $bash.Source -Arguments @("scripts/run_release_gate_audits.sh")

# 2) Database setup from .env
if (-not $SkipDbSetup) {
    Invoke-Step -Name "PostgreSQL Setup From .env" -FilePath $bash.Source -Arguments @("scripts/database/setup_postgres_from_env.sh")
}
else {
    Write-Host "[SKIP] PostgreSQL setup step" -ForegroundColor Yellow
}

# 3) Database export snapshot
if (-not $SkipDbExport) {
    $exportArgs = @("scripts/database/postgres_portable_dump.sh", "export")
    if (-not [string]::IsNullOrWhiteSpace($DumpFile)) {
        $exportArgs += $DumpFile
    }

    Invoke-Step -Name "PostgreSQL Export Snapshot" -FilePath $bash.Source -Arguments $exportArgs
}
else {
    Write-Host "[SKIP] PostgreSQL export step" -ForegroundColor Yellow
}

Write-Host "`nAll requested checks completed successfully." -ForegroundColor Green
