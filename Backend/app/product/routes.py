
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from bson import ObjectId
from bson.errors import InvalidId
from typing import Dict
from app.product.models import ProductCreate, ProductoUpdate
from datetime import datetime
from app.auth.routes import get_current_user
from app.core.database import collection_productos, collection_admin, collection_distribuidores

router = APIRouter()

# ENDPOINT PARA CREAR PRODUCTOS
@router.post("/productos/", status_code=status.HTTP_201_CREATED)
async def crear_producto(
    producto_data: dict,
    current_user: dict = Depends(get_current_user)
):
    print("📢 Iniciando creación de producto")

    # 1. Verificar permisos (solo admin)
    if current_user["rol"] != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden crear productos"
        )

    # 2. Validar datos
    try:
        producto = ProductCreate(**producto_data)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )

    # 3. Obtener admin
    admin = await collection_admin.find_one({"correo_electronico": current_user["email"]})
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrador no encontrado"
        )

    admin_id = str(admin["_id"])

    # 4. Generar ID secuencial desde la colección de productos
    ultimo_producto = await collection_productos.find_one(
        {"admin_id": admin_id},
        sort=[("id", -1)]  # Ordena por ID descendente
    )

    # Calcula nuevo ID (P001, P002...)
    ultimo_num = int(ultimo_producto["id"][1:]) if ultimo_producto else 0
    nuevo_id = f"P{str(ultimo_num + 1).zfill(3)}"

    # 5. Crear producto (sin margen de descuento)
    nuevo_producto = {
        "id": nuevo_id,
        "admin_id": admin_id,
        "nombre": producto.nombre,
        "categoria": producto.categoria,
        "precios": {
            "sin_iva_colombia": float(producto.precio_sin_iva_colombia),
            "con_iva_colombia": float(producto.precio_con_iva_colombia),
            "internacional": float(producto.precio_internacional),
            "fecha_actualizacion": datetime.now()
        },
        "stock": int(producto.stock),
        "activo": True,
        "creado_en": datetime.now()
    }

    # 6. Insertar en MongoDB
    try:
        result = await collection_productos.insert_one(nuevo_producto)
        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear producto"
            )

        # 7. Respuesta simplificada
        return {
            "id": nuevo_id,
            "nombre": producto.nombre,
            "precio": producto.precio_con_iva_colombia,
            "stock": producto.stock
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al crear producto: {str(e)}"
        )

@router.get("/productos/")
async def obtener_productos(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden ver los productos"
        )

    # Obtener el ID del administrador actual desde la base de datos
    admin = await collection_admin.find_one({"correo_electronico": current_user["email"]})
    if not admin:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")

    admin_id = str(admin["_id"])  # Convertir ObjectId a string

    # Obtener los productos asociados al administrador actual
    productos = await collection_productos.find({"admin_id": admin_id}).to_list(100)

    # Convertir ObjectId a string para evitar errores en la respuesta JSON
    for producto in productos:
        producto["_id"] = str(producto["_id"])

    return productos

# Endpoint para actualizar un producto
@router.patch("/productos/{producto_id}")
async def actualizar_producto(
    producto_id: str,
    producto_data: ProductoUpdate,
    current_user: dict = Depends(get_current_user)
):
    print(f"📢 Iniciando actualización de producto: {producto_id}")

    # Verificación de administrador
    if current_user["rol"] != "Admin":
        print("❌ Acceso denegado: Solo los administradores pueden modificar productos")
        raise HTTPException(status_code=403, detail="Solo los administradores pueden modificar productos")

    # Obtener admin
    admin = await collection_admin.find_one({"correo_electronico": current_user["email"]})
    if not admin:
        print("❌ Administrador no encontrado")
        raise HTTPException(status_code=404, detail="Administrador no encontrado")

    admin_id = str(admin["_id"])
    print(f"📢 ID del administrador autenticado: {admin_id}")

    # Crear filtro de búsqueda seguro
    filtro = {"admin_id": admin_id}
    
    try:
        # Primero intentar buscar por ObjectId
        filtro["_id"] = ObjectId(producto_id)
        print(f"🔍 Buscando producto por ObjectId: {producto_id}")
    except InvalidId:
        # Si falla, buscar por código personalizado (id_custom en este ejemplo)
        filtro["id_custom"] = producto_id
        print(f"🔍 Buscando producto por id_custom: {producto_id}")

    producto = await collection_productos.find_one(filtro)
    if not producto:
        print("❌ Producto no encontrado o no tienes permisos")
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado o no tienes permisos"
        )

    print(f"📢 Producto encontrado: {producto}")

    # Preparar datos de actualización
    update_data = producto_data.dict(exclude_unset=True)
    update_data["actualizado_en"] = datetime.utcnow()
    print(f"📊 Datos para actualizar: {update_data}")

    # Actualizar usando el mismo filtro
    result = await collection_productos.update_one(filtro, {"$set": update_data})
    if result.modified_count == 0:
        print("⚠️ No se realizaron cambios en el producto")
        raise HTTPException(status_code=304, detail="No se realizaron cambios")

    print("✅ Producto actualizado correctamente")
    return {"mensaje": "Producto actualizado correctamente"}

