from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from typing import List
from datetime import datetime
import bleach

from app.core.database import get_db
from app.models.task import Task, DailyTaskConfig, TaskComment
from app.models.user import User
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskOut, TaskCommentCreate, TaskCommentOut,
    DailyTaskConfigCreate, DailyTaskConfigUpdate, DailyTaskConfigOut,
)
from app.api.deps import get_current_user

router = APIRouter()

ASSIGNABLE_TASK_ROLES = {
    "Administrador": {"Administrador", "Supervisor"},
    "Supervisor": {"Administrador", "Usuario"},
}
def validate_task_assignee(creator: User, assignee: User) -> None:
    allowed_roles = ASSIGNABLE_TASK_ROLES.get(creator.role.name)
    if not allowed_roles:
        raise HTTPException(status_code=403, detail="No tienes permiso para asignar tareas.")
    if assignee.role.name not in allowed_roles:
        allowed_label = " o ".join(sorted(allowed_roles))
        raise HTTPException(
            status_code=400,
            detail=f"Como {creator.role.name}, solo puedes asignar tareas a roles: {allowed_label}.",
        )


def is_task_assignee(task: Task, user: User) -> bool:
    return task.assigned_to_user_id == user.id


def is_task_owner(task: Task, user: User) -> bool:
    """La persona que crea una tarea conserva su administración."""
    return task.created_by_id == user.id


def can_access_task(task: Task, user: User) -> bool:
    return is_task_owner(task, user) or is_task_assignee(task, user)

