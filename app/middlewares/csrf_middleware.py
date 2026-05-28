from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
import secrets

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Rutas exentas de verificación de CSRF (Login, etc.)
        exempt_paths = [
            "/api/auth/login",
            "/api/auth/recover-password",
            "/api/auth/reset-password"
        ]
        
        path = request.url.path
        if path in exempt_paths or path.startswith("/static"):
            return await call_next(request)
            
        # Si la petición es mutable, verificamos el token CSRF
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Obtener el token CSRF de la cookie
            csrf_cookie = request.cookies.get("csrf_token")
            
            # Obtener el token de las cabeceras
            csrf_header = request.headers.get("x-csrf-token")
            
            # Si no hay cookie de CSRF, rechazamos la petición
            if not csrf_cookie:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Falta la cookie de seguridad CSRF (CSRF cookie missing)."}
                )
                
            # Verificar si coincide
            if not csrf_header or csrf_header != csrf_cookie:
                # Comprobar si viene en el cuerpo del formulario
                # En FastAPI, leer form puede colgar la petición en un middleware asíncrono si no se maneja bien,
                # por lo que preferimos validar vía cabecera 'x-csrf-token' (estándar para peticiones fetch/SPA).
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Token CSRF inválido o ausente. Seguridad comprometida."}
                )
                
        response = await call_next(request)
        
        # Si no existe la cookie csrf_token, la creamos para las próximas peticiones
        if not request.cookies.get("csrf_token"):
            token = secrets.token_hex(32)
            # Cookie de sesión segura para el cliente JS (SameSite=Lax para permitir peticiones del mismo sitio)
            response.set_cookie(
                key="csrf_token",
                value=token,
                httponly=False,  # Permitir leer al JS para meterlo en la cabecera 'x-csrf-token'
                samesite="lax",
                secure=False  # Cambiar a True en producción con HTTPS
            )
            
        return response
