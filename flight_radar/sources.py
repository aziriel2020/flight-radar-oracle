import datetime as dt, hashlib, json, re
from pathlib import Path
from urllib.parse import quote
from .engine import Offer

def load_json(path):
    rows=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows,list):raise ValueError("Expected a JSON array")
    return [Offer(**x).validated() for x in rows]

def make_plan(origins,destinations,days_ahead,stays,limit,today=None):
    today=today or dt.date.today()
    anchor=dt.date.fromordinal(today.toordinal()-today.toordinal()%14)
    pool=[]
    for lead in days_ahead:
        for stay in stays:
            start=anchor+dt.timedelta(days=lead)
            if start<=today:continue
            end=start+dt.timedelta(days=stay)
            pool += [(o,d,str(start),str(end)) for o in origins for d in destinations if o!=d]
    def rank(seed,x):return hashlib.sha256((seed+"|"+("|".join(x))).encode()).hexdigest()
    fixed=sorted(pool,key=lambda x:rank(str(anchor),x))[:max(1,round(limit*.70))]
    remaining=sorted((x for x in pool if x not in fixed),key=lambda x:rank(str(today),x))
    return (fixed+remaining[:max(0,limit-len(fixed))])[:limit]

def price_float(x):
    s=re.sub(r"[^0-9,.]","",str(x))
    if "," in s and "." in s:s=s.replace(".","").replace(",",".") if s.rfind(",")>s.rfind(".") else s.replace(",","")
    elif "," in s:s=s.replace(",",".")
    return float(s)

def fast_flights_search(origin, dest, departure, return_date):
    """Observe published fare quotes using fast-flights 3.1.0.

    Quotes are NOT proof of a bookable roundtrip: re-check the final price.
    The unofficial provider may stop working or prohibit automated access.
    """
    try:
        from fast_flights import FlightQuery, Passengers, create_query, get_flights
    except ImportError as e:
        raise RuntimeError("fast-flights import failed: " + str(e)) from e
    queries = [FlightQuery(date=departure, from_airport=origin, to_airport=dest, max_stops=1)]
    if return_date:
        queries.append(FlightQuery(date=return_date, from_airport=dest, to_airport=origin, max_stops=1))
    q = create_query(
        flights=queries,
        seat="economy",
        trip="round-trip" if return_date else "one-way",
        passengers=Passengers(adults=1),
        currency="EUR",
        language="en-US",
        hide_separate_and_self_transfer=True,
    )
    res = get_flights(q)
    # v3.1.0 returns ResultList(list[Flights]); older releases used a wrapper.
    items = res if isinstance(res, (list, tuple)) else getattr(res, "flights", [])
    url = q.url()
    output = []
    for flight in items[:5]:
        price = getattr(flight, "price", None)
        segments = getattr(flight, "flights", None)
        if price is None or not isinstance(segments, (list, tuple)) or not segments:
            continue
        stops = len(segments) - 1
        if not 0 <= stops <= 5:
            continue
        airlines = getattr(flight, "airlines", [])
        carrier = " / ".join(map(str, airlines))[:80] if isinstance(airlines, (list, tuple)) else str(airlines)[:80]
        if not carrier:
            carrier = "Carrier unspecified"
        output.append(Offer(
            origin=origin,
            destination=dest,
            departure_date=departure,
            return_date=return_date,
            price_eur=price_float(price),
            carrier=carrier,
            source="fast-flights-unofficial",
            stops=stops,
            link=url,
            details="Google Flights indicative quote; may not include the return fare. Verify all legs, baggage and final checkout price.",
        ).validated())
    return output
