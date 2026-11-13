# Evidencia de la ventana de operacion continua (23-28/10/2026)

Respaldo de la ventana citada en el Anexo H de la tesis. Dos CSV, ambos con
horas en **ART (UTC-3)**:

| Archivo | Filas | Contenido |
|---|---|---|
| `ventana_continua_ciclos.csv` | 110 | Una fila por ciclo de n8n, ejecuciones #226 a #335 |
| `ventana_continua_altas_por_hora.csv` | 96 | Publicaciones nuevas por hora (solo horas con al menos una alta) |

## Columnas

`ventana_continua_ciclos.csv`: `id, hora_art, status, duracion_s, upserts, altas_nuevas`

- `id`: id de ejecucion de n8n.
- `hora_art`: hora de inicio del ciclo, truncada a la hora (`YYYY-MM-DD HH:MM`).
- `status`, `duracion_s`: estado y duracion registrados por n8n.
- `upserts`: posts enviados al nodo de carga en el ciclo (insertados o actualizados).
- `altas_nuevas`: posts cuyo `first_seen_at` cae en esa hora (0 si no hay).

`ventana_continua_altas_por_hora.csv`: `hora_art, altas`.

## Como se construyeron

1. **Ciclos y upserts.** Se leyo `execution_data` de la SQLite de n8n (solo lectura)
   con `export_upserts_por_ejecucion.py`, que cuenta los items que entran al
   nodo de carga de cada ejecucion. Salida: `upserts_por_ejecucion_2026-09-28.csv`
   (publicado en `evidencia/upserts_por_ejecucion_2026-09-28.csv`; el nombre
   conserva la fecha de la primera version y el archivo se regenero despues; el
   script esta en `evidencia/export_upserts_por_ejecucion.py`).
   Se filtraron las ejecuciones 226 a 335. `status` y `duracion_s` salen de ese
   mismo export; coinciden con `scripts/log_ejecuciones_n8n_2026-10-30.csv`
   (`export_ejecuciones_n8n.py`).
2. **Altas por hora.** Consulta de solo lectura sobre PostgreSQL. `first_seen_at`
   se fija en el INSERT y no se modifica en el `ON CONFLICT` (`schema.sql`), por
   lo que marca el primer avistamiento de cada post:

   ```sql
   SELECT to_char(date_trunc('hour',
            first_seen_at AT TIME ZONE 'America/Argentina/Buenos_Aires'),
            'YYYY-MM-DD HH24:MI') AS hora_art,
          COUNT(*) AS altas
   FROM posts
   WHERE first_seen_at >= '2026-10-24 01:00+00'
     AND first_seen_at <  '2026-10-28 14:30+00'
   GROUP BY 1 ORDER BY 1;
   ```

   El rango es 23/10 22:00 a 28/10 11:30 ART.
3. **Cruce.** Para cada ciclo se tomo `altas_nuevas` = altas de la hora que
   coincide con `hora_art` (el ciclo arranca en el minuto :00 y dura unos 18 min,
   por lo que sus altas caen en esa misma hora). Si no hay fila de altas, vale 0.

## Resultado (reproducible desde los CSV)

- 110 ciclos, 110 en estado `success`; primero #226 (23/10 22:00), ultimo #335 (28/10 11:00).
- 76.900 upserts en total (600-700 por ciclo).
- 358 altas nuevas, distribuidas en 96 de las 110 horas; en las otras 14 horas
  solo hubo re-encuentros de publicaciones ya vistas.
- Duracion por ciclo: 1.067 a 1.225 s.

Esto es evidencia de que el sistema ejecuto y **escribio datos nuevos** de forma
sostenida; no es una medicion de desempeno del clasificador.

## Limitaciones

- El umbral de 48-72 h es un criterio operativo fijado a posteriori; no figura
  en el Capitulo 1 de la tesis.
- `first_seen_at` se agrego el 28/9/2026 y, para filas anteriores, se completo con
  `collected_at`; no afecta a esta ventana (todos los posts de la ventana son
  posteriores).
- Los archivos de origen (log de n8n y export de upserts) estan publicados en
  `evidencia/`; las altas por hora se calculan sobre la tabla `posts`, que no se
  publica (la consulta SQL de arriba la reproduce sobre una copia de la base).
