"""Symulator strumieni: zgloszenia, obciazenie 112 i sygnaly social do Eventstream (custom endpoint).

Tryb --dry-run dziala offline i nie wymaga poswiadczen. Ground truth kampanii nie jest wysylany.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASETS = ROOT / "datasets"
STREAM_FILES = {
    "report": "fact_report",
    "report_update": "fact_report_update",
    "hotline": "fact_hotline_load",
    "social": "fact_social_signal",
    "disorder": "fact_disorder_event",
}
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_env():
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.strip().startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def parse_ts(value):
    if not value:
        return None
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def iter_events(names, start, end):
    for name in names:
        path = DATASETS / f"{STREAM_FILES[name]}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Brak pliku {path}; uruchom generate_datasets.py")
        with path.open(encoding="utf-8") as f:
            for line in f:
                ev = json.loads(line)
                ts = parse_ts(ev["timestamp"])
                if (start and ts < start) or (end and ts > end):
                    continue
                yield ts, ev


def send_batches(events, conn, hub, speed, flush_s=1.0):
    from azure.eventhub import EventData, EventHubProducerClient

    producer = EventHubProducerClient.from_connection_string(conn_str=conn, eventhub_name=hub)
    sent = 0
    with producer:
        batch = producer.create_batch()
        last_flush, prev = time.time(), None
        for ts, ev in events:
            if prev and speed > 0:
                time.sleep(min((ts - prev).total_seconds() / speed, 2.0))
            prev = ts
            data = EventData(json.dumps(ev, ensure_ascii=False))
            try:
                batch.add(data)
            except ValueError:
                producer.send_batch(batch)
                batch = producer.create_batch()
                batch.add(data)
            sent += 1
            if time.time() - last_flush >= flush_s and len(batch) > 0:
                producer.send_batch(batch)
                batch = producer.create_batch()
                last_flush = time.time()
        if len(batch) > 0:
            producer.send_batch(batch)
    return sent


def main():
    p = argparse.ArgumentParser(description="Odtwarzanie strumieni scenariusza do Eventstream")
    p.add_argument("--stream", default="all", help="report, report_update, hotline, social, disorder albo all")
    p.add_argument("--speed", type=float, default=3600.0, help="mnoznik czasu; 3600 = godzina danych w sekunde; 0 = bez opoznien")
    p.add_argument("--from", dest="from_ts", help="ISO timestamp od")
    p.add_argument("--to", dest="to_ts", help="ISO timestamp do")
    p.add_argument("--dry-run", action="store_true", help="offline: nie laczy sie z Eventstream, wypisuje liczniki i probke")
    p.add_argument("--output", help="zapisz zdarzenia dry-run do pliku JSONL")
    p.add_argument("--config", default="config.json")
    args = p.parse_args()

    load_env()
    names = list(STREAM_FILES) if args.stream == "all" else [s.strip() for s in args.stream.split(",")]
    for n in names:
        if n not in STREAM_FILES:
            raise SystemExit(f"Nieznany strumien: {n}")
    start, end = parse_ts(args.from_ts), parse_ts(args.to_ts)
    events = sorted(iter_events(names, start, end), key=lambda x: x[0])

    if args.dry_run:
        counts: dict[str, int] = {}
        out = open(args.output, "w", encoding="utf-8") if args.output else None
        try:
            for i, (ts, ev) in enumerate(events):
                counts[ev["stream"]] = counts.get(ev["stream"], 0) + 1
                if out:
                    out.write(json.dumps(ev, ensure_ascii=False) + "\n")
                elif i < 5:
                    print(json.dumps(ev, ensure_ascii=False))
        finally:
            if out:
                out.close()
        print(f"DRY_RUN_SENT={len(events)} by_stream={json.dumps(counts)}")
        if events:
            print(f"first={events[0][0].isoformat()} last={events[-1][0].isoformat()}")
        return

    cfg_path = ROOT / args.config
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    conn = os.environ.get("EVENTHUB_CONNECTION_STRING") or cfg.get("eventhub_connection_string")
    hub = os.environ.get("EVENTHUB_NAME") or cfg.get("eventhub_name")
    if not conn or not hub:
        raise SystemExit("Brak EVENTHUB_CONNECTION_STRING/EVENTHUB_NAME w .env albo config.json")
    sent = send_batches((e for e in events), conn, hub, args.speed)
    print(f"SENT={sent}")


if __name__ == "__main__":
    main()
