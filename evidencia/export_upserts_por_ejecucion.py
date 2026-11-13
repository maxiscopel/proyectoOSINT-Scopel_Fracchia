"""export_upserts_por_ejecucion.py — desglose de upserts por ejecucion y subreddit (2026-09-28, v2).

Responde el punto 3 de la lista de pendientes: para CADA ejecucion del workflow
osint_monitoreo_rss (44r3Ak5lL8SZPy6q), cuantos posts inserto/actualizo por
subreddit, segun el contenido real de execution_data (la tabla que no se poda).

Formato de n8n 2.x: el JSON de ejecucion viene deduplicado por indices:
data = [ {esqueleto con punteros "N" -> root[N]}, fragmentos... ].
Los punteros aparecen a TODOS los niveles (runs, data, main, branch, item,
json, valores de campos). Este script resuelve cada nivel con deref().

Deteccion de nodos agnostica a la version del workflow:
  - feeder: items con 'subreddit' y 'post_id' (lo que entra al nodo postgres).
  - saver: items con claves {post_id, threat_category} (RETURNING del INSERT).
  - resumen: nodo "Resumen del ciclo" (v3): {ciclos_ok, por_categoria}.

Salida: /data/scripts/upserts_por_ejecucion_2026-09-28.csv

Corre dentro del contenedor maxi-n8n:
    docker exec maxi-n8n /opt/python/bin/python3 /data/scripts/export_upserts_por_ejecucion.py
"""

import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta

WF_ID = "44r3Ak5lL8SZPy6q"
OUT = "/data/scripts/upserts_por_ejecucion_2026-09-28.csv"

con = sqlite3.connect("file:/home/node/.n8n/database.sqlite?mode=ro", uri=True)
con.row_factory = sqlite3.Row


def make_deref(root):
    def deref(x):
        seen = 0
        while isinstance(x, str) and x.isdigit() and int(x) < len(root) and seen < 10:
            nxt = root[int(x)]
            if nxt is x:
                break
            x = nxt
            seen += 1
        return x
    return deref


def load_run_data(raw):
    root = json.loads(raw)
    if not isinstance(root, list) or not root:
        return None, None, None
    deref = make_deref(root)
    skel = root[0]
    if not (isinstance(skel, dict) and "resultData" in skel):
        return None, None, None
    rd = deref(skel.get("resultData"))
    if not isinstance(rd, dict):
        return None, None, None
    run_data = deref(rd.get("runData"))
    if not isinstance(run_data, dict):
        return None, None, None
    return run_data, deref, rd.get("lastNodeExecuted")


def node_output_items(run_data, deref, node):
    """Items (dicts de json) de TODAS las ramas de salida del nodo."""
    out = []
    runs = deref(run_data.get(node))
    if not isinstance(runs, list):
        return out
    for r in runs:
        r = deref(r)
        if not isinstance(r, dict):
            continue
        d = deref(r.get("data"))
        if not isinstance(d, dict):
            continue
        branches = deref(d.get("main"))
        if branches is None:
            continue
        if not isinstance(branches, list):
            branches = [branches]
        for b in branches:
            items = deref(b)
            if not isinstance(items, list):
                continue
            for it in items:
                it = deref(it)
                if isinstance(it, dict) and isinstance(deref(it.get("json")), dict):
                    out.append(deref(it["json"]))
    return out


rows = con.execute(
    "SELECT e.id, e.status, e.mode, e.startedAt, e.stoppedAt, d.data "
    "FROM execution_entity e JOIN execution_data d ON d.executionId = e.id "
    "WHERE e.workflowId = ? ORDER BY e.id",
    (WF_ID,),
).fetchall()
print(f"ejecuciones del workflow con data: {len(rows)}")

