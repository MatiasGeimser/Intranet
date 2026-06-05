from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    file_path = Column(String(250), nullable=False)
    file_type = Column(String(50), nullable=True)  # pdf, docx, png, etc.
    size_bytes = Column(Integer, nullable=False)
    folder = Column(String(100), default="General", nullable=False)  # IT, RRHH, Finanzas, etc.
    uploader_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(20), default="v1.0", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    # Relaciones
    uploader = relationship("User", back_populates="documents")
