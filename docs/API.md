# ParroquiaApp – API v0.1 (Backend FastAPI)

> Estado: **MVP**. Módulos incluidos: **Evangelización**, **Misas**, **Avisos**.  
> Autenticación: no requerida en esta versión (endpoints públicos).

## Base
- URL local: `http://127.0.0.1:8000`
- Salud: `GET /` → `{"status":"ok","service":"ParroquiaApp"}`
- Swagger: `GET /docs`
- OpenAPI JSON: `GET /openapi.json`

---

## 1) Evangelización

### 1.1 `GET /evangelizacion/hoy` — Contenido Hoy
Devuelve la **reflexión del día**. Si no hay contenidos publicados en BD, entrega un **fallback de prueba**.

**Respuesta 200 (ContenidoOut)**
```json
{
  "id": 0,
  "tipo": "reflexion",
  "titulo": "Dios habla en lo pequeño",
  "cuerpo_md": "**Versículo**: Sal 46:10 — \"Estad quietos, y conoced que yo soy Dios\".\n\n**Reflexión (1 min)**: En el silencio cotidiano aprendemos a reconocer su voz.",
  "audio_url": null,
  "imagen_url": null,
  "etiquetas": null,
  "publicado_at": "2025-09-20T00:00:00Z"
}
