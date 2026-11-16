# -*- coding: utf-8 -*-
"""Verificaciones exploratorias del Anexo F sobre las 102 publicaciones del corte.

Reproduce, sobre el mismo conjunto de 102 publicaciones y contra el consenso
humano del censo (censo_gold_humano_113.csv):

  1. Sentimiento: VADER (title + raw_content, umbrales +-0,05 del Listado 3) y la
     linea de base trivial "todo neutral".
  2. Categoria de amenaza: clasificador por palabras clave en su version original
     (sin plurales) y en su version corregida (plurales -s/-es y -ies, la funcion
     real `classify_threat` de osint_pipeline.py), mas las etiquetas guardadas
     por el pipeline en produccion (censo_gold_pipeline_113.csv).
  3. Categoria de amenaza: TF-IDF + regresion logistica (validacion cruzada
     estratificada de 5 pliegues, semilla 42) sobre esas mismas 102 publicaciones.
     Requiere scikit-learn; si no esta instalado, se informa y se omite.

Las 102 publicaciones son las del censo de 113 con created_utc anterior al
28/8/2026 (se excluyen las 11 de la tanda 1 posteriores al corte de datos del
capitulo 5: ver §5.6).

Entradas (publicadas en este directorio):
  posts_dataset_113_completo.csv, censo_gold_humano_113.csv,
  censo_gold_pipeline_113.csv

Uso (desde cualquier directorio):
    python ground_truth/exploratorio_anexo_f.py
Dependencias: nltk con el lexicon de VADER (ya en requirements.txt); opcional
scikit-learn solo para el punto 3.
"""
import csv
import os
import re
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # raiz del repo: osint_pipeline.py

CUTOFF = "2026-08-28"  # created_utc < CUTOFF  ->  102 publicaciones
CAT_LABELS = ["no_clasificado", "vulnerabilidad", "malware", "phishing", "ransomware", "otro"]
SENT_LABELS = ["negativo", "neutral", "positivo"]
SEED = 42


# ---------------------------------------------------------------- metricas
def f1_micro(y_true, y_pred):
    # Con todas las clases incluidas, el F1 micro coincide con la exactitud.
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)


def f1_macro(y_true, y_pred, labels):
    total = 0.0
    for lab in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        total += 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    return total / len(labels)


def fmt(x):
    return f"{x:.3f}".replace(".", ",")


def report(nombre, y_true, y_pred, labels):
    print(f"  {nombre:48s} F1 micro = {fmt(f1_micro(y_true, y_pred))}   "
          f"F1 macro = {fmt(f1_macro(y_true, y_pred, labels))}")


