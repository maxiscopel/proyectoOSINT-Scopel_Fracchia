#!/usr/bin/env python3
"""OSINT pipeline v3 — etapa de extracción y transformación.

Lee los feeds Atom/RSS públicos de Reddit (sin Data API), normaliza, clasifica
por categoría de amenaza (palabra completa + conteo + desempate declarado) y
aplica VADER sobre el texto crudo para el análisis de sentimiento.

El enriquecimiento de score/num_comments (--enrich) usa PRAW contra la API de
Reddit y es opcional: sin credenciales o sin praw instalado, esos campos quedan
en 0, limitación de la fuente RSS documentada en la tesis.

n8n invoca las etapas por separado vía Execute Command: `osint_fetch.py`
(extracción RSS) escribe los registros crudos a un archivo y `osint_classify.py`
(transformación) los lee y emite clasificados como JSON array en stdout.
Este script mantiene el modo completo (fetch + clasificar) como interfaz CLI.
Los logs van a stderr.

Uso:
    python3 osint_pipeline.py [--subreddits netsec cybersecurity malware]
                              [--limit 100] [--out salida.json] [--enrich]
"""

import argparse
import hashlib
import html
import json
import logging
import re
import sys
import time

import feedparser

LOG = logging.getLogger("osint_pipeline")

USER_AGENT = "osint-monitor/1.0 by maxis (tesis UTN) py/feedparser"
AUTHOR_SALT = "tesis-osint-2026"  # Sal fija para seudonimización reproducible
# Throttle RSS de Reddit diagnosticado el 02-09-2026 con evidencia de headers:
# x-ratelimit-remaining: 0.0 tras UNA peticion, x-ratelimit-reset: 2 (min).
# Con 3 fetches consecutivos solo el primero tiene exito; los otros reciben
# 429. Backoff y espaciado pensados para ese presupuesto (~1 req / 2 min por IP).
RETRY_BACKOFF_SECONDS = (150, 150)
INTER_SUBREDDIT_DELAY = 150.0  # Espaciado entre subreddits (veces el reset del bucket)
MIN_TEXT_LENGTH = 20


def pseudonymize_author(author: str) -> str:
    """Seudonimiza el autor con SHA-256 + sal. Reversible solo con la sal."""
    return hashlib.sha256((AUTHOR_SALT + author).encode()).hexdigest()[:16]


THREAT_KEYWORDS = {
    "vulnerabilidad": [
        "vulnerability", "cve", "exploit", "patch", "zero day", "0day",
        "disclosure", "advisory", "flaw", "bug",
    ],
    "malware": [
        "malware", "trojan", "backdoor", "rootkit", "spyware", "botnet",
        "keylogger", "dropper", "payload",
    ],
    "phishing": [
        "phishing", "spear phishing", "credential", "fake login",
        "social engineering", "lure", "impersonation",
    ],
    "ransomware": [
        "ransomware", "lockbit", "blackcat", "alphv", "decryptor",
    ],
    "otro": [
        "ddos", "brute force", "injection", "xss", "sqli",
        "privilege escalation", "lateral movement",
    ],
}
# Desempate declarado: si dos categorías empatan en cantidad de coincidencias,
# gana la primera en este orden. Documentado en la tesis (§4.4.2).
TIEBREAK_ORDER = ("vulnerabilidad", "malware", "phishing", "ransomware", "otro")


def _word_regex(term: str) -> str:
    """Expresión regular de palabra completa para un término (multipalabra opcional)."""
    parts = [re.escape(p) for p in term.split()]
    return r"(?<![a-z0-9])" + r"\s+".join(parts) + r"(?![a-z0-9])"


_THREAT_REGEXES = {
    cat: [re.compile(_word_regex(t)) for t in terms]
    for cat, terms in THREAT_KEYWORDS.items()
}


def classify_threat(text: str) -> str:
    """Clasifica por conteo de coincidencias de palabra completa por categoría."""
    lowered = text.lower()
    counts = {}
    for cat, regexes in _THREAT_REGEXES.items():
        counts[cat] = sum(len(rx.findall(lowered)) for rx in regexes)
    best = TIEBREAK_ORDER[0]
    for cat in TIEBREAK_ORDER:
        if counts[cat] > counts[best]:
            best = cat
    return best if counts[best] else "no_clasificado"


_SIA = None


def _sentiment_analyzer():
    global _SIA
    if _SIA is None:
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            _SIA = SentimentIntensityAnalyzer()
        except LookupError:
            import nltk
            nltk.download("vader_lexicon")
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            _SIA = SentimentIntensityAnalyzer()
    return _SIA


def analyze_sentiment(text: str):
    """VADER sobre el texto crudo (sin normalizar). Umbrales documentados ±0.05."""
    compound = _sentiment_analyzer().polarity_scores(text)["compound"]
    if compound >= 0.05:
        return "positivo", compound
    if compound <= -0.05:
        return "negativo", compound
    return "neutral", compound


