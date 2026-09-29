FROM n8nio/n8n:2.9.2

USER root

# La imagen base de n8n 2.x es Alpine "hardened": no trae apk ni python.
# Se instala Python autónomo (python-build-standalone, musl) descargado con
# el fetch integrado de Node y extraido con tar (las unicas herramientas del SO).
RUN node -e "const { createWriteStream } = require('fs'); const { Readable } = require('stream'); const url = 'https://github.com/astral-sh/python-build-standalone/releases/download/20260807/cpython-3.12.13%2B20260807-x86_64-unknown-linux-musl-install_only.tar.gz'; fetch(url).then(async (r) => { if (!r.ok) throw new Error('HTTP ' + r.status); const out = createWriteStream('/tmp/py.tar.gz'); const body = Readable.fromWeb(r.body); body.pipe(out); await new Promise((res, rej) => { out.on('finish', res); out.on('error', rej); }); console.log('descargado', r.headers.get('content-length')); }).catch((e) => { console.error(e); process.exit(1); });" \
    && tar -xzf /tmp/py.tar.gz -C /opt \
    && rm /tmp/py.tar.gz \
    && /opt/python/bin/python3 -m pip install --no-cache-dir feedparser nltk praw \
    && /opt/python/bin/python3 -c "import nltk; nltk.download('vader_lexicon', download_dir='/opt/python/nltk_data')"

ENV PATH="/opt/python/bin:${PATH}"
ENV NLTK_DATA="/opt/python/nltk_data"
ENV PYTHONUNBUFFERED=1

USER node
