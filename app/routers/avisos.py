
"""Rutas de avisos / noticias (MVP)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models, schemas
from app.security import exigir_administrador


router = APIRouter(
    prefix="/avisos",
    tags=["avisos"]
)


# =====================================
# LISTAR AVISOS
# =====================================

@router.get("/", response_model=list[schemas.AvisoOut])
def listar_avisos(db: Session = Depends(get_db)):
    """Devuelve los avisos del más reciente al más antiguo."""

    return (
        db.query(models.Aviso)
        .order_by(models.Aviso.publicado_at.desc())
        .all()
    )


# =====================================
# CREAR AVISO DE PRUEBA
# =====================================

@router.post("/crear", response_model=schemas.AvisoOut)
def crear_aviso_demo(
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    """Crea un aviso de prueba para validar el módulo."""

    aviso = models.Aviso(
        titulo="Aviso de ejemplo",
        cuerpo="Este es un aviso de prueba creado automáticamente.",
        publicado_at=datetime.utcnow(),
        parroquia_id=None,
    )

    db.add(aviso)
    db.commit()
    db.refresh(aviso)

    return aviso


# =====================================
# CREAR AVISO
# =====================================

@router.post("/", response_model=schemas.AvisoOut)
def crear_aviso(
    aviso: schemas.AvisoCreate,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    """Crea un aviso real desde el panel o la API."""

    nuevo_aviso = models.Aviso(
        titulo=aviso.titulo,
        cuerpo=aviso.cuerpo,
        publicado_at=datetime.utcnow(),
        parroquia_id=aviso.parroquia_id,
    )

    db.add(nuevo_aviso)
    db.commit()
    db.refresh(nuevo_aviso)

    return nuevo_aviso


# =====================================
# ACTUALIZAR AVISO
# =====================================

@router.put("/{aviso_id}", response_model=schemas.AvisoOut)
def actualizar_aviso(
    aviso_id: int,
    datos: schemas.AvisoCreate,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    """
    Actualiza el título y la descripción de un aviso.
    Conserva la fecha original de publicación.
    """

    aviso = (
        db.query(models.Aviso)
        .filter(models.Aviso.id == aviso_id)
        .first()
    )

    if aviso is None:
        raise HTTPException(
            status_code=404,
            detail="Aviso no encontrado"
        )

    aviso.titulo = datos.titulo
    aviso.cuerpo = datos.cuerpo

    db.commit()
    db.refresh(aviso)

    return aviso


# =====================================
# ELIMINAR AVISO
# =====================================

@router.delete("/{aviso_id}")
def eliminar_aviso(
    aviso_id: int,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    aviso = (
        db.query(models.Aviso)
        .filter(models.Aviso.id == aviso_id)
        .first()
    )

    if not aviso:
        return {"error": "Aviso no encontrado"}

    db.delete(aviso)
    db.commit()

    return {"mensaje": "Aviso eliminado"}


# =====================================
# CONSULTAR AVISO INDIVIDUAL
# =====================================

@router.get("/{aviso_id}")
def obtener_aviso(
    aviso_id: int,
    db: Session = Depends(get_db)
):

    aviso = (
        db.query(models.Aviso)
        .filter(models.Aviso.id == aviso_id)
        .first()
    )

    if not aviso:
        return {"error": "Aviso no encontrado"}

    return aviso
