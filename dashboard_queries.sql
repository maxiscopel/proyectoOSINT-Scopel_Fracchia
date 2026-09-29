-- =====================================================
-- DASHBOARD OSINT - Consultas para Metabase
-- Base de datos: osint_db (PostgreSQL)
-- =====================================================

-- 1. Threat Stats: Distribucion por categoria de amenaza
SELECT threat_category,
       COUNT(*) AS total,
       ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS porcentaje
FROM posts
GROUP BY threat_category
ORDER BY total DESC;

-- 2. Sentiment Stats: Distribucion de sentimiento y promedio de compound
SELECT sentiment,
       COUNT(*) AS total,
       ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS porcentaje,
       ROUND(AVG(compound)::numeric, 4) AS compound_promedio
FROM posts
GROUP BY sentiment
ORDER BY total DESC;

-- 3. Interaction Stats: Interaccion por subreddit
SELECT subreddit,
       COUNT(*) AS n,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY score) AS mediana_score,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY num_comments) AS mediana_comentarios,
       ROUND(STDDEV(score)::numeric, 2) AS desviacion_score,
       ROUND(STDDEV(num_comments)::numeric, 2) AS desviacion_comentarios,
       ROUND(AVG(score)::numeric, 2) AS promedio_score,
       ROUND(AVG(num_comments)::numeric, 2) AS promedio_comentarios
FROM posts
GROUP BY subreddit
ORDER BY mediana_score DESC NULLS LAST;

-- 4. Temporal Series: Serie temporal diaria
SELECT DATE(created_utc) AS fecha,
       COUNT(*) AS total_posts,
       COUNT(*) FILTER (WHERE threat_category <> 'no_clasificado') AS clasificados,
       ROUND(AVG(compound)::numeric, 4) AS compound_promedio
FROM posts
WHERE created_utc IS NOT NULL
GROUP BY DATE(created_utc)
ORDER BY fecha;
