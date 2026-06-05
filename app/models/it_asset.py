from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class ITAsset(Base):
    __tablename__ = "it_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    asset_type = Column(String(30), nullable=False)  # SOFTWARE | HARDWARE | RED
    category = Column(String(80), nullable=True)      # Sub-categoria: ej. "Sistema Operativo", "Switch", "Servidor"
    description = Column(Text, nullable=True)

    # Campos de red / hardware
    ip_address = Column(String(50), nullable=True)
    mac_address = Column(String(50), nullable=True)

    # Campos de software
    license_key = Column(String(255), nullable=True)
    version = Column(String(50), nullable=True)
    vendor = Column(String(100), nullable=True)

    # Estado y fechas
    status = Column(String(20), default="Activo", nullable=False)  # Activo | Inactivo | Mantenimiento
    location = Column(String(120), nullable=True)                   # Sala, piso, oficina
    assigned_to = Column(String(120), nullable=True)                # Nombre de usuario o departamento
    acquired_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relaciones
    created_by = relationship("User", foreign_keys=[created_by_id])
