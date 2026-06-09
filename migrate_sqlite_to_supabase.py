import os
import sys
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Asegurar que el path del proyecto esté en sys.path para poder importar los modelos de la app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.models.role import Role, Permission
from app.models.user import User
from app.models.session import Session
from app.models.audit import AuditLog

def parse_dt(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    val = val.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(val)
    except ValueError:
        return None

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def run_migration():
    print("========================================")
    print("INICIANDO MIGRACIÓN MÁS SEGURA (SQLITE -> SUPABASE)")
    print("========================================")

    # 1. Configurar conexiones
    sqlite_path = "intranet.db"
    supabase_url = os.getenv("DATABASE_URL")

    if not supabase_url:
        print("[ERROR] DATABASE_URL no encontrada en el archivo .env")
        return

    print(f"-> Origen (Local SQLite): {sqlite_path}")
    print(f"-> Destino (Supabase): {supabase_url}")

    # Abrir conexión a SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = dict_factory
    sqlite_cur = sqlite_conn.cursor()

    # Abrir sesión de SQLAlchemy para Supabase
    remote_engine = create_engine(supabase_url)
    RemoteSession = sessionmaker(bind=remote_engine)
    remote_db = RemoteSession()

    try:
        # --- MIGRAR PERMISOS ---
        print("\n--- Migrando Permisos ---")
        sqlite_cur.execute("SELECT * FROM permissions")
        local_permissions = sqlite_cur.fetchall()
        added_permissions = 0
        for lp in local_permissions:
            exists = remote_db.query(Permission).filter(
                (Permission.id == lp['id']) | (Permission.code == lp['code'])
            ).first()
            if not exists:
                new_perm = Permission(id=lp['id'], code=lp['code'], description=lp.get('description'))
                remote_db.add(new_perm)
                added_permissions += 1
        remote_db.commit()
        print(f"[OK] Permisos: {added_permissions} nuevos insertados.")

        # --- MIGRAR ROLES ---
        print("\n--- Migrando Roles ---")
        sqlite_cur.execute("SELECT * FROM roles")
        local_roles = sqlite_cur.fetchall()
        added_roles = 0
        for lr in local_roles:
            exists = remote_db.query(Role).filter(
                (Role.id == lr['id']) | (Role.name == lr['name'])
            ).first()
            if not exists:
                new_role = Role(id=lr['id'], name=lr['name'], description=lr.get('description'))
                remote_db.add(new_role)
                added_roles += 1
        remote_db.commit()
        print(f"[OK] Roles: {added_roles} nuevos insertados.")

        # --- MIGRAR ROLE_PERMISSIONS ---
        print("\n--- Migrando Relaciones Rol-Permiso ---")
        sqlite_cur.execute("SELECT role_id, permission_id FROM role_permissions")
        local_relations = sqlite_cur.fetchall()
        added_relations = 0
        for rel in local_relations:
            r_id = rel['role_id']
            p_id = rel['permission_id']
            exists = remote_db.execute(
                text("SELECT 1 FROM role_permissions WHERE role_id = :r_id AND permission_id = :p_id"),
                {"r_id": r_id, "p_id": p_id}
            ).fetchone()
            
            if not exists:
                remote_db.execute(
                    text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r_id, :p_id)"),
                    {"r_id": r_id, "p_id": p_id}
                )
                added_relations += 1
        remote_db.commit()
        print(f"[OK] Relaciones Rol-Permiso: {added_relations} nuevas insertadas.")

        # --- MIGRAR USUARIOS ---
        print("\n--- Migrando Usuarios ---")
        sqlite_cur.execute("SELECT * FROM users")
        local_users = sqlite_cur.fetchall()
        added_users = 0
        for lu in local_users:
            exists = remote_db.query(User).filter(
                (User.id == lu['id']) | (User.email == lu['email'])
            ).first()
            if not exists:
                new_user = User(
                    id=lu['id'],
                    email=lu['email'],
                    hashed_password=lu['hashed_password'],
                    full_name=lu['full_name'],
                    avatar_url=lu.get('avatar_url', '/static/images/default-avatar.png'),
                    role_id=lu['role_id'],
                    is_active=bool(lu['is_active']),
                    created_at=parse_dt(lu.get('created_at')),
                    updated_at=parse_dt(lu.get('updated_at')),
                    area_id=lu.get('area_id')  # Será None si no existe en SQLite
                )
                remote_db.add(new_user)
                added_users += 1
        remote_db.commit()
        print(f"[OK] Usuarios: {added_users} nuevos insertados.")

        # --- MIGRAR SESIONES ---
        print("\n--- Migrando Sesiones ---")
        sqlite_cur.execute("SELECT * FROM sessions")
        local_sessions = sqlite_cur.fetchall()
        added_sessions = 0
        for ls in local_sessions:
            exists = remote_db.query(Session).filter(
                (Session.id == ls['id']) | (Session.session_token == ls['session_token'])
            ).first()
            if not exists:
                new_session = Session(
                    id=ls['id'],
                    user_id=ls['user_id'],
                    session_token=ls['session_token'],
                    user_agent=ls.get('user_agent'),
                    ip_address=ls.get('ip_address'),
                    created_at=parse_dt(ls['created_at']),
                    expires_at=parse_dt(ls['expires_at'])
                )
                remote_db.add(new_session)
                added_sessions += 1
        remote_db.commit()
        print(f"[OK] Sesiones: {added_sessions} nuevas insertadas.")

        # --- MIGRAR AUDIT LOGS ---
        print("\n--- Migrando Logs de Auditoría ---")
        sqlite_cur.execute("SELECT * FROM audit_logs")
        local_logs = sqlite_cur.fetchall()
        added_logs = 0
        for ll in local_logs:
            log_dt = parse_dt(ll['created_at'])
            exists = remote_db.query(AuditLog).filter(
                (AuditLog.id == ll['id']) | 
                ((AuditLog.created_at == log_dt) & (AuditLog.action == ll['action']) & (AuditLog.user_id == ll['user_id']))
            ).first()
            if not exists:
                new_log = AuditLog(
                    id=ll['id'],
                    user_id=ll['user_id'],
                    action=ll['action'],
                    ip_address=ll.get('ip_address'),
                    details=ll.get('details'),
                    created_at=log_dt
                )
                remote_db.add(new_log)
                added_logs += 1
        remote_db.commit()
        print(f"[OK] Logs de Auditoría: {added_logs} nuevos insertados.")

        # --- REINICIAR SECUENCIAS EN POSTGRESQL ---
        print("\n--- Reiniciando Secuencias de Primary Keys en PostgreSQL ---")
        tables_to_reset = ["permissions", "roles", "users", "sessions", "audit_logs"]
        for table in tables_to_reset:
            try:
                max_id_res = remote_db.execute(text(f"SELECT max(id) FROM \"{table}\"")).fetchone()
                max_id = max_id_res[0] if max_id_res else None
                
                if max_id is not None:
                    seq_res = remote_db.execute(
                        text("SELECT pg_get_serial_sequence(:table_name, 'id')"), 
                        {"table_name": table}
                    ).fetchone()
                    seq_name = seq_res[0] if seq_res else None

                    if seq_name:
                        remote_db.execute(
                            text(f"SELECT setval(:seq_name, :max_id, true)"), 
                            {"seq_name": seq_name, "max_id": max_id}
                        )
                        print(f"[OK] Secuencia '{seq_name}' reiniciada al máximo id: {max_id}")
                    else:
                        print(f"[AVISO] No se encontró secuencia de serial para la tabla '{table}'")
            except Exception as seq_err:
                print(f"[ERROR] No se pudo reiniciar la secuencia para '{table}': {seq_err}")
        
        remote_db.commit()
        print("\n========================================")
        print("MIGRACIÓN FINALIZADA CON ÉXITO")
        print("========================================")

    except Exception as e:
        remote_db.rollback()
        print(f"\n[ERROR CRÍTICO] La migración falló: {e}")
    finally:
        sqlite_conn.close()
        remote_db.close()

if __name__ == "__main__":
    run_migration()
