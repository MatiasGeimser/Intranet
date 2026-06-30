from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class UserMinimal(BaseModel):
    id: int
    full_name: str
    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    name: str
    folder: str = Field("General", max_length=100)

class DocumentCreate(DocumentBase):
    file_path: str
    file_type: Optional[str] = None
    size_bytes: int
    version: Optional[str] = "v1.0"

class DocumentContentUpdate(BaseModel):
    content: Optional[str] = None
    rows: Optional[list[list[str]]] = None
    sheet_name: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    file_path: str
    file_type: Optional[str] = None
    size_bytes: int
    version: str
    uploader_id: int
    is_public: bool
    allowed_users: List[UserMinimal] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
