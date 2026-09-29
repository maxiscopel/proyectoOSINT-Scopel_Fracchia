-- Schema definitivo para el sistema de monitoreo OSINT
-- Base de datos: PostgreSQL 15+
-- ESTE esquema es la UNICA verdad: el pipeline (osint_pipeline.py), el workflow n8n
-- y la tesis (§4.5.2) deben coincidir con el. No debe existir otra variante.
--
-- first_seen_at (agregada 2026-09-28 contra la base real): primer avistamiento del
-- post por el sistema. El UPSERT del workflow la asigna NOW() en el INSERT y NO la
-- toca en el ON CONFLICT DO UPDATE -> queda congelada en el alta (a diferencia de
-- collected_at, que se refresca en cada re-encuentro). Para bases existentes:
--   ALTER TABLE posts ADD COLUMN IF NOT EXISTS first_seen_at timestamptz;
--   UPDATE posts SET first_seen_at = collected_at WHERE first_seen_at IS NULL;
--   ALTER TABLE posts ALTER COLUMN first_seen_at SET DEFAULT now();

CREATE TABLE IF NOT EXISTS posts (
    post_id         VARCHAR(300) PRIMARY KEY,
    title           TEXT NOT NULL,
    content         TEXT,
    raw_content     TEXT,
    author          VARCHAR(100) NOT NULL,
    subreddit       VARCHAR(100) NOT NULL,
    url             TEXT,
    score           INTEGER DEFAULT 0,
    num_comments    INTEGER DEFAULT 0,
    threat_category VARCHAR(50) NOT NULL DEFAULT 'no_clasificado',
    sentiment       VARCHAR(20) NOT NULL DEFAULT 'neutral',
    compound        NUMERIC(5,4) DEFAULT 0,
    created_utc     TIMESTAMP,
    first_seen_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    collected_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    source          VARCHAR(50) NOT NULL DEFAULT 'reddit-rss'
);

-- Indices para consultas analiticas
CREATE INDEX IF NOT EXISTS idx_posts_threat    ON posts(threat_category);
CREATE INDEX IF NOT EXISTS idx_posts_sentiment ON posts(sentiment);
CREATE INDEX IF NOT EXISTS idx_posts_created   ON posts(created_utc);
CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);

-- Comentarios sobre las columnas
COMMENT ON TABLE posts IS 'Publicaciones recolectadas de Reddit via RSS para analisis OSINT';
COMMENT ON COLUMN posts.post_id IS 'Identificador unico del post en Reddit';
COMMENT ON COLUMN posts.author IS 'Autor seudonimizado (hash SHA-256 con sal)';
COMMENT ON COLUMN posts.threat_category IS 'Categoria de amenaza asignada por el clasificador';
COMMENT ON COLUMN posts.sentiment IS 'Polaridad VADER: negativo / positivo / neutral';
COMMENT ON COLUMN posts.compound IS 'Score compound de VADER en [-1, 1]';
COMMENT ON COLUMN posts.score IS 'Puntuacion real de Reddit (enriquecida via API si hay credenciales)';
COMMENT ON COLUMN posts.num_comments IS 'Cantidad real de comentarios (enriquecida via API si hay credenciales)';
COMMENT ON COLUMN posts.created_utc IS 'Fecha de creacion del post en Reddit (fuente RSS)';
COMMENT ON COLUMN posts.first_seen_at IS 'Primer avistamiento del post por el sistema (congelado en el primer INSERT; collected_at se refresca en cada re-encuentro)';
COMMENT ON COLUMN posts.collected_at IS 'Momento mas reciente en que el sistema re-encontro el registro';
COMMENT ON COLUMN posts.source IS 'Fuente de datos (reddit-rss)';
