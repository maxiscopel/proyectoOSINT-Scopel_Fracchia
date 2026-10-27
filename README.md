# OSINT Pipeline - Monitoreo de Ciberseguridad

Sistema automatizado de monitoreo OSINT aplicado a la ciberseguridad. Recolecta publicaciones de
Reddit, las clasifica por categoria de amenaza y analiza sentimiento. Desarrollado como parte de una
tesis de grado (Scopel & Fracchia, 2026); el ground truth y su evaluacion estan incluidos.

## Arquitectura

```
Reddit RSS -> n8n (orquestador) -> Python (E/T) -> PostgreSQL
```

- **Extraccion**: feeds RSS de Reddit (`/r/<sub>/new/.rss?limit=100`) de 7 subreddits:
  netsec, cybersecurity, malware, phishing, malwareanalysis, secopsdaily, threatintel
- **Transformacion**: clasificacion por palabras clave + VADER para sentimiento
- **Carga**: PostgreSQL con deduplicacion via `ON CONFLICT DO UPDATE`

## Requisitos

- Docker y Docker Compose
- 2 GB de RAM minimo
- Conexion a internet (para feeds RSS de Reddit)

## Instalacion

1. Clonar el repositorio:
```bash
git clone https://github.com/maxiscopel/proyectoOSINT-Scopel_Fracchia.git
cd proyectoOSINT-Scopel_Fracchia
```

2. Levantar los servicios:
```bash
docker-compose up -d
```

3. Verificar que los contenedores esten ejecutandose:
```bash
docker-compose ps
```

4. Acceder a n8n:
```
http://localhost:5678
```

5. Importar el workflow desde `workflow_osint_monitoreo_rss.json` en n8n y activarlo.

> **Importante (n8n >= 2.0):** el nodo `Execute Command` esta excluido por defecto por seguridad
> (`NODES_EXCLUDE`). El `docker-compose.yml` ya define `NODES_EXCLUDE: "[]"` para habilitarlo.
> Sin esto, al importar el workflow se pierden las conexiones del nodo `Execute Command`.
>
> **Importante (n8n 2.9.x):** si los ciclos quedan en 0 upserts con "JSON invalido en clasificado",
> verificar el modo binario. El nodo `Validate & Map` usa `this.helpers.getBinaryDataBuffer()`
> (API soportada en cualquier modo binario); el acceso directo a `binary.data.data` falla cuando
> n8n usa filesystem-v2 (el marcador no es base64).

## Estructura del repositorio

```
.
├── osint_pipeline.py                 # Pipeline de E/T (version de referencia)
├── osint_fetch.py                     # Fetch RSS (el que ejecuta n8n)
├── osint_classify.py                  # Clasificador + VADER (el que ejecuta n8n)
├── scripts/                           # Copia montada en /data/scripts (la que corre el contenedor)
├── Dockerfile                         # Imagen Docker con n8n + Python 3.12 (build-standalone musl)
├── docker-compose.yml                 # PostgreSQL + n8n + Metabase (restart: always)
├── workflow_osint_monitoreo_rss.json  # Workflow n8n activo (exportado de la DB que ejecuta)
├── schema.sql                         # DDL de la base de datos (esquema definitivo)
├── dashboard_queries.sql              # Consultas del dashboard (Metabase)
├── requirements.txt                   # Dependencias Python (versiones exactas)
├── requirements-freeze.txt            # pip freeze completo del contenedor que ejecuto
├── ground_truth/                      # Estudio de ground truth completo (ver abajo)
└── README.md                          # Este archivo
```

## Uso

### Ejecucion manual del pipeline

```bash
python osint_pipeline.py --subreddits netsec cybersecurity malware phishing malwareanalysis secopsdaily threatintel --limit 100 --out salida.json
```

### Parametros

- `--subreddits`: lista de subreddits a consultar
- `--limit`: numero maximo de publicaciones por subreddit (default: 100)
- `--out`: archivo de salida JSON (default: stdout)
- `--enrich`: enriquecer score/num_comments via API de Reddit (requiere praw y credenciales)

### Ejecucion automatica via n8n

El workflow (`workflow_osint_monitoreo_rss.json`) ejecuta el pipeline cada 60 minutos:

