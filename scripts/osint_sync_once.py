#!/usr/bin/env python3
"""osint_sync_once.py - recoleccion + clasificacion PUNTUAL para el boton «Sincronizar» del panel.

La invoca el workflow n8n `osint_sync_webhook` (dashboard_api/n8n_workflow_osint_sync_webhook.json).
Reusa osint_pipeline.py sin modificarlo; a diferencia del ciclo programado (150 s entre subreddits),
usa una pausa corta para que el webhook responda en ~1 minuto. Imprime UN objeto JSON por stdout:
  {"ok": true,  "fetched": N, "records": [...]}
  {"ok": false, "reason": "rate_limited" | "no_records", "errors": [...]}
"""
import argparse
import json
import sys

import osint_pipeline as p

USER_AGENT = "OSINT-CyberWatch-UTN/1.0 (tesis UTN FRM; lectura RSS publica)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subreddits", nargs="*", default=["netsec", "cybersecurity", "malware"])
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--delay", type=float, default=6.0)
    args = ap.parse_args()

    p.USER_AGENT = USER_AGENT
    p.INTER_SUBREDDIT_DELAY = args.delay
    p.RETRY_BACKOFF_SECONDS = (15,)

    errors = []
    orig = p.fetch_feed_with_retry

    def traced(sub):
        try:
            return orig(sub)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            raise

    p.fetch_feed_with_retry = traced
    records = p.collect_records(args.subreddits, args.limit)
    if not records:
        reason = "rate_limited" if errors and all("429" in e for e in errors) else "no_records"
        print(json.dumps({"ok": False, "reason": reason, "errors": errors[:5]}))
        return
    p.classify_records(records)
    print(json.dumps({"ok": True, "fetched": len(records), "records": records}, ensure_ascii=False))


if __name__ == "__main__":
    main()
