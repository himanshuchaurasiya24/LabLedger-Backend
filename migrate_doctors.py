import os
import django
import sqlite3
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LabLedger.settings')
django.setup()

from diagnosis.models import Doctor, DiagnosisCategory, DoctorCategoryPercentage
from center_detail.models import CenterDetail

OLD_DB_PATH = 'olddb.sqlite3'

def run_migration():
    if not os.path.exists(OLD_DB_PATH):
        print(f"Error: {OLD_DB_PATH} not found.")
        return

    print(f"Connecting to {OLD_DB_PATH}...")
    conn = sqlite3.connect(OLD_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM diagnosis_doctor")
        old_doctors = cursor.fetchall()
        print(f"Found {len(old_doctors)} doctors in old database.")
    except Exception as e:
        print(f"Error reading old database: {e}")
        return
    finally:
        conn.close()

    # Get default CenterDetail
    try:
        center = CenterDetail.objects.get(id=1)
    except CenterDetail.DoesNotExist:
        print("Error: CenterDetail with ID 1 not found. Please ensure it exists.")
        return

    # Categories to migrate
    CATEGORY_MAPPING = {
        'Ultrasound': 'ultrasound_percentage',
        'Pathology': 'pathology_percentage',
        'ECG': 'ecg_percentage',
        'X-Ray': 'xray_percentage',
        'Franchise Lab': 'franchise_lab_percentage',
    }

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    print("Starting migration...")

    for old_doc in old_doctors:
        phone = old_doc['phone_number']
        
        # Check if doctor already exists
        if Doctor.objects.filter(phone_number=phone).exists():
            print(f"Skipping doctor {old_doc['first_name']} {old_doc['last_name']} (Phone: {phone}) - Already exists.")
            skipped_count += 1
            continue

        try:
            # Create Doctor
            new_doc = Doctor(
                center_detail=center,
                first_name=old_doc['first_name'],
                last_name=old_doc['last_name'],
                hospital_name=old_doc['hospital_name'],
                address=old_doc['address'],
                phone_number=phone,
                email=old_doc['email'],
                # Legacy fields
                ultrasound_percentage=old_doc['ultrasound_percentage'],
                pathology_percentage=old_doc['pathology_percentage'],
                ecg_percentage=old_doc['ecg_percentage'],
                xray_percentage=old_doc['xray_percentage'],
                franchise_lab_percentage=old_doc['franchise_lab_percentage']
            )
            new_doc.save()

            # Create Incentive Percentages
            for cat_name, old_col in CATEGORY_MAPPING.items():
                percentage_value = old_doc[old_col]
                
                # Retrieve category object
                category_obj = DiagnosisCategory.objects.filter(name=cat_name).first()
                if category_obj:
                    DoctorCategoryPercentage.objects.create(
                        doctor=new_doc,
                        category=category_obj,
                        percentage=percentage_value
                    )
                else:
                    print(f"Warning: Category '{cat_name}' not found for doctor {new_doc}. Skipping incentive.")

            print(f"Migrated: {new_doc.first_name} {new_doc.last_name}")
            migrated_count += 1

        except Exception as e:
            print(f"Error migrating doctor {old_doc['first_name']} {old_doc['last_name']}: {e}")
            error_count += 1

    print("\nMigration Completed.")
    print(f"Total: {len(old_doctors)}")
    print(f"Migrated: {migrated_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Errors: {error_count}")

if __name__ == '__main__':
    run_migration()
