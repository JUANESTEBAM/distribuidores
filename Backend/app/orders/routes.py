from app.auth.routes import get_current_user
from fastapi import APIRouter, HTTPException, Depends, Body, status
from bson import ObjectId
from datetime import datetime, timedelta
import os
import smtplib
import ssl
from email.message import EmailMessage
from app.core.database import (
    collection_pedidos,
    collection_productos,
    collection_distribuidores,
    collection_admin
)

router = APIRouter()

EMAIL_SENDER = os.getenv("EMAIL_REMITENTE")
EMAIL_PASSWORD = os.getenv("EMAIL_CONTRASENA")  # Contraseña de aplicación generada en Gmail
print("EMAIL_SENDER:", EMAIL_SENDER)  # Debe imprimir info@rizosfelices.co
print("EMAIL_PASSWORD:", EMAIL_PASSWORD)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # Puerto seguro con SSL

def enviar_correo(destinatario, asunto, mensaje):
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = EMAIL_SENDER
    msg["To"] = destinatario
    msg.set_content(mensaje, subtype="html")  # Enviar contenido en HTML

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
    print(f"📧 Correo enviado a {destinatario}")


# ENDPOINT PARA CREAR EL PEDIDO Y DEVUELVE DETALLES
@router.post("/pedidos/")
async def crear_pedido(pedido: dict, current_user: dict = Depends(get_current_user)):
    print("📢 Iniciando creación de pedido")

    # Verificar si el usuario tiene el rol de distribuidor
    if current_user["rol"] != "distribuidor":
        print("❌ Acceso denegado: Solo los distribuidores pueden crear pedidos")
        raise HTTPException(status_code=403, detail="Solo los distribuidores pueden crear pedidos")

    # Obtener distribuidor actual
    distribuidor = await collection_distribuidores.find_one({"correo_electronico": current_user["email"]})
    if not distribuidor:
        print("❌ Distribuidor no encontrado")
        raise HTTPException(status_code=404, detail="Distribuidor no encontrado")

    distribuidor_id = str(distribuidor["_id"])
    distribuidor_nombre = distribuidor.get("nombre", "Desconocido")
    distribuidor_phone = distribuidor.get("phone", "No registrado")
    tipo_precio = distribuidor.get("tipo_precio", "con_iva")

    print(f"📢 Distribuidor encontrado: {distribuidor_nombre}, Tipo de precio: {tipo_precio}")

    # Validaciones básicas del pedido
    if "productos" not in pedido or not isinstance(pedido["productos"], list):
        print("❌ Pedido inválido: Falta lista de productos")
        raise HTTPException(status_code=400, detail="El pedido debe contener una lista de productos")

    if "direccion" not in pedido:
        print("❌ Pedido inválido: Falta dirección")
        raise HTTPException(status_code=400, detail="El pedido debe incluir una dirección")

    productos_actualizados = []
    subtotal = 0
    iva_total = 0

    # Procesar cada producto del pedido
    for producto in pedido["productos"]:
        if "id" not in producto or "cantidad" not in producto or "precio" not in producto:
            print(f"❌ Producto inválido: {producto}")
            raise HTTPException(status_code=400, detail="Cada producto debe tener 'id', 'cantidad' y 'precio'")

        producto_id = producto["id"]
        cantidad_solicitada = int(producto["cantidad"])
        precio_sin_iva = float(producto["precio"])  # 💡 El precio enviado desde el frontend sin IVA

        print(f"🔍 Verificando producto {producto_id}")

        producto_db = await collection_productos.find_one({"id": producto_id})
        if not producto_db:
            raise HTTPException(status_code=404, detail=f"Producto con ID {producto_id} no encontrado")

        if tipo_precio == "con_iva":
            iva = round(precio_sin_iva * 0.19, 2)
            precio_con_iva = round(precio_sin_iva + iva, 2)
            iva_producto = round(iva * cantidad_solicitada, 2)

        elif tipo_precio in ["sin_iva", "sin_iva_internacional"]:
            precio_con_iva = precio_sin_iva
            iva_producto = 0
            iva = 0

        else:
            raise HTTPException(status_code=400, detail="Tipo de precio no válido")

        print(f"✅ Producto {producto_id}: Precio sin IVA: {precio_sin_iva}, IVA unitario: {iva}, Total con IVA: {precio_con_iva}")

        # Actualizar stock
        nuevo_stock = producto_db["stock"] - cantidad_solicitada
        await collection_productos.update_one({"id": producto_id}, {"$set": {"stock": nuevo_stock}})

        productos_actualizados.append({
            "id": producto_id,
            "nombre": producto_db["nombre"],
            "cantidad": cantidad_solicitada,
            "precio": precio_con_iva,
            "precio_sin_iva": precio_sin_iva,
            "iva_unitario": iva,
            "total": precio_con_iva * cantidad_solicitada,
            "tipo_precio": tipo_precio
        })

        subtotal += precio_sin_iva * cantidad_solicitada
        iva_total += iva_producto

        print(f"✅ Producto {producto_id} actualizado con nuevo stock: {nuevo_stock}")

    total_pedido = subtotal + iva_total


    print(f"📦 Subtotal: {subtotal}, IVA Total: {iva_total}, Total Pedido: {total_pedido}")

    # Crear pedido en la base de datos
    pedido_id = f"PED-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    nuevo_pedido = {
        "id": pedido_id,
        "distribuidor_id": distribuidor_id,
        "distribuidor_nombre": distribuidor_nombre,
        "distribuidor_phone": distribuidor_phone,
        "productos": productos_actualizados,
        "direccion": pedido["direccion"],
        "notas": pedido.get("notas", ""),
        "fecha": datetime.now(),
        "estado": "Procesando",
        "subtotal": subtotal,
        "iva": iva_total,
        "total": total_pedido,
        "tipo_precio": tipo_precio
    }
    
    result = await collection_pedidos.insert_one(nuevo_pedido)
    print(f"📦 Pedido creado con ID: {pedido_id}")

    # Preparar mensajes de correo
    fecha_pedido = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Plantilla CSS para los correos
    estilo_correo = """
    <style>
        body { font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f8f1e9; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
        .logo { max-width: 150px; }
        .content { padding: 20px; background-color: #fff; border: 1px solid #e0e0e0; border-top: none; }
        .footer { text-align: center; padding: 20px; font-size: 12px; color: #777; }
        .product-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        .product-table th { background-color: #f8f1e9; text-align: left; padding: 10px; }
        .product-table td { padding: 10px; border-bottom: 1px solid #e0e0e0; }
        .totals { margin-top: 20px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }
        .totals-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .total-final { font-weight: bold; font-size: 1.1em; border-top: 1px solid #ddd; padding-top: 10px; }
        .status { display: inline-block; padding: 5px 10px; background-color: #e3f2fd; color: #1976d2; border-radius: 3px; }
    </style>
    """

    # Generar tabla de productos para el correo
    productos_html = """
    <table class="product-table">
        <thead>
            <tr>
                <th>Producto</th>
                <th>Cantidad</th>
                <th>Precio Unitario</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
    """

    for p in productos_actualizados:
        productos_html += f"""
        <tr>
            <td>{p['nombre']} (ID: {p['id']})</td>
            <td>{p['cantidad']}</td>
            <td>${p['precio']:,.0f}</td>
            <td>${p['total']:,.0f}</td>
        </tr>
        """
        if tipo_precio == "con_iva":
            productos_html += f"""
            <tr style="color: #666; font-size: 0.9em;">
                <td colspan="4">
                    (IVA incluido: ${p['iva_unitario']:,.0f} x {p['cantidad']} = ${p['iva_unitario'] * p['cantidad']:,.0f})
                </td>
            </tr>
            """

    productos_html += """
        </tbody>
    </table>
    """

    # Sección de totales
    totales_html = f"""
    <div class="totals">
        <div class="totals-row">
            <span>Subtotal:</span>
            <span>${subtotal:,.0f}</span>
        </div>
        {f'<div class="totals-row"><span>IVA (19%):</span><span>${iva_total:,.0f}</span></div>' if tipo_precio == "con_iva" else ""}
        <div class="totals-row total-final">
            <span>Total del Pedido:</span>
            <span>${total_pedido:,.0f}</span>
        </div>
    </div>
    """

    # Mensaje para el administrador
    mensaje_admin = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nuevo Pedido {pedido_id}</title>
        {estilo_correo}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="https://rizosfelicesdata.s3.us-east-2.amazonaws.com/logo+principal+rosado+letra+blanco_Mesa+de+tra+(1).png" alt="Rizos Felices" class="logo">
                <h1>Nuevo Pedido Recibido</h1>
            </div>
            
            <div class="content">
                <h2>Detalles del Pedido</h2>
                <p><strong>Número de Pedido:</strong> {pedido_id}</p>
                <p><strong>Fecha y Hora:</strong> {fecha_pedido}</p>
                <p><strong>Estado:</strong> <span class="status">Procesando</span></p>
                
                <h3>Información del Distribuidor</h3>
                <p><strong>Nombre:</strong> {distribuidor_nombre}</p>
                <p><strong>Teléfono:</strong> {distribuidor_phone}</p>
                
                <h3>Detalles de Entrega</h3>
                <p><strong>Dirección:</strong> {pedido['direccion']}</p>
                <p><strong>Notas:</strong> {pedido.get('notas', 'Ninguna')}</p>
                
                <h3>Productos Solicitados</h3>
                {productos_html}
                {totales_html}
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} Rizos Felices. Todos los derechos reservados.</p>
                <p>Este es un correo automático, por favor no responder.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Mensaje para el distribuidor
    mensaje_distribuidor = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Confirmación de Pedido {pedido_id}</title>
        {estilo_correo}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="https://rizosfelicesdata.s3.us-east-2.amazonaws.com/logo+principal+rosado+letra+blanco_Mesa+de+tra+(1).png" alt="Rizos Felices" class="logo">
                <h1>¡Gracias por tu pedido!</h1>
            </div>
            
            <div class="content">
                <p>Hemos recibido tu pedido correctamente y está siendo procesado. A continuación encontrarás los detalles:</p>
                
                <h2>Resumen del Pedido</h2>
                <p><strong>Número de Pedido:</strong> {pedido_id}</p>
                <p><strong>Fecha y Hora:</strong> {fecha_pedido}</p>
                <p><strong>Estado:</strong> <span class="status">Procesando</span></p>
                
                <h3>Detalles de Entrega</h3>
                <p><strong>Dirección:</strong> {pedido['direccion']}</p>
                <p><strong>Notas:</strong> {pedido.get('notas', 'Ninguna')}</p>
                
                <h3>Productos</h3>
                {productos_html}
                {totales_html}
                
                <p style="margin-top: 20px;">
                    <strong>Nota:</strong> Te notificaremos cuando tu pedido esté en camino. 
                    Para cualquier consulta, puedes responder a este correo o contactarnos al teléfono de soporte.
                </p>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} Rizos Felices. Todos los derechos reservados.</p>
                <p>Este es un correo automático, por favor no responder.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Enviar correos
    enviar_correo(
        "produccion@rizosfelices.co",
        f"📦 Nuevo Pedido: {pedido_id} - {distribuidor_nombre}",
        mensaje_admin
    )

    enviar_correo(
        "tesoreria@rizosfelices.co",
        f"📦 Nuevo Pedido: {pedido_id} - {distribuidor_nombre}",
        mensaje_admin
    )

    enviar_correo(
        current_user["email"],
        f"✅ Confirmación de Pedido: {pedido_id}",
        mensaje_distribuidor
    )

    
    print(f"📧 Correos enviados para el pedido {pedido_id}")

    # Convertir ObjectId a string para la respuesta JSON
    nuevo_pedido["_id"] = str(result.inserted_id)

    return {
        "message": "Pedido creado exitosamente",
        "pedido": nuevo_pedido
    }

