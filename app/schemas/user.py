from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.schemas.area import AreaSimple

class UserBase(BaseModel):
    email: str
    full_name: str = Field(..., min_length=3, max_length=100)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = True
    area_id: Optional[int] = None
    birth_date: Optional[datetime] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50)
    role_id: int

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, min_length=3, max_length=100)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None
    area_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=6, max_length=50)

class RoleSimple(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    role_id: int
    role: RoleSimple
    area: Optional[AreaSimple] = None
    created_at: datetime

    class Config:
        from_attributes = True
