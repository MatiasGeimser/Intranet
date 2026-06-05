import sqlite3

conn = sqlite3.connect('intranet.db')
cur = conn.cursor()

print("=== TABLAS ===")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(tables)

print("\n=== USUARIOS ===")
cur.execute("SELECT id, email, full_name, role_id, is_active FROM users")
for row in cur.fetchall():
    print(row)

print("\n=== ROLES ===")
cur.execute("SELECT id, name FROM roles")
for row in cur.fetchall():
    print(row)

print("\n=== ¿TABLA TASKS EXISTE? ===")
print("tasks" in tables)

conn.close()