@router.get("/", response_model=List[TaskOut])
def read_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieve only tasks created by or assigned to the current user.
    """
    query = db.query(Task).options(
        selectinload(Task.creator),
        selectinload(Task.assigned_user),
    ).filter(Task.daily_task_config_id.is_(None))
    query = query.filter(or_(
        Task.assigned_to_user_id == current_user.id,
        Task.created_by_id == current_user.id,
    ))
    return query.order_by(Task.created_at.desc()).all()

@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new task. Restricted to Admins and Supervisors.
    """
    if current_user.role.name not in ASSIGNABLE_TASK_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Únicamente los administradores y supervisores pueden crear tareas."
        )

    if task_in.assigned_to_role_id is not None:
        raise HTTPException(status_code=400, detail="Las tareas Scrum deben asignarse a una persona específica.")

    assignee_id = task_in.assigned_to_user_id
    if not assignee_id:
        raise HTTPException(status_code=400, detail="Selecciona un encargado para la tarea.")
    assignee = db.query(User).filter(User.id == assignee_id, User.is_active.is_(True)).first()
    if not assignee:
        raise HTTPException(status_code=400, detail="Selecciona un usuario activo para asignar la tarea.")
    validate_task_assignee(current_user, assignee)

    task_data = task_in.dict()
    task_data["assigned_to_user_id"] = assignee_id
    db_task = Task(
        **task_data,
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
            background_tasks.add_task(
                EmailService.send_task_assigned_email,
                recipient_email=recipient.email,
                recipient_name=recipient.full_name,
                task_title=db_task.title,
                assigner_name=current_user.full_name,
                note_title=note.title if note else "General"
            )
            
    return db_task

@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The creator can edit its task; the assignee can only change its status.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if not can_access_task(db_task, current_user):
        raise HTTPException(status_code=403, detail="No tienes autorización para acceder o actualizar esta tarea")

    old_assignee_id = db_task.assigned_to_user_id
    old_status = db_task.status
    can_manage_before_update = is_task_owner(db_task, current_user)
    update_data = task_in.dict(exclude_unset=True)

    if not can_manage_before_update:
        allowed_fields = {"status"}
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    elif update_data.get("assigned_to_role_id") is not None:
        raise HTTPException(status_code=400, detail="Las tareas Scrum deben asignarse a una persona específica.")
    elif "assigned_to_user_id" in update_data:
        assignee_id = update_data["assigned_to_user_id"]
        assignee = db.query(User).filter(User.id == assignee_id, User.is_active.is_(True)).first() if assignee_id else None
        if not assignee:
            raise HTTPException(status_code=400, detail="Selecciona un usuario activo para asignar la tarea.")
        validate_task_assignee(current_user, assignee)

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
    
    # Notificar solo si el creador reasignó una tarea propia a otra persona.
    if can_manage_before_update and db_task.assigned_to_user_id != old_assignee_id:
        recipient = db.query(User).filter(User.id == db_task.assigned_to_user_id).first()
        if recipient:
            from app.models.note import Note
            from app.services.email_service import EmailService
            note = db.query(Note).filter(Note.id == db_task.note_id).first() if db_task.note_id else None
            background_tasks.add_task(
                EmailService.send_task_assigned_email,
                recipient_email=recipient.email,
                recipient_name=recipient.full_name,
                task_title=db_task.title,
                assigner_name=current_user.full_name,
                note_title=note.title if note else "General"
            )

    # Avisar al creador cada vez que el encargado mueve la tarea entre columnas.
    # El SMTP no debe retrasar el movimiento de la tarjeta para quien la actualiza.
    if "status" in update_data and db_task.status != old_status:
        creator = db.query(User).filter(User.id == db_task.created_by_id, User.is_active.is_(True)).first()
        if creator:
            from app.models.note import Note
            from app.services.email_service import EmailService
            note = db.query(Note).filter(Note.id == db_task.note_id).first() if db_task.note_id else None
            background_tasks.add_task(
                EmailService.send_task_status_changed_email,
                recipient_email=creator.email,
                recipient_name=creator.full_name,
                task_title=db_task.title,
                previous_status=old_status,
                current_status=db_task.status,
                updated_by_name=current_user.full_name,
                note_title=note.title if note else "General",
            )
            
    return db_task


@router.get("/{task_id}/comments", response_model=List[TaskCommentOut])
def read_task_comments(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if not can_access_task(task, current_user):
        raise HTTPException(status_code=403, detail="No tienes autorización para ver los avances de esta tarea")

    return db.query(TaskComment).options(selectinload(TaskComment.author)).filter(
        TaskComment.task_id == task_id
    ).order_by(TaskComment.created_at.asc()).all()


@router.post("/{task_id}/comments", response_model=TaskCommentOut, status_code=status.HTTP_201_CREATED)
def add_task_comment(
    task_id: int,
    comment_in: TaskCommentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if not can_access_task(task, current_user):
        raise HTTPException(status_code=403, detail="No tienes autorización para agregar avances a esta tarea")

    content = bleach.clean(comment_in.content, tags=[], attributes={}, strip=True).strip()
    if not content:
        raise HTTPException(status_code=400, detail="Escribe un avance antes de guardarlo")

    comment = TaskComment(task_id=task.id, author_id=current_user.id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    recipient_id = task.assigned_to_user_id if current_user.id == task.created_by_id else task.created_by_id
    if recipient_id and recipient_id != current_user.id:
        recipient = db.query(User).filter(User.id == recipient_id, User.is_active.is_(True)).first()
        if recipient:
            from app.models.note import Note
            from app.services.email_service import EmailService
            note = db.query(Note).filter(Note.id == task.note_id).first() if task.note_id else None
            background_tasks.add_task(
                EmailService.send_task_comment_email,
                recipient_email=recipient.email,
                recipient_name=recipient.full_name,
                task_title=task.title,
                comment_content=comment.content,
                author_name=current_user.full_name,
                note_title=note.title if note else "General",
            )
    return comment


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete a task. Restricted to its creator.
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not is_task_owner(db_task, current_user):
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
        tasks = db.query(Task).options(
            selectinload(Task.creator),
            selectinload(Task.assigned_user),
        ).filter(Task.daily_task_config_id.isnot(None)).order_by(Task.created_at.desc()).all()
    else:
        tasks = db.query(Task).options(
            selectinload(Task.creator),
            selectinload(Task.assigned_user),
        ).filter(
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
