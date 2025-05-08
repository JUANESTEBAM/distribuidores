from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client["universe"]

# Colecciones (centralizadas en un solo lugar)
class Collections:
    clients = db["client"]
    ambassadors = db["ambassador"]
    transactions = db["transacciones"]
    orders = db["pedidos"]
    wallets = db["wallet"]
    businesses = db["negocios"]
    grand_distributors = db["grandistribuidor"]
    distributors = db["distribuidor"]

# Ejemplo de uso en otros archivos:
# from app.core.database import Collections
# await Collections.ambassadors.find_one(...)