# =====================================
# NOTIFICACIONES AUTOMÁTICAS
# EVANGELIZACIÓN - PARROQUIAAPP
# =====================================

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models
from app.db import SessionLocal
from app.firebase_service import enviar_notificaciones_multiples


def ahora_utc():
    """Devuelve la fecha y hora actual en UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =====================================
# BUSCAR NOTIFICACIONES PENDIENTES
# =====================================

def obtener_notificaciones_pendientes(db: Session):
    """
    Localiza las notificaciones de reflexiones programadas
    cuya fecha de publicación ya ha llegado.
    No realiza ningún envío.
    """

    instante = ahora_utc()

    return (
        db.query(models.NotificacionEvangelizacion)
        .join(
            models.Contenido,
            models.NotificacionEvangelizacion.contenido_id == models.Contenido.id
        )
        .filter(
            models.Contenido.tipo == "reflexion",
            models.NotificacionEvangelizacion.estado == "pendiente",
            models.NotificacionEvangelizacion.programado_at <= instante,
            models.Contenido.publicado_at <= instante,
            models.Contenido.programado_at <= instante
        )
        .order_by(
            models.NotificacionEvangelizacion.programado_at.asc()
        )
        .all()
    )


# =====================================
# RESERVAR NOTIFICACIÓN PARA SU ENVÍO
# =====================================

def reservar_notificacion(db: Session, notificacion_id: int):
    """
    Reserva una notificación pendiente de forma atómica.
    Evita que dos procesos la seleccionen para enviar.
    """

    instante = ahora_utc()

    actualizadas = (
        db.query(models.NotificacionEvangelizacion)
        .filter(
            models.NotificacionEvangelizacion.id == notificacion_id,
            models.NotificacionEvangelizacion.estado == "pendiente",
            models.NotificacionEvangelizacion.programado_at <= instante
        )
        .update(
            {
                models.NotificacionEvangelizacion.estado: "procesando",
                models.NotificacionEvangelizacion.iniciado_at: instante,
                models.NotificacionEvangelizacion.intentos:
                    models.NotificacionEvangelizacion.intentos + 1
            },
            synchronize_session=False
        )
    )

    db.commit()

    return actualizadas == 1


# =====================================
# REGISTRAR RESULTADO DEL ENVÍO
# =====================================

def registrar_resultado_envio(
    db: Session,
    notificacion_id: int,
    enviados: int,
    fallidos: int,
    error: str | None = None
):
    """
    Registra el resultado de una notificación procesada.
    No vuelve a enviar notificaciones.
    """

    notificacion = (
        db.query(models.NotificacionEvangelizacion)
        .filter(
            models.NotificacionEvangelizacion.id == notificacion_id,
            models.NotificacionEvangelizacion.estado == "procesando"
        )
        .first()
    )

    if notificacion is None:
        return False

    notificacion.enviados = enviados
    notificacion.fallidos = fallidos
    notificacion.ultimo_error = error
    notificacion.estado = "enviada" if fallidos == 0 else "parcial"
    notificacion.enviado_at = ahora_utc()

    db.commit()

    return True


# =====================================
# ENVIAR NOTIFICACIÓN PROGRAMADA
# =====================================

def enviar_notificacion_programada(db: Session, notificacion_id: int):
    """
    Envía una notificación previamente reservada.
    Registra el resultado y desactiva los tokens inválidos.
    """

    notificacion = (
        db.query(models.NotificacionEvangelizacion)
        .filter(
            models.NotificacionEvangelizacion.id == notificacion_id,
            models.NotificacionEvangelizacion.estado == "procesando"
        )
        .first()
    )

    if notificacion is None:
        return False

    publicacion = (
        db.query(models.Contenido)
        .filter(
            models.Contenido.id == notificacion.contenido_id
        )
        .first()
    )

    if publicacion is None:
        registrar_resultado_envio(
            db, notificacion_id, 0, 0,
            "La publicación ya no existe."
        )
        return False

    dispositivos = (
        db.query(models.DispositivoPush)
        .filter(models.DispositivoPush.activo.is_(True))
        .all()
    )

    tokens = [dispositivo.token for dispositivo in dispositivos]

    if not tokens:
        registrar_resultado_envio(db, notificacion_id, 0, 0)
        return True

    try:
        resultado = enviar_notificaciones_multiples(
            tokens,
            "Nueva reflexión disponible",
            publicacion.titulo[:100]
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

        registrar_resultado_envio(
            db,
            notificacion_id,
            resultado["enviados"],
            resultado["fallidos"]
        )

        return True

    except Exception as error:
        registrar_resultado_envio(
            db,
            notificacion_id,
            0,
            len(tokens),
            str(error)[:500]
        )
        return False


# =====================================
# PROCESAR NOTIFICACIONES PENDIENTES
# =====================================

def procesar_notificaciones_pendientes():
    """
    Comprueba las notificaciones pendientes y procesa
    aquellas cuya fecha programada ya ha llegado.
    """

    db = SessionLocal()

    try:
        # =====================================
        # REVISAR ENVÍOS INTERRUMPIDOS
        # =====================================
        detectar_envios_interrumpidos(db)

        # =====================================
        # OBTENER NOTIFICACIONES PENDIENTES
        # =====================================
        pendientes = obtener_notificaciones_pendientes(db)

        for notificacion in pendientes:
            notificacion_id = notificacion.id

            if reservar_notificacion(db, notificacion_id):
                enviar_notificacion_programada(
                    db,
                    notificacion_id
                )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# =====================================
# DETECTAR ENVÍOS INTERRUMPIDOS
# =====================================

def detectar_envios_interrumpidos(db: Session):
    """
    Identifica envíos que llevan más de 10 minutos
    en procesamiento.

    No los reenvía automáticamente para evitar duplicados.
    """

    limite = ahora_utc() - timedelta(minutes=10)

    registros = (
        db.query(models.NotificacionEvangelizacion)
        .filter(
            models.NotificacionEvangelizacion.estado == "procesando",
            models.NotificacionEvangelizacion.iniciado_at < limite
        )
        .all()
    )

    for registro in registros:
        registro.estado = "revision"
        registro.ultimo_error = (
            "Envío interrumpido o sin confirmación. "
            "Requiere revisión antes de repetirlo."
        )

    if registros:
        db.commit()

    return len(registros)

# =====================================
# EJECUCIÓN PERIÓDICA DE NOTIFICACIONES
# =====================================

import asyncio
import logging

logger = logging.getLogger(__name__)


async def ejecutar_notificaciones_periodicamente():
    """
    Comprueba cada 30 segundos las notificaciones pendientes.

    Ejecuta las operaciones de base de datos y Firebase
    en un hilo independiente para no bloquear FastAPI.
    """

    while True:
        try:
            await asyncio.to_thread(
                procesar_notificaciones_pendientes
            )
            
            await asyncio.to_thread(
                procesar_notificaciones_dominicales
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Error en el procesamiento automático de notificaciones."
            )

        await asyncio.sleep(30)
        
# =====================================
# REFLEXIONES DOMINICALES
# BUSCAR NOTIFICACIONES PENDIENTES
# =====================================

def obtener_notificaciones_dominicales_pendientes(db: Session):
    """
    Busca notificaciones de reflexiones dominicales
    cuya fecha y hora de publicación ya han llegado.
    """

    instante = ahora_utc()

    return (
        db.query(models.NotificacionReflexionDominical)
        .join(
            models.ReflexionDominical,
            models.NotificacionReflexionDominical.reflexion_id
            == models.ReflexionDominical.id
        )
        .filter(
            models.NotificacionReflexionDominical.estado == "pendiente",
            models.NotificacionReflexionDominical.programado_at <= instante,
            models.ReflexionDominical.programado_at <= instante
        )
        .order_by(
            models.NotificacionReflexionDominical.programado_at.asc()
        )
        .all()
    )
    
# =====================================
# REFLEXIONES DOMINICALES
# RESERVAR NOTIFICACIÓN
# =====================================

def reservar_notificacion_dominical(db: Session, notificacion_id: int):
    """
    Reserva una notificación pendiente de forma atómica.
    Evita que dos procesos la envíen simultáneamente.
    """

    instante = ahora_utc()

    actualizadas = (
        db.query(models.NotificacionReflexionDominical)
        .filter(
            models.NotificacionReflexionDominical.id == notificacion_id,
            models.NotificacionReflexionDominical.estado == "pendiente",
            models.NotificacionReflexionDominical.programado_at <= instante
        )
        .update(
            {
                models.NotificacionReflexionDominical.estado: "procesando",
                models.NotificacionReflexionDominical.iniciado_at: instante,
                models.NotificacionReflexionDominical.intentos:
                    models.NotificacionReflexionDominical.intentos + 1
            },
            synchronize_session=False
        )
    )

    db.commit()

    return actualizadas == 1
    
# =====================================
# REFLEXIONES DOMINICALES
# REGISTRAR RESULTADO DEL ENVÍO
# =====================================

def registrar_resultado_dominical(
    db: Session,
    notificacion_id: int,
    enviados: int,
    fallidos: int,
    error: str | None = None
):
    """
    Registra el resultado del envío.
    No vuelve a enviar la notificación.
    """

    notificacion = (
        db.query(models.NotificacionReflexionDominical)
        .filter(
            models.NotificacionReflexionDominical.id == notificacion_id,
            models.NotificacionReflexionDominical.estado == "procesando"
        )
        .first()
    )

    if notificacion is None:
        return False

    notificacion.enviados = enviados
    notificacion.fallidos = fallidos
    notificacion.ultimo_error = error
    notificacion.estado = "enviada" if fallidos == 0 else "parcial"
    notificacion.enviado_at = ahora_utc()

    db.commit()

    return True
    
# =====================================
# REFLEXIONES DOMINICALES
# ENVIAR NOTIFICACIÓN PROGRAMADA
# =====================================

def enviar_notificacion_dominical(db: Session, notificacion_id: int):
    """
    Envía una notificación dominical previamente reservada.
    Registra el resultado y desactiva los tokens inválidos.
    """

    notificacion = (
        db.query(models.NotificacionReflexionDominical)
        .filter(
            models.NotificacionReflexionDominical.id == notificacion_id,
            models.NotificacionReflexionDominical.estado == "procesando"
        )
        .first()
    )

    if notificacion is None:
        return False

    reflexion = db.get(
        models.ReflexionDominical,
        notificacion.reflexion_id
    )

    if reflexion is None:
        registrar_resultado_dominical(
            db, notificacion_id, 0, 0,
            "La reflexión ya no existe."
        )
        return False

    dispositivos = (
        db.query(models.DispositivoPush)
        .filter(models.DispositivoPush.activo.is_(True))
        .all()
    )

    tokens = [dispositivo.token for dispositivo in dispositivos]

    if not tokens:
        registrar_resultado_dominical(
            db, notificacion_id, 0, 0
        )
        return True

    try:
        resultado = enviar_notificaciones_multiples(
            tokens,
            "Nueva reflexión dominical",
            reflexion.titulo[:100]
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

        registrar_resultado_dominical(
            db,
            notificacion_id,
            resultado["enviados"],
            resultado["fallidos"]
        )

        return True

    except Exception as error:
        registrar_resultado_dominical(
            db,
            notificacion_id,
            0,
            len(tokens),
            str(error)[:500]
        )
        return False
        
# =====================================
# REFLEXIONES DOMINICALES
# DETECTAR ENVÍOS INTERRUMPIDOS
# =====================================

def detectar_envios_dominicales_interrumpidos(db: Session):
    """
    Identifica envíos que llevan más de 10 minutos
    en procesamiento.

    No los reenvía automáticamente para evitar duplicados.
    """

    limite = ahora_utc() - timedelta(minutes=10)

    registros = (
        db.query(models.NotificacionReflexionDominical)
        .filter(
            models.NotificacionReflexionDominical.estado == "procesando",
            models.NotificacionReflexionDominical.iniciado_at < limite
        )
        .all()
    )

    for registro in registros:
        registro.estado = "revision"
        registro.ultimo_error = (
            "Envío interrumpido o sin confirmación. "
            "Requiere revisión antes de repetirlo."
        )

    if registros:
        db.commit()

    return len(registros)
    
# =====================================
# REFLEXIONES DOMINICALES
# PROCESAR NOTIFICACIONES PENDIENTES
# =====================================

def procesar_notificaciones_dominicales():
    """
    Comprueba las notificaciones dominicales pendientes
    y procesa las que han alcanzado su fecha programada.
    """

    db = SessionLocal()

    try:
        detectar_envios_dominicales_interrumpidos(db)

        pendientes = obtener_notificaciones_dominicales_pendientes(db)

        for notificacion in pendientes:
            notificacion_id = notificacion.id

            if reservar_notificacion_dominical(db, notificacion_id):
                enviar_notificacion_dominical(
                    db,
                    notificacion_id
                )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()