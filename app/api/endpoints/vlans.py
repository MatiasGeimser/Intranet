from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.vlan import VLAN
from app.schemas.vlan import VLANCreate, VLANUpdate, VLANResponse
from app.api.deps import PermissionChecker
from app.services.audit_service import audit_service
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[VLANResponse])
def get_vlans(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Obtiene todas las VLANs configuradas, filtrable por estado."""
    query = db.query(VLAN)
    if status:
        query = query.filter(VLAN.status == status)
    return query.order_by(VLAN.vlan_id).all()


@router.get("/{vlan_id}", response_model=VLANResponse)
def get_vlan(
    vlan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Obtiene una VLAN específica por su ID VLAN."""
    vlan = db.query(VLAN).filter(VLAN.vlan_id == vlan_id).first()
    if not vlan:
        raise HTTPException(status_code=404, detail="VLAN no encontrada.")
    return vlan


@router.post("", response_model=VLANResponse, status_code=status.HTTP_201_CREATED)
def create_vlan(
    request: Request,
    vlan_data: VLANCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Registra una nueva VLAN."""
    
    # Verificar si ya existe
    existing = db.query(VLAN).filter(VLAN.vlan_id == vlan_data.vlan_id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"La VLAN {vlan_data.vlan_id} ya existe."
        )
    
    db_vlan = VLAN(**vlan_data.model_dump(), created_by_id=current_user.id)
    db.add(db_vlan)
    db.commit()
    db.refresh(db_vlan)

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="vlan_create",
        ip_address=request.client.host if request.client else None,
        details=f"Creó VLAN {db_vlan.vlan_id}: {db_vlan.name}"
    )
    return db_vlan


@router.put("/{vlan_id}", response_model=VLANResponse)
def update_vlan(
    vlan_id: int,
    request: Request,
    vlan_data: VLANUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Actualiza los datos de una VLAN."""
    vlan = db.query(VLAN).filter(VLAN.vlan_id == vlan_id).first()
    if not vlan:
        raise HTTPException(status_code=404, detail="VLAN no encontrada.")

    for field, value in vlan_data.model_dump(exclude_unset=True).items():
        setattr(vlan, field, value)

    db.commit()
    db.refresh(vlan)

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="vlan_update",
        ip_address=request.client.host if request.client else None,
        details=f"Actualizó VLAN {vlan.vlan_id}: {vlan.name}"
    )
    return vlan


@router.delete("/{vlan_id}")
def delete_vlan(
    vlan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Elimina una VLAN."""
    vlan = db.query(VLAN).filter(VLAN.vlan_id == vlan_id).first()
    if not vlan:
        raise HTTPException(status_code=404, detail="VLAN no encontrada.")

    name = vlan.name
    db.delete(vlan)
    db.commit()

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="vlan_delete",
        ip_address=request.client.host if request.client else None,
        details=f"Eliminó VLAN {vlan_id}: {name}"
    )
    return {"detail": "VLAN eliminada exitosamente."}
