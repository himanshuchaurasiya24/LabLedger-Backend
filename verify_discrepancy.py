import sqlite3
import os

db_path = 'olddb.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== 1. Structure of diagnosis_doctor Table ===")
cursor.execute("PRAGMA table_info(diagnosis_doctor)")
columns = cursor.fetchall()
incentive_cols = [col[1] for col in columns if 'percentage' in col[1]]
print(f"Found {len(incentive_cols)} incentive columns:")
for col in incentive_cols:
    print(f"  - {col}")

print("\n=== 2. Content of diagnosis_diagnosistype Table ===")
print("Distinct Categories found:")
cursor.execute("SELECT DISTINCT category FROM diagnosis_diagnosistype")
categories = cursor.fetchall()
for cat in categories:
    print(f"  - '{cat[0]}'")

print("\n=== 3. Searching for 'ECG' or 'X-Ray' in Diagnosis Names ===")
cursor.execute("SELECT name, category FROM diagnosis_diagnosistype WHERE name LIKE '%ECG%' OR name LIKE '%X-Ray%' OR name LIKE '%XRay%'")
matches = cursor.fetchall()
if matches:
    print(f"Found {len(matches)} diagnoses matching 'ECG' or 'X-Ray':")
    for match in matches:
        print(f"  - Name: {match[0]}, Category: {match[1]}")
else:
    print("No diagnoses found with 'ECG' or 'X-Ray' in the name.")

conn.close()
