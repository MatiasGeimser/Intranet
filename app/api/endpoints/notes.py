from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.note import Note
from app.models.task import Task
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[NoteOut])
def read_notes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Obtiene el catálogo compartido de proyectos, con tareas filtradas por usuario.
    """
    notes = db.query(Note).order_by(Note.created_at.desc()).all()
    return [{
            "id": note.id,
            "title": note.title,
            "area_id": note.area_id,
            "created_by_id": note.created_by_id,
            "created_at": note.created_at,
            "tasks": [
                task for task in note.tasks
                if task.daily_task_config_id is None
                and (task.assigned_to_user_id == current_user.id or task.created_by_id == current_user.id)
            ],
        } for note in notes]

@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(note_in: NoteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Crea una nueva nota. Solo permitido para Administradores y Supervisores.
    """
    if current_user.role.name not in ["Administrador", "Supervisor"]:
        raise HTTPException(
            status_code=403,
            detail="Únicamente los administradores o supervisores pueden crear proyectos/notas."
        )
        
    area_id = current_user.area_id
    if current_user.role.name == "Administrador" and note_in.area_id is not None:
        area_id = note_in.area_id

    db_note = Note(
        title=note_in.title,
        created_by_id=current_user.id,
        area_id=area_id
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Elimina una nota. Permitido para el creador o Administradores/Supervisores.
    """
    db_note = db.query(Note).filter(Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
        
    if db_note.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para eliminar este proyecto/nota.")
    if any(task.assigned_to_user_id != current_user.id for task in db_note.tasks if task.daily_task_config_id is None):
        raise HTTPException(status_code=409, detail="No puedes eliminar un proyecto que contiene tareas asignadas a otras personas.")
        
    db.delete(db_note)
    db.commit()
    return None
