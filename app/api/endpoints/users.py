import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile, File
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.user import UserResponse, UserCreate, UserUpdate, NaturaManagersUpdate
from app.models.user import User
from app.models.role import Role
from app.models.folder_access import FolderAccess
from app.models.area import Area
from app.services.natura_access import is_natura_manager
from app.api.deps import get_current_active_user, PermissionChecker
from app.core.security import get_password_hash
from app.services.audit_service import audit_service
from datetime import datetime
from app.core.config import settings

router = APIRouter()


def is_natura_account(user_or_email) -> bool:
    if hasattr(user_or_email, "is_natura_user") and user_or_email.is_natura_user:
        return True
    email = user_or_email.email if hasattr(user_or_email, "email") else user_or_email
    return bool(email and email.lower().strip().endswith("@natura.cl"))


def is_natura_manager_actor(db: Session, actor: User) -> bool:
    return is_natura_manager(db, actor)


def ensure_supervisor_scope(db: Session, actor: User, target: User | None = None, email: str | None = None) -> None:
    """Supervisores y responsables administran exclusivamente cuentas Natura."""
    if is_natura_manager_actor(db, actor):
        return
    if actor.role.name != "Supervisor":
        return
    if target is not None and not is_natura_account(target):
        raise HTTPException(status_code=403, detail="El supervisor solo puede administrar usuarios de Natura.")
    if email is not None and not is_natura_account(email):
        raise HTTPException(status_code=400, detail="Los usuarios creados por un supervisor deben usar correo @natura.cl.")


def ensure_natura_manager_fields(db: Session, actor: User, role: Role, area_id: int | None) -> None:
    if not is_natura_manager_actor(db, actor):
        return
    if role.name != "Usuario":
        raise HTTPException(status_code=403, detail="Los responsables Natura solo pueden crear usuarios con rol Usuario.")
    sales_area = db.query(Area).filter(Area.name == "Ventas").first()
    if not sales_area or area_id != sales_area.id:
        raise HTTPException(status_code=400, detail="Los usuarios Natura deben pertenecer al área Ventas.")


