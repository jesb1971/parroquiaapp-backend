
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