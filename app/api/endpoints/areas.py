from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.area import Area
from app.schemas.area import AreaOut
from app.api.deps import get_current_active_user
from app.services.natura_access import is_natura_manager

router = APIRouter()

@router.get("", response_model=List[AreaOut])
def get_areas(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Obtiene el listado de todas las áreas de trabajo registradas."""
    if is_natura_manager(db, current_user):
        return db.query(Area).filter(Area.name == "Ventas").all()
    return db.query(Area).all()
