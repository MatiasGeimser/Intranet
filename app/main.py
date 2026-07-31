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
from app.middlewares.role_access import RoleAccessMiddleware
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import auth, users, roles, credentials, events, documents, news, audit, dashboard, views, it_assets, vlans, network_devices, phone_numbers, tasks, notes, areas, duplicate_phones, collaborators, search, inventory_map, admin_chat

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

# Restrict operational modules for non-administrator users.
app.add_middleware(RoleAccessMiddleware)

# 4. Registrar Middleware CORS para permitir Zammad
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "https://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Asegurar que existan los directorios de subida y estáticos de forma segura (tolerante a entornos read-only)
try:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join("app", "static"), exist_ok=True)
except Exception as e:
    print(f"====== AVISO: No se pudieron crear los directorios estáticos: {e} ======")

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
app.include_router(notes.router, prefix="/api/notes", tags=["Gestión de Notas"])
app.include_router(areas.router, prefix="/api/areas", tags=["Gestión de Áreas"])
app.include_router(duplicate_phones.router, prefix="/api/duplicate-phones", tags=["Limpieza de Teléfonos"])
app.include_router(collaborators.router, prefix="/api/collaborators", tags=["Directorio Corporativo"])
app.include_router(search.router, prefix="/api/search", tags=["Búsqueda Global"])
app.include_router(inventory_map.router, tags=["Mapa de Inventario"])
app.include_router(admin_chat.router, prefix="/api/admin-chat", tags=["Chat Institucional"])

from app.services.scheduler_service import scheduler_service

# Evento de inicialización de Base de Datos
@app.on_event("startup")
def on_startup():
    """Siembra y configura automáticamente la base de datos local o Postgres."""
    if os.environ.get("VERCEL"):
        print("====== INTRANET SERVERLESS: se omite la siembra de arranque ======")
        return
    db = SessionLocal()
    try:
        seed_database(db)
        print("====== INTRANET DATABASE CONFIGURADA Y SEMBRADA CORRECTAMENTE ======")
    except Exception as e:
        print(f"====== ERROR AL SEMBRAR LA BASE DE DATOS: {e} ======")
    finally:
        db.close()
        
    # Iniciar el servicio de tareas programadas (schedulers)
    if not os.environ.get("VERCEL"):
        scheduler_service.start()

@app.on_event("shutdown")
def on_shutdown():
    """Detiene los servicios en segundo plano al apagar la aplicación."""
    if not os.environ.get("VERCEL"):
        scheduler_service.stop()
