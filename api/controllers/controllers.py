from models.models import conexion
from fastapi import UploadFile, File, HTTPException,Form
import base64
from typing import Union, List, Dict
from pydantic import BaseModel
import logging
import datetime
from elasticsearch import Elasticsearch

class Orden(BaseModel):
    imagen: str
    nombre_producto: str
    cantidad: int

class Ordenes(BaseModel):
    ordenes: list[Orden]


async def handle_image_upload(nombre_producto: str, file: UploadFile):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        # Leer la imagen en binario
        imagen_bytes = await file.read()

        # Codificar la imagen en base64
        imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')

        # Verificar si la imagen ya existe en la base de datos
        with connection.cursor() as cursor:
            query_check = "SELECT COUNT(*) FROM productos WHERE imagen_64 = %s"
            cursor.execute(query_check, (imagen_base64,))
            resultado = cursor.fetchone()

        if resultado[0] > 0:
            return {"message": "Imagen ya existe en la base de datos."}
        else:
            # Insertar la nueva imagen
            with connection.cursor() as cursor:
                query_insert = "INSERT INTO productos (nombre_producto, imagen_64) VALUES (%s, %s)"
                cursor.execute(query_insert, (nombre_producto, imagen_base64))
                connection.commit()

            return {"message": f"Imagen '{nombre_producto}' insertada correctamente."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir la imagen: {str(e)}")

async def get_product_details(id_producto: int):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        # Consultar los detalles del producto por su ID
        with connection.cursor() as cursor:
            query = "SELECT id_product, nombre_producto, imagen_64 FROM productos WHERE id_product = %s"
            cursor.execute(query, (id_producto,))
            resultado = cursor.fetchone()

        if resultado:
            # Retornar los datos del producto
            return {
                "id_product": resultado[0],
                "nombre_producto": resultado[1],
                "imagen_64": resultado[2]
            }
        else:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el producto: {str(e)}")

async def delete_image(id_producto: int):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        # Verificar si la imagen existe en la base de datos
        with connection.cursor() as cursor:
            query_check = "SELECT COUNT(*) FROM productos WHERE id_product = %s"
            cursor.execute(query_check, (id_producto,))
            resultado = cursor.fetchone()

        if resultado[0] == 0:
            raise HTTPException(status_code=404, detail="Imagen no encontrada.")

        # Eliminar la imagen
        with connection.cursor() as cursor:
            query_delete = "DELETE FROM productos WHERE id_product = %s"
            cursor.execute(query_delete, (id_producto,))
            connection.commit()

        # Verificar si la tabla quedó vacía
        with connection.cursor() as cursor:
            query_count = "SELECT COUNT(*) FROM productos"
            cursor.execute(query_count)
            count_result = cursor.fetchone()

        # Si la tabla está vacía, restablecer el AUTO_INCREMENT
        if count_result[0] == 0:
            with connection.cursor() as cursor:
                query_reset = "ALTER TABLE productos AUTO_INCREMENT = 1"
                cursor.execute(query_reset)
                connection.commit()

        return {"message": f"Imagen con ID {id_producto} eliminada correctamente."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar la imagen: {str(e)}")
    finally:
        connection.close()

async def get_all_images():
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        with connection.cursor() as cursor:
            query = "SELECT id_product, nombre_producto, imagen_64 FROM productos"
            cursor.execute(query)
            imagenes = cursor.fetchall()

        # Formatear los resultados
        return [{"id": img[0], "nombre_producto": img[1], "imagen_64": img[2]} for img in imagenes]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener las imágenes: {str(e)}")
    finally:
        connection.close()

async def update_product(id_producto: int, nombre_producto: str, file: Union[UploadFile, None] = None):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        # Verificar si el producto existe
        with connection.cursor() as cursor:
            query_check = "SELECT COUNT(*) FROM productos WHERE id_product = %s"
            cursor.execute(query_check, (id_producto,))
            resultado = cursor.fetchone()

        if resultado[0] == 0:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")

        # Si hay un archivo de imagen, convertirlo a base64
        if file:
            imagen_bytes = await file.read()
            imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
        else:
            imagen_base64 = None

        # Actualizar el producto
        with connection.cursor() as cursor:
            if imagen_base64:
                query_update = "UPDATE productos SET nombre_producto = %s, imagen_64 = %s WHERE id_product = %s"
                cursor.execute(query_update, (nombre_producto, imagen_base64, id_producto))
            else:
                query_update = "UPDATE productos SET nombre_producto = %s WHERE id_product = %s"
                cursor.execute(query_update, (nombre_producto, id_producto))
            
            connection.commit()

        return {"message": f"Producto con ID {id_producto} actualizado correctamente."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al modificar el producto: {str(e)}")
    
async def register_user(username: str, password: str, role: str):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        # Verificar si el usuario ya existe
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            result = cursor.fetchone()
            if result:
                raise HTTPException(status_code=400, detail="El usuario ya existe")

        # Registrar el nuevo usuario
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO usuarios (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
            connection.commit()

        return {"message": "Usuario registrado exitosamente"}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def login_user(username: str, password: str):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        with connection.cursor() as cursor:
            query = "SELECT username, role FROM usuarios WHERE username = %s AND password = %s"
            cursor.execute(query, (username, password))
            result = cursor.fetchone()

        if result:
            return {"username": result[0], "role": result[1]}
        else:
            raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_all_users():
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        with connection.cursor() as cursor:
            # Consultar todos los usuarios
            cursor.execute("SELECT id, username, role, password FROM usuarios")
            usuarios = cursor.fetchall()

        # Formatear el resultado
        return [{"id": u[0], "username": u[1], "role": u[2], "password": u[3]} for u in usuarios]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_user_by_id(user_id: int):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        with connection.cursor() as cursor:
            # Consultar usuario por ID
            cursor.execute("SELECT id, username, role, password FROM usuarios WHERE id = %s", (user_id,))
            usuario = cursor.fetchone()

        if usuario:
            # Formatear el resultado si se encuentra el usuario
            return {
                "id": usuario[0],
                "username": usuario[1],
                "role": usuario[2],
                "password": usuario[3]
            }
        else:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def update_user(user_id: int, username: str, password: str, role: str):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        with connection.cursor() as cursor:
            # Actualizar los datos del usuario
            cursor.execute("""
                UPDATE usuarios SET username = %s, password = %s, role = %s WHERE id = %s
            """, (username, password, role, user_id))
            connection.commit()

        return {"message": "Usuario actualizado correctamente"}

    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

async def delete_user(user_id: int):
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
            connection.commit()

        return {"message": "Usuario eliminado correctamente"}

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
async def crear_ordenes(ordenes: Dict[str, List[Dict[str, Union[str, int]]]]):
    try:
        connection = conexion()
        with connection.cursor() as cursor:
            for orden in ordenes['ordenes']:  
                cursor.execute(
                    "INSERT INTO ordenes (pedido_id, imagen, nombre_producto, cantidad) VALUES (%s, %s, %s, %s)", 
                    (orden['id'], orden['imagen'], orden['nombre_producto'], orden['cantidad'])
                )
            connection.commit()
        return {"detail": "Órdenes guardadas correctamente"}
    except Exception as e:
        print(f"Error al insertar en la base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error al guardar las órdenes")

async def get_all_orders():
    try:
        connection = conexion()
        if connection is None:
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

        with connection.cursor() as cursor:
            cursor.execute("SELECT pedido_id, imagen, nombre_producto, cantidad FROM ordenes")
            ordenes = cursor.fetchall()

        ordenes_agrupadas = {}
        for u in ordenes:
            pedido_id = u[0]  # Esto ahora debe obtener el pedido_id correctamente
            if pedido_id not in ordenes_agrupadas:
                ordenes_agrupadas[pedido_id] = []

            ordenes_agrupadas[pedido_id].append({
                "imagen": u[1],
                "nombre_producto": u[2],
                "cantidad": u[3]
            })

        # Formatear el resultado
        resultado = [{"pedido_id": pid, "productos": productos} for pid, productos in ordenes_agrupadas.items()]

        return resultado

    except Exception as e:
        print(f"Error al obtener órdenes: {e}")  # Debug: imprimir el error
        raise HTTPException(status_code=500, detail=str(e))


