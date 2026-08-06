from jose import JWTError, jwt
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.deps import get_token_from_request
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.services.natura_access import is_natura_manager
from sqlalchemy.orm import joinedload, selectinload


class RoleAccessMiddleware(BaseHTTPMiddleware):
    """Limita a usuarios no administradores a los tres modulos autorizados."""

    public_paths = {"/", "/login", "/favicon.ico"}
    member_pages = {"/passwords", "/vault", "/directory", "/profile"}
    chat_roles = {"Administrador", "Supervisor"}

    @staticmethod
    def _is_natura_user(user: User) -> bool:
        return bool(user.is_natura_user or (user.email and user.email.lower().endswith("@natura.cl")))

    @staticmethod
    def _has_full_scrum_access(user: User) -> bool:
        return bool(
            user.role
            and user.role.name in {"Administrador", "Supervisor"}
            and user.area
            and user.area.name in {"Administración", "Administracion", "Ventas"}
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self.public_paths or path.startswith("/static"):
            return await call_next(request)

        token = get_token_from_request(request)
        if not token:
            return await call_next(request)

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = int(payload.get("sub"))
            if payload.get("type") != "access":
                raise ValueError("Invalid token type")
        except (JWTError, TypeError, ValueError):
            return await call_next(request)

        db = SessionLocal()
        try:
            user = (
                db.query(User)
                .options(joinedload(User.role), selectinload(User.folder_permissions))
                .filter(User.id == user_id, User.is_active.is_(True))
                .first()
            )
            if not user or user.role.name == "Administrador":
                return await call_next(request)

            if self._has_full_scrum_access(user) and self._is_allowed_full_scrum_request(request):
                return await call_next(request)

            if is_natura_manager(db, user):
                if self._is_allowed_natura_manager_request(request):
                    return await call_next(request)
                if path.startswith("/api/"):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Los responsables Natura solo tienen acceso a Gestión Documental."},
                    )
                return RedirectResponse(url="/documents", status_code=303)

            if self._is_natura_user(user):
                if self._is_allowed_natura_request(request):
                    return await call_next(request)
                if path.startswith("/api/"):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Las cuentas Natura solo tienen acceso a Gestión Documental."},
                    )
                return RedirectResponse(url="/documents", status_code=303)
        finally:
            db.close()

        if self._is_allowed_member_request(request, user):
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse(
                status_code=403,
                content={"detail": "Este recurso es exclusivo para administradores."},
            )

        return RedirectResponse(url="/passwords", status_code=303)

    @staticmethod
    def _is_allowed_natura_request(request: Request) -> bool:
        path = request.url.path
        method = request.method

        if path.startswith("/api/auth/"):
            return True
        return path == "/documents" or (path.startswith("/api/documents") and method == "GET")

    @staticmethod
    def _is_allowed_full_scrum_request(request: Request) -> bool:
        path = request.url.path
        method = request.method
        is_task_collection = path.rstrip("/") == "/api/tasks"
        is_task_comment = path.startswith("/api/tasks/") and path.endswith("/comments")
        return (
            path in {"/", "/dashboard"}
            or (
                path.startswith("/api/notes")
                and method in {"GET", "POST", "DELETE"}
            )
            or (path == "/api/users/list-minimal" and method == "GET")
            or (
                path.startswith("/api/tasks")
                and (
                    method in {"GET", "PUT", "DELETE"}
                    or (method == "POST" and (is_task_collection or is_task_comment))
                )
            )
        )

    @staticmethod
    def _is_allowed_natura_manager_request(request: Request) -> bool:
        path = request.url.path
        return (
            path.startswith("/api/auth/")
            or path in {"/documents", "/admin"}
            or path.startswith("/api/documents")
            or path.startswith("/api/users")
            or path.startswith("/api/areas")
            or path.startswith("/api/roles")
        )

    @staticmethod
    def _is_allowed_member_request(request: Request, user: User) -> bool:
        path = request.url.path
        method = request.method
        role_name = user.role.name

        if role_name in RoleAccessMiddleware.chat_roles and (
            path == "/admin-chat" or path.startswith("/api/admin-chat")
        ):
            return True
        if role_name == "Supervisor" and (path == "/admin" or path.startswith("/api/users") or path.startswith("/api/areas") or path.startswith("/api/roles")):
            return True
        if path in {"/", "/dashboard"}:
            return True
        if path == "/calendar" or (path.startswith("/api/events") and method == "GET"):
            return True
        if path.startswith("/api/notes") and method == "GET":
            return True
        if path.startswith("/api/tasks") and (
            method in {"GET", "PUT"}
            or (method == "POST" and path.startswith("/api/tasks/") and path.endswith("/comments"))
        ):
            return True
        if path in RoleAccessMiddleware.member_pages:
            return True
        if path.startswith("/api/auth/"):
            return True
        if path.startswith("/api/collaborators") and method == "GET":
            return True
        if path == "/documents" or (
            path.startswith("/api/documents")
            and (method == "GET" or any(permission.can_write for permission in user.folder_permissions))
        ):
            return True
        if path.startswith("/api/credentials") and method == "GET":
            return True
        if path == "/api/users/me" and method in {"GET", "PUT"}:
            return True
        return False
