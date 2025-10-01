from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

# ─────────────────────────────────────────────────────────────
# Tablas base
# ─────────────────────────────────────────────────────────────

class Parroquia(Base):
    __tablename__ = "parroquias"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    direccion = Column(String(255))


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    nombre = Column(String(120))
    rol = Column(String(20), default="feligres")  # feligres | admin
    parroquia_id = Column(Integer, ForeignKey("parroquias.id"))

# ─────────────────────────────────────────────────────────────
# Módulo de Evangelización
# ─────────────────────────────────────────────────────────────

class Contenido(Base):
    __tablename__ = "contenidos"
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(30), index=True)  # reflexion | homilia | testimonio | serie_cap
    titulo = Column(String(200), nullable=False)
    cuerpo_md = Column(Text, nullable=False)
    audio_url = Column(String(255))
    imagen_url = Column(String(255))
    etiquetas = Column(String(255))  # CSV simple: jovenes,familia
    parroquia_id = Column(Integer, ForeignKey("parroquias.id"))
    publicado_at = Column(DateTime)
    programado_at = Column(DateTime)
    autor_id = Column(Integer, ForeignKey("users.id"))


class Serie(Base):
    __tablename__ = "series"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    dias = Column(Integer, default=7)
    portada_url = Column(String(255))


class SerieCapitulo(Base):
    __tablename__ = "series_capitulos"
    id = Column(Integer, primary_key=True, index=True)
    serie_id = Column(Integer, ForeignKey("series.id"), index=True)
    orden = Column(Integer, nullable=False)
    contenido_id = Column(Integer, ForeignKey("contenidos.id"))


class Habito(Base):
    __tablename__ = "habitos"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    periodicidad = Column(String(20), default="daily")  # daily | weekly


class UserHabito(Base):
    __tablename__ = "user_habitos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    habito_id = Column(Integer, ForeignKey("habitos.id"))
    fecha = Column(DateTime, default=datetime.utcnow)
    completado = Column(Boolean, default=True)

# ─────────────────────────────────────────────────────────────
# Módulo de Misas (Cruz del Señor)
# ─────────────────────────────────────────────────────────────
class Misa(Base):
    __tablename__ = "misas"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False)  # ← antes era fecha_hora
    descripcion = Column(Text)
    sacerdote = Column(String(120))
    es_festiva = Column(Boolean, default=False)
    parroquia_id = Column(Integer, ForeignKey("parroquias.id"))
    creada_en = Column(DateTime, default=datetime.utcnow)

# ─────────────────────────────────────────────────────────────
# Módulo de Avisos / Noticias
# ─────────────────────────────────────────────────────────────

class Aviso(Base):
    __tablename__ = "avisos"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    cuerpo = Column(Text, nullable=False)
    publicado_at = Column(DateTime, default=datetime.utcnow)
    parroquia_id = Column(Integer, ForeignKey("parroquias.id"))
