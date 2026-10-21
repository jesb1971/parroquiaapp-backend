
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

IMAGENES_DIR = Path("/var/data/evangelizacion/imagenes")
MAX_IMAGEN_BYTES = 5 * 1024 * 1024

FORMATOS_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

FIRMAS = {
    ".jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
    ".png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    ".webp": lambda b: (
        b.startswith(b"RIFF") and b[8:12] == b"WEBP"
    )
}


# =====================================
# CONSULTA DE REFLEXIONES
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
# GUARDAR PUBLICACIÓN
# =====================================

@router.post("/admin/evangelizacion/crear")
async def crear_publicacion(
    titulo: str = Form(...),
    cita_biblica: str = Form(""),
    reflexion: str = Form(...),
    pregunta_reflexion: str = Form(""),
    audio_url: str = Form(""),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    imagen_url = None
    ruta_imagen = None

    # Procesar imagen, si se ha seleccionado
    if imagen is not None and imagen.filename:

        extension = FORMATOS_PERMITIDOS.get(
            imagen.content_type
        )

        if not extension:
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten imágenes JPG, PNG o WebP."
            )

        datos = await imagen.read(MAX_IMAGEN_BYTES + 1)

        if len(datos) > MAX_IMAGEN_BYTES:
            raise HTTPException(
                status_code=413,
                detail="La imagen no puede superar los 5 MB."
            )

        if not datos or not FIRMAS[extension](datos):
            raise HTTPException(
                status_code=400,
                detail="El archivo no es una imagen válida."
            )

        IMAGENES_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        nombre_imagen = f"{uuid4().hex}{extension}"
        ruta_imagen = IMAGENES_DIR / nombre_imagen

        try:
            with open(ruta_imagen, "xb") as archivo:
                archivo.write(datos)
        except OSError:
            raise HTTPException(
                status_code=500,
                detail="No se pudo guardar la imagen."
            )

        imagen_url = (
            f"/media/evangelizacion/{nombre_imagen}"
        )

    # Preparar texto
    partes = []

    if cita_biblica.strip():
        partes.append(f"📖 {cita_biblica.strip()}")

    partes.append(reflexion.strip())

    if pregunta_reflexion.strip():
        partes.append(
            f"❓ {pregunta_reflexion.strip()}"
        )

    if audio_url.strip():
        partes.append(f"🎧 Audio:\n{audio_url.strip()}")

    contenido = "\n\n".join(partes)

    # Guardar en base de datos
    try:
        nuevo = models.Contenido(
            tipo="reflexion",
            titulo=titulo.strip(),
            cuerpo_md=contenido,
            imagen_url=imagen_url,
            publicado_at=datetime.utcnow()
        )

        db.add(nuevo)
        db.commit()

    except Exception:
        db.rollback()

        # Evitar archivos huérfanos si falla la BD
        if ruta_imagen is not None:
            try:
                os.remove(ruta_imagen)
            except OSError:
                pass

        raise

    return RedirectResponse(
        url="/admin/evangelizacion",
        status_code=303
    )
