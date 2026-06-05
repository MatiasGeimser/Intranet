import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.models.user import User
from app.models.role import Role
from app.api.deps import get_current_active_user, PermissionChecker
from app.core.security import get_password_hash
from app.services.audit_service import audit_service
from app.core.config import settings

router = APIRouter()

@router.get("", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("users:read"))
):
    """Obtiene la lista completa de usuarios corporativos, filtrada por área si no es admin."""
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
    if current_user.role.name != "Administrador":
        return db.query(User).filter(User.is_active == True, User.area_id == current_user.area_id).all()
    return db.query(User).filter(User.is_active == True).all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(PermissionChecker("users:create"))
):
    """Crea un nuevo usuario en la intranet corporativa."""
    # Verificar si el correo ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado en la plataforma."
        )

    # Verificar si el rol existe
    role = db.query(Role).filter(Role.id == user_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol especificado no existe."
        )

    hashed_pw = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_pw,
        full_name=user_data.full_name,
        role_id=user_data.role_id,
        area_id=user_data.area_id,
        avatar_url=user_data.avatar_url or "/static/images/default-avatar.png",
        is_active=user_data.is_active
    )
    db.add(db_user)
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
    admin_user: User = Depends(PermissionChecker("users:update"))
):
    """Actualiza la información de un usuario específico."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # Si se actualiza el email, verificar unicidad
    if user_data.email and user_data.email != user.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="El correo electrónico ya está en uso.")
        user.email = user_data.email

    # Si se actualiza el rol
    if user_data.role_id is not None:
        role = db.query(Role).filter(Role.id == user_data.role_id).first()
        if not role:
            raise HTTPException(status_code=400, detail="El rol especificado no existe.")
        user.role_id = user_data.role_id

    # Si se actualiza el área
    if user_data.area_id is not None:
        user.area_id = user_data.area_id

    # Actualizar campos comunes
    if user_data.full_name:
        user.full_name = user_data.full_name
    if user_data.avatar_url is not None:
        user.avatar_url = user_data.avatar_url
    if user_data.is_active is not None:
        # Si se desactiva un usuario, verificar que no sea el administrador actual
        if user_id == admin_user.id and not user_data.is_active:
            raise HTTPException(status_code=400, detail="No puede desactivar su propia cuenta de administrador.")
        user.is_active = user_data.is_active
    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)

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
