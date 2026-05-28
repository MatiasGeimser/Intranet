from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # SET NULL si se borra el usuario
    action = Column(String(100), nullable=False)  # ej. "login_success", "credential_decrypt", "user_create"
    ip_address = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)  # ej. "Se accedió a la credencial ID 4"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relaciones
    user = relationship("User", back_populates="audit_logs")
