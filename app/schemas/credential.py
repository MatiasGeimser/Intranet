from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CredentialBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    url: Optional[str] = Field(None, max_length=200)
    username: str = Field(..., min_length=1, max_length=100)
    category: str = Field("General", max_length=50)
    is_active: Optional[bool] = True

class CredentialCreate(CredentialBase):
    password: str = Field(..., min_length=1, max_length=100)

class CredentialUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, max_length=200)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

class CredentialResponse(CredentialBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    decrypted_password: Optional[str] = None  # Se llenará bajo demanda (autorizado)

    class Config:
        from_attributes = True


class ExecutiveCredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    correo_user: Optional[str] = None
    correo_pass: Optional[str] = None
    crm_user: Optional[str] = None
    crm_pass: Optional[str] = None
    vocalcom_user: Optional[str] = None
    vocalcom_pass: Optional[str] = None
    vocalcom_estacion: Optional[str] = None
    pc_user: Optional[str] = None
    pc_pass: Optional[str] = None

