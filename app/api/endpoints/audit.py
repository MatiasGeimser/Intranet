from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.api.deps import PermissionChecker
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class AuditResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    ip_address: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("", response_model=List[AuditResponse])
def get_audit_logs(
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("audit:read"))
):
    """Obtiene el historial de registros de auditoría de ciberseguridad (Solo Administrador)."""
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if search:
        query = query.filter(AuditLog.details.ilike(f"%{search}%"))
        
    logs = query.order_by(AuditLog.created_at.desc()).limit(200).all()
    
    # Mapear para incluir nombre y correo del usuario para mayor legibilidad
    response_logs = []
    for log in logs:
        user_name = "Anónimo / Sistema"
        user_email = "-"
        if log.user:
            user_name = log.user.full_name
            user_email = log.user.email
            
        response_logs.append({
            "id": log.id,
            "user_id": log.user_id,
            "user_name": user_name,
            "user_email": user_email,
            "action": log.action,
            "ip_address": log.ip_address,
            "details": log.details,
            "created_at": log.created_at
        })
        
    return response_logs
