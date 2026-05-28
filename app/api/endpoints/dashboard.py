from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import get_db
from app.models.user import User
from app.models.session import Session as UserSession
from app.models.document import Document
from app.models.credential import Credential
from app.models.event import Event
from app.models.audit import AuditLog
from app.api.deps import get_current_active_user
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    connected_users: int
    total_documents: int
    vault_credentials_count: int
    events_count: int
    recent_activity: List[dict]

@router.get("", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retorna los contadores de analítica y actividad reciente para el Dashboard Principal."""
    
    # 1. Usuarios totales y activos
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # 2. Usuarios conectados (sesiones no expiradas)
    connected_users = db.query(UserSession.user_id).filter(
        UserSession.expires_at > datetime.now(timezone.utc)
    ).distinct().count()
    
    # 3. Documentos totales
    total_documents = db.query(Document).count()
    
    # 4. Credenciales de la Bóveda (si es admin, total; si es usuario, solo las propias)
    if current_user.role.name == "Administrador":
        vault_credentials_count = db.query(Credential).count()
    else:
        vault_credentials_count = db.query(Credential).filter(Credential.owner_id == current_user.id).count()
        
    # 5. Eventos futuros
    events_count = db.query(Event).filter(Event.end_date >= datetime.now(timezone.utc)).count()
    
    # 6. Actividad reciente para el feed (logs de auditoría)
    # Si no es administrador, solo ve sus propias acciones en el feed de actividad
    audit_query = db.query(AuditLog)
    if current_user.role.name != "Administrador":
        audit_query = audit_query.filter(AuditLog.user_id == current_user.id)
        
    recent_logs = audit_query.order_by(AuditLog.created_at.desc()).limit(7).all()
    
    mapped_activity = []
    for log in recent_logs:
        mapped_activity.append({
            "id": log.id,
            "action": log.action,
            "details": log.details or "",
            "time": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "user_name": log.user.full_name if log.user else "Anónimo / Sistema"
        })
        
    return {
        "total_users": total_users,
        "active_users": active_users,
        "connected_users": max(connected_users, 1), # Al menos el usuario actual está conectado
        "total_documents": total_documents,
        "vault_credentials_count": vault_credentials_count,
        "events_count": events_count,
        "recent_activity": mapped_activity
    }