def require_user_management(permission: str):
    def checker(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role.name == "Administrador" or permission in {p.code for p in current_user.role.permissions}:
            return current_user
        if is_natura_manager_actor(db, current_user) and permission in {"users:create", "users:read", "users:update", "users:delete"}:
            return current_user
        raise HTTPException(status_code=403, detail=f"Permiso insuficiente. Requiere el permiso: {permission}")
    return checker


def get_natura_folder_names(db: Session) -> list[str]:
    return [
        name for (name,) in db.query(FolderAccess.folder_name)
        .filter(FolderAccess.folder_name.like("Natura / %"))
        .distinct()
        .all()
    ]


def get_natura_manager_ids(db: Session, folder_names: list[str]) -> set[int]:
    if not folder_names:
        return set()
    required_count = len(folder_names)
    candidates = db.query(FolderAccess).filter(
        FolderAccess.folder_name.in_(folder_names),
        FolderAccess.can_read.is_(True),
        FolderAccess.can_write.is_(True),
    ).all()
    coverage: dict[int, set[str]] = {}
    for permission in candidates:
        coverage.setdefault(permission.user_id, set()).add(permission.folder_name)
    return {user_id for user_id, folders in coverage.items() if len(folders) == required_count}


def grant_natura_folder_access(db: Session, user_id: int, folder_names: list[str]) -> None:
    existing = {
        permission.folder_name: permission
        for permission in db.query(FolderAccess).filter(
            FolderAccess.user_id == user_id,
            FolderAccess.folder_name.in_(folder_names),
        ).all()
    }
    for folder_name in folder_names:
        permission = existing.get(folder_name)
        if permission:
            permission.can_read = True
            permission.can_write = True
        else:
            db.add(FolderAccess(
                user_id=user_id,
                folder_name=folder_name,
                can_read=True,
                can_write=True,
            ))

@router.get("/birthdays", response_model=List[UserResponse])
def get_birthdays(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtiene los usuarios que cumplen años en el mes actual."""
    users = db.query(User).filter(User.is_active == True, User.birth_date.isnot(None)).all()
    current_month = datetime.now().month
    birthdays = [u for u in users if u.birth_date.month == current_month]
    return birthdays

@router.get("", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management("users:read"))
):
    """Obtiene la lista completa de usuarios corporativos, filtrada por área si no es admin."""
    if current_user.role.name == "Supervisor" or is_natura_manager_actor(db, current_user):
        return db.query(User).filter(or_(User.is_natura_user.is_(True), func.lower(User.email).like("%@natura.cl"))).all()
    if current_user.role.name != "Administrador":
        return db.query(User).filter(User.area_id == current_user.area_id).all()
    return db.query(User).all()


@router.get("/me", response_model=UserResponse)
def get_user_me(current_user: User = Depends(get_current_active_user)):
    """Retorna la información del usuario en sesión."""
    return current_user


@router.get("/list-minimal", response_model=List[UserResponse])
def get_users_minimal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtiene la lista minimalista de todos los colaboradores activos para asignación, filtrado por área si no es admin."""
    if current_user.role.name not in ["Administrador", "Supervisor"]:
        return db.query(User).filter(User.is_active == True, User.area_id == current_user.area_id).all()
    return db.query(User).filter(User.is_active == True).all()


@router.get("/natura-managers")
def get_natura_managers(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("roles:manage")),
):
    folder_names = get_natura_folder_names(db)
    manager_ids = get_natura_manager_ids(db, folder_names)
    managers = db.query(User).filter(User.id.in_(manager_ids)).all() if manager_ids else []
    return {
        "manager_ids": sorted(manager_ids),
        "folder_count": len(folder_names),
        "managers": [{"id": user.id, "full_name": user.full_name, "email": user.email} for user in managers],
    }


@router.put("/natura-managers")
def update_natura_managers(
    payload: NaturaManagersUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("roles:manage")),
):
    manager_ids = list(dict.fromkeys(payload.manager_ids))
    if len(manager_ids) > 2:
        raise HTTPException(status_code=400, detail="Puedes asignar como máximo dos responsables Natura.")

    folder_names = get_natura_folder_names(db)
    if not folder_names:
        raise HTTPException(status_code=400, detail="No hay carpetas personales de Natura disponibles.")

    selected_users = db.query(User).filter(User.id.in_(manager_ids), User.is_active.is_(True)).all()
    if len(selected_users) != len(manager_ids):
        raise HTTPException(status_code=400, detail="Selecciona usuarios activos y válidos.")
    if any(user.email.lower().endswith("@natura.cl") for user in selected_users):
        raise HTTPException(status_code=400, detail="Los responsables Natura deben ser cuentas corporativas internas.")
    if any(
        user.role.name != "Administrador"
        and "documents:read" not in {permission.code for permission in user.role.permissions}
        for user in selected_users
    ):
        raise HTTPException(status_code=400, detail="Los responsables deben tener acceso al gestor documental.")

    previous_manager_ids = get_natura_manager_ids(db, folder_names)
    for user_id in previous_manager_ids - set(manager_ids):
        db.query(FolderAccess).filter(
            FolderAccess.user_id == user_id,
            FolderAccess.folder_name.in_(folder_names),
        ).delete(synchronize_session=False)

    for user_id in manager_ids:
        grant_natura_folder_access(db, user_id, folder_names)

    db.commit()
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="natura_managers_update",
        ip_address=request.client.host if request.client else None,
        details=f"Actualizó responsables de Natura: {manager_ids}. Carpetas asignadas: {len(folder_names)}.",
    )
    return {"manager_ids": manager_ids, "folder_count": len(folder_names)}


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_user_management("users:create"))
):
    """Crea un nuevo usuario en la intranet corporativa."""
    # Verificar si el correo ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado en la plataforma."
        )

    ensure_supervisor_scope(db, admin_user, email=user_data.email)

    # Verificar si el rol existe
    role = db.query(Role).filter(Role.id == user_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol especificado no existe."
        )

    if admin_user.role.name == "Supervisor" and role.name != "Usuario":
        raise HTTPException(status_code=403, detail="Un supervisor solo puede crear usuarios con rol Usuario.")
    ensure_natura_manager_fields(db, admin_user, role, user_data.area_id)

    hashed_pw = get_password_hash(user_data.password)
    default_avatar = "/static/uploads/avatars/woman.png" if user_data.gender and user_data.gender.lower() == 'mujer' else "/static/uploads/avatars/man.png"
    
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_pw,
        full_name=user_data.full_name,
        role_id=user_data.role_id,
        area_id=user_data.area_id,
        is_natura_user=is_natura_manager_actor(db, admin_user),
        supervisor_id=user_data.supervisor_id,
        gender=user_data.gender,
        avatar_url=user_data.avatar_url or default_avatar,
        is_active=user_data.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Añadir permisos de carpeta si los hay
    if user_data.folder_permissions is not None:
        for perm in user_data.folder_permissions:
            new_perm = FolderAccess(
                user_id=db_user.id,
                folder_name=perm.folder_name,
                can_read=perm.can_read,
                can_write=perm.can_write
            )
            db.add(new_perm)
        db.commit()
        db.refresh(db_user)

    # Log de auditoría
    audit_service.log_action(
        db=db,
        user_id=admin_user.id,
        action="user_create",
        ip_address=request.client.host if request.client else None,
        details=f"Creó el usuario con ID {db_user.id} ({db_user.email}) con rol {role.name}."
    )

    return db_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    request: Request,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_user_management("users:update"))
):
    """Actualiza la información de un usuario específico."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    ensure_supervisor_scope(db, admin_user, target=user)

    # Si se actualiza el email, verificar unicidad
    if user_data.email and user_data.email != user.email:
        ensure_supervisor_scope(db, admin_user, email=user_data.email)
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="El correo electrónico ya está en uso.")
        user.email = user_data.email

    # Si se actualiza el rol
    if user_data.role_id is not None:
        role = db.query(Role).filter(Role.id == user_data.role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="El rol especificado no existe.")
        if admin_user.role.name == "Supervisor" and role.name != "Usuario":
            raise HTTPException(status_code=403, detail="Un supervisor solo puede mantener usuarios con rol Usuario.")
        ensure_natura_manager_fields(db, admin_user, role, user_data.area_id or user.area_id)
        user.role_id = user_data.role_id

    # Si se actualiza el área
    if user_data.area_id is not None:
        if is_natura_manager_actor(db, admin_user):
            sales_area = db.query(Area).filter(Area.name == "Ventas").first()
            if not sales_area or user_data.area_id != sales_area.id:
                raise HTTPException(status_code=400, detail="Los usuarios Natura deben pertenecer al área Ventas.")
        user.area_id = user_data.area_id

    # Actualizar campos comunes
    if user_data.full_name:
        user.full_name = user_data.full_name
    if user_data.supervisor_id is not None:
        user.supervisor_id = user_data.supervisor_id
    if user_data.gender:
        user.gender = user_data.gender
        # Si no tiene avatar o es uno autogenerado/predeterminado, lo actualizamos al cambiar género/nombre
        if not user.avatar_url or "avatar.iran.liara.run" in user.avatar_url or "default-avatar.png" in user.avatar_url or "api.dicebear.com" in user.avatar_url:
            user.avatar_url = "/static/uploads/avatars/woman.png" if user.gender and user.gender.lower() == 'mujer' else "/static/uploads/avatars/man.png"
            
    if user_data.avatar_url is not None:
        user.avatar_url = user_data.avatar_url
    if user_data.is_active is not None:
        # Si se desactiva un usuario, verificar que no sea el administrador actual
        if user_id == admin_user.id and not user_data.is_active:
            raise HTTPException(status_code=400, detail="No puede desactivar su propia cuenta de administrador.")
        user.is_active = user_data.is_active
    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)

    # Actualizar permisos de carpeta si vienen en la petición
    if user_data.folder_permissions is not None:
        # Eliminar permisos anteriores
        db.query(FolderAccess).filter(FolderAccess.user_id == user.id).delete()
        # Agregar los nuevos
        for perm in user_data.folder_permissions:
            new_perm = FolderAccess(
                user_id=user.id,
                folder_name=perm.folder_name,
                can_read=perm.can_read,
                can_write=perm.can_write
            )
            db.add(new_perm)

    db.commit()
    db.refresh(user)

    # Log de auditoría
    audit_service.log_action(
        db=db,
        user_id=admin_user.id,
        action="user_update",
        ip_address=request.client.host if request.client else None,
        details=f"Actualizó datos del usuario ID {user.id} ({user.email})."
    )

    return user


@router.post("/me/avatar")
def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Permite al usuario activo subir su propia foto de perfil."""
    # Sanitizar y validar que sea una imagen
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagen inválido. Solo se admiten archivos PNG, JPG, JPEG o WEBP."
        )

    # Carpeta física en disco
    avatar_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)

    # Guardar archivo con nombre único
    filename = f"avatar_user_{current_user.id}{ext}"
    file_path = os.path.join(avatar_dir, filename)

    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Guardar ruta relativa web
    relative_web_path = f"/static/uploads/avatars/{filename}"
    current_user.avatar_url = relative_web_path
    db.commit()

    # Log de auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="user_avatar_update",
        ip_address=request.client.host if request.client else None,
        details="Actualizó su foto de perfil corporativa."
    )

    return {"avatar_url": relative_web_path}


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_user_management("users:delete"))
):
    """Elimina un usuario de forma permanente de la intranet."""
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta de administrador en sesión."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    ensure_supervisor_scope(db, admin_user, target=user)

    # Eliminar/Desvincular dependencias no automatizadas por cascade en SQLAlchemy/DB
    from app.models.task import Task
    from app.models.note import Note
    
    # 1. Eliminar tareas creadas por el usuario
    db.query(Task).filter(Task.created_by_id == user_id).delete()
    
    # 2. Desvincular tareas asignadas al usuario (poner asignado en NULL)
    db.query(Task).filter(Task.assigned_to_user_id == user_id).update({Task.assigned_to_user_id: None})
    
    # 3. Eliminar notas creadas por el usuario
    db.query(Note).filter(Note.created_by_id == user_id).delete()
    
    # Proceder a eliminar al usuario
    db.delete(user)
    db.commit()

    # Log de auditoría
    audit_service.log_action(
        db=db,
        user_id=admin_user.id,
        action="user_delete",
        ip_address=request.client.host if request.client else None,
        details=f"Eliminó por completo al usuario {user.full_name} ({user.email})."
    )

    return {"detail": f"Usuario {user.full_name} eliminado correctamente."}

