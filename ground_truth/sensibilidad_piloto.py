#!/usr/bin/env python3
"""sensibilidad_piloto.py — sensibilidad exacta de la adjudicacion del piloto.

El 28/9/2026 las 22 discrepancias del piloto (n=60 del censo de 113) se
adjudicaron en bloque a favor de la etiqueta del Evaluador 1
(registro_adjudicacion_piloto.md). Este script recalcula el desempeno del
pipeline sobre el censo de 113 en dos escenarios:

  - declarado:  las 22 discrepancias quedan con la etiqueta de E1 (censo_gold_humano_113.csv);
  - alternativo: las 22 se adjudican a favor de E2 (discrepancias_piloto.csv, columnas *_E2).

El resto del consenso (91 posts) no cambia. Metricas: F1 micro y macro de
categoria (6 clases) y de sentimiento (3 clases) del pipeline
(censo_gold_pipeline_113.csv) contra cada consenso. Biblioteca estandar.

Uso (desde cualquier directorio):
    python ground_truth/sensibilidad_piloto.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATS = ["no_clasificado", "vulnerabilidad", "malware", "phishing", "ransomware", "otro"]
SENTS = ["positivo", "negativo", "neutral"]


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def f1s(y_true, y_pred, labels):
    """(F1 micro, F1 macro). Micro con todas las clases = exactitud; macro sobre `labels`."""
    micro = sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true)
    fs = []
    for lab in labels:
        tp = sum(t == lab and p == lab for t, p in zip(y_true, y_pred))
        fp = sum(t != lab and p == lab for t, p in zip(y_true, y_pred))
        fn = sum(t == lab and p != lab for t, p in zip(y_true, y_pred))
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        fs.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    return micro, sum(fs) / len(fs)


def main():
    human = {r["post_id"]: r for r in read("censo_gold_humano_113.csv")}
    pipe = {r["post_id"]: r for r in read("censo_gold_pipeline_113.csv")}
    disc = {r["post_id"]: r for r in read("discrepancias_piloto.csv")}
    assert len(human) == 113 and set(human) == set(pipe) and len(disc) == 22 and set(disc) <= set(human)

    alt = {pid: dict(r) for pid, r in human.items()}
    for pid, d in disc.items():
        alt[pid]["threat_category"] = d["threat_category_E2"]
        alt[pid]["sentiment"] = d["sentiment_E2"]
    cambia_cat = sum(alt[p]["threat_category"] != human[p]["threat_category"] for p in disc)
    cambia_sen = sum(alt[p]["sentiment"] != human[p]["sentiment"] for p in disc)

    ids = sorted(human)
    res = {}
    for nombre, g in (("declarada (E1)", human), ("alternativa (E2)", alt)):
        ct = [g[i]["threat_category"] for i in ids]
        cp = [pipe[i]["threat_category"] for i in ids]
        st = [g[i]["sentiment"] for i in ids]
        sp = [pipe[i]["sentiment"] for i in ids]
        res[nombre] = (*f1s(ct, cp, CATS), *f1s(st, sp, SENTS))

    print(f"Censo de 113; 22 discrepancias del piloto. Cambian de etiqueta al pasar a E2: "
          f"categoria {cambia_cat}/22, sentimiento {cambia_sen}/22.\n")
    print(f"{'Metrica (censo de 113)':32s}" + "".join(f"{n:>20s}" for n in res))
    for i, m in enumerate(["F1 micro de categoria", "F1 macro de categoria",
                           "F1 micro de sentimiento", "F1 macro de sentimiento"]):
        print(f"{m:32s}" + "".join(f"{v[i]:>20.3f}" for v in res.values()))


if __name__ == "__main__":
    main()
