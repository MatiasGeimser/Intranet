from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ReturnedEquipment(BaseModel):
    applies: bool = False
    equipment_type: Optional[str] = None
    brand_model: Optional[str] = None
    serial: Optional[str] = None
    reason: Optional[str] = None
    operational_status: Optional[str] = None


class DeliveryRecordCreate(BaseModel):
    delivery_date: date
    site: Optional[str] = Field(None, max_length=120)
    collaborator_id: Optional[int] = None
    # Compatibilidad con formularios ya abiertos antes de migrar al directorio.
    recipient_id: Optional[int] = None
    recipient_name: str = Field(..., min_length=2, max_length=140)
    recipient_email: Optional[str] = Field(None, max_length=140)
    recipient_run: Optional[str] = Field(None, max_length=32)
    recipient_role: Optional[str] = Field(None, max_length=120)
    recipient_unit: Optional[str] = Field(None, max_length=120)
    employment_type: Optional[str] = Field(None, max_length=32)
    equipment_type: str = Field(..., pattern="^(Notebook|Desktop|All-in-One|Otro)$")
    equipment_brand_model: Optional[str] = Field(None, max_length=160)
    equipment_hostname: Optional[str] = Field(None, max_length=120)
    equipment_serial: Optional[str] = Field(None, max_length=120)
    mac_address: Optional[str] = Field(None, max_length=64)
    monitor_serial: Optional[str] = Field(None, max_length=120)
    dock_serial: Optional[str] = Field(None, max_length=120)
    accessories: List[str] = []
    delivery_condition: Optional[str] = Field(None, max_length=32)
    label_number: Optional[str] = Field(None, max_length=64)
    migration: List[str] = []
    returned_equipment: ReturnedEquipment = ReturnedEquipment()
    observations: Optional[str] = Field(None, max_length=4000)


class PublicSignatureCreate(BaseModel):
    signer_name: str = Field(..., min_length=2, max_length=140)
    signature_data: str = Field(..., min_length=32, max_length=700000)


class DeliveryRecordSummary(BaseModel):
    id: int
    reference: str
    recipient_name: str
    equipment_type: str
    equipment_brand_model: Optional[str]
    delivery_date: date
    status: str
    created_at: datetime
    recipient_signed_at: Optional[datetime]


class DeliveryRecordDetail(DeliveryRecordSummary):
    site: Optional[str]
    recipient_email: Optional[str]
    recipient_run: Optional[str]
    recipient_role: Optional[str]
    recipient_unit: Optional[str]
    employment_type: Optional[str]
    equipment_hostname: Optional[str]
    equipment_serial: Optional[str]
    mac_address: Optional[str]
    monitor_serial: Optional[str]
    dock_serial: Optional[str]
    accessories: List[str]
    delivery_condition: Optional[str]
    label_number: Optional[str]
    migration: List[str]
    returned_equipment: ReturnedEquipment
    observations: Optional[str]
    created_by_name: str
    signature_url: Optional[str] = None
    signature_expires_at: datetime
    recipient_signature_data: Optional[str] = None
    recipient_signer_name: Optional[str] = None
    content_hash: Optional[str] = None
    signed_document_hash: Optional[str] = None