# ENDPOINT PARA OBTENER LOS PEDIDOS
@router.get("/pedidos/")
async def obtener_pedidos(current_user: dict = Depends(get_current_user)):
    try:
        email = current_user["email"]
        rol = current_user["rol"]

        print(f"📢 Usuario autenticado: {email}, Rol: {rol}")  # Debug

        if rol == "Admin":
            # Obtener el admin actual
            admin = await collection_admin.find_one({"correo_electronico": email})
            if not admin:
                raise HTTPException(status_code=404, detail="Admin no encontrado")

            admin_id = str(admin["_id"])  # Convertir ObjectId a str
            print(f"📦 ID del admin: {admin_id}")  # Debug

            # Obtener los distribuidores asociados al admin
            distribuidores = await collection_distribuidores.find({"admin_id": ObjectId(admin_id)}).to_list(None)
            distribuidores_ids = [str(distribuidor["_id"]) for distribuidor in distribuidores]
            print(f"📦 Distribuidores asociados al admin: {distribuidores_ids}")  # Debug

            # Obtener los pedidos de los distribuidores asociados
            pedidos = []
            for distribuidor_id in distribuidores_ids:
                pedidos_distribuidor = await collection_pedidos.find({"distribuidor_id": distribuidor_id}).to_list(None)
                pedidos.extend(pedidos_distribuidor)

        elif rol == "distribuidor":
            # Obtener el distribuidor actual
            distribuidor = await collection_distribuidores.find_one({"correo_electronico": email})
            if not distribuidor:
                raise HTTPException(status_code=404, detail="Distribuidor no encontrado")

            distribuidor_id = str(distribuidor["_id"])
            print(f"📦 ID del distribuidor: {distribuidor_id}")  # Debug

            # Obtener los pedidos del distribuidor
            pedidos = await collection_pedidos.find({"distribuidor_id": distribuidor_id}).to_list(None)

        elif rol == "produccion":
            # Obtener todos los pedidos (o los relevantes para producción)
            pedidos = await collection_pedidos.find().to_list(None)
            
        elif rol == "facturacion":
            # Obtener todos los pedidos (o los relevantes para facturación)
            pedidos = await collection_pedidos.find().to_list(None)

        else:
            raise HTTPException(status_code=403, detail="Rol no autorizado para ver pedidos")

        # Convertir ObjectId a str para la respuesta JSON
        for pedido in pedidos:
            pedido["_id"] = str(pedido["_id"])

        return {"pedidos": pedidos}

    except Exception as e:
        print(f"❌ Error al obtener pedidos: {e}")  # Debug
        raise HTTPException(status_code=500, detail="Error interno al obtener pedidos")

