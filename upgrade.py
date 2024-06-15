import sqlite3


conn = sqlite3.connect('main.db')
cursor = conn.cursor()

cursor.execute(f'''
    SELECT group_id
    FROM groups
''')
for group_id in cursor.fetchall():
    group_id = group_id[0]
    print(f"Updrading group {group_id} datas")
    cursor.execute(f"ALTER TABLE group_{group_id} ADD COLUMN loan INTEGER DEFAULT 0")
conn.commit()
print("Done")

conn.close()
