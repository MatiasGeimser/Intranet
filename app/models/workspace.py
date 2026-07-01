from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.it_asset import ITAsset
class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True) # P1, P2...
    pos_x = Column(Float, nullable=False, default=0.0)
    pos_y = Column(Float, nullable=False, default=0.0)
    
    # Optional assignment to a user and/or an IT Asset
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    temp_user_name = Column(String(100), nullable=True)
    asset_id = Column(Integer, ForeignKey("it_assets.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", backref="workspace")
    asset = relationship("ITAsset", backref="workspace")
