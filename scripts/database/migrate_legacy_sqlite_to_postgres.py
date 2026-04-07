#!/usr/bin/env python3
"""Migrate legacy sqlite schema into current PostgreSQL Django schema.

Usage:
  set -a && source .env && set +a && \
  ./venv/bin/python scripts/database/migrate_legacy_sqlite_to_postgres.py --sqlite db.sqlite3
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LabLedger.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from django.utils.dateparse import parse_date, parse_datetime  # noqa: E402

from authentication.models import StaffAccount  # noqa: E402
from center_detail.models import CenterDetail, Subscription  # noqa: E402
from diagnosis.models import (  # noqa: E402
    Bill,
    BillDiagnosisType,
    DiagnosisCategory,
    DiagnosisType,
    Doctor,
    DoctorCategoryPercentage,
    FranchiseName,
    PatientReport,
    SampleTestReport,
)


def qall(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table}")
    return cur.fetchall()


def as_dt(value):
    if value is None:
        return None
    dt = parse_datetime(str(value))
    return dt


def as_date(value):
    if value is None:
        return None
    d = parse_date(str(value))
    return d


def as_bool(value) -> bool:
    if value in (True, 1, "1", "true", "True"):
        return True
    return False


def as_int(value, default=0):
    if value is None or value == "":
        return default
    return int(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="db.sqlite3", help="Path to legacy sqlite db")
    args = parser.parse_args()

    sqlite_path = os.path.abspath(args.sqlite)
    if not os.path.exists(sqlite_path):
        raise SystemExit(f"sqlite source not found: {sqlite_path}")

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    # Read source tables.
    centers = qall(conn, "center_detail_centerdetail")
    subs = qall(conn, "center_detail_subscription")
    staff = qall(conn, "authentication_staffaccount")
    doctors = qall(conn, "diagnosis_doctor")
    dtypes = qall(conn, "diagnosis_diagnosistype")
    franchises = qall(conn, "diagnosis_franchisename")
    bills = qall(conn, "diagnosis_bill")
    preports = qall(conn, "diagnosis_patientreport")
    sreports = qall(conn, "diagnosis_sampletestreport")

    # Build legacy diagnosis type lookups.
    dtype_by_id = {row["id"]: row for row in dtypes}
    categories = sorted({str(row["category"]).strip() for row in dtypes if row["category"]})

    # Migrate in one transaction.
    with transaction.atomic():
        # Ensure target is empty for migrated app data.
        BillDiagnosisType.objects.all().delete()
        Bill.objects.all().delete()
        PatientReport.objects.all().delete()
        SampleTestReport.objects.all().delete()
        DoctorCategoryPercentage.objects.all().delete()
        DiagnosisType.objects.all().delete()
        DiagnosisCategory.objects.all().delete()
        Doctor.objects.all().delete()
        FranchiseName.objects.all().delete()
        Subscription.objects.all().delete()
        StaffAccount.objects.all().delete()
        CenterDetail.objects.all().delete()

        # Centers
        center_objs = []
        for r in centers:
            center_objs.append(
                CenterDetail(
                    id=r["id"],
                    center_name=r["center_name"],
                    address=r["address"],
                    owner_name=r["owner_name"],
                    owner_phone=r["owner_phone"],
                )
            )
        CenterDetail.objects.bulk_create(center_objs)

        # Subscriptions
        sub_objs = []
        for r in subs:
            sub_objs.append(
                Subscription(
                    id=r["id"],
                    center_id=r["center_id"],
                    plan_type=r["plan_type"],
                    purchase_date=as_date(r["purchase_date"]),
                    expiry_date=as_date(r["expiry_date"]),
                    is_active=as_bool(r["is_active"]),
                )
            )
        Subscription.objects.bulk_create(sub_objs)

        # Staff
        staff_objs = []
        for r in staff:
            staff_objs.append(
                StaffAccount(
                    id=r["id"],
                    password=r["password"],
                    last_login=as_dt(r["last_login"]),
                    is_superuser=as_bool(r["is_superuser"]),
                    is_active=as_bool(r["is_active"]),
                    date_joined=as_dt(r["date_joined"]),
                    username=r["username"],
                    email=r["email"],
                    first_name=r["first_name"],
                    last_name=r["last_name"],
                    address=r["address"],
                    is_admin=as_bool(r["is_admin"]),
                    phone_number=r["phone_number"],
                    center_detail_id=r["center_detail_id"],
                    is_locked=as_bool(r["is_locked"]),
                    is_staff=as_bool(r["is_staff"]),
                    failed_login_attempts=as_int(r["failed_login_attempts"]),
                    lockout_until=as_dt(r["lockout_until"]),
                )
            )
        StaffAccount.objects.bulk_create(staff_objs)

        # Categories (new schema)
        cat_map = {}
        for idx, name in enumerate(categories, start=1):
            obj = DiagnosisCategory(
                id=idx,
                name=name,
                is_franchise_lab=name.strip().lower() == "franchise lab",
                is_active=True,
            )
            obj.save(force_insert=True)
            cat_map[name] = obj.id

        # Doctors
        doctor_objs = []
        for r in doctors:
            doctor_objs.append(
                Doctor(
                    id=r["id"],
                    center_detail_id=r["center_detail_id"],
                    first_name=r["first_name"],
                    last_name=r["last_name"],
                    hospital_name=r["hospital_name"],
                    address=r["address"],
                    phone_number=r["phone_number"],
                    email=r["email"],
                    ultrasound_percentage=as_int(r["ultrasound_percentage"]),
                    pathology_percentage=as_int(r["pathology_percentage"]),
                    ecg_percentage=as_int(r["ecg_percentage"]),
                    xray_percentage=as_int(r["xray_percentage"]),
                    franchise_lab_percentage=as_int(r["franchise_lab_percentage"]),
                    others_percentage=0,
                )
            )
        Doctor.objects.bulk_create(doctor_objs)

        # Diagnosis types (convert old category text -> FK)
        dtype_objs = []
        for r in dtypes:
            cat_id = cat_map.get(str(r["category"]).strip())
            if not cat_id:
                continue
            dtype_objs.append(
                DiagnosisType(
                    id=r["id"],
                    center_detail_id=r["center_detail_id"],
                    name=r["name"],
                    category_id=cat_id,
                    price=as_int(r["price"]),
                )
            )
        DiagnosisType.objects.bulk_create(dtype_objs)

        # Populate dynamic doctor/category percentages from legacy doctor fields.
        percent_by_name = {
            "ultrasound": "ultrasound_percentage",
            "pathology": "pathology_percentage",
            "ecg": "ecg_percentage",
            "x-ray": "xray_percentage",
            "xray": "xray_percentage",
            "franchise lab": "franchise_lab_percentage",
            "others": "others_percentage",
        }
        cat_id_by_lower = {name.lower(): cid for name, cid in cat_map.items()}

        dcp_objs = []
        for d in doctor_objs:
            for cname, cid in cat_id_by_lower.items():
                attr = percent_by_name.get(cname)
                pct = getattr(d, attr) if attr else 0
                dcp_objs.append(
                    DoctorCategoryPercentage(
                        doctor_id=d.id,
                        category_id=cid,
                        percentage=max(0, as_int(pct)),
                    )
                )
        DoctorCategoryPercentage.objects.bulk_create(dcp_objs, ignore_conflicts=True)

        # Franchises
        fr_objs = []
        for r in franchises:
            fr_objs.append(
                FranchiseName(
                    id=r["id"],
                    franchise_name=r["franchise_name"],
                    address=r["address"],
                    phone_number=r["phone_number"],
                    center_detail_id=r["center_detail_id"],
                )
            )
        FranchiseName.objects.bulk_create(fr_objs)

        # Bills + through table conversion from legacy diagnosis_type_id.
        bill_objs = []
        through_objs = []

        for r in bills:
            bill_objs.append(
                Bill(
                    id=r["id"],
                    bill_number=r["bill_number"],
                    date_of_test=as_dt(r["date_of_test"]),
                    patient_name=r["patient_name"],
                    patient_age=as_int(r["patient_age"]),
                    patient_sex=r["patient_sex"],
                    patient_phone_number=as_int(r["patient_phone_number"], 9999999999),
                    test_done_by_id=r["test_done_by_id"],
                    referred_by_doctor_id=r["referred_by_doctor_id"],
                    franchise_name_id=r["franchise_name_id"],
                    date_of_bill=as_dt(r["date_of_bill"]),
                    bill_status=r["bill_status"],
                    total_amount=as_int(r["total_amount"]),
                    paid_amount=as_int(r["paid_amount"]),
                    disc_by_center=as_int(r["disc_by_center"]),
                    disc_by_doctor=as_int(r["disc_by_doctor"]),
                    incentive_amount=as_int(r["incentive_amount"]),
                    center_detail_id=r["center_detail_id"],
                )
            )

            old_dtype_id = r["diagnosis_type_id"]
            old_dtype = dtype_by_id.get(old_dtype_id)
            price_at_time = as_int(old_dtype["price"]) if old_dtype else as_int(r["total_amount"])
            if old_dtype_id is not None:
                through_objs.append(
                    BillDiagnosisType(
                        bill_id=r["id"],
                        diagnosis_type_id=old_dtype_id,
                        price_at_time=price_at_time,
                    )
                )

        Bill.objects.bulk_create(bill_objs)
        BillDiagnosisType.objects.bulk_create(through_objs, ignore_conflicts=True)

        # Patient reports
        pr_objs = []
        for r in preports:
            pr_objs.append(
                PatientReport(
                    id=r["id"],
                    report_file=r["report_file"],
                    bill_id=r["bill_id"],
                    center_detail_id=r["center_detail_id"],
                )
            )
        PatientReport.objects.bulk_create(pr_objs)

        # Sample reports
        sr_objs = []
        for r in sreports:
            sr_objs.append(
                SampleTestReport(
                    id=r["id"],
                    diagnosis_name=r["diagnosis_name"],
                    sample_report_file=r["sample_report_file"],
                    center_detail_id=r["center_detail_id"],
                    category=r["category"],
                )
            )
        SampleTestReport.objects.bulk_create(sr_objs)

    # Summary
    summary = {
        "staff": StaffAccount.objects.count(),
        "centers": CenterDetail.objects.count(),
        "subscriptions": Subscription.objects.count(),
        "doctors": Doctor.objects.count(),
        "categories": DiagnosisCategory.objects.count(),
        "diagnosis_types": DiagnosisType.objects.count(),
        "franchises": FranchiseName.objects.count(),
        "bills": Bill.objects.count(),
        "bill_diagnosis_types": BillDiagnosisType.objects.count(),
        "patient_reports": PatientReport.objects.count(),
        "sample_reports": SampleTestReport.objects.count(),
    }
    print("MIGRATION_SUMMARY", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
