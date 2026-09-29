#!/usr/bin/env python3
"""osint_fetch.py — etapa de extracción (nodo 2 del workflow).

Trae los feeds RSS públicos de Reddit y escribe los registros crudos
(sin clasificar) como JSON array en el archivo indicado por --out.

El siguiente nodo (osint_classify.py) los clasifica. Emite a stdout un
resumen JSON; los logs van a stderr.
"""

import argparse
import json
import logging
import sys

import osint_pipeline as p

LOG = logging.getLogger("osint_fetch")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="OSINT fetch: RSS de Reddit (crudo)")
    parser.add_argument("--subreddits", nargs="*", default=["netsec", "cybersecurity", "malware"])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", required=True, help="Archivo JSON de salida (registros crudos)")
    args = parser.parse_args(argv)

    records = p.collect_records(args.subreddits, args.limit)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False)

    sys.stdout.write(json.dumps({"ok": True, "total": len(records)}) + "\n")
    LOG.info("Fetch OK: %d registros crudos (subreddits=%s)", len(records), ",".join(args.subreddits))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    main()
