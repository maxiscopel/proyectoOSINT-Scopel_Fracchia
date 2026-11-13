-- limpiar_pie_usuario.sql
--
-- Sanea la tabla public.posts: elimina el pie que Reddit agrega al resumen RSS,
--     "submitted by /u/<usuario> [link] [comments]",
-- de las columnas content y raw_content. Ese pie contiene el nombre de usuario
-- en claro; el pipeline ya no lo guarda (entry_to_record, osint_pipeline.py),
-- pero los registros insertados antes del cambio lo conservan.
--
-- Es idempotente (volver a ejecutarlo no cambia nada) y solo toca las filas que
-- contienen el pie. No modifica author, title, threat_category ni sentiment.
-- La regex replica la del pipeline (_SUBMITTED_BY_RE) y es insensible a mayusculas
-- porque content esta en minusculas y raw_content conserva el texto original.
--
-- Uso (desde repo/, con el stack arriba y el .env cargado):
--     docker exec -i osint-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--         -v ON_ERROR_STOP=1 < scripts/limpiar_pie_usuario.sql
--
-- Antes de ejecutarlo conviene un respaldo:
--     docker exec osint-postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t public.posts > posts_respaldo.sql

BEGIN;

\echo '== Antes =='
SELECT count(*)                                           AS total,
       count(*) FILTER (WHERE content     ~* 'submitted\s+by') AS content_con_pie,
       count(*) FILTER (WHERE raw_content ~* 'submitted\s+by') AS raw_content_con_pie,
       count(*) FILTER (WHERE title ~* '(^|[^[:alnum:]])/?u/[[:alnum:]_-]+') AS titulos_con_usuario
FROM public.posts;

UPDATE public.posts
SET content = btrim(regexp_replace(
        regexp_replace(content,
            '\s*submitted\s+by\s+/?u/[[:alnum:]_-]+(\s*\[link\])?(\s*\[comments\])?',
            ' ', 'gi'),
        '\s+', ' ', 'g'))
WHERE content ~* 'submitted\s+by\s+/?u/';

UPDATE public.posts
SET raw_content = btrim(regexp_replace(
        regexp_replace(raw_content,
            '\s*submitted\s+by\s+/?u/[[:alnum:]_-]+(\s*\[link\])?(\s*\[comments\])?',
            ' ', 'gi'),
        '\s+', ' ', 'g'))
WHERE raw_content ~* 'submitted\s+by\s+/?u/';

\echo '== Despues (content_con_pie y raw_content_con_pie deben ser 0) =='
SELECT count(*)                                           AS total,
       count(*) FILTER (WHERE content     ~* 'submitted\s+by') AS content_con_pie,
       count(*) FILTER (WHERE raw_content ~* 'submitted\s+by') AS raw_content_con_pie,
       count(*) FILTER (WHERE title ~* '(^|[^[:alnum:]])/?u/[[:alnum:]_-]+') AS titulos_con_usuario
FROM public.posts;

-- Los titulos con usuario (si los hubiera) se revisan a mano: no se reescriben
-- automaticamente porque el titulo es texto de la publicacion, no un pie.

COMMIT;
