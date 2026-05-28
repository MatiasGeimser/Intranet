from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.role import Role, Permission
from app.schemas.user import RoleSimple
from app.api.deps import PermissionChecker

router = APIRouter()

@router.get("", response_model=List[RoleSimple])
def get_roles(
    db: Session = Depends(get_db),
    current_user = Depends(PermissionChecker("roles:manage"))
):
    """Obtiene todos los roles disponibles en el sistema (Solo Administradores)."""
    return db.query(Role).all()
