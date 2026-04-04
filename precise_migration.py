import sqlite3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LabLedger.settings')
django.setup()

from center_detail.models import CenterDetail, Subscription
from authentication.models import StaffAccount
from diagnosis.models import (
    DiagnosisCategory, DiagnosisType, Doctor, DoctorCategoryPercentage,
    Bill, BillDiagnosisType, PatientReport, SampleTestReport, FranchiseName
)

def run_precise_migration():
    # 1. Connect to old database
    conn = sqlite3.connect('hasdatadb.sqlite3')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- STARTING PRECISE MIGRATION ---")

    # 2. CLEAR ALL EXISTING DATA (Truncate logic)
    print("Clearing existing data for a fresh sync...")
    BillDiagnosisType.objects.all().delete()
    PatientReport.objects.all().delete()
    SampleTestReport.objects.all().delete()
    Bill.objects.all().delete()
    DoctorCategoryPercentage.objects.all().delete()
    Doctor.objects.all().delete()
    DiagnosisType.objects.all().delete()
    DiagnosisCategory.objects.all().delete()
    FranchiseName.objects.all().delete()
    StaffAccount.objects.all().delete()
    Subscription.objects.all().delete()
    CenterDetail.objects.all().delete()

    # 3. Migrate CenterDetail & Subscription
    print("Migrating Centers...")
    cursor.execute("SELECT * FROM center_detail_centerdetail")
    centers = cursor.fetchall()
    for row in centers:
        CenterDetail.objects.create(
            id=row['id'],
            center_name=row['center_name'],
            owner_name=row['owner_name'],
            owner_phone=row['owner_phone'],
            address=row['address'],
        )

    print("Migrating Subscriptions...")
    cursor.execute("SELECT * FROM center_detail_subscription")
    subs = cursor.fetchall()
    for row in subs:
        Subscription.objects.create(
            id=row['id'],
            plan_type=row['plan_type'],
            purchase_date=row['purchase_date'],
            is_active=row['is_active'],
            expiry_date=row['expiry_date'],
            center_id=row['center_id']
        )

    # 4. Migrate StaffAccount (Users)
    print("Migrating Users (StaffAccounts)...")
    cursor.execute("SELECT * FROM authentication_staffaccount")
    users = cursor.fetchall()
    for row in users:
        u = StaffAccount(
            id=row['id'],
            password=row['password'],
            last_login=row['last_login'],
            is_superuser=row['is_superuser'],
            is_active=row['is_active'],
            date_joined=row['date_joined'],
            username=row['username'],
            email=row['email'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            address=row['address'],
            phone_number=row['phone_number'],
            center_detail_id=row['center_detail_id'],
            is_admin=row['is_admin'],
            is_staff=row['is_staff'],
            is_locked=row['is_locked'],
            failed_login_attempts=row['failed_login_attempts'],
            lockout_until=row['lockout_until']
        )
        u.save(force_insert=True) # force_insert = preserve ID

    # 5. Initialize Diagnosis Categories
    print("Initializing Diagnosis Categories...")
    cat_names = ['Ultrasound', 'Pathology', 'ECG', 'X-Ray', 'Franchise Lab', 'Others']
    category_map = {}
    for name in cat_names:
        cat = DiagnosisCategory.objects.create(
            name=name,
            is_franchise_lab=(name == 'Franchise Lab')
        )
        category_map[name] = cat

    # 6. Migrate Doctors & Percentages
    print("Migrating Doctors and Incentive Percentages...")
    cursor.execute("SELECT * FROM diagnosis_doctor")
    doctors = cursor.fetchall()
    for row in doctors:
        doc = Doctor.objects.create(
            id=row['id'],
            center_detail_id=row['center_detail_id'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            hospital_name=row['hospital_name'],
            address=row['address'],
            phone_number=row['phone_number'],
            email=row['email'],
            # Preserve old fields for legacy app instances if needed
            ultrasound_percentage=row['ultrasound_percentage'],
            pathology_percentage=row['pathology_percentage'],
            ecg_percentage=row['ecg_percentage'],
            xray_percentage=row['xray_percentage'],
            franchise_lab_percentage=row['franchise_lab_percentage']
        )
        
        # Mapping old percentage fields to new DoctorCategoryPercentage table
        percentage_data = [
            ('Ultrasound', row['ultrasound_percentage']),
            ('Pathology', row['pathology_percentage']),
            ('ECG', row['ecg_percentage']),
            ('X-Ray', row['xray_percentage']),
            ('Franchise Lab', row['franchise_lab_percentage']),
        ]
        
        for cat_name, pct in percentage_data:
            if pct and pct > 0:
                DoctorCategoryPercentage.objects.create(
                    doctor=doc,
                    category=category_map[cat_name],
                    percentage=pct
                )

    # 7. Migrate DiagnosisType
    print("Migrating DiagnosisTypes...")
    cursor.execute("SELECT * FROM diagnosis_diagnosistype")
    d_types = cursor.fetchall()
    for row in d_types:
        # Match old category string to new DiagnosisCategory object
        old_cat = row['category']
        if old_cat not in category_map:
            old_cat = 'Others'
            
        DiagnosisType.objects.create(
            id=row['id'],
            center_detail_id=row['center_detail_id'],
            name=row['name'],
            price=row['price'],
            category=category_map[old_cat]
        )

    conn.close()
    print("--- PRECISE MIGRATION COMPLETED SUCCESSFULLY ---")

if __name__ == '__main__':
    run_precise_migration()
