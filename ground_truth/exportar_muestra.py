#!/usr/bin/env python3
"""exportar_muestra.py — genera la muestra de ground truth (Fase 4, v3).

v3 (2026-09-03): diseño por CENSO EN TANDAS (híbrido). El estudio
definitivo incluye TODOS los posts no-piloto recolectados a la fecha de
corte, en tandas incrementales que se etiquetan a medida que el corpus
crece con la operación continua del sistema:

  - Tanda 1 (hoy): censo de los posts disponibles (corpus - piloto).
  - Tanda 2 (corte): censo de los posts nuevos, excluyendo piloto y tanda 1.
  - El estudio está completo cuando n(t1) + n(t2) >= 200.

Ventaja sobre el muestreo por cuotas (v2): nada de lo etiquetado en la
tanda 1 queda fuera del estudio final, y no hay sesgo muestral que
discutir (el estudio ES el corpus no-piloto al corte). --total actúa como
tope por tanda; si hay menos posts disponibles, se toman todos (censo).
La semilla md5 sigue fijando un ORDEN determinista y reproducible de las
filas. --exclude-from ahora acepta VARIOS archivos (p. ej. piloto + tanda 1).

Emite (con el prefijo dado):
  - <prefix>_eval1.csv / <prefix>_eval2.csv : para que cada evaluador
    etiquete a mano. threat_category y sentiment salen VACÍOS y sin las
    etiquetas del pipeline, para no sesgar la decisión humana.
  - <prefix>_gold.csv : etiquetas del pipeline (keywords + VADER), solo
    para el análisis comparativo posterior (evaluar_ground_truth.py).

Uso (desde este directorio, con Docker levantado):

    Tanda 1 (censo de disponibles, excluyendo el piloto):
    python exportar_muestra.py --total 200 --seed "tesis-f4-2026b" \
        --exclude-from muestra_gold.csv --prefix muestra_f4_t1

    Tanda 2 (censo de nuevos, excluyendo piloto y tanda 1):
    python exportar_muestra.py --total 200 --seed "tesis-f4-2026b" \
        --exclude-from muestra_gold.csv muestra_f4_t1_gold.csv \
        --prefix muestra_f4_t2
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


def fetch_corpus() -> list:
    sql = (
        "SELECT json_agg(t) FROM ("
        "SELECT post_id, subreddit, title, raw_content, threat_category, sentiment, compound "
        "FROM public.posts) t;"
    )
    proc = subprocess.run(
        ["docker", "exec", POSTGRES, "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", sql],
        capture_output=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
        sys.exit(1)
    rows = json.loads(proc.stdout.decode("utf-8", errors="replace"))
    return rows or []


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


def sample(corpus: list, quotas: dict, seed: str) -> list:
    """Toma `quotas[sub]` posts por subreddit, ordenados por md5(post_id||seed)."""
    by_sub = {}
    for r in corpus:
        by_sub.setdefault(r["subreddit"], []).append(r)
    picked = []
    for sub, quota in quotas.items():
        pool = by_sub.get(sub, [])
        pool.sort(key=lambda r: hashlib.md5((r["post_id"] + seed).encode()).hexdigest())
        picked.extend(pool[:quota])
    return picked


def load_excluded(paths: list) -> set:
    ids = set()
    for path in paths:
        with open(path, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                pid = (row.get("post_id") or "").strip()
                if pid:
                    ids.add(pid)
    return ids


def write_eval_csv(path: str, records: list) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(EVAL_HEADERS)
        for r in records:
            writer.writerow([r["post_id"], r["subreddit"], r["title"], r["raw_content"], "", ""])


def write_gold_csv(path: str, records: list) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(GOLD_HEADERS)
        for r in records:
            writer.writerow(
                [r["post_id"], r["subreddit"], r["threat_category"], r["sentiment"], r["compound"]]
            )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Exporta la muestra de ground truth (v3, censo en tandas)")
    parser.add_argument("--total", type=int, default=200, help="Tope de posts por tanda (si hay menos, se toman todos)")
    parser.add_argument("--seed", default="tesis-f4-2026b", help="Semilla del orden reproducible de filas")
    parser.add_argument("--prefix", default="muestra200", help="Prefijo de los archivos de salida")
    parser.add_argument(
        "--exclude-from",
        nargs="+",
        default=None,
        help="CSV(s) (p. ej. muestra_gold.csv del piloto, tanda 1) con post_ids a excluir",
    )
    parser.add_argument("--out-dir", default=".", help="Directorio de salida")
    args = parser.parse_args(argv)

    corpus = fetch_corpus()
    excluded = load_excluded(args.exclude_from) if args.exclude_from else set()
    if excluded:
        corpus = [r for r in corpus if r["post_id"] not in excluded]

    counts = {}
    for r in corpus:
        counts[r["subreddit"]] = counts.get(r["subreddit"], 0) + 1
    quotas = largest_remainder(args.total, counts)
    records = sample(corpus, quotas, args.seed)

    out = args.out_dir.rstrip("/")
    with open(f"{out}/{args.prefix}_raw.json", "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    write_eval_csv(f"{out}/{args.prefix}_eval1.csv", records)
    write_eval_csv(f"{out}/{args.prefix}_eval2.csv", records)
    write_gold_csv(f"{out}/{args.prefix}_gold.csv", records)

    print(f"Corpus total: {sum(counts.values())} | excluidos: {len(excluded)}")
    print(f"Muestra: {len(records)} registros | cuotas: {quotas}")
    print(f"Semilla: '{args.seed}' (documentar en la tesis para reproducibilidad)")


if __name__ == "__main__":
    main()
