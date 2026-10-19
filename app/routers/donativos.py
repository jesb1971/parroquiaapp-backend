
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Donativos"])

templates = Jinja2Templates(directory="app/templates")

# Datos de colaboración de la Parroquia Cruz del Señor
BIZUM_CODIGO = "03155"

DONATIVO_URL = (
    "https://www.donoamiiglesia.es/es/donar.html/"
    "4cb6bfb6-ed3e-e611-80e8-005056b101e1"
)


@router.get("/donativos", response_class=HTMLResponse)
def pagina_donativos(request: Request):
    return templates.TemplateResponse(
        "donativos.html",
        {
            "request": request,
            "bizum_codigo": BIZUM_CODIGO,
            "donativo_url": DONATIVO_URL,
        },
    )
