from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        
        # 1. Protección contra Clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # 2. Protección contra Sniffing de MIME-type
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 3. Control de Referencia
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 4. HSTS (HTTP Strict Transport Security) - Habilitar en HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # 5. Content Security Policy (CSP) simplificada y adaptada para estáticos y Tailwind CDN
        # NOTA: En producción real, CSP debe ser más estricta. Aquí permitimos fuentes CDN estándar para facilitar carga.
        csp_policies = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https://images.unsplash.com; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policies
        
        return response
