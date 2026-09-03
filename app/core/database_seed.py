import unicodedata
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
from app.models.admin_chat import AdminChatAttachment, AdminChatMessage  # noqa: F401
from app.models.admin_chat_presence import AdminChatPresence  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.folder_access import FolderAccess  # noqa: F401
from app.models.task import TaskComment  # noqa: F401
from app.models.delivery_record import DeliveryRecord  # noqa: F401


NATURA_MONTHS = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)


def migrate_natura_document_structure(db: Session) -> None:
    """Normaliza las rutas Natura y crea la rama compartida de Personas Natura."""
    for permission in db.query(FolderAccess).all():
        parts = [part.strip() for part in permission.folder_name.split(" / ")]
        if len(parts) >= 3 and parts[0] == "Natura" and parts[1] not in {"CBE", "Personas Natura"}:
            permission.folder_name = "Natura / CBE / " + " / ".join(parts[1:])

    for document in db.query(Document).all():
        parts = [part.strip() for part in document.folder.split(" / ")]
        if len(parts) >= 3 and parts[0] == "Natura" and parts[1] not in {"CBE", "Personas Natura"}:
            document.folder = "Natura / CBE / " + " / ".join(parts[1:])

    shared_folders = ["Natura / Personas Natura / Contratos vigentes"]
    shared_folders.extend(
        f"Natura / Personas Natura / Boletas de honorarios / {month}"
        for month in NATURA_MONTHS
    )
    shared_folders.extend(
        f"Natura / Personas Natura / Comprobante de pago / {month}"
        for month in NATURA_MONTHS
    )
    cbe_folders = [
        name for (name,) in db.query(FolderAccess.folder_name)
        .filter(FolderAccess.folder_name.like("Natura / CBE / %"))
        .distinct()
        .all()
    ]
    manager_ids = set()
    if cbe_folders:
        candidates = db.query(FolderAccess).filter(
            FolderAccess.folder_name.in_(cbe_folders),
            FolderAccess.can_read.is_(True),
            FolderAccess.can_write.is_(True),
        ).all()
        coverage = {}
        for permission in candidates:
            coverage.setdefault(permission.user_id, set()).add(permission.folder_name)
        manager_ids = {
            user_id for user_id, folders in coverage.items()
            if len(folders) == len(cbe_folders)
        }
    natura_users = db.query(User).filter(
        User.is_active.is_(True),
        User.email.ilike("%@natura.cl"),
    ).all()
    shared_access = [(user.id, False) for user in natura_users]
    shared_access.extend((user_id, True) for user_id in manager_ids if user_id not in {user.id for user in natura_users})
    for user_id, can_write in shared_access:
        existing = {
            permission.folder_name: permission
            for permission in db.query(FolderAccess).filter(FolderAccess.user_id == user_id).all()
        }
        for folder_name in shared_folders:
            permission = existing.get(folder_name)
            if permission:
                permission.can_read = True
                permission.can_write = permission.can_write or can_write
            else:
                db.add(FolderAccess(user_id=user_id, folder_name=folder_name, can_read=True, can_write=can_write))

    db.commit()

