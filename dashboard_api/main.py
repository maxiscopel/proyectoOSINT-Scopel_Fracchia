"""OSINT CyberWatch - API REST (FastAPI) sobre la tabla `posts` del pipeline OSINT."""
import logging
import os
import sys
import urllib.request
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

import database as db
from schemas import Category, Post, PostPage, PostUpdate, Sentiment, SyncResult

LOG = logging.getLogger("dashboard_api")
POST_COLS = ("post_id, title, content, author, subreddit, url, score, num_comments, "
             "threat_category, sentiment, compound::float AS compound, created_utc, collected_at")
SORTS = {"created_utc": "created_utc", "collected_at": "collected_at", "score": "score"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(
    title="OSINT CyberWatch API",
    description="API REST del panel de inteligencia de amenazas (tesis OSINT, Scopel & Fracchia).",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _where(category, sentiment, subreddit, q):
    clauses, params = [], []
    if category:
        clauses.append("threat_category = %s")
        params.append(category)
    if sentiment:
        clauses.append("sentiment = %s")
        params.append(sentiment)
    if subreddit:
        clauses.append("subreddit = %s")
        params.append(subreddit)
    if q:
        clauses.append("(title ILIKE %s OR content ILIKE %s)")
        like = f"%{q}%"
        params += [like, like]
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


@app.get("/api/health", tags=["sistema"])
def health():
    with db.pool.connection() as c:
        c.execute("SELECT 1")
    return {"status": "ok", "database": "connected"}


@app.get("/api/stats", tags=["analitica"])
def stats(granularity: str = Query("day", pattern="^(day|week)$"),
          days: int = Query(60, ge=1, le=3650)):
    """KPIs en vivo: totales, conteos por categoria/sentimiento/subreddit y serie temporal."""
    with db.pool.connection() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]
        cats = c.execute("SELECT threat_category AS k, COUNT(*) AS n FROM posts GROUP BY 1 ORDER BY 2 DESC").fetchall()
        sents = c.execute("SELECT sentiment AS k, COUNT(*) AS n FROM posts GROUP BY 1 ORDER BY 2 DESC").fetchall()
        subs = c.execute("SELECT subreddit AS k, COUNT(*) AS n FROM posts GROUP BY 1 ORDER BY 2 DESC").fetchall()
        cross = c.execute("SELECT subreddit, sentiment, COUNT(*) AS n FROM posts GROUP BY 1, 2").fetchall()
        last = c.execute("SELECT MAX(collected_at) AS t FROM posts").fetchone()["t"]
        series = c.execute(
            "SELECT date_trunc(%s, created_utc)::date AS period, COUNT(*) AS total, "
            "COUNT(*) FILTER (WHERE threat_category <> 'no_clasificado') AS clasificados "
            "FROM posts WHERE created_utc >= (SELECT MAX(created_utc) FROM posts) - make_interval(days => %s) "
            "GROUP BY 1 ORDER BY 1", (granularity, days)).fetchall()
    return {
        "total_posts": total,
        "by_category": {r["k"]: r["n"] for r in cats},
        "by_sentiment": {r["k"]: r["n"] for r in sents},
        "by_subreddit": {r["k"]: r["n"] for r in subs},
        "sentiment_by_subreddit": cross,
        "last_collected_at": last,
        "granularity": granularity,
        "timeseries": series,
    }


@app.get("/api/posts", response_model=PostPage, tags=["posts"])
def list_posts(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
               sort: str = Query("created_utc", pattern="^(created_utc|collected_at|score)$"),
               order: str = Query("desc", pattern="^(asc|desc)$"),
               category: Optional[Category] = None, sentiment: Optional[Sentiment] = None,
               subreddit: Optional[str] = None, q: Optional[str] = Query(None, max_length=200)):
    """Listado paginado, ordenable y filtrable (filtros combinables; `q` busca en titulo y contenido)."""
    where, params = _where(category, sentiment, subreddit, q)
    with db.pool.connection() as c:
        total = c.execute(f"SELECT COUNT(*) AS n FROM posts{where}", params).fetchone()["n"]
        rows = c.execute(
            f"SELECT {POST_COLS} FROM posts{where} ORDER BY {SORTS[sort]} {order} NULLS LAST, post_id "
            "LIMIT %s OFFSET %s", params + [page_size, (page - 1) * page_size]).fetchall()
    return {"total": total, "page": page, "page_size": page_size, "items": rows}


@app.get("/api/posts/{post_id}", response_model=Post, tags=["posts"])
def get_post(post_id: str):
    with db.pool.connection() as c:
        row = c.execute(f"SELECT {POST_COLS} FROM posts WHERE post_id = %s", (post_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Publicacion no encontrada")
    return row


@app.patch("/api/posts/{post_id}", response_model=Post, tags=["posts"])
def reclassify_post(post_id: str, body: PostUpdate):
    """Triage humano: el analista reclasifica categoria y/o sentimiento."""
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(422, "Indicar threat_category y/o sentiment")
    sets = ", ".join(f"{k} = %s" for k in changes)
    with db.pool.connection() as c:
        row = c.execute(f"UPDATE posts SET {sets} WHERE post_id = %s RETURNING {POST_COLS}",
                        [*changes.values(), post_id]).fetchone()
    if not row:
        raise HTTPException(404, "Publicacion no encontrada")
    return row


@app.delete("/api/posts/{post_id}", tags=["posts"])
def discard_post(post_id: str):
    """Descarta una publicacion (ruido / falso positivo)."""
    with db.pool.connection() as c:
        n = c.execute("DELETE FROM posts WHERE post_id = %s", (post_id,)).rowcount
    if not n:
        raise HTTPException(404, "Publicacion no encontrada")
    return {"deleted": post_id}


# Diferencia deliberada con el UPSERT de n8n: un re-encuentro NO pisa threat_category ni
# sentiment, para no sobrescribir las reclasificaciones manuales de la bandeja de triage.
UPSERT = """
INSERT INTO public.posts (post_id, title, content, raw_content, author, subreddit, url, score,
  num_comments, threat_category, sentiment, compound, created_utc, source, first_seen_at)
VALUES (%(post_id)s, %(title)s, %(content)s, %(raw_content)s, %(author)s, %(subreddit)s, %(url)s,
  %(score)s, %(num_comments)s, %(threat_category)s, %(sentiment)s, %(compound)s, %(created_utc)s,
  %(source)s, NOW())
ON CONFLICT (post_id) DO UPDATE SET score = EXCLUDED.score, num_comments = EXCLUDED.num_comments,
  collected_at = NOW()
RETURNING (xmax = 0) AS inserted
"""


def _sync_local(subreddits: list[str], limit: int) -> SyncResult:
    """Fetch + clasificacion con el modulo real del pipeline y UPSERT en la base."""
    sys.path.insert(0, os.environ.get("PIPELINE_DIR", "/pipeline"))
    import osint_pipeline as p
    p.INTER_SUBREDDIT_DELAY = 2.0      # corrida puntual: sin el espaciado de 150 s del ciclo programado
    p.RETRY_BACKOFF_SECONDS = (10,)
    records = p.collect_records(subreddits, limit)
    if not records:
        return SyncResult(ok=False, mode="local",
                          detail="Sin registros (posible rate limit de Reddit); reintentar en unos minutos")
    p.classify_records(records)
    ins = 0
    with db.pool.connection() as c:
        for r in records:
            r = {**r, "source": "reddit-rss", "created_utc": r.get("created_utc") or None,
                 "content": (r.get("content") or "")[:10000],
                 "raw_content": (r.get("raw_content") or "")[:10000], "title": r["title"][:500]}
            ins += bool(c.execute(UPSERT, r).fetchone()["inserted"])
        total = c.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]
    cats: dict[str, int] = {}
    for r in records:
        cats[r["threat_category"]] = cats.get(r["threat_category"], 0) + 1
    return SyncResult(ok=True, mode="local",
                      detail=f"{len(records)} registros procesados, {ins} altas nuevas",
                      fetched=len(records), inserted=ins, updated=len(records) - ins,
                      total_posts=total, by_category=cats)


def _sync_webhook(url: str) -> SyncResult:
    req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=100) as resp:
        body = resp.read().decode("utf-8", "replace")[:500]
        return SyncResult(ok=True, mode="n8n-webhook", detail=f"Webhook de n8n: HTTP {resp.status} {body}")


@app.post("/api/pipeline/sync", response_model=SyncResult, tags=["pipeline"])
async def sync_pipeline(subreddits: Optional[list[str]] = Query(None), limit: int = Query(25, ge=1, le=100)):
    """Recoleccion/clasificacion puntual: webhook de n8n si N8N_WEBHOOK_URL esta definido; si no, corrida local."""
    url = os.environ.get("N8N_WEBHOOK_URL")
    try:
        if url:
            return await run_in_threadpool(_sync_webhook, url)
        subs = subreddits or ["netsec", "cybersecurity", "malware"]
        return await run_in_threadpool(_sync_local, subs, limit)
    except Exception as exc:  # noqa: BLE001
        LOG.exception("sync fallo")
        return SyncResult(ok=False, mode="n8n-webhook" if url else "local",
                          detail=f"{type(exc).__name__}: {exc}")
