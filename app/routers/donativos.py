
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from app.db import get_db
from app.models import ConfiguracionDonativos
from app.security import (
    exigir_administrador,
    generar_csrf_formulario,
    validar_csrf_formulario
)

router = APIRouter(tags=["Donativos"])

templates = Jinja2Templates(directory="app/templates")

# ==========================================
# DATOS OFICIALES DE LA PARROQUIA
# ==========================================

BIZUM_CODIGO = "03155"

DONATIVO_URL = (
    "https://www.donoamiiglesia.es/es/donar.html/"
    "4cb6bfb6-ed3e-e611-80e8-005056b101e1"
)

MENSAJE_INFORMATIVO = (
    "Tu colaboración ayuda a sostener la vida, "
    "las actividades y la misión de nuestra parroquia."
)

MENSAJE_AGRADECIMIENTO = (
    "Gracias por tu generosidad. Cada aportación "
    "contribuye al mantenimiento de nuestra parroquia."
)


# ==========================================
# OBTENER CONFIGURACIÓN
# ==========================================

def obtener_configuracion(db: Session):
    configuracion = db.query(
        ConfiguracionDonativos
    ).first()

    if configuracion is None:
        configuracion = ConfiguracionDonativos(
            bizum_codigo=BIZUM_CODIGO,
            donativo_url=DONATIVO_URL,
            mensaje_informativo=MENSAJE_INFORMATIVO,
            mensaje_agradecimiento=MENSAJE_AGRADECIMIENTO,
            activo=True
        )

        db.add(configuracion)
        db.commit()
        db.refresh(configuracion)

    return configuracion


# ==========================================
# PÁGINA PÚBLICA DE DONATIVOS
# ==========================================

@router.get("/donativos", response_class=HTMLResponse)
def pagina_donativos(
    request: Request,
    db: Session = Depends(get_db)
):
    configuracion = obtener_configuracion(db)

    if not configuracion.activo:
        raise HTTPException(
            status_code=404,
            detail="El módulo Donativos no está disponible."
        )

    return templates.TemplateResponse(
        "donativos.html",
        {
            "request": request,
            "bizum_codigo": configuracion.bizum_codigo,
            "donativo_url": configuracion.donativo_url,
            "mensaje_informativo": configuracion.mensaje_informativo,
            "mensaje_agradecimiento": configuracion.mensaje_agradecimiento,
            "activo": configuracion.activo
        }
    )


# ==========================================
# PANEL DE ADMINISTRACIÓN
# ==========================================

@router.get("/admin/donativos", response_class=HTMLResponse)
def administrar_donativos(
    request: Request,
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):
    configuracion = obtener_configuracion(db)

    csrf = generar_csrf_formulario(request)

    return templates.TemplateResponse(
        "admin_donativos.html",
        {
            "request": request,
            "configuracion": configuracion,
            "csrf_token": csrf["csrf_token"],
            "csrf_firma": csrf["csrf_firma"]
        }
    )


# ==========================================
# GUARDAR CONFIGURACIÓN
# ==========================================

@router.post("/admin/donativos")
def guardar_donativos(
    request: Request,
    bizum_codigo: str = Form(...),
    donativo_url: str = Form(...),
    mensaje_informativo: str = Form(...),
    mensaje_agradecimiento: str = Form(...),
    csrf_token: str = Form(...),
    csrf_firma: str = Form(...),
    activo: bool = Form(False),
    db: Session = Depends(get_db),
    admin: bool = Depends(exigir_administrador)
):

    # Comprobar protección CSRF
    validar_csrf_formulario(
        request,
        csrf_token,
        csrf_firma
    )

    # Validar código Bizum
    bizum_codigo = bizum_codigo.strip()

    if (
        not bizum_codigo.isascii()
        or not bizum_codigo.isdigit()
        or len(bizum_codigo) != 5
    ):
        raise HTTPException(
            status_code=400,
            detail="El código Bizum debe contener exactamente 5 dígitos."
        )

    # Validar enlace oficial
    donativo_url = donativo_url.strip()
    url = urlparse(donativo_url)

    if (
        url.scheme != "https"
        or url.netloc != "www.donoamiiglesia.es"
        or url.path != (
            "/es/donar.html/"
            "4cb6bfb6-ed3e-e611-80e8-005056b101e1"
        )
        or url.username is not None
        or url.password is not None
        or url.fragment
    ):
        raise HTTPException(
            status_code=400,
            detail="El enlace debe corresponder a la parroquia en Dono a mi Iglesia."
        )

    # Validar mensajes
    mensaje_informativo = mensaje_informativo.strip()
    mensaje_agradecimiento = mensaje_agradecimiento.strip()

    if not mensaje_informativo or not mensaje_agradecimiento:
        raise HTTPException(
            status_code=400,
            detail="Los mensajes no pueden estar vacíos."
        )

    if (
        len(mensaje_informativo) > 2000
        or len(mensaje_agradecimiento) > 2000
    ):
        raise HTTPException(
            status_code=400,
            detail="Los mensajes no pueden superar los 2000 caracteres."
        )

    # Guardar configuración
    configuracion = obtener_configuracion(db)

    configuracion.bizum_codigo = bizum_codigo
    configuracion.donativo_url = donativo_url
    configuracion.mensaje_informativo = mensaje_informativo
    configuracion.mensaje_agradecimiento = mensaje_agradecimiento
    configuracion.activo = activo

    db.commit()

    return RedirectResponse(
        url="/admin/donativos",
        status_code=303
    )
