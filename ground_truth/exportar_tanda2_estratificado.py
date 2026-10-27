#!/usr/bin/env python3
"""exportar_tanda2_estratificado.py — tanda 2 del censo (Fase 4, estratificada).

v1 (2026-10-13): tanda 2 con diseño ESTRATIFICADO, pedida por el lado del
documento para crecer las clases escasas del censo de 113 (phishing 5,
ransomware 4 en el oro humano):

  - Estrato A (censo completo): TODOS los posts del pool cuya etiqueta del
    pipeline es phishing o ransomware.
  - Estrato B (muestra proporcional): --total-b posts del resto del pool,
    con cuotas proporcionales por subreddit (resto mayor) y orden
    determinista md5(post_id||seed) — el mismo patrón de exportar_muestra.py
    v3, para que el F1 recalculado sobre el censo expandido no quede sesgado
    por seleccionar solo sobre las etiquetas del propio pipeline.

Pool: posts con first_seen_at posterior al corte del censo de 113
(default 2026-09-03 00:00 UTC), excluyendo los post_ids ya etiquetados
(piloto + tanda 1) via --exclude-from.

Emite (en --out-dir):
  - posts_dataset_tanda2_<N>_completo.csv : el POOL COMPLETO con las 15
    columnas y el orden de posts_dataset_tanda1_53_completo.csv.
  - <prefix>_eval1.csv / <prefix>_eval2.csv : para etiquetado a mano
    (etiquetas VACIAS, sin las del pipeline).
  - <prefix>_gold.csv : etiquetas del pipeline del sample (A+B).
  - <prefix>_raw.json : registros del sample.

Uso (desde tesis/ground_truth, con Docker levantado):

    python exportar_tanda2_estratificado.py \
        --exclude-from muestra_gold.csv muestra_f4_t1_gold.csv \
        --total-b 250 --seed "tesis-f4-2026c" --prefix muestra_f4_t2
"""

import argparse
import csv
import hashlib
import json
import subprocess
import sys

POSTGRES = "osint-postgres"
DB_USER = "osint_user"
DB_NAME = "osint_db"

EVAL_HEADERS = ["post_id", "subreddit", "title", "content", "threat_category", "sentiment"]
GOLD_HEADERS = ["post_id", "subreddit", "threat_category", "sentiment", "compound"]
DATASET_HEADERS = [
    "post_id", "subreddit", "created_utc", "title", "content", "raw_content",
    "author", "url", "score", "num_comments", "threat_category", "sentiment",
    "compound", "collected_at", "source",
]

POOL_SQL = (
    "SELECT json_agg(t) FROM ("
    "SELECT post_id, subreddit, title, content, raw_content, author, url, "
    "score, num_comments, threat_category, sentiment, compound, created_utc, "
    "collected_at, source "
    "FROM public.posts WHERE first_seen_at > '{corte}'"
    ") t;"
)


