from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class PCLoginHistory(Base):
    __tablename__ = "pc_login_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("it_assets.id", ondelete="CASCADE"), nullable=False)
    username_reported = Column(String(150), nullable=False, index=True) # E.g., domain\\user or email
    logged_in_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    asset = relationship("ITAsset")
