# Registro de adjudicación del piloto — RESUELTO (28 de septiembre de 2026)

Las **22 discrepancias del piloto (13/8/2026: 3 de categoría + 20 de sentimiento; un post
discrepa en ambas)** quedaron **adjudicadas en sesión conjunta (llamada) E1 + E2 del piloto
(M. Scopel + G. Fracchia), 28/9/2026**. **Resultado: las 22 se resolvieron a favor de la
etiqueta E1 (M. Scopel, etiquetado manual exhaustivo)** — las etiquetas asistidas por LLM
que discrepaban fueron descartadas por decisión conjunta.

Con esto el censo fusionado (n=113) queda con **consenso 113/113 en categoría y en
sentimiento (sin exclusiones)**.

## Archivos

- `discrepancias_piloto.csv` — material de la sesión (los 22 posts, las dos etiquetas).
- `discrepancias_piloto_resueltas.csv` — resolución aplicada (22 filas = etiqueta E1),
  generada y verificada desde `muestra_eval1.csv` (etiquetas E1 originales).
- `censo_resueltas.csv` — resolución combinada del censo (10 de tanda 1 + 22 del piloto = 32).
- `resultados_censo_final_113.md` — evaluación FINAL del censo completo (n=113, sin exclusiones).
- `censo_gold_humano_113.csv` — gold humano final (`post_id,subreddit,threat_category,sentiment,compound`).

## Registro de la sesión

| Sesión | Quién | Fecha | Inicio | Fin | Guardado de la resolución |
|---|---|---|---|---|---|
| Adjudicación de las 22 discrepancias del piloto | E1: M. Scopel + E2: G. Fracchia (llamada) | 28/9/2026 | _(a anotar)_ | _(a anotar)_ | 28/9/2026 23:57 ART |

Condiciones: etiquetas finales acordadas por discusión conjunta sobre el material de
`discrepancias_piloto.csv`, sin acceso a las etiquetas del pipeline durante la decisión.

## Nota sobre el protocolo del piloto (aclarada 28/9/2026)

El E2 del piloto (13/8) fue **clasificación ciega asistida por LLM, revisada y confirmada
por M. Scopel** (confirmado por el evaluador el 28/9/2026; el LLM no tuvo acceso a las
etiquetas del pipeline ni a las de E1). El kappa del piloto (0.937 categoría / 0.310
sentimiento) mide, por lo tanto, el acuerdo entre el etiquetado manual exhaustivo y el
asistido por IA bajo revisión humana — no es una autoevaluación del sistema (el pipeline
evaluado es keywords + VADER, no un LLM).

## Resultados finales del censo (ver `resultados_censo_final_113.md`)

- Acuerdo inter-evaluador pre-adjudicación: **κ 0.876** categoría (IC 95 % [0.798, 0.943]) /
  **0.469** sentimiento (IC 95 % [0.281, 0.655]).
- Pipeline vs consenso humano (n=113): categoría **F1 macro 0.516 / micro 0.469**,
  V de Cramér 0.618, p < 0.0001. Sentimiento **F1 micro 0.230** (p = 0.155: sin asociación
  — VADER inoperante en el dominio, consistente con lo declarado).
