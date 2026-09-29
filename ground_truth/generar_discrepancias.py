#!/usr/bin/env python3
"""generar_discrepancias.py — lista de discrepancias E1 vs E2 (Fase 4).

Compara los dos archivos de etiquetado individual (eval1/eval2) y emite:

  1. <out>: una fila por post donde E1 y E2 discrepan en categoría y/o
     sentimiento, con título, contenido y las dos etiquetas de cada uno —
     el material de trabajo de la sesión de adjudicación.
  2. <out_resuelto>: plantilla vacía (post_id, threat_category, sentiment)
     con SOLO los ids discrepantes, para que los evaluadores completen
     la etiqueta acordada en la sesión conjunta.

Al terminar, correr evaluar_ground_truth.py con --resuelto <out_resuelto>.

Uso:
    python generar_discrepancias.py --eval1 muestra_f4_t1_eval1.csv \
        --eval2 muestra_f4_t1_eval2.csv --out discrepancias_t1.csv \
        --out-resuelto discrepancias_t1_resueltas.csv
"""

import argparse
import csv

DISC_HEADERS = [
    "post_id", "subreddit", "title", "content",
    "threat_category_E1", "threat_category_E2",
    "sentiment_E1", "sentiment_E2",
]
RESUELTO_HEADERS = ["post_id", "threat_category", "sentiment"]


def load(path):
    rows = {}
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            rows[row["post_id"].strip()] = row
    return rows


def main():
    parser = argparse.ArgumentParser(description="Discrepancias E1 vs E2 (Fase 4)")
    parser.add_argument("--eval1", required=True)
    parser.add_argument("--eval2", required=True)
    parser.add_argument("--out", default="discrepancias.csv")
    parser.add_argument("--out-resuelto", default="discrepancias_resueltas.csv")
    args = parser.parse_args()

    e1 = load(args.eval1)
    e2 = load(args.eval2)
    pids = sorted(set(e1) & set(e2))
    if len(pids) != len(e1) or len(pids) != len(e2):
        print(f"ADVERTENCIA: ids no coinciden (E1={len(e1)}, E2={len(e2)}, comunes={len(pids)})")

    disc = []
    for pid in pids:
        r1, r2 = e1[pid], e2[pid]
        cat_ok = r1["threat_category"].strip() == r2["threat_category"].strip()
        sent_ok = r1["sentiment"].strip() == r2["sentiment"].strip()
        if not (cat_ok and sent_ok):
            disc.append({
                "post_id": pid,
                "subreddit": r1.get("subreddit", ""),
                "title": r1.get("title", ""),
                "content": r1.get("content", "") or r1.get("raw_content", ""),
                "threat_category_E1": r1["threat_category"],
                "threat_category_E2": r2["threat_category"],
                "sentiment_E1": r1["sentiment"],
                "sentiment_E2": r2["sentiment"],
            })

    with open(args.out, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=DISC_HEADERS)
        writer.writeheader()
        writer.writerows(disc)

    with open(args.out_resuelto, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=RESUELTO_HEADERS)
        writer.writeheader()
        for d in disc:
            writer.writerow({"post_id": d["post_id"], "threat_category": "", "sentiment": ""})

    n = len(pids)
    disc_cat = sum(1 for d in disc if d["threat_category_E1"] != d["threat_category_E2"])
    disc_sent = sum(1 for d in disc if d["sentiment_E1"] != d["sentiment_E2"])
    print(f"Posts comparados: {n}")
    print(f"  categoria: acuerdo {n - disc_cat}/{n} ({100.0 * (n - disc_cat) / n:.1f}%) | discrepancias {disc_cat}")
    print(f"  sentimiento: acuerdo {n - disc_sent}/{n} ({100.0 * (n - disc_sent) / n:.1f}%) | discrepancias {disc_sent}")
    print(f"  posts discrepantes (cat o sent): {len(disc)}")
    print(f"  -> material de adjudicacion: {args.out}")
    print(f"  -> plantilla a completar:    {args.out_resuelto}")


if __name__ == "__main__":
    main()
