from sqlalchemy.orm import Session
from typing import Optional
from app.core.security import encrypt_aes, decrypt_aes
from app.services.audit_service import audit_service

class CryptoService:
    @staticmethod
    def encrypt_password(password: str) -> str:
        """Encripta una contraseña usando AES-256-GCM."""
        return encrypt_aes(password)

    @staticmethod
    def decrypt_password(
        encrypted_password: str,
        db: Session,
        user_id: int,
        credential_id: int,
        ip_address: Optional[str] = None
    ) -> str:
        """Desencripta la contraseña y genera un registro de auditoría obligatorio."""
        decrypted = decrypt_aes(encrypted_password)
        
        # Registrar el acceso a la credencial por auditoría de ciberseguridad
        audit_service.log_action(
            db=db,
            user_id=user_id,
            action="credential_decrypt",
            ip_address=ip_address,
            details=f"Desencriptó la contraseña de la credencial con ID {credential_id}"
        )
        
        return decrypted

crypto_service = CryptoService()