csv_rows = []
node_names_by_era = {}
for r in rows:
    run_data, deref, last_node = load_run_data(r["data"])
    rec = {
        "execution_id": r["id"], "mode": r["mode"], "status": r["status"],
        "started_at_utc": r["startedAt"], "started_at_art": "", "duration_s": "",
        "era": "?", "saver_node": "", "feeder_node": "", "upserts": {},
        "resumen_ciclos_ok": "", "resumen_por_categoria": "", "last_node": last_node or "",
    }
    try:
        t1 = datetime.strptime(r["startedAt"][:19], "%Y-%m-%d %H:%M:%S")
        rec["started_at_art"] = (t1 - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        if r["stoppedAt"]:
            t2 = datetime.strptime(r["stoppedAt"][:19], "%Y-%m-%d %H:%M:%S")
            rec["duration_s"] = int((t2 - t1).total_seconds())
    except Exception:
        pass

    if run_data:
        names = sorted(run_data.keys())
        rec["nodes"] = names
        if any("RSS Feed Read" in n or "Definir fuentes" in n for n in names):
            rec["era"] = "v2"
        elif any("Fetch (Python)" in n for n in names):
            rec["era"] = "v3"
        node_names_by_era.setdefault(rec["era"], set()).update(names)

        feeder = saver = None
        for n in names:
            items = node_output_items(run_data, deref, n)
            if not items:
                continue
            keys = set()
            for it in items[:50]:
                keys.update(it.keys())
            if feeder is None and "subreddit" in keys and "post_id" in keys:
                feeder = n
            if saver is None and keys and keys <= {"post_id", "threat_category"}:
                saver = n
        rec["saver_node"] = saver or ""
        rec["feeder_node"] = feeder or ""
        if feeder:
            counts = Counter()
            for it in node_output_items(run_data, deref, feeder):
                counts[str(deref(it.get("subreddit")))] += 1
            rec["upserts"] = dict(counts)
        if "Resumen del ciclo" in run_data:
            for it in node_output_items(run_data, deref, "Resumen del ciclo"):
                if "ciclos_ok" in it:
                    rec["resumen_ciclos_ok"] = deref(it.get("ciclos_ok"))
                    pc = deref(it.get("por_categoria"))
                    rec["resumen_por_categoria"] = json.dumps(pc, ensure_ascii=False) if isinstance(pc, dict) else str(pc)
    else:
        rec["nodes"] = []
    csv_rows.append(rec)

con.close()

SUBS = ["netsec", "cybersecurity", "malware", "phishing", "malwareanalysis", "secopsdaily", "threatintel"]
with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(
        ["execution_id", "started_at_utc", "started_at_art", "status", "mode", "duration_s",
         "era", "saver_node", "feeder_node", "total_upserts"] +
        [f"upserts_{s}" for s in SUBS] +
        ["resumen_ciclos_ok", "resumen_por_categoria", "last_node"]
    )
    for rec in csv_rows:
        ups = rec["upserts"]
        w.writerow(
            [rec["execution_id"], rec["started_at_utc"], rec["started_at_art"], rec["status"],
             rec["mode"], rec["duration_s"], rec["era"], rec["saver_node"], rec["feeder_node"],
             sum(ups.values())] +
            [ups.get(s, 0) for s in SUBS] +
            [rec["resumen_ciclos_ok"], rec["resumen_por_categoria"], rec["last_node"]]
        )

print(f"CSV: {OUT} ({len(csv_rows)} filas)\n")
print("nodos vistos por era:")
for era, names in sorted(node_names_by_era.items()):
    print(f"  {era}: {sorted(names)}")

print("\n=== TODAS las ejecuciones (id, ART, status, dur, era, upserts por sub) ===")
for rec in csv_rows:
    ups = rec["upserts"]
    subs = ",".join(f"{k}={v}" for k, v in sorted(ups.items())) or "-"
    print(f"  #{rec['execution_id']:>4} {rec['started_at_art'] or rec['started_at_utc']:<19} "
          f"{rec['status']:<8} {str(rec['duration_s']):>5}s {rec['era']:<2} {subs}")
