# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Base de datos: crear tablas en desarrollo
from .db import Base, engine

# Routers
from app.routers import evangelizacion, misas, avisos, auth, frontend

app = FastAPI(title="ParroquiaApp")

# ⚠️ Solo para desarrollo: crea las tablas si no existen
Base.metadata.create_all(bind=engine)

# Monta los routers
app.include_router(evangelizacion.router)
app.include_router(misas.router)
app.include_router(avisos.router)
app.include_router(auth.router)
app.include_router(frontend.router)

# Servir carpeta static (para imágenes, CSS, etc.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configurar templates
templates = Jinja2Templates(directory="app/templates")

# Ruta raíz → redirige a la portada demo
@app.get("/")
def root():
    return RedirectResponse(url="/app")

# Portada demo para feligreses
@app.get("/app", response_class=HTMLResponse)
def app_home(request: Request):
    return templates.TemplateResponse("home_demo.html", {"request": request})
