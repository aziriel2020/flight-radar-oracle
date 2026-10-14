"""Synchronize public, non-sensitive GitHub fare snapshots into isolated Oracle storage.

Collector runs on GitHub Actions, because unofficial Google Flights parsing fails
from the current Oracle egress IP. The Oracle VM holds durable data and images.
No credentials, account PII, browser challenge bypass, or Nuvio access.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = "https://raw.githubusercontent.com/aziriel2020/flight-radar-oracle/main/data/"
TARGET = Path("/var/lib/flight-radar/data")
MAX_BYTES = 10 * 1024 * 1024


def fetch_json(name):
    url = ROOT + name + ".json"
    req = Request(url, headers={"User-Agent": "Flight-Radar-Beta-Snapshot-Sync/1.0", "Accept": "application/json"})
    with urlopen(req, timeout=18) as response:
        if response.status != 200:
            raise RuntimeError("Upstream snapshot HTTP " + str(response.status))
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Upstream snapshot too large")
    obj = json.loads(raw)
    if not isinstance(obj, dict) or obj.get("schema_version") != 1:
        raise ValueError("Invalid feed schema")
    return obj


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".writing")
    try:
        temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def sync(target=TARGET):
    history = fetch_json("history")
    market = fetch_json("market")
    quotes = history.get("observations")
    offers = market.get("offers")
    if not isinstance(quotes, list) or not isinstance(offers, list):
        raise ValueError("Malformed upstream collection")
    if len(quotes) > 6000 or len(offers) > 72:
        raise ValueError("Upstream limit exceeded")
    # Never overwrite a healthy market with synthetic prices.
    if any(isinstance(o, dict) and o.get("source") == "DEMO_NON_REEL" for o in offers):
        raise ValueError("Synthetic deal source forbidden")
    if market.get("status") not in ("ok", "partial", "error", "not_started"):
        raise ValueError("Malformed provider status")
    atomic_write(target / "history.json", history)
    atomic_write(target / "market.json", market)
    print("Oracle mirror updated:",len(quotes),"historical observations;",
          len(offers),"recent price observations; source status:",market.get("status"),flush=True)


if __name__ == "__main__":
    sync()
