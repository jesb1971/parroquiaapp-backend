from fastapi import APIRouter, Depends, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models, schemas
from app.routers.misas import listar_misas

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

    misas = listar_misas(db)

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


@router.post("/contacto")
async def enviar_contacto(request: Request, db: Session = Depends(get_db)):

    data = await request.json()

    nuevo = models.Contacto(
        nombre=data.get("nombre"),
        email=data.get("email"),
        mensaje=data.get("mensaje")
    )

    db.add(nuevo)
    db.commit()

    return {"ok": True}


@router.get("/admin/contacto", response_class=HTMLResponse)
def admin_contacto(request: Request, db: Session = Depends(get_db)):

    mensajes = db.query(models.Contacto).order_by(models.Contacto.id.desc()).all()

    return templates.TemplateResponse("admin_contacto.html", {
        "request": request,
        "mensajes": mensajes
    })