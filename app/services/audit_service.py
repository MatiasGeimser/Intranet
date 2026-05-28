from sqlalchemy.orm import Session
from typing import Optional
from app.models.audit import AuditLog

class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[int],
        action: str,
        ip_address: Optional[str] = None,
        details: Optional[str] = None
    ) -> AuditLog:
        """Registra un evento de seguridad o acción de usuario en la base de datos."""
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            details=details
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry

audit_service = AuditService()
