#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

AUDITS=(
  "scripts/run_security_audit.sh"
  "scripts/run_accounting_audit.sh"
  "scripts/run_accounting_reconciliation_audit.sh"
  "scripts/run_remaining_four_audits.sh"
  "scripts/run_data_quality_audit.sh"
  "scripts/run_dependency_vulnerability_audit.sh"
)

pass_count=0
fail_count=0

for audit in "${AUDITS[@]}"; do
  echo "=== RUNNING: $audit ==="
  if bash "$audit"; then
    echo "=== PASS: $audit ==="
    pass_count=$((pass_count + 1))
  else
    echo "=== FAIL: $audit ==="
    fail_count=$((fail_count + 1))
  fi
  echo
 done

echo "RELEASE_GATE_SUMMARY: passed=${pass_count} failed=${fail_count} total=${#AUDITS[@]}"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi
