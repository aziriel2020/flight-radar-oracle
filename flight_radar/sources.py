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

def fast_flights_search(origin,dest,departure,return_date):
    # Unofficial experimental connector, opt-in only; no challenge bypass or proxies.
    try:
        from fast_flights import FlightQuery,Passengers,create_query,get_flights
    except ImportError as e:raise RuntimeError("pip install 'fast-flights>=3,<4'") from e
    flights=[FlightQuery(date=departure,from_airport=origin,to_airport=dest,max_stops=1)]
    if return_date:flights.append(FlightQuery(date=return_date,from_airport=dest,to_airport=origin,max_stops=1))
    q=create_query(flights=flights,seat="economy",trip="round-trip" if return_date else "one-way",passengers=Passengers(adults=1),currency="EUR",language="en",hide_separate_and_self_transfer=True)
    res=get_flights(q)
    output=[]
    for flight in getattr(res,"flights",[])[:5]:
        p=getattr(flight,"price",None)
        if p is None:continue
        url="https://www.google.com/travel/flights?q="+quote(f"Flights from {origin} to {dest} on {departure} return {return_date}")
        stops_raw = getattr(flight, "stops", None)
        if isinstance(stops_raw, (int, float)):
            stops = int(stops_raw)
        elif isinstance(stops_raw, str):
            value = stops_raw.strip().lower()
            if value in ("nonstop", "non-stop", "direct", "0 stops", "0 stop"):
                stops = 0
            elif re.match(r"^[1-5]\\s+stops?$", value):
                stops = int(value[0])
            else:
                # Do not invent direct flights when stop count is unknown.
                continue
        else:
            # Some versions omit a structured stop count. Do not guess.
            continue
        output.append(Offer(origin,dest,departure,return_date,price_float(p),str(getattr(flight,"name","Unknown")), "fast-flights-unofficial",stops,link=url,details="Indicative third-party observed fare. Verify itinerary, baggages and booking price.").validated())
    return output
