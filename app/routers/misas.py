"""Rutas de misas (definitivas)."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..db import get_db
from .. import models, schemas
from ..services.misas_scheduler import generar_misas

router = APIRouter(prefix="/misas", tags=["misas"])
PARROQUIA_ID = 1  # Cruz del Señor (fijo por ahora)

# --- helpers de normalización ---
def _to_naive_utc(dt: datetime) -> datetime:
    """Convierte a NAIVE en UTC para guardar/filtrar de forma consistente."""
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
# Listar (con filtros sencillos y paginación)
# ─────────────────────────────────────────────
@router.get("/", response_model=list[schemas.MisaOut])
def listar_misas(
    desde: datetime | None = Query(None, description="ISO 8601; si trae TZ se normaliza a UTC"),
    hasta: datetime | None = Query(None, description="ISO 8601; si trae TZ se normaliza a UTC"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if desde is None:
        desde = datetime.utcnow()
    else:
        desde = _to_naive_utc(desde)
    q = (db.query(models.Misa)
           .filter(models.Misa.fecha >= desde,
                   models.Misa.parroquia_id == PARROQUIA_ID))
    if hasta:
        q = q.filter(models.Misa.fecha <= _to_naive_utc(hasta))
    return q.order_by(models.Misa.fecha.asc()).offset(offset).limit(limit).all()

# ─────────────────────────────────────────────
# Próximas misas
# ─────────────────────────────────────────────
@router.get("/proximas", response_model=list[schemas.MisaOut])
def proximas(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    ahora = datetime.utcnow()  # NAIVE UTC
    return (db.query(models.Misa)
              .filter(models.Misa.fecha >= ahora,
                      models.Misa.parroquia_id == PARROQUIA_ID)
              .order_by(models.Misa.fecha.asc())
              .limit(limit)
              .all())

# ─────────────────────────────────────────────
# Obtener por ID
# ─────────────────────────────────────────────
@router.get("/{misa_id}", response_model=schemas.MisaOut)
def obtener_misa(misa_id: int, db: Session = Depends(get_db)):
    misa = db.query(models.Misa).filter(
        models.Misa.id == misa_id,
        models.Misa.parroquia_id == PARROQUIA_ID
    ).first()
    if not misa:
        raise HTTPException(status_code=404, detail="Misa no encontrada.")
    return misa

# ─────────────────────────────────────────────
# Crear
# ─────────────────────────────────────────────
@router.post("/", response_model=schemas.MisaOut, status_code=status.HTTP_201_CREATED)
def crear_misa(payload: schemas.MisaCreate, db: Session = Depends(get_db)):
    payload.fecha = _to_naive_utc(payload.fecha)
    _assert_unique_datetime(db, payload.fecha)
    misa = models.Misa(**payload.model_dump(), parroquia_id=PARROQUIA_ID)
    db.add(misa)
    db.commit()
    db.refresh(misa)
    return misa

# ─────────────────────────────────────────────
# Actualizar
# ─────────────────────────────────────────────
@router.patch("/{misa_id}", response_model=schemas.MisaOut)
def actualizar_misa(misa_id: int, payload: schemas.MisaUpdate, db: Session = Depends(get_db)):
    misa = db.query(models.Misa).filter(
        models.Misa.id == misa_id,
        models.Misa.parroquia_id == PARROQUIA_ID
    ).first()
    if not misa:
        raise HTTPException(status_code=404, detail="Misa no encontrada.")
    changes = payload.model_dump(exclude_unset=True)
    if "fecha" in changes and changes["fecha"] is not None:
        changes["fecha"] = _to_naive_utc(changes["fecha"])
        _assert_unique_datetime(db, changes["fecha"], skip_id=misa_id)
    for k, v in changes.items():
        setattr(misa, k, v)
    db.commit()
    db.refresh(misa)
    return misa

# ─────────────────────────────────────────────
# Eliminar
# ─────────────────────────────────────────────
@router.delete("/{misa_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_misa(misa_id: int, db: Session = Depends(get_db)):
    misa = db.query(models.Misa).filter(
        models.Misa.id == misa_id,
        models.Misa.parroquia_id == PARROQUIA_ID
    ).first()
    if not misa:
        raise HTTPException(status_code=404, detail="Misa no encontrada.")
    db.delete(misa)
    db.commit()
    return

# ─────────────────────────────────────────────
# Regenerar calendario (Cruz del Señor)
# ─────────────────────────────────────────────
@router.post("/regenerar", status_code=202)
def regenerar_calendario(semanas: int = Query(12, ge=1, le=52), db: Session = Depends(get_db)):
    generar_misas(db, semanas=semanas, parroquia_id=PARROQUIA_ID)
    return {"detail": f"Calendario generado para {semanas} semanas"}

# ─────────────────────────────────────────────
# Depuración: listar todo sin filtros (temporal)
# ─────────────────────────────────────────────
@router.get("/debug/all", response_model=list[schemas.MisaOut])
def debug_all(db: Session = Depends(get_db)):
    return (db.query(models.Misa)
              .filter(models.Misa.parroquia_id == PARROQUIA_ID)
              .order_by(models.Misa.fecha.asc())
              .all())
