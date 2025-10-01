"""Rutas de evangelización (MVP)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas import ContenidoOut
from app import models
from app.db import get_db

router = APIRouter(prefix="/evangelizacion", tags=["evangelizacion"])

@router.get("/hoy", response_model=ContenidoOut)
def contenido_hoy(db: Session = Depends(get_db)):
    # Por ahora: devolvemos el último publicado si existe; si no, un fallback.
    item = (
        db.query(models.Contenido)
        .filter(models.Contenido.tipo == "reflexion")
        .filter(models.Contenido.publicado_at != None)  # noqa: E711
        .order_by(models.Contenido.publicado_at.desc())
        .first()
    )

    if item:
        return item

    # Fallback (sin guardar en BD) para probar la app:
    return ContenidoOut(
        id=0,
        tipo="reflexion",
        titulo="Dios habla en lo pequeño",
        cuerpo_md=(
            "**Versículo**: Sal 46:10 — \"Estad quietos, y conoced que yo soy Dios\".\n\n"
            "**Reflexión (1 min)**: En el silencio cotidiano aprendemos a reconocer su voz."
        ),
        publicado_at=datetime.utcnow(),
    )
