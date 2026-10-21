
import os

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext

from app.security import (
    crear_token_admin,
    COOKIE_NAME,
    SESSION_MINUTES,
)

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

contexto = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


@router.post("/login")
def login(
    usuario: str = Form(...),
    password: str = Form(...)
):
    autenticado = False

    if ADMIN_PASSWORD_HASH and usuario == ADMIN_USER:
        autenticado = contexto.verify(
            password,
            ADMIN_PASSWORD_HASH
        )

    if not autenticado:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    token = crear_token_admin()

    response = RedirectResponse(
        url="/admin",
        status_code=303
    )

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_MINUTES * 60,
        path="/"
    )

    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(
        url="/",
        status_code=303
    )

    response.delete_cookie(
        COOKIE_NAME,
        path="/"
    )

    response.delete_cookie(
        "admin",
        path="/"
    )

    return response
