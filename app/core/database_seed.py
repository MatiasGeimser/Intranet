from sqlalchemy.orm import Session
from app.core.database import Base, engine
from app.models.role import Role, Permission
from app.models.user import User
from app.models.it_asset import ITAsset  # noqa: F401 — ensures table is created
from app.models.vlan import VLAN  # noqa: F401 — ensures table is created
from app.models.network_devices import SwitchDevice, SwitchInterface  # noqa: F401
from app.models.phone_number import PhoneNumber  # noqa: F401 — ensures table is created
from app.models.note import Note  # noqa: F401 — ensures table is created
from app.models.area import Area  # noqa: F401 — ensures table is created
from app.core.security import get_password_hash
from app.core.config import settings

def seed_database(db: Session):
    """Inicializa el esquema de la base de datos y siembra datos iniciales."""
    # 1. Crear tablas si no existen
    Base.metadata.create_all(bind=engine)

    # Migración dinámica de la columna note_id en la tabla tasks
    from sqlalchemy import text
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS note_id INTEGER REFERENCES notes(id) ON DELETE CASCADE"))
        else:
            db.execute(text("ALTER TABLE tasks ADD COLUMN note_id INTEGER REFERENCES notes(id) ON DELETE CASCADE"))
        db.commit()
        print("====== COLUMNA note_id VERIFICADA/AÑADIDA EN LA TABLA tasks ======")
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (note_id): {e} ======")

    # Migración dinámica de la columna updated_at en la tabla documents
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE"))
        else:
            db.execute(text("ALTER TABLE documents ADD COLUMN updated_at TIMESTAMP"))
        db.commit()
        print("====== COLUMNA updated_at VERIFICADA/AÑADIDA EN LA TABLA documents ======")
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (documents.updated_at): {e} ======")

    # Se añade la siembra de áreas de trabajo
    areas_list = [
        {"name": "Administración", "description": "Gestión general y administración"},
        {"name": "Tecnología", "description": "Departamento de sistemas y desarrollo"},
        {"name": "Soporte", "description": "Mesa de ayuda y soporte técnico"},
        {"name": "Finanzas", "description": "Contabilidad y finanzas"},
        {"name": "Ventas", "description": "Comercialización y ventas"}
    ]

    db_areas = {}
    for area_data in areas_list:
        db_area = db.query(Area).filter(Area.name == area_data["name"]).first()
        if not db_area:
            db_area = Area(name=area_data["name"], description=area_data["description"])
            db.add(db_area)
            db.flush()
        db_areas[area_data["name"]] = db_area
    db.commit()

    # Migración de llaves foráneas para area_id
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS area_id INTEGER REFERENCES areas(id) ON DELETE SET NULL"))
        else:
            db.execute(text("ALTER TABLE users ADD COLUMN area_id INTEGER REFERENCES areas(id) ON DELETE SET NULL"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (users.area_id): {e} ======")

    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE notes ADD COLUMN IF NOT EXISTS area_id INTEGER REFERENCES areas(id) ON DELETE CASCADE"))
        else:
            db.execute(text("ALTER TABLE notes ADD COLUMN area_id INTEGER REFERENCES areas(id) ON DELETE CASCADE"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (notes.area_id): {e} ======")

    # Asignar área por defecto ("Administración") a usuarios y notas existentes que no tengan asignado área
    try:
        admin_area = db_areas["Administración"]
        db.execute(text(f"UPDATE users SET area_id = {admin_area.id} WHERE area_id IS NULL"))
        db.execute(text(f"UPDATE notes SET area_id = {admin_area.id} WHERE area_id IS NULL"))
        db.commit()
        print("====== MIGRACIÓN DE DATOS (area_id por defecto) APLICADA ======")
    except Exception as e:
        db.rollback()
        print(f"====== ERROR AL ACTUALIZAR ÁREAS POR DEFECTO: {e} ======")

    # 2. Definir permisos básicos
    permissions_list = [
        # Gestión de Usuarios
        {"code": "users:create", "description": "Crear nuevos usuarios"},
        {"code": "users:read", "description": "Ver lista y detalles de usuarios"},
        {"code": "users:update", "description": "Modificar información de usuarios"},
        {"code": "users:delete", "description": "Eliminar o desactivar usuarios"},
        
        # Gestión de Roles y Seguridad
        {"code": "roles:manage", "description": "Gestionar roles y permisos del sistema"},
        {"code": "audit:read", "description": "Ver registros de auditoría de ciberseguridad"},
        
        # Módulos Internos
        {"code": "credentials:manage", "description": "Gestionar credenciales en el gestor de contraseñas"},
        {"code": "events:manage", "description": "Gestionar eventos en el calendario corporativo"},
        {"code": "documents:manage", "description": "Gestionar archivos en el gestor documental"},
        {"code": "news:manage", "description": "Gestionar artículos y comentarios de noticias"},
        {"code": "it:manage", "description": "Gestionar el inventario de activos IT (Software, Hardware, Redes)"},
    ]

    db_permissions = {}
    for perm_data in permissions_list:
        db_perm = db.query(Permission).filter(Permission.code == perm_data["code"]).first()
        if not db_perm:
            db_perm = Permission(code=perm_data["code"], description=perm_data["description"])
            db.add(db_perm)
            db.flush()
        db_permissions[perm_data["code"]] = db_perm

    # 3. Definir Roles
    roles_list = [
        {"name": "Administrador", "description": "Acceso total, configuración global y auditoría"},
        {"name": "Supervisor", "description": "Acceso parcial a reportes, noticias y gestión de equipos"},
        {"name": "Usuario", "description": "Acceso limitado a sus propios módulos autorizados"}
    ]

    db_roles = {}
    for role_data in roles_list:
        db_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not db_role:
            db_role = Role(name=role_data["name"], description=role_data["description"])
            db.add(db_role)
            db.flush()
        db_roles[role_data["name"]] = db_role

    db.commit()

    # 4. Asignar permisos a roles
    # Administrador tiene todos los permisos
    admin_role = db_roles["Administrador"]
    admin_role.permissions = list(db_permissions.values())

    # Supervisor tiene permisos de lectura de usuarios y gestión de módulos
    supervisor_role = db_roles["Supervisor"]
    supervisor_permissions = [
        db_permissions["users:read"],
        db_permissions["credentials:manage"],
        db_permissions["events:manage"],
        db_permissions["documents:manage"],
        db_permissions["news:manage"]
    ]
    supervisor_role.permissions = supervisor_permissions

    # Usuario estándar tiene permisos en los módulos operativos básicos
    usuario_role = db_roles["Usuario"]
    usuario_permissions = [
        db_permissions["credentials:manage"],
        db_permissions["events:manage"],
        db_permissions["documents:manage"]
    ]
    usuario_role.permissions = usuario_permissions

    db.commit()

    # 5. Crear Administrador Inicial si no existe ningún administrador
    admin_user = db.query(User).filter(User.role_id == admin_role.id).first()
    if not admin_user:
        hashed_pw = get_password_hash(settings.INITIAL_ADMIN_PASSWORD)
        admin_user = User(
            email=settings.INITIAL_ADMIN_EMAIL,
            hashed_password=hashed_pw,
            full_name="Administrador de Sistemas",
            avatar_url="/static/images/default-avatar.png",
            role_id=admin_role.id,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
