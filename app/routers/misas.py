"""Rutas de misas (definitivas)."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
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


def _assert_unique_datetime(db: Session, fecha: datetime, skip_id: int | None = None):
    q = db.query(models.Misa).filter(
        models.Misa.fecha == fecha,
        models.Misa.parroquia_id == PARROQUIA_ID
    )
    if skip_id:
        q = q.filter(models.Misa.id != skip_id)
    if db.query(q.exists()).scalar():
        raise HTTPException(status_code=409, detail="Ya existe una misa en esa fecha/hora.")


# ─────────────────────────────────────────────
# ✝️ CALENDARIO + FIESTAS PARROQUIA
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

    # 🔥 1. FIESTAS PARROQUIALES (PRIORIDAD TOTAL)
    fiesta = db.query(models.FiestaParroquia).filter(
        models.FiestaParroquia.fecha == fecha.date(),
        models.FiestaParroquia.parroquia_id == PARROQUIA_ID
    ).first()

    if fiesta:
        return {
            "tiempo": "fiesta_local",
            "color": fiesta.color,
            "celebracion": f"🎉 {fiesta.nombre}"
        }

    # 🔥 2. CALENDARIO UNIVERSAL
    year = fecha.year

    pascua = calcular_pascua(year)
    ceniza = pascua - timedelta(days=46)
    domingo_ramos = pascua - timedelta(days=7)
    jueves_santo = pascua - timedelta(days=3)
    viernes_santo = pascua - timedelta(days=2)
    vigilia = pascua - timedelta(days=1)
    pentecostes = pascua + timedelta(days=49)

    navidad = datetime(year, 12, 25)
    epifania = datetime(year, 1, 6)

    adviento_inicio = navidad - timedelta(days=(navidad.weekday() + 1) % 7 + 21)

    if fecha >= adviento_inicio and fecha < navidad:
        tiempo = "adviento"
        color = "morado"

    elif fecha >= navidad or fecha < ceniza:
        tiempo = "navidad"
        color = "blanco"

    elif fecha >= ceniza and fecha < domingo_ramos:
        tiempo = "cuaresma"
        color = "morado"

    elif fecha >= domingo_ramos and fecha < pascua:
        tiempo = "semana_santa"
        color = "rojo"

    elif fecha >= pascua and fecha <= pentecostes:
        tiempo = "pascua"
        color = "blanco"

    else:
        tiempo = "tiempo_ordinario"
        color = "verde"

    celebracion = None

    # CELEBRACIONES UNIVERSALES
    if fecha.date() == navidad.date():
        celebracion = "🎄 Navidad"

    elif fecha.date() == epifania.date():
        celebracion = "⭐ Epifanía del Señor"

    elif fecha.date() == domingo_ramos.date():
        celebracion = "🌿 Domingo de Ramos"
        color = "rojo"

    elif fecha.date() == jueves_santo.date():
        celebracion = "🍞 Jueves Santo"

    elif fecha.date() == viernes_santo.date():
        celebracion = "✝ Viernes Santo"
        color = "rojo"

    elif fecha.date() == vigilia.date():
        celebracion = "🔥 Vigilia Pascual"

    elif fecha.date() == pascua.date():
        celebracion = "✨ Domingo de Pascua"

    elif fecha.date() == pentecostes.date():
        celebracion = "🔥 Pentecostés"
        color = "rojo"

    # ROSA
    if fecha.weekday() == 6:

        if tiempo == "adviento":
            tercer_domingo = adviento_inicio + timedelta(days=14)
            if fecha.date() == tercer_domingo.date():
                color = "rosa"

        if tiempo == "cuaresma":
            cuarto_domingo = ceniza + timedelta(days=21)
            if fecha.date() == cuarto_domingo.date():
                color = "rosa"

    return {
        "tiempo": tiempo,
        "color": color,
        "celebracion": celebracion
    }


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

        if lit["celebracion"]:
            misa.descripcion = lit["celebracion"]

    return result


# ─────────────────────────────────────────────
# ACTUALIZAR
# ─────────────────────────────────────────────
@router.patch("/{misa_id}", response_model=schemas.MisaOut)
def actualizar_misa(
    misa_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    x_admin: str = Header(None)
):
    check_admin(x_admin)

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
def regenerar_calendario(db: Session = Depends(get_db)):
    generar_misas(db, semanas=12, parroquia_id=PARROQUIA_ID)
    return {"detail": "Calendario regenerado"}
    
    # ─────────────────────────────────────────────
# 🔧 DEBUG: CREAR FIESTA PARROQUIAL (TEMPORAL)
# ─────────────────────────────────────────────
@router.get("/debug/crear-fiesta")
def crear_fiesta_debug(db: Session = Depends(get_db)):

    from datetime import date

    fiesta = models.FiestaParroquia(
        parroquia_id=1,
        fecha=date(2026, 3, 31),  # 👈 fecha que estás viendo
        nombre="Fiesta parroquial prueba",
        color="rojo"
    )

    db.add(fiesta)
    db.commit()

    return {"ok": "fiesta creada"}