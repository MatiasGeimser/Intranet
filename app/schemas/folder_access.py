from pydantic import BaseModel
from typing import Optional

class FolderAccessBase(BaseModel):
    folder_name: str
    can_read: bool = True
    can_write: bool = False

class FolderAccessCreate(FolderAccessBase):
    pass

class FolderAccessResponse(FolderAccessBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
