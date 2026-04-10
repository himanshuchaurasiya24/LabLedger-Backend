#!/usr/bin/env python3
"""Accounting reconciliation audit for LabLedger backend.

Focus:
- historical bill price immutability via price_at_time
- bill retrieval consistency after diagnosis price edits
- update path behavior when diagnosis list is unchanged
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from all_urls import API_TOKEN, api_bill_by_id


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
    allowed_hosts = os.environ.get("ALLOWED_HOSTS", "")
    if "testserver" not in allowed_hosts:
        os.environ["ALLOWED_HOSTS"] = (
            f"{allowed_hosts},testserver" if allowed_hosts else "testserver"
        )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LabLedger.settings")
    import django

    django.setup()


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str


def run_checks() -> list[CheckResult]:
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    from center_detail.models import CenterDetail
    from diagnosis.models import Bill, BillDiagnosisType, DiagnosisCategory, DiagnosisType, Doctor, DoctorCategoryPercentage

    User = get_user_model()
    client = APIClient()
    client.raise_request_exception = False
    run_id = str(int(time.time()))[-8:]

    created = []
    results: list[CheckResult] = []

    def mk(model, **kwargs):
        obj = model.objects.create(**kwargs)
        created.append(obj)
        return obj

    def record(name: str, passed: bool, details: str):
        results.append(CheckResult(name=name, passed=passed, details=details))

    def request(method: str, path: str, **kwargs):
        fn = getattr(client, method.lower())
        return fn(path, secure=True, **kwargs)

    try:
        center = mk(
            CenterDetail,
            center_name=f"ReconCenter_{run_id}",
            address="A",
            owner_name="O",
            owner_phone=f"94{run_id}01",
        )
        user = mk(
            User,
            username=f"recon{run_id}",
            email=f"recon_{run_id}@example.com",
            first_name="R",
            last_name="U",
            phone_number=f"98{run_id}01",
            address="A",
            center_detail=center,
            is_admin=True,
            is_staff=True,
        )
        user.set_password("Passw0rd!23")
        user.save()

        cat = mk(DiagnosisCategory, name=f"ReconCat_{run_id}", is_active=True)
        dt = mk(DiagnosisType, center_detail=center, name=f"ReconType_{run_id}", category=cat, price=100)
        doctor = mk(Doctor, center_detail=center, first_name="Doc", last_name="R")
        mk(DoctorCategoryPercentage, doctor=doctor, category=cat, percentage=10)

        bill = mk(
            Bill,
            patient_name="P",
            patient_age=30,
            patient_sex="Male",
            patient_phone_number=9999999991,
            referred_by_doctor=doctor,
            center_detail=center,
            test_done_by=user,
            bill_status="Fully Paid",
            paid_amount=100,
            disc_by_center=0,
            disc_by_doctor=0,
        )
        bdt = mk(BillDiagnosisType, bill=bill, diagnosis_type=dt, price_at_time=100)
        bill.calculate_totals_and_incentive()

        original_total = bill.total_amount
        original_snapshot_price = bdt.price_at_time

        # Change master diagnosis type price (should NOT affect existing bill snapshot)
        dt.price = 250
        dt.save(update_fields=["price"])

        bill.refresh_from_db()
        bdt.refresh_from_db()

        record(
            "snapshot_price_immutable_after_master_price_change",
            bdt.price_at_time == original_snapshot_price,
            f"expected={original_snapshot_price}, actual={bdt.price_at_time}",
        )

        # Recalculate existing bill after master price change -> should still use price_at_time
        bill.calculate_totals_and_incentive()
        bill.refresh_from_db()
        record(
            "bill_total_immutable_after_recalculation",
            bill.total_amount == original_total,
            f"expected_total={original_total}, actual_total={bill.total_amount}",
        )

        # API response should include price_at_time and keep total stable
        token = request(
            "post",
            API_TOKEN,
            data={"username": user.username, "password": "Passw0rd!23"},
            format="json",
        )
        access = token.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        r = request("get", api_bill_by_id(bill.id))
        price_at_time = None
        if r.status_code == 200 and r.data.get("diagnosis_types_output"):
            price_at_time = r.data["diagnosis_types_output"][0].get("price_at_time")

        record(
            "bill_api_exposes_snapshot_price",
            r.status_code == 200 and price_at_time == original_snapshot_price,
            f"status={r.status_code}, price_at_time={price_at_time}",
        )

        # Update bill without changing diagnosis_types should preserve snapshot price
        update_payload = {
            "paid_amount": bill.paid_amount,
            "disc_by_center": bill.disc_by_center,
            "disc_by_doctor": bill.disc_by_doctor,
            "bill_status": bill.bill_status,
        }
        ur = request("patch", api_bill_by_id(bill.id), data=update_payload, format="json")
        bill.refresh_from_db()
        bdt.refresh_from_db()
        record(
            "update_without_diagnosis_change_preserves_snapshot",
            ur.status_code in (200, 202) and bdt.price_at_time == original_snapshot_price,
            f"status={ur.status_code}, snapshot={bdt.price_at_time}",
        )

    finally:
        for obj in reversed(created):
            try:
                obj.delete()
            except Exception:
                pass

    return results


def main() -> int:
    bootstrap()
    results = run_checks()

    print("ACCOUNTING_RECON_RESULTS_START")
    for item in results:
        state = "PASS" if item.passed else "FAIL"
        print(f"{item.name}|{state}|{item.details}")
    print("ACCOUNTING_RECON_RESULTS_END")

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
