"""Rutas de misas (definitivas)."""
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import csv
from pathlib import Path
from io import StringIO

from ..db import get_db
from .. import models, schemas
from ..services.misas_scheduler import generar_misas

router = APIRouter(prefix="/misas", tags=["misas"])
PARROQUIA_ID = 1


def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def numero_romano(n):
    romanos = {1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII"}
    return romanos.get(n, str(n))


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


# 🔥 CSV LOCAL
def cargar_calendario_desde_csv(db: Session, year: int):

    ruta = Path("app/data") / f"calendario_{year}.csv"

    if not ruta.exists():
        print(f"⚠️ No existe {ruta}")
        return

    with open(ruta, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            fecha = datetime.strptime(row["fecha"], "%Y-%m-%d").date()

            existe = db.query(models.FiestaParroquia).filter(
                models.FiestaParroquia.fecha == fecha,
                models.FiestaParroquia.parroquia_id == PARROQUIA_ID
            ).first()

            if not existe:
                db.add(models.FiestaParroquia(
                    parroquia_id=PARROQUIA_ID,
                    fecha=fecha,
                    nombre=row["celebracion"],
                    color=row["color"]
                ))

    db.commit()


# 🔥 LITURGIA
def obtener_liturgia(fecha: datetime, db: Session) -> dict:

    # PRIORIDAD: CSV
    fiesta = db.query(models.FiestaParroquia).filter(
        models.FiestaParroquia.fecha == fecha.date(),
        models.FiestaParroquia.parroquia_id == PARROQUIA_ID
    ).first()

    if fiesta:
        return {
            "tiempo": "calendario",
            "color": fiesta.color,
            "celebracion": fiesta.nombre
        }

    year = fecha.year
    pascua = calcular_pascua(year)

    if fecha < pascua or fecha > pascua + timedelta(days=49):
        return {"tiempo": "ordinario", "color": "verde"}

    dias = (fecha - pascua).days
    dia_semana = fecha.weekday()

    # Domingo de Pascua
    if dias == 0:
        return {"tiempo": "pascua", "color": "blanco", "celebracion": "Domingo de Pascua"}

    # Octava
    if 1 <= dias <= 6:
        nombres = [
            "Lunes de la Octava de Pascua",
            "Martes de la Octava de Pascua",
            "Miércoles de la Octava de Pascua",
            "Jueves de la Octava de Pascua",
            "Viernes de la Octava de Pascua",
            "Sábado de la Octava de Pascua",
        ]
        return {"tiempo": "pascua", "color": "blanco", "celebracion": nombres[dias - 1]}

    # 🔥 DOMINGOS CORRECTOS
    domingos = {
        7: "II Domingo de Pascua",
        14: "III Domingo de Pascua",
        21: "IV Domingo de Pascua",
        28: "V Domingo de Pascua",
        35: "VI Domingo de Pascua",
        42: "VII Domingo de Pascua",
        49: "Domingo de Pentecostés"
    }

    if dia_semana == 6 and dias in domingos:
        return {
            "tiempo": "pascua",
            "color": "blanco",
            "celebracion": domingos[dias]
        }

    # Semana normal
    dias_post_octava = dias - 7
    semana = (dias_post_octava // 7) + 2

    nombres_dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

    return {
        "tiempo": "pascua",
        "color": "blanco",
        "celebracion": f"{nombres_dias[dia_semana]} de la {numero_romano(semana)} Semana de Pascua"
    }


# LISTAR
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


# ACTUALIZAR
@router.patch("/{misa_id}", response_model=schemas.MisaOut)
def actualizar_misa(misa_id:int,payload:dict,request:Request,db:Session=Depends(get_db)):
    if request.cookies.get("admin") != "1":
        raise HTTPException(status_code=403)

    misa = db.query(models.Misa).filter(
        models.Misa.id == misa_id,
        models.Misa.parroquia_id == PARROQUIA_ID
    ).first()

    if "descripcion" in payload:
        misa.descripcion = payload["descripcion"]

    db.commit()
    db.refresh(misa)
    return misa


# REGENERAR
@router.post("/regenerar", status_code=202)
def regenerar_calendario(meses:int=Query(3),db:Session=Depends(get_db)):

    # 🔥 LIMPIEZA TOTAL (CLAVE)
    db.query(models.FiestaParroquia).delete()
    db.query(models.Misa).delete()
    db.commit()

    # ❌ CSV desactivado por ahora
    # year = datetime.now().year
    # cargar_calendario_desde_csv(db, year)

    # 🔄 GENERAR MISAS
    semanas = meses * 4
    generar_misas(db, semanas=semanas, parroquia_id=PARROQUIA_ID)

    return {"detail": f"Calendario regenerado ({meses} meses)"}


# 🔥 SUBIR CSV
@router.post("/cargar-calendario")
def cargar_calendario(request: Request, file: UploadFile, db: Session = Depends(get_db)):

    if request.cookies.get("admin") != "1":
        raise HTTPException(status_code=403)

    contenido = file.file.read().decode("utf-8")
    reader = csv.DictReader(StringIO(contenido))

    db.query(models.FiestaParroquia).filter(
        models.FiestaParroquia.parroquia_id == PARROQUIA_ID
    ).delete()

    for row in reader:
        fecha = datetime.strptime(row["fecha"], "%Y-%m-%d").date()

        db.add(models.FiestaParroquia(
            parroquia_id=PARROQUIA_ID,
            fecha=fecha,
            nombre=row["celebracion"],
            color=row["color"]
        ))

    db.commit()

    return {"ok": "Calendario cargado correctamente"}