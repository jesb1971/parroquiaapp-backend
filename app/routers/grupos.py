
"""
Módulo Grupos Parroquiales - ParroquiaApp.
Gestión de grupos apostólicos y sus categorías.
"""

from pathlib import Path
from uuid import uuid4
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
    prefix="/api/grupos",
    tags=["Grupos parroquiales"]
)


# =====================================
# CATEGORÍAS PARROQUIALES
# =====================================

CATEGORIAS = [
    "Asociaciones de Laicos",
    "Grupos Acción Caritativa y Social",
    "Grupos de Oración",
    "Grupos de Formación"
]


# =====================================
# CONFIGURACIÓN DE IMÁGENES
# =====================================

IMAGENES_DIR = Path("/var/data/grupos/imagenes")

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
# GUARDAR IMAGEN DEL GRUPO
# =====================================

async def guardar_imagen_grupo(imagen: UploadFile):

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

    return ruta, f"/media/grupos/{nombre}"


# =====================================
# LISTAR GRUPOS PARROQUIALES PÚBLICOS
# =====================================

@router.get("/")
def listar_grupos_publicos(
    db: Session = Depends(get_db)
):
    grupos = (
        db.query(models.GrupoParroquial)
        .filter(models.GrupoParroquial.activo.is_(True))
        .order_by(
            models.GrupoParroquial.orden.asc(),
            models.GrupoParroquial.nombre.asc()
        )
        .all()
    )

    return {
        "categorias": CATEGORIAS,
        "grupos": grupos
    }


# =====================================
# LISTAR TODOS LOS GRUPOS PARA ADMINISTRACIÓN
# =====================================

@router.get("/admin/listado")
def listar_grupos_administracion(
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    grupos = (
        db.query(models.GrupoParroquial)
        .order_by(
            models.GrupoParroquial.orden.asc(),
            models.GrupoParroquial.nombre.asc()
        )
        .all()
    )

    return grupos


# =====================================
# CONSULTAR INFORMACIÓN DE UN GRUPO
# =====================================

@router.get("/{grupo_id}")
def obtener_grupo_publico(
    grupo_id: int,
    db: Session = Depends(get_db)
):
    grupo = (
        db.query(models.GrupoParroquial)
        .filter(
            models.GrupoParroquial.id == grupo_id,
            models.GrupoParroquial.activo.is_(True)
        )
        .first()
    )

    if grupo is None:
        raise HTTPException(
            status_code=404,
            detail="Grupo parroquial no encontrado."
        )

    return grupo


# =====================================
# CREAR GRUPO PARROQUIAL
# =====================================

@router.post("/crear")
async def crear_grupo(
    categoria: str = Form(...),
    nombre: str = Form(...),
    descripcion: str = Form(...),
    orden: int = Form(0),
    activo: bool = Form(True),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    if categoria not in CATEGORIAS:
        raise HTTPException(
            status_code=400,
            detail="La categoría seleccionada no es válida."
        )

    if not nombre.strip() or not descripcion.strip():
        raise HTTPException(
            status_code=400,
            detail="El nombre y la descripción son obligatorios."
        )

    ruta_guardada = None
    imagen_url = None

    try:
        if imagen is not None and imagen.filename:
            ruta_guardada, imagen_url = (
                await guardar_imagen_grupo(imagen)
            )

        grupo = models.GrupoParroquial(
            categoria=categoria,
            nombre=nombre.strip(),
            descripcion=descripcion.strip(),
            imagen=imagen_url,
            orden=orden,
            activo=activo
        )

        db.add(grupo)
        db.commit()
        db.refresh(grupo)

    except Exception:
        db.rollback()

        if ruta_guardada is not None:
            try:
                os.remove(ruta_guardada)
            except OSError:
                pass

        raise

    return grupo


# =====================================
# EDITAR GRUPO PARROQUIAL
# =====================================

@router.put("/{grupo_id}")
async def editar_grupo(
    grupo_id: int,
    categoria: str = Form(...),
    nombre: str = Form(...),
    descripcion: str = Form(...),
    orden: int = Form(0),
    activo: bool = Form(True),
    imagen: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    grupo = (
        db.query(models.GrupoParroquial)
        .filter(models.GrupoParroquial.id == grupo_id)
        .first()
    )

    if grupo is None:
        raise HTTPException(
            status_code=404,
            detail="Grupo parroquial no encontrado."
        )

    if categoria not in CATEGORIAS:
        raise HTTPException(
            status_code=400,
            detail="La categoría seleccionada no es válida."
        )

    if not nombre.strip() or not descripcion.strip():
        raise HTTPException(
            status_code=400,
            detail="El nombre y la descripción son obligatorios."
        )

    ruta_guardada = None

    try:
        if imagen is not None and imagen.filename:
            ruta_guardada, nueva_url = (
                await guardar_imagen_grupo(imagen)
            )
            grupo.imagen = nueva_url

        grupo.categoria = categoria
        grupo.nombre = nombre.strip()
        grupo.descripcion = descripcion.strip()
        grupo.orden = orden
        grupo.activo = activo

        db.commit()
        db.refresh(grupo)

    except Exception:
        db.rollback()

        if ruta_guardada is not None:
            try:
                os.remove(ruta_guardada)
            except OSError:
                pass

        raise

    return grupo


# =====================================
# ELIMINAR GRUPO PARROQUIAL
# =====================================

@router.delete("/{grupo_id}")
def eliminar_grupo(
    grupo_id: int,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    grupo = (
        db.query(models.GrupoParroquial)
        .filter(models.GrupoParroquial.id == grupo_id)
        .first()
    )

    if grupo is None:
        raise HTTPException(
            status_code=404,
            detail="Grupo parroquial no encontrado."
        )

    db.delete(grupo)
    db.commit()

    return {
        "mensaje": "Grupo parroquial eliminado correctamente."
    }
