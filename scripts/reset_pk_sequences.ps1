Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

param(
    [switch]$DryRun
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
Set-Location $ProjectRoot

if (-not (Test-Path (Join-Path $ProjectRoot 'manage.py'))) {
    throw "manage.py not found in $ProjectRoot"
}

$envFile = Join-Path $ProjectRoot '.env'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
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

        [Environment]::SetEnvironmentVariable($key, $value)
    }
}

$pythonExe = 'python'
$venvPython = Join-Path $ProjectRoot 'venv/Scripts/python.exe'
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
}

$dryRunFlag = if ($DryRun.IsPresent) { 'True' } else { 'False' }

$pyCode = @"
from django.db import connection
from django.apps import apps

dry_run = $dryRunFlag
vendor = connection.vendor
print(f'Vendor: {vendor}')
if vendor != 'postgresql':
    raise SystemExit('This script supports PostgreSQL only.')

reset_count = 0
skipped = 0

with connection.cursor() as cursor:
    for model in apps.get_models():
        table = model._meta.db_table
        pk = model._meta.pk
        if not pk or getattr(pk, 'column', None) != 'id':
            skipped += 1
            continue

        cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
        row = cursor.fetchone()
        seq = row[0] if row else None
        if not seq:
            skipped += 1
            continue

        if dry_run:
            print(f'[DRY RUN] {table} -> {seq}')
            continue

        cursor.execute(
            f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
        )
        reset_count += 1

print(f'Reset sequences: {reset_count}, skipped: {skipped}')
"@

& $pythonExe manage.py shell -c $pyCode
