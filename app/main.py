from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.database_seed import seed_database

# Importar Middlewares de Seguridad
from app.middlewares.security_headers import SecurityHeadersMiddleware
from app.middlewares.csrf_middleware import CSRFMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware

from app.api.endpoints import auth, users, roles, credentials, events, documents, news, audit, dashboard, views, it_assets, vlans, network_devices, phone_numbers, tasks

# Crear Aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intranet Corporativa de Alta Seguridad y Diseño Premium",
    version="1.0.0"
)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print("\n❌ ====== ERROR DE VALIDACIÓN DETECTADO ======")
    print(exc.errors())
    print("=============================================\n")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# 1. Registrar Middleware de Cabeceras de Seguridad (Clickjacking, CSP, XSS, nosniff)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Registrar Middleware de Protección contra CSRF
app.add_middleware(CSRFMiddleware)

# 3. Registrar Middleware de Rate Limiting (Mitigación Fuerza Bruta)
# Permite un máximo de 20 peticiones cada 2 segundos para APIs críticas
app.add_middleware(RateLimitMiddleware, limit_seconds=2, max_requests=20)

# Asegurar que existan los directorios de subida y estáticos
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join("app", "static"), exist_ok=True)

# Montar carpeta estática
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Incluir Rutas del Frontend Jinja2 (sin prefijo para navegar la web)
app.include_router(views.router, tags=["Vistas Frontend"])

# Incluir Rutas del API REST (con prefijos específicos)
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(users.router, prefix="/api/users", tags=["Usuarios"])
app.include_router(roles.router, prefix="/api/roles", tags=["Roles & Permisos"])
app.include_router(credentials.router, prefix="/api/credentials", tags=["Bóveda Contraseñas"])
app.include_router(events.router, prefix="/api/events", tags=["Calendario Corporativo"])
app.include_router(documents.router, prefix="/api/documents", tags=["Gestión Documental"])
app.include_router(news.router, prefix="/api/news", tags=["Noticias & Comunicados"])
app.include_router(audit.router, prefix="/api/audit", tags=["Auditoría Forense"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard Analítica"])
app.include_router(it_assets.router, prefix="/api/it-assets", tags=["Inventario IT"])
app.include_router(vlans.router, prefix="/api/vlans", tags=["Gestión de VLANs"])
app.include_router(network_devices.router, prefix="/api/switches", tags=["Dispositivos de Red"])
app.include_router(phone_numbers.router, prefix="/api/phone-numbers", tags=["Números Contratados"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Gestión de Tareas Diarias"])


# Evento de inicialización de Base de Datos
@app.on_event("startup")
def on_startup():
    """Siembra y configura automáticamente la base de datos local o Postgres."""
    db = SessionLocal()
    try:
        seed_database(db)
        print("====== INTRANET DATABASE CONFIGURADA Y SEMBRADA CORRECTAMENTE ======")
    except Exception as e:
        print(f"====== ERROR AL SEMBRAR LA BASE DE DATOS: {e} ======")
    finally:
        db.close()
