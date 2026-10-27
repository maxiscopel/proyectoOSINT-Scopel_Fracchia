# Resultados ground truth (Fase 4)

**Generado por:** `evaluar_ground_truth.py` (v2)

## 1. Muestra analizada

- Ítems comparables: **639**
- Evaluador 1: 639 filas | Evaluador 2: 639 filas | Gold: 639 filas
- Excluidos por falta de etiqueta en algún archivo: 0

## 2. Acuerdo inter-evaluador (humanos, pre-adjudicación)

- Categoría de amenaza: **κ = 0.852** (casi perfecto), IC 95 % [0.820, 0.881]
- Sentimiento: **κ = 0.498** (moderado), IC 95 % [0.411, 0.577]

Acuerdo bruto: categoría 562/639 (87.9 %) | sentimiento 537/639 (84.0 %).

Interpretación Landis & Koch (1977). IC percentil bootstrap (2000 remuestreos). Objetivo del estudio: κ > 0.70.
El kappa de esta sección es el acuerdo ANTES de la adjudicación conjunta de discrepancias.

## 3. Acuerdo evaluador vs. pipeline

| Comparación | Categoría (κ) | Sentimiento (κ) |
|---|---|---|
| Evaluador 1 vs. pipeline | 0.444 | 0.043 |
| Evaluador 2 vs. pipeline | 0.444 | 0.043 |

## 4. Consenso humano y discrepancias

- Ítems con consenso en categoría: **639 / 639** (100.0%)
- Ítems con consenso en sentimiento: **639 / 639** (100.0%)
- Discrepancias de categoría: **0** | de sentimiento: **0**
- Pre-adjudicación el consenso era: categoría 562/639 | sentimiento 537/639. Resueltas por adjudicación conjunta: 169 | sin resolver (categoría): 0 | sin resolver (sentimiento): 0

Los ítems con discrepancia se excluyen del análisis de desempeño (sección 5) salvo que se resuelvan con `--resuelto`.

## 5.a. Desempeño del pipeline vs. consenso humano — categoría de amenaza

Ítems considerados: **639** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| no_clasificado | 0.469 | 0.628 | 0.537 | 145 |
| vulnerabilidad | 0.625 | 0.579 | 0.601 | 95 |
| malware | 0.814 | 0.414 | 0.549 | 116 |
| phishing | 0.541 | 0.875 | 0.668 | 144 |
| ransomware | 0.589 | 0.892 | 0.710 | 37 |
| otro | 0.000 | 0.000 | 0.000 | 102 |
| **Macro** | 0.506 | 0.565 | 0.511 | 639 |
| **Micro** | 0.552 | 0.552 | 0.552 | 639 |

- F1 micro IC 95 %: [0.513, 0.592] | F1 macro IC 95 %: [0.476, 0.543]
- χ² = 891.48, **p = 0.0000** (2000 permutaciones)
- **V de Cramér = 0.528** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | no_clasificado | vulnerabilidad | malware | phishing | ransomware | otro |
|---|---|---|---|---|---|---|
| no_clasificado | 91 | 30 | 31 | 17 | 0 | 25 |
| vulnerabilidad | 13 | 55 | 7 | 0 | 0 | 13 |
| malware | 7 | 1 | 48 | 1 | 1 | 1 |
| phishing | 22 | 3 | 27 | 126 | 3 | 52 |
| ransomware | 10 | 1 | 1 | 0 | 33 | 11 |
| otro | 2 | 5 | 2 | 0 | 0 | 0 |

## 5.b. Desempeño del pipeline vs. consenso humano — sentimiento

Ítems considerados: **639** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| positivo | 0.044 | 0.556 | 0.082 | 18 |
| negativo | 0.194 | 0.644 | 0.298 | 104 |
| neutral | 0.925 | 0.120 | 0.212 | 517 |
| **Macro** | 0.388 | 0.440 | 0.197 | 639 |
| **Micro** | 0.218 | 0.218 | 0.218 | 639 |

- F1 micro IC 95 %: [0.185, 0.250] | F1 macro IC 95 %: [0.166, 0.230]
- χ² = 12.83, **p = 0.0090** (2000 permutaciones)
- **V de Cramér = 0.100** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | positivo | negativo | neutral |
|---|---|---|---|
| positivo | 10 | 34 | 183 |
| negativo | 6 | 67 | 272 |
| neutral | 2 | 3 | 62 |