# Endpoint para obtener detalles de un pedido específico
@router.get("/pedidos/{pedido_id}")
async def obtener_detalles_pedido(pedido_id: str, current_user: dict = Depends(get_current_user)):
    try:
        email = current_user["email"]
        rol = current_user["rol"]

        print(f"📢 Usuario autenticado: {email}, Rol: {rol}")  # Debug

        # Buscar el pedido por su ID
        pedido = await collection_pedidos.find_one({"id": pedido_id})
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")

        # Convertir ObjectId a str para la respuesta JSON
        pedido["_id"] = str(pedido["_id"])

        # Verificar permisos según el rol
        if rol == "Admin":
            # Obtener el admin actual
            admin = await collection_admin.find_one({"correo_electronico": email})
            if not admin:
                raise HTTPException(status_code=404, detail="Admin no encontrado")

            admin_id = str(admin["_id"])  # Convertir ObjectId a str

            # Verificar si el pedido pertenece a un distribuidor asociado al admin
            distribuidor = await collection_distribuidores.find_one({"_id": ObjectId(pedido["distribuidor_id"])})
            if not distribuidor or str(distribuidor["admin_id"]) != admin_id:
                raise HTTPException(status_code=403, detail="No tienes permisos para ver este pedido")

        elif rol == "distribuidor":
            # Obtener el distribuidor actual
            distribuidor = await collection_distribuidores.find_one({"correo_electronico": email})
            if not distribuidor:
                raise HTTPException(status_code=404, detail="Distribuidor no encontrado")

            distribuidor_id = str(distribuidor["_id"])

            # Verificar si el pedido pertenece al distribuidor
            if pedido["distribuidor_id"] != distribuidor_id:
                raise HTTPException(status_code=403, detail="No tienes permisos para ver este pedido")

        elif rol in ["produccion", "facturacion"]:
            # Los roles de producción y facturación pueden ver cualquier pedido
            pass

        else:
            raise HTTPException(status_code=403, detail="Rol no autorizado para ver pedidos")

        return {"pedido": pedido}

    except Exception as e:
        print(f"❌ Error al obtener detalles del pedido: {e}")  # Debug
        raise HTTPException(status_code=500, detail="Error interno al obtener detalles del pedido")

