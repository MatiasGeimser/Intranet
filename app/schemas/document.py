from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DocumentBase(BaseModel):
    name: str
    folder: str = Field("General", max_length=100)

class DocumentCreate(DocumentBase):
    file_path: str
    file_type: Optional[str] = None
    size_bytes: int
    version: Optional[str] = "v1.0"

class DocumentResponse(DocumentBase):
    id: int
    file_path: str
    file_type: Optional[str] = None
    size_bytes: int
    version: str
    uploader_id: int
    created_at: datetime

    class Config:
        from_attributes = True
