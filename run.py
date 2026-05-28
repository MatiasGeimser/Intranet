import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    # Inicia el servidor de desarrollo local de FastAPI
    print(f"Iniciando {settings.PROJECT_NAME} en http://localhost:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True  # Recarga automática en cambios de código
    )
