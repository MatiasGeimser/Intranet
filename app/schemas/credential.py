from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CredentialBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    url: Optional[str] = Field(None, max_length=200)
    username: str = Field(..., min_length=1, max_length=100)
    category: str = Field("General", max_length=50)

class CredentialCreate(CredentialBase):
    password: str = Field(..., min_length=1, max_length=100)

class CredentialUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, max_length=200)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)

class CredentialResponse(CredentialBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    decrypted_password: Optional[str] = None  # Se llenará bajo demanda (autorizado)

    class Config:
        from_attributes = True
