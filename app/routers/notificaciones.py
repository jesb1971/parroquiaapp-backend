
# =====================================
# NOTIFICACIONES PUSH - PARROQUIAAPP
# =====================================

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models


router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones Push"]
)


# =====================================
# DATOS DE REGISTRO
# =====================================

class DispositivoDatos(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    plataforma: str = "android"


# =====================================
# REGISTRAR DISPOSITIVO
# =====================================

# @router.post("/registrar")
def registrar_dispositivo(
    datos: DispositivoDatos,
    db: Session = Depends(get_db)
):

    if datos.plataforma != "android":
        raise HTTPException(
            status_code=400,
            detail="Plataforma no permitida."
        )

    dispositivo = (
        db.query(models.DispositivoPush)
        .filter(
            models.DispositivoPush.token == datos.token
        )
        .first()
    )

    if dispositivo:

        dispositivo.activo = True
        dispositivo.actualizado_at = datetime.utcnow()

        db.commit()

        return {
            "mensaje": "Dispositivo actualizado correctamente."
        }

    nuevo_dispositivo = models.DispositivoPush(
        token=datos.token,
        plataforma="android",
        activo=True
    )

    db.add(nuevo_dispositivo)
    db.commit()

    return {
        "mensaje": "Dispositivo registrado correctamente."
    }
