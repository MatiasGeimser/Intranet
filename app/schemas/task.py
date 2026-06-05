from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TaskBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: str = Field(default="pending", max_length=50)
    assigned_to_user_id: Optional[int] = None
    assigned_to_role_id: Optional[int] = None
    due_date: Optional[datetime] = None
    note_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)
    assigned_to_user_id: Optional[int] = None
    assigned_to_role_id: Optional[int] = None
    due_date: Optional[datetime] = None
    note_id: Optional[int] = None

class TaskOut(TaskBase):
    id: int
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True
