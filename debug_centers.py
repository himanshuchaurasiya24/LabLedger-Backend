import sqlite3

OLD_DB = 'olddb.sqlite3'
conn = sqlite3.connect(OLD_DB)
curr = conn.cursor()

print("=== Checking Center Tables ===")
curr.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in curr.fetchall()]
for t in tables:
    if 'center' in t.lower():
        print(f"Table: {t}")
        curr.execute(f"SELECT COUNT(*) FROM {t}")
        count = curr.fetchone()[0]
        print(f"  Rows: {count}")
        if count > 0:
            curr.execute(f"SELECT * FROM {t} LIMIT 1")
            print(f"  Sample: {curr.fetchone()}")
            # Show columns
            curr.execute(f"PRAGMA table_info({t})")
            cols = [c[1] for c in curr.fetchall()]
            print(f"  Columns: {cols}")

print("\n=== Checking Users ===")
curr.execute("SELECT id, username FROM authentication_staffaccount LIMIT 5")
users = curr.fetchall()
print(f"Users found (id, username): {users}")

conn.close()
