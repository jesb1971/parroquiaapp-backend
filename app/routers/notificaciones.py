
# =====================================
# NOTIFICACIONES PUSH - PARROQUIAAPP
# =====================================

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..db import get_db
from .. import models

from ..firebase_service import enviar_notificaciones_multiples
from firebase_admin import app_check
from ..firebase_service import inicializar_firebase
from ..security import (
    exigir_administrador,
    validar_csrf_formulario
)

from slowapi import Limiter
from slowapi.util import get_remote_address


# =====================================
# LIMITADOR DE SOLICITUDES
# =====================================

limiter = Limiter(
    key_func=get_remote_address
)


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
# DATOS PARA ENVIAR NOTIFICACIONES
# =====================================

class NotificacionDatos(BaseModel):
    titulo: str = Field(
        min_length=1,
        max_length=100
    )

    mensaje: str = Field(
        min_length=1,
        max_length=500
    )

    csrf_token: str = Field(min_length=1)
    csrf_firma: str = Field(min_length=1)


# =====================================
# VALIDAR SEGURIDAD DEL ENVÍO
# =====================================

def comprobar_seguridad_envio(
    request: Request,
    csrf_token: str,
    csrf_firma: str
):
    exigir_administrador(request)

    validar_csrf_formulario(
        request,
        csrf_token,
        csrf_firma
    )

    return True

# =====================================
# VERIFICAR TOKEN FIREBASE APP CHECK
# =====================================

def verificar_app_check(request: Request):

    token = request.headers.get("X-Firebase-AppCheck")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Falta el token de App Check."
        )

    try:
        inicializar_firebase()
        app_check.verify_token(token)

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token de App Check no válido."
        )

    return True



# =====================================
# REGISTRAR DISPOSITIVO
# =====================================

@router.post("/registrar")
@limiter.limit("5/minute")
def registrar_dispositivo(
    request: Request,
    datos: DispositivoDatos,
    db: Session = Depends(get_db),
    app_check_valido: bool = Depends(verificar_app_check)
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

    try:
        db.add(nuevo_dispositivo)
        db.commit()

    except IntegrityError:
        db.rollback()

        return {
            "mensaje": "El dispositivo ya estaba registrado."
        }

    return {
        "mensaje": "Dispositivo registrado correctamente."
    }


# =====================================
# ENVIAR NOTIFICACIONES DESDE ADMIN
# =====================================

@router.post("/enviar")
def enviar_notificacion_admin(
    request: Request,
    datos: NotificacionDatos,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    comprobar_seguridad_envio(
        request,
        datos.csrf_token,
        datos.csrf_firma
    )

    titulo = datos.titulo.strip()
    mensaje = datos.mensaje.strip()

    if not titulo or not mensaje:
        raise HTTPException(
            status_code=400,
            detail="El título y el mensaje son obligatorios."
        )

    dispositivos = (
        db.query(models.DispositivoPush)
        .filter(models.DispositivoPush.activo.is_(True))
        .all()
    )

    if not dispositivos:
        return {
            "mensaje": "No hay dispositivos registrados.",
            "enviados": 0,
            "fallidos": 0
        }

    tokens = [
        dispositivo.token
        for dispositivo in dispositivos
    ]

    resultado = enviar_notificaciones_multiples(
        tokens,
        titulo,
        mensaje
    )

    if resultado["tokens_invalidos"]:
        (
            db.query(models.DispositivoPush)
            .filter(
                models.DispositivoPush.token.in_(
                    resultado["tokens_invalidos"]
                )
            )
            .update(
                {models.DispositivoPush.activo: False},
                synchronize_session=False
            )
        )

        db.commit()

    return {
        "mensaje": "Proceso de envío finalizado.",
        "enviados": resultado["enviados"],
        "fallidos": resultado["fallidos"]
    }
