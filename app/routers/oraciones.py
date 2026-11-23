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

# Almacenamiento persistente de audios
AUDIOS_DIR = Path("/var/data/oraciones/audios")

MAX_AUDIO_BYTES = 30 * 1024 * 1024

FORMATOS_AUDIO = {
    ".opus": "audio/ogg",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".mpeg": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac"
}

TIPOS_AUDIO = {
    ".opus": {"audio/ogg", "audio/opus", "application/ogg"},
    ".ogg": {"audio/ogg", "application/ogg"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".mpeg": {"audio/mpeg", "audio/mp3", "audio/x-mpeg", "video/mpeg"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".aac": {"audio/aac", "audio/x-aac"}
}


# =====================================
# FECHA ACTUAL DE CANARIAS
# =====================================

def fecha_actual_canarias():
    return datetime.now(
        ZoneInfo("Atlantic/Canary")
    ).date()


# =====================================
# CONVERTIR FECHA Y HORA DE CANARIAS A UTC
# =====================================

def convertir_canarias_utc(fecha_hora: datetime) -> datetime:
    if fecha_hora.tzinfo is None:
        fecha_hora = fecha_hora.replace(
            tzinfo=ZoneInfo("Atlantic/Canary")
        )

    return fecha_hora.astimezone(
        ZoneInfo("UTC")
    ).replace(tzinfo=None)


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
# GUARDAR AUDIO DE LA ORACIÓN
# =====================================

async def guardar_audio_oracion(audio: UploadFile):
    extension = Path(audio.filename).suffix.lower()

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
        valido = len(datos) >= 12 and datos[4:8] == b"ftyp"
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

    return ruta, f"/media/oraciones/audios/{nombre}"


# =====================================
# CREAR Y PROGRAMAR ORACIÓN
# =====================================

@router.post("/publicar")
async def publicar_oracion(
    fecha: date = Form(...),
    programado_at: datetime | None = Form(None),
    titulo: str = Form(...),
    contenido: str = Form(...),
    autor: str = Form(""),
    imagen: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
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

    # Validar campos obligatorios
    if not titulo.strip() or not contenido.strip():
        raise HTTPException(
            status_code=400,
            detail="El título y el contenido son obligatorios."
        )

    # Convertir la programación de Canarias a UTC
    fecha_programada_utc = (
        convertir_canarias_utc(programado_at)
        if programado_at is not None
        else None
    )

    # Impedir programaciones con fechas pasadas
    if fecha_programada_utc is not None:
        ahora_utc = datetime.now(
            ZoneInfo("UTC")
        ).replace(tzinfo=None)

        if fecha_programada_utc <= ahora_utc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "La fecha y hora programadas "
                    "deben ser futuras."
                )
            )

    ruta_guardada = None
    imagen_url = None
    ruta_audio_guardado = None
    audio_url = None

    try:
        # Guardar imagen si se ha seleccionado
        if imagen is not None and imagen.filename:
            ruta_guardada, imagen_url = (
                await guardar_imagen_oracion(imagen)
            )

        # Guardar audio si se ha seleccionado
        if audio is not None and audio.filename:
            ruta_audio_guardado, audio_url = (
                await guardar_audio_oracion(audio)
            )

        # Crear oración
        oracion = models.OracionDiaria(
            fecha=fecha,
            titulo=titulo.strip(),
            contenido=contenido.strip(),
            autor=autor.strip() or None,
            imagen=imagen_url,
            audio_url=audio_url,
            programado_at=fecha_programada_utc
        )

        db.add(oracion)
        db.flush()

        # Registrar notificación automática
        # únicamente para publicaciones programadas
        if fecha_programada_utc is not None:
            db.add(
                models.NotificacionOracionDiaria(
                    oracion_id=oracion.id,
                    programado_at=fecha_programada_utc,
                    estado="pendiente"
                )
            )

        # Guardar oración y notificación
        # en una misma transacción
        db.commit()
        db.refresh(oracion)

    except Exception:
        db.rollback()

        # Eliminar imagen nueva si falla el guardado
        if ruta_guardada is not None:
            try:
                os.remove(ruta_guardada)
            except OSError:
                pass

        if ruta_audio_guardado is not None:
            try:
                os.remove(ruta_audio_guardado)
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
    ahora_utc = datetime.utcnow()

    oracion = (
        db.query(models.OracionDiaria)
        .filter(
            models.OracionDiaria.fecha <= hoy,
            (
                models.OracionDiaria.programado_at.is_(None)
                | (models.OracionDiaria.programado_at <= ahora_utc)
            )
        )
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
    ahora_utc = datetime.utcnow()

    oraciones = (
        db.query(models.OracionDiaria)
        .filter(
            models.OracionDiaria.fecha <= hoy,
            (
                models.OracionDiaria.programado_at.is_(None)
                | (models.OracionDiaria.programado_at <= ahora_utc)
            )
        )
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
    programado_at: datetime | None = Form(None),
    titulo: str = Form(...),
    contenido: str = Form(...),
    autor: str = Form(""),
    imagen: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
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

    # Conservar la programación original.
    programacion_original = oracion.programado_at

    nueva_programacion = (
        convertir_canarias_utc(programado_at)
        if programado_at is not None
        else None
    )

    # Consultar la notificación existente.
    notificacion = (
        db.query(models.NotificacionOracionDiaria)
        .filter(
            models.NotificacionOracionDiaria.oracion_id == oracion.id
        )
        .first()
    )

    # Conservar la programación de notificaciones
    # que ya se hayan procesado o estén en proceso.
    if (
        notificacion is not None
        and notificacion.estado in (
            "enviada",
            "parcial",
            "procesando"
        )
    ):
        if nueva_programacion is None:
            nueva_programacion = programacion_original

        elif nueva_programacion != programacion_original:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Esta oración ya tiene una notificación "
                    "enviada o en proceso. No se puede "
                    "modificar su programación."
                )
            )

    # Validar nuevas programaciones.
    if (
        nueva_programacion is not None
        and nueva_programacion != programacion_original
        and nueva_programacion <= datetime.now(
            ZoneInfo("UTC")
        ).replace(tzinfo=None)
    ):
        raise HTTPException(
            status_code=400,
            detail="La fecha y hora programadas deben ser futuras."
        )

    ruta_guardada = None
    ruta_audio_guardado = None

    try:
        # Guardar una imagen nueva si se ha seleccionado.
        if imagen is not None and imagen.filename:
            ruta_guardada, nueva_url = (
                await guardar_imagen_oracion(imagen)
            )
            oracion.imagen = nueva_url

        # Sustituir el audio solo si se selecciona uno nuevo.
        # Si no, conservar el audio anterior.
        if audio is not None and audio.filename:
            ruta_audio_guardado, nueva_audio_url = (
                await guardar_audio_oracion(audio)
            )
            oracion.audio_url = nueva_audio_url

        # Actualizar los datos de la oración.
        oracion.fecha = fecha
        oracion.titulo = titulo.strip()
        oracion.contenido = contenido.strip()
        oracion.autor = autor.strip() or None
        oracion.programado_at = nueva_programacion

        # Gestionar la notificación pendiente.
        if nueva_programacion is not None:

            if notificacion is None:
                db.add(
                    models.NotificacionOracionDiaria(
                        oracion_id=oracion.id,
                        programado_at=nueva_programacion,
                        estado="pendiente"
                    )
                )

            elif notificacion.estado == "pendiente":
                notificacion.programado_at = nueva_programacion

        elif (
            notificacion is not None
            and notificacion.estado == "pendiente"
        ):
            db.delete(notificacion)

        # Guardar todos los cambios en una transacción.
        db.commit()
        db.refresh(oracion)

    except Exception:
        db.rollback()

        # Eliminar la imagen nueva si falla el guardado.
        if ruta_guardada is not None:
            try:
                os.remove(ruta_guardada)
            except OSError:
                pass

        if ruta_audio_guardado is not None:
            try:
                os.remove(ruta_audio_guardado)
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
