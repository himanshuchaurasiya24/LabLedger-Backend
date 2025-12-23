import sqlite3
import shutil
import os
from datetime import datetime

OLD_DB = 'olddb.sqlite3'
NEW_DB = 'db.sqlite3'

def connect_db(db_name):
    return sqlite3.connect(db_name)

def format_doctor_name(first_name, last_name):
    f = (first_name or "").strip()
    l = (last_name or "").strip()
    full = f"{f} {l}".strip()
    lower_full = full.lower()
    if lower_full.startswith("dr."):
        full = full[3:].strip()
    elif lower_full.startswith("dr"):
        full = full[2:].strip()
    full = full.title()
    return f"Dr. {full}"

def migrate():
    if not os.path.exists(OLD_DB):
        print(f"Error: {OLD_DB} not found")
        return

    conn_old = connect_db(OLD_DB)
    curr_old = conn_old.cursor()
    
    conn_new = connect_db(NEW_DB)
    curr_new = conn_new.cursor()
    
    curr_new.execute("PRAGMA foreign_keys = OFF;")
    
    try:
        print("=== 1. Cleaning Target Tables ===")
        # Order matters for deletion (reverse dependency), though FK check is OFF.
        # Tables to migrate:
        tables_to_clear = [
            'diagnosis_patientreport',
            'diagnosis_sampletestreport',
            'diagnosis_billdiagnosistype',
            'diagnosis_bill',
            'diagnosis_diagnosistype',
            'diagnosis_franchisename',
            'diagnosis_doctorcategorypercentage', # NEW: Clear this first
            'diagnosis_doctor', 
            'diagnosis_diagnosiscategory', 
            'center_detail_subscription', # NEW: Clear subscriptions
            'center_detail_centerdetail', 
            'authentication_staffaccount'
        ]
        for table in tables_to_clear:
            try:
                curr_new.execute(f"DELETE FROM {table}")
                print(f"Cleared table: {table}")
            except sqlite3.Error as e:
                print(f"Warning: Could not clear {table}: {e}")
        
        # === 2. CENTER MIGRATION ===
        print("=== 2. Migrating Center Details ===")
        center_map = {} # old_id -> new_id
        
        curr_old.execute("SELECT * FROM center_detail_centerdetail")
        cols_old_cd = [d[0] for d in curr_old.description]
        old_centers = curr_old.fetchall()
        
        for row in old_centers:
            d = dict(zip(cols_old_cd, row))
            curr_new.execute("""
                INSERT INTO center_detail_centerdetail
                (center_name, address, owner_name, owner_phone) 
                VALUES (?, ?, ?, ?)
            """, (d.get('center_name'), d.get('address'), d.get('owner_name'), d.get('owner_phone')))
            center_map[d['id']] = curr_new.lastrowid
        print(f"Migrated {len(center_map)} centers.")

        # === 3. USER MIGRATION ===
        print("=== 3. Migrating Users ===")
        user_map = {} # old_id -> new_id
        
        curr_old.execute("SELECT * FROM authentication_staffaccount")
        cols_users = [d[0] for d in curr_old.description]
        for row in curr_old.fetchall():
            d = dict(zip(cols_users, row))
            new_cid = center_map.get(d.get('center_detail_id'))
            
            curr_new.execute("""
                INSERT INTO authentication_staffaccount 
                (password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, address, phone_number, center_detail_id, is_admin, is_locked, failed_login_attempts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d.get('password'), d.get('last_login'), d.get('is_superuser'), d.get('username'),
                d.get('first_name'), d.get('last_name'), d.get('email'), d.get('is_staff'),
                d.get('is_active'), d.get('date_joined'), d.get('address'), d.get('phone_number'),
                new_cid, 0, 0, 0
            ))
            user_map[d['id']] = curr_new.lastrowid
        print(f"Migrated {len(user_map)} users.")

        # === 3.5. MIGRATING SUBSCRIPTIONS ===
        print("=== 3.5. Migrating Subscriptions ===")
        curr_new.execute("DELETE FROM center_detail_subscription") # Double check clear
        curr_old.execute("SELECT * FROM center_detail_subscription")
        cols_sub = [d[0] for d in curr_old.description]
        sub_count = 0
        for row in curr_old.fetchall():
            sub = dict(zip(cols_sub, row))
            new_cid = center_map.get(sub.get('center_id'))
            if not new_cid:
                continue
            
            curr_new.execute("""
                INSERT INTO center_detail_subscription
                (plan_type, purchase_date, is_active, expiry_date, center_id)
                VALUES (?, ?, ?, ?, ?)
            """,(
                sub.get('plan_type'), sub.get('purchase_date'), sub.get('is_active'), sub.get('expiry_date'), new_cid
            ))
            sub_count += 1
        print(f"Migrated {sub_count} subscriptions.")

        # === 4. CATEGORIES ===
        print("=== 4. Creating Categories ===")
        categories = [
            ("Ultrasound", "Ultrasound Tests", False),
            ("Pathology", "Pathology Tests", False),
            ("ECG", "ECG Tests", False),
            ("X-Ray", "X-Ray Tests", False),
            ("Franchise Lab", "Franchise Lab Tests", True)
        ]
        cat_map = {} # name -> id
        for name, desc, is_fran in categories:
            curr_new.execute("""
                INSERT INTO diagnosis_diagnosiscategory (name, description, is_franchise_lab, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, desc, is_fran, True, datetime.now(), datetime.now()))
            cat_map[name] = curr_new.lastrowid
        print(f"Created {len(categories)} categories.")

        # === 5. DOCTORS ===
        print("=== 5. Migrating Doctors ===")
        doctor_map = {} # old_id -> new_id
        curr_old.execute("SELECT * FROM diagnosis_doctor")
        cols_doc = [d[0] for d in curr_old.description]
        for row in curr_old.fetchall():
            d = dict(zip(cols_doc, row))
            
            formatted_name = format_doctor_name(d.get('first_name'), d.get('last_name'))
            parts = formatted_name.split(' ', 1)
            f_original = (d.get('first_name') or "").strip()
            if f_original.lower().startswith('dr'): f_original = f_original[2:].replace('.', '').strip()
            final_first = f"Dr. {f_original.title()}"
            final_last = (d.get('last_name') or "").strip().title()
            
            new_cid = center_map.get(d.get('center_detail_id'))
            
            curr_new.execute("""
                INSERT INTO diagnosis_doctor 
                (first_name, last_name, hospital_name, address, phone_number, email, 
                 ultrasound_percentage, pathology_percentage, ecg_percentage, xray_percentage, franchise_lab_percentage,
                 center_detail_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                final_first, final_last, d.get('hospital_name'), d.get('address'), d.get('phone_number'), d.get('email'),
                d.get('ultrasound_percentage', 0), d.get('pathology_percentage', 0), d.get('ecg_percentage', 0),
                d.get('xray_percentage', 0), d.get('franchise_lab_percentage', 0), new_cid
            ))
            new_doc_id = curr_new.lastrowid
            doctor_map[d['id']] = new_doc_id

            # NEW: Populate DoctorCategoryPercentage
            legacy_percentages = [
                ('Ultrasound', d.get('ultrasound_percentage', 0)),
                ('Pathology', d.get('pathology_percentage', 0)),
                ('ECG', d.get('ecg_percentage', 0)),
                ('X-Ray', d.get('xray_percentage', 0)),
                ('Franchise Lab', d.get('franchise_lab_percentage', 0))
            ]

            for cat_name, pct in legacy_percentages:
                if pct and pct > 0:
                    cat_id = cat_map.get(cat_name)
                    if cat_id:
                        curr_new.execute("""
                            INSERT INTO diagnosis_doctorcategorypercentage (percentage, category_id, doctor_id)
                            VALUES (?, ?, ?)
                        """, (pct, cat_id, new_doc_id))
        print(f"Migrated {len(doctor_map)} doctors and their percentages.")

        # === 6. FRANCHISES ===
        print("=== 6. Migrating Franchises ===")
        franchise_map = {} # old_id -> new_id
        curr_old.execute("SELECT * FROM diagnosis_franchisename")
        cols_fran = [d[0] for d in curr_old.description]
        for row in curr_old.fetchall():
            d = dict(zip(cols_fran, row))
            new_cid = center_map.get(d.get('center_detail_id'))
            curr_new.execute("""
                INSERT INTO diagnosis_franchisename (franchise_name, address, phone_number, center_detail_id)
                VALUES (?, ?, ?, ?)
            """, (d.get('franchise_name'), d.get('address'), d.get('phone_number'), new_cid))
            franchise_map[d['id']] = curr_new.lastrowid
        print(f"Migrated {len(franchise_map)} franchises.")

        # === 7. DIAGNOSIS TYPES ===
        print("=== 7. Migrating Diagnosis Types ===")
        dt_map = {} # old_id -> new_id
        curr_old.execute("SELECT * FROM diagnosis_diagnosistype")
        cols_dt = [d[0] for d in curr_old.description]
        for row in curr_old.fetchall():
            d = dict(zip(cols_dt, row))
            new_cat_id = cat_map.get(d.get('category'))
            new_cid = center_map.get(d.get('center_detail_id'))
            
            if not new_cat_id:
                print(f"Warning: Category {d.get('category')} not found.")
                continue # Or skip?
            
            curr_new.execute("""
                INSERT INTO diagnosis_diagnosistype (name, price, category_id, center_detail_id)
                VALUES (?, ?, ?, ?)
            """, (d.get('name'), d.get('price'), new_cat_id, new_cid))
            dt_map[d['id']] = curr_new.lastrowid
        print(f"Migrated {len(dt_map)} diagnosis types.")

        # === 8. BILLS ===
        print("=== 8. Migrating Bills ===")
        bill_map = {} # old_id -> new_id
        curr_old.execute("SELECT * FROM diagnosis_bill")
        cols_bill = [d[0] for d in curr_old.description]
        m2m_records = []
        
        for row in curr_old.fetchall():
            d = dict(zip(cols_bill, row))
            new_cid = center_map.get(d.get('center_detail_id'))
            new_doc = doctor_map.get(d.get('referred_by_doctor_id'))
            new_staff = user_map.get(d.get('test_done_by_id'))
            new_fran = franchise_map.get(d.get('franchise_name_id'))
            
            curr_new.execute("""
                INSERT INTO diagnosis_bill 
                (bill_number, date_of_test, patient_name, patient_age, patient_sex, patient_phone_number,
                 date_of_bill, bill_status, total_amount, paid_amount, disc_by_center, disc_by_doctor, incentive_amount,
                 center_detail_id, referred_by_doctor_id, test_done_by_id, franchise_name_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d.get('bill_number'), d.get('date_of_test'), d.get('patient_name'), d.get('patient_age'),
                d.get('patient_sex'), d.get('patient_phone_number'), d.get('date_of_bill'), d.get('bill_status'),
                d.get('total_amount'), d.get('paid_amount'), d.get('disc_by_center'), d.get('disc_by_doctor'),
                d.get('incentive_amount'), new_cid, new_doc, new_staff, new_fran
            ))
            new_bill_id = curr_new.lastrowid
            bill_map[d['id']] = new_bill_id
            
            # Map old diagnosis type to new M2M
            old_dt = d.get('diagnosis_type_id')
            new_dt = dt_map.get(old_dt)
            if new_dt:
                price = d.get('total_amount') # Approximate
                m2m_records.append((new_bill_id, new_dt, price))
        
        print(f"Migrated {len(bill_map)} bills.")

        # === 9. BILL M2M ===
        print("=== 9. Creating BillDiagnosisType entries ===")
        for b_id, dt_id, price in m2m_records:
            curr_new.execute("""
                INSERT INTO diagnosis_billdiagnosistype (bill_id, diagnosis_type_id, price_at_time)
                VALUES (?, ?, ?)
            """, (b_id, dt_id, price))
        print(f"Created {len(m2m_records)} M2M entries.")

        # === 10. PATIENT REPORTS ===
        print("=== 10. Migrating Patient Reports ===")
        curr_old.execute("SELECT * FROM diagnosis_patientreport")
        cols_pr = [d[0] for d in curr_old.description]
        count_pr = 0
        for row in curr_old.fetchall():
            d = dict(zip(cols_pr, row))
            new_bill = bill_map.get(d.get('bill_id'))
            new_cid = center_map.get(d.get('center_detail_id'))
            if new_bill:
                curr_new.execute("""
                    INSERT INTO diagnosis_patientreport (report_file, bill_id, center_detail_id)
                    VALUES (?, ?, ?)
                """, (d.get('report_file'), new_bill, new_cid))
                count_pr += 1
        print(f"Migrated {count_pr} patient reports.")

        # === 11. SAMPLE REPORTS ===
        print("=== 11. Migrating Sample Reports ===")
        curr_old.execute("SELECT * FROM diagnosis_sampletestreport")
        cols_str = [d[0] for d in curr_old.description]
        count_str = 0
        for row in curr_old.fetchall():
            d = dict(zip(cols_str, row))
            new_cid = center_map.get(d.get('center_detail_id'))
            curr_new.execute("""
                INSERT INTO diagnosis_sampletestreport (category, diagnosis_name, sample_report_file, center_detail_id)
                VALUES (?, ?, ?, ?)
            """, (d.get('category'), d.get('diagnosis_name'), d.get('sample_report_file'), new_cid))
            count_str += 1
        print(f"Migrated {count_str} sample reports.")

        conn_new.commit()
        print("Migration committed successfully.")
        
    except Exception as e:
        print(f"Migration Failed: {e}")
        conn_new.rollback()
    finally:
        curr_new.execute("PRAGMA foreign_keys = ON;")
        conn_old.close()
        conn_new.close()

if __name__ == "__main__":
    migrate()
