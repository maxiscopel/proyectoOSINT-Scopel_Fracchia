"""OSINT CyberWatch - API REST (FastAPI) sobre la tabla `posts` del pipeline OSINT."""
import csv
import hashlib
import io
import json
import logging
import os
import sys
import threading
import time
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import database as db
from schemas import Category, NewPost, Post, PostPage, PostUpdate, Sentiment, SyncResult

SYNC_USER_AGENT = "OSINT-CyberWatch-UTN/1.0 (tesis UTN FRM; lectura RSS publica)"
SYNC_DELAY_SECONDS = 6.0     # pausa entre subreddits: Reddit permite ~1 req/2 min por IP en RSS
SYNC_COOLDOWN_SECONDS = 90   # separacion minima entre dos sincronizaciones consecutivas
_sync_lock = threading.Lock()
_last_sync = -1e9
EXPORT_LIMIT = 50000

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


def _csv_cell(v):
    """Neutraliza inyeccion de formulas al abrir el CSV en Excel/Sheets."""
    if v is None:
        return ""
    s = v.isoformat(sep=" ") if isinstance(v, datetime) else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


@app.get("/api/posts/export", tags=["posts"])
def export_posts(category: Optional[Category] = None, sentiment: Optional[Sentiment] = None,
                 subreddit: Optional[str] = None, q: Optional[str] = Query(None, max_length=200)):
    """Descarga en CSV (UTF-8 con BOM) los registros que cumplen los filtros activos."""
    where, params = _where(category, sentiment, subreddit, q)
    cols = ["post_id", "created_utc", "subreddit", "title", "content", "threat_category",
            "sentiment", "compound", "score", "num_comments", "url", "author", "collected_at"]
    with db.pool.connection() as c:
        rows = c.execute(f"SELECT {', '.join(cols[:7])}, compound::float AS compound, score, num_comments, "
                         f"url, author, collected_at FROM posts{where} ORDER BY created_utc DESC NULLS LAST, post_id "
                         "LIMIT %s", params + [EXPORT_LIMIT]).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(cols)
    for r in rows:
        w.writerow([_csv_cell(r[k]) for k in cols])
    name = f"osint_posts_{datetime.now(timezone.utc):%Y%m%d_%H%M}.csv"
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"',
                                      "X-Total-Rows": str(len(rows))})


def _clean_source(s: str) -> str:
    """Quita el prefijo 'r/' (o '/r/') para que la fuente nunca se duplique como r/r/xxx."""
    import re
    return re.sub(r"^(?:/?r/)+", "", s.strip(), flags=re.IGNORECASE).strip()


@app.post("/api/posts", response_model=Post, status_code=201, tags=["posts"])
def create_post(body: NewPost):
    """Ingreso manual: pasa titulo+texto por el clasificador real y VADER del pipeline y lo guarda."""
    p = _pipeline()
    title, content = body.title.strip(), body.content.strip()
    threat = p.classify_threat(f"{title} {content}")
    sentiment, compound = p.analyze_sentiment(f"{title}\n{content}")
    now = datetime.now(timezone.utc)
    pid = "manual-" + hashlib.sha256(f"{title}|{content}|{now.isoformat()}".encode()).hexdigest()[:12]
    with db.pool.connection() as c:
        row = c.execute(
            "INSERT INTO posts (post_id, title, content, raw_content, author, subreddit, url, threat_category, "
            "sentiment, compound, created_utc, source) VALUES (%s,%s,%s,%s,'analista-manual',%s,%s,%s,%s,%s,%s,'manual') "
            f"RETURNING {POST_COLS}",
            (pid, title, content, content, _clean_source(body.source) or "manual", body.url or None, threat, sentiment,
             compound, now.replace(tzinfo=None))).fetchone()
    return row


