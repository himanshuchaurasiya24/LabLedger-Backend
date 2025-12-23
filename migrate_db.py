import sqlite3
import shutil
import os
from datetime import datetime

OLD_DB = 'olddb.sqlite3'
NEW_DB = 'db.sqlite3'

def connect_db(db_name):
    return sqlite3.connect(db_name)

def format_doctor_name(first_name, last_name):
    # Combine first and last name, treating None or empty strings gracefully
    f = (first_name or "").strip()
    l = (last_name or "").strip()
    full = f"{f} {l}".strip()
    
    # Remove existing "Dr" prefixes to standardize
    lower_full = full.lower()
    if lower_full.startswith("dr."):
        full = full[3:].strip()
    elif lower_full.startswith("dr"):
        full = full[2:].strip()
        
    # Title Case everything
    full = full.title()
    
    # Prepend "Dr. "
    return f"Dr. {full}"

def migrate():
    if not os.path.exists(OLD_DB):
        print(f"Error: {OLD_DB} not found")
        return

    # Connect to both DBs
    conn_old = connect_db(OLD_DB)
    curr_old = conn_old.cursor()
    
    conn_new = connect_db(NEW_DB)
    curr_new = conn_new.cursor()
    
    # Turn off FK checks temporarily to avoid constraint issues during bulk insert
    curr_new.execute("PRAGMA foreign_keys = OFF;")
    
    try:
        print("=== 1. Calculating ID Maps & Cleaning Target ===")
        # NEW: Clear tables to ensure clean state and avoid UNIQUE constraint errors on re-run
        tables_to_clear = [
            'diagnosis_doctor', 
            'diagnosis_diagnosiscategory', 
            'center_detail_centerdetail', 
            'authentication_staffaccount'
        ]
        for table in tables_to_clear:
            try:
                curr_new.execute(f"DELETE FROM {table}")
                print(f"Cleared table: {table}")
            except sqlite3.Error as e:
                print(f"Warning: Could not clear {table}: {e}")
        

        # PRE-CALCULATION:
        # We need to map old centers to new centers first, because Users refer to Centers.
        
        center_map = {} # old_id -> new_id
        
        print("=== 2. Migrating Center Details ===")
        # Schema matches Old DB mostly: id, center_name, address, owner_name, owner_phone
        try:
            curr_old.execute("SELECT * FROM center_detail_centerdetail")
            cols_old_cd = [d[0] for d in curr_old.description]
            old_centers = curr_old.fetchall()
            
            for row in old_centers:
                row_dict = dict(zip(cols_old_cd, row))
                old_cid = row_dict['id']
                
                curr_new.execute("""
                    INSERT INTO center_detail_centerdetail
                    (center_name, address, owner_name, owner_phone) 
                    VALUES (?, ?, ?, ?)
                """, (
                    row_dict.get('center_name'),
                    row_dict.get('address'),
                    row_dict.get('owner_name'),
                    row_dict.get('owner_phone')
                    # Note: no is_active or dates in new schema based on check_center_schema.py output
                ))
                new_cid_inserted = curr_new.lastrowid
                center_map[old_cid] = new_cid_inserted
                    
            print(f"Migrated {len(center_map)} centers.")
            
        except sqlite3.OperationalError as e:
            print(f"Error migrating centers: {e}")

        # ID MAPPINGS: old_id -> new_id
        user_map = {} # for authentication_staffaccount
        
        print("=== 3. Migrating Users (authentication_staffaccount) ===")
        curr_old.execute("SELECT * FROM authentication_staffaccount")
        cols_old = [description[0] for description in curr_old.description]
        old_users = curr_old.fetchall()
        
        for row in old_users:
            old_row = dict(zip(cols_old, row))
            
            old_center_id = old_row.get('center_detail_id')
            new_center_id = center_map.get(old_center_id) # map to new ID or None
            
            curr_new.execute("""
                INSERT INTO authentication_staffaccount 
                (password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, address, phone_number, center_detail_id, is_admin, is_locked, failed_login_attempts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                old_row.get('password'),
                old_row.get('last_login'),
                old_row.get('is_superuser'),
                old_row.get('username'),
                old_row.get('first_name'),
                old_row.get('last_name'),
                old_row.get('email'),
                old_row.get('is_staff'),
                old_row.get('is_active'),
                old_row.get('date_joined'),
                old_row.get('address'),
                old_row.get('phone_number'),
                new_center_id, # link to new center
                0, # is_admin default
                0, # is_locked default
                0  # failed_login_attempts default
            ))
            new_id = curr_new.lastrowid
            user_map[old_row['id']] = new_id
            
        print(f"Migrated {len(user_map)} users.")



        
        print("=== 4. Creating Fixed Categories ===")
        # Categories: Ultrasound, Pathology, ECG, X-Ray, Franchise Lab
        # Table: diagnosis_diagnosiscategory (name, description, is_franchise_lab, is_active)
        
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

        print("=== 5. Migrating Doctors ===")
        # Table: diagnosis_doctor
        # Old cols: first_name, last_name, ultrasound_percentage, etc.
        # New cols: first_name, last_name, ultrasound_percentage, etc.
        
        curr_old.execute("SELECT * FROM diagnosis_doctor")
        cols_doc = [d[0] for d in curr_old.description]
        doctors = curr_old.fetchall()
        
        for row in doctors:
            d = dict(zip(cols_doc, row))
            
            # Format Name
            formatted_name = format_doctor_name(d.get('first_name'), d.get('last_name'))
            # Split back into First/Last for storage?
            # User said "name needs to be like first letter of every word in capital and dr should be Dr. then space"
            # The schema has first_name and last_name columns.
            # So I should probably store "Dr. Firstname" as first_name and "Lastname" as last_name? 
            # Or "Dr." as title? Schema doesn't have title.
            # Usually keep "Dr." in first name or just store cleanly. 
            # Let's put "Dr. Firstname" in first_name field to adhere to "Doctor Name" request broadly.
            
            parts = formatted_name.split(' ', 1)
            new_first = parts[0] # Dr.
            if len(parts) > 1:
                new_first += " " + parts[1].split(' ')[0] # Dr. Name
                # This is getting messy. 
                # Let's just do: First Name = "Dr. Firstname", Last Name = "Lastname"
                # Or better: First = "Dr. [First]", Last = "[Last]"
            
            f_original = (d.get('first_name') or "").strip()
            l_original = (d.get('last_name') or "").strip()
            
            # Clean original names
            if f_original.lower().startswith('dr'): f_original = f_original[2:].replace('.', '').strip()
            
            final_first = f"Dr. {f_original.title()}"
            final_last = l_original.title()
            
            # Center ID mapping
            old_cid = d.get('center_detail_id')
            new_cid = center_map.get(old_cid)
            
            if not new_cid:
                # Fallback: if we didn't migrate centers properly, try to find ANY center or use NULL
                # For now let's leave NULL if not found, or use 1 if we want to force assign.
                # But strict mapping is better.
                pass
            
            curr_new.execute("""
                INSERT INTO diagnosis_doctor 
                (first_name, last_name, hospital_name, address, phone_number, email, 
                 ultrasound_percentage, pathology_percentage, ecg_percentage, xray_percentage, franchise_lab_percentage,
                 center_detail_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                final_first,
                final_last,
                d.get('hospital_name'),
                d.get('address'),
                d.get('phone_number'),
                d.get('email'),
                d.get('ultrasound_percentage', 0),
                d.get('pathology_percentage', 0),
                d.get('ecg_percentage', 0),
                d.get('xray_percentage', 0),
                d.get('franchise_lab_percentage', 0),
                new_cid
            ))
            
            # Note: diagnosis_doctorcategorypercentage table exists in New DB. 
            # The user Asked "match the categories of the incentive percetage of doctor which is 5 so add 5 in categories"
            # It seems the New DB MIGHT expect us to populate `diagnosis_doctorcategorypercentage` linking doctor <-> category.
            # BUT the `diagnosis_doctor` table in New DB DOES have the percentage columns directly (ultrasound_percentage, etc).
            # So I will populate BOTH to be safe if that linkage table is intended for normalization.
            # However, looking at the schema: `diagnosis_doctor` HAS the columns. 
            # `diagnosis_doctorcategorypercentage` also exists. 
            # Populating the direct columns is definitely required. Populating the join table is a "bonus" for future proofing but might be redundant.
            # I will stick to populating the columns in `diagnosis_doctor` as requested: "ensure they all have there respsective incentive percentage in the new model".
            
        print(f"Migrated {len(doctors)} doctors.")

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
