"""Actualiza las URLs del workflow osint_monitoreo_rss en la DB de n8n.

Cambio (2026-09-02, workflow v2): feeds de portada (.rss, 25 entradas) ->
feeds de novedades con limite 100 (/new/.rss?limit=100), consistente con
osint_pipeline.py (el extractor documentado). Con backup previo de la DB.

Correr con la instancia de n8n DETENIDA:
    docker run --rm --entrypoint /opt/python/bin/python3 \
      -v ttesis_n8n_data:/home/node/.n8n \
      -v <scripts>:/data/scripts ttesis-maxi-n8n:latest \
      /data/scripts/update_workflow_urls.py
"""

import json
import shutil
import sqlite3
import time
from pathlib import Path

DB = Path("/home/node/.n8n/database.sqlite")
BACKUP_DIR = Path("/home/node/.n8n/backup_db")
WORKFLOW_ID = "44r3Ak5lL8SZPy6q"
NODE_NAME = "Definir fuentes (Reddit RSS)"
URL_MAP = {
    "https://www.reddit.com/r/netsec/.rss": "https://www.reddit.com/r/netsec/new/.rss?limit=100",
    "https://www.reddit.com/r/cybersecurity/.rss": "https://www.reddit.com/r/cybersecurity/new/.rss?limit=100",
    "https://www.reddit.com/r/malware/.rss": "https://www.reddit.com/r/malware/new/.rss?limit=100",
}


def main() -> None:
    # 1. Backup de la DB (+ WAL/SHM) antes de tocar nada
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / stamp
    target.mkdir()
    for suffix in ("", "-wal", "-shm"):
        src = Path(str(DB) + suffix)
        if src.exists():
            shutil.copy2(src, target / src.name)
    print(f"Backup en: {target}")

    # 2. Abrir y localizar el workflow
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT id, name, nodes FROM workflow_entity WHERE id = ?", (WORKFLOW_ID,))
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"Workflow {WORKFLOW_ID} no encontrado")
    nodes = json.loads(row["nodes"])

    # 3. Editar el jsCode del nodo de fuentes
    changed = 0
    for node in nodes:
        if node.get("name") != NODE_NAME:
            continue
        js = node["parameters"]["jsCode"]
        for old, new in URL_MAP.items():
            if old in js:
                js = js.replace(old, new)
                changed += 1
        node["parameters"]["jsCode"] = js
    if changed != len(URL_MAP):
        raise SystemExit(f"Se reemplazaron {changed}/{len(URL_MAP)} URLs; ABORTADO sin escribir")

    # 4. Guardar y verificar
    cur.execute(
        "UPDATE workflow_entity SET nodes = ? WHERE id = ?",
        (json.dumps(nodes, ensure_ascii=False), WORKFLOW_ID),
    )
    con.commit()
    cur.execute("SELECT nodes FROM workflow_entity WHERE id = ?", (WORKFLOW_ID,))
    js_back = json.loads(cur.fetchone()["nodes"])
    for node in js_back:
        if node.get("name") == NODE_NAME:
            code = node["parameters"]["jsCode"]
            assert "/new/.rss?limit=100" in code, "Verificacion fallo"
            assert ".rss'" not in code, "Quedan URLs viejas"
            print("URLs nuevas OK:")
            for line in code.splitlines():
                if "reddit.com" in line:
                    print("   ", line.strip())
    con.close()
    print("Workflow actualizado y verificado.")


if __name__ == "__main__":
    main()
