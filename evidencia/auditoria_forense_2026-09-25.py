"""auditoria_forense_2026-09-25.py — responde las preguntas bloqueantes del profesor.

1) SELECT execution_entity id BETWEEN 20 AND 30 — DB viva + todos los backups
2) huérfanas en execution_data (distingue "nunca existieron" vs "borradas")
3) workflow de la ejecución 22 (workflow borrado, ¿flujo 3?)
4) versiones del workflow osint_monitoreo_rss con las URLs del feed (25 vs 100)

Corre dentro del contenedor maxi-n8n (bind mount ./scripts -> /data/scripts):
    docker exec maxi-n8n /opt/python/bin/python3 /data/scripts/auditoria_forense_2026-09-25.py
"""

import glob
import json
import re
import sqlite3

LIVE = "/home/node/.n8n/database.sqlite"
BACKUPS = sorted(glob.glob("/home/node/.n8n/backup_db/*.sqlite"))
WF_RSS = "44r3Ak5lL8SZPy6q"


def ro(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def q20_30(con: sqlite3.Connection, label: str) -> None:
    cur = con.execute(
        "SELECT e.id, e.workflowId, w.name, e.status, e.mode, e.startedAt, e.stoppedAt "
        "FROM execution_entity e LEFT JOIN workflow_entity w ON w.id = e.workflowId "
        "WHERE e.id BETWEEN 20 AND 30 ORDER BY e.id"
    )
    rows = cur.fetchall()
    print(f"\n=== {label} — execution_entity id 20..30 ({len(rows)} filas) ===")
    for r in rows:
        print("   ", r)


print("### PUNTO 2: ejecuciones 23-27 (SELECT literal del profesor)")

con = ro(LIVE)
total = con.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM execution_entity").fetchone()
print(f"\nDB viva: {total[0]} ejecuciones (id {total[1]}..{total[2]})")
q20_30(con, "DB viva /home/node/.n8n/database.sqlite")
orphans = con.execute(
    "SELECT executionId FROM execution_data WHERE executionId BETWEEN 20 AND 30 ORDER BY executionId"
).fetchall()
print("   execution_data id 20..30 presentes:", [o[0] for o in orphans])
seq = con.execute("SELECT * FROM sqlite_sequence WHERE name = 'execution_entity'").fetchall()
print("   sqlite_sequence:", seq)
con.close()

for b in BACKUPS:
    con = ro(b)
    total = con.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM execution_entity").fetchone()
    print(f"\nbackup {b}: {total[0]} ejecuciones (id {total[1]}..{total[2]})")
    q20_30(con, f"backup {b}")
    con.close()

print("\n### workflow de la ejecución 22 (workflow borrado, ¿flujo 3?)")
con = ro(LIVE)
r22 = con.execute(
    "SELECT id, workflowId, status, mode, startedAt FROM execution_entity WHERE id = 22"
).fetchone()
print("   exec 22:", r22)
if r22 and r22[1]:
    wf = r22[1]
    cur = con.execute("SELECT name, active, versionId FROM workflow_entity WHERE id = ?", (wf,))
    print("   workflow_entity:", cur.fetchone(), "(None = workflow borrado)")
    cur = con.execute(
        "SELECT versionId, name, createdAt FROM workflow_history WHERE workflowId = ? ORDER BY createdAt",
        (wf,),
    )
    for row in cur.fetchall():
        print("   workflow_history del borrado:", row)

print("\n### workflows vivos")
for row in con.execute("SELECT id, name, active, activeVersionId, updatedAt FROM workflow_entity"):
    print("   ", row)

print(f"\n### versiones del workflow {WF_RSS} (osint_monitoreo_rss)")
rows = con.execute(
    "SELECT versionId, name, createdAt, length(nodes) FROM workflow_history "
    f"WHERE workflowId = '{WF_RSS}' ORDER BY createdAt"
).fetchall()
for row in rows:
    print("   ", row)

print("\n### URLs del feed y comandos por versión")
out = {}
for versionId, name, createdAt, _ in rows:
    nodeblob = con.execute(
        "SELECT nodes FROM workflow_history WHERE versionId = ?", (versionId,)
    ).fetchone()
    nodes = json.loads(nodeblob[0]) if nodeblob and nodeblob[0] else []
    urls, cmds = set(), []
    for n in nodes:
        params = n.get("parameters", {})
        s = json.dumps(params)
        for m in re.findall(r"https?://[^\"'\\ ]+", s):
            if "reddit" in m:
                urls.add(m)
        if "command" in params:
            cmds.append(params["command"])
    out[versionId] = {"name": name, "createdAt": createdAt,
                      "reddit_urls": sorted(urls), "commands": cmds}
    print(f"\n-- {versionId} ({name}, {createdAt})")
    for u in sorted(urls):
        print("     url:", u)
    for c in cmds:
        print("     cmd:", c if len(c) < 220 else c[:220] + "...")
con.close()

with open("/data/scripts/workflow_versiones_2026-09-25.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)
print("\nEvidencia completa -> /data/scripts/workflow_versiones_2026-09-25.json")
