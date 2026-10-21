
"""Rutas de evangelización de ParroquiaApp."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4
import os

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    File,
    UploadFile,
    HTTPException
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.schemas import ContenidoOut
from app import models
from app.db import get_db
from app.security import exigir_administrador


router = APIRouter(tags=["evangelizacion"])
templates = Jinja2Templates(directory="app/templates")


# =====================================
# ALMACENAMIENTO PERSISTENTE
# =====================================

BASE_DIR = Path("/var/data/evangelizacion")
IMAGENES_DIR = BASE_DIR / "imagenes"
AUDIOS_DIR = BASE_DIR / "audios"

MAX_IMAGEN_BYTES = 5 * 1024 * 1024
MAX_AUDIO_BYTES = 30 * 1024 * 1024

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
    ".mpeg": {
        "audio/mpeg",
        "audio/mp3",
        "audio/x-mpeg",
        "video/mpeg"
    },
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".aac": {"audio/aac", "audio/x-aac"}
}


# =====================================
# CONSULTAS
# =====================================

def consultar_reflexiones(db):
    return (
        db.query(models.Contenido)
        .filter(models.Contenido.tipo == "reflexion")
        .filter(models.Contenido.publicado_at.isnot(None))
        .order_by(
            models.Contenido.publicado_at.desc(),
            models.Contenido.id.desc()
        )
    )


def obtener_publicacion(db, publicacion_id):
    publicacion = (
        db.query(models.Contenido)
        .filter(models.Contenido.id == publicacion_id)
        .filter(models.Contenido.tipo == "reflexion")
        .first()
    )

    if not publicacion:
        raise HTTPException(
            status_code=404,
            detail="Publicación no encontrada."
        )

    return publicacion


def separar_contenido(cuerpo):
    """Recupera los campos del contenido existente."""
    texto = cuerpo or ""
    cita = ""
    pregunta = ""
    partes_reflexion = []

    for bloque in texto.split("\n\n"):
        bloque = bloque.strip()

        if bloque.startswith("📖 "):
            cita = bloque[2:].strip()
        elif bloque.startswith("❓ "):
            pregunta = bloque[2:].strip()
        elif bloque.startswith("🎧 Audio:"):
            continue
        elif bloque:
            partes_reflexion.append(bloque)

    return {
        "cita_biblica": cita,
        "reflexion": "\n\n".join(partes_reflexion),
        "pregunta_reflexion": pregunta
    }


def construir_contenido(cita, reflexion, pregunta):
    partes = []

    if cita.strip():
        partes.append(f"📖 {cita.strip()}")

    partes.append(reflexion.strip())

    if pregunta.strip():
        partes.append(f"❓ {pregunta.strip()}")

    return "\n\n".join(partes)


# =====================================
# API: REFLEXIÓN DEL DÍA
# =====================================

@router.get("/evangelizacion/hoy", response_model=ContenidoOut)
def contenido_hoy(db: Session = Depends(get_db)):

    item = consultar_reflexiones(db).first()

    if item:
        return item

    return ContenidoOut(
        id=0,
        tipo="reflexion",
        titulo="Dios habla en lo pequeño",
        cuerpo_md=(
            '**Versículo**: Sal 46:10 — '
            '"Estad quietos, y conoced que yo soy Dios".\n\n'
            "**Reflexión (1 min)**: En el silencio cotidiano "
            "aprendemos a reconocer su voz."
        ),
        publicado_at=datetime.utcnow()
    )


# =====================================
# VISTA PÚBLICA
# =====================================

@router.get("/evangelizacion")
def evangelizacion_view(
    request: Request,
    db: Session = Depends(get_db)
):

    publicaciones = consultar_reflexiones(db).all()

    return templates.TemplateResponse(
        "evangelizacion.html",
        {
            "request": request,
            "contenido": (
                publicaciones[0] if publicaciones else None
            ),
            "publicaciones": publicaciones
        }
    )
    

# =====================================
# VISTA INDIVIDUAL DE REFLEXIÓN
# =====================================

@router.get("/evangelizacion/{publicacion_id}")
def ver_reflexion(
    publicacion_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    publicacion = (
        consultar_reflexiones(db)
        .filter(models.Contenido.id == publicacion_id)
        .first()
    )

    if publicacion is None:
        raise HTTPException(
            status_code=404,
            detail="La reflexión no existe."
        )

    return templates.TemplateResponse(
        "evangelizacion_detalle.html",
        {
            "request": request,
            "publicacion": publicacion
        }
    )



# =====================================
# PANEL ADMINISTRADOR
# =====================================

@router.get("/admin/evangelizacion")
def admin_evangelizacion(
    request: Request,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    publicaciones = consultar_reflexiones(db).all()

    return templates.TemplateResponse(
        "admin_evangelizacion.html",
        {
            "request": request,
            "publicaciones": publicaciones
        }
    )


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

    return ruta, f"/media/evangelizacion/{nombre}"


# =====================================
# GUARDAR AUDIO
# =====================================

async def guardar_audio(audio: UploadFile):

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

    return ruta, f"/media/evangelizacion/audios/{nombre}"


# =====================================
# CREAR PUBLICACIÓN
# =====================================

@router.post("/admin/evangelizacion/crear")
async def crear_publicacion(
    titulo: str = Form(...),
    cita_biblica: str = Form(""),
    reflexion: str = Form(...),
    pregunta_reflexion: str = Form(""),
    imagen: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    imagen_url = None
    audio_url = None
    archivos_guardados = []

    try:
        if imagen is not None and imagen.filename:
            ruta, imagen_url = await guardar_imagen(imagen)
            archivos_guardados.append(ruta)

        if audio is not None and audio.filename:
            ruta, audio_url = await guardar_audio(audio)
            archivos_guardados.append(ruta)

        nuevo = models.Contenido(
            tipo="reflexion",
            titulo=titulo.strip(),
            cuerpo_md=construir_contenido(
                cita_biblica,
                reflexion,
                pregunta_reflexion
            ),
            imagen_url=imagen_url,
            audio_url=audio_url,
            publicado_at=datetime.utcnow()
        )

        db.add(nuevo)
        db.commit()

    except Exception:
        db.rollback()

        for ruta in archivos_guardados:
            try:
                os.remove(ruta)
            except OSError:
                pass

        raise

    return RedirectResponse(
        url="/admin/evangelizacion",
        status_code=303
    )


# =====================================
# FORMULARIO DE EDICIÓN
# =====================================

@router.get("/admin/evangelizacion/editar/{publicacion_id}")
def formulario_edicion(
    publicacion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    publicacion = obtener_publicacion(db, publicacion_id)

    campos = separar_contenido(publicacion.cuerpo_md)

    return templates.TemplateResponse(
        "editar_evangelizacion.html",
        {
            "request": request,
            "publicacion": publicacion,
            **campos
        }
    )


# =====================================
# GUARDAR EDICIÓN
# =====================================

@router.post("/admin/evangelizacion/editar/{publicacion_id}")
async def guardar_edicion(
    publicacion_id: int,
    titulo: str = Form(...),
    cita_biblica: str = Form(""),
    reflexion: str = Form(...),
    pregunta_reflexion: str = Form(""),
    imagen: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    publicacion = obtener_publicacion(db, publicacion_id)
    archivos_guardados = []

    try:
        if imagen is not None and imagen.filename:
            ruta, imagen_url = await guardar_imagen(imagen)
            archivos_guardados.append(ruta)
            publicacion.imagen_url = imagen_url

        if audio is not None and audio.filename:
            ruta, audio_url = await guardar_audio(audio)
            archivos_guardados.append(ruta)
            publicacion.audio_url = audio_url

        publicacion.titulo = titulo.strip()
        publicacion.cuerpo_md = construir_contenido(
            cita_biblica,
            reflexion,
            pregunta_reflexion
        )

        db.commit()

    except Exception:
        db.rollback()

        for ruta in archivos_guardados:
            try:
                os.remove(ruta)
            except OSError:
                pass

        raise

    return RedirectResponse(
        url="/admin/evangelizacion",
        status_code=303
    )


# =====================================
# ELIMINAR PUBLICACIÓN
# =====================================

@router.post("/admin/evangelizacion/eliminar/{publicacion_id}")
def eliminar_publicacion(
    publicacion_id: int,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    publicacion = obtener_publicacion(db, publicacion_id)

    db.delete(publicacion)
    db.commit()

    return RedirectResponse(
        url="/admin/evangelizacion",
        status_code=303
    )
