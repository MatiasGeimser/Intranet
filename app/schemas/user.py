from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=3, max_length=100)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50)
    role_id: int

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=3, max_length=100)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None
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
    created_at: datetime

    class Config:
        from_attributes = True
