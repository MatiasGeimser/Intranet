from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime

class EventBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    start_date: datetime
    end_date: datetime
    event_type: str = Field("internal", max_length=50) # birthday, internal, reminder
    is_shared: bool = False

class EventCreate(EventBase):
    @model_validator(mode='after')
    def check_dates(self) -> 'EventCreate':
        if self.start_date > self.end_date:
            raise ValueError("La fecha de inicio debe ser anterior a la fecha de fin.")
        return self

class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: Optional[str] = None
    is_shared: Optional[bool] = None

class CreatorSimple(BaseModel):
    id: int
    full_name: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class EventResponse(EventBase):
    id: int
    creator_id: int
    creator: CreatorSimple
    created_at: datetime
    is_holiday: bool = False

    class Config:
        from_attributes = True