```
Schedule Trigger (60') -> Fetch (Python) -> Clasificar (Python) -> Read Classified (Disk)
  -> Code Validate & Map -> IF Registros validos -> Postgres Save (ON CONFLICT DO UPDATE)
      -> Resumen del ciclo -> consolidar -> [Threat Stats | Sentiment Stats | Interaction Stats | Temporal Series]
  -> (else) Log de errores
```

- **Fetch (Python)**: `osint_fetch.py` sobre los 7 subreddits con espaciado entre requests.
- **Clasificar (Python)**: `osint_classify.py` (keywords + VADER) escribe `/tmp/osint_classified.json`.
- **Validate & Map**: valida y mapea al esquema; lee el binario con `getBinaryDataBuffer()`.
- **Save to DB**: `INSERT ... ON CONFLICT (post_id) DO UPDATE` de `score`, `num_comments`,
  `compound` y `collected_at`. La columna `first_seen_at` se asigna `NOW()` en el INSERT y **no**
  se toca en el `ON CONFLICT` -> queda congelada en el primer avistamiento (a diferencia de
  `collected_at`, que se refresca en cada re-encuentro).
- Las estadisticas (Threat/Sentiment/Interaction/Temporal) se ejecutan una vez por ciclo.

Para activar el enriquecimiento de interaccion real (score/num_comments), definir
`REDDIT_CLIENT_ID` y `REDDIT_CLIENT_SECRET` en el entorno del contenedor. Sin credenciales,
esos campos quedan en 0 (limitacion documentada).

## Clasificacion de amenazas

El sistema clasifica las publicaciones en 5 categorias:

| Categoria | Keywords ejemplo |
|-----------|------------------|
| vulnerabilidad | vulnerability, cve, exploit, patch, zero day |
| malware | malware, trojan, backdoor, rootkit, botnet |
| phishing | phishing, credential, social engineering |
| ransomware | ransomware, lockbit, decryptor |
| otro | ddos, brute force, injection, xss |

**Desempate**: si dos categorias empatan en coincidencias, gana la primera en orden:
vulnerabilidad > malware > phishing > ransomware > otro. Lo que no matchea queda
`no_clasificado`.

## Analisis de sentimiento

VADER (Valence Aware Dictionary and sEntiment Reasoner) sobre el texto crudo (sin normalizar).

- **Positivo**: compound >= 0.05
- **Negativo**: compound <= -0.05
- **Neutral**: -0.05 < compound < 0.05

## Ground truth y evaluacion (`ground_truth/`)

Estudio de evaluacion sobre publicaciones reales del corpus, en tandas (censo):

- **Piloto (13/8/2026, 60 posts)**: E1 humano exhaustivo + E2 clasificacion ciega asistida
  por LLM. Resultados: `resultados_ground_truth.md`.
- **Tanda 1 (3/9/2026, 53 posts)**: dos evaluadores humanos independientes (M. Scopel +
  G. Fracchia), sin LLM, con adjudicacion conjunta de 10 discrepancias
  (`registro_sesiones.md`). Resultados: `resultados_tanda1.md`.
- **Censo fusionado (113 posts = corpus completo al corte del 3/9)**:
  `censo_eval*_113.csv`, `censo_resueltas.csv` (32 adjudicadas: 10 de tanda 1 + 22 del piloto,
  todas estas ultimas a favor de la etiqueta E1) y `censo_gold_humano_113.csv` (gold final
  humano). Protocolo mixto declarado (ver nota metodologica en `resultados_censo_final_113.md`).
- **Tanda 2 (526 posts, etiquetada 20-21/10/2026)**: muestra estratificada sobre el corpus
  ampliado (1.956 publicaciones al corte del 13/10; estrato A = las 276 phishing/ransomware
  del pipeline + estrato B = 250 proporcional por subreddit; seed reproducible en
  `exportar_tanda2_estratificado.py`, corpus fuente en `posts_dataset_tanda2_1956_completo.csv`).
  Dos evaluadores humanos independientes, sin LLM: 137 discrepancias
  (`discrepancias_tanda2.csv`) resueltas por adjudicacion conjunta el 22/10/2026
  (`resuelto_tanda2_137.csv`).
