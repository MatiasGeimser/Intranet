from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from app.models.user import User
from app.models.session import Session as UserSession
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, verify_token
from app.services.audit_service import audit_service
from app.core.config import settings

class AuthService:
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Autentica a un usuario y verifica si está activo."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_user_session(
        db: Session,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, str]:
        """Crea tokens de acceso y refresco, y guarda la sesión en la base de datos."""
        access_token = create_access_token(subject=user_id)
        refresh_token = create_refresh_token(subject=user_id)
        
        # Guardar en base de datos para control de sesiones activas
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session_entry = UserSession(
            user_id=user_id,
            session_token=refresh_token,  # Guardamos el token de refresco como identificador de sesión
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        db.add(session_entry)
        db.commit()
        
        return access_token, refresh_token

    @staticmethod
    def refresh_user_session(
        db: Session,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, str]:
        """Renueva la sesión verificando el token de refresco en la base de datos."""
        user_id_str = verify_token(refresh_token, token_type="refresh")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de refresco inválido o expirado.")
        
        user_id = int(user_id_str)
        # Buscar la sesión activa en BD
        session = db.query(UserSession).filter(UserSession.session_token == refresh_token).first()
        if not session or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            if session:
                db.delete(session)
                db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión expirada o no encontrada.")
            
        # Generar nuevos tokens (Rotación)
        new_access_token = create_access_token(subject=user_id)
        new_refresh_token = create_refresh_token(subject=user_id)
        
        # Actualizar sesión en la base de datos
        session.session_token = new_refresh_token
        session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session.ip_address = ip_address
        session.user_agent = user_agent
        db.commit()
        
        return new_access_token, new_refresh_token

    @staticmethod
    def terminate_session(db: Session, refresh_token: str):
        """Termina una sesión activa eliminándola de la base de datos (Logout)."""
        session = db.query(UserSession).filter(UserSession.session_token == refresh_token).first()
        if session:
            db.delete(session)
            db.commit()

auth_service = AuthService()
