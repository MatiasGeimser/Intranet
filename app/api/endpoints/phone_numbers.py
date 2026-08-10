from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.phone_number import PhoneNumber
from app.schemas.phone_number import PhoneNumberCreate, PhoneNumberUpdate, PhoneNumberResponse
from app.api.deps import get_current_active_user, PermissionChecker
from app.services.audit_service import audit_service
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[PhoneNumberResponse])
def get_phone_numbers(
    cliente   : Optional[str] = None,
    direccion : Optional[str] = None,
    is_active : Optional[bool] = None,
    search    : Optional[str] = None,
    db        : Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Lista todos los números contratados con filtros opcionales."""
    query = db.query(PhoneNumber)

    if cliente:
        query = query.filter(PhoneNumber.cliente.ilike(f"%{cliente}%"))
    if direccion:
        query = query.filter(PhoneNumber.direccion == direccion)
    if is_active is not None:
        query = query.filter(PhoneNumber.is_active.is_(is_active))
    if search:
        query = query.filter(
            PhoneNumber.numero.ilike(f"%{search}%") |
            PhoneNumber.cliente.ilike(f"%{search}%") |
            PhoneNumber.prefijo.ilike(f"%{search}%")
        )

    return query.order_by(PhoneNumber.cliente, PhoneNumber.numero).all()


@router.post("", response_model=PhoneNumberResponse, status_code=status.HTTP_201_CREATED)
def create_phone_number(
    request    : Request,
    data       : PhoneNumberCreate,
    db         : Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Registra un nuevo número contratado."""
    # Verificar duplicado por número
    existing = db.query(PhoneNumber).filter(PhoneNumber.numero == data.numero.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El número '{data.numero}' ya está registrado."
        )

    phone = PhoneNumber(
        cliente   = data.cliente.strip(),
        numero    = data.numero.strip(),
        direccion = data.direccion,
        prefijo   = data.prefijo.strip() if data.prefijo else None,
        notas     = data.notas.strip()   if data.notas   else None,
        is_active = data.is_active,
    )
    db.add(phone)
    db.commit()
    db.refresh(phone)

    audit_service.log_action(
        db=db, user_id=current_user.id,
        action="phone_number_create",
        ip_address=request.client.host if request.client else None,
        details=f"Registró el número '{phone.numero}' para el cliente '{phone.cliente}'."
    )

    return phone


@router.put("/{phone_id}", response_model=PhoneNumberResponse)
def update_phone_number(
    phone_id   : int,
    request    : Request,
    data       : PhoneNumberUpdate,
    db         : Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Actualiza los datos de un número contratado."""
    phone = db.query(PhoneNumber).filter(PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Número no encontrado.")

    if data.cliente   is not None: phone.cliente   = data.cliente.strip()
    if data.numero    is not None: phone.numero    = data.numero.strip()
    if data.direccion is not None: phone.direccion = data.direccion
    if data.prefijo   is not None: phone.prefijo   = data.prefijo.strip() or None
    if data.notas     is not None: phone.notas     = data.notas.strip()   or None
    if data.is_active is not None: phone.is_active = data.is_active

    db.commit()
    db.refresh(phone)

    audit_service.log_action(
        db=db, user_id=current_user.id,
        action="phone_number_update",
        ip_address=request.client.host if request.client else None,
        details=f"Actualizó el número ID {phone.id} ('{phone.numero}')."
    )

    return phone


@router.delete("/{phone_id}")
def delete_phone_number(
    phone_id   : int,
    request    : Request,
    db         : Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Elimina un número contratado."""
    phone = db.query(PhoneNumber).filter(PhoneNumber.id == phone_id).first()
    if not phone:
        raise HTTPException(status_code=404, detail="Número no encontrado.")

    numero  = phone.numero
    cliente = phone.cliente
    db.delete(phone)
    db.commit()

    audit_service.log_action(
        db=db, user_id=current_user.id,
        action="phone_number_delete",
        ip_address=request.client.host if request.client else None,
        details=f"Eliminó el número '{numero}' del cliente '{cliente}'."
    )

    return {"detail": f"Número '{numero}' eliminado correctamente."}
