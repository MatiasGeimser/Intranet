from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class VLAN(Base):
    __tablename__ = "vlans"

    id = Column(Integer, primary_key=True, index=True)
    vlan_id = Column(Integer, nullable=False, unique=True)  # ID numérico de la VLAN
    name = Column(String(150), nullable=False)              # Nombre de la VLAN
    description = Column(Text, nullable=True)
    network = Column(String(50), nullable=True)             # Ej: 192.168.1.0/24
    gateway = Column(String(50), nullable=True)             # Puerta de enlace
    status = Column(String(20), default="Activo")           # Activo | Inactivo

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relaciones
    created_by = relationship("User", foreign_keys=[created_by_id])
