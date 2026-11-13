# -*- coding: utf-8 -*-
"""Recalculo del clasificador CORREGIDO (plurales -s/-es y -ies, Listado 2,
§4.4.2) sobre el censo expandido completo (639 = 113 + 526), frente al
consenso humano ya adjudicado (eval1_639.csv + resuelto_639.csv, con el mismo
criterio de evaluar_ground_truth.py).

El script ejecuta la funcion real `classify_threat` de `osint_pipeline.py`
(raiz del repositorio) sobre el texto (titulo + contenido) de los 639 posts.
Si ese modulo no pudiera importarse (por ejemplo, por falta de `feedparser`),
usa una copia fiel del diccionario de 38 terminos y de la regla de coincidencia
de palabra completa del clasificador.

Es la reclasificacion sobre texto exportado: no es una corrida del pipeline de
produccion, por lo que puede diferir en unos pocos posts de las etiquetas
guardadas en `censo_gold_pipeline_113.csv` y `muestra_f4_t2_gold.csv`
(F1 micro 0,552 con las etiquetas en vivo).

Archivos de entrada (todos publicados en este directorio):
  - posts_dataset_113_completo.csv           (texto de los 113 del censo)
  - posts_dataset_tanda2_1956_completo.csv   (texto de los 1.956 de tanda 2,
                                              de los que se usan los 526 etiquetados)
  - eval1_639.csv, eval2_639.csv, resuelto_639.csv  (consenso humano adjudicado)

Uso (desde cualquier directorio; solo biblioteca estandar):
    python ground_truth/recalc_clasificador_639.py
"""
import csv
import os
import random
import re
import sys


LABELS = ["no_clasificado", "vulnerabilidad", "malware", "phishing", "ransomware", "otro"]

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # raiz del repo: osint_pipeline.py

try:
    from osint_pipeline import classify_threat as classify_threat_FIX  # type: ignore
    print("Usando la funcion real del repo (osint_pipeline.classify_threat).")
except ImportError:
    print("AVISO: no se pudo importar osint_pipeline.py; se usa la copia fiel "
          "del diccionario de 38 terminos y de la regla de palabra completa.")

    THREAT_KEYWORDS = {
        "vulnerabilidad": ["vulnerability", "cve", "exploit", "patch", "zero day", "0day",
                           "disclosure", "advisory", "flaw", "bug"],
        "malware": ["malware", "trojan", "backdoor", "rootkit", "spyware", "botnet",
                    "keylogger", "dropper", "payload"],
        "phishing": ["phishing", "spear phishing", "credential", "fake login",
                     "social engineering", "lure", "impersonation"],
        "ransomware": ["ransomware", "lockbit", "blackcat", "alphv", "decryptor"],
        "otro": ["ddos", "brute force", "injection", "xss", "sqli",
                 "privilege escalation", "lateral movement"],
    }
    assert sum(len(v) for v in THREAT_KEYWORDS.values()) == 38
    TIEBREAK_ORDER = ("vulnerabilidad", "malware", "phishing", "ransomware", "otro")

    def _word_regex_fixed(term):
        words = term.split()
        last = words[-1]
        if last.endswith("y") and last[-2:-1] not in "aeiou":
            last_rx = re.escape(last[:-1]) + r"(?:y|ies)"
        else:
            last_rx = re.escape(last) + r"(?:e?s)?"
        core = r"\s+".join([re.escape(w) for w in words[:-1]] + [last_rx])
        return r"(?<![a-z0-9])" + core + r"(?![a-z0-9])"

    _REGEX_FIX = {cat: [re.compile(_word_regex_fixed(t), re.IGNORECASE) for t in terms]
                  for cat, terms in THREAT_KEYWORDS.items()}

    def classify_threat_FIX(text):
        lowered = text.lower()
        counts = {cat: sum(len(rx.findall(lowered)) for rx in rs) for cat, rs in _REGEX_FIX.items()}
        best = TIEBREAK_ORDER[0]
        for cat in TIEBREAK_ORDER:
            if counts[cat] > counts[best]:
                best = cat
        return best if counts[best] else "no_clasificado"


