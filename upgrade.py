import sqlite3


conn = sqlite3.connect('main.db')
cursor = conn.cursor()

cursor.execute("""SELECT name FROM sqlite_master
    WHERE type='table';""")

for group in cursor.fetchall():
    group = group[0]
    if group == "groups":
        cursor.execute("DROP TABLE groups")
        continue
    print(f"Updrading group {group.split('_')[1]} datas")
    cursor.execute(f'''ALTER TABLE {group} ADD COLUMN hand TEXT DEFAULT ""''')
conn.commit()
print("Done")

conn.close()
