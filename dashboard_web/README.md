# OSINT CyberWatch — panel web (rama `feature/dashboard-api`)

Capa de producto sobre la base `posts` de la tesis. No modifica el pipeline, el esquema ni el ground truth.
Vista general y puesta en marcha: ver la seccion «Dashboard Interactivo Comercial» del [README principal](../README.md).

| Servicio | URL | Contenido |
|---|---|---|
| `osint-web` | http://localhost:8080 | Frontend (HTML + Tailwind CDN + Chart.js), Nginx con proxy `/api` |
| `osint-api` | http://localhost:8000/docs | API REST FastAPI (`dashboard_api/`), Swagger |
| `maxi-n8n` | http://localhost:5678 | Orquestador (workflow programado + webhook de sync) |

```powershell
docker compose -p ttesis up -d --build   # desde repo/, con .env (POSTGRES_*, AUTHOR_SALT)
```

## Frontend

- Un solo `index.html` sin build; Tailwind y Chart.js por CDN y fuentes de Google Fonts (**Inter** para la interfaz y los
  graficos, **JetBrains Mono** para badges, fechas, conteos e IDs). Requiere internet.
- **Responsive** (probado en 375, 768 y 1280 px, sin desborde horizontal): header que se apila, KPIs en 1/2/4 columnas,
  graficos en 1/2 columnas con leyenda que pasa abajo en movil, filtros en grilla, tabla con scroll horizontal y modales
  con margen y scroll interno.
- Categoria y sentimiento son una unica pildora desplegable coloreada por valor; al cambiarla se hace `PATCH`, se
  repinta al instante y se refrescan KPIs y graficos sin recargar la tabla.
- La fuente de una alta manual se normaliza: `r/cybersecurity` o `/r/cybersecurity` se guarda como `cybersecurity`
  (nunca `r/r/...`); lo limpian el frontend y la API.

## Endpoints

| Metodo y ruta | Funcion |
|---|---|
| `GET /api/health` | Estado de la conexion a PostgreSQL |
| `GET /api/stats` | KPIs, conteos por categoria/sentimiento/subreddit, cruce sentimiento x fuente y serie temporal |
| `GET /api/posts` | Listado paginado (`page`, `page_size`, `sort`, `order`) con filtros `category`, `sentiment`, `subreddit`, `q` |
| `GET /api/posts/export` | CSV (UTF-8 con BOM) con los mismos filtros; neutraliza formulas (`=`, `+`, `-`, `@`) |
| `POST /api/posts` | Alta manual: `classify_threat` + VADER del pipeline real; guarda con `source='manual'` |
| `PATCH /api/posts/{id}` | Reclasificacion manual de `threat_category` y/o `sentiment` |
| `DELETE /api/posts/{id}` | Descarte definitivo de un post |
| `POST /api/posts/{id}/translate` | Traduccion al espanol (ver abajo) |
| `POST /api/pipeline/sync` | Sincronizacion puntual (ver abajo) |

### Traduccion

Google Translate (`deep-translator`, bloques de 4.500 caracteres) con **respaldo automatico a MyMemory** (en-GB -> es-ES,
bloques de 450) si Google falla o limita, y cache en memoria por `post_id` en el backend (y por post en el modal).
Si ambos fallan responde 503 con un mensaje claro. MyMemory anonimo tiene una cuota diaria.

### Sincronizacion (`POST /api/pipeline/sync`)

1. Dispara el webhook de n8n `/webhook/osint-sync` (workflow `osint_sync_webhook`, JSON en
   `dashboard_api/n8n_workflow_osint_sync_webhook.json`, que usa `scripts/osint_sync_once.py`). Se importa con
   `n8n import:workflow` + `publish:workflow` y un reinicio de n8n (pasos en el README principal).
2. Si el webhook no responde, corre `osint_pipeline.py` dentro de la API, con User-Agent
   `OSINT-CyberWatch-UTN/1.0`, 6 s entre subreddits y 90 s de espera entre sincronizaciones vivas.
3. Si Reddit rechaza todas las fuentes con HTTP 429 (o no entrega registros), procesa `dashboard_api/sample_feed.xml`
   (4 entradas reales del RSS que ya estan en la base) con el mismo pipeline y devuelve HTTP 200 con
   «Sincronización completada (respaldo local por límite de tasa de Reddit): 4 registros procesados.».
   Ese respaldo **no trae datos nuevos**: solo hace UPSERT de esas 4 publicaciones (renueva `collected_at`).

Un re-encuentro no pisa categoria ni sentimiento, para respetar el triage manual (el workflow programado de la tesis si
los refresca). Solo se devuelve `ok: false` si tambien falla el respaldo local.

## Notas

- `PATCH` y `DELETE` modifican la base real; `DELETE` es definitivo.
- Los puertos se publican solo en `127.0.0.1`.
