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
        from_attributes = True  # Permite crear desde ORM (SQLAlchemy) en Pydantic v2


# ─────────────────────────────────────────────────────────────
# Misas
# ─────────────────────────────────────────────────────────────

class MisaOut(BaseModel):
    id: int
    fecha_hora: datetime
    templo: Optional[str] = None
    celebrante: Optional[str] = None
    notas: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# Avisos / Noticias
# ─────────────────────────────────────────────────────────────

class AvisoOut(BaseModel):
    id: int
    titulo: str
    cuerpo: str
    publicado_at: datetime
    parroquia_id: Optional[int] = None

    class Config:
        from_attributes = True
        
from pydantic import BaseModel
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# Schemas de Misas
# ─────────────────────────────────────────────────────────────

class MisaBase(BaseModel):
    fecha: datetime
    descripcion: str | None = None
    sacerdote: str | None = None
    es_festiva: bool = False
    parroquia_id: int = 1

class MisaCreate(MisaBase):
    pass

class MisaUpdate(BaseModel):
    fecha: datetime | None = None
    descripcion: str | None = None
    sacerdote: str | None = None
    es_festiva: bool | None = None

class MisaOut(MisaBase):
    id: int
    creada_en: datetime

    class Config:
        from_attributes = True

