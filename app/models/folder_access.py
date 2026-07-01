from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.core.database import Base

class FolderAccess(Base):
    __tablename__ = "folder_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    folder_name = Column(String(100), nullable=False)
    can_read = Column(Boolean, default=True, nullable=False)
    can_write = Column(Boolean, default=False, nullable=False)
