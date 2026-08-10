from sqlalchemy import Boolean, Column, Integer, String, DateTime, Enum
from datetime import datetime, timezone
from app.core.database import Base
import enum

class LineDirection(str, enum.Enum):
    entrada = "Entrada"
    salida  = "Salida"
    ambos   = "Ambos"

class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id          = Column(Integer, primary_key=True, index=True)
    cliente     = Column(String(120), nullable=False, index=True)
    numero      = Column(String(30),  nullable=False, index=True)
    direccion   = Column(String(10),  nullable=False, default="Ambos")  # Entrada / Salida / Ambos
    prefijo     = Column(String(20),  nullable=True)
    notas       = Column(String(300), nullable=True)
    is_active   = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)
