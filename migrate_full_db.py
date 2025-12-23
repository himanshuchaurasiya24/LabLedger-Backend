import os
import django
import sqlite3
from datetime import datetime
from django.utils.dateparse import parse_datetime
from django.utils import timezone as django_timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LabLedger.settings')
django.setup()

from diagnosis.models import (
    Doctor, DiagnosisCategory, DoctorCategoryPercentage, DiagnosisType,
    FranchiseName, Bill, BillDiagnosisType, PatientReport, SampleTestReport
)
from center_detail.models import CenterDetail
from authentication.models import StaffAccount

OLD_DB_PATH = 'olddb.sqlite3'

def get_aware_datetime(dt_str):
    if not dt_str:
        return None
    try:
        # DB usually stores as string
        dt = parse_datetime(dt_str)
        if dt is None:
             # Fallback for simple formats if parse_datetime fails
             dt = datetime.fromisoformat(dt_str)
        
        if dt and django_timezone.is_naive(dt):
             return django_timezone.make_aware(dt)
        return dt
    except Exception:
        return None

def run_migration():
    if not os.path.exists(OLD_DB_PATH):
        print(f"Error: {OLD_DB_PATH} not found.")
        return

    print(f"Connecting to {OLD_DB_PATH}...")
    conn = sqlite3.connect(OLD_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get default CenterDetail
    try:
        center = CenterDetail.objects.get(id=1)
    except CenterDetail.DoesNotExist:
        print("Error: CenterDetail with ID 1 not found.")
        return

    # MAPPINGS (Old ID -> New Instance)
    staff_map = {}
    franchise_map = {}
    diagnosis_type_map = {}
    doctor_map = {}
    bill_map = {}

    # ==========================================
    # 1. StaffAccount Migration
    # ==========================================
    print("\n--- Migrating StaffAccounts ---")
    cursor.execute("SELECT * FROM authentication_staffaccount")
    for row in cursor.fetchall():
        try:
            username = row['username']
            # Check if exists
            staff = StaffAccount.objects.filter(username=username).first()
            if not staff:
                staff = StaffAccount(
                    username=username,
                    email=row['email'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    address=row['address'],
                    phone_number=row['phone_number'],
                    is_active=row['is_active'],
                    is_staff=row['is_staff'],
                    is_superuser=row['is_superuser'],
                    password=row['password'], # Copy hash
                    center_detail=center
                )
                staff.save()
                print(f"Created Staff: {username}")
            else:
                print(f"Skipped Staff: {username} (Exists)")
            
            staff_map[row['id']] = staff
        except Exception as e:
            print(f"Error migrating staff {row['username']}: {e}")

    # ==========================================
    # 2. FranchiseName Migration
    # ==========================================
    print("\n--- Migrating FranchiseNames ---")
    cursor.execute("SELECT * FROM diagnosis_franchisename")
    for row in cursor.fetchall():
        try:
            name = row['franchise_name']
            franchise = FranchiseName.objects.filter(franchise_name=name).first()
            if not franchise:
                franchise = FranchiseName.objects.create(
                    franchise_name=name,
                    address=row['address'],
                    phone_number=row['phone_number'],
                    center_detail=center
                )
                print(f"Created Franchise: {name}")
            else:
                 print(f"Skipped Franchise: {name} (Exists)")
            
            franchise_map[row['id']] = franchise
        except Exception as e:
            print(f"Error migrating franchise {row['franchise_name']}: {e}")

    # ==========================================
    # 3. DiagnosisType Migration
    # ==========================================
    print("\n--- Migrating DiagnosisTypes ---")
    cursor.execute("SELECT * FROM diagnosis_diagnosistype")
    for row in cursor.fetchall():
        try:
            name = row['name']
            category_name = row['category']
            
            # Find Category
            category = DiagnosisCategory.objects.filter(name=category_name).first()
            if not category:
                # Fallback or create if missing? Better to warn.
                print(f"Warning: Category '{category_name}' not found for diagnosis '{name}'. Skipping.")
                continue

            # Check if DT exists (by name and category)
            dt = DiagnosisType.objects.filter(name=name, category=category).first()
            if not dt:
                dt = DiagnosisType.objects.create(
                    name=name,
                    category=category,
                    price=row['price'],
                    center_detail=center
                )
                print(f"Created DiagnosisType: {name} ({category_name})")
            
            diagnosis_type_map[row['id']] = dt
        except Exception as e:
            print(f"Error migrating DiagnosisType {row['name']}: {e}")

    # ==========================================
    # 4. Doctor Mapping (Already migrated)
    # ==========================================
    print("\n--- Mapping Doctors ---")
    cursor.execute("SELECT * FROM diagnosis_doctor")
    for row in cursor.fetchall():
        try:
            phone = row['phone_number']
            doc = Doctor.objects.filter(phone_number=phone).first()
            if doc:
                doctor_map[row['id']] = doc
            else:
                print(f"Warning: Doctor {row['first_name']} (Phone: {phone}) not found in new DB but exists in old DB.")
        except Exception as e:
            pass

    # ==========================================
    # 5. Bill Migration
    # ==========================================
    print("\n--- Migrating Bills ---")
    cursor.execute("SELECT * FROM diagnosis_bill")
    for row in cursor.fetchall():
        try:
            bill_number = row['bill_number']
            if Bill.objects.filter(bill_number=bill_number).exists():
                print(f"Skipping Bill {bill_number} (Exists)")
                bill_map[row['id']] = Bill.objects.get(bill_number=bill_number)
                continue

            # Resolve FKs
            doctor = doctor_map.get(row['referred_by_doctor_id'])
            test_done_by = staff_map.get(row['test_done_by_id'])
            franchise = franchise_map.get(row['franchise_name_id'])
            old_dt = diagnosis_type_map.get(row['diagnosis_type_id'])

            if not old_dt:
                print(f"Error: Diagnosis Type missing for bill {bill_number}. Skipping.")
                continue

            # Create Bill
            # Note: We set total_amount/incentive_amount manually to match old record exactly
            bill = Bill(
                bill_number=bill_number,
                date_of_test=get_aware_datetime(row['date_of_test']),
                patient_name=row['patient_name'],
                patient_age=row['patient_age'],
                patient_sex=row['patient_sex'],
                patient_phone_number=row['patient_phone_number'],
                test_done_by=test_done_by,
                referred_by_doctor=doctor,
                franchise_name=franchise,
                date_of_bill=get_aware_datetime(row['date_of_bill']),
                bill_status=row['bill_status'],
                paid_amount=row['paid_amount'],
                disc_by_center=row['disc_by_center'],
                disc_by_doctor=row['disc_by_doctor'],
                center_detail=center
            )
            # We save first to get an ID
            bill.save()
            
            # Force update calculated fields to match legacy data exactly
            Bill.objects.filter(id=bill.id).update(
                total_amount=row['total_amount'],
                incentive_amount=row['incentive_amount']
            )

            # Create BillDiagnosisType (M2M)
            # The old system had 1 diagnosis per bill. New system allows multiple.
            # We map the single old one to the new M2M table.
            BillDiagnosisType.objects.create(
                bill=bill,
                diagnosis_type=old_dt,
                price_at_time=row['total_amount'] # Assuming price was total amount
            )

            bill_map[row['id']] = bill
            print(f"Created Bill: {bill_number}")

        except Exception as e:
            print(f"Error migrating Bill {row.get('bill_number')}: {e}")

    # ==========================================
    # 6. PatientReport Migration
    # ==========================================
    print("\n--- Migrating PatientReports ---")
    cursor.execute("SELECT * FROM diagnosis_patientreport")
    for row in cursor.fetchall():
        try:
            old_bill_id = row['bill_id']
            new_bill = bill_map.get(old_bill_id)
            
            if not new_bill:
                print(f"Warning: Bill not found for report {row['id']}. Skipping.")
                continue
            
            # Check for duplicates? report_file is unique potentially?
            # We'll just create it.
            
            # NOTE: We are keeping the file path string. 
            # If files need physically moving, that is a separate OS task.
            # Assuming file storage location is compatible or user moves files.
            
            PatientReport.objects.create(
                bill=new_bill,
                report_file=row['report_file'],
                center_detail=center
            )
            print(f"Created PatientReport for Bill {new_bill.bill_number}")
            
        except Exception as e:
             print(f"Error migrating PatientReport {row.get('id')}: {e}")

    # ==========================================
    # 7. SampleTestReport Migration
    # ==========================================
    print("\n--- Migrating SampleTestReports ---")
    cursor.execute("SELECT * FROM diagnosis_sampletestreport")
    for row in cursor.fetchall():
        try:
            cat = row['category']
            diag_name = row['diagnosis_name']
            
            if not SampleTestReport.objects.filter(category=cat, diagnosis_name=diag_name).exists():
                SampleTestReport.objects.create(
                    category=cat,
                    diagnosis_name=diag_name,
                    sample_report_file=row['sample_report_file'],
                    center_detail=center
                )
                print(f"Created SampleReport: {diag_name}")
            else:
                 print(f"Skipped SampleReport: {diag_name} (Exists)")

        except Exception as e:
             print(f"Error migrating SampleTestReport {row.get('id')}: {e}")

    conn.close()
    print("\nFull Database Migration Completed.")

if __name__ == '__main__':
    run_migration()
