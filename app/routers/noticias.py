from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db
from .. import models

router = APIRouter(prefix="/noticias", tags=["noticias"])


@router.get("/")
def listar_noticias(db: Session = Depends(get_db)):
    return db.query(models.Noticia).order_by(models.Noticia.fecha.desc()).all()


@router.post("/crear")
def crear_noticia(db: Session = Depends(get_db)):
    noticia = models.Noticia(
        titulo="Noticia de ejemplo",
        contenido="Contenido de prueba",
        fecha=datetime.utcnow()
    )

    db.add(noticia)
    db.commit()
    db.refresh(noticia)

    return noticia