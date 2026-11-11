# Recuperación de `osint_pipeline.py` v1 (agosto 2026) — procedencia y verificación

**Fecha de recuperación:** 2026-10-01
**Motivo:** la v1 (la que produjo el corpus entre el 13/08 y el 02/09) fue sobrescrita
el 02/09/2026 15:09:28 por la v3 y no quedó versionada en git. El repositorio público
mostraba solo la v3, dejando un hueco de trazabilidad declarado como "limitación abierta".

**Método:** NO se usó el historial de versiones de OneDrive (la acción manual_resultó
innecesaria). La v1 se recuperó de la base de sesiones del propio agente
(`~/.local/share/opencode/opencode.db`, SQLite), que conserva la salida íntegra de las
llamadas `read` de agosto: el contenido del archivo leído, línea por línea, con la ruta
y la marca temporal. Son lecturas de archivo, no reinterpretaciones: cada bloque es una
copia literal del contenido en disco en ese instante.

---

## 1. Evidencia: cuatro lecturas completas (contenido idéntico donde corresponde)

| # | Fecha y hora (ART) | Ruta leída | Sesión opencode | `part_id` | chars | líneas | sha256 del contenido |
|---|--------------------|-----------|-----------------|-----------|-------|--------|----------------------|
| E1 | 2026-08-13 18:25:08 | `ttesis\scripts\osint_pipeline.py` | `ses_003923542ffeHn37hIwTNdIdlN` | `prt_ffd03bc6e001G5Wba9PWDIn8Ar` | 10744 | 295 | `25c43e803fa9…b9145` |
| E2 | 2026-08-13 20:46:53 | `ttesis\repo\osint_pipeline.py` | `ses_0027a9f33ffe3IDdFmov35M8F4` | `prt_ffd85858800139nglR1aKK9mbV` | 10744 | 295 | `25c43e803fa9…b9145` |
| E3 | 2026-08-27 22:33:39 | `ttesis\scripts\osint_pipeline.py` | `ses_fba00bed1ffestDa6kUoQiF5Z3` | `prt_046004c26001xTEeQZIxz5MQ2Q` | 10744 | 295 | `25c43e803fa9…b9145` |
| E4 | 2026-09-02 12:48:50 | `ttesis\repo\osint_pipeline.py` | `ses_f9d382769ffe0WfabnBgIgwd6s` | `prt_062cf0a99001BiIRYNSPRBpIOf` | 10927 | 297 | `29c556303d51…47c19` |

