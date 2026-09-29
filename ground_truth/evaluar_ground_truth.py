#!/usr/bin/env python3
"""evaluar_ground_truth.py — métricas de la Fase 4 (ground truth, v3).

v3 (2026-09-03): reporta el kappa inter-evaluador PRE-adjudicación (el
acuerdo genuino entre etiquetadores individuales) además del consenso
post-adjudicación; valida que el archivo --resuelto tenga etiquetas
completas y válidas antes de aplicarlo (antes una etiqueta vacía se
normalizaba en silencio como no_clasificado y corrompía el reporte).

v2 (2026-09-02): agrega intervalos de confianza bootstrap al 95 % para el
kappa inter-evaluador y para los F1 (micro y macro) del pipeline vs.
consenso; corrige el conteo de excluidos (antes hardcodeado en 60).

Compara las etiquetas humanas (eval1/eval2) entre sí y contra las del
pipeline (gold). Calcula y reporta:

  - Kappa de Cohen pre-adjudicación (acuerdo inter-evaluador) + IC.
  - Acuerdo evaluador vs. pipeline (etiquetas individuales) + kappa.
  - Consenso humano (post-adjudicación con --resuelto) y conteo de
    discrepancias resueltas.
  - Matriz de confusión del pipeline vs. consenso humano, por categoría y
    por sentimiento.
  - Precisión, exhaustividad (recall) y F1 por clase + macro/micro + IC.
  - Test chi-cuadrado de asociación (bootstrap por permutación, p-valor) y
    V de Cramér como tamaño de efecto.

Sin dependencias externas (stdlib). Genera un reporte Markdown.

Uso:
    python evaluar_ground_truth.py --eval1 muestra_f4_t1_eval1.csv \
        --eval2 muestra_f4_t1_eval2.csv --gold muestra_f4_t1_gold.csv \
        [--resuelto discrepancias_t1_resueltas.csv] \
        [--perm 2000] [--bootstrap 2000] [--out resultados_tanda1.md]
"""

import argparse
import csv
import random
from collections import Counter

CATEGORIAS = ["no_clasificado", "vulnerabilidad", "malware", "phishing", "ransomware", "otro"]
SENTIMIENTOS = ["positivo", "negativo", "neutral"]

ALIAS = {
    "no_clasificado": "no_clasificado", "no clasificado": "no_clasificado", "no_clasif": "no_clasificado",
    "sin categoria": "no_clasificado", "sin categoría": "no_clasificado", "ninguna": "no_clasificado",
    "none": "no_clasificado", "": "no_clasificado",
    "vulnerabilidad": "vulnerabilidad", "vulnerabilidades": "vulnerabilidad", "vuln": "vulnerabilidad",
    "malware": "malware", "trojan": "malware",
    "phishing": "phishing", "phising": "phishing",
    "ransomware": "ransomware", "ransom": "ransomware",
    "otro": "otro", "otros": "otro", "other": "otro",
    "positivo": "positivo", "positiva": "positivo", "pos": "positivo",
    "negativo": "negativo", "negativa": "negativo", "neg": "negativo",
    "neutral": "neutral", "neutro": "neutral", "neutra": "neutral",
    "neutre": "neutral",
}


def normalize(value: str) -> str:
    return ALIAS.get(str(value).strip().lower(), str(value).strip().lower())


def load_eval(path: str) -> dict:
    rows = {}
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            pid = row["post_id"].strip()
            rows[pid] = {
                "cat": normalize(row.get("threat_category", "")),
                "sent": normalize(row.get("sentiment", "")),
            }
    return rows


def load_gold(path: str) -> dict:
    rows = {}
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            pid = row["post_id"].strip()
            rows[pid] = {
                "cat": normalize(row["threat_category"]),
                "sent": normalize(row["sentiment"]),
            }
    return rows


def cohen_kappa(labels_a: list, labels_b: list) -> float:
    """Kappa de Cohen para dos listas de etiquetas alineadas."""
    n = len(labels_a)
    if n == 0:
        return float("nan")
    agreed = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    po = agreed / n
    ca = Counter(labels_a)
    cb = Counter(labels_b)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if pe == 1.0:
        return 1.0 if agreed == n else float("nan")
    return (po - pe) / (1 - pe)


