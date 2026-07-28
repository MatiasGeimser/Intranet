from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer

from app.core.database import Base


class AdminChatPresence(Base):
    """Último heartbeat de cada usuario del chat institucional."""

    __tablename__ = "admin_chat_presence"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
