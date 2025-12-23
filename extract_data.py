import sqlite3
import os

db_path = 'olddb.sqlite3'
output_file = 'extracted_data.txt'

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=== DIAGNOSIS CATEGORIES ===\n")
    try:
        cursor.execute("SELECT DISTINCT category FROM diagnosis_diagnosistype ORDER BY category")
        categories = cursor.fetchall()
        if not categories:
            f.write("No categories found.\n")
        for cat in categories:
            if cat[0]:
                f.write(f"- {cat[0]}\n")
            else:
                f.write(f"- [NULL]\n")
    except Exception as e:
        f.write(f"Error extracting categories: {e}\n")

    f.write("\n\n=== DOCTORS AND INCENTIVE PERCENTAGES ===\n")
    f.write(f"{'Doctor Name':<40} | {'Ultrasound':<10} | {'Pathology':<10} | {'ECG':<5} | {'X-Ray':<5} | {'Franchise':<10}\n")
    f.write("-" * 100 + "\n")
    
    try:
        cursor.execute("""
            SELECT first_name, last_name, 
                   ultrasound_percentage, pathology_percentage, ecg_percentage, xray_percentage, franchise_lab_percentage 
            FROM diagnosis_doctor 
            ORDER BY first_name, last_name
        """)
        doctors = cursor.fetchall()
        
        if not doctors:
            f.write("No doctors found.\n")
            
        for doc in doctors:
            first_name = doc[0] if doc[0] else ""
            last_name = doc[1] if doc[1] else ""
            full_name = f"{first_name} {last_name}".strip()
            
            us_perc = doc[2] if doc[2] is not None else 0
            path_perc = doc[3] if doc[3] is not None else 0
            ecg_perc = doc[4] if doc[4] is not None else 0
            xray_perc = doc[5] if doc[5] is not None else 0
            fran_perc = doc[6] if doc[6] is not None else 0
            
            f.write(f"{full_name:<40} | {us_perc:<10} | {path_perc:<10} | {ecg_perc:<5} | {xray_perc:<5} | {fran_perc:<10}\n")
            
    except Exception as e:
        f.write(f"Error extracting doctors: {e}\n")

conn.close()
print(f"Data extracted to {output_file}")