def confusion_matrix(ref: list, pred: list, classes: list) -> dict:
    """Matriz de confusión: filas = pred (pipeline), columnas = ref (consenso)."""
    m = {c: {c2: 0 for c2 in classes} for c in classes}
    for r, p in zip(ref, pred):
        if r in classes and p in classes:
            m[p][r] += 1
    return m


def precision_recall_f1(m: dict, classes: list) -> dict:
    out = {}
    for c in classes:
        tp = m[c][c]
        pred_c = sum(m[c].values())
        ref_c = sum(m[c2][c] for c2 in classes)
        precision = tp / pred_c if pred_c else 0.0
        recall = tp / ref_c if ref_c else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        out[c] = {"precision": precision, "recall": recall, "f1": f1, "support": ref_c}
    n = sum(sum(m[c].values()) for c in classes)
    tp_sum = sum(m[c][c] for c in classes)
    macro_p = sum(out[c]["precision"] for c in classes) / len(classes)
    macro_r = sum(out[c]["recall"] for c in classes) / len(classes)
    macro_f1 = sum(out[c]["f1"] for c in classes) / len(classes)
    micro_p = tp_sum / n if n else 0.0
    micro_r = micro_p
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0
    return {"classes": out, "macro": {"precision": macro_p, "recall": macro_r, "f1": macro_f1},
            "micro": {"precision": micro_p, "recall": micro_r, "f1": micro_f1}}


def chi2_and_cramers(ref: list, pred: list, classes: list) -> tuple:
    """chi-cuadrado de asociación + V de Cramér."""
    m = confusion_matrix(ref, pred, classes)
    n = sum(sum(m[c].values()) for c in classes)
    if n == 0:
        return 0.0, 0.0
    row = {c: sum(m[c].values()) for c in classes}
    col = {c: sum(m[c2][c] for c2 in classes) for c in classes}
    chi2 = 0.0
    for c in classes:
        for c2 in classes:
            if row[c] and col[c2]:
                e = row[c] * col[c2] / n
                chi2 += (m[c][c2] - e) ** 2 / e
    k = min(len(classes) - 1, len(classes) - 1)
    v = (chi2 / (n * k)) ** 0.5 if k else 0.0
    return chi2, v


def permutation_pvalue(ref: list, pred: list, classes: list, perm: int, seed: int = 42) -> tuple:
    """p-valor por bootstrap de permutación sobre el chi-cuadrado observado."""
    chi2_obs, _ = chi2_and_cramers(ref, pred, classes)
    rng = random.Random(seed)
    count = 0
    for _ in range(perm):
        shuffled = list(pred)
        rng.shuffle(shuffled)
        chi2_perm, _ = chi2_and_cramers(ref, shuffled, classes)
        if chi2_perm >= chi2_obs:
            count += 1
    return chi2_obs, count / perm


def bootstrap_ci(pairs: list, metric: str, classes: list, b: int, seed: int = 42) -> tuple:
    """IC percentil al 95 % por bootstrap para kappa o F1 (micro/macro).

    pairs: lista de tuplas (ref, pred) — para kappa, (etiquetas_e1, e2) por
    ítem; para F1, (consenso, pipeline) por ítem.
    """
    rng = random.Random(seed)
    n = len(pairs)
    if n == 0:
        return (float("nan"), float("nan"))
    vals = []
    for _ in range(b):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        a = [p[0] for p in sample]
        c = [p[1] for p in sample]
        if metric == "kappa":
            vals.append(cohen_kappa(a, c))
        else:
            m = confusion_matrix(a, c, classes)
            prf = precision_recall_f1(m, classes)
            vals.append(prf["micro" if metric == "micro" else "macro"]["f1"])
    vals.sort()
    lo = vals[int(0.025 * b)]
    hi = vals[min(int(0.975 * b), b - 1)]
    return (lo, hi)


