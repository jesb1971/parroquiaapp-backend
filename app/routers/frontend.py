from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
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