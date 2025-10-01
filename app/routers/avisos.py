"""Rutas de avisos / noticias (MVP)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db
from .. import models, schemas

router = APIRouter(prefix="/avisos", tags=["avisos"])

@router.get("/", response_model=list[schemas.AvisoOut])
def listar_avisos(db: Session = Depends(get_db)):
    """Devuelve los avisos ordenados del más reciente al más antiguo."""
    return (
        db.query(models.Aviso)
        .order_by(models.Aviso.publicado_at.desc())
        .all()
    )

@router.post("/crear", response_model=schemas.AvisoOut)
def crear_aviso_demo(db: Session = Depends(get_db)):
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
