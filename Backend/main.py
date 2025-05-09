# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings  # Configuración centralizada

# Importar routers de cada módulo
from app.ambassadors import router as ambassadors_router
from app.auth import router as auth_router
from app.business import router as business_router
from app.clients import router as clients_router
from app.distributors import router as distributors_router
from app.orders import router as orders_router
from app.payments import router as payments_router
from app.utils import router as utils_router

# Inicializar la aplicación FastAPI
app = FastAPI(
    title="Universe Backend API",
    description="API para el ecosistema Universe",
    version="1.0.0",
    openapi_url="/openapi.json" if settings.ENV != "production" else None  # Ocultar en producción
)

# Configurar CORS (ajusta según tus necesidades)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, reemplaza con tus dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir todos los routers
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(ambassadors_router, prefix="/api/ambassadors", tags=["Ambassadors"])
app.include_router(business_router, prefix="/api/business", tags=["Business"])
app.include_router(clients_router, prefix="/api/clients", tags=["Clients"])
app.include_router(distributors_router, prefix="/api/distributors", tags=["Distributors"])
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(payments_router, prefix="/api/payments", tags=["Payments"])
app.include_router(utils_router, prefix="/api/utils", tags=["Utils"])

# Health Check Endpoint
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Bienvenido a Universe Backend API",
        "environment": settings.ENV,
        "status": "running"
}