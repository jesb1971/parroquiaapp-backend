from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

# 🔐 credenciales simples (luego las mejoramos)
ADMIN_USER = "admin"
ADMIN_PASS = "1234"


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(usuario: str = Form(...), password: str = Form(...)):

    if usuario == ADMIN_USER and password == ADMIN_PASS:
        response = RedirectResponse(url="/demo", status_code=302)
        response.set_cookie(key="admin", value="1")
        return response

    return RedirectResponse(url="/login", status_code=302)


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("admin")
    return response