def enrich_interaction(records: list) -> list:
    """Enriquece score y num_comments desde la API de Reddit (PRAW).

    Solo se activa si praw está instalado y hay credenciales en el entorno
    (REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET). Sin credenciales los campos
    quedan en 0, lo cual está documentado en la tesis como limitación de la
    fuente RSS. La ventana de maduración de 24 h se gestiona en la fase de
    actualización del workflow (no aquí).
    """
    import os

    if not (os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET")):
        LOG.info("Sin credenciales de Reddit: score/num_comments quedan en 0")
        return records
    try:
        import praw
    except ImportError:
        LOG.info("praw no instalado: score/num_comments quedan en 0")
        return records

    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=USER_AGENT,
    )
    for rec in records:
        pid = rec.get("post_id", "")
        if not pid:
            continue
        try:
            submission = reddit.submission(id=pid)
            rec["score"] = submission.score or 0
            rec["num_comments"] = submission.num_comments or 0
        except Exception as exc:  # pragma: no cover - depende de la API externa
            LOG.warning("No se pudo enriquecer %s: %s", pid, exc)
    return records


def fetch_feed(subreddit: str):
    # limit=100: ventana profunda del feed (cubre interrupciones del servicio).
    # v2 02-09-2026, consistente con el workflow osint_monitoreo_rss.
    url = f"https://www.reddit.com/r/{subreddit}/new/.rss?limit=100"
    feed = feedparser.parse(url, agent=USER_AGENT)
    status = getattr(feed, "status", None)
    if status and status >= 400:
        raise RuntimeError(f"HTTP {status} para r/{subreddit}")
    if not feed.entries:
        raise RuntimeError(f"feed vacío para r/{subreddit} (status={status})")
    return feed


def fetch_feed_with_retry(subreddit: str):
    last = None
    for wait in (0,) + RETRY_BACKOFF_SECONDS:
        try:
            return fetch_feed(subreddit)
        except Exception as exc:
            last = exc
            LOG.warning("r/%s falló: %s (retry en %ss)", subreddit, exc, wait)
            if wait:
                time.sleep(wait)
    raise RuntimeError(f"r/{subreddit} agotó reintentos: {last}")


def entry_to_record(entry, subreddit: str) -> dict:
    title = html.unescape(entry.get("title") or "").strip()
    raw_content = entry.get("summary") or ""
    if not raw_content:
        raw_content = "".join(c.value for c in (entry.get("content") or []))
    # Texto crudo para VADER: conserva mayúsculas, puntuación y emoticones (C-08)
    raw_text_for_sentiment = html.unescape(re.sub(r"<[^>]+>", " ", raw_content))
    raw_text_for_sentiment = re.sub(r"\s+", " ", raw_text_for_sentiment).strip()
    # Texto normalizado para clasificación de amenazas
    content = raw_text_for_sentiment.lower()

    link = entry.get("link") or ""
    id_match = re.search(r"/comments/([a-z0-9]{4,12})/", link)
    post_id = id_match.group(1) if id_match else (entry.get("id") or entry.get("guid") or title)
    author = entry.get("author") or (entry.get("author_detail") or {}).get("name") or "reddit"
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    created_utc = time.strftime("%Y-%m-%d %H:%M:%S", published) if published else None

    return {
        "post_id": post_id[:300],
        "title": title[:500],
        "content": content[:10000],
        "raw_content": raw_text_for_sentiment[:10000],
        "author": pseudonymize_author(author),
        "subreddit": subreddit,
        "url": entry.get("link") or "",
        "score": 0,
        "num_comments": 0,
        "threat_category": "no_clasificado",
        "sentiment": "neutral",
        "compound": 0.0,
        "created_utc": created_utc,
        "source": "reddit-rss",
    }


def collect_records(subreddits: list, limit: int) -> list:
    """Extracción: trae los feeds RSS y normaliza los registros crudos.

    Los registros salen SIN clasificar (threat_category='no_clasificado',
    sentiment='neutral', compound=0.0). La clasificación es etapa separada
    (classify_records) para que n8n las ejecute como nodos distintos.
    """
    records = []
    seen = set()
    for sub in subreddits:
        try:
            feed = fetch_feed_with_retry(sub)
        except Exception as exc:
            LOG.error(str(exc))
            continue
        for entry in feed.entries[:limit]:
            rec = entry_to_record(entry, sub)
            text = f"{rec['title']} {rec['content']}"
            if not rec["title"] or len(text) < MIN_TEXT_LENGTH:
                continue
            if rec["post_id"] in seen:
                continue
            seen.add(rec["post_id"])
            records.append(rec)
        time.sleep(INTER_SUBREDDIT_DELAY)
    return records


def classify_records(records: list) -> list:
    """Transformación: clasifica por amenaza (palabra completa) y VADER.

    VADER corre sobre el texto crudo (C-08): mayúsculas, puntuación y
    emoticones preservados. Se modifica la lista in-place y se devuelve.
    """
    for rec in records:
        text = f"{rec['title']} {rec['content']}"
        rec["threat_category"] = classify_threat(text)
        rec["sentiment"], rec["compound"] = analyze_sentiment(f"{rec['title']}\n{rec['raw_content']}")
    return records


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="OSINT pipeline v3 (E/T)")
    parser.add_argument("--subreddits", nargs="*", default=["netsec", "cybersecurity", "malware"])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", default=None, help="Archivo de salida opcional (default: stdout)")
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Enriquecer score/num_comments via API de Reddit (requiere credenciales)",
    )
    args = parser.parse_args(argv)

    records = classify_records(collect_records(args.subreddits, args.limit))

    if args.enrich:
        records = enrich_interaction(records)

    payload = json.dumps(records, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n")

    LOG.info("Ciclo completo: %d registros únicos (subreddits=%s)", len(records), ",".join(args.subreddits))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    main()
