
"""Rutas del módulo Noticias de ParroquiaApp."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4
import os

from fastapi import (
    APIRouter,
    Depends,
    Body,
    File,
    Form,
    UploadFile,
    HTTPException
)
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from app.security import exigir_administrador


router = APIRouter(prefix="/noticias", tags=["noticias"])

# =====================================
# ALMACENAMIENTO DE IMÁGENES
# =====================================

IMAGENES_DIR = Path("/var/data/noticias/imagenes")
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
# CONSULTAR NOTICIA
# =====================================

def obtener_noticia(db: Session, noticia_id: int):
    noticia = (
        db.query(models.Noticia)
        .filter(models.Noticia.id == noticia_id)
        .first()
    )

    if noticia is None:
        raise HTTPException(
            status_code=404,
            detail="Noticia no encontrada."
        )

    return noticia


# =====================================
# GUARDAR IMAGEN
# =====================================

async def guardar_imagen(imagen: UploadFile):

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

    return ruta, f"/media/noticias/{nombre}"


# =====================================
# LISTAR NOTICIAS
# =====================================

@router.get("/")
def listar_noticias(db: Session = Depends(get_db)):
    return (
        db.query(models.Noticia)
        .order_by(
            models.Noticia.fecha.desc(),
            models.Noticia.id.desc()
        )
        .all()
    )


# =====================================
# CREAR NOTICIA DEMO (CONSERVADA)
# =====================================

@router.post("/crear")
def crear_noticia(
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    noticia = models.Noticia(
        titulo="Día de la parroquia",
        contenido="Celebración con actividades, música y convivencia.",
        fecha=datetime.utcnow(),
        imagen="https://images.unsplash.com/photo-1507692049790-de58290a4334"
    )

    db.add(noticia)
    db.commit()
    db.refresh(noticia)

    return noticia


# =====================================
# CREAR NOTICIA JSON (COMPATIBILIDAD)
# =====================================

@router.post("/")
def crear_noticia_admin(
    titulo: str = Body(...),
    contenido: str = Body(...),
    imagen: str = Body(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    noticia = models.Noticia(
        titulo=titulo,
        contenido=contenido,
        fecha=datetime.utcnow(),
        imagen=imagen
    )

    db.add(noticia)
    db.commit()
    db.refresh(noticia)

    return noticia


# =====================================
# CREAR NOTICIA CON IMAGEN
# =====================================

@router.post("/publicar")
async def publicar_noticia(
    titulo: str = Form(...),
    contenido: str = Form(...),
    imagen_url: str = Form(""),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    ruta_guardada = None
    url_final = imagen_url.strip() or None

    try:
        if imagen is not None and imagen.filename:
            ruta_guardada, url_final = await guardar_imagen(imagen)

        noticia = models.Noticia(
            titulo=titulo.strip(),
            contenido=contenido.strip(),
            fecha=datetime.utcnow(),
            imagen=url_final
        )

        db.add(noticia)
        db.commit()
        db.refresh(noticia)

    except Exception:
        db.rollback()

        if ruta_guardada is not None:
            try:
                os.remove(ruta_guardada)
            except OSError:
                pass

        raise

    return noticia


# =====================================
# EDITAR NOTICIA
# =====================================

@router.put("/{noticia_id}")
async def actualizar_noticia(
    noticia_id: int,
    titulo: str = Form(...),
    contenido: str = Form(...),
    imagen_url: str = Form(""),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    noticia = obtener_noticia(db, noticia_id)
    ruta_guardada = None

    try:
        if imagen is not None and imagen.filename:
            ruta_guardada, nueva_url = await guardar_imagen(imagen)
            noticia.imagen = nueva_url

        elif imagen_url.strip():
            noticia.imagen = imagen_url.strip()

        noticia.titulo = titulo.strip()
        noticia.contenido = contenido.strip()

        # Conservamos la fecha original de publicación
        db.commit()
        db.refresh(noticia)

    except Exception:
        db.rollback()

        if ruta_guardada is not None:
            try:
                os.remove(ruta_guardada)
            except OSError:
                pass

        raise

    return noticia


# =====================================
# CREAR NOTICIA DEMO (CONSERVADA)
# =====================================

@router.post("/crear-demo")
def crear_noticia_demo(
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    noticia = models.Noticia(
        titulo="Día de la parroquia",
        contenido="Celebración con actividades, música y convivencia.",
        fecha=datetime.utcnow(),
        imagen="https://images.unsplash.com/photo-1507692049790-de58290a4334"
    )

    db.add(noticia)
    db.commit()
    db.refresh(noticia)

    return noticia


# =====================================
# ELIMINAR NOTICIA
# =====================================

@router.delete("/{noticia_id}")
def eliminar_noticia(
    noticia_id: int,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    noticia = obtener_noticia(db, noticia_id)

    db.delete(noticia)
    db.commit()

    return {"mensaje": "Noticia eliminada"}
