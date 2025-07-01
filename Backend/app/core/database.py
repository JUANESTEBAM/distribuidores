from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("MONGODB_URI")
db_name = os.getenv("MONGODB_NAME", "DatabaseInvetary")

if not uri:
    raise RuntimeError("MONGODB_URI no está definida en .env")

client = AsyncIOMotorClient(uri)
db = client[db_name]
collection_productos = db["productos"]
collection_pedidos = db["pedidos"]
collection_distribuidores = db["distribuidores"]
collection_facturas = db["facturadores"]
collection_produccion = db["produccion"]
collection_admin = db["admin"]

def connect_to_mongo():
    pass
