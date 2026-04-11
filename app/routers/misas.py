"""Rutas de misas (definitivas)."""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from ..db import get_db
from .. import models, schemas
from ..services.misas_scheduler import generar_misas

router = APIRouter(prefix="/misas", tags=["misas"])
PARROQUIA_ID = 1


# 🔐 ADMIN (SE MANTIENE, aunque ya no se usa en PATCH)
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
# ✝️ LITURGIA (SIN TOCAR DESCRIPCIÓN)
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

    # 🔥 FIESTAS PARROQUIALES
    fiesta = db.query(models.FiestaParroquia).filter(
        models.FiestaParroquia.fecha == fecha.date(),
        models.FiestaParroquia.parroquia_id == PARROQUIA_ID
    ).first()

    if fiesta:
        return {
        "tiempo": "fiesta_local",
        "color": fiesta.color,
        "celebracion": fiesta.nombre
    }

    # 🔥 CALENDARIO UNIVERSAL
    year = fecha.year
    pascua = calcular_pascua(year)
    ceniza = pascua - timedelta(days=46)
    domingo_ramos = pascua - timedelta(days=7)

    if fecha >= ceniza and fecha < domingo_ramos:
        return {"tiempo": "cuaresma", "color": "morado"}

    elif fecha >= domingo_ramos and fecha < pascua:
        return {"tiempo": "semana_santa", "color": "rojo"}

    elif fecha >= pascua and fecha <= pascua + timedelta(days=49):
        return {"tiempo": "pascua", "color": "blanco"}

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
# ACTUALIZAR (🔒 SEGURIDAD REAL CON COOKIE)
# ─────────────────────────────────────────────
@router.patch("/{misa_id}", response_model=schemas.MisaOut)
def actualizar_misa(
    misa_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db)
):

    # 🔐 VALIDACIÓN REAL
    admin_cookie = request.cookies.get("admin")

    if admin_cookie != "1":
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
from fastapi import Query

@router.post("/regenerar", status_code=202)
def regenerar_calendario(
    meses: int = Query(3),
    db: Session = Depends(get_db)
):

    from datetime import date

    # 🔥 CARGAR FIESTAS AUTOMÁTICAS (SOLO SI NO EXISTEN)
    fiestas = [
        {"fecha": date(2026, 4, 12), "nombre": "Domingo de Pascua", "color": "blanco"},
        {"fecha": date(2026, 4, 19), "nombre": "II Domingo de Pascua", "color": "blanco"},
        {"fecha": date(2026, 4, 26), "nombre": "III Domingo de Pascua", "color": "blanco"},
        {"fecha": date(2026, 5, 24), "nombre": "Pentecostés", "color": "rojo"},
        {"fecha": date(2026, 6, 7), "nombre": "Corpus Christi", "color": "blanco"},
    ]

    for f in fiestas:
        existe = db.query(models.FiestaParroquia).filter(
            models.FiestaParroquia.fecha == f["fecha"],
            models.FiestaParroquia.parroquia_id == PARROQUIA_ID
        ).first()

        if not existe:
            db.add(models.FiestaParroquia(
                parroquia_id=PARROQUIA_ID,
                fecha=f["fecha"],
                nombre=f["nombre"],
                color=f["color"]
            ))

    db.commit()  # 👈 IMPORTANTE (guardar fiestas primero)

    # 🧠 convertir meses → semanas (aprox)
    semanas = meses * 4

    generar_misas(db, semanas=semanas, parroquia_id=PARROQUIA_ID)

    return {"detail": f"Calendario regenerado ({meses} meses)"}
# ─────────────────────────────────────────────
# DEBUG LIMPIO (OPCIONAL)
# ─────────────────────────────────────────────
@router.get("/debug/crear-fiesta")
def crear_fiesta_debug(db: Session = Depends(get_db)):

    from datetime import date

    fiesta = models.FiestaParroquia(
        parroquia_id=1,
        fecha=date(2026, 3, 31),
        nombre="Fiesta parroquial prueba",
        color="rojo"
    )

    db.add(fiesta)
    db.commit()

    return {"ok": "fiesta creada"}