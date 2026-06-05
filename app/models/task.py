from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False) # e.g. "pending", "completed"
    
    # Who created the task
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Task assigned to specific user or specific role
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    due_date = Column(DateTime, nullable=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by_id], backref="created_tasks")
    assigned_user = relationship("User", foreign_keys=[assigned_to_user_id], back_populates="tasks")
    assigned_role = relationship("Role", foreign_keys=[assigned_to_role_id], back_populates="tasks")
    note = relationship("Note", back_populates="tasks")
