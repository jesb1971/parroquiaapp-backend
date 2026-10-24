
"""Rutas del módulo Reflexión dominical."""

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

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
# CONFIGURACIÓN DE ARCHIVOS
# =====================================

IMAGENES_DIR = Path("/var/data/reflexiones/imagenes")
AUDIOS_DIR = Path("/var/data/reflexiones/audios")

MAX_IMAGEN_BYTES = 5 * 1024 * 1024
MAX_AUDIO_BYTES = 30 * 1024 * 1024

FORMATOS_IMAGEN = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

FIRMAS_IMAGEN = {
    ".jpg": lambda datos: datos.startswith(b"\xff\xd8\xff"),
    ".png": lambda datos: datos.startswith(b"\x89PNG\r\n\x1a\n"),
    ".webp": lambda datos: (
        datos.startswith(b"RIFF")
        and datos[8:12] == b"WEBP"
    )
}

FORMATOS_AUDIO = {
    ".opus": "audio/ogg",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".mpeg": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac"
}

TIPOS_AUDIO = {
    ".opus": {
        "audio/ogg",
        "audio/opus",
        "application/ogg"
    },
    ".ogg": {
        "audio/ogg",
        "application/ogg"
    },
    ".mp3": {
        "audio/mpeg",
        "audio/mp3"
    },
    ".mpeg": {
        "audio/mpeg",
        "audio/mp3",
        "audio/x-mpeg"
    },
    ".m4a": {
        "audio/mp4",
        "audio/x-m4a"
    },
    ".aac": {
        "audio/aac",
        "audio/x-aac"
    }
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
    audio_url: str | None = Field(
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
    extension = FORMATOS_IMAGEN.get(imagen.content_type)

    if extension is None:
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

    return {
        "imagen": f"/media/reflexiones/{nombre}"
    }


# =====================================
# SUBIR AUDIO
# =====================================

@router.post("/subir-audio")
async def subir_audio_reflexion(
    audio: UploadFile = File(...),
    admin: bool = Depends(exigir_administrador)
):
    extension = Path(audio.filename or "").suffix.lower()

    if extension not in FORMATOS_AUDIO:
        raise HTTPException(
            status_code=400,
            detail="Formato de audio no permitido."
        )

    if audio.content_type not in TIPOS_AUDIO[extension]:
        raise HTTPException(
            status_code=400,
            detail="El tipo de audio no coincide con su extensión."
        )

    datos = await audio.read(MAX_AUDIO_BYTES + 1)

    if len(datos) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El audio supera el límite de 30 MB."
        )

    if not datos:
        raise HTTPException(
            status_code=400,
            detail="El archivo de audio está vacío."
        )

    if extension in {".opus", ".ogg"}:
        valido = datos.startswith(b"OggS")

    elif extension in {".mp3", ".mpeg"}:
        valido = (
            datos.startswith(b"ID3")
            or (
                len(datos) >= 2
                and datos[0] == 0xFF
                and (datos[1] & 0xE0) == 0xE0
            )
        )

    elif extension == ".m4a":
        valido = (
            len(datos) >= 12
            and datos[4:8] == b"ftyp"
        )

    else:
        valido = (
            datos.startswith(b"\xff\xf1")
            or datos.startswith(b"\xff\xf9")
        )

    if not valido:
        raise HTTPException(
            status_code=400,
            detail="El archivo no tiene una cabecera de audio válida."
        )

    AUDIOS_DIR.mkdir(parents=True, exist_ok=True)

    nombre = f"{uuid4().hex}{extension}"
    ruta = AUDIOS_DIR / nombre

    try:
        with open(ruta, "xb") as archivo:
            archivo.write(datos)
    except OSError:
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar el audio."
        )

    return {
        "audio_url": f"/media/reflexiones/audios/{nombre}"
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
        audio_url=datos.audio_url,
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
    reflexion.audio_url = datos.audio_url

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
