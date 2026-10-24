from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Date
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
    tipo = Column(String(30), index=True)
    titulo = Column(String(200), nullable=False)
    cuerpo_md = Column(Text, nullable=False)
    audio_url = Column(String(255))
    imagen_url = Column(String(255))
    etiquetas = Column(String(255))
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
    periodicidad = Column(String(20), default="daily")


class UserHabito(Base):
    __tablename__ = "user_habitos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    habito_id = Column(Integer, ForeignKey("habitos.id"))
    fecha = Column(DateTime, default=datetime.utcnow)
    completado = Column(Boolean, default=True)

# ─────────────────────────────────────────────────────────────
# Módulo de Misas (CORREGIDO)
# ─────────────────────────────────────────────────────────────

class Misa(Base):
    __tablename__ = "misas"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False)

    descripcion = Column(String, nullable=True)
    es_manual = Column(Boolean, default=False)

    parroquia_id = Column(Integer, nullable=False)

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

# ─────────────────────────────────────────────
# 🎉 FIESTAS PROPIAS DE LA PARROQUIA
# ─────────────────────────────────────────────

class FiestaParroquia(Base):
    __tablename__ = "fiestas_parroquia"

    id = Column(Integer, primary_key=True, index=True)
    parroquia_id = Column(Integer, ForeignKey("parroquias.id"))
    fecha = Column(Date, nullable=False)
    nombre = Column(String, nullable=False)
    color = Column(String, default="blanco")
    
# ─────────────────────────────────────────────
# Módulo de contacto
# ─────────────────────────────────────────────

class Contacto(Base):
    __tablename__ = "contactos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, nullable=False)
    mensaje = Column(String, nullable=False)
    
# ─────────────────────────────────────────────
# Módulo de noticias
# ─────────────────────────────────────────────

from sqlalchemy import Column, Integer, String, DateTime


class Noticia(Base):
    __tablename__ = "noticias"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    contenido = Column(String, nullable=False)
    fecha = Column(DateTime)
    imagen = Column(String, nullable=True)  # 👈 NUEVO
    
# ─────────────────────────────────────────────
# Módulo de evangelización
# ─────────────────────────────────────────────

class Evangelizacion(Base):
    __tablename__ = "evangelizacion"

    id = Column(Integer, primary_key=True, index=True)

    titulo = Column(String, nullable=False)

    cita_biblica = Column(String, nullable=True)

    reflexion = Column(Text, nullable=False)

    pregunta_reflexion = Column(Text, nullable=True)

    imagen_url = Column(String, nullable=True)

    audio_url = Column(String, nullable=True)

    video_url = Column(String, nullable=True)

    autor = Column(String, default="Padre Sigfredo")

    publicado = Column(Boolean, default=True)

    fecha_publicacion = Column(DateTime, default=datetime.utcnow)
    

# ─────────────────────────────────────────────
# Módulo de Donativos - Configuración
# ─────────────────────────────────────────────

class ConfiguracionDonativos(Base):
    __tablename__ = "configuracion_donativos"

    id = Column(Integer, primary_key=True, index=True)

    bizum_codigo = Column(String(20), nullable=False, default="03155")

    donativo_url = Column(
        String(500),
        nullable=False,
        default=(
            "https://www.donoamiiglesia.es/es/donar.html/"
            "4cb6bfb6-ed3e-e611-80e8-005056b101e1"
        )
    )

    mensaje_informativo = Column(
        Text,
        default=(
            "Tu colaboración ayuda a sostener la vida, "
            "las actividades y la misión de nuestra parroquia."
        )
    )

    mensaje_agradecimiento = Column(
        Text,
        default=(
            "Gracias por tu generosidad. Cada aportación "
            "contribuye al mantenimiento de nuestra parroquia."
        )
    )

    activo = Column(Boolean, default=True, nullable=False)
    
# =====================================
# Módulo de Reflexión dominical
# =====================================

class ReflexionDominical(Base):
    __tablename__ = "reflexiones_dominicales"

    id = Column(Integer, primary_key=True, index=True)
    fecha_domingo = Column(Date, nullable=False, index=True)
    titulo = Column(String(200), nullable=False)
    subtitulo = Column(String(300), nullable=True)
    contenido = Column(Text, nullable=False)
    imagen = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)
    publicado_at = Column(DateTime, default=datetime.utcnow)
