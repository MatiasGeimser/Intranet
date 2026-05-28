from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    url = Column(String(200), nullable=True)
    username = Column(String(100), nullable=False)
    encrypted_password = Column(String(500), nullable=False)  # Encriptada con AES-256-GCM
    category = Column(String(50), default="General", nullable=False)  # Servidores, BDs, Redes, etc.
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relaciones
    owner = relationship("User", back_populates="credentials")