def seed_database(db: Session):
    """Inicializa el esquema de la base de datos y siembra datos iniciales."""
    # 1. Crear tablas si no existen
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import text

    # Estado operativo de las líneas contratadas. Las existentes permanecen activas.
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE phone_numbers ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"))
        else:
            db.execute(text("ALTER TABLE phone_numbers ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (phone_numbers.is_active): {e} ======")

    # Vincula las actas al Directorio Corporativo, no a cuentas de acceso.
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE delivery_records ADD COLUMN IF NOT EXISTS collaborator_id INTEGER REFERENCES collaborators(id) ON DELETE SET NULL"))
        else:
            existing_columns = {column["name"] for column in inspect(engine).get_columns("delivery_records")}
            if "collaborator_id" not in existing_columns:
                db.execute(text("ALTER TABLE delivery_records ADD COLUMN collaborator_id INTEGER REFERENCES collaborators(id) ON DELETE SET NULL"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (delivery_records.collaborator_id): {e} ======")

    # Gestión de puertos: asignación física a puesto y habilitación administrativa.
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE switch_interfaces ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE"))
            db.execute(text("ALTER TABLE switch_interfaces ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL"))
        else:
            existing_columns = {column["name"] for column in inspect(engine).get_columns("switch_interfaces")}
            if "is_enabled" not in existing_columns:
                db.execute(text("ALTER TABLE switch_interfaces ADD COLUMN is_enabled BOOLEAN NOT NULL DEFAULT 1"))
            if "workspace_id" not in existing_columns:
                db.execute(text("ALTER TABLE switch_interfaces ADD COLUMN workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (switch_interfaces): {e} ======")

    # Mensajes directos del chat: nullable para conservar el canal institucional existente.
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE admin_chat_messages ADD COLUMN IF NOT EXISTS recipient_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
        else:
            db.execute(text("ALTER TABLE admin_chat_messages ADD COLUMN recipient_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (admin_chat_messages.recipient_id): {e} ======")

    # Los eventos son privados por defecto y solo se muestran a todos cuando su creador lo indica.
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS is_shared BOOLEAN NOT NULL DEFAULT FALSE"))
        else:
            db.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS is_shared BOOLEAN NOT NULL DEFAULT 0"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (events.is_shared): {e} ======")

    try:
        migrate_natura_document_structure(db)
        print("====== ESTRUCTURA NATURA NORMALIZADA Y CARPETAS COMPARTIDAS VERIFICADAS ======")
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (estructura Natura): {e} ======")

    # Migración dinámica de la columna note_id en la tabla tasks
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

    # Migración dinámica de columnas para tareas diarias en la tabla tasks
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS daily_task_config_id INTEGER REFERENCES daily_task_configs(id) ON DELETE SET NULL"))
            db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITHOUT TIME ZONE"))
        else:
            db.execute(text("ALTER TABLE tasks ADD COLUMN daily_task_config_id INTEGER REFERENCES daily_task_configs(id) ON DELETE SET NULL"))
            db.execute(text("ALTER TABLE tasks ADD COLUMN completed_at DATETIME"))
        db.commit()
        print("====== COLUMNAS daily_task_config_id Y completed_at VERIFICADAS/AÑADIDAS EN tasks ======")
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (daily_task_config_id/completed_at): {e} ======")

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

    # Migración de estados antiguos de tareas a los estados del tablero Scrum (todo, done)
    try:
        db.execute(text("UPDATE tasks SET status = 'todo' WHERE status = 'pending'"))
        db.execute(text("UPDATE tasks SET status = 'done' WHERE status = 'completed'"))
        db.commit()
        print("====== ESTADOS DE TAREAS ACTUALIZADOS (todo, done) ======")
    except Exception as e:
        db.rollback()
        print(f"====== AVISO ACTUALIZACIÓN ESTADOS DE TAREAS: {e} ======")

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

    # Permiso especial limitado al gestor documental.
    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_natura_user BOOLEAN NOT NULL DEFAULT FALSE"))
        else:
            db.execute(text("ALTER TABLE users ADD COLUMN is_natura_user BOOLEAN NOT NULL DEFAULT 0"))
        db.commit()
        db.execute(text("UPDATE users SET is_natura_user = TRUE WHERE lower(email) LIKE '%@natura.cl'"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (users.is_natura_user): {e} ======")

    try:
        if engine.name == "postgresql":
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_document_admin BOOLEAN NOT NULL DEFAULT FALSE"))
        else:
            db.execute(text("ALTER TABLE users ADD COLUMN is_document_admin BOOLEAN NOT NULL DEFAULT 0"))
        db.commit()
        for user in db.query(User).filter(User.is_active.is_(True)).all():
            normalized_name = "".join(
                char for char in unicodedata.normalize("NFKD", user.full_name or "").lower()
                if not unicodedata.combining(char)
            )
            if "catalina" in normalized_name and "munoz" in normalized_name:
                user.is_document_admin = True
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"====== AVISO MIGRACIÓN (users.is_document_admin): {e} ======")

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
        {"code": "credentials:read", "description": "Ver credenciales en el gestor de contraseñas"},
        {"code": "events:manage", "description": "Gestionar eventos en el calendario corporativo"},
        {"code": "events:read", "description": "Ver eventos en el calendario corporativo"},
        {"code": "documents:manage", "description": "Gestionar archivos en el gestor documental"},
        {"code": "documents:read", "description": "Ver y descargar archivos en el gestor documental"},
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
        db_permissions["users:create"],
        db_permissions["users:read"],
        db_permissions["users:update"],
        db_permissions["users:delete"],
        db_permissions["credentials:manage"],
        db_permissions["credentials:read"],
        db_permissions["events:manage"],
        db_permissions["events:read"],
        db_permissions["documents:manage"],
        db_permissions["documents:read"],
        db_permissions["news:manage"]
    ]
    supervisor_role.permissions = supervisor_permissions

    # Usuario estándar tiene permisos en los módulos operativos básicos de solo lectura (observar)
    usuario_role = db_roles["Usuario"]
    usuario_permissions = [
        db_permissions["credentials:read"],
        db_permissions["events:read"],
        db_permissions["documents:read"]
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
