# -*- coding: utf-8 -*-
"""Recalculo del clasificador CORREGIDO (plural en -ies, Listado 2, §4.4.2)
sobre el censo expandido completo (639 = 113 + 526), frente al consenso
humano ya adjudicado (eval1_639.csv + resuelto_639.csv, con el mismo
criterio de evaluar_ground_truth.py).

Por que lo corre Maxi y no queda como esta: la version de abajo es una
REIMPLEMENTACION del fix a partir del script ya existente en el repo
(recalc_c06_n113.py), aplicada directamente sobre el texto crudo de los
639 posts -- no es una corrida real del pipeline de produccion. Como
control, la version "ORIGINAL" (sin el fix) de este mismo script da F1
micro = 0,556 sobre el texto, mientras que el pipeline real que genero
muestra_f4_t2_gold.csv / censo_gold_pipeline_113.csv dio F1 micro = 0,552
(los dos oficiales, ya en la tesis) -- una diferencia de ~4 posts sobre
639, probablemente por algun detalle de implementacion entre esta
reimplementacion y el codigo real de osint_pipeline.py.

Lo que se necesita: correr la funcion CLASSIFY_THREAT real (la que
efectivamente tiene aplicado el fix de -ies en el repo de produccion,
osint_pipeline.py) sobre el texto (title+content) de los 639 posts del
censo expandido, y comparar contra el consenso humano adjudicado. Si
reemplazas la funcion `classify_threat_FIX` de abajo por un import directo
de la real (`from osint_pipeline import classify_threat`), este script
ya hace el resto: arma el texto de los 639, corre la clasificacion y
calcula F1/matriz de confusion/IC bootstrap exactamente con el mismo
criterio que las Tablas 5.5 a 5.7 de la tesis.

Archivos que necesitas (te los paso junto con este script):
  - posts_dataset_113_completo.csv   (texto de los 113 del censo original)
  - eval2_gonzalo_final.csv          (texto + labels de los 526 de tanda 2)
  - eval1_639.csv, eval2_639.csv, resuelto_639.csv  (para reconstruir el
    consenso humano adjudicado de los 639, igual que evaluar_ground_truth.py)

Uso:
    python3 recalc_clasificador_639.py
"""
import csv
import random
import re

from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support

LABELS = ["no_clasificado", "vulnerabilidad", "malware", "phishing", "ransomware", "otro"]

# -----------------------------------------------------------------------
# REEMPLAZAR ESTO por la funcion real del repo (osint_pipeline.py), que ya
# tiene aplicado el fix de -ies. Lo de abajo es solo una reconstruccion a
# partir de recalc_c06_n113.py, mantenida como fallback si no se encuentra
# el import real.
# -----------------------------------------------------------------------
try:
    from osint_pipeline import classify_threat as classify_threat_FIX  # type: ignore
    print("Usando la funcion real del repo (osint_pipeline.classify_threat).")
except ImportError:
    print("AVISO: no se encontro osint_pipeline.py en este directorio -- "
          "usando la reconstruccion del fix a partir de recalc_c06_n113.py. "
          "Si tenes el repo clonado aca al lado, corre este script desde esa "
          "carpeta para que use la funcion real.")

    THREAT_KEYWORDS = {
        "vulnerabilidad": ["vulnerability", "cve", "exploit", "patch", "zero day", "0day",
                            "0 day", "disclosure", "advisory", "flaw", "bug"],
        "malware": ["malware", "trojan", "backdoor", "rootkit", "spyware", "botnet",
                    "keylogger", "dropper", "payload"],
        "phishing": ["phishing", "spear phishing", "credential", "fake login",
                     "social engineering", "lure", "impersonation"],
        "ransomware": ["ransomware", "lockbit", "blackcat", "alphv", "decryptor"],
        "otro": ["ddos", "brute force", "injection", "xss", "sqli",
                 "privilege escalation", "lateral movement"],
    }
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


def load_text():
    text_by_pid = {}
    with open("posts_dataset_113_completo.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            text_by_pid[r["post_id"]] = (r["title"] or "") + " " + (r["content"] or "")
    with open("eval2_gonzalo_final.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            text_by_pid[r["post_id"]] = (r["title"] or "") + " " + (r["content"] or "")
    return text_by_pid


def load_consensus():
    def load_eval(path):
        with open(path, encoding="utf-8-sig") as f:
            return {r["post_id"]: r["threat_category"].strip() for r in csv.DictReader(f)}

    e1 = load_eval("eval1_639.csv")
    e2 = load_eval("eval2_639.csv")
    with open("resuelto_639.csv", encoding="utf-8-sig") as f:
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
    text_by_pid = load_text()
    consensus = load_consensus()
    assert set(consensus) == set(text_by_pid), (
        len(set(consensus) - set(text_by_pid)), len(set(text_by_pid) - set(consensus))
    )
    ids = sorted(consensus)
    y_true = [consensus[pid] for pid in ids]
    y_pred = [classify_threat_FIX(text_by_pid[pid]) for pid in ids]

    p, r, f1, sup = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, zero_division=0)
    micro = f1_score(y_true, y_pred, average="micro", labels=LABELS)
    macro = f1_score(y_true, y_pred, average="macro", labels=LABELS)
    print(f"\n--- CORREGIDO (-ies) -- N={len(y_true)} F1 micro={micro:.3f} F1 macro={macro:.3f} ---")
    for lab, pp, rr, ff, ss in zip(LABELS, p, r, f1, sup):
        print(f"  {lab:16s} P={pp:.3f} R={rr:.3f} F1={ff:.3f} n={ss}")

    cm = confusion_matrix(y_pred, y_true, labels=LABELS)
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
        boot_micro.append(f1_score(yt, yp, average="micro", labels=LABELS))
        boot_macro.append(f1_score(yt, yp, average="macro", labels=LABELS))
    boot_micro.sort()
    boot_macro.sort()
    print(f"\nF1 micro IC95%: [{boot_micro[50]:.3f}, {boot_micro[1950]:.3f}]")
    print(f"F1 macro IC95%: [{boot_macro[50]:.3f}, {boot_macro[1950]:.3f}]")


if __name__ == "__main__":
    main()
