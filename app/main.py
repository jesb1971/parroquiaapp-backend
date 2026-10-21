
# app/main.py

import os
import shutil
from datetime import datetime

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Base de datos
from .db import Base, engine

# Importar modelos para registrar todas las tablas
from app.models import *

# Routers
from app.routers import (
    evangelizacion,
    misas,
    avisos,
    auth,
    frontend,
    donativos,
    noticias
)

from app.security import exigir_administrador


# =====================================
# APLICACIÓN
# =====================================

app = FastAPI(title="ParroquiaApp")

# Crear tablas automáticamente
Base.metadata.create_all(bind=engine)


# =====================================
# ROUTERS
# =====================================

app.include_router(evangelizacion.router)
app.include_router(misas.router)
app.include_router(avisos.router)
app.include_router(auth.router)
app.include_router(frontend.router)
app.include_router(noticias.router)
app.include_router(donativos.router)


# =====================================
# ARCHIVOS ESTÁTICOS
# =====================================

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)


# =====================================
# ARCHIVOS DE EVANGELIZACIÓN
# =====================================

IMAGENES_DIR = "/var/data/evangelizacion/imagenes"
AUDIOS_DIR = "/var/data/evangelizacion/audios"

# Crear carpetas si todavía no existen
os.makedirs(IMAGENES_DIR, exist_ok=True)
os.makedirs(AUDIOS_DIR, exist_ok=True)


# =====================================
# AUDIOS DE EVANGELIZACIÓN
# =====================================

# Esta ruta debe registrarse antes que
# /media/evangelizacion para evitar conflictos.

app.mount(
    "/media/evangelizacion/audios",
    StaticFiles(directory=AUDIOS_DIR),
    name="media_evangelizacion_audios"
)


# =====================================
# IMÁGENES DE EVANGELIZACIÓN
# =====================================

app.mount(
    "/media/evangelizacion",
    StaticFiles(directory=IMAGENES_DIR),
    name="media_evangelizacion"
)


# =====================================
# PLANTILLAS
# =====================================

templates = Jinja2Templates(
    directory="app/templates"
)


# =====================================
# PÁGINA PRINCIPAL
# =====================================

@app.get("/")
def root():
    return RedirectResponse(url="/app")


@app.get("/app", response_class=HTMLResponse)
def app_home(request: Request):
    return templates.TemplateResponse(
        "home_demo.html",
        {"request": request}
    )


# =====================================
# COPIA DE SEGURIDAD
# =====================================

def backup_db():
    try:
        origen = "/var/data/parroquia.db"

        destino = (
            "/var/data/backup_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )

        if os.path.exists(origen):
            shutil.copy(origen, destino)
            print(f"Backup creado: {destino}")

    except Exception as e:
        print("Error backup:", e)


@app.on_event("shutdown")
def shutdown_event():
    backup_db()


# =====================================
# PANEL ADMINISTRADOR
# =====================================

@app.get("/admin", response_class=HTMLResponse)
def admin_panel(
    request: Request,
    admin: bool = Depends(exigir_administrador)
):
    return templates.TemplateResponse(
        "admin_panel.html",
        {"request": request}
    )


# =====================================
# ADMINISTRACIÓN DE AVISOS
# =====================================

@app.get("/admin/avisos", response_class=HTMLResponse)
def admin_avisos(request: Request):
    return templates.TemplateResponse(
        "admin_avisos.html",
        {"request": request}
    )


# =====================================
# AVISOS PÚBLICOS
# =====================================

@app.get("/avisos-publicos", response_class=HTMLResponse)
def avisos_publicos(request: Request):
    return templates.TemplateResponse(
        "avisos_publicos.html",
        {"request": request}
    )


@app.get("/aviso/{aviso_id}", response_class=HTMLResponse)
def vista_aviso(request: Request, aviso_id: int):
    return templates.TemplateResponse(
        "aviso_detalle.html",
        {
            "request": request,
            "aviso_id": aviso_id
        }
    )


# =====================================
# NOTICIAS PÚBLICAS
# =====================================

@app.get("/noticias-publicas", response_class=HTMLResponse)
def noticias_publicas(request: Request):
    return templates.TemplateResponse(
        "noticias_publicas.html",
        {"request": request}
    )


# =====================================
# ADMINISTRACIÓN DE NOTICIAS
# =====================================

@app.get("/admin-noticias", response_class=HTMLResponse)
def admin_noticias(
    request: Request,
    admin: bool = Depends(exigir_administrador)
):
    return templates.TemplateResponse(
        "admin_noticias.html",
        {"request": request}
    )