def per_class(y_true, y_pred):
    """Precision, exhaustividad, F1 y soporte por clase (0 si el denominador es 0)."""
    out = []
    for lab in LABELS:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        out.append((pr, rc, f1, tp + fn))
    return out


def f1_micro(y_true, y_pred):
    # Con todas las clases (incluida no_clasificado), el F1 micro es la exactitud.
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)


def f1_macro(y_true, y_pred):
    return sum(c[2] for c in per_class(y_true, y_pred)) / len(LABELS)


def confusion(y_pred, y_true):
    idx = {lab: i for i, lab in enumerate(LABELS)}
    cm = [[0] * len(LABELS) for _ in LABELS]
    for p, t in zip(y_pred, y_true):
        cm[idx[p]][idx[t]] += 1
    return cm


def _path(name):
    return os.path.join(HERE, name)


def load_text(wanted):
    """Texto (title + content) de los posts pedidos, desde los datasets publicados."""
    text_by_pid = {}
    for name in ("posts_dataset_113_completo.csv", "posts_dataset_tanda2_1956_completo.csv"):
        with open(_path(name), encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["post_id"] in wanted and r["post_id"] not in text_by_pid:
                    text_by_pid[r["post_id"]] = (r["title"] or "") + " " + (r["content"] or "")
    return text_by_pid


def load_consensus():
    def load_eval(path):
        with open(_path(path), encoding="utf-8-sig") as f:
            return {r["post_id"]: r["threat_category"].strip() for r in csv.DictReader(f)}

    e1 = load_eval("eval1_639.csv")
    e2 = load_eval("eval2_639.csv")
    with open(_path("resuelto_639.csv"), encoding="utf-8-sig") as f:
        resuelto = {r["post_id"]: r["threat_category"].strip() for r in csv.DictReader(f)}
    consensus = {}
    for pid in e1:
        if pid in resuelto:
            consensus[pid] = resuelto[pid]
        else:
            assert e1[pid] == e2[pid], f"{pid} sin consenso y sin resolucion"
            consensus[pid] = e1[pid]
    return consensus


def main():
    consensus = load_consensus()
    text_by_pid = load_text(set(consensus))
    assert set(consensus) == set(text_by_pid), (
        len(set(consensus) - set(text_by_pid)), len(set(text_by_pid) - set(consensus))
    )
    ids = sorted(consensus)
    y_true = [consensus[pid] for pid in ids]
    y_pred = [classify_threat_FIX(text_by_pid[pid]) for pid in ids]

    stats = per_class(y_true, y_pred)
    micro = f1_micro(y_true, y_pred)
    macro = f1_macro(y_true, y_pred)
    print(f"\n--- CORREGIDO (-ies) -- N={len(y_true)} F1 micro={micro:.3f} F1 macro={macro:.3f} ---")
    for lab, (pp, rr, ff, ss) in zip(LABELS, stats):
        print(f"  {lab:16s} P={pp:.3f} R={rr:.3f} F1={ff:.3f} n={ss}")

    cm = confusion(y_pred, y_true)
    print("\nMatriz de confusion (filas=pipeline, columnas=consenso humano):")
    print(" ", LABELS)
    for lab, row in zip(LABELS, cm):
        print(" ", lab, list(row))

    random.seed(42)
    n = len(y_true)
    idx = list(range(n))
    boot_micro, boot_macro = [], []
    for _ in range(2000):
        s = [random.choice(idx) for _ in range(n)]
        yt = [y_true[i] for i in s]
        yp = [y_pred[i] for i in s]
        boot_micro.append(f1_micro(yt, yp))
        boot_macro.append(f1_macro(yt, yp))
    boot_micro.sort()
    boot_macro.sort()
    print(f"\nF1 micro IC95%: [{boot_micro[50]:.3f}, {boot_micro[1950]:.3f}]")
    print(f"F1 macro IC95%: [{boot_macro[50]:.3f}, {boot_macro[1950]:.3f}]")


if __name__ == "__main__":
    main()