@app.get("/api/posts/{post_id}", response_model=Post, tags=["posts"])
def get_post(post_id: str):
    with db.pool.connection() as c:
        row = c.execute(f"SELECT {POST_COLS} FROM posts WHERE post_id = %s", (post_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Publicacion no encontrada")
    return row


TRANSLATE_CHUNK = 4500


def _split_text(text: str, limit: int = TRANSLATE_CHUNK) -> list[str]:
    """Divide en bloques <= limit, cortando en saltos de linea o espacios (nunca a mitad de palabra)."""
    chunks = []
    while len(text) > limit:
        cut = max(text.rfind("\n", 0, limit), text.rfind(". ", 0, limit) + 1, text.rfind(" ", 0, limit))
        cut = cut if cut > 0 else limit
        chunks.append(text[:cut])
        text = text[cut:]
    chunks.append(text)
    return [c for c in chunks if c.strip()] or [""]


MYMEMORY_CHUNK = 450          # MyMemory admite ~500 caracteres por request
_TRANSLATION_CACHE: dict[str, dict] = {}   # post_id -> respuesta exitosa (en memoria del proceso)
_CACHE_MAX = 1000


def _translate_with(translator, text: str, limit: int) -> str:
    if not text or not text.strip():
        return text or ""
    out = []
    for chunk in _split_text(text, limit):
        res = translator.translate(chunk) or ""
        if res.upper().startswith("MYMEMORY WARNING"):   # cuota diaria agotada: MyMemory lo devuelve como texto
            raise RuntimeError(res[:200])
        out.append(res)
    return "".join(out)


def _translate_post_texts(title: str, content: str) -> tuple[str, str, str]:
    """Google primero; si falla o limita, MyMemory (en-GB -> es-ES, bloques de 450). Devuelve (titulo, contenido, proveedor)."""
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    errors = []
    try:
        g = GoogleTranslator(source="auto", target="es")
        return (_translate_with(g, title, TRANSLATE_CHUNK), _translate_with(g, content, TRANSLATE_CHUNK), "google")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"google: {type(exc).__name__}")
        LOG.warning("Google Translate fallo (%s); se usa MyMemory", exc)
    try:
        m = MyMemoryTranslator(source="en-GB", target="es-ES")
        return (_translate_with(m, title, MYMEMORY_CHUNK), _translate_with(m, content, MYMEMORY_CHUNK), "mymemory")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"mymemory: {type(exc).__name__}: {str(exc)[:120]}")
        raise RuntimeError("; ".join(errors)) from exc


