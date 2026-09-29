# Registro de sesiones — Fase 4, tanda 1 (3 de septiembre de 2026)

Registro para el apéndice metodológico de la tesis. Los tiempos de
finalización están anclados a los timestamps de guardado de cada archivo;
los tiempos de inicio y duraciones según lo declarado por los evaluadores.

| Sesión | Quién | Inicio | Fin (anclado a archivo) | Duración |
|---|---|---|---|---|
| Generación de la muestra tanda 1 (censo, 53 posts, seed `tesis-f4-2026b`) | — | — | 13:10:54 | — |
| Etiquetado individual eval1 | Evaluador 1: Máximo Scopel | 14:10 | 14:44:58 | ~35 min |
| Etiquetado individual eval2 | Evaluador 2: Gonzalo Fracchia | ~13:55 (inicio declarado: 55 min antes de su guardado) | 14:50:30 | ~55 min |
| Sesión conjunta de adjudicación (10 discrepancias) | E1 + E2 (llamada) | inicio no anclado a archivo | 15:02:32 (guardado de la resolución) | ~25 min (declarada) |
| Evaluación (`evaluar_ground_truth.py` v3) | — | — | 15:08:29 | — |

Nota sobre la adjudicación: la lista formal de discrepancias
(`discrepancias_t1.csv`) fue generada a las 14:55:38, dentro de la ventana
de la llamada; la resolución de las 10 discrepancias (8 de categoría, 3 de
sentimiento) quedó guardada a las 15:02:32.

Condiciones del etiquetado (3-sep-2026):

- Muestra: censo de los 53 posts no-piloto del corpus al 3-sep-2026
  (corpus total: 113 posts), generada con `exportar_muestra.py` v3.
- Etiquetado individual e independiente, en archivos separados, sin
  asistencia de IA (sin LLM), sin acceso a las etiquetas del pipeline.
  **Independencia confirmada por ambos evaluadores** (cada uno etiquetó por
  su lado, sin consultar las etiquetas del otro durante la fase individual).
- Adjudicación: sesión conjunta sobre las 10 discrepancias, resolviendo una
  etiqueta final por post (`discrepancias_t1_resueltas.csv`).
- Ritmo de etiquetado E1: 53 posts en ~35 min (~40 s/post, lectura de
  título y contenido) — consistente con etiquetado humano individual.
