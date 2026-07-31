import os
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings


def get_runtime_database_url() -> str:
    """Use Supavisor transaction mode for Vercel's short-lived functions."""
    database_url = settings.DATABASE_URL
    if os.environ.get("VERCEL") and "pooler.supabase.com" in database_url:
        parsed = urlsplit(database_url)
        if parsed.port == 5432:
            hostname = parsed.hostname or ""
            auth = ""
            if parsed.username:
                auth = parsed.username
                if parsed.password:
                    auth += f":{parsed.password}"
                auth += "@"
            netloc = f"{auth}{hostname}:6543"
            database_url = urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    return database_url


runtime_database_url = get_runtime_database_url()

# Determinar si estamos usando SQLite
is_sqlite = runtime_database_url.startswith("sqlite")

# Configurar argumentos de conexión
connect_args = {}
if is_sqlite:
    # Evitar problemas de múltiples hilos en SQLite
    connect_args = {"check_same_thread": False}
else:
    connect_args = {
        "connect_timeout": 10,
        "sslmode": "require",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 3,
    }

# Crear motor de base de datos
engine = create_engine(
    runtime_database_url,
    connect_args=connect_args,
    pool_pre_ping=True  # Verifica si la conexión está viva antes de usarla
)

# Las funciones serverless no deben retener conexiones entre invocaciones.
if os.environ.get("VERCEL"):
    engine = create_engine(
        runtime_database_url,
        connect_args=connect_args,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

# Creador de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para modelos
Base = declarative_base()

def get_db():
    """Generador de sesiones de base de datos para dependencias de FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