- **Censo expandido (639 = 113 + 526, definitivo, 22/10/2026)**: etiquetado crudo por
  evaluador (`eval1_639.csv`, `eval2_639.csv`), resolucion total (`resuelto_639.csv`:
  169 adjudicadas = 32 del censo original + 137 de tanda 2), etiquetas del pipeline
  (`gold_639.csv` = `censo_gold_pipeline_113.csv` + `muestra_f4_t2_gold.csv`), texto fuente
  (`posts_dataset_113_completo.csv` + `posts_dataset_tanda2_1956_completo.csv`) y reporte
  (`resultados_censo_639.md`).

Resultados del censo expandido (n=639, consenso 639/639, sin exclusiones; reemplaza al
censo de 113 como resultado principal, conservado arriba por transparencia):

- Acuerdo inter-evaluador (pre-adjudicacion): kappa categoria **0.852** (IC 95%
  [0.820, 0.881]) | sentimiento **0.498** (IC 95% [0.411, 0.577]).
- Pipeline vs consenso humano, categoria: **F1 macro 0.511 / micro 0.552** (n=639,
  IC 95% [0.513, 0.592]), V de Cramer 0.528, p < 0.0001.
- Pipeline vs consenso humano, sentimiento: **F1 micro 0.218** (n=639, p = 0.009,
  V de Cramer 0.100) - VADER resulta inoperante en el dominio tecnico.
- Con el clasificador corregido (fix de plurales s/es y -ies, commit 984b2cc) sobre la
  misma base de texto: **F1 micro 0.559** (IC 95% [0.521, 0.598]) / **macro 0.520**
  (IC 95% [0.483, 0.552]) - reproducible con `recalc_clasificador_639.py`.

Reproduccion del reporte del censo expandido:

```bash
python ground_truth/evaluar_ground_truth.py \
    --eval1 ground_truth/eval1_639.csv --eval2 ground_truth/eval2_639.csv \
    --gold ground_truth/gold_639.csv --resuelto ground_truth/resuelto_639.csv \
    --out resultados_censo_639.md
```

Herramientas: `exportar_muestra.py` (censo en tandas, semilla reproducible),
`exportar_tanda2_estratificado.py` (muestra estratificada de tanda 2, seed documentada),
`generar_discrepancias.py`, `evaluar_ground_truth.py` (kappa, F1, IC bootstrap,
chi-cuadrado, V de Cramer; stdlib pura) y `recalc_clasificador_639.py` (recalculo del
clasificador corregido sobre el censo expandido, importa `classify_threat` del repo).
Guia completa: `GUIA_ETIQUETADO.md`. Registros: `registro_sesiones.md` (tanda 1) y
`registro_adjudicacion_piloto.md` (piloto, 28/9/2026).

## Limitaciones documentadas

1. **Fuente unica**: solo Reddit via RSS (sin API de datos)
2. **Clasificador por reglas**: F1 micro 0.552 en categoria sobre el censo expandido
   (n=639; 0.559 con el fix de plurales; la clase "otro" tiene F1 = 0 en todos los
   cortes, por ausencia de vocabulario, no por plural)
3. **VADER en dominio tecnico**: F1 micro 0.218 en sentimiento (n=639)
4. **Interaccion**: score/num_comments = 0 en RSS (limitacion documentada)
5. **Modo binario de n8n**: el workflow requiere el fix `getBinaryDataBuffer` (incluido)

## Dashboard (Metabase)

El `docker-compose.yml` incluye Metabase conectado a PostgreSQL:

```bash
docker-compose up -d
# Metabase: http://localhost:3000
# PostgreSQL: localhost:5432 (osint_user / osint_pass / osint_db)
```

### Setup inicial de Metabase

1. Abrir `http://localhost:3000` y completar el asistente
2. PostgreSQL: host `osint-postgres`, puerto 5432, base `osint_db`, usuario `osint_user`,
   contrasena `osint_pass`
3. Importar las 4 consultas de `dashboard_queries.sql` como preguntas guardadas
4. Crear un dashboard y agregar las 4 preguntas

## Licencia

Este codigo es parte de una tesis de grado universitaria (Scopel & Fracchia, 2026). Uso academico.
