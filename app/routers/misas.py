"""Rutas de misas (definitivas)."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..db import get_db
from .. import models, schemas
from ..services.misas_scheduler import generar_misas

router = APIRouter(prefix="/misas", tags=["misas"])
PARROQUIA_ID = 1


# 🔐 ADMIN SIMPLE
def check_admin(x_admin: str = Header(None)):
    if x_admin != "1234":
        raise HTTPException(status_code=403, detail="No autorizado")


# --- helpers ---
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


# 🔥 NUEVO: TIEMPO + COLOR LITÚRGICO
def obtener_liturgia(fecha: datetime) -> dict:

    # --- base ---
    if fecha.month == 12 and fecha.day >= 1:
        tiempo = "adviento"
        color = "morado"

    elif fecha.month in (1, 12):
        tiempo = "navidad"
        color = "blanco"

    elif fecha.month in (2, 3):
        tiempo = "cuaresma"
        color = "morado"

    elif fecha.month in (3, 4):
        tiempo = "semana_santa"
        color = "rojo"

    elif fecha.month in (4, 5):
        tiempo = "pascua"
        color = "blanco"

    else:
        tiempo = "tiempo_ordinario"
        color = "verde"

    # --- 🎯 DOMINGOS ROSA ---
    if fecha.weekday() == 6:

        # Gaudete (Adviento)
        if tiempo == "adviento" and 10 <= fecha.day <= 20:
            color = "rosa"

        # Laetare (Cuaresma)
        if tiempo == "cuaresma" and 10 <= fecha.day <= 25:
            color = "rosa"

    return {
        "tiempo": tiempo,
        "color": color
    }


# ─────────────────────────────────────────────
# LISTAR
# ─────────────────────────────────────────────
@router.get("/", response_model=list[schemas.MisaOut])
def listar_misas(
    desde: datetime | None = Query(None),
    hasta: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if desde is None:
        desde = datetime.utcnow()
    else:
        desde = _to_naive_utc(desde)

    q = db.query(models.Misa).filter(
        models.Misa.fecha >= desde,
        models.Misa.parroquia_id == PARROQUIA_ID
    )

    if hasta:
        q = q.filter(models.Misa.fecha <= _to_naive_utc(hasta))

    result = q.order_by(models.Misa.fecha.asc()).offset(offset).limit(limit).all()

    # 🔥 añadir liturgia
    for misa in result:
        lit = obtener_liturgia(misa.fecha)
        misa.tiempo = lit["tiempo"]
        misa.color = lit["color"]

    return result


# ─────────────────────────────────────────────
# PROXIMAS
# ─────────────────────────────────────────────
@router.get("/proximas", response_model=list[schemas.MisaOut])
def proximas(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    ahora = datetime.utcnow()

    result = db.query(models.Misa)\
        .filter(models.Misa.fecha >= ahora,
                models.Misa.parroquia_id == PARROQUIA_ID)\
        .order_by(models.Misa.fecha.asc())\
        .limit(limit)\
        .all()

    for misa in result:
        lit = obtener_liturgia(misa.fecha)
        misa.tiempo = lit["tiempo"]
        misa.color = lit["color"]

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

    # DESCRIPCIÓN
    if "descripcion" in payload:
        misa.descripcion = payload["descripcion"]

    # HORA
    if "hora" in payload:
        try:
            hora, minuto = map(int, payload["hora"].split(":"))
            nueva_fecha = misa.fecha.replace(hour=hora, minute=minuto)
            _assert_unique_datetime(db, nueva_fecha, skip_id=misa_id)
            misa.fecha = nueva_fecha
        except:
            raise HTTPException(status_code=400, detail="Formato de hora inválido")

    # TIPOS MISAL ROMANO
    if "tipo" in payload:

        tipo = payload["tipo"]

        desc = misa.descripcion.replace("✨ ", "").replace("📌 ", "").replace("✝ ", "")

        if tipo == "ordinaria":
            misa.es_festiva = False
            misa.descripcion = desc

        elif tipo == "dominical":
            misa.es_festiva = True
            misa.descripcion = f"Domingo - {desc}"

        elif tipo == "vespertina":
            misa.es_festiva = True
            misa.descripcion = f"Misa de víspera - {desc}"

        elif tipo == "solemne":
            misa.es_festiva = True
            misa.descripcion = f"✨ Solemne - {desc}"

        elif tipo == "votiva":
            misa.es_festiva = True
            misa.descripcion = f"Votiva - {desc}"

        elif tipo == "difuntos":
            misa.es_festiva = True
            misa.descripcion = f"✝ Difuntos - {desc}"

        elif tipo == "ritual":
            misa.es_festiva = True
            misa.descripcion = f"Ritual - {desc}"

        elif tipo == "accion_gracias":
            misa.es_festiva = True
            misa.descripcion = f"Acción de gracias - {desc}"

        elif tipo == "ninos":
            misa.es_festiva = True
            misa.descripcion = f"Misa con niños - {desc}"

        elif tipo == "envio":
            misa.es_festiva = True
            misa.descripcion = f"📌 Envío - {desc}"

    db.commit()
    db.refresh(misa)

    return misa


# ─────────────────────────────────────────────
# REGENERAR
# ─────────────────────────────────────────────
@router.post("/regenerar", status_code=202)
def regenerar_calendario(semanas: int = Query(12, ge=1, le=52), db: Session = Depends(get_db)):
    generar_misas(db, semanas=semanas, parroquia_id=PARROQUIA_ID)
    return {"detail": f"Calendario generado para {semanas} semanas"}