from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
import os
from typing import Optional
from app.core.database import get_db
from app.api.deps import get_token_from_request
from jose import jwt
from app.core.config import settings
from app.models.user import User

router = APIRouter()

# Configurar motor de plantillas Jinja2 con Environment manual
# (Fix de compatibilidad: Starlette 1.2.0 + Jinja2 + Python 3.14 tienen un bug
#  en la caché LRU cuando se usa el constructor directo con 'directory')
_jinja_env = Environment(
    loader=FileSystemLoader(os.path.join("app", "templates")),
    autoescape=True
)
templates = Jinja2Templates(env=_jinja_env)

def get_current_user_optional(request: Request, db: Session) -> Optional[User]:
    """Obtiene el usuario en sesión si el token es válido, sin lanzar excepciones."""
    token = get_token_from_request(request)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


@router.get("/login", response_class=HTMLResponse)
def login_view(request: Request, db: Session = Depends(get_db)):
    """Muestra la página de inicio de sesión. Si ya tiene sesión, redirige al Dashboard."""
    user = get_current_user_optional(request, db)
    if user and user.is_active:
        return RedirectResponse(url="/dashboard")
    
    response = templates.TemplateResponse(request=request,name= "login.html", context={"project_name": settings.PROJECT_NAME})
    # Asegurar que se elimine cualquier cookie corrupta
    if not user:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
    return response


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el Dashboard principal."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "active_page": "dashboard",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/passwords", response_class=HTMLResponse)
def passwords_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el gestor de contraseñas de la Intranet."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    # Verificar si el rol tiene permiso
    permissions = [p.code for p in user.role.permissions]
    if user.role.name not in ["Administrador", "Usuario"] and "credentials:manage" not in permissions:
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse(request=request, name="passwords.html", context={
        "user": user,
        "active_page": "passwords",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/vault", response_class=HTMLResponse)
def vault_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el gestor de contraseñas generales (Bóveda)."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")

    permissions = [p.code for p in user.role.permissions]
    if user.role.name != "Administrador" and "credentials:manage" not in permissions:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(request=request, name="vault.html", context={
        "user": user,
        "active_page": "vault",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/calendar", response_class=HTMLResponse)
def calendar_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el calendario corporativo."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    permissions = [p.code for p in user.role.permissions]
    if user.role.name not in ["Administrador", "Usuario"] and "events:manage" not in permissions:
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse(request=request, name="calendar.html", context={
        "user": user,
        "active_page": "calendar",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/documents", response_class=HTMLResponse)
def documents_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el gestor documental virtualizado."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    permissions = [p.code for p in user.role.permissions]
    if user.role.name not in ["Administrador", "Usuario"] and "documents:manage" not in permissions:
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse(request=request, name="documents.html", context={
        "user": user,
        "active_page": "documents",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/directory", response_class=HTMLResponse)
def directory_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el Directorio Corporativo."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    return templates.TemplateResponse(request=request, name="directory.html", context={
        "user": user,
        "active_page": "directory",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/news", response_class=HTMLResponse)
def news_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el portal de comunicación y noticias corporativas."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    permissions = [p.code for p in user.role.permissions]
    if user.role.name not in ["Administrador", "Usuario"] and "news:manage" not in permissions:
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse(request=request, name="news.html", context={
        "user": user,
        "active_page": "news",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/it-assets", response_class=HTMLResponse)
def it_assets_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el módulo de inventario IT (Software, Hardware, Redes)."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")

    permissions = [p.code for p in user.role.permissions]
    if user.role.name != "Administrador" and "it:manage" not in permissions:
        return RedirectResponse(url="/dashboard")

    all_users = db.query(User).filter(User.is_active == True).all()

    return templates.TemplateResponse(request=request, name="it_assets.html", context={
        "user": user,
        "all_users": all_users,
        "active_page": "it-assets",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/profile", response_class=HTMLResponse)
def profile_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el perfil y configuración del usuario actual."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    return templates.TemplateResponse(request=request, name="profile.html", context={
        "user": user,
        "active_page": "profile",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/admin", response_class=HTMLResponse)
def admin_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el panel de administración global (Solo Administrador)."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active or user.role.name != "Administrador":
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "user": user,
        "active_page": "admin",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/network", response_class=HTMLResponse)
def network_view(request: Request, db: Session = Depends(get_db)):
    """Muestra la gestión de dispositivos de red (Switches)."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")

    permissions = [p.code for p in user.role.permissions]
    if user.role.name != "Administrador" and "it:manage" not in permissions:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(request=request, name="network_devices.html", context={
        "user": user,
        "active_page": "network",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/phone-numbers", response_class=HTMLResponse)
def phone_numbers_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el módulo de números telefónicos contratados."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")

    permissions = [p.code for p in user.role.permissions]
    if user.role.name != "Administrador" and "it:manage" not in permissions:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(request=request, name="phone_numbers.html", context={
        "user": user,
        "active_page": "phone-numbers",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/excel-converter", response_class=HTMLResponse)
def excel_converter_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el módulo conversor de Excel a CSV de campos seleccionados."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")

    permissions = [p.code for p in user.role.permissions]
    if user.role.name != "Administrador" and "it:manage" not in permissions:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(request=request, name="excel_converter.html", context={
        "user": user,
        "active_page": "excel-converter",
        "project_name": settings.PROJECT_NAME
    })

@router.get("/duplicate-phones", response_class=HTMLResponse)
def duplicate_phones_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el módulo para eliminar teléfonos duplicados de un Excel."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")

    permissions = [p.code for p in user.role.permissions]
    if user.role.name != "Administrador" and "it:manage" not in permissions:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(request=request, name="duplicate_phones.html", context={
        "user": user,
        "active_page": "duplicate-phones",
        "project_name": settings.PROJECT_NAME
    })

