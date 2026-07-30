from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(100), nullable=False)
    avatar_url = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_natura_user = Column(Boolean, default=False, nullable=False)
    is_document_admin = Column(Boolean, default=False, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    gender = Column(String(10), default="Hombre", nullable=True)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relaciones
    role = relationship("Role", back_populates="users")
    area = relationship("Area", back_populates="users")
    supervisor = relationship("User", remote_side=[id], backref="subordinates")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("Credential", back_populates="owner", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="uploader", cascade="all, delete-orphan")
    news_posts = relationship("News", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="creator", cascade="all, delete-orphan")
    tasks = relationship("Task", foreign_keys="[Task.assigned_to_user_id]", back_populates="assigned_user")
    folder_permissions = relationship("FolderAccess", backref="user", cascade="all, delete-orphan")
