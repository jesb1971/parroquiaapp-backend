from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db
from .. import models

router = APIRouter(prefix="/noticias", tags=["noticias"])


# 🔹 LISTAR NOTICIAS
@router.get("/")
def listar_noticias(db: Session = Depends(get_db)):
    return db.query(models.Noticia).order_by(models.Noticia.fecha.desc()).all()


# 🔹 CREAR NOTICIA DEMO (NO TOCAMOS)
@router.post("/crear")
def crear_noticia(db: Session = Depends(get_db)):
    noticia = models.Noticia(
        titulo="Día de la parroquia",
        contenido="Celebración con actividades, música y convivencia.",
        fecha=datetime.utcnow(),
        imagen="https://images.unsplash.com/photo-1507692049790-de58290a4334"
    )

    db.add(noticia)
    db.commit()
    db.refresh(noticia)

    return noticia


# 🔹 CREAR NOTICIA DESDE ADMIN (REAL)
@router.post("/")
def crear_noticia_admin(
    titulo: str = Body(...),
    contenido: str = Body(...),
    imagen: str = Body(None),
    db: Session = Depends(get_db)
):
    noticia = models.Noticia(
        titulo=titulo,
        contenido=contenido,
        fecha=datetime.utcnow(),
        imagen=imagen
    )

    db.add(noticia)
    db.commit()
    db.refresh(noticia)

    return noticia


# 🔹 CREAR NOTICIA DEMO (GET)
@router.get("/crear-demo")
def crear_noticia_demo(db: Session = Depends(get_db)):
    noticia = models.Noticia(
        titulo="Día de la parroquia",
        contenido="Celebración con actividades, música y convivencia.",
        fecha=datetime.utcnow(),
        imagen="https://images.unsplash.com/photo-1507692049790-de58290a4334"
    )

    db.add(noticia)
    db.commit()
    db.refresh(noticia)

    return noticia