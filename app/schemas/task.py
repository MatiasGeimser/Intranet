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
    daily_task_config_id: Optional[int] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DailyTaskConfigBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    schedule_time: str = Field(..., description="Hora de ejecución en formato HH:MM (ej. 09:00)", max_length=5)
    assigned_to_user_id: int

class DailyTaskConfigCreate(DailyTaskConfigBase):
    pass

class DailyTaskConfigUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    schedule_time: Optional[str] = Field(None, max_length=5)
    assigned_to_user_id: Optional[int] = None
    is_active: Optional[bool] = None

class DailyTaskConfigOut(DailyTaskConfigBase):
    id: int
    is_active: bool
    created_by_id: int
    created_at: datetime
    last_triggered_date: Optional[datetime] = None

    class Config:
        from_attributes = True
