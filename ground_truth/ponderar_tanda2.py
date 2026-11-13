#!/usr/bin/env python3
"""ponderar_tanda2.py — metricas de la tanda 2 ponderadas por el diseno muestral.

v1 (2026-11-10).

La muestra de tanda 2 (526 publicaciones de un lote de 1.956) se construyo
estratificando por la SALIDA del propio pipeline:

  - Estrato A: la totalidad de las 276 que el pipeline clasifico como
    phishing o ransomware (probabilidad de inclusion 1).
  - Estrato B: 250 de las 1.680 restantes, proporcionales por subreddit
    (probabilidad de inclusion 250/1680 ~= 0,1488).

Informar las metricas de esa muestra sin ponderar sobreestima la
exhaustividad de las clases del estrato A (todo lo que el sistema predijo
en esas clases entra con probabilidad 1). Este script estima las metricas
del clasificador sobre el lote completo de 1.956 mediante ponderacion por
el inverso de la probabilidad de inclusion (peso 1 en A, 1680/250 = 6,72 en
B), con intervalo bootstrap estratificado al 95 % (2.000 remuestreos,
re-muestreando dentro de cada estrato).

Compara, para el conjunto de tanda 2 (n = 526):

  1. Metricas sin ponderar (las que informa la tesis).
  2. Metricas ponderadas por diseno (estimacion para el lote de 1.956).
  3. Totales poblacionales estimados por clase (suma de pesos).

Como control, reproduce primero las cifras del censo de 639 (sin ponderar)
que informa la tesis (F1 micro 0,552 / macro 0,511; sentimiento 0,218).

Entradas (mismo directorio que este script):
  - eval1_639.csv / eval2_639.csv : etiquetas humanas crudas (pre-adjudicacion)
  - resuelto_639.csv              : etiquetas adjudicadas de las 169 discrepancias
  - gold_639.csv                  : etiquetas as-run del pipeline (prediccion)
  - muestra_f4_t2_gold.csv        : los 526 post_id de tanda 2 (mismas
                                    etiquetas del pipeline; define el subconjunto)

Salida: resultados_tanda2_ponderados.md

Uso:
    python ponderar_tanda2.py [--bootstrap 2000] [--seed 42]
"""

import os
import argparse
import csv
import random
from collections import Counter

CATEGORIAS = ["no_clasificado", "vulnerabilidad", "malware", "phishing", "ransomware", "otro"]
SENTIMIENTOS = ["positivo", "negativo", "neutral"]
ESTRATO_A = {"phishing", "ransomware"}

N_LOTE = 1956          # lote de tanda 2 (first_seen > 2026-09-03, 7 subreddits)
N_A = 276              # estrato A: census del pipeline (phishing + ransomware)
N_B = N_LOTE - N_A     # 1680
N_MUESTRA_B = 250      # 250 de 1680 -> peso 6,72
PESO_B = N_B / N_MUESTRA_B


def normalize(value):
    v = str(value).strip().lower()
    aliases = {
        "no_clasificado": "no_clasificado", "no clasificado": "no_clasificado",
        "no_clasif": "no_clasificado", "": "no_clasificado",
        "vulnerabilidades": "vulnerabilidad", "vuln": "vulnerabilidad",
        "phising": "phishing", "ransom": "ransomware", "otros": "otro",
        "positiva": "positivo", "pos": "positivo", "negativa": "negativo",
        "neg": "negativo", "neutro": "neutral", "neutra": "neutral",
    }
    return aliases.get(v, v)


def load_labels(path, cols=("threat_category", "sentiment")):
    rows = {}
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            pid = row["post_id"].strip()
            rows[pid] = {
                "cat": normalize(row.get(cols[0], "")),
                "sent": normalize(row.get(cols[1], "")),
            }
    return rows


def consensus(e1, e2, resuelto):
    """Consenso humano post-adjudicacion.

    Replica la semantica de evaluar_ground_truth.py v3: --resuelto sobrescribe
    e1/e2 COMPLETOS para los pids adjudicados (ambos campos), y el consenso es
    la etiqueta donde e1 == e2 (tras el override, siempre coinciden en los
    resueltos).
    """
    sin_resolver = 0
    out = {}
    for pid in sorted(set(e1) & set(e2)):
        a, b = e1[pid], e2[pid]
        if pid in resuelto:
            a = resuelto[pid]
            b = resuelto[pid]
        if a["cat"] != b["cat"] or a["sent"] != b["sent"]:
            sin_resolver += 1
            continue
        out[pid] = {"cat": a["cat"], "sent": a["sent"]}
    return out, sin_resolver


