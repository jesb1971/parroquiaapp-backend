"""Rutas de evangelización (MVP)."""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas import ContenidoOut
from app import models
from app.db import get_db


router = APIRouter(prefix="/evangelizacion", tags=["evangelizacion"])
templates = Jinja2Templates(directory="app/templates")

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
    
@router.get("")
def evangelizacion_view(request: Request, db: Session = Depends(get_db)):

    item = (
        db.query(models.Contenido)
        .filter(models.Contenido.tipo == "reflexion")
        .filter(models.Contenido.publicado_at != None)
        .order_by(models.Contenido.publicado_at.desc())
        .first()
    )

    return templates.TemplateResponse(
        "evangelizacion.html",
        {
            "request": request,
            "contenido": item
        }
    )
    
@router.post("/admin/evangelizacion/crear")
def crear_publicacion(
    titulo: str = Form(...),
    cita_biblica: str = Form(""),
    reflexion: str = Form(...),
    pregunta_reflexion: str = Form(""),
    imagen_url: str = Form(""),
    audio_url: str = Form(""),
    db: Session = Depends(get_db)
):

    contenido = f"""
📖 {cita_biblica}

{reflexion}

❓ {pregunta_reflexion}

🎧 Audio:
{audio_url}
"""

    nuevo = models.Contenido(
        tipo="reflexion",
        titulo=titulo,
        cuerpo_md=contenido,
        imagen_url=imagen_url,
        publicado_at=datetime.utcnow()
    )

    db.add(nuevo)
    db.commit()

    return RedirectResponse(
        url="/admin/evangelizacion",
        status_code=303
    )
