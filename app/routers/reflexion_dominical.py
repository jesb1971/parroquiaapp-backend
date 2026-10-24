
"""Rutas del módulo Reflexión dominical."""

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
import os

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    File,
    UploadFile
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from app.security import exigir_administrador


router = APIRouter(
    prefix="/reflexiones-dominicales",
    tags=["Reflexión dominical"]
)


# =====================================
# CONFIGURACIÓN DE IMÁGENES
# =====================================

IMAGENES_DIR = Path(
    "/var/data/reflexiones/imagenes"
)

MAX_IMAGEN_BYTES = 5 * 1024 * 1024

FORMATOS_IMAGEN = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

FIRMAS_IMAGEN = {
    ".jpg": lambda datos: datos.startswith(
        b"\xff\xd8\xff"
    ),
    ".png": lambda datos: datos.startswith(
        b"\x89PNG\r\n\x1a\n"
    ),
    ".webp": lambda datos: (
        datos.startswith(b"RIFF")
        and datos[8:12] == b"WEBP"
    )
}


# =====================================
# DATOS DE ENTRADA
# =====================================

class ReflexionDatos(BaseModel):
    fecha_domingo: date
    titulo: str = Field(min_length=1, max_length=200)
    subtitulo: str | None = Field(
        default=None,
        max_length=300
    )
    contenido: str = Field(min_length=1)
    imagen: str | None = Field(
        default=None,
        max_length=500
    )


# =====================================
# CONSULTAR HISTORIAL
# =====================================

@router.get("/")
def listar_reflexiones(
    db: Session = Depends(get_db)
):
    return (
        db.query(models.ReflexionDominical)
        .order_by(
            models.ReflexionDominical.fecha_domingo.desc(),
            models.ReflexionDominical.id.desc()
        )
        .all()
    )


# =====================================
# SUBIR IMAGEN
# =====================================

@router.post("/subir-imagen")
async def subir_imagen_reflexion(
    imagen: UploadFile = File(...),
    admin: bool = Depends(exigir_administrador)
):
    extension = FORMATOS_IMAGEN.get(
        imagen.content_type
    )

    if extension is None:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten imágenes JPG, PNG o WebP."
        )

    datos = await imagen.read(
        MAX_IMAGEN_BYTES + 1
    )

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

    IMAGENES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

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

    return {
        "imagen": f"/media/reflexiones/{nombre}"
    }


# =====================================
# CONSULTAR UNA REFLEXIÓN
# =====================================

@router.get("/{reflexion_id}")
def obtener_reflexion(
    reflexion_id: int,
    db: Session = Depends(get_db)
):
    reflexion = db.get(
        models.ReflexionDominical,
        reflexion_id
    )

    if reflexion is None:
        raise HTTPException(
            status_code=404,
            detail="Reflexión no encontrada"
        )

    return reflexion


# =====================================
# PUBLICAR REFLEXIÓN
# =====================================

@router.post("/")
def crear_reflexion(
    datos: ReflexionDatos,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    reflexion = models.ReflexionDominical(
        fecha_domingo=datos.fecha_domingo,
        titulo=datos.titulo.strip(),
        subtitulo=datos.subtitulo,
        contenido=datos.contenido.strip(),
        imagen=datos.imagen,
        publicado_at=datetime.utcnow()
    )

    db.add(reflexion)
    db.commit()
    db.refresh(reflexion)

    return reflexion


# =====================================
# EDITAR REFLEXIÓN
# =====================================

@router.put("/{reflexion_id}")
def editar_reflexion(
    reflexion_id: int,
    datos: ReflexionDatos,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    reflexion = db.get(
        models.ReflexionDominical,
        reflexion_id
    )

    if reflexion is None:
        raise HTTPException(
            status_code=404,
            detail="Reflexión no encontrada"
        )

    reflexion.fecha_domingo = datos.fecha_domingo
    reflexion.titulo = datos.titulo.strip()
    reflexion.subtitulo = datos.subtitulo
    reflexion.contenido = datos.contenido.strip()
    reflexion.imagen = datos.imagen

    db.commit()
    db.refresh(reflexion)

    return reflexion


# =====================================
# ELIMINAR REFLEXIÓN
# =====================================

@router.delete("/{reflexion_id}")
def eliminar_reflexion(
    reflexion_id: int,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    reflexion = db.get(
        models.ReflexionDominical,
        reflexion_id
    )

    if reflexion is None:
        raise HTTPException(
            status_code=404,
            detail="Reflexión no encontrada"
        )

    db.delete(reflexion)
    db.commit()

    return {
        "mensaje": "Reflexión eliminada correctamente"
    }
