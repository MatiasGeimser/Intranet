from sqlalchemy.orm import Session
from app.core.database import Base, engine
from app.models.role import Role, Permission
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings

def seed_database(db: Session):
    """Inicializa el esquema de la base de datos y siembra datos iniciales."""
    # 1. Crear tablas si no existen
    Base.metadata.create_all(bind=engine)

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
        {"code": "news:manage", "description": "Gestionar artículos y comentarios de noticias"}
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

    # 5. Crear Administrador Inicial si no existe ningún usuario
    admin_user = db.query(User).filter(User.email == settings.INITIAL_ADMIN_EMAIL).first()
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
