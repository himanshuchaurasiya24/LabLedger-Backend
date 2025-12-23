import sqlite3
import os

DB_PATH = 'db.sqlite3'

def verify():
    if not os.path.exists(DB_PATH):
        print("Error: DB not found")
        return

    conn = sqlite3.connect(DB_PATH)
    curr = conn.cursor()
    
    print("=== Verification of Migrated Data ===")
    
    # 1. Users
    curr.execute("SELECT count(*) FROM authentication_staffaccount")
    user_count = curr.fetchone()[0]
    print(f"Users Count: {user_count} (Expected ~4)")
    
    # Check one user
    curr.execute("SELECT username, center_detail_id FROM authentication_staffaccount LIMIT 1")
    user = curr.fetchone()
    print(f"Sample User: {user}")

    # 2. Centers
    curr.execute("SELECT count(*) FROM center_detail_centerdetail")
    center_count = curr.fetchone()[0]
    print(f"Centers Count: {center_count} (Expected ~1)")
    
    # 3. Categories
    curr.execute("SELECT name FROM diagnosis_diagnosiscategory")
    categories = [r[0] for r in curr.fetchall()]
    print(f"Categories: {categories}")
    expected_cats = ['Ultrasound', 'Pathology', 'ECG', 'X-Ray', 'Franchise Lab']
    missing = set(expected_cats) - set(categories)
    if missing:
        print(f"ERROR: Missing categories: {missing}")
    else:
        print("All categories present.")

    # 4. Doctors
    curr.execute("SELECT count(*) FROM diagnosis_doctor")
    doc_count = curr.fetchone()[0]
    print(f"Doctors Count: {doc_count} (Expected ~71)")
    
    # Check Name Formatting & Incentives
    print("\nSample Doctors:")
    curr.execute("SELECT first_name, last_name, ultrasound_percentage, center_detail_id FROM diagnosis_doctor LIMIT 5")
    for doc in curr.fetchall():
        print(f"  Name: '{doc[0]}' '{doc[1]}' | US: {doc[2]}% | CenterID: {doc[3]}")
        
    conn.close()

if __name__ == "__main__":
    verify()
