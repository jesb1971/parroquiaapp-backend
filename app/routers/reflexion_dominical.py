
"""Rutas del módulo Reflexión dominical."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
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
# DATOS DE ENTRADA
# =====================================

class ReflexionDatos(BaseModel):
    fecha_domingo: date
    titulo: str = Field(min_length=1, max_length=200)
    subtitulo: str | None = Field(default=None, max_length=300)
    contenido: str = Field(min_length=1)
    imagen: str | None = Field(default=None, max_length=500)


# =====================================
# CONSULTAR HISTORIAL
# =====================================

@router.get("/")
def listar_reflexiones(db: Session = Depends(get_db)):
    return (
        db.query(models.ReflexionDominical)
        .order_by(
            models.ReflexionDominical.fecha_domingo.desc(),
            models.ReflexionDominical.id.desc()
        )
        .all()
    )


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
