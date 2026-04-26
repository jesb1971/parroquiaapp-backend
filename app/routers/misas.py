"""Rutas de misas (definitivas)."""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
import csv
from io import StringIO

from ..db import get_db
from .. import models, schemas
from ..services.misas_scheduler import generar_misas

router = APIRouter(prefix="/misas", tags=["misas"])
PARROQUIA_ID = 1


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


# 🔥 ÚNICO ENDPOINT CSV (sin duplicados)
@router.post("/cargar-calendario")
def cargar_calendario(file: UploadFile = File(...), db: Session = Depends(get_db)):

    contenido = file.file.read().decode("utf-8")
    reader = csv.reader(StringIO(contenido), delimiter=';')

    next(reader, None)  # saltar cabecera

    db.query(models.FiestaParroquia).delete()

    insertados = 0

    for row in reader:
        try:
            if len(row) < 3:
                continue

            fecha = datetime.strptime(row[0].strip(), "%Y-%m-%d").date()
            celebracion = row[1].strip().replace('"', '')
            color = row[2].strip()

            db.add(models.FiestaParroquia(
                parroquia_id=PARROQUIA_ID,
                fecha=fecha,
                nombre=celebracion,
                color=color
            ))

            insertados += 1

        except Exception as e:
            print("Error fila:", row, e)

    db.commit()

    return {"ok": f"{insertados} registros insertados"}


# 🔥 LITURGIA (DEFINITIVA Y ESTABLE)
def obtener_liturgia(fecha: datetime, db: Session) -> dict:

    # 🔹 PRIORIDAD 1: CSV
    fiesta = db.query(models.FiestaParroquia).filter(
        models.FiestaParroquia.fecha == fecha.date(),
        models.FiestaParroquia.parroquia_id == PARROQUIA_ID
    ).first()

    if fiesta:
        return {
            "tiempo": "calendario",
            "color": fiesta.color,
            "celebracion": fiesta.nombre,
            "es_memoria": True
        }

    year = fecha.year
    pascua = calcular_pascua(year)

    nombres_dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    dia_semana = fecha.weekday()

    # 🔹 FECHAS CLAVE
    miercoles_ceniza = pascua - timedelta(days=46)
    pentecostes = pascua + timedelta(days=49)
    inicio_ordinario_post = pentecostes + timedelta(days=1)

    # 🔹 BAUTISMO DEL SEÑOR (simplificado)
    bautismo = datetime(year, 1, 12)  # válido en la mayoría de casos prácticos
    inicio_ordinario_pre = bautismo + timedelta(days=1)

    # =========================
    # 🔵 CUARESMA
    # =========================
    if miercoles_ceniza <= fecha < pascua:
        return {
            "tiempo": "cuaresma",
            "color": "morado",
            "celebracion": f"{nombres_dias[dia_semana]} de Cuaresma"
        }

    # =========================
    # 🟡 PASCUA
    # =========================
    dias = (fecha - pascua).days

    if dias == 0:
        return {
            "tiempo": "pascua",
            "color": "blanco",
            "celebracion": "Domingo de Pascua"
        }

    if 1 <= dias <= 6:
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

    if dias <= 49:
        semana = ((dias - 7) // 7) + 2
        return {
            "tiempo": "pascua",
            "color": "blanco",
            "celebracion": f"{nombres_dias[dia_semana]} de la {numero_romano(semana)} Semana de Pascua"
        }

       # =========================
    # 🟢 TIEMPO ORDINARIO (REAL)
    # =========================

    dias_post = (fecha - inicio_ordinario_post).days
    semana_total = 8 + (dias_post // 7)

    # 🔹 Conversión a romano segura
    romanos = {
        1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII",8:"VIII",9:"IX",10:"X",
        11:"XI",12:"XII",13:"XIII",14:"XIV",15:"XV",16:"XVI",17:"XVII",18:"XVIII",
        19:"XIX",20:"XX",21:"XXI",22:"XXII",23:"XXIII",24:"XXIV",25:"XXV",
        26:"XXVI",27:"XXVII",28:"XXVIII",29:"XXIX",30:"XXX",31:"XXXI",
        32:"XXXII",33:"XXXIII",34:"XXXIV"
    }

    semana_romana = romanos.get(semana_total, str(semana_total))

    return {
        "tiempo": "ordinario",
        "color": "verde",
        "celebracion": f"{nombres_dias[dia_semana]} de la {semana_romana} Semana del Tiempo Ordinario"
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

        misa.descripcion = lit.get("celebracion", "Sin descripción")

    return result


# REGENERAR
@router.post("/regenerar", status_code=202)
def regenerar_calendario(meses:int=Query(3),db:Session=Depends(get_db)):

    db.query(models.Misa).delete()
    db.commit()

    semanas = meses * 4
    generar_misas(db, semanas=semanas, parroquia_id=PARROQUIA_ID)

    return {"detail": f"Calendario regenerado ({meses} meses)"}