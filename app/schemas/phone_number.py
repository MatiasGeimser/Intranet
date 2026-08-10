from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class LineDirection(str, Enum):
    entrada = "Entrada"
    salida  = "Salida"
    ambos   = "Ambos"

class PhoneNumberBase(BaseModel):
    cliente   : str            = Field(..., max_length=120, description="Nombre del cliente o empresa")
    numero    : str            = Field(..., max_length=30,  description="Número telefónico contratado")
    direccion : LineDirection  = Field(default=LineDirection.ambos, description="Entrada / Salida / Ambos")
    prefijo   : Optional[str]  = Field(default=None, max_length=20,  description="Prefijo DDI o interno")
    notas     : Optional[str]  = Field(default=None, max_length=300, description="Observaciones adicionales")
    is_active : bool           = Field(default=True, description="Indica si la línea contratada se encuentra activa")

class PhoneNumberCreate(PhoneNumberBase):
    pass

class PhoneNumberUpdate(BaseModel):
    cliente   : Optional[str]          = Field(default=None, max_length=120)
    numero    : Optional[str]          = Field(default=None, max_length=30)
    direccion : Optional[LineDirection] = None
    prefijo   : Optional[str]          = Field(default=None, max_length=20)
    notas     : Optional[str]          = Field(default=None, max_length=300)
    is_active : Optional[bool]         = None

class PhoneNumberResponse(PhoneNumberBase):
    id         : int
    created_at : datetime
    updated_at : datetime

    class Config:
        from_attributes = True