def kappa_label(a: float) -> str:
    """Interpretación convencional de Landis & Koch (1977)."""
    if a != a:  # NaN
        return "n/a"
    if a < 0.20:
        return "insuficiente"
    if a < 0.40:
        return "debil"
    if a < 0.60:
        return "moderado"
    if a < 0.80:
        return "sustancial"
    return "casi perfecto"


def write_report(out_path: str, sections: list, nota: str = None) -> None:
    lines = [
        "# Resultados ground truth (Fase 4)",
        "",
        "**Generado por:** `evaluar_ground_truth.py` (v3)",
        "",
    ]
    for block in sections:
        lines.extend(block)
        lines.append("")
    if nota:
        lines.extend(["## Nota metodológica", "", nota, ""])
    with open(out_path, "w", encoding="utf-8-sig") as fh:
        fh.write("\n".join(lines))


def table(headers: list, rows: list) -> list:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return lines


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Métricas de ground truth (Fase 4, v2)")
    parser.add_argument("--eval1", default="muestra200_eval1.csv")
    parser.add_argument("--eval2", default="muestra200_eval2.csv")
    parser.add_argument("--gold", default="muestra200_gold.csv")
    parser.add_argument("--resuelto", default=None, help="CSV con resolución de discrepancias")
    parser.add_argument("--perm", type=int, default=2000, help="Permutaciones para el p-valor")
    parser.add_argument("--bootstrap", type=int, default=2000, help="Remuestreos para los IC 95 %")
    parser.add_argument("--nota", default=None, help="Nota metodológica opcional (texto) agregada al final del reporte")
    parser.add_argument("--out", default="resultados_ground_truth.md")
    args = parser.parse_args(argv)

    e1 = load_eval(args.eval1)
    e2 = load_eval(args.eval2)
    gold = load_gold(args.gold)
    todos = set(e1) | set(e2) | set(gold)
    pids = sorted(set(e1) & set(e2) & set(gold))
    n = len(pids)

    # --- Etiquetas individuales crudas (PRE-adjudicacion)
    pre_cats_e1 = [e1[p]["cat"] for p in pids]
    pre_cats_e2 = [e2[p]["cat"] for p in pids]
    pre_sent_e1 = [e1[p]["sent"] for p in pids]
    pre_sent_e2 = [e2[p]["sent"] for p in pids]
    pre_cats_gold = [gold[p]["cat"] for p in pids]
    pre_sent_gold = [gold[p]["sent"] for p in pids]

    # --- Acuerdo inter-evaluador PRE-adjudicacion (con IC bootstrap)
    k_pre_cat = cohen_kappa(pre_cats_e1, pre_cats_e2)
    k_pre_sent = cohen_kappa(pre_sent_e1, pre_sent_e2)
    ci_kcat = bootstrap_ci(list(zip(pre_cats_e1, pre_cats_e2)), "kappa", CATEGORIAS, args.bootstrap)
    ci_ksent = bootstrap_ci(list(zip(pre_sent_e1, pre_sent_e2)), "kappa", SENTIMIENTOS, args.bootstrap)
    ndisc_pre_cat = sum(1 for a, b in zip(pre_cats_e1, pre_cats_e2) if a != b)
    ndisc_pre_sent = sum(1 for a, b in zip(pre_sent_e1, pre_sent_e2) if a != b)

    # --- Adjudicacion (post): pisa las etiquetas individuales con lo acordado
    n_resueltos = 0
    if args.resuelto:
        resuelto = load_eval(args.resuelto)
        invalidos = [
            (pid, resuelto[pid]["cat"], resuelto[pid]["sent"])
            for pid in pids
            if pid in resuelto
            and (resuelto[pid]["cat"] not in CATEGORIAS or resuelto[pid]["sent"] not in SENTIMIENTOS)
        ]
        if invalidos:
            for pid, cat, sent in invalidos:
                print(f"ERROR: etiqueta invalida/vacia en --resuelto para {pid}: cat='{cat}' sent='{sent}'")
            raise SystemExit("El archivo --resuelto debe tener threat_category y sentiment completos y validos en todas las filas")
        for pid in pids:
            if pid in resuelto:
                e1[pid] = resuelto[pid]
                e2[pid] = resuelto[pid]
                n_resueltos += 1

    cats_e1 = [e1[p]["cat"] for p in pids]
    cats_e2 = [e2[p]["cat"] for p in pids]
    cats_gold = [gold[p]["cat"] for p in pids]
    sent_e1 = [e1[p]["sent"] for p in pids]
    sent_e2 = [e2[p]["sent"] for p in pids]
    sent_gold = [gold[p]["sent"] for p in pids]

    sections = []

    # --- Descriptivo
    sections.append([
        f"## 1. Muestra analizada",
        "",
        f"- Ítems comparables: **{n}**",
        f"- Evaluador 1: {len(e1)} filas | Evaluador 2: {len(e2)} filas | Gold: {len(gold)} filas",
        f"- Excluidos por falta de etiqueta en algún archivo: {len(todos) - n}",
    ])

    # --- Acuerdo inter-evaluador PRE-adjudicacion (con IC bootstrap)
    sections.append([
        "## 2. Acuerdo inter-evaluador (humanos, pre-adjudicacion)",
        "",
        f"- Categoria de amenaza: **κ = {k_pre_cat:.3f}** ({kappa_label(k_pre_cat)}), IC 95 % [{ci_kcat[0]:.3f}, {ci_kcat[1]:.3f}]",
        f"- Sentimiento: **κ = {k_pre_sent:.3f}** ({kappa_label(k_pre_sent)}), IC 95 % [{ci_ksent[0]:.3f}, {ci_ksent[1]:.3f}]",
        "",
        f"Acuerdo bruto: categoria {n - ndisc_pre_cat}/{n} ({100.0 * (n - ndisc_pre_cat) / n:.1f} %) | sentimiento {n - ndisc_pre_sent}/{n} ({100.0 * (n - ndisc_pre_sent) / n:.1f} %).",
        "",
        f"Interpretación Landis & Koch (1977). IC percentil bootstrap ({args.bootstrap} remuestreos). Objetivo del estudio: κ > 0.70.",
        *(
            [f"Discrepancias resueltas por adjudicación conjunta: **{n_resueltos}** posts (el kappa de esta sección es el acuerdo ANTES de esa sesión)."]
            if args.resuelto
            else []
        ),
    ])

    # --- Evaluador vs pipeline (etiquetas individuales crudas)
    k_e1g_cat = cohen_kappa(pre_cats_e1, pre_cats_gold)
    k_e2g_cat = cohen_kappa(pre_cats_e2, pre_cats_gold)
    k_e1g_sent = cohen_kappa(pre_sent_e1, pre_sent_gold)
    k_e2g_sent = cohen_kappa(pre_sent_e2, pre_sent_gold)
    sections.append([
        "## 3. Acuerdo evaluador vs. pipeline",
        "",
        *table(
            ["Comparación", "Categoría (κ)", "Sentimiento (κ)"],
            [
                ["Evaluador 1 vs. pipeline", f"{k_e1g_cat:.3f}", f"{k_e1g_sent:.3f}"],
                ["Evaluador 2 vs. pipeline", f"{k_e2g_cat:.3f}", f"{k_e2g_sent:.3f}"],
            ],
        ),
    ])

    # --- Consenso (post-adjudicacion si hubo --resuelto)
    cons_cat = [cats_e1[i] if cats_e1[i] == cats_e2[i] else "DISCREPANCIA" for i in range(n)]
    cons_sent = [sent_e1[i] if sent_e1[i] == sent_e2[i] else "DISCREPANCIA" for i in range(n)]
    ndisc_cat = sum(1 for c in cons_cat if c == "DISCREPANCIA")
    ndisc_sent = sum(1 for c in cons_sent if c == "DISCREPANCIA")
    consenso_linea = (
        f"Resueltas por adjudicación conjunta: {n_resueltos} | sin resolver: {ndisc_cat + ndisc_sent}"
        if args.resuelto
        else "Sin sesión de adjudicación (correr con --resuelto para resolverlas)."
    )
    sections.append([
        "## 4. Consenso humano y discrepancias",
        "",
        f"- Ítems con consenso en categoría: **{n - ndisc_cat} / {n}** ({100.0 * (n - ndisc_cat) / n:.1f}%)",
        f"- Ítems con consenso en sentimiento: **{n - ndisc_sent} / {n}** ({100.0 * (n - ndisc_sent) / n:.1f}%)",
        f"- Discrepancias de categoría: **{ndisc_cat}** | de sentimiento: **{ndisc_sent}**",
        f"- Pre-adjudicación el consenso era: categoría {n - ndisc_pre_cat}/{n} | sentimiento {n - ndisc_pre_sent}/{n}. {consenso_linea}",
        "",
        "Los ítems con discrepancia se excluyen del análisis de desempeño (sección 5) salvo que se resuelvan con `--resuelto`.",
    ])

    # --- Desempeño del pipeline vs consenso (con IC bootstrap)
    for nombre, classes, cons, gold_list in [
        ("categoría de amenaza", CATEGORIAS, cons_cat, cats_gold),
        ("sentimiento", SENTIMIENTOS, cons_sent, sent_gold),
    ]:
        idx = [i for i in range(n) if cons[i] != "DISCREPANCIA"]
        ref = [cons[i] for i in idx]           # consenso humano (referencia)
        pred = [gold_list[i] for i in idx]     # pipeline (predicción)
        m = confusion_matrix(ref, pred, classes)
        prf = precision_recall_f1(m, classes)
        chi2, cramers = chi2_and_cramers(ref, pred, classes)
        chi2_obs, pval = permutation_pvalue(ref, pred, classes, args.perm)
        ci_micro = bootstrap_ci(list(zip(ref, pred)), "micro", classes, args.bootstrap)
        ci_macro = bootstrap_ci(list(zip(ref, pred)), "macro", classes, args.bootstrap)
        rows = [
            [c, f"{prf['classes'][c]['precision']:.3f}", f"{prf['classes'][c]['recall']:.3f}",
             f"{prf['classes'][c]['f1']:.3f}", prf["classes"][c]["support"]]
            for c in classes
        ]
        rows.append(["**Macro**", f"{prf['macro']['precision']:.3f}", f"{prf['macro']['recall']:.3f}",
                     f"{prf['macro']['f1']:.3f}", sum(prf["classes"][c]["support"] for c in classes)])
        rows.append(["**Micro**", f"{prf['micro']['precision']:.3f}", f"{prf['micro']['recall']:.3f}",
                     f"{prf['micro']['f1']:.3f}", sum(prf["classes"][c]["support"] for c in classes)])
        sections.append([
            f"## 5.{'a' if nombre == 'categoría de amenaza' else 'b'}. Desempeño del pipeline vs. consenso humano — {nombre}",
            "",
            f"Ítems considerados: **{len(ref)}** (consenso humano).",
            "",
            *table(["Clase", "Precisión", "Exhaustividad", "F1", "Soporte"], rows),
            "",
            f"- F1 micro IC 95 %: [{ci_micro[0]:.3f}, {ci_micro[1]:.3f}] | F1 macro IC 95 %: [{ci_macro[0]:.3f}, {ci_macro[1]:.3f}]",
            f"- χ² = {chi2_obs:.2f}, **p = {pval:.4f}** ({args.perm} permutaciones)",
            f"- **V de Cramér = {cramers:.3f}** (tamaño de efecto)",
            "",
            "**Matriz de confusión** (filas = pipeline, columnas = consenso humano):",
            "",
            *table([""] + classes, [[c] + [m[c][c2] for c2 in classes] for c in classes]),
        ])

    write_report(args.out, sections, args.nota)
    print(f"Reporte generado: {args.out}")
    print(f"  Kappa categoría (E1 vs E2, pre-adjudicación): {k_pre_cat:.3f} IC95 [{ci_kcat[0]:.3f}, {ci_kcat[1]:.3f}]")
    print(f"  Kappa sentimiento (E1 vs E2, pre-adjudicación): {k_pre_sent:.3f} IC95 [{ci_ksent[0]:.3f}, {ci_ksent[1]:.3f}]")
    print(f"  Discrepancias pre-adjudicación: categoría {ndisc_pre_cat} | sentimiento {ndisc_pre_sent} | resueltas: {n_resueltos}")


if __name__ == "__main__":
    main()