@app.post("/api/posts/{post_id}/translate", tags=["posts"])
async def translate_post(post_id: str):
    """Traduce al espanol titulo y contenido: Google Translate con fallback a MyMemory y cache en memoria."""
    cached = _TRANSLATION_CACHE.get(post_id)
    if cached:
        return {**cached, "cached": True}
    with db.pool.connection() as c:
        row = c.execute("SELECT title, content FROM posts WHERE post_id = %s", (post_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Publicacion no encontrada")
    try:
        title, content, provider = await run_in_threadpool(_translate_post_texts, row["title"], row["content"] or "")
    except Exception as exc:  # noqa: BLE001 - ambos servicios fallaron
        LOG.warning("traduccion fallo en todos los proveedores: %s", exc)
        raise HTTPException(503, "No se pudo traducir: Google Translate y MyMemory no respondieron o limitaron "
                                 "las solicitudes desde esta conexion; reintentar en unos minutos") from exc
    result = {"post_id": post_id, "title": title, "content": content, "target": "es", "provider": provider}
    if len(_TRANSLATION_CACHE) >= _CACHE_MAX:
        _TRANSLATION_CACHE.pop(next(iter(_TRANSLATION_CACHE)))
    _TRANSLATION_CACHE[post_id] = result
    return {**result, "cached": False}


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


def _pipeline():
    """Importa el modulo real del pipeline (montado en /pipeline)."""
    pdir = os.environ.get("PIPELINE_DIR", "/pipeline")
    if pdir not in sys.path:
        sys.path.insert(0, pdir)
    import osint_pipeline as p
    return p


SAMPLE_FEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_feed.xml")


class _Blocked(Exception):
    """Reddit no entrego registros (reason: 'rate_limited' si todas las fuentes dieron HTTP 429)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _upsert_records(records: list[dict]) -> tuple[int, int, dict[str, int]]:
    """UPSERT de registros ya clasificados. Devuelve (altas, total_en_base, conteo_por_categoria)."""
    ins = 0
    with db.pool.connection() as c:
        for r in records:
            r = {**r, "source": r.get("source") or "reddit-rss", "created_utc": r.get("created_utc") or None,
                 "content": (r.get("content") or "")[:10000],
                 "raw_content": (r.get("raw_content") or "")[:10000], "title": r["title"][:500]}
            ins += bool(c.execute(UPSERT, r).fetchone()["inserted"])
        total = c.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]
    cats: dict[str, int] = {}
    for r in records:
        cats[r["threat_category"]] = cats.get(r["threat_category"], 0) + 1
    return ins, total, cats


def _sync_local_locked(subreddits: list[str], limit: int) -> SyncResult:
    """Respaldo si el webhook no responde: corre el modulo real del pipeline dentro de la API."""
    p = _pipeline()
    p.USER_AGENT = SYNC_USER_AGENT                 # User-Agent unico y descriptivo
    p.INTER_SUBREDDIT_DELAY = SYNC_DELAY_SECONDS   # corrida puntual: sin el espaciado de 150 s del ciclo programado
    p.RETRY_BACKOFF_SECONDS = (15,)
    errors: list[str] = []
    orig = p.fetch_feed_with_retry

    def traced(sub):
        try:
            return orig(sub)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            raise

    p.fetch_feed_with_retry = traced
    try:
        records = p.collect_records(subreddits, limit)
    finally:
        p.fetch_feed_with_retry = orig
    if not records:
        raise _Blocked("rate_limited" if errors and all("429" in e for e in errors) else "no_records")
    p.classify_records(records)
    ins, total, cats = _upsert_records(records)
    return SyncResult(ok=True, mode="local", detail=f"{len(records)} registros procesados, {ins} altas nuevas",
                      fetched=len(records), inserted=ins, updated=len(records) - ins,
                      total_posts=total, by_category=cats)


def _sync_webhook(url: str) -> SyncResult:
    """Dispara el workflow de n8n (Webhook -> fetch/clasificacion -> PostgreSQL) y devuelve su resumen."""
    req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=100) as resp:
        body = json.loads(resp.read().decode("utf-8", "replace"))
    if body.get("ok") is False:
        if body.get("reason") in ("rate_limited", "no_records"):
            raise _Blocked(body["reason"])
        raise RuntimeError(f"n8n respondio con error: {str(body)[:200]}")
    with db.pool.connection() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]
    return SyncResult(ok=True, mode="n8n-webhook", detail=body.get("detail", "Sincronizacion en n8n completada"),
                      fetched=int(body.get("fetched", 0)), inserted=int(body.get("inserted", 0)),
                      updated=int(body.get("updated", 0)), total_posts=total)


_SAMPLE_NOTES = {
    "rate_limited": "respaldo local por límite de tasa de Reddit",
    "cooldown": "respaldo local: sincronización reciente, se evita saturar a Reddit",
}


def _sync_sample(reason: str) -> SyncResult:
    """Respaldo: procesa un feed Atom local (entradas reales del RSS de Reddit) con el pipeline real y UPSERT."""
    import re
    import feedparser
    p = _pipeline()
    feed = feedparser.parse(SAMPLE_FEED)
    records = []
    for entry in feed.entries:
        m = re.search(r"/r/([^/]+)/comments/", entry.get("link", ""))
        records.append(p.entry_to_record(entry, (m.group(1) if m else "cybersecurity").lower()))
    if not records:
        raise RuntimeError("sample_feed.xml no contiene entradas")
    p.classify_records(records)
    ins, total, cats = _upsert_records(records)
    note = _SAMPLE_NOTES.get(reason, "respaldo local: Reddit no disponible")
    return SyncResult(ok=True, mode="respaldo-local",
                      detail=f"Sincronización completada ({note}): {len(records)} registros procesados.",
                      fetched=len(records), inserted=ins, updated=len(records) - ins,
                      total_posts=total, by_category=cats)


def _sync_orchestrate(subreddits: list[str], limit: int) -> SyncResult:
    """n8n (webhook) -> pipeline local -> feed de muestra. Reddit bloqueando NUNCA devuelve error."""
    global _last_sync
    if not _sync_lock.acquire(blocking=False):
        return _sync_sample("cooldown")
    try:
        if time.monotonic() - _last_sync < SYNC_COOLDOWN_SECONDS:
            return _sync_sample("cooldown")
        _last_sync = time.monotonic()
        url = os.environ.get("N8N_WEBHOOK_URL")
        try:
            if url:
                try:
                    return _sync_webhook(url)
                except _Blocked:
                    raise
                except Exception as exc:  # noqa: BLE001 - webhook caido/inactivo: respaldo con osint_pipeline.py
                    LOG.warning("webhook de n8n no respondio (%s); se ejecuta osint_pipeline.py localmente", exc)
            return _sync_local_locked(subreddits, limit)
        except _Blocked as b:
            return _sync_sample(b.reason)
        except Exception as exc:  # noqa: BLE001
            LOG.exception("sync fallo; se usa el respaldo local")
            return _sync_sample(type(exc).__name__)
    finally:
        _sync_lock.release()


@app.post("/api/pipeline/sync", response_model=SyncResult, tags=["pipeline"])
async def sync_pipeline(subreddits: Optional[list[str]] = Query(None), limit: int = Query(25, ge=1, le=100)):
    """Sincronizacion puntual: webhook de n8n; si no responde, osint_pipeline.py local; si Reddit bloquea
    (HTTP 429), respaldo con sample_feed.xml. Solo devuelve ok=false si tambien falla el respaldo local."""
    subs = subreddits or ["netsec", "cybersecurity", "malware"]
    try:
        return await run_in_threadpool(_sync_orchestrate, subs, limit)
    except Exception as exc:  # noqa: BLE001
        LOG.exception("sync fallo incluso el respaldo local")
        return SyncResult(ok=False, mode="error", detail=f"{type(exc).__name__}: {exc}")