def prf_weighted(pairs, classes, weights=None):
    """P/R/F1 por clase + macro/micro. pairs: (ref, pred). weights: lista o None."""
    n = len(pairs)
    if weights is None:
        weights = [1.0] * n
    m = {p: {r: 0.0 for r in classes} for p in classes}   # m[pred][ref] += w
    for (ref, pred), w in zip(pairs, weights):
        if ref in classes and pred in classes:
            m[pred][ref] += w
    out = {}
    for c in classes:
        tp = m[c][c]
        pred_c = sum(m[c].values())
        ref_c = sum(m[c2][c] for c2 in classes)
        precision = tp / pred_c if pred_c else 0.0
        recall = tp / ref_c if ref_c else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        out[c] = {"precision": precision, "recall": recall, "f1": f1, "support": ref_c}
    total = sum(sum(m[c].values()) for c in classes)
    tp_sum = sum(m[c][c] for c in classes)
    micro = tp_sum / total if total else 0.0
    macro_f1 = sum(out[c]["f1"] for c in classes) / len(classes)
    return {"classes": out, "micro": micro, "macro": macro_f1}


def main(argv=None):
    # Las rutas de entrada/salida son relativas a este directorio: se puede
    # ejecutar desde la raiz del repositorio o desde ground_truth/.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description="Metricas tanda 2 ponderadas por diseno")
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="resultados_tanda2_ponderados.md")
    args = parser.parse_args(argv)

    e1 = load_labels("eval1_639.csv")
    e2 = load_labels("eval2_639.csv")
    resuelto = load_labels("resuelto_639.csv")
    gold = load_labels("gold_639.csv")            # pipeline (prediccion as-run)
    tanda2_ids = set(load_labels("muestra_f4_t2_gold.csv").keys())

    cons, sin_resolver = consensus(e1, e2, resuelto)
    pids = sorted(cons.keys())
    assert sin_resolver == 0, f"discrepancias sin resolver: {sin_resolver}"

    # --- control: censo de 639 sin ponderar (debe reproducir la tesis) ---
    ref639 = [(cons[p]["cat"], gold[p]["cat"]) for p in pids]
    sent639 = [(cons[p]["sent"], gold[p]["sent"]) for p in pids]
    ctrl = prf_weighted(ref639, CATEGORIAS)
    ctrl_s = prf_weighted(sent639, SENTIMIENTOS)

    # --- subconjunto tanda 2 ---
    pids_t2 = [p for p in pids if p in tanda2_ids]
    n_a = sum(1 for p in pids_t2 if gold[p]["cat"] in ESTRATO_A)
    n_b = len(pids_t2) - n_a

    ref_t2 = [(cons[p]["cat"], gold[p]["cat"]) for p in pids_t2]
    pred_t2 = [(cons[p]["sent"], gold[p]["sent"]) for p in pids_t2]
    w = [1.0 if gold[p]["cat"] in ESTRATO_A else PESO_B for p in pids_t2]

    sin_pon = prf_weighted(ref_t2, CATEGORIAS)
    sin_pon_s = prf_weighted(pred_t2, SENTIMIENTOS)
    pon = prf_weighted(ref_t2, CATEGORIAS, w)
    pon_s = prf_weighted(pred_t2, SENTIMIENTOS, w)

    # totales poblacionales estimados (suma de pesos por clase de consenso)
    tot_est = Counter()
    for p, ww in zip(pids_t2, w):
        tot_est[cons[p]["cat"]] += ww

    # --- bootstrap estratificado ---
    rng = random.Random(args.seed)
    idx_a = [i for i, p in enumerate(pids_t2) if gold[p]["cat"] in ESTRATO_A]
    idx_b = [i for i, p in enumerate(pids_t2) if gold[p]["cat"] not in ESTRATO_A]

    def metricas_boot(indices):
        refs = [ref_t2[i] for i in indices]
        preds = [pred_t2[i] for i in indices]
        ws = [w[i] for i in indices]
        c = prf_weighted(refs, CATEGORIAS, ws)
        s = prf_weighted(preds, SENTIMIENTOS, ws)
        return (c["micro"], c["macro"], s["micro"],
                c["classes"]["phishing"]["recall"],
                c["classes"]["ransomware"]["recall"],
                c["classes"]["vulnerabilidad"]["recall"])

    boots = []
    for _ in range(args.bootstrap):
        idx = ([rng.choice(idx_a) for _ in idx_a] + [rng.choice(idx_b) for _ in idx_b])
        boots.append(metricas_boot(idx))
    names = ["F1 micro categoria", "F1 macro categoria", "F1 micro sentimiento",
             "Exhaustividad phishing", "Exhaustividad ransomware", "Exhaustividad vulnerabilidad"]
    cis = []
    for k in range(len(names)):
        vals = sorted(b[k] for b in boots)
        lo = vals[int(0.025 * args.bootstrap)]
        hi = vals[min(int(0.975 * args.bootstrap), args.bootstrap - 1)]
        cis.append((lo, hi))

    # --- reporte ---
    L = []
    L.append("# Metricas de tanda 2 ponderadas por el diseno muestral")
    L.append("")
    L.append("Generado por `ponderar_tanda2.py` v1 (2026-11-10). La muestra de tanda 2")
    L.append("(526 de 1.956) estratifico por la salida")
    L.append("del propio pipeline (estrato A = las 276 phishing/ransomware que predijo el")
    L.append("sistema, inclusion con probabilidad 1; estrato B = 250 de 1.680, probabilidad")
    L.append("0,1488). Las metricas sin ponderar de esa muestra no estiman el desempeno sobre")
    L.append("el lote: se pondera por el inverso de la probabilidad de inclusion")
    L.append("(peso 1 en A, 6,72 en B).")
    L.append("")
    L.append("## Control: censo de 639 sin ponderar (reproduccion de la tesis)")
    L.append("")
    L.append(f"- F1 micro categoria: **{ctrl['micro']:.3f}** | F1 macro: **{ctrl['macro']:.3f}**")
    L.append(f"- F1 micro sentimiento: **{ctrl_s['micro']:.3f}**")
    L.append(f"- Exhaustividad phishing: {ctrl['classes']['phishing']['recall']:.3f} | "
             f"ransomware: {ctrl['classes']['ransomware']['recall']:.3f} | "
             f"vulnerabilidad: {ctrl['classes']['vulnerabilidad']['recall']:.3f}")
    L.append("")
    L.append("## Tanda 2 (n = 526) sin ponderar / ponderada por diseno")
    L.append("")
    L.append(f"- Estratos en la muestra: A = {n_a} (esperado {N_A}), B = {n_b} (esperado {N_MUESTRA_B})")
    L.append("")
    L.append("| Metrica | Sin ponderar | Ponderada (IC 95 % bootstrap) |")
    L.append("|---|---|---|")
    rows = [
        ("F1 micro categoria", sin_pon["micro"], pon["micro"]),
        ("F1 macro categoria", sin_pon["macro"], pon["macro"]),
        ("F1 micro sentimiento", sin_pon_s["micro"], pon_s["micro"]),
        ("Exhaustividad phishing", sin_pon["classes"]["phishing"]["recall"], pon["classes"]["phishing"]["recall"]),
        ("Exhaustividad ransomware", sin_pon["classes"]["ransomware"]["recall"], pon["classes"]["ransomware"]["recall"]),
        ("Exhaustividad vulnerabilidad", sin_pon["classes"]["vulnerabilidad"]["recall"], pon["classes"]["vulnerabilidad"]["recall"]),
    ]
    for (nombre, v_sin, v_pon), (lo, hi) in zip(rows, cis):
        L.append(f"| {nombre} | {v_sin:.3f} | **{v_pon:.3f}** [{lo:.3f}; {hi:.3f}] |")
    L.append("")
    L.append("Intervalos: bootstrap estratificado al 95 % ("
             f"{args.bootstrap} remuestreos dentro de cada estrato, semilla {args.seed}).")
    L.append("")
    L.append("## Totales poblacionales estimados por clase (lote de 1.956)")
    L.append("")
    L.append("| Clase (consenso) | Casos en la muestra | Total estimado en el lote |")
    L.append("|---|---|---|")
    muestra_counts = Counter(cons[p]["cat"] for p in pids_t2)
    for c in CATEGORIAS:
        L.append(f"| {c} | {muestra_counts.get(c, 0)} | {tot_est.get(c, 0.0):.0f} |")
    L.append(f"| **Total** | **{len(pids_t2)}** | **{sum(tot_est.values()):.0f}** |")
    L.append("")
    L.append("## Nota metodologica")
    L.append("")
    L.append("El estrato A incluye con probabilidad 1 todo lo que el propio sistema predijo")
    L.append("como phishing o ransomware; por eso la exhaustividad sin ponderar de esas")
    L.append("clases en la muestra (condicionada al diseno) no es la del lote. La ponderacion")
    L.append("por el inverso de la probabilidad de inclusion corrige ese sesgo: la")
    L.append("exhaustividad de phishing pasa de sobrestimada a su estimacion poblacional.")
    L.append("El conjunto de 639 NO es un censo del corpus ampliado: es el censo del corpus")
    L.append("analizado (113) mas una muestra estratificada de un lote distinto.")

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"OK: {args.out}")
    print(f"  control 639: micro {ctrl['micro']:.3f} / macro {ctrl['macro']:.3f} / sent {ctrl_s['micro']:.3f}")
    print(f"  526 sin ponderar: micro {sin_pon['micro']:.3f} / macro {sin_pon['macro']:.3f} / sent {sin_pon_s['micro']:.3f}")
    print(f"  526 ponderado:    micro {pon['micro']:.3f} [{cis[0][0]:.3f}; {cis[0][1]:.3f}] / "
          f"macro {pon['macro']:.3f} / sent {pon_s['micro']:.3f}")
    print(f"  recall phish {pon['classes']['phishing']['recall']:.3f} | "
          f"ransom {pon['classes']['ransomware']['recall']:.3f} | "
          f"vuln {pon['classes']['vulnerabilidad']['recall']:.3f}")


if __name__ == "__main__":
    main()
