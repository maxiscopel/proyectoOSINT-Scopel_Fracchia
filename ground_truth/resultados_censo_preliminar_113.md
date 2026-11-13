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
Discrepancias resueltas por adjudicación conjunta: **10** posts (el kappa de esta sección es el acuerdo ANTES de esa sesión).

## 3. Acuerdo evaluador vs. pipeline

| Comparación | Categoría (κ) | Sentimiento (κ) |
|---|---|---|
| Evaluador 1 vs. pipeline | 0.330 | -0.010 |
| Evaluador 2 vs. pipeline | 0.300 | 0.060 |

## 4. Consenso humano y discrepancias

- Ítems con consenso en categoría: **110 / 113** (97.3%)
- Ítems con consenso en sentimiento: **93 / 113** (82.3%)
- Discrepancias de categoría: **3** | de sentimiento: **20**
- Pre-adjudicación el consenso era: categoría 102/113 | sentimiento 90/113. Resueltas por adjudicación conjunta: 10 | sin resolver: 23

Los ítems con discrepancia se excluyen del análisis de desempeño (sección 5) salvo que se resuelvan con `--resuelto`.

## 5.a. Desempeño del pipeline vs. consenso humano — categoría de amenaza

Ítems considerados: **110** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| no_clasificado | 0.361 | 0.846 | 0.506 | 26 |
| vulnerabilidad | 0.524 | 0.367 | 0.431 | 30 |
| malware | 1.000 | 0.400 | 0.571 | 25 |
| phishing | 0.444 | 0.800 | 0.571 | 5 |
| ransomware | 1.000 | 1.000 | 1.000 | 4 |
| otro | 0.000 | 0.000 | 0.000 | 20 |
| **Macro** | 0.555 | 0.569 | 0.513 | 110 |
| **Micro** | 0.464 | 0.464 | 0.464 | 110 |

- F1 micro IC 95 %: [0.373, 0.555] | F1 macro IC 95 %: [0.414, 0.583]
- χ² = 209.29, **p = 0.0000** (2000 permutaciones)
- **V de Cramér = 0.617** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | no_clasificado | vulnerabilidad | malware | phishing | ransomware | otro |
|---|---|---|---|---|---|---|
| no_clasificado | 22 | 14 | 13 | 1 | 0 | 11 |
| vulnerabilidad | 3 | 11 | 1 | 0 | 0 | 6 |
| malware | 0 | 0 | 10 | 0 | 0 | 0 |
| phishing | 1 | 0 | 1 | 4 | 0 | 3 |
| ransomware | 0 | 0 | 0 | 0 | 4 | 0 |
| otro | 0 | 5 | 0 | 0 | 0 | 0 |

## 5.b. Desempeño del pipeline vs. consenso humano — sentimiento

Ítems considerados: **93** (consenso humano).

| Clase | Precisión | Exhaustividad | F1 | Soporte |
|---|---|---|---|---|
| positivo | 0.071 | 0.600 | 0.128 | 5 |
| negativo | 0.125 | 0.333 | 0.182 | 12 |
| neutral | 0.842 | 0.211 | 0.337 | 76 |
| **Macro** | 0.346 | 0.381 | 0.215 | 93 |
| **Micro** | 0.247 | 0.247 | 0.247 | 93 |

- F1 micro IC 95 %: [0.161, 0.333] | F1 macro IC 95 %: [0.134, 0.296]
- χ² = 4.53, **p = 0.3295** (2000 permutaciones)
- **V de Cramér = 0.156** (tamaño de efecto)

**Matriz de confusión** (filas = pipeline, columnas = consenso humano):

|  | positivo | negativo | neutral |
|---|---|---|---|
| positivo | 3 | 7 | 32 |
| negativo | 0 | 4 | 28 |
| neutral | 2 | 1 | 16 |

## Nota metodológica

Conjunto fusionado del censo (n=113 = piloto 60 del 13/8 + tanda 1 53 del 3/9, corpus completo al corte del 3/9). Protocolo mixto declarado: E1 = M. Scopel (humano, manual, ambas tandas); E2 piloto = clasificacion ciega asistida por LLM (13/8, sin acceso a etiquetas del pipeline ni de E1); E2 tanda 1 = G. Fracchia (humano, manual, sin LLM). Discrepancias de tanda 1 (10/53) resueltas por adjudicacion conjunta el 3/9; discrepancias del piloto (22/60) PENDIENTES de adjudicacion: en este reporte preliminar quedan excluidas del analisis de desempeno (seccion 5a sobre 110/113 items y 5b sobre 93/113 items; los 3+20 con discrepancia del piloto quedan fuera hasta la adjudicacion). El reporte final (post-adjudicacion) cubrira los 113. Etiquetas del pipeline generadas por el sistema en produccion (n8n + RSS Reddit + keywords + VADER + PostgreSQL).

---

## Errata (12/11/2026)

**Qué se corrigió.** El texto de arriba es el original de septiembre de 2026 y se conserva
sin cambios. Atribuía el Evaluador 1 (E1) del piloto a M. Scopel. El 11/11/2026 (commit
`dc081c2`) se había reescrito ese texto para unificar los roles; ese cambio se hizo sin
errata y queda registrado aquí. La atribución vigente es: **en el piloto (13/8/2026), E1 =
G. Fracchia (etiquetado manual) y E2 = M. Scopel (clasificación ciega asistida por LLM,
revisada y confirmada por M. Scopel)**. En la tanda 1 (3/9/2026) y en la tanda 2, E1 = M. Scopel
y E2 = G. Fracchia, sin LLM.

**Evidencia en que se apoya.** La atribución vigente se apoya en la declaración conjunta de
los autores y en los registros de sesión (`registro_sesiones.md`, que cubre la tanda 1). No
existe un registro contemporáneo independiente de quién etiquetó cada archivo del piloto:
`muestra_eval1.csv` y `muestra_eval2.csv` son plantillas vacías e idénticas, y el registro
contemporáneo (el texto original de arriba) indicaba otra cosa. Se declara así en la tesis (§5.6).

**Efecto sobre las métricas.** Ninguno en el κ ni en el desempeño declarado: las etiquetas
no cambian, solo el nombre de quien las produjo. Para acotar el efecto de la adjudicación en
bloque de las 22 discrepancias del piloto a favor de E1, se recalculó la sensibilidad exacta
adjudicándolas a favor de E2:

Véase la tabla de sensibilidad en `registro_adjudicacion_piloto.md` (reproducible con `sensibilidad_piloto.py`): categoría 0,469 → 0,451 (F1 micro) y 0,516 → 0,509 (macro); sentimiento 0,230 → 0,319 (micro) y 0,193 → 0,296 (macro).
