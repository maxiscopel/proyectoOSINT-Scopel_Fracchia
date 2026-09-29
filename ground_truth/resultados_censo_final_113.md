# Resultados ground truth (Fase 4)

**Generado por:** `evaluar_ground_truth.py` (v3)

## 1. Muestra analizada

- Ítems comparables: **113**
- Evaluador 1: 113 filas | Evaluador 2: 113 filas | Gold: 113 filas
- Excluidos por falta de etiqueta en algún archivo: 0

## 2. Acuerdo inter-evaluador (humanos, pre-adjudicacion)

- Categoria de amenaza: **κ = 0.876** (casi perfecto), IC 95 % [0.798, 0.943]
- Sentimiento: **κ = 0.469** (moderado), IC 95 % [0.281, 0.655]

Acuerdo bruto: categoria 102/113 (90.3 %) | sentimiento 90/113 (79.6 %).

Interpretación Landis & Koch (1977). IC percentil bootstrap (2000 remuestreos). Objetivo del estudio: κ > 0.70.
Discrepancias resueltas por adjudicación conjunta: **32** posts (el kappa de esta sección es el acuerdo ANTES de esa sesión).

## 3. Acuerdo evaluador vs. pipeline

| Comparación | Categoría (κ) | Sentimiento (κ) |
|---|---|---|
| Evaluador 1 vs. pipeline | 0.330 | -0.010 |
| Evaluador 2 vs. pipeline | 0.300 | 0.060 |

## 4. Consenso humano y discrepancias

- Ítems con consenso en categoría: **113 / 113** (100.0%)
- Ítems con consenso en sentimiento: **113 / 113** (100.0%)
- Discrepancias de categoría: **0** | de sentimiento: **0**
- Pre-adjudicación el consenso era: categoría 102/113 | sentimiento 90/113. Resueltas por adjudicación conjunta: 32 | sin resolver: 0

Los ítems con discrepancia se excluyen del análisis de desempeño (sección 5) salvo que se resuelvan con `--resuelto`.

## 5.a. Desempeño del pipeline vs. consenso humano — categoría de amenaza

Ítems considerados: **113** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| no_clasificado | 0.375 | 0.857 | 0.522 | 28 |
| vulnerabilidad | 0.524 | 0.367 | 0.431 | 30 |
| malware | 1.000 | 0.400 | 0.571 | 25 |
| phishing | 0.444 | 0.800 | 0.571 | 5 |
| ransomware | 1.000 | 1.000 | 1.000 | 4 |
| otro | 0.000 | 0.000 | 0.000 | 21 |
| **Macro** | 0.557 | 0.571 | 0.516 | 113 |
| **Micro** | 0.469 | 0.469 | 0.469 | 113 |

- F1 micro IC 95 %: [0.381, 0.558] | F1 macro IC 95 %: [0.403, 0.583]
- χ² = 215.67, **p = 0.0000** (2000 permutaciones)
- **V de Cramér = 0.618** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | no_clasificado | vulnerabilidad | malware | phishing | ransomware | otro |
|---|---|---|---|---|---|---|
| no_clasificado | 24 | 14 | 13 | 1 | 0 | 12 |
| vulnerabilidad | 3 | 11 | 1 | 0 | 0 | 6 |
| malware | 0 | 0 | 10 | 0 | 0 | 0 |
| phishing | 1 | 0 | 1 | 4 | 0 | 3 |
| ransomware | 0 | 0 | 0 | 0 | 4 | 0 |
| otro | 0 | 5 | 0 | 0 | 0 | 0 |

## 5.b. Desempeño del pipeline vs. consenso humano — sentimiento

Ítems considerados: **113** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| positivo | 0.065 | 0.600 | 0.118 | 5 |
| negativo | 0.089 | 0.308 | 0.138 | 13 |
| neutral | 0.864 | 0.200 | 0.325 | 95 |
| **Macro** | 0.339 | 0.369 | 0.193 | 113 |
| **Micro** | 0.230 | 0.230 | 0.230 | 113 |

- F1 micro IC 95 %: [0.159, 0.310] | F1 macro IC 95 %: [0.125, 0.265]
- χ² = 6.74, **p = 0.1550** (2000 permutaciones)
- **V de Cramér = 0.173** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | positivo | negativo | neutral |
|---|---|---|---|
| positivo | 3 | 8 | 35 |
| negativo | 0 | 4 | 41 |
| neutral | 2 | 1 | 19 |

## Nota metodológica

Conjunto fusionado del censo (n=113 = piloto 60 del 13/8 + tanda 1 53 del 3/9, corpus completo al corte del 3/9). Protocolo mixto declarado: E1 = M. Scopel (humano, manual, ambas tandas); E2 piloto = clasificacion ciega asistida por LLM, REVISADA Y CONFIRMADA por M. Scopel (13/8, sin acceso del LLM a las etiquetas del pipeline ni de E1); E2 tanda 1 = G. Fracchia (humano, manual, sin LLM). Discrepancias resueltas por adjudicacion conjunta: 10 de tanda 1 (sesion del 3/9/2026) y 22 del piloto (sesion conjunta del 28/9/2026, resueltas todas a favor de la etiqueta E1). Con la adjudicacion aplicada el consenso cubre los 113 items (sin exclusiones). Etiquetas del pipeline generadas por el sistema en produccion (n8n + RSS Reddit + keywords + VADER + PostgreSQL). Registro de sesiones: ground_truth/registro_sesiones.md y gonza_pendientes_2026-09-28/01_censo_ground_truth/registro_adjudicacion_piloto.md.