def fetch_pool(corte: str) -> list:
    proc = subprocess.run(
        ["docker", "exec", POSTGRES, "psql", "-U", DB_USER, "-d", DB_NAME,
         "-t", "-A", "-c", POOL_SQL.format(corte=corte)],
        capture_output=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
        sys.exit(1)
    rows = json.loads(proc.stdout.decode("utf-8", errors="replace"))
    return rows or []


def load_excluded(paths: list) -> set:
    ids = set()
    for path in paths:
        with open(path, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                pid = (row.get("post_id") or "").strip()
                if pid:
                    ids.add(pid)
    return ids


def largest_remainder(total: int, counts: dict) -> dict:
    """Reparte `total` entre subreddits proporcional a `counts` (resto mayor)."""
    if not counts:
        return {}
    grand = sum(counts.values())
    if grand <= total:
        return dict(counts)
    quotas = {}
    remainders = []
    assigned = 0
    for sub, n in counts.items():
        exact = total * n / grand
        q = int(exact)
        quotas[sub] = q
        assigned += q
        remainders.append((exact - q, sub))
    rest = total - assigned
    remainders.sort(reverse=True)
    for _, sub in remainders[:rest]:
        quotas[sub] += 1
    return quotas


def md5_key(row: dict, seed: str) -> str:
    return hashlib.md5((row["post_id"] + seed).encode()).hexdigest()


def ts(v) -> str:
    """'2026-10-05T17:22:57.367083+00:00' -> '2026-10-05 17:22:57.367083'."""
    if not v:
        return ""
    return str(v).replace("T", " ").replace("+00:00", "")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Tanda 2 estratificada (Fase 4)")
    parser.add_argument("--total-b", type=int, default=250,
                        help="Tope del estrato B (muestra proporcional del resto)")
    parser.add_argument("--seed", default="tesis-f4-2026c",
                        help="Semilla del orden reproducible de filas")
    parser.add_argument("--prefix", default="muestra_f4_t2")
    parser.add_argument("--exclude-from", nargs="+", default=None,
                        help="CSV(s) con post_ids ya etiquetados (piloto, tanda 1)")
    parser.add_argument("--corte", default="2026-09-03 00:00+00",
                        help="Corte del pool sobre first_seen_at (UTC)")
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args(argv)

    pool = fetch_pool(args.corte)
    n_pool_bruto = len(pool)
    excluded = load_excluded(args.exclude_from) if args.exclude_from else set()
    if excluded:
        pool = [r for r in pool if r["post_id"] not in excluded]
    print(f"Pool bruto (first_seen > {args.corte}): {n_pool_bruto}")
    print(f"Excluidos (ya etiquetados): {len(excluded)} -> pool final: {len(pool)}")

    estrato_a = [r for r in pool if r["threat_category"] in ("phishing", "ransomware")]
    resto = [r for r in pool if r["threat_category"] not in ("phishing", "ransomware")]
    counts = {}
    for r in resto:
        counts[r["subreddit"]] = counts.get(r["subreddit"], 0) + 1
    quotas = largest_remainder(args.total_b, counts)

    by_sub = {}
    for r in resto:
        by_sub.setdefault(r["subreddit"], []).append(r)
    estrato_b = []
    for sub, quota in quotas.items():
        candidatos = sorted(by_sub.get(sub, []), key=lambda r: md5_key(r, args.seed))
        estrato_b.extend(candidatos[:quota])

    estrato_a.sort(key=lambda r: (r["subreddit"], md5_key(r, args.seed)))
    estrato_b.sort(key=lambda r: (r["subreddit"], md5_key(r, args.seed)))
    sample = estrato_a + estrato_b

    n_a = {}
    for r in estrato_a:
        n_a[r["threat_category"]] = n_a.get(r["threat_category"], 0) + 1
    print(f"Estrato A (todos los phishing/ransomware del pool): {len(estrato_a)} {n_a}")
    print(f"Estrato B (proporcional por subreddit, total {args.total_b}): {len(estrato_b)} {quotas}")
    print(f"Sample total (A+B): {len(sample)}")

    vacios_content = sum(1 for r in pool if not (r.get("content") or "").strip())
    vacios_raw = sum(1 for r in pool if not (r.get("raw_content") or "").strip())
    print(f"Vacios en el pool: content {vacios_content} | raw_content {vacios_raw}")
    if vacios_content or vacios_raw:
        for r in pool:
            if not (r.get("content") or "").strip() or not (r.get("raw_content") or "").strip():
                print(f"  AVISO: post {r['post_id']} con texto vacio (sub={r['subreddit']})")

    out = args.out_dir.rstrip("/")

    pool_ordenado = sorted(pool, key=lambda r: (r.get("created_utc") or "", r["post_id"]))
    dataset_path = f"{out}/posts_dataset_tanda2_{len(pool)}_completo.csv"
    with open(dataset_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(DATASET_HEADERS)
        for r in pool_ordenado:
            writer.writerow([
                r["post_id"], r["subreddit"], ts(r.get("created_utc")), r["title"],
                r.get("content") or "", r.get("raw_content") or "", r["author"],
                r.get("url") or "", r.get("score", 0), r.get("num_comments", 0),
                r["threat_category"], r["sentiment"],
                f"{float(r['compound'] or 0):.4f}",
                ts(r.get("collected_at")), r.get("source") or "",
            ])
    print(f"Escribio {dataset_path} ({len(pool)} filas, 15 columnas)")

    for suffix in ("eval1", "eval2"):
        path = f"{out}/{args.prefix}_{suffix}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(EVAL_HEADERS)
            for r in sample:
                writer.writerow([r["post_id"], r["subreddit"], r["title"],
                                 r.get("raw_content") or "", "", ""])
        print(f"Escribio {path} ({len(sample)} filas, etiquetas vacias)")

    gold_path = f"{out}/{args.prefix}_gold.csv"
    with open(gold_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(GOLD_HEADERS)
        for r in sample:
            writer.writerow([r["post_id"], r["subreddit"], r["threat_category"],
                             r["sentiment"], r["compound"]])
    print(f"Escribio {gold_path}")

    raw_path = f"{out}/{args.prefix}_raw.json"
    with open(raw_path, "w", encoding="utf-8") as fh:
        json.dump(sample, fh, ensure_ascii=False, indent=2)
    print(f"Escribio {raw_path}")

    print(f"Reproducibilidad: seed '{args.seed}' | corte {args.corte} | "
          f"excluidos {len(excluded)} | estrato A {len(estrato_a)} + estrato B {len(estrato_b)}")


if __name__ == "__main__":
    main()
