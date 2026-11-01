
# =====================================
# FIREBASE ADMIN SDK - PARROQUIAAPP
# =====================================

import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials


FIREBASE_CREDENTIALS_PATH = Path(
    os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        "/etc/secrets/firebase-service-account.json"
    )
)


def inicializar_firebase():
    """
    Inicializa Firebase Admin SDK una sola vez.
    Utiliza las credenciales privadas almacenadas en Render.
    """

    if firebase_admin._apps:
        return firebase_admin.get_app()

    if not FIREBASE_CREDENTIALS_PATH.is_file():
        raise RuntimeError(
            "No se encontró el archivo de credenciales de Firebase."
        )

    credencial = credentials.Certificate(
        str(FIREBASE_CREDENTIALS_PATH)
    )

    return firebase_admin.initialize_app(credencial)

# =====================================
# ENVIAR NOTIFICACIÓN A UN DISPOSITIVO
# =====================================

from firebase_admin import messaging


def enviar_notificacion_dispositivo(
    token: str,
    titulo: str,
    contenido: str
):
    """
    Envía una notificación a un dispositivo
    registrado en Firebase Cloud Messaging.
    """

    inicializar_firebase()

    mensaje = messaging.Message(
        notification=messaging.Notification(
            title=titulo,
            body=contenido
        ),
        token=token
    )

    return messaging.send(mensaje)


# =====================================
# ENVIAR NOTIFICACIONES A VARIOS DISPOSITIVOS
# =====================================

def enviar_notificaciones_multiples(
    tokens: list[str],
    titulo: str,
    contenido: str
):
    """
    Envía notificaciones a los dispositivos registrados.
    Devuelve los resultados y los tokens que deben darse de baja.
    """

    inicializar_firebase()

    if not tokens:
        return {
            "enviados": 0,
            "fallidos": 0,
            "tokens_invalidos": []
        }

    enviados = 0
    fallidos = 0
    tokens_invalidos = []

    for token in tokens:
        try:
            enviar_notificacion_dispositivo(
                token,
                titulo,
                contenido
            )
            enviados += 1

        except (
            messaging.UnregisteredError,
            messaging.SenderIdMismatchError
        ):
            fallidos += 1
            tokens_invalidos.append(token)

        except Exception:
            fallidos += 1

    return {
        "enviados": enviados,
        "fallidos": fallidos,
        "tokens_invalidos": tokens_invalidos
    }
