from fastapi import Depends, HTTPException, Request, status
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Generator, Optional
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.role import Role, Permission

def get_token_from_request(request: Request) -> Optional[str]:
    """Extrae el token JWT tanto de la cabecera Authorization como de las cookies."""
    # 1. Intentar cabecera Authorization (Bearer Token)
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token and token.lower() not in ("null", "undefined"):
            return token
        # Si el token no es válido en la cabecera, caer de nuevo a cookie
        
    # 2. Intentar Cookies de sesión (Útil para navegación Jinja2)
    return request.cookies.get("access_token")

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Obtiene el usuario autenticado decodificando el token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión. Por favor inicie sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = get_token_from_request(request)
    if not token:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id_str is None or token_type != "access":
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifica si el usuario autenticado está activo en la plataforma."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Su cuenta de usuario está desactivada. Contacte al administrador."
        )
    return current_user

class PermissionChecker:
    """Verificador dinámico de permisos RBAC para dependencias de FastAPI."""
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(
        self,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # El Administrador tiene acceso absoluto a todas las operaciones
        if current_user.role.name == "Administrador":
            return current_user
            
        # Extraer códigos de permisos que el rol del usuario posee
        user_permissions = [p.code for p in current_user.role.permissions]
        
        if self.required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente. Requiere el permiso: {self.required_permission}"
            )
            
        return current_user
