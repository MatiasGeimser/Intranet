from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class SwitchDevice(Base):
    """Dispositivo de Red (Switch)"""
    __tablename__ = "switch_devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(150), nullable=False, unique=True)
    ip_address = Column(String(50), nullable=False)
    model = Column(String(100), nullable=True)
    manufacturer = Column(String(100), default="Cisco")
    location = Column(String(150), nullable=True)
    status = Column(String(20), default="Activo")  # Activo, Inactivo, Mantenimiento
    
    # Especificaciones
    total_ports = Column(Integer, default=24)
    uplink_ports = Column(Integer, default=2)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    interfaces = relationship("SwitchInterface", back_populates="switch", cascade="all, delete-orphan")


class SwitchInterface(Base):
    """Puerto/Interfaz de un Switch"""
    __tablename__ = "switch_interfaces"

    id = Column(Integer, primary_key=True, index=True)
    switch_id = Column(Integer, ForeignKey("switch_devices.id", ondelete="CASCADE"), nullable=False)
    
    # Información de Puerto
    interface_name = Column(String(50), nullable=False)  # Fa0/1, Gi0/1, etc
    port_type = Column(String(30))  # FastEthernet, Gigabit, etc
    port_number = Column(Integer)  # 1, 2, 3...
    
    # Configuración de VLAN
    vlan_id = Column(Integer, ForeignKey("vlans.id", ondelete="SET NULL"), nullable=True)
    vlan_name = Column(String(100), nullable=True)
    
    # Estado del Puerto
    status = Column(String(20), default="Active")  # Active, Down, etc
    description = Column(String(255), nullable=True)  # "ENDPOINT CONECTADO", "LIBRE", etc
    
    # Información de Dispositivo Conectado
    connected_device = Column(String(100), nullable=True)  # Nombre del equipo conectado
    connected_device_type = Column(String(50), nullable=True)  # PC, Printer, Camera, etc
    mac_address = Column(String(50), nullable=True)
    
    # Metadata
    is_uplink = Column(Boolean, default=False)
    is_trunk = Column(Boolean, default=False)
    trunk_vlans = Column(Text, nullable=True)  # JSON o comma-separated
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relaciones
    switch = relationship("SwitchDevice", back_populates="interfaces")
    vlan = relationship("VLAN")
    created_by = relationship("User", foreign_keys=[created_by_id])
