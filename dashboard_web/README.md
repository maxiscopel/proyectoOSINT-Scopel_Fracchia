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
`PATCH /api/posts/{id}` (triage), `DELETE /api/posts/{id}`, `POST /api/pipeline/sync`, `GET /api/health`.

Notas:
- `sync`: si `N8N_WEBHOOK_URL` esta definida llama a ese webhook (el workflow actual no tiene trigger webhook);
  si no, corre el modulo real `osint_pipeline.py` (montado desde `scripts/`) con 3 subreddits y espaciado corto,
  y hace UPSERT. A diferencia del workflow de n8n, un re-encuentro no pisa categoria ni sentimiento,
  para respetar las reclasificaciones manuales. Reddit puede responder 429 (limite por IP).
- PATCH y DELETE modifican la base real; DELETE es definitivo.
- Los puertos se publican solo en `127.0.0.1`.
