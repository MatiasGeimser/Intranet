from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.schemas.area import AreaSimple
from app.schemas.folder_access import FolderAccessCreate, FolderAccessResponse
from typing import Optional, List

class UserBase(BaseModel):
    email: str
    full_name: str = Field(..., min_length=3, max_length=100)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = True
    area_id: Optional[int] = None
    birth_date: Optional[datetime] = None
    gender: Optional[str] = "Hombre"
    supervisor_id: Optional[int] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50)
    role_id: int
    folder_permissions: Optional[List[FolderAccessCreate]] = None

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, min_length=3, max_length=100)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None
    area_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    gender: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6, max_length=50)
    folder_permissions: Optional[List[FolderAccessCreate]] = None


class NaturaManagersUpdate(BaseModel):
    manager_ids: List[int] = Field(default_factory=list, max_length=2)

class RoleSimple(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    is_document_admin: bool = False
    role_id: int
    role: RoleSimple
    area: Optional[AreaSimple] = None
    supervisor_id: Optional[int] = None
    created_at: datetime
    folder_permissions: Optional[List[FolderAccessResponse]] = None

    class Config:
        from_attributes = True
