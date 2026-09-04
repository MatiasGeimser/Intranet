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
from app.core.database_seed import ensure_delivery_record_signature_columns
from app.models.user import User
from app.models.delivery_record import DeliveryRecord
from app.services.natura_access import is_natura_manager
from app.services.delivery_record_access import is_delivery_records_only_user

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


def is_natura_user(user: User) -> bool:
    return bool(user.is_natura_user or (user.email and user.email.lower().endswith("@natura.cl")))


def has_full_scrum_access(user: User) -> bool:
    """Allows Administration and Sales supervisors to manage the Scrum Board."""
    return bool(
        user.role
        and user.role.name in {"Administrador", "Supervisor"}
        and user.area
        and user.area.name in {"Administración", "Administracion", "Ventas"}
    )


def can_manage_vault_folders(user: User) -> bool:
    return bool(
        user.role
        and user.role.name == "Administrador"
        and user.area
        and user.area.name in {"Administración", "Administracion"}
    )


def can_manage_delivery_records(user: User) -> bool:
    area_name = (user.area.name if user.area else "").strip().casefold()
    is_technology_user = user.role and user.role.name == "Usuario" and (
        area_name.startswith("tecnolog") or area_name == "it"
    )
    return bool(
        is_delivery_records_only_user(user)
        or (
        user.role
        and (
            user.role.name == "Administrador"
            or any(permission.code == "it:manage" for permission in user.role.permissions)
            or is_technology_user
        )
        )
    )


@router.get("/login", response_class=HTMLResponse)
def login_view(request: Request, db: Session = Depends(get_db)):
    """Muestra la página de inicio de sesión. Si ya tiene sesión, redirige al Dashboard."""
    user = get_current_user_optional(request, db)
    if user and user.is_active:
        if is_delivery_records_only_user(user):
            return RedirectResponse(url="/delivery-records")
        use_documents_home = is_natura_user(user) and not has_full_scrum_access(user)
        return RedirectResponse(url="/documents" if use_documents_home else "/dashboard")
    
    response = templates.TemplateResponse(request=request,name= "login.html", context={"project_name": settings.PROJECT_NAME})
    # Asegurar que se elimine cualquier cookie corrupta
    if not user:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
    return response


