from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    nombre: str
    pais: str
    correo_electronico: EmailStr
    phone: str = Field(..., min_length=7, max_length=15)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    rol: str = Field(..., description="Rol del usuario: distribuidor, produccion, facturacion")
    tipo_precio: Optional[str] = Field(
        None,
        description="Solo para distribuidores: sin_iva, con_iva, sin_iva_internacional"
    )

# MODELO DE RESPUESTA PARA USUARIOS
class UserResponse(BaseModel):
    id: str
    nombre: str
    correo_electronico: str
    rol: str
    phone: str
    estado: str
    fecha_ultimo_acceso: str
    admin_id: str | None = None  # Puede ser opcional
    tipo_precio: str | None = None  # Puede ser opcional

class AdminCreate(BaseModel):
    nombre: str
    pais: str
    whatsapp: str
    correo_electronico: EmailStr
    password: str = Field(..., min_length=8)
    rol: str = Field(..., description="Rol del admin: Admin")

class DistribuidorCreate(UserBase):
    password: str = Field(..., min_length=8)
    admin_id: str
    
class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    correo_electronico: Optional[str] = None
    rol: Optional[str] = None
    phone: Optional[str] = None
    estado: Optional[str] = None
    tipo_precio: Optional[str] = None
    contrasena: Optional[str] = None


