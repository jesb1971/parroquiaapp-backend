# app/routers/frontend.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/demo", response_class=HTMLResponse)
def demo_misas(request: Request, db: Session = Depends(get_db)):
    parroquia = (
        db.query(models.Parroquia)
          .filter(models.Parroquia.id == 1)
          .first()
    )
    misas = (
        db.query(models.Misa)
          .filter(models.Misa.parroquia_id == 1)
          .order_by(models.Misa.fecha.asc())
          .limit(20)
          .all()
    )
    return templates.TemplateResponse(
        "misas_demo.html",
        {"request": request, "misas": misas, "parroquia": parroquia}
    )
