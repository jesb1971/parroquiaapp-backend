# app/services/misas_scheduler.py
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from app.models import Misa

def _combine(d: date, hh: int, mm: int) -> datetime:
    """Devuelve datetime NAIVE (sin tz)."""
    return datetime.combine(d, time(hh, mm))

def _add_if_missing(db: Session, dt: datetime, descripcion: str, parroquia_id: int = 1):
    """Inserta una misa si no existe otra con la misma fecha/hora (NAIVE)."""
    exists = db.query(Misa).filter(Misa.fecha == dt).first()
    if not exists:
        db.add(Misa(
            parroquia_id=parroquia_id,
            fecha=dt,
            descripcion=descripcion,
            es_festiva=False
        ))

def generar_misas(db: Session, semanas: int = 12, parroquia_id: int = 1):
    """
    Genera misas para las próximas `semanas` con el horario de Cruz del Señor:
      - Martes a sábado 19:00 (sábado = 'Misa de víspera')
      - Domingo 10:00 y 12:00
    No crea duplicados si ya existen en esa fecha/hora.
    """
    try:
        hoy = datetime.now().date()  # NAIVE (local)
        fin = hoy + timedelta(weeks=semanas)

        d = hoy
        while d <= fin:
            wd = d.weekday()  # 0=Lun ... 5=Sáb, 6=Dom
            if wd in (1, 2, 3, 4, 5):  # Mar-Sáb
                desc = "Misa de víspera" if wd == 5 else "Misa diaria"
                _add_if_missing(db, _combine(d, 19, 0), desc, parroquia_id)
            if wd == 6:  # Domingo
                _add_if_missing(db, _combine(d, 10, 0), "Misa dominical 10:00", parroquia_id)
                _add_if_missing(db, _combine(d, 12, 0), "Misa dominical 12:00", parroquia_id)
            d += timedelta(days=1)

        db.commit()
    except Exception as e:
        # rollback solo si el objeto tiene rollback()
        if hasattr(db, "rollback"):
            db.rollback()
        raise RuntimeError(f"Error en generar_misas: {type(e).__name__} -> {e}") from e
