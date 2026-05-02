from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from app.routers.misas import obtener_liturgia  # 🔥 IMPORTANTE

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/demo", response_class=HTMLResponse)
def demo_misas(request: Request, db: Session = Depends(get_db)):

    # 🔐 comprobar login
    admin_cookie = request.cookies.get("admin", "0")

    parroquia = (
        db.query(models.Parroquia)
        .filter(models.Parroquia.id == 1)
        .first()
    )

    misas = (
        db.query(models.Misa)
        .filter(models.Misa.parroquia_id == 1)
        .order_by(models.Misa.fecha.asc())
        .limit(50)
        .all()
    )

    # 🔥 APLICAR LITURGIA (CORRECTO Y COMPLETO)
    for misa in misas:
        lit = obtener_liturgia(misa.fecha, db)

        # ✔ color siempre
        misa.color = lit.get("color", "blanco")

        # ✔ descripción litúrgica
        descripcion_liturgica = f"🎉 {lit['celebracion']}" if "celebracion" in lit else ""

        # ✔ combinar con tipo de misa (lo que viene de BD)
        if misa.descripcion and misa.descripcion.strip():
            misa.descripcion = f"{misa.descripcion} | {descripcion_liturgica}"
        else:
            misa.descripcion = descripcion_liturgica

    return templates.TemplateResponse(
        "misas_demo.html",
        {
            "request": request,
            "misas": misas,
            "parroquia": parroquia,
            "es_admin": admin_cookie == "1"
        }
    )