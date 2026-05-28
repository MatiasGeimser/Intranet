from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from collections import defaultdict
import threading

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_seconds: int = 1, max_requests: int = 10):
        super().__init__(app)
        self.limit_seconds = limit_seconds
        self.max_requests = max_requests
        # Diccionario para almacenar accesos: {ip: [timestamps]}
        self.history = defaultdict(list)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Solo aplicar limitador de tasa a rutas API críticas (como login)
        path = request.url.path
        if not path.startswith("/api/auth"):
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.now()
        
        with self.lock:
            # Limpiar historial viejo de este cliente
            cutoff = now - timedelta(seconds=self.limit_seconds)
            self.history[client_ip] = [ts for ts in self.history[client_ip] if ts > cutoff]
            
            # Verificar si excede el límite
            if len(self.history[client_ip]) >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demasiadas peticiones. Por favor, espere antes de intentar de nuevo."}
                )
                
            # Registrar esta petición
            self.history[client_ip].append(now)
            
        return await call_next(request)
