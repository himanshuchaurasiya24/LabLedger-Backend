# LabLedger Backend Script Run Guide

This guide explains what each important script does and when to run it.

## 1) PostgreSQL Setup (Linux)

### Script
- `scripts/database/setup_postgres_from_env.sh`

### What it does
- Loads `.env` with `set -a` / `set +a`.
- If missing, appends these DB keys to `.env` with defaults:
  - `DB_ENGINE=django.db.backends.postgresql`
  - `DB_NAME=labledger`
  - `DB_USER=labledger_user`
  - `DB_PASSWORD=RandomPasswordForLabLedgerPostgreSQL`
  - `DB_HOST=localhost`
  - `DB_PORT=5432`
- Installs PostgreSQL using `apt-get` if `psql` is not available.
- Enables and starts PostgreSQL service (`systemctl`) when available.
- Creates/updates PostgreSQL role and database from `.env`.
- Tests DB connectivity with app credentials.
- Runs PK sequence reset using `scripts/reset_pk_sequences.sh`.
- Prints success message when setup completes.

### Run
```bash
chmod +x scripts/database/setup_postgres_from_env.sh
./scripts/database/setup_postgres_from_env.sh
```

## 2) PostgreSQL Setup (Windows)

### Script
- `scripts/database/postgres_tools.ps1` (Action: `setup`)

### What it does
- Reads `.env`, auto-adds missing DB keys with the same defaults listed above.
- Validates that `DB_ENGINE` is PostgreSQL.
- Checks for PostgreSQL tools (`psql`, `pg_dump`, `pg_restore`).
- If tools are missing, tries to install PostgreSQL using:
  - `winget` (preferred)
  - `choco` (fallback)
- Creates/updates PostgreSQL role and database from `.env`.
- Tests DB connectivity with app credentials.
- Runs PK sequence reset using `scripts/reset_pk_sequences.ps1`.
- Prints success message when setup completes.

### Run
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\database\postgres_tools.ps1 -Action setup
```

## 3) Django Server Run (Linux)

### Script
- `runserver.sh`

### What it does
- Verifies `.env` exists.
- Creates `venv` automatically if missing.
- Upgrades `pip`, `setuptools`, and `wheel`.
- Installs dependencies from `requirements.txt` (with one retry).
- Loads `.env` using `set -a` / `set +a`.
- Verifies `DJANGO_SECRET_KEY` is present.
- Runs Django server on:
  - `RUNSERVER_HOST` (default `0.0.0.0`)
  - `RUNSERVER_PORT` (default `8000`)

### Run
```bash
chmod +x runserver.sh
./runserver.sh
```

## 4) Django Server Run (Windows)

### Script
- `runserver.ps1`

### What it does
- Verifies `.env` exists.
- Creates `venv` automatically if missing.
- Upgrades `pip`, `setuptools`, and `wheel`.
- Installs dependencies from `requirements.txt` (with one retry).
- Loads `.env` into process environment.
- Verifies `DJANGO_SECRET_KEY` is present.
- Runs Django server on:
  - `RUNSERVER_HOST` (default `0.0.0.0`)
  - `RUNSERVER_PORT` (default `8000`)

### Run
```powershell
powershell -ExecutionPolicy Bypass -File .\runserver.ps1
```

## 5) PK Sequence Reset Scripts (manual run)

### Linux
```bash
./scripts/reset_pk_sequences.sh
```

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset_pk_sequences.ps1
```

## 6) Existing Database Utility Actions (Windows)

`postgres_tools.ps1` also supports:
- `-Action export`: Export PostgreSQL database to dump file.
- `-Action import`: Import dump into target DB.

Examples:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\database\postgres_tools.ps1 -Action export
powershell -ExecutionPolicy Bypass -File .\scripts\database\postgres_tools.ps1 -Action import -DumpFile .\scripts\database\exports\labledger_YYYYMMDD_HHMMSS.dump
```
