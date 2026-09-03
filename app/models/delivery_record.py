from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class DeliveryRecord(Base):
    """Acta digital de entrega y recepción de equipamiento."""

    __tablename__ = "delivery_records"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(32), unique=True, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    collaborator_id = Column(Integer, ForeignKey("collaborators.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(24), nullable=False, default="pending_signature")

    delivery_date = Column(Date, nullable=False)
    site = Column(String(120), nullable=True)
    recipient_name = Column(String(140), nullable=False)
    recipient_email = Column(String(140), nullable=True)
    recipient_run = Column(String(32), nullable=True)
    recipient_role = Column(String(120), nullable=True)
    recipient_unit = Column(String(120), nullable=True)
    employment_type = Column(String(32), nullable=True)

    equipment_type = Column(String(32), nullable=False)
    equipment_brand_model = Column(String(160), nullable=True)
    equipment_hostname = Column(String(120), nullable=True)
    equipment_serial = Column(String(120), nullable=True)
    mac_address = Column(String(64), nullable=True)
    monitor_serial = Column(String(120), nullable=True)
    dock_serial = Column(String(120), nullable=True)
    accessories_json = Column(Text, nullable=False, default="[]")
    delivery_condition = Column(String(32), nullable=True)
    label_number = Column(String(64), nullable=True)
    migration_json = Column(Text, nullable=False, default="[]")

    returned_equipment_json = Column(Text, nullable=False, default="{}")
    observations = Column(Text, nullable=True)

    signature_token_hash = Column(String(64), unique=True, nullable=False, index=True)
    signature_expires_at = Column(DateTime, nullable=False)
    delivery_signature_data = Column(Text, nullable=True)
    delivery_signer_name = Column(String(140), nullable=True)
    recipient_signature_data = Column(Text, nullable=True)
    recipient_signer_name = Column(String(140), nullable=True)
    technician_signature_data = Column(Text, nullable=True)
    technician_signer_name = Column(String(140), nullable=True)
    recipient_signed_at = Column(DateTime, nullable=True)
    recipient_signature_ip = Column(String(64), nullable=True)
    content_hash = Column(String(64), nullable=False)
    signed_document_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_by = relationship("User", foreign_keys=[created_by_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
    collaborator = relationship("Collaborator", foreign_keys=[collaborator_id])
