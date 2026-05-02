from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from app.routers.misas import obtener_liturgia, listar_misas  # 🔥 AÑADIDO listar_misas

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

    # 🔥 CAMBIO CLAVE: usar la lógica del backend
    misas = listar_misas(db)

    # 🔥 APLICAR LITURGIA (lo dejamos de momento, no lo tocamos aún)
    for misa in misas:
        lit = obtener_liturgia(misa.fecha, db)

        misa.color = lit.get("color", "blanco")

        celebracion = lit.get("celebracion", "").strip()

        if celebracion:
            if misa.descripcion and misa.descripcion.strip():
                if celebracion not in misa.descripcion:
                    misa.descripcion = f"{misa.descripcion} | 🎉 {celebracion}"
            else:
                misa.descripcion = f"🎉 {celebracion}"

    return templates.TemplateResponse(
        "misas_demo.html",
        {
            "request": request,
            "misas": misas,
            "parroquia": parroquia,
            "es_admin": admin_cookie == "1"
        }
    )