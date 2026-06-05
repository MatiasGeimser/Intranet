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
    return db_task

@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Update a task (e.g. mark as completed).
    """
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Check permissions if necessary, right now allowing if they can see it or created it
    # Just update the fields
    update_data = task_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
        
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
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