# ENDPOINT PARA CAMBIAR ESTADO DE PEDIDO (facturado/en camino)
@router.put("/pedidos/{pedido_id}/estado")
async def cambiar_estado_pedido(
    pedido_id: str,
    nuevo_estado: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    try:
        email = current_user["email"]
        rol = current_user["rol"]

        # Verificar permisos
        if rol not in ["Admin", "produccion", "facturacion", "distribuidor"]:
            raise HTTPException(status_code=403, detail="No tienes permisos para cambiar estados")

        # Validar estado
        if nuevo_estado not in ["facturado", "en camino"]:
            raise HTTPException(status_code=400, detail="Estado no válido")

        # Buscar y actualizar usando el ID personalizado (no ObjectId)
        resultado = await collection_pedidos.update_one(
            {"id": pedido_id},  # Buscar por tu ID personalizado
            {"$set": {"estado": nuevo_estado}}
        )

        if resultado.modified_count == 0:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")

        # Obtener pedido actualizado
        pedido_actualizado = await collection_pedidos.find_one({"id": pedido_id})
        
        # Limpiar el _id de MongoDB si existe
        if pedido_actualizado and "_id" in pedido_actualizado:
            del pedido_actualizado["_id"]

        return {
            "mensaje": f"Estado actualizado a '{nuevo_estado}'",
            "pedido": pedido_actualizado
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint de Estadísticas Generales
@router.get("/estadisticas/generales")
async def obtener_estadisticas_generales():
    """
    Accesible para cualquier usuario
    """
    try:
        # 1. Pedidos totales
        total_pedidos = await collection_pedidos.count_documents({})
        
        # 2. Cantidad de productos
        try:
            total_productos = await collection_productos.count_documents({
                "activo": True,
                "eliminado": {"$ne": True}  # Filtro adicional por si usas borrado lógico
            })
        except Exception as e:
            print(f"❌ Error al contar productos: {str(e)}")
            total_productos = 0  # Mantener 0 como valor seguro si hay error
        
        # 3. Cantidad de distribuidores
        total_distribuidores = await collection_distribuidores.count_documents({})
        
        # 4. Ventas mensuales
        fecha_inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fecha_fin_mes = (fecha_inicio_mes + timedelta(days=32)).replace(day=1)
        
        pipeline_ventas = [
            {
                "$match": {
                    "fecha": {"$gte": fecha_inicio_mes, "$lt": fecha_fin_mes},
                    "estado": "facturado"
                }
            },
            {"$unwind": "$productos"},
            {
                "$group": {
                    "_id": None,
                    "total_ventas": {
                        "$sum": {"$multiply": ["$productos.cantidad", "$productos.precio"]}
                    },
                    "count_ventas": {"$sum": 1}  # Contar número de transacciones
                }
            }
        ]
        
        ventas_mensuales = await collection_pedidos.aggregate(pipeline_ventas).to_list(length=1)
        total_ventas = ventas_mensuales[0]["total_ventas"] if ventas_mensuales and "total_ventas" in ventas_mensuales[0] else 0
        
        return {
            "pedidos_totales": total_pedidos,
            "total_productos": total_productos,
            "total_distribuidores": total_distribuidores,
            "ventas_mensuales": total_ventas,
            "fecha_consulta": datetime.now().isoformat()  # Para debugging
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )

## Endpoint de Pedidos Recientes
@router.get("/pedidos/recientes", response_model=list[dict])
async def obtener_pedidos_recientes():
    """
    Obtiene los 5 pedidos más recientes.
    Accesible para cualquier usuario sin autenticación.
    
    Returns:
        List[dict]: Lista de pedidos con sus datos básicos
    """
    try:
        # Obtener pedidos ordenados por fecha descendente
        pedidos = await collection_pedidos.find({}) \
            .sort("fecha", -1) \
            .limit(5) \
            .to_list(length=None)
        
        if not pedidos:
            return []
        
        # Formatear respuesta
        response = []
        for pedido in pedidos:
            # Calcular total
            total = sum(
                producto["cantidad"] * producto["precio"] 
                for producto in pedido.get("productos", [])
            )
            
            # Estructurar datos de respuesta
            response.append({
                "id": str(pedido["_id"]),
                "distribuidor": pedido.get("distribuidor_nombre", ""),
                "fecha": pedido.get("fecha", "").isoformat() if pedido.get("fecha") else "",
                "estado": pedido.get("estado", ""),
                "total": total,
                "productos_count": len(pedido.get("productos", []))
            })
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener pedidos recientes: {str(e)}"
        )

@router.get("/productos/populares")
async def obtener_productos_populares(current_user: dict = Depends(get_current_user)):
    """
    Accesible para: admin, produccion
    Devuelve los 5 productos más vendidos en el mes actual
    """
    # Debug inicial
    print(f"🔍 Iniciando consulta para {current_user['email']} (Rol: {current_user['rol']})")
    
    # Validación de roles
    if current_user["rol"].lower() == "facturacion":
        print("⛔ Acceso denegado a facturación")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta información"
        )
    
    # Configurar fechas para el mes actual
    hoy = datetime.now()
    fecha_inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fecha_fin_mes = (fecha_inicio_mes + timedelta(days=32)).replace(day=1)
    print(f"📅 Rango del mes: {fecha_inicio_mes} a {fecha_fin_mes}")

    # Pipeline de agregación mejorado
    pipeline = [
        {
            "$match": {
                "fecha": {
                    "$gte": fecha_inicio_mes,
                    "$lt": fecha_fin_mes
                },
                "estado": "facturado",
                "productos": {"$exists": True, "$not": {"$size": 0}}  # Asegura que hay productos
            }
        },
        {"$unwind": "$productos"},
        {
            "$match": {
                "productos.id": {"$exists": True},  # Valida que tenga ID
                "productos.cantidad": {"$gt": 0}    # Solo productos con cantidad > 0
            }
        },
        {
            "$group": {
                "_id": "$productos.id",
                "nombre": {"$first": "$productos.nombre"},
                "categoria": {"$first": "$productos.categoria"},
                "precio": {"$avg": "$productos.precio"},  # Usamos avg por si hay variaciones
                "vendidos": {"$sum": "$productos.cantidad"},
                "num_pedidos": {"$sum": 1}  # Para saber en cuántos pedidos apareció
            }
        },
        {"$sort": {"vendidos": -1}},
        {"$limit": 5},
        {
            "$lookup": {
                "from": "productos",
                "localField": "_id",
                "foreignField": "id",
                "as": "producto_info"
            }
        },
        {"$unwind": "$producto_info"},
        {
            "$addFields": {
                "stock": "$producto_info.stock",
                "activo": "$producto_info.activo",
                "imagen": "$producto_info.imagen"  # Agregar más campos si es necesario
            }
        },
        {
            "$project": {
                "_id": 0,
                "id": "$_id",
                "nombre": 1,
                "categoria": 1,
                "precio": 1,
                "vendidos": 1,
                "stock": 1,
                "activo": 1,
                "imagen": 1,
                "num_pedidos": 1,
                "en_produccion": "$producto_info.en_produccion"
            }
        }
    ]
    
    print("🔎 Ejecutando pipeline de agregación...")
    try:
        productos = await collection_pedidos.aggregate(pipeline).to_list(length=None)
        print(f"✅ Productos encontrados: {len(productos)}")
        
        # Filtrado adicional para producción
        if current_user["rol"].lower() == "produccion":
            productos = [p for p in productos if p.get("en_produccion", False)]
            print(f"🛠️ Filtrados para producción: {len(productos)}")
        
        # Validar si hay resultados
        if not productos:
            print("⚠️ No se encontraron productos populares este mes")
            # Opcional: devolver productos aleatorios o más recientes como fallback
            return []
        
        return productos
        
    except Exception as e:
        print(f"❌ Error en agregación: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener productos populares: {str(e)}"
        )


