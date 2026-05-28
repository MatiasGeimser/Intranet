from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="General", nullable=False)  # Comunicado, Evento, IT, RRHH
    is_featured = Column(Boolean, default=False, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relaciones
    author = relationship("User", back_populates="news_posts")
    comments = relationship("Comment", back_populates="news", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    news_id = Column(Integer, ForeignKey("news.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relaciones
    news = relationship("News", back_populates="comments")
    author = relationship("User", back_populates="comments")
