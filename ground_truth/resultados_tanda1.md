# Resultados ground truth (Fase 4)

**Generado por:** `evaluar_ground_truth.py` (v3)

## 1. Muestra analizada

- Ítems comparables: **53**
- Evaluador 1: 53 filas | Evaluador 2: 53 filas | Gold: 53 filas
- Excluidos por falta de etiqueta en algún archivo: 0

## 2. Acuerdo inter-evaluador (humanos, pre-adjudicacion)

- Categoria de amenaza: **κ = 0.794** (sustancial), IC 95 % [0.652, 0.920]
- Sentimiento: **κ = 0.798** (sustancial), IC 95 % [0.516, 1.000]

Acuerdo bruto: categoria 45/53 (84.9 %) | sentimiento 50/53 (94.3 %).

Interpretación Landis & Koch (1977). IC percentil bootstrap (2000 remuestreos). Objetivo del estudio: κ > 0.70.
Discrepancias resueltas por adjudicación conjunta: **10** posts (el kappa de esta sección es el acuerdo ANTES de esa sesión).

## 3. Acuerdo evaluador vs. pipeline

| Comparación | Categoría (κ) | Sentimiento (κ) |
|---|---|---|
| Evaluador 1 vs. pipeline | 0.240 | 0.000 |
| Evaluador 2 vs. pipeline | 0.207 | -0.018 |

## 4. Consenso humano y discrepancias

- Ítems con consenso en categoría: **53 / 53** (100.0%)
- Ítems con consenso en sentimiento: **53 / 53** (100.0%)
- Discrepancias de categoría: **0** | de sentimiento: **0**
- Pre-adjudicación el consenso era: categoría 45/53 | sentimiento 50/53. Resueltas por adjudicación conjunta: 10 | sin resolver: 0

Los ítems con discrepancia se excluyen del análisis de desempeño (sección 5) salvo que se resuelvan con `--resuelto`.

## 5.a. Desempeño del pipeline vs. consenso humano — categoría de amenaza

Ítems considerados: **53** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| no_clasificado | 0.276 | 0.800 | 0.410 | 10 |
| vulnerabilidad | 0.538 | 0.333 | 0.412 | 21 |
| malware | 1.000 | 0.400 | 0.571 | 10 |
| phishing | 1.000 | 1.000 | 1.000 | 1 |
| ransomware | 1.000 | 1.000 | 1.000 | 1 |
| otro | 0.000 | 0.000 | 0.000 | 10 |
| **Macro** | 0.636 | 0.589 | 0.566 | 53 |
| **Micro** | 0.396 | 0.396 | 0.396 | 53 |

- F1 micro IC 95 %: [0.264, 0.528] | F1 macro IC 95 %: [0.196, 0.622]
- χ² = 134.31, **p = 0.0000** (2000 permutaciones)
- **V de Cramér = 0.712** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | no_clasificado | vulnerabilidad | malware | phishing | ransomware | otro |
|---|---|---|---|---|---|---|
| no_clasificado | 8 | 9 | 5 | 0 | 0 | 7 |
| vulnerabilidad | 2 | 7 | 1 | 0 | 0 | 3 |
| malware | 0 | 0 | 4 | 0 | 0 | 0 |
| phishing | 0 | 0 | 0 | 1 | 0 | 0 |
| ransomware | 0 | 0 | 0 | 0 | 1 | 0 |
| otro | 0 | 5 | 0 | 0 | 0 | 0 |

## 5.b. Desempeño del pipeline vs. consenso humano — sentimiento

Ítems considerados: **53** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| positivo | 0.100 | 0.667 | 0.174 | 3 |
| negativo | 0.105 | 0.333 | 0.160 | 6 |
| neutral | 0.857 | 0.273 | 0.414 | 44 |
| **Macro** | 0.354 | 0.424 | 0.249 | 53 |
| **Micro** | 0.302 | 0.302 | 0.302 | 53 |

- F1 micro IC 95 %: [0.189, 0.415] | F1 macro IC 95 %: [0.141, 0.359]
- χ² = 2.52, **p = 0.6835** (2000 permutaciones)
- **V de Cramér = 0.154** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | positivo | negativo | neutral |
|---|---|---|---|
| positivo | 2 | 3 | 15 |
| negativo | 0 | 2 | 17 |
| neutral | 1 | 1 | 12 |

## Nota metodológica

Etiquetado individual e independiente por dos evaluadores humanos (E1: M. Scopel; E2: G. Fracchia), sin asistencia de IA, sin acceso a las etiquetas del pipeline. Registro completo de sesiones con timestamps anclados a archivo: ground_truth/registro_sesiones.md. Discrepancias (10/53) resueltas en sesion conjunta de adjudicacion (3-sep-2026). Muestra tanda 1 por censo: 53 posts no-piloto del corpus al 3-sep-2026 (seed de orden: tesis-f4-2026b). Etiquetas del pipeline generadas por el sistema en produccion (n8n + RSS Reddit + keywords + VADER + PostgreSQL).