# ----------------------------------------------------------------- datos
def read_csv(name):
    with open(os.path.join(HERE, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_102():
    posts = [r for r in read_csv("posts_dataset_113_completo.csv") if r["created_utc"] < CUTOFF]
    gold = {r["post_id"]: r for r in read_csv("censo_gold_humano_113.csv")}
    prod = {r["post_id"]: r for r in read_csv("censo_gold_pipeline_113.csv")}
    return posts, gold, prod


def _pipeline():
    """Importa osint_pipeline.py; si falta `feedparser` (no se usa para clasificar)
    se registra un sustituto vacio para poder reutilizar la funcion real."""
    try:
        import osint_pipeline  # type: ignore
    except ImportError:
        import types
        sys.modules.setdefault("feedparser", types.ModuleType("feedparser"))
        import osint_pipeline  # type: ignore
    return osint_pipeline


# --------------------------------------------- clasificador original (sin plurales)
def _build_original():
    """Version original del clasificador (antes del commit 3ba6127): palabra
    completa, sin plurales y sensible a mayusculas (se aplica sobre texto en minusculas)."""
    pl = _pipeline()
    THREAT_KEYWORDS, TIEBREAK_ORDER = pl.THREAT_KEYWORDS, pl.TIEBREAK_ORDER

    regexes = {
        cat: [re.compile(r"(?<![a-z0-9])" + r"\s+".join(re.escape(p) for p in t.split())
                         + r"(?![a-z0-9])") for t in terms]
        for cat, terms in THREAT_KEYWORDS.items()
    }

    def classify(text):
        lowered = text.lower()
        counts = {c: sum(len(rx.findall(lowered)) for rx in rs) for c, rs in regexes.items()}
        best = TIEBREAK_ORDER[0]
        for cat in TIEBREAK_ORDER:
            if counts[cat] > counts[best]:
                best = cat
        return best if counts[best] else "no_clasificado"

    return classify


# ------------------------------------------------------------------ VADER
def vader_labels(posts):
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    try:
        sia = SentimentIntensityAnalyzer()
    except LookupError:
        import nltk
        nltk.download("vader_lexicon", quiet=True)
        sia = SentimentIntensityAnalyzer()
    out = []
    for p in posts:
        text = (p["title"] or "") + " " + (p["raw_content"] or "")
        c = sia.polarity_scores(text)["compound"]
        out.append("positivo" if c >= 0.05 else "negativo" if c <= -0.05 else "neutral")
    return out


# --------------------------------------------------------------------- ML
def ml_models(posts, y_true):
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import (LeaveOneOut, StratifiedKFold,
                                             cross_val_predict)
        from sklearn.pipeline import make_pipeline
        from sklearn.svm import LinearSVC
    except ImportError:
        print("  (scikit-learn no instalado: se omite la comparacion con ML; "
              "instalar con `pip install scikit-learn`)")
        return
    import sklearn
    print(f"  scikit-learn {sklearn.__version__}, semilla {SEED}")
    X = [(p["title"] or "") + " " + (p["content"] or "") for p in posts]
    y = np.array(y_true)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    modelos = [
        ("TF-IDF + regresion logistica, VC 5 pliegues",
         make_pipeline(TfidfVectorizer(lowercase=True), LogisticRegression(max_iter=1000)), skf),
        ("TF-IDF + LinearSVC, VC 5 pliegues",
         make_pipeline(TfidfVectorizer(lowercase=True), LinearSVC()), skf),
        ("TF-IDF + regresion logistica, leave-one-out",
         make_pipeline(TfidfVectorizer(lowercase=True), LogisticRegression(max_iter=1000)),
         LeaveOneOut()),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # clases con < 5 casos en StratifiedKFold
        for nombre, model, cv in modelos:
            pred = list(cross_val_predict(model, X, y, cv=cv))
            report(nombre, y_true, pred, CAT_LABELS)
            if nombre.startswith("TF-IDF + regresion logistica, VC"):
                for lab in ("phishing", "ransomware"):
                    tp = sum(1 for t, p in zip(y_true, pred) if t == lab and p == lab)
                    n = sum(1 for t in y_true if t == lab)
                    print(f"      {lab}: {tp} de {n} recuperados")


def main():
    posts, gold, prod = load_102()
    ids = [p["post_id"] for p in posts]
    assert len(ids) == 102 and all(i in gold and i in prod for i in ids), len(ids)
    print(f"Publicaciones del corte: N = {len(ids)} (created_utc < {CUTOFF}); "
          f"consenso humano de censo_gold_humano_113.csv\n")

    # 1. Sentimiento
    s_true = [gold[i]["sentiment"] for i in ids]
    print("1) Sentimiento (consenso humano)")
    report("VADER (title + raw_content, umbral +-0,05)", s_true, vader_labels(posts), SENT_LABELS)
    report("Etiquetas guardadas por el pipeline", s_true, [prod[i]["sentiment"] for i in ids],
           SENT_LABELS)
    report('Linea de base "todo neutral"', s_true, ["neutral"] * len(ids), SENT_LABELS)

    # 2. Categoria por palabras clave
    classify_threat = _pipeline().classify_threat  # clasificador corregido (real)
    original = _build_original()
    texts = [(p["title"] or "") + " " + (p["content"] or "") for p in posts]
    c_true = [gold[i]["threat_category"] for i in ids]
    print("\n2) Categoria de amenaza por palabras clave (consenso humano)")
    report("Original (sin plurales)", c_true, [original(t) for t in texts], CAT_LABELS)
    report("Corregido (plurales -s/-es/-ies, funcion real)", c_true,
           [classify_threat(t) for t in texts], CAT_LABELS)
    report("Etiquetas guardadas por el pipeline (produccion)", c_true,
           [prod[i]["threat_category"] for i in ids], CAT_LABELS)
    dist = {lab: c_true.count(lab) for lab in CAT_LABELS}
    print("  Distribucion del consenso:", dist)

    # 3. ML
    print("\n3) Categoria de amenaza por aprendizaje automatico (mismas 102 publicaciones)")
    ml_models(posts, c_true)


if __name__ == "__main__":
    main()
