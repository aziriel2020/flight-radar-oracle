"""Scheduled public flight-price observation snapshots.

No credentials, no customer PII. This module deliberately never labels a
third-party scrape as a verified/bookable fare or a guaranteed discount.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
from pathlib import Path

from .engine import Offer, now, stamp
from .sources import fast_flights_search, load_json, make_plan

MAX_HISTORY = 6000
HISTORY_DAYS = 90
FRESH_HOURS = 12
REQUIRED_DAYS = 8
MAX_OFFERS = 72


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def save_json(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".writing")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, target)


def quote_identity(row):
    return "|".join(str(row.get(k, "")) for k in (
        "origin", "destination", "departure_date", "return_date",
        "carrier", "stops", "cabin", "baggage",
    ))


def normalize(o, reference):
    o.validated()
    if o.source == "DEMO_NON_REEL":
        raise ValueError("Synthetic demo fares must never enter live collection")
    if not (dt.date.today() < dt.date.fromisoformat(o.departure_date)):
        raise ValueError("Flight already departed")
    # Future-dated sample timestamps may not be published.
    moment = dt.datetime.fromisoformat((o.collected_at or stamp(reference)).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError("Timestamp must contain timezone")
    if moment > reference + dt.timedelta(minutes=5):
        raise ValueError("Observation is in the future")
    if reference - moment > dt.timedelta(days=HISTORY_DAYS):
        raise ValueError("Observation is too old")
    return {
        "origin": o.origin, "destination": o.destination,
        "departure_date": o.departure_date, "return_date": o.return_date,
        "price_eur": round(float(o.price_eur), 2),
        "carrier": o.carrier[:80], "source": o.source[:100],
        "stops": int(o.stops), "cabin": o.cabin,
        "baggage": o.baggage, "link": o.link[:500],
        "checked_at": moment.isoformat(timespec="seconds"),
        "state": "observed",
    }


def compile_feed(history, new_rows, reference=None):
    reference = reference or now()
    cutoff = reference - dt.timedelta(days=HISTORY_DAYS)
    seen = {}
    for row in history + new_rows:
        if not isinstance(row, dict) or row.get("source") == "DEMO_NON_REEL":
            continue
        try:
            when = dt.datetime.fromisoformat(str(row["checked_at"]).replace("Z", "+00:00"))
            date = dt.date.fromisoformat(str(row["departure_date"]))
            price = float(row["price_eur"])
            if when.tzinfo is None or when < cutoff or when > reference + dt.timedelta(minutes=5):
                continue
            if date <= reference.date() or not 0 < price <= 100000:
                continue
            ident = quote_identity(row) + "|" + when.isoformat()
            prior = seen.get(ident)
            if prior is None or price < float(prior["price_eur"]):
                seen[ident] = row
        except (ValueError, KeyError, TypeError):
            continue
    all_rows = sorted(seen.values(), key=lambda x: x["checked_at"], reverse=True)[:MAX_HISTORY]

    # Compare identical itineraries across distinct collection days only.
    groups = collections.defaultdict(dict)
    for row in all_rows:
        day = row["checked_at"][:10]
        group = groups[quote_identity(row)]
        best = group.get(day)
        if best is None or row["price_eur"] < best:
            group[day] = row["price_eur"]

    # Latest observation per EXACT itinerary. Ignore stale snapshots.
    freshest = {}
    for row in all_rows:
        try:
            age = reference - dt.datetime.fromisoformat(row["checked_at"].replace("Z", "+00:00"))
            if age < dt.timedelta(0) or age > dt.timedelta(hours=FRESH_HOURS):
                continue
            ident = quote_identity(row)
            prev = freshest.get(ident)
            if prev is None or row["checked_at"] > prev["checked_at"] or (
                row["checked_at"] == prev["checked_at"] and row["price_eur"] < prev["price_eur"]
            ):
                freshest[ident] = row
        except (ValueError, KeyError, TypeError):
            continue

    offers = []
    for row in freshest.values():
        days = groups[quote_identity(row)]
        baseline = None
        saving_pct = None
        saving_eur = None
        if len(days) >= REQUIRED_DAYS:
            values = sorted(days.values())
            midpoint = len(values)//2
            baseline = (values[midpoint] if len(values)%2 else (values[midpoint-1]+values[midpoint])/2)
            saving_eur = baseline-row["price_eur"]
            saving_pct = round(100*saving_eur/baseline, 1) if baseline > 0 else None
        offer = dict(row)
        offer["baseline_eur"] = round(baseline, 2) if baseline is not None else None
        offer["evidence_days"] = len(days)
        offer["saving_pct"] = saving_pct
        offer["saving_eur"] = round(saving_eur, 2) if saving_eur is not None else None
        offer["potential_deal"] = bool(len(days) >= REQUIRED_DAYS and saving_pct is not None and saving_pct >= 25 and saving_eur >= 50)
        offer["verified"] = False
        offers.append(offer)
    offers.sort(key=lambda x: (not x["potential_deal"], x["price_eur"], x["checked_at"]))
    return all_rows, offers[:MAX_OFFERS]


def run(config, source, limit=4, input_file=None, experimental=False,
        history_path="data/history.json", feed_path="data/market.json"):
    reference = now()
    old = read_json(history_path, {"observations": []})
    history = old.get("observations", []) if isinstance(old, dict) else []
    results, errors = [], []
    if source == "json":
        if not input_file:
            raise ValueError("--file required for source json")
        for o in load_json(input_file):
            try:
                results.append(normalize(o, reference))
            except (ValueError, TypeError) as exc:
                errors.append(str(exc)[:160])
    elif source == "fast-flights":
        if not experimental:
            raise ValueError("Unofficial provider requires --allow-unofficial-collection")
        plan = make_plan(config["origins"], config["destinations"],
                         config["days_ahead"], config["stays"], max(1, min(limit, 12)))
        for origin, destination, departure, returning in plan:
            try:
                offers = fast_flights_search(origin, destination, departure, returning)
                for offer in offers:
                    results.append(normalize(offer, reference))
                print(f"{origin}->{destination} {departure}: {len(offers)} observations", flush=True)
            except Exception as exc:
                message = f"{origin}->{destination} {type(exc).__name__}: {str(exc)[:120]}"
                errors.append(message)
                print("Provider error: " + message, flush=True)
    else:
        raise ValueError("Unsupported source")

    updated_history, visible = compile_feed(history, results, reference)
    if results:
        save_json(history_path, {"schema_version": 1, "observations": updated_history})
    status = "ok" if results and not errors else "partial" if results else "error"
    feed = {
        "schema_version": 1,
        "updated_at": stamp(reference),
        "status": status,
        "source": source,
        "scanned_offers": len(results),
        "errors": errors[:6],
        "history_observations": len(updated_history),
        "offers": visible,
        "disclaimer": "Indicative observed prices, not guaranteed bookable fares; confirm price and baggage on booking site.",
    }
    save_json(feed_path, feed)
    print(json.dumps({"status": status, "scanned_offers": len(results),
                      "visible": len(visible), "history": len(updated_history),
                      "errors": errors[:6]}, ensure_ascii=False))
    # An outage must not be interpreted as a successful live collection.
    return 0 if results else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["json", "fast-flights"], required=True)
    ap.add_argument("--file")
    ap.add_argument("--allow-unofficial-collection", action="store_true")
    ap.add_argument("--limit", type=int, default=4)
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--history", default="data/history.json")
    ap.add_argument("--feed", default="data/market.json")
    args = ap.parse_args()
    conf = read_json(args.config, None)
    if not isinstance(conf, dict):
        ap.error("Missing JSON config")
    raise SystemExit(run(conf, args.source, args.limit, args.file,
                         args.allow_unofficial_collection, args.history, args.feed))


if __name__ == "__main__":
    main()
