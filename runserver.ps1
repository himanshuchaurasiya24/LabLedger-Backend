Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $RootDir '.env'
$VenvDir = Join-Path $RootDir 'venv'
$PythonExe = Join-Path $VenvDir 'Scripts/python.exe'

if (-not (Test-Path $EnvFile)) {
    throw "missing .env file at $EnvFile"
}

Set-Location $RootDir

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating virtual environment in $VenvDir ..." -ForegroundColor Cyan
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue

    if ($pyLauncher) {
        & py -3 -m venv $VenvDir
    }
    elseif ($pythonCmd) {
        & python -m venv $VenvDir
    }
    else {
        throw "Python is not installed. Install Python 3 and rerun."
    }
}

Write-Host "Installing/upgrading Python dependencies..." -ForegroundColor Cyan
& $PythonExe -m pip install --upgrade pip setuptools wheel

try {
    & $PythonExe -m pip install -r requirements.txt
}
catch {
    Write-Host "First dependency install attempt failed. Retrying once..." -ForegroundColor Yellow
    & $PythonExe -m pip cache purge
    & $PythonExe -m pip install -r requirements.txt
}

Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ([string]::IsNullOrWhiteSpace($line)) { return }
    if ($line.StartsWith('#')) { return }
    if ($line -notmatch '=') { return }

    $parts = $line.Split('=', 2)
    $key = $parts[0].Trim()
    $value = $parts[1].Trim()

    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    [Environment]::SetEnvironmentVariable($key, $value, 'Process')
}

if ([string]::IsNullOrWhiteSpace($env:DJANGO_SECRET_KEY)) {
    throw 'DJANGO_SECRET_KEY is not set after loading .env'
}

$HostAddress = if ($env:RUNSERVER_HOST) { $env:RUNSERVER_HOST } else { '0.0.0.0' }
$Port = if ($env:RUNSERVER_PORT) { $env:RUNSERVER_PORT } else { '8000' }

Write-Host "Starting Django server at http://$HostAddress`:$Port/" -ForegroundColor Green
& $PythonExe manage.py runserver "$HostAddress`:$Port"
