# Guía de etiquetado — Ground truth (Fase 4, estudio definitivo)

**Proyecto:** Monitoreo de Redes Sociales para OSINT (Tesis — Scopel & Fracchia)
**Fecha de actualización:** 3 de septiembre de 2026 (v3 — censo en tandas)
**Diseño:** el estudio incluye **TODOS los posts no-piloto del corpus a la
fecha de corte**, en tandas incrementales (censo, no muestreo):

- **Tanda 1 (ya disponible): 53 posts** — archivos `muestra_f4_t1_*.csv`.
- **Tanda 2 (a la fecha de corte): posts nuevos** recolectados por la
  operación continua del sistema, excluyendo piloto y tanda 1.
- El estudio queda completo cuando **t1 + t2 ≥ 200** posts etiquetados.

La muestra de 60 del piloto inicial ya fue etiquetada y queda como estudio
piloto reportable; sus posts están EXCLUIDOS de este estudio.

---

## 1. Rol de los evaluadores

- **Evaluador 1:** `muestra200_eval1.csv`
- **Evaluador 2:** `muestra200_eval2.csv`

Cada evaluador etiqueta **su propio archivo de forma totalmente independiente**.
No miren el archivo del otro, no consulten entre ustedes y **no abran
`muestra200_gold.csv`** (contiene las etiquetas del sistema y sesgaría la
decisión humana). No usar asistentes de IA (LLM) para etiquetar: el estándar
debe ser humano, es el punto metodológico del estudio.

**Registro de sesiones (para el apéndice metodológico):** anoten fecha, hora
de inicio y fin de cada sesión de etiquetado. Ej.: "Evaluador 1: 05-sep
16:00–17:40 (200/200)". Esto documenta que el etiquetado fue humano y real.

## 2. Cómo completar los archivos

1. Abran `muestra_f4_t1_eval1.csv` / `muestra_f4_t1_eval2.csv` con Excel (o
   Google Sheets).
2. Para cada una de las 53 filas, lean el **título** y el **contenido** del post.
3. Completen las dos columnas vacías:

| Columna | Valores válidos (exactos, en minúscula) |
|---|---|
| `threat_category` | `no_clasificado`, `vulnerabilidad`, `malware`, `phishing`, `ransomware`, `otro` |
| `sentiment` | `positivo`, `negativo`, `neutral` |

4. Guarden el archivo como CSV (manteniendo el nombre).

**Regla general:** ignoren el pie de texto `submitted by /u/... [link] [comments]`:
no aporta ni a la categoría ni al sentimiento.

**Tips para que no sea un martirio:** congelen la fila de encabezado
(Vista → Inmovilizar paneles), agranden la columna `content`, y hagan pausas
cada 50 posts. A un ritmo de ~45–60 s por post, la tanda 1 son 40–55 min
por evaluador; se puede dividir en sesiones (registrando cada una).

## 3. Definición de categorías

| Categoría | Qué significa | Señales típicas |
|---|---|---|
| `vulnerabilidad` | Fallas y debilidades de seguridad en software/hardware | CVEs, exploits, parches, disclosure/advisory, "0-day", bugs de seguridad |
| `malware` | Software malicioso y su operación | troyanos, backdoors, rootkits, botnets, spyware, keyloggers, payloads |
| `phishing` | Engaños para robar credenciales o instalar cosas | correos de phishing, sitios falsos, ingeniería social, suplantación |
| `ransomware` | Secuestro de datos a cambio de rescate | ransomware, familias (LockBit, BlackCat/ALPHV...), decryptors |
| `otro` | Otras amenazas cibernéticas | DDoS, fuerza bruta, inyección, XSS, escalada de privilegios, movimiento lateral |
| `no_clasificado` | El post **no** trata una amenaza de seguridad | carreras laborales, preguntas generales de TI, noticias no técnicas |

**Si el post menciona más de una amenaza**, elegí la que sea el **tema principal**
(la que domina el título y el contenido), no la suma de menciones.

## 4. Definición de sentimiento

| Valor | Cuándo usarlo |
|---|---|
| `positivo` | Tono favorable, optimista, de elogio o alivio |
| `negativo` | Tono crítico, de alerta, miedo, preocupación o desaprobación |
| `neutral` | Tono informativo/descriptivo, sin carga emocional clara |

**Importante:** el sentimiento es del **tono del texto**, no del tema.
Una noticia de una vulnerabilidad grave puede estar redactada de forma
informativa (`neutral`) o de forma alarmista (`negativo`).

## 5. Reglas de oro

1. Independencia total entre evaluadores.
2. No mirar `muestra200_gold.csv` ni el resultado del sistema.
3. Completar **todas las filas de su tanda**; no dejar ninguna sin etiqueta.
4. Si un post te parece ambiguo, elegí la opción que mejor describa el **tema
   principal** y marcá una `X` en una columna extra `dudoso` si querés
   discutirlo después.
5. Las etiquetas van en minúscula y exactas como en la tabla de la sección 2.
6. Las discrepancias entre evaluadores se resuelven DESPUÉS, en una sesión
   conjunta de adjudicación (no durante el etiquetado individual).

## 6. Después del etiquetado individual

1. Ambos devuelven su CSV de la tanda completo.
2. Se genera la lista de discrepancias (posts donde E1 ≠ E2).
3. **Sesión de adjudicación:** los dos evaluadores revisan juntos los posts
   discrepantes y acuerdan una etiqueta final por post →
   `discrepancias_resueltas.csv` (columnas: post_id, threat_category, sentiment).
4. Recién ahí se corre la evaluación completa contra el sistema
   (`evaluar_ground_truth.py`).

## 7. Tanda 2 y cierre del estudio

- Mientras etiquetan la tanda 1, el sistema sigue recolectando en operación
  continua (ciclo horario, stack Docker levantado).
- A la fecha de corte (cuando el corpus alcance ~260 posts: 60 del piloto +
  53 de la tanda 1 + ~147 nuevos), se genera la **tanda 2**:

  ```
  python exportar_muestra.py --total 200 --seed "tesis-f4-2026b" ^
      --exclude-from muestra_gold.csv muestra_f4_t1_gold.csv ^
      --prefix muestra_f4_t2
  ```

- Se etiqueta la tanda 2 con el mismo procedimiento (secciones 1–6).
- Al cerrar: se fusionan t1 + t2 en los archivos finales `muestra200_eval1.csv`
  / `muestra200_eval2.csv` / `muestra200_gold.csv` (concatenación de filas,
  mismo formato) y se corre la evaluación definitiva con esos archivos.
