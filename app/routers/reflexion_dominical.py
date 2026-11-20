
"""Rutas del módulo Reflexión dominical."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
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


# =====================================
# CONVERTIR HORA DE CANARIAS A UTC
# =====================================

def convertir_canarias_utc(fecha_programada):
    if fecha_programada is None:
        return None

    if fecha_programada.tzinfo is None:
        fecha_programada = fecha_programada.replace(
            tzinfo=ZoneInfo("Atlantic/Canary")
        )

    return fecha_programada.astimezone(
        timezone.utc
    ).replace(tzinfo=None)

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
        "audio/x-mpeg",
        "video/mpeg",
        "application/octet-stream"
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
    programado_at: datetime | None = None
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
# CONSULTAR TODAS LAS REFLEXIONES
# SOLO ADMINISTRADOR
# =====================================

@router.get("/admin/todas")
def listar_reflexiones_admin(
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
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
# CONSULTAR REFLEXIONES PUBLICADAS
# =====================================

@router.get("/")
def listar_reflexiones(
    db: Session = Depends(get_db)
):
    instante = datetime.now(timezone.utc).replace(tzinfo=None)

    return (
        db.query(models.ReflexionDominical)
        .filter(
            (models.ReflexionDominical.programado_at.is_(None)) |
            (models.ReflexionDominical.programado_at <= instante)
        )
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

    if (
        reflexion.programado_at is not None
        and reflexion.programado_at > datetime.now(timezone.utc).replace(tzinfo=None)
    ):
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
    instante = datetime.now(timezone.utc).replace(tzinfo=None)
    programado = convertir_canarias_utc(datos.programado_at)

    if programado is not None and programado <= instante:
        raise HTTPException(status_code=400, detail="La fecha programada debe ser futura.")

    reflexion = models.ReflexionDominical(
        fecha_domingo=datos.fecha_domingo,
        programado_at=programado,
        titulo=datos.titulo.strip(),
        subtitulo=datos.subtitulo,
        contenido=datos.contenido.strip(),
        imagen=datos.imagen,
        audio_url=datos.audio_url,
        publicado_at=programado if programado is not None else instante
    )

    try:
        db.add(reflexion)
        db.flush()
        if programado is not None:
            db.add(models.NotificacionReflexionDominical(
                reflexion_id=reflexion.id,
                programado_at=programado,
                estado="pendiente"
            ))
        db.commit()
        db.refresh(reflexion)
    except Exception:
        db.rollback()
        raise

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
    reflexion = db.get(models.ReflexionDominical, reflexion_id)
    if reflexion is None:
        raise HTTPException(status_code=404, detail="Reflexión no encontrada")

    instante = datetime.now(timezone.utc).replace(tzinfo=None)
    nueva_programacion = convertir_canarias_utc(datos.programado_at)
    ya_publicada = (
        reflexion.programado_at is None
        or reflexion.programado_at <= instante
    )
    notificacion = (
        db.query(models.NotificacionReflexionDominical)
        .filter(models.NotificacionReflexionDominical.reflexion_id == reflexion.id)
        .first()
    )

    if ya_publicada and nueva_programacion is not None:
        raise HTTPException(
            status_code=400,
            detail="Una reflexión ya publicada no puede volver a programarse."
        )

    if not ya_publicada and nueva_programacion is not None and nueva_programacion <= instante:
        raise HTTPException(
            status_code=400,
            detail="La fecha programada debe ser futura."
        )

    if not ya_publicada and notificacion is not None and notificacion.estado != "pendiente":
        if nueva_programacion != reflexion.programado_at:
            raise HTTPException(
                status_code=400,
                detail="No se puede modificar una programación ya procesada."
            )

    reflexion.fecha_domingo = datos.fecha_domingo
    reflexion.titulo = datos.titulo.strip()
    reflexion.subtitulo = datos.subtitulo
    reflexion.contenido = datos.contenido.strip()
    reflexion.imagen = datos.imagen
    reflexion.audio_url = datos.audio_url

    if not ya_publicada:
        reflexion.programado_at = nueva_programacion
        if nueva_programacion is None:
            reflexion.publicado_at = instante
            if notificacion is not None and notificacion.estado == "pendiente":
                db.delete(notificacion)
        else:
            reflexion.publicado_at = nueva_programacion
            if notificacion is not None and notificacion.estado == "pendiente":
                notificacion.programado_at = nueva_programacion
            elif notificacion is None:
                db.add(models.NotificacionReflexionDominical(
                    reflexion_id=reflexion.id,
                    programado_at=nueva_programacion,
                    estado="pendiente"
                ))

    try:
        db.commit()
        db.refresh(reflexion)
    except Exception:
        db.rollback()
        raise

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
    reflexion = db.get(models.ReflexionDominical, reflexion_id)
    if reflexion is None:
        raise HTTPException(status_code=404, detail="Reflexión no encontrada")

    try:
        (db.query(models.NotificacionReflexionDominical)
         .filter(models.NotificacionReflexionDominical.reflexion_id == reflexion.id)
         .delete(synchronize_session=False))
        db.delete(reflexion)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"mensaje": "Reflexión eliminada correctamente"}
