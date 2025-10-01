"""Rutas de autenticación (estructura base)."""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
