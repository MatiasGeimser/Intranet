from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from datetime import datetime, timezone
from app.core.database import Base

class Collaborator(Base):
    __tablename__ = "collaborators"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False, index=True)
    avatar_url = Column(String(300), nullable=True)
    position = Column(String(100), nullable=True)
    company = Column(String(100), nullable=True, index=True)
    area = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    direct_boss = Column(String(150), nullable=True)
    email = Column(String(150), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    extension_3cx = Column(String(20), nullable=True, index=True)
    branch = Column(String(100), nullable=True)
    address = Column(String(200), nullable=True)
    hire_date = Column(DateTime, nullable=True)
    gender = Column(String(10), default="Hombre", nullable=True)
    status = Column(String(50), default="Disponible", nullable=False) # Disponible, Vacaciones, Licencia, Teletrabajo, etc.
    observations = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Índice compuesto opcional para búsquedas ultra rápidas, 
    # aunque los índices simples en MySQL/Postgres resuelven bien la búsqueda general.
    __table_args__ = (
        Index("idx_collab_search", "full_name", "email", "phone"),
    )
