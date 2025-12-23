import sqlite3

db_path = 'db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables first
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
table_names = [t[0] for t in tables]


# Filter for relevant tables
relevant_keywords = ['authentication', 'user']
relevant_tables = [t for t in table_names if any(k in t.lower() for k in relevant_keywords)]

print(f"Inspecting {len(relevant_tables)} tables: {relevant_tables}")

for table in relevant_tables:
    print(f"\n--- {table} ---")
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

conn.close()
