from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SwitchInterfaceBase(BaseModel):
    interface_name: str = Field(..., max_length=50)
    port_type: Optional[str] = Field(None, max_length=30)
    port_number: Optional[int] = None
    vlan_id: Optional[int] = None
    vlan_name: Optional[str] = Field(None, max_length=100)
    status: str = Field("Active", max_length=20)
    is_enabled: bool = True
    description: Optional[str] = Field(None, max_length=255)
    connected_device: Optional[str] = Field(None, max_length=100)
    connected_device_type: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    workspace_id: Optional[int] = None
    is_uplink: bool = False
    is_trunk: bool = False
    trunk_vlans: Optional[str] = None


class SwitchInterfaceCreate(SwitchInterfaceBase):
    switch_id: int


class SwitchInterfaceUpdate(BaseModel):
    interface_name: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=20)
    is_enabled: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)
    connected_device: Optional[str] = Field(None, max_length=100)
    connected_device_type: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    workspace_id: Optional[int] = None
    vlan_id: Optional[int] = None
    vlan_name: Optional[str] = Field(None, max_length=100)
    is_trunk: Optional[bool] = None
    trunk_vlans: Optional[str] = None


class SwitchInterfaceResponse(SwitchInterfaceBase):
    id: int
    switch_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    workspace_code: Optional[str] = None

    class Config:
        from_attributes = True


class SwitchDeviceBase(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=150)
    ip_address: str = Field(..., max_length=50)
    model: Optional[str] = Field(None, max_length=100)
    manufacturer: str = Field("Cisco", max_length=100)
    location: Optional[str] = Field(None, max_length=150)
    status: str = Field("Activo", max_length=20)
    total_ports: int = Field(24, ge=1)
    uplink_ports: int = Field(2, ge=0)


class SwitchDeviceCreate(SwitchDeviceBase):
    pass


class SwitchDeviceUpdate(BaseModel):
    hostname: Optional[str] = Field(None, min_length=1, max_length=150)
    ip_address: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=150)
    status: Optional[str] = Field(None, max_length=20)
    total_ports: Optional[int] = Field(None, ge=1)
    uplink_ports: Optional[int] = Field(None, ge=0)


class SwitchDeviceDetailResponse(SwitchDeviceBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    interfaces: List[SwitchInterfaceResponse] = []

    class Config:
        from_attributes = True


class SwitchDeviceResponse(SwitchDeviceBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
