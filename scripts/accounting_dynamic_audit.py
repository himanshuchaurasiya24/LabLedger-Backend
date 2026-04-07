#!/usr/bin/env python3
"""Dynamic accounting audit for LabLedger backend.

Checks runtime correctness for:
- incentive endpoint stability and response shape
- incentive aggregation correctness (no undercount)
- flexible incentive report deduplication under M2M filters
- negative financial input rejection

Exit code is non-zero if any check fails.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
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


def bootstrap_django() -> None:
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
    client = APIClient()
    client.raise_request_exception = False

    run_id = str(int(time.time()))[-8:]
    results: list[CheckResult] = []
    created_objs: list[object] = []

    def record(name: str, passed: bool, details: str) -> None:
        results.append(CheckResult(name=name, passed=passed, details=details))

    def request(method: str, path: str, **kwargs):
        fn = getattr(client, method.lower())
        return fn(path, secure=True, **kwargs)

    def mk(model, **kwargs):
        obj = model.objects.create(**kwargs)
        created_objs.append(obj)
        return obj

    try:
        center = mk(
            CenterDetail,
            center_name=f"AcctCenter_{run_id}",
            address="Audit Address",
            owner_name="Audit Owner",
            owner_phone=f"93{run_id}01",
        )

        user = mk(
            User,
            username=f"acctadmin{run_id}",
            email=f"acctadmin_{run_id}@example.com",
            first_name="Acct",
            last_name="Admin",
            phone_number=f"98{run_id}01",
            address="Audit Address",
            center_detail=center,
            is_admin=True,
            is_staff=True,
        )
        user.set_password("Passw0rd!23")
        user.save()

        cat_a = mk(DiagnosisCategory, name=f"AuditCatA_{run_id}", is_active=True)
        cat_b = mk(DiagnosisCategory, name=f"AuditCatB_{run_id}", is_active=True)

        dt1 = mk(
            DiagnosisType,
            center_detail=center,
            name=f"AuditType1_{run_id}",
            category=cat_a,
            price=100,
        )
        dt2 = mk(
            DiagnosisType,
            center_detail=center,
            name=f"AuditType2_{run_id}",
            category=cat_b,
            price=100,
        )

        doctor = mk(
            Doctor,
            center_detail=center,
            first_name="Audit",
            last_name="Doctor",
        )
        mk(DoctorCategoryPercentage, doctor=doctor, category=cat_a, percentage=10)
        mk(DoctorCategoryPercentage, doctor=doctor, category=cat_b, percentage=10)

        # Bill 1: one diagnosis type -> incentive 10
        b1 = mk(
            Bill,
            patient_name="P1",
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
        mk(BillDiagnosisType, bill=b1, diagnosis_type=dt1, price_at_time=100)
        b1.calculate_totals_and_incentive()

        # Bill 2: same incentive amount to catch distinct-sum undercount bugs
        b2 = mk(
            Bill,
            patient_name="P2",
            patient_age=40,
            patient_sex="Female",
            patient_phone_number=9999999992,
            referred_by_doctor=doctor,
            center_detail=center,
            test_done_by=user,
            bill_status="Fully Paid",
            paid_amount=100,
            disc_by_center=0,
            disc_by_doctor=0,
        )
        mk(BillDiagnosisType, bill=b2, diagnosis_type=dt1, price_at_time=100)
        b2.calculate_totals_and_incentive()

        # Bill 3: two diagnosis types to test distinct handling in flexible report
        b3 = mk(
            Bill,
            patient_name="P3",
            patient_age=35,
            patient_sex="Male",
            patient_phone_number=9999999993,
            referred_by_doctor=doctor,
            center_detail=center,
            test_done_by=user,
            bill_status="Fully Paid",
            paid_amount=200,
            disc_by_center=0,
            disc_by_doctor=0,
        )
        mk(BillDiagnosisType, bill=b3, diagnosis_type=dt1, price_at_time=100)
        mk(BillDiagnosisType, bill=b3, diagnosis_type=dt2, price_at_time=100)
        b3.calculate_totals_and_incentive()

        token_resp = request(
            "post",
            "/api/token/",
            data={"username": user.username, "password": "Passw0rd!23"},
            format="json",
        )
        token_data = getattr(token_resp, "data", None)
        if token_resp.status_code != 200 or not isinstance(token_data, dict) or not token_data.get("access"):
            record("auth_login", False, f"status={token_resp.status_code}, body={token_data}")
            return results

        record("auth_login", True, f"status={token_resp.status_code}")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_data['access']}")

        # 1) Doctor incentives endpoint stability with diagnosis_type filter
        r = request(
            "get",
            f"/diagnosis/doctors/{doctor.id}/incentives/?diagnosis_type_id={dt1.id}",
        )
        record(
            "doctor_incentives_filter_no_500",
            r.status_code != 500,
            f"status={r.status_code}",
        )

        # 2) Doctor incentives response shape for frontend parsing
        expected_keys = {"total_bills", "total_incentive", "diagnosis_counts"}
        current_month = (getattr(r, "data", {}) or {}).get("current_month", {})
        record(
            "doctor_incentives_response_shape",
            expected_keys.issubset(set(current_month.keys())),
            f"keys={sorted(list(current_month.keys())) if isinstance(current_month, dict) else 'invalid'}",
        )

        # 3) Referral stats sum must include duplicate-valued incentives exactly
        rr = request("get", f"/diagnosis/referral-stat/?referred_by_doctor={doctor.id}")
        expected_sum = (b1.incentive_amount or 0) + (b2.incentive_amount or 0) + (b3.incentive_amount or 0)
        actual_sum = None
        if rr.status_code == 200 and rr.data.get("this_month"):
            actual_sum = rr.data["this_month"][0].get("incentive_amount")
        record(
            "referral_sum_exact_no_distinct_undercount",
            rr.status_code == 200 and int(actual_sum or 0) == int(expected_sum),
            f"status={rr.status_code}, expected={expected_sum}, actual={actual_sum}",
        )

        # 4) Flexible incentive report should not duplicate totals when filtering by multiple diagnosis types
        start_date = date.today().replace(day=1).isoformat()
        end_date = date.today().isoformat()
        path = (
            "/diagnosis/incentives/"
            f"?doctor_id={doctor.id}"
            f"&diagnosis_type_id={dt1.id}&diagnosis_type_id={dt2.id}"
            "&bill_status=Fully%20Paid"
            f"&start_date={start_date}&end_date={end_date}"
        )
        fr = request("get", path)
        expected_distinct_sum = (
            Bill.objects.filter(center_detail=center, referred_by_doctor=doctor, bill_status="Fully Paid")
            .values("id")
            .distinct()
            .aggregate(total=Sum("incentive_amount"))
            .get("total")
            or 0
        )
        actual_total = 0
        if fr.status_code == 200 and isinstance(fr.data, list) and fr.data:
            actual_total = fr.data[0].get("total_incentive", 0)
        record(
            "flexible_report_no_m2m_double_count",
            fr.status_code == 200 and int(actual_total) == int(expected_distinct_sum),
            f"status={fr.status_code}, expected={expected_distinct_sum}, actual={actual_total}",
        )

        # 5) Negative financial inputs should be rejected
        bad_payload = {
            "patient_name": "Bad",
            "patient_age": 22,
            "patient_sex": "Male",
            "patient_phone_number": 9999999988,
            "date_of_test": "2026-04-01T00:00:00Z",
            "date_of_bill": "2026-04-01T00:00:00Z",
            "bill_status": "Fully Paid",
            "paid_amount": -1,
            "disc_by_center": 0,
            "disc_by_doctor": 0,
            "diagnosis_types": [dt1.id],
            "referred_by_doctor": doctor.id,
        }
        br = request("post", "/diagnosis/bill/", data=bad_payload, format="json")
        record(
            "negative_financial_input_rejected",
            br.status_code in (400, 422),
            f"status={br.status_code}",
        )

    finally:
        for obj in reversed(created_objs):
            try:
                obj.delete()
            except Exception:
                pass

    return results


def main() -> int:
    bootstrap_django()
    results = run_checks()

    print("DYNAMIC_ACCOUNTING_RESULTS_START")
    for item in results:
        state = "PASS" if item.passed else "FAIL"
        print(f"{item.name}|{state}|{item.details}")
    print("DYNAMIC_ACCOUNTING_RESULTS_END")

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
