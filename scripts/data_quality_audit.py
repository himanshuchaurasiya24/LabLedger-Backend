#!/usr/bin/env python3
"""Data quality audit for persisted accounting invariants."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def bootstrap() -> None:
    load_env_file(ENV_PATH)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LabLedger.settings")
    import django

    django.setup()


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str


def run_checks() -> list[CheckResult]:
    from diagnosis.models import Bill

    results: list[CheckResult] = []

    def record(name: str, passed: bool, details: str) -> None:
        results.append(CheckResult(name=name, passed=passed, details=details))

    bills = Bill.objects.all()

    neg_count = bills.filter(
        paid_amount__lt=0
    ).count() + bills.filter(disc_by_center__lt=0).count() + bills.filter(disc_by_doctor__lt=0).count()
    record("no_negative_financial_fields", neg_count == 0, f"violations={neg_count}")

    full_mismatch = 0
    partial_mismatch = 0
    unpaid_mismatch = 0
    snapshot_mismatch = 0
    no_doctor_incentive_mismatch = 0

    for bill in bills.iterator():
        paid = int(bill.paid_amount or 0)
        center_disc = int(bill.disc_by_center or 0)
        doctor_disc = int(bill.disc_by_doctor or 0)
        total = int(bill.total_amount or 0)

        if bill.bill_status == "Fully Paid" and total != paid + center_disc + doctor_disc:
            full_mismatch += 1
        if bill.bill_status == "Partially Paid" and total <= paid + center_disc + doctor_disc:
            partial_mismatch += 1
        if bill.bill_status == "Unpaid" and (paid > 0 or center_disc > 0 or doctor_disc > 0):
            unpaid_mismatch += 1

        snapshot_sum = sum(int(x.price_at_time or 0) for x in bill.bill_diagnosis_types.all())
        if total != snapshot_sum:
            snapshot_mismatch += 1

        if bill.referred_by_doctor is None and int(bill.incentive_amount or 0) != 0:
            no_doctor_incentive_mismatch += 1

    record("fully_paid_equation_consistent", full_mismatch == 0, f"violations={full_mismatch}")
    record("partially_paid_equation_consistent", partial_mismatch == 0, f"violations={partial_mismatch}")
    record("unpaid_equation_consistent", unpaid_mismatch == 0, f"violations={unpaid_mismatch}")
    record("bill_total_matches_price_at_time_sum", snapshot_mismatch == 0, f"violations={snapshot_mismatch}")
    record("no_doctor_implies_zero_incentive", no_doctor_incentive_mismatch == 0, f"violations={no_doctor_incentive_mismatch}")

    return results


def main() -> int:
    bootstrap()
    results = run_checks()

    print("DATA_QUALITY_RESULTS_START")
    for item in results:
        state = "PASS" if item.passed else "FAIL"
        print(f"{item.name}|{state}|{item.details}")
    print("DATA_QUALITY_RESULTS_END")

    failures = [r for r in results if not r.passed]
    summary = {
        "total": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "failures": [f.name for f in failures],
    }
    print("SUMMARY_JSON=" + json.dumps(summary))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
