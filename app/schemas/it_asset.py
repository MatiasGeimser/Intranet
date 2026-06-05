from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ITAssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    asset_type: str = Field(..., pattern="^(SOFTWARE|HARDWARE|RED)$")
    category: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = None
    ip_address: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    license_key: Optional[str] = Field(None, max_length=255)
    version: Optional[str] = Field(None, max_length=50)
    vendor: Optional[str] = Field(None, max_length=100)
    status: str = Field("Activo", max_length=20)
    location: Optional[str] = Field(None, max_length=120)
    assigned_to: Optional[str] = Field(None, max_length=120)
    acquired_at: Optional[datetime] = None


class ITAssetCreate(ITAssetBase):
    pass


class ITAssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    asset_type: Optional[str] = Field(None, pattern="^(SOFTWARE|HARDWARE|RED)$")
    category: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = None
    ip_address: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    license_key: Optional[str] = Field(None, max_length=255)
    version: Optional[str] = Field(None, max_length=50)
    vendor: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=120)
    assigned_to: Optional[str] = Field(None, max_length=120)
    acquired_at: Optional[datetime] = None


class ITAssetResponse(ITAssetBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
