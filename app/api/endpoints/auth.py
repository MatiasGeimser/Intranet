from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import LoginRequest, Token, PasswordChangeRequest, PasswordRecoveryRequest, PasswordResetRequest
from app.services.auth_service import auth_service
from app.services.audit_service import audit_service
from app.api.deps import get_current_active_user
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings

router = APIRouter()


def set_session_cookies(response: Response, request: Request, access_token: str, refresh_token: str) -> None:
    """Persiste la sesión y usa cookies seguras cuando la petición llega por HTTPS."""
    secure = request.url.scheme == "https"
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    cookie_options = {
        "httponly": True,
        "samesite": "lax",
        "secure": secure,
        "max_age": max_age,
        "expires": max_age,
        "path": "/",
    }
    response.set_cookie(key="access_token", value=access_token, **cookie_options)
    response.set_cookie(key="refresh_token", value=refresh_token, **cookie_options)

@router.post("/login", response_model=Token)
def login(
    response: Response,
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Autentica al usuario y guarda los tokens en cookies y respuesta JSON."""
    user = auth_service.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        # Registrar intento de acceso fallido
        audit_service.log_action(
            db=db,
            user_id=None,
            action="login_failed",
            ip_address=request.client.host if request.client else None,
            details=f"Intento de login fallido para el correo: {login_data.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Correo electrónico o contraseña incorrectos."
        )

    # Crear tokens y registrar la sesión en la base de datos
    access_token, refresh_token = auth_service.create_user_session(
        db=db,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    # Guardar en cookies para facilidad del frontend Jinja2
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False  # Cambiar a True en producción
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False  # Cambiar a True en producción
    )

    # Registrar inicio de sesión exitoso
    audit_service.log_action(
        db=db,
        user_id=user.id,
        action="login_success",
        ip_address=request.client.host if request.client else None,
        details=f"Inicio de sesión exitoso de {user.full_name}"
    )

    set_session_cookies(response, request, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """Termina la sesión actual borrando cookies y eliminando la sesión de la base de datos."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        # Registrar auditoría de logout antes de borrar la sesión
        user_id = None
        current_token = request.cookies.get("access_token")
        if current_token:
            from jose import jwt
            from app.core.config import settings
            try:
                payload = jwt.decode(current_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_id = int(payload.get("sub"))
            except Exception:
                pass
        
        audit_service.log_action(
            db=db,
            user_id=user_id,
            action="logout",
            ip_address=request.client.host if request.client else None,
            details="El usuario cerró sesión voluntariamente."
        )
        
        auth_service.terminate_session(db, refresh_token)

    # Borrar las cookies de sesión
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"detail": "Sesión cerrada correctamente."}


@router.post("/refresh", response_model=Token)
def refresh(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """Renueva los tokens JWT expirados usando la rotación de Refresh Tokens."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        # Si no viene en cookie, intentar cabecera Authorization
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header.split(" ")[1]

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de refresco."
        )

    # Renovar la sesión
    access_token, new_refresh_token = auth_service.refresh_user_session(
        db=db,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    # Actualizar cookies
    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax", secure=False)
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, samesite="lax", secure=False)

    set_session_cookies(response, request, access_token, new_refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/change-password")
def change_password(
    request: Request,
    pw_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Permite al usuario activo cambiar su contraseña actual."""
    from app.core.security import verify_password
    if not verify_password(pw_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual proporcionada es incorrecta."
        )

    current_user.hashed_password = get_password_hash(pw_data.new_password)
    db.commit()

    # Log de auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="password_change",
        ip_address=request.client.host if request.client else None,
        details="Cambió su contraseña de acceso correctamente."
    )

    return {"detail": "Contraseña modificada exitosamente."}


@router.post("/recover-password")
def recover_password(
    request: Request,
    rec_data: PasswordRecoveryRequest,
    db: Session = Depends(get_db)
):
    """Endpoint simulado para recuperación de contraseña (ciberseguridad)."""
    # Verificar si el usuario existe (evitando enumeración de usuarios en mensaje de error)
    user = db.query(User).filter(User.email == rec_data.email).first()
    
    if user:
        # Registrar auditoría
        audit_service.log_action(
            db=db,
            user_id=user.id,
            action="password_recovery_requested",
            ip_address=request.client.host if request.client else None,
            details=f"Solicitó un enlace de recuperación de contraseña."
        )
    
    # Retornar siempre un mensaje amigable genérico por seguridad (evita enumeración de usuarios)
    return {"detail": "Si el correo está registrado, recibirá un enlace seguro de recuperación en unos minutos."}
