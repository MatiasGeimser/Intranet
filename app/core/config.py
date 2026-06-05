import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Intranet Corporativa Premium"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    
    # Base de datos
    DATABASE_URL: str = "sqlite:///intranet.db"
    
    # JWT
    SECRET_KEY: str = "supersecret_jwt_key_default"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AES key for credentials
    AES_SECRET_KEY: str = "wG5kM9sB4uD1xF7tP2zH8vC3qR0jA6eN1yI4mK7sQ9o="
    
    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Admin Inicial
    INITIAL_ADMIN_EMAIL: str = "admin@intranet.local"
    INITIAL_ADMIN_PASSWORD: str = "Admin12345!"

    # Carpetas para subida de archivos
    UPLOAD_DIR: str = os.path.join("static", "uploads")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: Optional[str]) -> str:
        if isinstance(v, str):
            v = v.strip()
            for prefix in ["DATABASE_URL=", "database_url=", "POSTGRES_URL=", "postgres_url="]:
                if v.lower().startswith(prefix.lower()):
                    v = v[len(prefix):].strip()

        if not v or (isinstance(v, str) and not v.strip()):
            postgres_url = os.environ.get("POSTGRES_URL")
            if postgres_url:
                postgres_url = postgres_url.strip()
                for prefix in ["POSTGRES_URL=", "postgres_url=", "DATABASE_URL=", "database_url="]:
                    if postgres_url.lower().startswith(prefix.lower()):
                        postgres_url = postgres_url[len(prefix):].strip()
                v = postgres_url
            else:
                if os.environ.get("VERCEL"):
                    v = "sqlite:////tmp/intranet.db"
                else:
                    v = "sqlite:///intranet.db"

        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql://", 1)
            elif "intranet.db" in v and os.environ.get("VERCEL"):
                v = "sqlite:////tmp/intranet.db"
        return v

    @field_validator("UPLOAD_DIR", mode="before")
    @classmethod
    def validate_upload_dir(cls, v: str) -> str:
        if os.environ.get("VERCEL"):
            return "/tmp/uploads"
        return v

settings = Settings()

# Asegurar que el directorio de subidas exista de forma segura (tolerante a entornos read-only)
try:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
except Exception as e:
    print(f"====== AVISO: No se pudo crear el directorio de subidas: {e} ======")
