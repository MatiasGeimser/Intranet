from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventResponse, EventCreate, EventUpdate
from app.api.deps import PermissionChecker, get_current_active_user
from app.services.audit_service import audit_service

router = APIRouter()

@router.get("", response_model=List[EventResponse])
def get_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("events:manage"))
):
    """Obtiene todos los eventos del calendario."""
    events = db.query(Event).all()
    
    return events


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    request: Request,
    event_data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("events:manage"))
):
    """Crea un nuevo evento en el calendario corporativo."""
    db_event = Event(
        title=event_data.title,
        description=event_data.description,
        start_date=event_data.start_date,
        end_date=event_data.end_date,
        event_type=event_data.event_type,
        creator_id=current_user.id
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="event_create",
        ip_address=request.client.host if request.client else None,
        details=f"Creó el evento '{db_event.title}' de tipo {db_event.event_type}."
    )

    return db_event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    request: Request,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("events:manage"))
):
    """Modifica un evento existente en el calendario."""
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Evento no encontrado.")
        
    # Validar permisos
    if current_user.role.name != "Administrador" and db_event.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar este evento.")

    if event_data.title:
        db_event.title = event_data.title
    if event_data.description is not None:
        db_event.description = event_data.description
    if event_data.start_date:
        db_event.start_date = event_data.start_date
    if event_data.end_date:
        db_event.end_date = event_data.end_date
    if event_data.event_type:
        db_event.event_type = event_data.event_type

    db.commit()
    db.refresh(db_event)

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="event_update",
        ip_address=request.client.host if request.client else None,
        details=f"Actualizó el evento ID {db_event.id} ('{db_event.title}')."
    )

    return db_event


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("events:manage"))
):
    """Elimina un evento del calendario corporativo."""
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Evento no encontrado.")
        
    if current_user.role.name != "Administrador" and db_event.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tiene permisos para eliminar este evento.")

    title = db_event.title
    db.delete(db_event)
    db.commit()

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="event_delete",
        ip_address=request.client.host if request.client else None,
        details=f"Eliminó el evento '{title}' del calendario."
    )

    return {"detail": "Evento eliminado correctamente."}
