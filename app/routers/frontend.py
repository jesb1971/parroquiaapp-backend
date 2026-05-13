from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models, schemas
from app.routers.misas import listar_misas  # 🔥 SOLO esto, quitamos obtener_liturgia

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/demo", response_class=HTMLResponse)
def demo_misas(request: Request, db: Session = Depends(get_db)):

    admin_cookie = request.cookies.get("admin", "0")

    parroquia = (
        db.query(models.Parroquia)
        .filter(models.Parroquia.id == 1)
        .first()
    )

    # 🔥 USAR SOLO LA LÓGICA DEL BACKEND
    misas = listar_misas(db)

    # 🔥 NO tocar liturgia aquí

    return templates.TemplateResponse(
        "misas_demo.html",
        {
            "request": request,
            "misas": misas,
            "parroquia": parroquia,
            "es_admin": admin_cookie == "1"
        }
    )
    
@router.get("/contacto", response_class=HTMLResponse)
def contacto_page(request: Request):
    return templates.TemplateResponse("contacto.html", {"request": request})
    
from sqlalchemy.orm import Session
from fastapi import Depends
from app.db import SessionLocal
from app import models

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/admin/contacto", response_class=HTMLResponse)
def admin_contacto(request: Request, db: Session = Depends(get_db)):

    mensajes = db.query(models.Contacto).order_by(models.Contacto.id.desc()).all()

    return templates.TemplateResponse("admin_contacto.html", {
        "request": request,
        "mensajes": mensajes
    })
    
    from app import schemas

@router.post("/contacto")
def enviar_contacto(data: schemas.ContactoCreate, db: Session = Depends(get_db)):

    nuevo = models.Contacto(
        nombre=data.nombre,
        email=data.email,
        mensaje=data.mensaje
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return {"ok": True}