E1 = E2 = E3 (mismo sha256): **estado único y estable del 13/08 al 27/08**, observado en
las dos rutas (`scripts\` = la que monta el contenedor en producción, y `repo\`).
E4 es el estado de `repo\osint_pipeline.py` 2 h 21 min antes de la sobrescritura del 2/9.

### Historial de escritura (misma base, operaciones `write`/`edit`)

- `write` inicial: **2026-08-12 12:18 ART**, 7028 chars (`ses_009a85259f…`).
- 40 operaciones `edit` entre el 12/08 12:23 y el **13/08 21:59** (última).
- Entre el 13/08 21:59 y el 2/09 15:09 **no hay ninguna escritura ni edición** sobre
  ese archivo: solo lecturas. Por eso E1/E2/E3 son el mismo contenido.
- **2026-09-02 15:09:28**: sobrescritura por la v3 (301 líneas, sha256 `f91cc214c79a…8c91c`).

Nota: el paso de E3 a E4 (la normalización de guiones, ver §3) no quedó registrado como
operación `write`/`edit` en la base: se aplicó sobre la copia `repo\` por una vía que no
dejó traza de herramienta (la traza es la propia lectura E4).

---

## 2. Archivos recuperados en esta carpeta

| Archivo | Qué es | sha256 |
|---------|--------|--------|
| `osint_pipeline_v1_2026-08-12_a_2026-09-01_PRODUCCION.py` | v1: la que produjo el corpus del 13/08 al 02/09 (= E1 = E2 = E3) | `25c43e803fa92940d0cbb0303a2130533c5e8a7f88e7795842af6083eabb9145` |
| `osint_pipeline_v1B_2026-09-02_1248_repo_pre_v3.py` | v1B: estado de `repo\` el 2/09 12:48 (= E4), rama muerta | `29c556303d51ce4265f511c34bfdb3074fb68584597a6c3aaad4d3f746d47c19` |
| `diff_v1A_vs_v1B.diff` | v1 → v1B (único cambio: normalización de guiones) | — |
| `diff_v1B_vs_v3_actual.diff` | v1B → v3 (fix de rate-limit de Reddit + revert de la normalización) | — |

Los tres archivos compilan (`compile()` OK) y conservan el contenido literal leído.

---

## 3. Qué cambió entre v1 y v3 (tres hunks, en total)

1. **Throttle de Reddit** (fix del 2/9, con la evidencia de headers en el comentario):
   `RETRY_BACKOFF_SECONDS (10, 30) → (150, 150)`, `INTER_SUBREDDIT_DELAY 5.0 → 150.0`,
   y `?limit=100` en la URL del feed.
2. **Normalización léxica**: la v1B (solo `repo\`, entre las 12:48 y las 15:09 del 2/9)
   agregó `content = re.sub(r"[-_]+", " ", raw).lower()`. La v3 la quitó y quedó en
   `content = raw.lower()`. **Ver la nota forensic más abajo: esa línea nunca corrió.**
3. Docstring/comments (la v3 documenta las etapas y el diagnóstico del throttle).

### El clasificador NO cambió entre v1 y v3

`THREAT_KEYWORDS`, `TIEBREAK_ORDER`, `_word_regex` y `classify_threat` son **idénticos en
v1, v1B y v3**: mismo diccionario (10/7/9/5/6 términos), mismo regex de palabra completa
**sin manejo de plural y sin `re.IGNORECASE`**, mismo desempate.

**Verificación empírica** (`classify_threat` de cada versión aplicado a
`title + content` de las 860 filas del export del 14/09 y comparado con
`threat_category` almacenado en la base):

| Versión | Etiquetas almacenadas reproducidas |
|---------|------------------------------------|
| v1 (producción 13/08–02/09) | **860 / 860 (100.00 %)** |
| v1B (repo, 2/9 12:48) | **860 / 860 (100.00 %)** |
| v3 (actual, desde 2/9 15:09) | **860 / 860 (100.00 %)** |

Es decir: **las 860 etiquetas del corpus de referencia son reproducibles con el código
publicado en el repo.** No hay deriva de clasificación entre la versión que produjo el
corpus y la que está publicada.

---

## 4. Hallazgo forense: la "normalización léxica" de la tesis nunca se ejecutó

§4.4.1 de la tesis afirma: "conversión a minúsculas, colapso de espacios y **normalización
léxica (por ejemplo, zero-day pasa a zero day)**". Esa línea existió únicamente en la
copia `repo\` entre las 12:48 y las 15:09 del 2/9 (v1B) y **no produjo ningún efecto en
el corpus**:

- En la base viva (1598 posts al 2026-10-01): 40 posts tienen `zero-day` (con guion) en
  `content` y solo **1** tiene `zero day` (con espacio), siendo ese uno un post del 30/09
  que ya traía el término separado de origen.
- En el export del 14/09 (860 filas): 9 filas con la forma con guion en `raw_content`
  siguen **con guion** en `content`.

Consecuencia operativa: los términos multipalabra del diccionario (`zero day`,
`social engineering`, `spear phishing`, `privilege escalation`, `brute force`,
`fake login`) **no matchean** sus formas con guion (`zero-day`, `social-engineering`,
`privilege-escalation`, …), porque el código vigente no normaliza y el diccionario no
contiene las variantes con guion. El sufijo plural `(?:e?s)?` de la versión corregida de
la tesis **no** corrige esto (no alcanza el guion).

---

## 5. Estado del hueco de trazabilidad

**Cerrado con evidencia primaria.** La versión de agosto que produjo el corpus está
recuperada, con hash, origen (sesión + `part_id` + timestamp) y verificación de que
reproduce el 100 % de las etiquetas del corpus. El bonus que Gonza dejó pasar como
"pocas chances" no requirió el historial de OneDrive: la evidencia estaba en el
almacenamiento de sesiones del agente, no en el sistema de archivos.
