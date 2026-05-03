from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

# 🔐 credenciales (por ahora simples)
ADMIN_USER = "admin"
ADMIN_PASS = "1234"


# 🔹 FORMULARIO LOGIN
@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# 🔹 PROCESAR LOGIN
@router.post("/login")
def login(usuario: str = Form(...), password: str = Form(...)):

    if usuario == ADMIN_USER and password == ADMIN_PASS:
        response = RedirectResponse(url="/admin", status_code=302)
        response.set_cookie(key="admin", value="1")
        return response

    return RedirectResponse(url="/login", status_code=302)


# 🔹 LOGOUT
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("admin")
    return response