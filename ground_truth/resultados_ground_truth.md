# Resultados ground truth (Fase 4)

**Generado por:** `evaluar_ground_truth.py`

## 1. Muestra analizada

- Ítems comparables: **60**
- Evaluador 1: 60 filas | Evaluador 2: 60 filas | Gold: 60 filas
- Excluidos por falta de etiqueta en algún archivo: 0

## 2. Acuerdo inter-evaluador (humanos)

- Categoría de amenaza: **κ = 0.937** (casi perfecto)
- Sentimiento: **κ = 0.310** (debil)

Interpretación Landis & Koch (1977). Objetivo del estudio: κ > 0.70.

## 3. Acuerdo evaluador vs. pipeline

| Comparación | Categoría (κ) | Sentimiento (κ) |
|---|---|---|
| Evaluador 1 vs. pipeline | 0.393 | -0.014 |
| Evaluador 2 vs. pipeline | 0.364 | 0.089 |

## 4. Consenso humano y discrepancias

- Ítems con consenso en categoría: **57 / 60** (95.0%)
- Ítems con consenso en sentimiento: **40 / 60** (66.7%)
- Discrepancias de categoría: **3** | de sentimiento: **20**

Los ítems con discrepancia se excluyen del análisis de desempeño (sección 5) salvo que se resuelvan con `--resuelto`.

## 5.a. Desempeño del pipeline vs. consenso humano — categoría de amenaza

Ítems considerados: **57** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| no_clasificado | 0.438 | 0.875 | 0.583 | 16 |
| vulnerabilidad | 0.500 | 0.444 | 0.471 | 9 |
| malware | 1.000 | 0.400 | 0.571 | 15 |
| phishing | 0.375 | 0.750 | 0.500 | 4 |
| ransomware | 1.000 | 1.000 | 1.000 | 3 |
| otro | 0.000 | 0.000 | 0.000 | 10 |
| **Macro** | 0.552 | 0.578 | 0.521 | 57 |
| **Micro** | 0.526 | 0.526 | 0.526 | 57 |

- χ² = 103.35, **p = 0.0000** (2000 permutaciones)
- **V de Cramér = 0.602** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | no_clasificado | vulnerabilidad | malware | phishing | ransomware | otro |
|---|---|---|---|---|---|---|
| no_clasificado | 14 | 5 | 8 | 1 | 0 | 4 |
| vulnerabilidad | 1 | 4 | 0 | 0 | 0 | 3 |
| malware | 0 | 0 | 6 | 0 | 0 | 0 |
| phishing | 1 | 0 | 1 | 3 | 0 | 3 |
| ransomware | 0 | 0 | 0 | 0 | 3 | 0 |
| otro | 0 | 0 | 0 | 0 | 0 | 0 |

## 5.b. Desempeño del pipeline vs. consenso humano — sentimiento

Ítems considerados: **40** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| positivo | 0.045 | 0.500 | 0.083 | 2 |
| negativo | 0.154 | 0.333 | 0.211 | 6 |
| neutral | 0.800 | 0.125 | 0.216 | 32 |
| **Macro** | 0.333 | 0.319 | 0.170 | 40 |
| **Micro** | 0.175 | 0.175 | 0.175 | 40 |

- χ² = 3.86, **p = 0.4815** (2000 permutaciones)
- **V de Cramér = 0.220** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | positivo | negativo | neutral |
|---|---|---|---|
| positivo | 1 | 4 | 17 |
| negativo | 0 | 2 | 11 |
| neutral | 1 | 0 | 4 |

## Nota metodológica

El Evaluador 2 fue asistido por un modelo de lenguaje con clasificación ciega (sin consultar el resultado del pipeline ni el etiquetado del Evaluador 1). El acuerdo inter-evaluador (kappa) mide el acuerdo humano vs. asistido por IA, no el acuerdo entre dos humanos.