# Endpoint para eliminar un producto
@router.delete("/productos/{producto_id}")
async def eliminar_producto(producto_id: str, current_user: Dict = Depends(get_current_user)):
    # Verificar si el usuario es administrador
    if current_user["rol"] != "Admin":
        raise HTTPException(status_code=403, detail="Solo los administradores pueden eliminar productos")

    # Buscar el producto en la base de datos
    producto_existente = await collection_productos.find_one({"id": producto_id})
    if not producto_existente:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Eliminar el producto
    await collection_productos.delete_one({"id": producto_id})

    return {"message": "Producto eliminado exitosamente"}

# Endpoint para obtener productos disponibles
@router.get("/productos/disponibles")
async def obtener_productos_disponibles(
    current_user: Dict = Depends(get_current_user)
):
    try:
        print("📢 Iniciando obtención de productos disponibles")  # Debug

        # 1. Obtener información del distribuidor (si aplica)
        tipo_precio = None
        if current_user["rol"] == "distribuidor":
            print(f"🔍 Buscando distribuidor: {current_user['email']}")  # Debug
            distribuidor = await collection_distribuidores.find_one(
                {"correo_electronico": current_user["email"]}
            )
            if not distribuidor:
                print("❌ Distribuidor no encontrado")  # Debug
                raise HTTPException(
                    status_code=404,
                    detail="Distribuidor no encontrado"
                )
            tipo_precio = distribuidor.get("tipo_precio")
            print(f"📢 Tipo de precio del distribuidor: {tipo_precio}")  # Debug
            if not tipo_precio:
                print("❌ Tipo de precio no configurado para el distribuidor")  # Debug
                raise HTTPException(
                    status_code=400,
                    detail="El distribuidor no tiene configurado un tipo de precio"
                )

        # 2. Obtener productos con stock > 0
        print("🔍 Buscando productos con stock disponible")  # Debug
        productos = await collection_productos.find({"stock": {"$gt": 0}}).to_list(100)
        print(f"📢 Productos encontrados: {len(productos)}")  # Debug

        # 3. Mapear el campo de precio según el tipo de precio del distribuidor
        mapeo_precios = {
            "sin_iva": "precios.sin_iva_colombia",
            "con_iva": "precios.con_iva_colombia",
            "sin_iva_internacional": "precios.internacional"
        }

        # 4. Procesar cada producto
        productos_response = []
        for producto in productos:
            print(f"🔍 Procesando producto: {producto['nombre']}")  # Debug
            producto_data = {
                "id": str(producto["id"]),
                "nombre": producto["nombre"],
                "categoria": producto["categoria"],
                "descripcion": producto.get("descripcion", ""),
                "imagen": producto.get("imagen", ""),
                "stock": producto["stock"]
            }

            # Para distribuidores: usar el precio específico configurado
            if current_user["rol"] == "distribuidor" and tipo_precio:
                campo_precio = mapeo_precios[tipo_precio]
                print(f"📢 Campo de precio seleccionado: {campo_precio}")  # Debug
                # Obtener el precio usando notación de puntos (ej: precios.sin_iva_colombia)
                partes = campo_precio.split('.')
                precio = producto
                for parte in partes:
                    precio = precio.get(parte, 0)
                print(f"📢 Precio calculado: {precio}")  # Debug
                
                producto_data["precio"] = precio
                producto_data["tipo_precio"] = tipo_precio
            else:
                # Para no distribuidores: usar precio base
                producto_data["precio"] = producto.get("precio", 0)
                producto_data["tipo_precio"] = "base"
                print(f"📢 Precio base asignado: {producto_data['precio']}")  # Debug

            productos_response.append(producto_data)

        print(f"📢 Productos procesados: {len(productos_response)}")  # Debug
        return productos_response

    except Exception as e:
        print(f"❌ Error al obtener productos: {str(e)}")  # Debug
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener productos: {str(e)}"
        )



