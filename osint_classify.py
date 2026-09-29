#!/usr/bin/env python3
"""osint_classify.py — etapa de transformación (nodo 3 del workflow).

Lee los registros crudos (JSON array) desde --input, aplica la clasificación
por categoría de amenaza y el análisis de sentimiento VADER, y emite el
resultado como JSON array en stdout para que n8n lo consuma.

Los logs van a stderr, para no ensuciar el stdout.
"""

import argparse
import json
import logging
import sys

import osint_pipeline as p

LOG = logging.getLogger("osint_classify")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="OSINT classify: keywords + VADER")
    parser.add_argument("--input", required=True, help="Archivo JSON con registros crudos")
    parser.add_argument(
        "--out", default=None,
        help="Archivo JSON de salida clasificado (si se pasa, stdout solo lleva un resumen)",
    )
    args = parser.parse_args(argv)

    with open(args.input, encoding="utf-8") as fh:
        records = json.load(fh)

    records = p.classify_records(records)
    for record in records:
        if record.get("author"):
            record["author"] = p.pseudonymize_author(record["author"])

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False)
        sys.stdout.write(json.dumps({"ok": True, "total": len(records), "out": args.out}))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(json.dumps(records, ensure_ascii=False))
        sys.stdout.write("\n")
    LOG.info("Clasificación OK: %d registros", len(records))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    main()
