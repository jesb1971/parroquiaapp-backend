
import os
import hmac
import secrets

from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt


# ==========================================
# CONFIGURACIÓN DE SEGURIDAD
# ==========================================

SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

ALGORITHM = "HS256"
SESSION_MINUTES = 120
COOKIE_NAME = "parroquia_session"


# ==========================================
# CREAR SESIÓN DE ADMINISTRADOR
# ==========================================

def crear_token_admin():
    if not SECRET_KEY:
        raise RuntimeError(
            "SESSION_SECRET_KEY no está configurada"
        )

    expiracion = datetime.now(timezone.utc) + timedelta(
        minutes=SESSION_MINUTES
    )

    datos = {
        "sub": "admin",
        "exp": expiracion,
        "jti": secrets.token_urlsafe(16)
    }

    return jwt.encode(
        datos,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ==========================================
# COMPROBAR SESIÓN
# ==========================================

def es_administrador(request: Request) -> bool:
    if not SECRET_KEY:
        return False

    token = request.cookies.get(COOKIE_NAME)

    if not token:
        return False

    try:
        datos = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return datos.get("sub") == "admin"

    except JWTError:
        return False


# ==========================================
# EXIGIR AUTENTICACIÓN
# ==========================================

def exigir_administrador(request: Request):
    if not es_administrador(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acceso exclusivo para administradores"
        )

    return True


# ==========================================
# GENERAR TOKEN CSRF
# ==========================================

def crear_token_csrf():
    return secrets.token_urlsafe(32)


# ==========================================
# FIRMAR TOKEN CSRF
# ==========================================

def firmar_token_csrf(token: str, sesion: str) -> str:
    if not SECRET_KEY:
        raise RuntimeError(
            "SESSION_SECRET_KEY no está configurada"
        )

    mensaje = f"{sesion}:{token}".encode("utf-8")

    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        mensaje,
        sha256
    ).hexdigest()


# ==========================================
# VERIFICAR FIRMA CSRF
# ==========================================

def verificar_firma_csrf(
    token: str,
    sesion: str,
    firma: str
) -> bool:
    if not token or not sesion or not firma:
        return False

    firma_esperada = firmar_token_csrf(
        token,
        sesion
    )

    return hmac.compare_digest(
        firma_esperada,
        firma
    )


# ==========================================
# GENERAR PROTECCIÓN PARA FORMULARIO
# ==========================================

def generar_csrf_formulario(request: Request):
    exigir_administrador(request)

    sesion = request.cookies.get(COOKIE_NAME)
    token = crear_token_csrf()
    firma = firmar_token_csrf(token, sesion)

    return {
        "csrf_token": token,
        "csrf_firma": firma
    }


# ==========================================
# VALIDAR PROTECCIÓN DEL FORMULARIO
# ==========================================

def validar_csrf_formulario(
    request: Request,
    token: str,
    firma: str
):
    exigir_administrador(request)

    sesion = request.cookies.get(COOKIE_NAME)

    if not verificar_firma_csrf(
        token,
        sesion,
        firma
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solicitud no autorizada: token CSRF inválido."
        )

    return True
