# Evidencia citada en la tesis

Material de respaldo (logs, scripts forenses, datos del 14/9). Se publica tal como se
generó, salvo las anonimizaciones indicadas.

| Archivo | Qué es |
|---|---|
| `PROVENIENCIA.md` | Recuperación de `osint_pipeline.py` v1 (agosto 2026). Los archivos `.py` recuperados **no** se publican porque contienen la sal de seudonimización anterior. |
| `log_ejecuciones_n8n_2026-09-14.csv`, `_10-13`, `_10-22`, `_10-30` | Exports del log de ejecuciones de n8n (`scripts/export_ejecuciones_n8n.py`). |
| `update_workflow_urls.py` | Cambio del 2/9/2026 de feeds `.rss` a `/new/.rss?limit=100`. |
| `evidencia_eventlog_windows.txt` | Evidencia de cortes de red/energía (Event Log de Windows). |
| `auditoria_forense_2026-09-25.py` y `auditoria_forense_salida_2026-09-25.txt` | Script forense (antes `forense_gonza_2026-09-25.py`) y su salida. |
| `datos_flujo_2026-09-14/posts_dataset.csv` | Corpus de 860 publicaciones al 14/9. **Anonimizado:** `author` = `sha256(AUTHOR_SALT + hash_previo)[:16]` (el usuario original es irrecuperable) y un nombre de usuario dentro de un título reemplazado por `[usuario eliminado]`. |
| `datos_flujo_2026-09-14/workflow_osint_monitoreo_rss_2026-09-14.json` | Workflow n8n vigente el 14/9. |

`build_anexo_b.py` no existe y no se cita.
