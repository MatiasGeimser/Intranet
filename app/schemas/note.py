from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.schemas.task import TaskOut

class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    area_id: Optional[int] = None

class NoteCreate(NoteBase):
    pass

class NoteOut(NoteBase):
    id: int
    created_by_id: int
    created_at: datetime
    tasks: List[TaskOut] = []

    class Config:
        from_attributes = True
