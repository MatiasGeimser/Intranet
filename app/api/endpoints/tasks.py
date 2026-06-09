from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from app.core.database import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[TaskOut])
def read_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieve tasks assigned to the current user OR to the user's role.
    """
    tasks = db.query(Task).filter(
        or_(
            Task.assigned_to_user_id == current_user.id,
            Task.assigned_to_role_id == current_user.role_id,
            Task.created_by_id == current_user.id
        )
    ).order_by(Task.created_at.desc()).all()
    return tasks

@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new task.
    """
    db_task = Task(
        **task_in.dict(),
        created_by_id=current_user.id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Enviar correo si se asignó a un usuario
    if db_task.assigned_to_user_id:
        recipient = db.query(User).filter(User.id == db_task.assigned_to_user_id).first()
        if recipient:
            from app.models.note import Note
            from app.services.email_service import EmailService
            note = db.query(Note).filter(Note.id == db_task.note_id).first() if db_task.note_id else None
            EmailService.send_task_assigned_email(
                recipient_email=recipient.email,
                recipient_name=recipient.full_name,
                task_title=db_task.title,
                assigner_name=current_user.full_name,
                note_title=note.title if note else "General"
            )
            
    return db_task

@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Update a task (e.g. mark as completed).
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Check permissions: only creator, assignee, or role assignee can update (or Administrator)
    if current_user.role.name != "Administrador" and \
       db_task.created_by_id != current_user.id and \
       db_task.assigned_to_user_id != current_user.id and \
       db_task.assigned_to_role_id != current_user.role_id:
        raise HTTPException(status_code=403, detail="Not authorized to access or update this task")
        
    old_assignee_id = db_task.assigned_to_user_id
    
    # Just update the fields
    update_data = task_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
        
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Enviar correo si el asignado cambió y no es nulo
    if db_task.assigned_to_user_id and db_task.assigned_to_user_id != old_assignee_id:
        recipient = db.query(User).filter(User.id == db_task.assigned_to_user_id).first()
        if recipient:
            from app.models.note import Note
            from app.services.email_service import EmailService
            note = db.query(Note).filter(Note.id == db_task.note_id).first() if db_task.note_id else None
            EmailService.send_task_assigned_email(
                recipient_email=recipient.email,
                recipient_name=recipient.full_name,
                task_title=db_task.title,
                assigner_name=current_user.full_name,
                note_title=note.title if note else "General"
            )
            
    return db_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete a task.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Only creator can delete
    if db_task.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
        
    db.delete(db_task)
    db.commit()
    return None
