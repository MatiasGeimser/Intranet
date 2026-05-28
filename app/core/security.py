import os
import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt
import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

    #  Código nuevo directo con bcrypt (Sin depender de passlib)
def get_password_hash(password: str) -> str:
    # Convierte el string de la contraseña a bytes
    password_bytes = password.encode('utf-8')
    # Genera la sal (salt) automáticamente
    salt = bcrypt.gensalt()
    # Genera el hash y lo vuelve a convertir a string para guardarlo en la BD
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')

#  Código nuevo
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

# --- SISTEMA DE ENCRIPCIÓN AES-256-GCM PARA CREDENCIALES ---

def _get_aes_key() -> bytes:
    """Decodifica la clave AES desde base64. Genera una de respaldo si hay un error."""
    try:
        # Intentar decodificar en base64
        key = base64.b64decode(settings.AES_SECRET_KEY)
        if len(key) == 32:
            return key
    except Exception:
        pass
    # Si falla, derivar una clave de 32 bytes de forma determinista usando el secret key
    derived = settings.SECRET_KEY.ljust(32)[:32]
    return derived.encode("utf-8")

def encrypt_aes(plain_text: str) -> str:
    """Encripta texto usando AES-256-GCM y retorna el resultado en Base64."""
    if not plain_text:
        return ""
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # Nonce estándar de 12 bytes para GCM
    encrypted = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
    # Guardamos nonce + ciphertext
    return base64.b64encode(nonce + encrypted).decode("utf-8")

def decrypt_aes(encrypted_b64: str) -> str:
    """Desencripta texto codificado en Base64 usando AES-256-GCM."""
    if not encrypted_b64:
        return ""
    try:
        key = _get_aes_key()
        aesgcm = AESGCM(key)
        data = base64.b64decode(encrypted_b64)
        if len(data) < 12:
            return "[Error: Datos corruptos]"
        nonce = data[:12]
        ciphertext = data[12:]
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")
    except Exception as e:
        return f"[Error al desencriptar: Clave inválida o datos corruptos]"

# --- TOKENS JWT DE AUTENTICACIÓN ---

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT de acceso."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT de refresco."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """Verifica un token JWT y retorna el subject (user_id) si es válido."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None
