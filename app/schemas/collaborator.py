from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class CollaboratorBase(BaseModel):
    full_name: str
    avatar_url: Optional[str] = None
    position: Optional[str] = None
    company: Optional[str] = None
    area: Optional[str] = None
    department: Optional[str] = None
    direct_boss: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    extension_3cx: Optional[str] = None
    branch: Optional[str] = None
    address: Optional[str] = None
    hire_date: Optional[datetime] = None
    gender: Optional[str] = "Hombre"
    status: str = "Disponible"
    observations: Optional[str] = None

class CollaboratorCreate(CollaboratorBase):
    pass

class CollaboratorUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    position: Optional[str] = None
    company: Optional[str] = None
    area: Optional[str] = None
    department: Optional[str] = None
    direct_boss: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    extension_3cx: Optional[str] = None
    branch: Optional[str] = None
    address: Optional[str] = None
    hire_date: Optional[datetime] = None
    gender: Optional[str] = None
    status: Optional[str] = None
    observations: Optional[str] = None

class CollaboratorOut(CollaboratorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
