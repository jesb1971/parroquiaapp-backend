"""
Módulo Oración del día - ParroquiaApp.
Gestión de oraciones, imágenes y publicaciones programadas.
"""

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
import os

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    HTTPException
)

from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from app.security import exigir_administrador


# =====================================
# CONFIGURACIÓN DEL MÓDULO
# =====================================

router = APIRouter(
    prefix="/oraciones",
    tags=["Oración del día"]
)

# Almacenamiento persistente de imágenes
IMAGENES_DIR = Path("/var/data/oraciones/imagenes")

MAX_IMAGEN_BYTES = 5 * 1024 * 1024

FORMATOS_IMAGEN = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

FIRMAS_IMAGEN = {
    ".jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
    ".png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    ".webp": lambda b: (
        b.startswith(b"RIFF") and b[8:12] == b"WEBP"
    )
}


# =====================================
# FECHA ACTUAL DE CANARIAS
# =====================================

def fecha_actual_canarias():
    return datetime.now(
        ZoneInfo("Atlantic/Canary")
    ).date()


# =====================================
# GUARDAR IMAGEN DE LA ORACIÓN
# =====================================

async def guardar_imagen_oracion(imagen: UploadFile):

    extension = FORMATOS_IMAGEN.get(imagen.content_type)

    if not extension:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten imágenes JPG, PNG o WebP."
        )

    datos = await imagen.read(MAX_IMAGEN_BYTES + 1)

    if len(datos) > MAX_IMAGEN_BYTES:
        raise HTTPException(
            status_code=413,
            detail="La imagen supera el límite de 5 MB."
        )

    if not datos or not FIRMAS_IMAGEN[extension](datos):
        raise HTTPException(
            status_code=400,
            detail="El archivo no es una imagen válida."
        )

    IMAGENES_DIR.mkdir(parents=True, exist_ok=True)

    nombre = f"{uuid4().hex}{extension}"
    ruta = IMAGENES_DIR / nombre

    try:
        with open(ruta, "xb") as archivo:
            archivo.write(datos)
    except OSError:
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar la imagen."
        )

    return ruta, f"/media/oraciones/{nombre}"


# =====================================
# CREAR Y PROGRAMAR ORACIÓN
# =====================================

@router.post("/publicar")
async def publicar_oracion(
    fecha: date = Form(...),
    titulo: str = Form(...),
    contenido: str = Form(...),
    autor: str = Form(""),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    # Evitar dos oraciones con la misma fecha
    existente = (
        db.query(models.OracionDiaria)
        .filter(models.OracionDiaria.fecha == fecha)
        .first()
    )

    if existente:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una oración para esta fecha."
        )

    if not titulo.strip() or not contenido.strip():
        raise HTTPException(
            status_code=400,
            detail="El título y el contenido son obligatorios."
        )

    ruta_guardada = None
    imagen_url = None

    try:
        if imagen is not None and imagen.filename:
            ruta_guardada, imagen_url = (
                await guardar_imagen_oracion(imagen)
            )

        oracion = models.OracionDiaria(
            fecha=fecha,
            titulo=titulo.strip(),
            contenido=contenido.strip(),
            autor=autor.strip() or None,
            imagen=imagen_url
        )

        db.add(oracion)
        db.commit()
        db.refresh(oracion)

    except Exception:
        db.rollback()

        if ruta_guardada is not None:
            try:
                os.remove(ruta_guardada)
            except OSError:
                pass

        raise

    return oracion


# =====================================
# CONSULTAR ORACIÓN DEL DÍA
# =====================================

@router.get("/hoy")
def obtener_oracion_del_dia(
    db: Session = Depends(get_db)
):

    hoy = fecha_actual_canarias()

    oracion = (
        db.query(models.OracionDiaria)
        .filter(models.OracionDiaria.fecha <= hoy)
        .order_by(
            models.OracionDiaria.fecha.desc(),
            models.OracionDiaria.id.desc()
        )
        .first()
    )

    if oracion is None:
        raise HTTPException(
            status_code=404,
            detail="Todavía no hay oraciones publicadas."
        )

    return oracion


# =====================================
# HISTÓRICO PÚBLICO DE ORACIONES
# =====================================

@router.get("/historico")
def obtener_historico_oraciones(
    db: Session = Depends(get_db)
):

    hoy = fecha_actual_canarias()

    oraciones = (
        db.query(models.OracionDiaria)
        .filter(models.OracionDiaria.fecha <= hoy)
        .order_by(
            models.OracionDiaria.fecha.desc(),
            models.OracionDiaria.id.desc()
        )
        .all()
    )

    return oraciones


# =====================================
# EDITAR ORACIÓN
# =====================================

@router.put("/{oracion_id}")
async def editar_oracion(
    oracion_id: int,
    fecha: date = Form(...),
    titulo: str = Form(...),
    contenido: str = Form(...),
    autor: str = Form(""),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    oracion = (
        db.query(models.OracionDiaria)
        .filter(models.OracionDiaria.id == oracion_id)
        .first()
    )

    if oracion is None:
        raise HTTPException(
            status_code=404,
            detail="Oración no encontrada."
        )

    if not titulo.strip() or not contenido.strip():
        raise HTTPException(
            status_code=400,
            detail="El título y el contenido son obligatorios."
        )

    existente = (
        db.query(models.OracionDiaria)
        .filter(
            models.OracionDiaria.fecha == fecha,
            models.OracionDiaria.id != oracion_id
        )
        .first()
    )

    if existente:
        raise HTTPException(
            status_code=409,
            detail="Ya existe otra oración para esta fecha."
        )

    ruta_guardada = None

    try:
        if imagen is not None and imagen.filename:
            ruta_guardada, nueva_url = (
                await guardar_imagen_oracion(imagen)
            )
            oracion.imagen = nueva_url

        oracion.fecha = fecha
        oracion.titulo = titulo.strip()
        oracion.contenido = contenido.strip()
        oracion.autor = autor.strip() or None

        db.commit()
        db.refresh(oracion)

    except Exception:
        db.rollback()

        if ruta_guardada is not None:
            try:
                os.remove(ruta_guardada)
            except OSError:
                pass

        raise

    return oracion


# =====================================
# ELIMINAR ORACIÓN
# =====================================

@router.delete("/{oracion_id}")
def eliminar_oracion(
    oracion_id: int,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    oracion = (
        db.query(models.OracionDiaria)
        .filter(models.OracionDiaria.id == oracion_id)
        .first()
    )

    if oracion is None:
        raise HTTPException(
            status_code=404,
            detail="Oración no encontrada."
        )

    db.delete(oracion)
    db.commit()

    return {
        "mensaje": "Oración eliminada correctamente."
    }


# =====================================
# LISTAR TODAS LAS ORACIONES (ADMIN)
# =====================================

@router.get("/admin/listado")
def listar_oraciones_admin(
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    oraciones = (
        db.query(models.OracionDiaria)
        .order_by(
            models.OracionDiaria.fecha.desc(),
            models.OracionDiaria.id.desc()
        )
        .all()
    )

    return oraciones
