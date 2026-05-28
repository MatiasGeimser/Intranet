from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Determinar si estamos usando SQLite
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Configurar argumentos de conexión
connect_args = {}
if is_sqlite:
    # Evitar problemas de múltiples hilos en SQLite
    connect_args = {"check_same_thread": False}

# Crear motor de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True  # Verifica si la conexión está viva antes de usarla
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
