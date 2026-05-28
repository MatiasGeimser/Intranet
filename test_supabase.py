import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar las variables de entorno desde .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

print("========================================")
print(f"Probando conexión a: {DATABASE_URL}")
print("========================================")

try:
    # 1. Probar conexión
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    print("[OK] Conexion a Supabase establecida correctamente.\n")

    # 2. Consultar las tablas directamente
    from app.models.user import User
    from app.models.role import Role

    users = db.query(User).all()
    roles = db.query(Role).all()

    print(f"[OK] Se encontraron {len(roles)} roles en la base de datos.")
    for r in roles:
        print(f"   - Rol: {r.name} (ID: {r.id})")
        
    print(f"\n[OK] Se encontraron {len(users)} usuarios en la base de datos.")
    for u in users:
        print(f"   - Usuario: {u.full_name} | Email: {u.email} | Activo: {u.is_active}")

    if len(users) > 0:
        print("\n[EXITO] La base de datos se ha sembrado correctamente.")
        print(f"Puedes iniciar sesion en tu Vercel con el correo: {users[0].email}")
    else:
        print("\n[AVISO] Las tablas existen pero no hay usuarios. Asegurate de haber entrado a la web en Vercel para que se active la siembra inicial de la base de datos.")

    db.close()

except Exception as e:
    print("[ERROR] ERROR AL CONECTAR CON SUPABASE")
    print("Detalles del error:")
    print(e)
