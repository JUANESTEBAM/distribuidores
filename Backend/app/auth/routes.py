
from fastapi import APIRouter, HTTPException, Form
from datetime import datetime, timedelta
from app.core.security import create_access_token, pwd_context, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordBearer
from fastapi import status
from app.auth.models import TokenResponse
from jose import jwt, JWTError
from fastapi import Depends
from app.core.database import (
    collection_admin,
    collection_distribuidores,
    collection_produccion,
    collection_facturas
)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        rol: str = payload.get("rol")
        
        if not email or not rol:
            raise credentials_exception
        return {"email": email, "rol": rol}
    except jwt.PyJWTError:
        raise credentials_exception

@router.post("/token", response_model=TokenResponse)
async def login(
    username: str = Form(...),  # Correo electrónico
    password: str = Form(...)   # Contraseña
):
    user = None  # Inicializamos la variable user
    rol = None   # Inicializamos el rol del usuario

    # Buscar en todas las colecciones
    collections = [
        (collection_admin, "collection_admin"),
        (collection_distribuidores, "collection_distribuidores"),
        (collection_produccion, "collection_produccion"),
        (collection_facturas, "collection_facturas")
    ]
    print("Iniciando búsqueda de usuario en las colecciones...")
    for collection, name in collections:
        try:
            print(f"Buscando en {name} para el usuario: {username}")
            user = await collection.find_one({"correo_electronico": username})
            if user:
                print(f"Usuario encontrado en {name}: {user}")
                rol = user.get("rol")
                break
            else:
                print(f"Usuario no encontrado en {name}")
        except Exception as e:
            print(f"Error al conectar o buscar en {name}: {e}")

    # Si no se encontró en ninguna colección
    if not user:
        print("Usuario no encontrado en ninguna colección.")
        raise HTTPException(status_code=400, detail="Usuario no encontrado.")

    # Verificar la contraseña
    try:
        if not pwd_context.verify(password, user.get("hashed_password")):
            print("Contraseña incorrecta para el usuario.")
            raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
        else:
            print("Contraseña verificada correctamente.")
    except Exception as e:
        print(f"Error al verificar la contraseña: {e}")
        raise HTTPException(status_code=500, detail="Error interno al verificar la contraseña.")

    # Actualizar la fecha de último acceso
    try:
        print("Actualizando fecha de último acceso...")
        await collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"fecha_ultimo_acceso": datetime.now().strftime("%Y-%m-%d %H:%M")}}
        )
        print("Fecha de último acceso actualizada.")
    except Exception as e:
        print(f"Error al actualizar la fecha de último acceso: {e}")

    # Crear el token de acceso
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["correo_electronico"], "rol": rol, "nombre": user.get("nombre"), "pais": user.get("pais")},
        expires_delta=access_token_expires
    )
    print("Token de acceso generado correctamente.")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        rol=rol,
        nombre=user.get("nombre"),
        pais=user.get("pais"),
        email=user.get("correo_electronico")
    )

@router.get("/validate_token")
async def validate_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"valid": True, "exp": payload.get("exp")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
