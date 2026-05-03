from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────
# Evangelización
# ─────────────────────────────────────────────────────────────

class ContenidoOut(BaseModel):
    id: int
    tipo: str
    titulo: str
    cuerpo_md: str
    audio_url: Optional[str] = None
    imagen_url: Optional[str] = None
    etiquetas: Optional[str] = None
    publicado_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Misas (VERSIÓN ÚNICA Y LIMPIA)
# ─────────────────────────────────────────────────────────────

class MisaBase(BaseModel):
    fecha: datetime
    descripcion: Optional[str] = None
    sacerdote: Optional[str] = None
    es_festiva: bool = False
    parroquia_id: int = 1


class MisaCreate(MisaBase):
    pass


class MisaUpdate(BaseModel):
    fecha: Optional[datetime] = None
    descripcion: Optional[str] = None
    sacerdote: Optional[str] = None
    es_festiva: Optional[bool] = None
    hora: str | None = None   # 🔥 ESTE ES EL QUE FALTA

from pydantic import BaseModel
from datetime import datetime

class MisaOut(BaseModel):
    id: int
    fecha: datetime
    descripcion: str | None = None
    color: str | None = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Avisos / Noticias
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AvisoOut(BaseModel):
    id: int
    titulo: str
    cuerpo: str
    publicado_at: datetime
    parroquia_id: Optional[int] = None

    class Config:
        from_attributes = True


class AvisoCreate(BaseModel):
    titulo: str
    cuerpo: str
    parroquia_id: Optional[int] = None