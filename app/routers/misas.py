"""Rutas de misas (definitivas)."""
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from ..db import get_db
from .. import models, schemas
from ..services.misas_scheduler import generar_misas

router = APIRouter(prefix="/misas", tags=["misas"])
PARROQUIA_ID = 1


# 🔐 ADMIN
def check_admin(x_admin: str = Header(None)):
    if x_admin != "1234":
        raise HTTPException(status_code=403, detail="No autorizado")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ─────────────────────────────────────────────
# ✝️ LITURGIA COMPLETA (AUTOMÁTICA)
# ─────────────────────────────────────────────
def calcular_pascua(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day = ((h + l - 7*m + 114) % 31) + 1
    return datetime(year, month, day)


def obtener_liturgia(fecha: datetime, db: Session) -> dict:

    # 🔥 1. FIESTAS PARROQUIALES (PRIORIDAD)
    inicio_dia = datetime(fecha.year, fecha.month, fecha.day)
    fin_dia = inicio_dia + timedelta(days=1)

    fiesta = db.query(models.FiestaParroquia).filter(
        models.FiestaParroquia.fecha >= inicio_dia.date(),
        models.FiestaParroquia.fecha < fin_dia.date(),
        models.FiestaParroquia.parroquia_id == PARROQUIA_ID
    ).first()

    if fiesta:
        return {
            "tiempo": "fiesta_local",
            "color": fiesta.color,
            "celebracion": fiesta.nombre
        }

    # 🔥 2. CALENDARIO AUTOMÁTICO
    year = fecha.year
    pascua = calcular_pascua(year)
    ceniza = pascua - timedelta(days=46)
    domingo_ramos = pascua - timedelta(days=7)

    # CUARESMA
    if fecha >= ceniza and fecha < domingo_ramos:
        return {"tiempo": "cuaresma", "color": "morado"}

    # SEMANA SANTA
    if fecha >= domingo_ramos and fecha < pascua:
        return {"tiempo": "semana_santa", "color": "rojo"}

    # 🔥 PASCUA COMPLETA (AQUÍ ESTÁ LA MAGIA)
    if fecha >= pascua and fecha <= pascua + timedelta(days=49):

        dias = (fecha - pascua).days

        if dias == 0:
            return {
                "tiempo": "pascua",
                "color": "blanco",
                "celebracion": "Domingo de Pascua"
            }

        if dias < 7:
            nombres = [
                "Lunes de la Octava de Pascua",
                "Martes de la Octava de Pascua",
                "Miércoles de la Octava de Pascua",
                "Jueves de la Octava de Pascua",
                "Viernes de la Octava de Pascua",
                "Sábado de la Octava de Pascua",
            ]
            return {
                "tiempo": "pascua",
                "color": "blanco",
                "celebracion": nombres[dias - 1]
            }

        semana = (dias // 7) + 1

        dias_nombres = {
            0: "Lunes",
            1: "Martes",
            2: "Miércoles",
            3: "Jueves",
            4: "Viernes",
            5: "Sábado",
            6: "Domingo"
        }

        dia_semana = fecha.weekday()
        nombre_dia = dias_nombres[dia_semana]

        if dia_semana == 6:
            return {
                "tiempo": "pascua",
                "color": "blanco",
                "celebracion": f"{semana}º Domingo de Pascua"
            }

        return {
            "tiempo": "pascua",
            "color": "blanco",
            "celebracion": f"{nombre_dia} de la {semana}ª Semana de Pascua"
        }

    # ORDINARIO
    return {"tiempo": "ordinario", "color": "verde"}


# ─────────────────────────────────────────────
# LISTAR
# ─────────────────────────────────────────────
@router.get("/", response_model=list[schemas.MisaOut])
def listar_misas(db: Session = Depends(get_db)):

    result = db.query(models.Misa)\
        .filter(models.Misa.parroquia_id == PARROQUIA_ID)\
        .order_by(models.Misa.fecha.asc())\
        .all()

    for misa in result:
        lit = obtener_liturgia(misa.fecha, db)
        misa.tiempo = lit["tiempo"]
        misa.color = lit["color"]

        if "celebracion" in lit:
            misa.descripcion = lit["celebracion"]

    return result


# ─────────────────────────────────────────────
# ACTUALIZAR
# ─────────────────────────────────────────────
@router.patch("/{misa_id}", response_model=schemas.MisaOut)
def actualizar_misa(
    misa_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db)
):

    if request.cookies.get("admin") != "1":
        raise HTTPException(status_code=403, detail="No autorizado")

    misa = db.query(models.Misa).filter(
        models.Misa.id == misa_id,
        models.Misa.parroquia_id == PARROQUIA_ID
    ).first()

    if not misa:
        raise HTTPException(status_code=404, detail="Misa no encontrada.")

    if "descripcion" in payload:
        misa.descripcion = payload["descripcion"]

    db.commit()
    db.refresh(misa)

    return misa


# ─────────────────────────────────────────────
# REGENERAR
# ─────────────────────────────────────────────
@router.post("/regenerar", status_code=202)
def regenerar_calendario(
    meses: int = Query(3),
    db: Session = Depends(get_db)
):

    # 🧨 BORRAR MISAS
    db.query(models.Misa).filter(
        models.Misa.parroquia_id == PARROQUIA_ID
    ).delete()

    db.commit()

    semanas = meses * 4
    generar_misas(db, semanas=semanas, parroquia_id=PARROQUIA_ID)

    return {"detail": f"Calendario regenerado ({meses} meses)"}