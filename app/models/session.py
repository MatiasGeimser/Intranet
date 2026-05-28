from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(200), unique=True, index=True, nullable=False)
    user_agent = Column(String(200), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relaciones
    user = relationship("User", back_populates="sessions")
