# OSINT CyberWatch — panel web (rama `feature/dashboard-api`)

Capa de producto sobre la base `posts` de la tesis. No modifica el pipeline, el esquema ni el ground truth.

| Servicio | URL | Contenido |
|---|---|---|
| `osint-web` | http://localhost:8080 | Frontend (HTML + Tailwind CDN + Chart.js), Nginx con proxy `/api` |
| `osint-api` | http://localhost:8000/docs | API REST FastAPI (`dashboard_api/`), Swagger |

```powershell
docker compose -p ttesis up -d --build   # desde repo/, con .env (POSTGRES_*, AUTHOR_SALT)
```

Endpoints: `GET /api/stats`, `GET /api/posts` (page, page_size, sort, order, category, sentiment, subreddit, q),
`GET /api/posts/export` (CSV con los filtros activos), `POST /api/posts/{id}/translate` (traduce al espanol: Google Translate con fallback a MyMemory en-GB->es-ES en bloques de 450 caracteres, cache en memoria; 503 con mensaje claro si ambos fallan; MyMemory anonimo tiene cuota diaria), `POST /api/posts` (clasifica un texto con `classify_threat` + VADER y lo guarda), `PATCH /api/posts/{id}` (triage), `DELETE /api/posts/{id}`, `POST /api/pipeline/sync`, `GET /api/health`.

Notas:
- `sync` (`POST /api/pipeline/sync`): 1) dispara el webhook de n8n `/webhook/osint-sync` (workflow `osint_sync_webhook`,
  JSON en `dashboard_api/n8n_workflow_osint_sync_webhook.json`; importado con `n8n import:workflow` + `publish:workflow`
  y reinicio de n8n; usa `scripts/osint_sync_once.py`); 2) si el webhook no responde, corre `osint_pipeline.py` dentro de la API;
  3) si Reddit rechaza todas las fuentes con HTTP 429 (o no entrega registros), procesa `dashboard_api/sample_feed.xml`
  (4 entradas reales del RSS que ya estan en la base) con el mismo pipeline y devuelve HTTP 200 con
  «Sincronización completada (respaldo local por límite de tasa de Reddit): 4 registros procesados.».
  Ese respaldo NO trae datos nuevos: solo hace UPSERT de esas 4 publicaciones (renueva `collected_at`).
  Un re-encuentro no pisa categoria ni sentimiento (respeta el triage manual). Hay 90 s de espera entre sincronizaciones vivas.
- PATCH y DELETE modifican la base real; DELETE es definitivo.
- Los puertos se publican solo en `127.0.0.1`.
