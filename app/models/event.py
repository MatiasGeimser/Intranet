from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    event_type = Column(String(50), default="internal", nullable=False)  # birthday, internal, reminder
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relaciones
    creator = relationship("User", back_populates="events")
