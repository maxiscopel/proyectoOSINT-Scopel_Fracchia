# Evidencia citada en la tesis

Material de respaldo (logs, scripts forenses, datos del 14/9). Se publica tal como se
generó, salvo las anonimizaciones indicadas.

| Archivo | Qué es |
|---|---|
| `PROVENIENCIA.md` | Recuperación de `osint_pipeline.py` v1 (agosto 2026). Los archivos `.py` recuperados **no** se publican porque contienen la sal de seudonimización anterior. |
| `log_ejecuciones_n8n_2026-09-14.csv`, `_10-13`, `_10-22`, `_10-30` | Exports del log de ejecuciones de n8n (`scripts/export_ejecuciones_n8n.py`). |
| `update_workflow_urls.py` | Cambio del 2/9/2026 de feeds `.rss` a `/new/.rss?limit=100`. |
| `evidencia_eventlog_windows.txt` | Evidencia de cortes de red/energía (Event Log de Windows). |
| `auditoria_forense_2026-09-25.py` y `auditoria_forense_salida_2026-09-25.txt` | Script forense del 25/9/2026 (versión publicada con nombre descriptivo) y su salida. |
| `log_ejecuciones_n8n_2026-09-03.csv` | Export del log de n8n del 3/9/2026: ids 2 a 31 (corridas manuales de agosto y ciclos horarios hasta el corte del corpus de 102). |
| `upserts_por_ejecucion_2026-09-28.csv` y `export_upserts_por_ejecucion.py` | Desglose de upserts por ejecución (por subreddit y categoría) y el script que lo genera. Respalda los 850 upserts del §5.1 y la columna `upserts` de `ground_truth/ventana_continua_ciclos.csv`. |
| `datos_flujo_2026-09-14/posts_dataset.csv` | Corpus de 860 publicaciones al 14/9. **Anonimizado:** `author` = `sha256(AUTHOR_SALT + hash_previo)[:16]` (el usuario original es irrecuperable) y un nombre de usuario dentro de un título reemplazado por `[usuario eliminado]`. |
| `datos_flujo_2026-09-14/posts_dataset_completo.csv` | Los mismos 860 registros **con `content` y `raw_content`** (sin el pie `submitted by /u/usuario [link] [comments]` y con 3 menciones `u/usuario` del cuerpo reemplazadas por `u/[usuario eliminado]`), `collected_at` y `source`. Permite reclasificar el corpus: `title + " " + content` con el clasificador original (commit `3ba6127^`) reproduce las 860 etiquetas; con el corregido (plurales), cambian 40. |
| `datos_flujo_2026-09-14/workflow_osint_monitoreo_rss_2026-09-14.json` | Workflow n8n vigente el 14/9. |

`build_anexo_b.py` no existe y no se cita.
