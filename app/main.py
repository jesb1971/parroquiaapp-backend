# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Base de datos
from .db import Base, engine

# 🔥 IMPORTANTE: importar models para que cree TODAS las tablas
from app import models

# Routers
from app.routers import evangelizacion, misas, avisos, auth, frontend

app = FastAPI(title="ParroquiaApp")

# ⚠️ Crear tablas automáticamente (incluye fiestas_parroquia)
Base.metadata.create_all(bind=engine)

# Routers
app.include_router(evangelizacion.router)
app.include_router(misas.router)
app.include_router(avisos.router)
app.include_router(auth.router)
app.include_router(frontend.router)

# Static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Root
@app.get("/")
def root():
    return RedirectResponse(url="/app")

# Portada
@app.get("/app", response_class=HTMLResponse)
def app_home(request: Request):
    return templates.TemplateResponse("home_demo.html", {"request": request})
    
import shutil
import os
from datetime import datetime

def backup_db():
    try:
        origen = "/var/data/parroquia.db"
        destino = f"/var/data/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        if os.path.exists(origen):
            shutil.copy(origen, destino)
            print(f"Backup creado: {destino}")
    except Exception as e:
        print("Error backup:", e)


@app.on_event("shutdown")
def shutdown_event():
    backup_db()

@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request):
    return templates.TemplateResponse("admin_panel.html", {"request": request})
    
@app.get("/admin/avisos", response_class=HTMLResponse)
def admin_avisos(request: Request):
    return templates.TemplateResponse("admin_avisos.html", {"request": request})
    
@app.get("/avisos-publicos", response_class=HTMLResponse)
def avisos_publicos(request: Request):
    return templates.TemplateResponse("avisos_publicos.html", {"request": request})