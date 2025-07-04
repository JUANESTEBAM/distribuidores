from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class ProductCreate(BaseModel):
    nombre: str
    categoria: str
    precio_sin_iva_colombia: float
    precio_con_iva_colombia: float
    precio_internacional: float
    stock: int
    margen_descuento: float = 0.45
    codigo_tipo: Optional[int] = None

    class Config:
        json_encoders = {
            float: lambda v: round(v, 2),
        }
        
# MODELO PARA RESPUESTA DE PRODUCTOS
class PreciosUpdate(BaseModel):
    sin_iva_colombia: Optional[int] = None
    con_iva_colombia: Optional[int] = None
    internacional: Optional[int] = None
    fecha_actualizacion: Optional[datetime] = None

class MargenesUpdate(BaseModel):
    descuento: Optional[float] = None
    tipo_codigo: Optional[int] = None

class ProductoUpdate(BaseModel):
    id: Optional[str] = None
    admin_id: Optional[str] = None
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    precios: Optional[PreciosUpdate] = None
    margenes: Optional[MargenesUpdate] = None
    stock: Optional[int] = None
    activo: Optional[bool] = None
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None