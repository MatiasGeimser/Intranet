from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
    Obtiene las notas pertenecientes al área del usuario (o todas si es admin).
    """
    if current_user.role.name != "Administrador":
        notes = db.query(Note).filter(Note.area_id == current_user.area_id).order_by(Note.created_at.desc()).all()
    else:
        notes = db.query(Note).order_by(Note.created_at.desc()).all()
    return notes

@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(note_in: NoteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Crea una nueva nota asignándole automáticamente el área del creador.
    """
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
    Elimina una nota. Solo permitido para el creador de la nota.
    """
    db_note = db.query(Note).filter(Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
        
    if db_note.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para eliminar esta nota.")
        
    db.delete(db_note)
    db.commit()
    return None
