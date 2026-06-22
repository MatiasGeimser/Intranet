from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models.task import Task, DailyTaskConfig
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut, DailyTaskConfigCreate, DailyTaskConfigUpdate, DailyTaskConfigOut
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[TaskOut])
def read_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieve tasks assigned to the current user (if standard user) or all tasks (if Admin/Supervisor).
    """
    if current_user.role.name == "Administrador":
        tasks = db.query(Task).filter(Task.daily_task_config_id.is_(None)).order_by(Task.created_at.desc()).all()
    else:
        # Regular users (including Supervisors) see tasks assigned to them or created by them
        tasks = db.query(Task).filter(
            Task.daily_task_config_id.is_(None),
            or_(
                Task.assigned_to_user_id == current_user.id,
                Task.created_by_id == current_user.id
            )
        ).order_by(Task.created_at.desc()).all()
    return tasks

@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new task. Restricted to Admins and Supervisors.
    """
    if current_user.role.name != "Administrador":
        raise HTTPException(
            status_code=403,
            detail="Únicamente los administradores pueden crear tareas."
        )

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
    Update a task. Standard users can only update the task status if it is assigned to them.
    Admins and Supervisors can update any task fields.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    is_management = current_user.role.name == "Administrador"
    
    # Check permissions
    if not is_management and db_task.assigned_to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes autorización para acceder o actualizar esta tarea")
        
    old_assignee_id = db_task.assigned_to_user_id
    
    # Just update the fields
    update_data = task_in.dict(exclude_unset=True)
    
    # Standard user can ONLY change the status of the task
    if not is_management:
        allowed_fields = {"status"}
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
    for field, value in update_data.items():
        setattr(db_task, field, value)
        
    if "status" in update_data:
        if update_data["status"] in ["done", "completed"]:
            db_task.completed_at = datetime.now()
        else:
            db_task.completed_at = None
            
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Enviar correo si el asignado cambió y no es nulo (solo gestionado por admin/supervisor)
    if is_management and db_task.assigned_to_user_id and db_task.assigned_to_user_id != old_assignee_id:
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
    Delete a task. Restricted to the creator, Admins, and Supervisors.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    is_management = current_user.role.name == "Administrador"
    
    # Creator or Admins/Supervisors can delete
    if not is_management and db_task.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes autorización para eliminar esta tarea")
        
    db.delete(db_task)
    db.commit()
    return None

# --- DAILY TASKS ROUTES ---

@router.get("/daily/instances", response_model=List[TaskOut])
def read_daily_task_instances(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieve generated daily tasks (instances) assigned to the current user.
    """
    if current_user.role.name == "Administrador":
        tasks = db.query(Task).filter(Task.daily_task_config_id.isnot(None)).order_by(Task.created_at.desc()).all()
    else:
        tasks = db.query(Task).filter(
            Task.daily_task_config_id.isnot(None),
            or_(
                Task.assigned_to_user_id == current_user.id,
                Task.created_by_id == current_user.id
            )
        ).order_by(Task.created_at.desc()).all()
    return tasks

@router.get("/daily", response_model=List[DailyTaskConfigOut])
def read_daily_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieve daily tasks.
    """
    if current_user.role.name == "Administrador":
        tasks = db.query(DailyTaskConfig).order_by(DailyTaskConfig.created_at.desc()).all()
    else:
        tasks = db.query(DailyTaskConfig).filter(
            or_(
                DailyTaskConfig.assigned_to_user_id == current_user.id,
                DailyTaskConfig.created_by_id == current_user.id
            )
        ).order_by(DailyTaskConfig.created_at.desc()).all()
    return tasks

@router.post("/daily", response_model=DailyTaskConfigOut, status_code=status.HTTP_201_CREATED)
def create_daily_task(task_in: DailyTaskConfigCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new daily task config. Restricted to Admins and Supervisors.
    """
    if current_user.role.name != "Administrador":
        raise HTTPException(
            status_code=403,
            detail="Únicamente los administradores o supervisores pueden crear tareas diarias."
        )

    db_task = DailyTaskConfig(
        **task_in.dict(),
        created_by_id=current_user.id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.put("/daily/{task_id}", response_model=DailyTaskConfigOut)
def update_daily_task(task_id: int, task_in: DailyTaskConfigUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Update a daily task config.
    """
    db_task = db.query(DailyTaskConfig).filter(DailyTaskConfig.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Daily Task not found")
        
    is_management = current_user.role.name == "Administrador"
    if not is_management and db_task.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes autorización para actualizar esta tarea")
        
    update_data = task_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
        
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.delete("/daily/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete a daily task config.
    """
    db_task = db.query(DailyTaskConfig).filter(DailyTaskConfig.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Daily Task not found")
    
    is_management = current_user.role.name == "Administrador"
    if not is_management and db_task.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes autorización para eliminar esta tarea")
        
    db.delete(db_task)
    db.commit()
    return None
