import sqlite3

conn = sqlite3.connect('intranet.db')
cur = conn.cursor()

tables_to_check = ['users', 'sessions', 'audit_logs', 'roles', 'permissions', 'role_permissions']
for table in tables_to_check:
    print(f"\n=== COLUMNS FOR {table} ===")
    cur.execute(f"PRAGMA table_info({table})")
    for col in cur.fetchall():
        print(col)



conn.close()
