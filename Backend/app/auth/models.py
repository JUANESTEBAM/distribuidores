from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    nombre: str
    pais: str
    correo_electronico: str
    phone: str
    password: str
    rol: str
    tipo_precio: Optional[str] = None  # Solo para distribuidores

class UserResponse(BaseModel):
    id: str
    nombre: str
    correo_electronico: str
    phone: str
    rol: str
    estado: str
    fecha_ultimo_acceso: str
    admin_id: str
    tipo_precio: Optional[str] = None
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str
    pais: str
    email: str