@router.get("/inventory-map", response_class=HTMLResponse)
async def inventory_map_view(request: Request, db: Session = Depends(get_db)):
    """Vista del Mapa Interactivo de Activos TI."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    return templates.TemplateResponse(request=request, name="inventory_map.html", context={
        "user": user,
        "active_page": "inventory-map",
        "project_name": settings.PROJECT_NAME
    })


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el Dashboard principal."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
    if is_natura_user(user) and not has_full_scrum_access(user):
        return RedirectResponse(url="/documents", status_code=status.HTTP_303_SEE_OTHER)

    full_scrum_access = has_full_scrum_access(user)
    limited_scrum_dashboard = not full_scrum_access and (
        is_natura_user(user) or is_natura_manager(db, user)
    )

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "active_page": "dashboard",
        "project_name": settings.PROJECT_NAME,
        "is_limited_scrum_dashboard": limited_scrum_dashboard,
        "can_manage_projects_and_daily_tasks": full_scrum_access,
    })


@router.get("/passwords", response_class=HTMLResponse)
def passwords_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el gestor de contraseñas de la Intranet."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    # Verificar si el rol tiene permiso
    permissions = [p.code for p in user.role.permissions]
    if user.role.name not in ["Administrador", "Usuario", "Supervisor"] and "credentials:manage" not in permissions:
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

    return templates.TemplateResponse(request=request, name="vault.html", context={
        "user": user,
        "active_page": "vault",
        "project_name": settings.PROJECT_NAME,
        "can_manage_vault_folders": can_manage_vault_folders(user),
    })


@router.get("/admin-chat", response_class=HTMLResponse)
def admin_chat_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el chat institucional y llamadas internas para el equipo operativo."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
    if user.role.name == "Usuario":
        return RedirectResponse(url="/passwords", status_code=303)

    response = templates.TemplateResponse(request=request, name="admin_chat.html", context={
        "user": user,
        "active_page": "admin-chat",
        "project_name": settings.PROJECT_NAME
    })
    # El chat contiene conversaciones privadas: nunca reutilizar una página anterior desde caché.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@router.get("/calendar", response_class=HTMLResponse)
def calendar_view(request: Request, db: Session = Depends(get_db)):
    """Muestra el calendario corporativo."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
        
    permissions = [p.code for p in user.role.permissions]
    if user.role.name != "Administrador" and not {"events:read", "events:manage"}.intersection(permissions):
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
    natura_manager = is_natura_manager(db, user)
    if not natura_manager and user.role.name not in ["Administrador", "Usuario"] and "documents:manage" not in permissions:
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse(request=request, name="documents.html", context={
        "user": user,
        "is_natura_manager": natura_manager,
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
    """Mantiene compatibilidad con enlaces antiguos de Inventario PC."""
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")

    permissions = [p.code for p in user.role.permissions]
    if user.role.name != "Administrador" and "it:manage" not in permissions:
        return RedirectResponse(url="/dashboard")

    return RedirectResponse(url="/network", status_code=303)


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
    natura_manager = bool(user and user.is_active and is_natura_manager(db, user))
    if not user or not user.is_active or (user.role.name not in {"Administrador", "Supervisor"} and not natura_manager):
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "user": user,
        "is_natura_manager": natura_manager,
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


@router.get("/delivery-records", response_class=HTMLResponse)
def delivery_records_view(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
    if not can_manage_delivery_records(user):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="delivery_records.html", context={
        "user": user,
        "active_page": "delivery-records",
        "project_name": settings.PROJECT_NAME,
    })


@router.get("/my-delivery-records", response_class=HTMLResponse)
def my_delivery_records_view(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="my_delivery_records.html", context={
        "user": user,
        "active_page": "my-delivery-records",
        "project_name": settings.PROJECT_NAME,
    })


@router.get("/delivery-records/{record_id}/firma-terreno", response_class=HTMLResponse)
def field_delivery_signature(record_id: int, request: Request, db: Session = Depends(get_db)):
    import json

    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
    if not can_manage_delivery_records(user):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    ensure_delivery_record_signature_columns(db)
    record = db.query(DeliveryRecord).filter(DeliveryRecord.id == record_id).first()
    if not record or record.status == "signed":
        return RedirectResponse(url="/delivery-records", status_code=status.HTTP_303_SEE_OTHER)

    def parse_json(value, fallback):
        try:
            return json.loads(value or "")
        except (TypeError, json.JSONDecodeError):
            return fallback

    return templates.TemplateResponse(request=request, name="delivery_signature.html", context={
        "record": record,
        "token": None,
        "signature_endpoint": f"/api/delivery-records/{record.id}/sign-field",
        "accessories": parse_json(record.accessories_json, []),
        "migration_items": parse_json(record.migration_json, []),
        "returned_equipment": parse_json(record.returned_equipment_json, {}),
        "issuer_name": record.created_by.full_name if record.created_by else "GEIMSER",
        "field_agent_name": user.full_name,
        "project_name": settings.PROJECT_NAME,
        "invalid_link": False,
        "field_signature": True,
        "return_url": "/delivery-records",
    })


@router.get("/actas/{record_id}/firma", response_class=HTMLResponse)
def intranet_delivery_signature(record_id: int, request: Request, db: Session = Depends(get_db)):
    import json

    user = get_current_user_optional(request, db)
    if not user or not user.is_active:
        return RedirectResponse(url="/login")
    ensure_delivery_record_signature_columns(db)
    record = db.query(DeliveryRecord).filter(DeliveryRecord.id == record_id).first()
    is_recipient = bool(
        record
        and record.status != "signed"
        and record.recipient_email
        and user.email
        and record.recipient_email.strip().casefold() == user.email.strip().casefold()
    )
    if not is_recipient:
        return RedirectResponse(url="/my-delivery-records", status_code=status.HTTP_303_SEE_OTHER)

    def parse_json(value, fallback):
        try:
            return json.loads(value or "")
        except (TypeError, json.JSONDecodeError):
            return fallback

    return templates.TemplateResponse(request=request, name="delivery_signature.html", context={
        "record": record,
        "token": None,
        "signature_endpoint": f"/api/delivery-records/{record.id}/sign-intranet",
        "accessories": parse_json(record.accessories_json, []),
        "migration_items": parse_json(record.migration_json, []),
        "returned_equipment": parse_json(record.returned_equipment_json, {}),
        "issuer_name": record.created_by.full_name if record.created_by else "GEIMSER",
        "field_agent_name": None,
        "project_name": settings.PROJECT_NAME,
        "invalid_link": False,
        "field_signature": False,
        "return_url": "/my-delivery-records",
    })


@router.get("/actas/firma/{token}", response_class=HTMLResponse)
def public_delivery_signature(token: str, request: Request, db: Session = Depends(get_db)):
    import hashlib
    import json
    from datetime import datetime, timezone

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    ensure_delivery_record_signature_columns(db)
    record = db.query(DeliveryRecord).filter(DeliveryRecord.signature_token_hash == token_hash).first()
    valid = bool(
        record
        and record.status != "signed"
        and record.signature_expires_at.replace(tzinfo=timezone.utc) >= datetime.now(timezone.utc)
    )
    def parse_json(value, fallback):
        try:
            return json.loads(value or "")
        except (TypeError, json.JSONDecodeError):
            return fallback

    return templates.TemplateResponse(request=request, name="delivery_signature.html", context={
        "record": record if valid else None,
        "token": token if valid else None,
        "signature_endpoint": f"/api/delivery-records/sign/{token}" if valid else None,
        "accessories": parse_json(record.accessories_json, []) if valid else [],
        "migration_items": parse_json(record.migration_json, []) if valid else [],
        "returned_equipment": parse_json(record.returned_equipment_json, {}) if valid else {},
        "issuer_name": record.created_by.full_name if valid and record.created_by else "GEIMSER",
        "field_agent_name": None,
        "project_name": settings.PROJECT_NAME,
        "invalid_link": not valid,
        "field_signature": False,
        "return_url": None,
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

