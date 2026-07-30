from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.role import Role, Permission
from app.schemas.user import RoleSimple
from app.api.deps import get_current_active_user
from app.services.natura_access import is_natura_manager

router = APIRouter()

@router.get("", response_model=List[RoleSimple])
def get_roles(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Obtiene todos los roles disponibles en el sistema (Solo Administradores)."""
    if current_user.role.name == "Administrador" or "roles:manage" in {p.code for p in current_user.role.permissions}:
        return db.query(Role).all()
    if is_natura_manager(db, current_user):
        return db.query(Role).filter(Role.name == "Usuario").all()
    raise HTTPException(status_code=403, detail="No tienes permisos para consultar roles.")
