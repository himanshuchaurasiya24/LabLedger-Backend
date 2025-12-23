import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("PRAGMA table_info(center_detail_centerdetail)")
print("Columns in db.sqlite3 center_detail_centerdetail:")
for col in cur.fetchall():
    print(col)
conn.close()
