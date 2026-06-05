from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VLANBase(BaseModel):
    vlan_id: int = Field(..., gt=0, le=4094)  # VLANs válidas van de 1 a 4094
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    network: Optional[str] = Field(None, max_length=50)
    gateway: Optional[str] = Field(None, max_length=50)
    status: str = Field("Activo", max_length=20)


class VLANCreate(VLANBase):
    pass


class VLANUpdate(BaseModel):
    vlan_id: Optional[int] = Field(None, gt=0, le=4094)
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    network: Optional[str] = Field(None, max_length=50)
    gateway: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=20)


class VLANResponse(VLANBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
