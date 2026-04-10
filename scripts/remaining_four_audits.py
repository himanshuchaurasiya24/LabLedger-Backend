#!/usr/bin/env python3
"""Remaining 4 audits runner.

Covers:
1) Concurrency stress on bill updates
2) Cross-endpoint reconciliation for incentive totals
3) Large-data performance smoke test
4) Report-data correctness (API snapshot payload shape)
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from all_urls import (
    API_DIAGNOSIS_BILL,
    API_DIAGNOSIS_BILL_GROWTH_STATS,
    API_DIAGNOSIS_INCENTIVES,
    API_DIAGNOSIS_REFERRAL_STAT,
    API_TOKEN,
    api_bill_by_id,
    api_doctor_incentives,
)


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
    from django.db.models import Sum
    from rest_framework.test import APIClient

    from center_detail.models import CenterDetail
    from diagnosis.models import (
        Bill,
        BillDiagnosisType,
        DiagnosisCategory,
        DiagnosisType,
        Doctor,
        DoctorCategoryPercentage,
    )

    User = get_user_model()
    run_id = str(int(time.time()))[-8:]
    results: list[CheckResult] = []
    created: list[object] = []

    def mk(model, **kwargs):
        obj = model.objects.create(**kwargs)
        created.append(obj)
        return obj

    def record(name: str, passed: bool, details: str):
        results.append(CheckResult(name=name, passed=passed, details=details))

    def auth_client(username: str, password: str) -> APIClient:
        c = APIClient()
        c.raise_request_exception = False
        token_resp = c.post(
            API_TOKEN,
            {"username": username, "password": password},
            format="json",
            secure=True,
        )
        token = token_resp.data.get("access") if token_resp.status_code == 200 else None
        if token:
            c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return c

    try:
        center = mk(
            CenterDetail,
            center_name=f"RemainCenter_{run_id}",
            address="Audit",
            owner_name="Owner",
            owner_phone=f"93{run_id}77",
        )
        user = mk(
            User,
            username=f"remain{run_id}",
            email=f"remain_{run_id}@example.com",
            first_name="Remain",
            last_name="Audit",
            phone_number=f"98{run_id}77",
            address="Audit",
            center_detail=center,
            is_admin=True,
            is_staff=True,
        )
        user.set_password("Passw0rd!23")
        user.save()

        cat = mk(DiagnosisCategory, name=f"RemainCat_{run_id}", is_active=True)
        dt = mk(DiagnosisType, center_detail=center, name=f"RemainType_{run_id}", category=cat, price=100)
        doctor = mk(Doctor, center_detail=center, first_name="Doc", last_name="Remain")
        mk(DoctorCategoryPercentage, doctor=doctor, category=cat, percentage=10)

        bill = mk(
            Bill,
            patient_name="Concurrent",
            patient_age=30,
            patient_sex="Male",
            patient_phone_number=9999999994,
            referred_by_doctor=doctor,
            center_detail=center,
            test_done_by=user,
            bill_status="Fully Paid",
            paid_amount=100,
            disc_by_center=0,
            disc_by_doctor=0,
        )
        mk(BillDiagnosisType, bill=bill, diagnosis_type=dt, price_at_time=100)
        bill.calculate_totals_and_incentive()

        # Audit 1: Concurrency stress for update endpoint
        def do_patch(i: int):
            c = auth_client(user.username, "Passw0rd!23")
            paid = 100 - (i % 5) * 10
            payload = {
                "bill_status": "Fully Paid",
                "paid_amount": paid,
                "disc_by_center": 0,
                "disc_by_doctor": 100 - paid,
            }
            r = c.patch(api_bill_by_id(bill.id), payload, format="json", secure=True)
            return r.status_code

        statuses = []
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(do_patch, i) for i in range(30)]
            for f in as_completed(futures):
                statuses.append(f.result())

        bill.refresh_from_db()
        valid_final = bill.total_amount == bill.paid_amount + bill.disc_by_center + bill.disc_by_doctor
        no_server_errors = all(s != 500 for s in statuses)
        record(
            "concurrency_bill_patch_no_500_and_valid_final_state",
            no_server_errors and valid_final,
            f"statuses={sorted(set(statuses))}, final=({bill.total_amount},{bill.paid_amount},{bill.disc_by_center},{bill.disc_by_doctor})",
        )

        # Seed more bills for reconciliation/performance
        for i in range(120):
            b = mk(
                Bill,
                patient_name=f"P{i}",
                patient_age=20 + (i % 40),
                patient_sex="Male" if i % 2 == 0 else "Female",
                patient_phone_number=9000000000 + i,
                referred_by_doctor=doctor,
                center_detail=center,
                test_done_by=user,
                bill_status="Fully Paid",
                paid_amount=100,
                disc_by_center=0,
                disc_by_doctor=0,
            )
            mk(BillDiagnosisType, bill=b, diagnosis_type=dt, price_at_time=100)
            b.calculate_totals_and_incentive()

        client = auth_client(user.username, "Passw0rd!23")

        # Audit 2: Cross-endpoint reconciliation (same period/doctor)
        start_date = date.today().replace(day=1).isoformat()
        end_date = date.today().isoformat()

        d_resp = client.get(api_doctor_incentives(doctor.id), secure=True)
        f_resp = client.get(
            f"{API_DIAGNOSIS_INCENTIVES}?doctor_id={doctor.id}&bill_status=Fully%20Paid&start_date={start_date}&end_date={end_date}",
            secure=True,
        )
        r_resp = client.get(f"{API_DIAGNOSIS_REFERRAL_STAT}?referred_by_doctor={doctor.id}", secure=True)

        d_total = ((d_resp.data or {}).get("current_month") or {}).get("total_incentive", 0) if d_resp.status_code == 200 else None
        f_total = 0
        if f_resp.status_code == 200 and isinstance(f_resp.data, list) and f_resp.data:
            f_total = f_resp.data[0].get("total_incentive", 0)
        r_total = 0
        if r_resp.status_code == 200 and r_resp.data.get("this_month"):
            r_total = r_resp.data["this_month"][0].get("incentive_amount", 0)

        recon_ok = d_resp.status_code == 200 and f_resp.status_code == 200 and r_resp.status_code == 200 and int(d_total or 0) == int(f_total or 0) == int(r_total or 0)
        record(
            "reconciliation_doctor_vs_flexible_vs_referral",
            recon_ok,
            f"doctor={d_total}, flexible={f_total}, referral={r_total}",
        )

        # Audit 3: Performance smoke test on larger dataset
        t0 = time.perf_counter()
        list_resp = client.get(f"{API_DIAGNOSIS_BILL}?page=1&page_size=50", secure=True)
        t1 = time.perf_counter()
        growth_resp = client.get(API_DIAGNOSIS_BILL_GROWTH_STATS, secure=True)
        t2 = time.perf_counter()
        perf_ok = (
            list_resp.status_code == 200
            and growth_resp.status_code == 200
            and (t1 - t0) < 5.0
            and (t2 - t1) < 5.0
        )
        record(
            "performance_smoke_under_threshold",
            perf_ok,
            f"list={t1-t0:.3f}s, growth={t2-t1:.3f}s",
        )

        # Audit 4: report-data correctness for snapshot payload shape
        one_bill = client.get(api_bill_by_id(bill.id), secure=True)
        snapshot_ok = False
        details = "invalid"
        if one_bill.status_code == 200 and one_bill.data.get("diagnosis_types_output"):
            first = one_bill.data["diagnosis_types_output"][0]
            snapshot_ok = first.get("price_at_time") is not None and first.get("diagnosis_type_detail", {}).get("price") is not None
            details = f"price_at_time={first.get('price_at_time')}, detail_price={first.get('diagnosis_type_detail', {}).get('price')}"
        record("report_payload_contains_snapshot_fields", snapshot_ok, details)

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
    print("REMAINING_FOUR_AUDITS_START")
    for item in results:
        state = "PASS" if item.passed else "FAIL"
        print(f"{item.name}|{state}|{item.details}")
    print("REMAINING_FOUR_AUDITS_END")
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
