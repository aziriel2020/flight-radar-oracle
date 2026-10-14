from __future__ import annotations
import dataclasses, datetime as dt, re, sqlite3, statistics
from typing import Any

UTC=dt.timezone.utc
def now(): return dt.datetime.now(UTC)
def stamp(d=None): return (d or now()).isoformat(timespec="seconds")
@dataclasses.dataclass
class Offer:
    origin: str
    destination: str
    departure_date: str
    return_date: str
    price_eur: float
    carrier: str
    source: str
    stops: int=0
    cabin: str="economy"
    baggage: str="unknown"
    link: str=""
    details: str=""
    collected_at: str=""
    def validated(self):
        if not re.fullmatch(r"[A-Z]{3}",self.origin) or not re.fullmatch(r"[A-Z]{3}",self.destination): raise ValueError("Invalid IATA code")
        d=dt.date.fromisoformat(self.departure_date)
        if self.return_date and dt.date.fromisoformat(self.return_date)<=d: raise ValueError("Invalid return date")
        if not (0<float(self.price_eur)<=100000): raise ValueError("Invalid price")
        if not 0<=int(self.stops)<=5: raise ValueError("Invalid stops")
        if self.baggage not in ("unknown","personal","cabin","checked"): raise ValueError("Invalid baggage")
        if not self.source or not self.carrier: raise ValueError("Missing source or carrier")
        return self

def connect(path):
    c=sqlite3.connect(path,timeout=10)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY, origin TEXT NOT NULL, destination TEXT NOT NULL,
        departure_date TEXT NOT NULL, return_date TEXT NOT NULL, price_eur REAL NOT NULL,
        carrier TEXT NOT NULL, source TEXT NOT NULL, stops INTEGER NOT NULL, cabin TEXT NOT NULL,
        baggage TEXT NOT NULL, link TEXT, details TEXT, collected_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_history ON observations(origin,destination,departure_date,return_date,carrier,stops,cabin,baggage,collected_at);
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY, observation_id INTEGER UNIQUE NOT NULL,
        baseline_eur REAL, saving_pct REAL, savings_eur REAL, score INTEGER,
        evidence_days INTEGER, state TEXT NOT NULL DEFAULT 'pending',
        checked_price_eur REAL, checked_at TEXT, sent_at TEXT
    );
    CREATE TABLE IF NOT EXISTS source_runs (id INTEGER PRIMARY KEY, source TEXT, checked_at TEXT, successful INTEGER, count INTEGER, message TEXT);
    """)
    return c

def baseline(c,o,reference,min_days=8):
    rows=c.execute("""
    SELECT substr(collected_at,1,10) day, MIN(price_eur) price FROM observations
    WHERE origin=? AND destination=? AND departure_date=? AND return_date=?
    AND carrier=? AND stops=? AND cabin=? AND baggage=? AND collected_at>=?
    GROUP BY substr(collected_at,1,10)
    """,(o.origin,o.destination,o.departure_date,o.return_date,o.carrier,o.stops,o.cabin,o.baggage,stamp(reference-dt.timedelta(days=120)))).fetchall()
    return (float(statistics.median(x["price"] for x in rows)),len(rows)) if len(rows)>=min_days else None

def ingest(c,o,reference=None,min_days=8,min_saving_pct=.25,min_savings_eur=50):
    o.validated(); reference=reference or now()
    b=baseline(c,o,reference,min_days)
    with c:
        cur=c.execute("""INSERT INTO observations(origin,destination,departure_date,return_date,price_eur,carrier,source,stops,cabin,baggage,link,details,collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",(o.origin,o.destination,o.departure_date,o.return_date,o.price_eur,o.carrier,o.source,o.stops,o.cabin,o.baggage,o.link,o.details,o.collected_at or stamp(reference)))
        result={"observation_id":cur.lastrowid,"candidate_id":None}
        if b is None: return result
        base,days=b
        saving=base-float(o.price_eur)
        pct=saving/base
        if pct<min_saving_pct or saving<min_savings_eur:return result
        prior=c.execute("""SELECT ob.price_eur FROM candidates ca JOIN observations ob ON ca.observation_id=ob.id WHERE ob.origin=? AND ob.destination=? AND ob.departure_date=? AND ob.return_date=? AND ob.carrier=? AND ob.stops=? AND ob.cabin=? AND ob.baggage=? AND ca.state<>'rejected' AND ob.collected_at>=? ORDER BY ob.price_eur LIMIT 1""",(o.origin,o.destination,o.departure_date,o.return_date,o.carrier,o.stops,o.cabin,o.baggage,stamp(reference-dt.timedelta(hours=48)))).fetchone()
        if prior and float(o.price_eur)>=prior["price_eur"]*.92:return result
        score=min(100,round(100*(.65*min(pct/.6,1)+.2*min(saving/300,1)+.15*min(days/20,1))))
        cur=c.execute("INSERT INTO candidates(observation_id,baseline_eur,saving_pct,savings_eur,score,evidence_days) VALUES (?,?,?,?,?,?)",(cur.lastrowid,round(base,2),round(pct*100,2),round(saving,2),score,days))
        result.update(candidate_id=cur.lastrowid,saving_pct=round(pct*100,2),score=score)
        return result

def list_candidates(c,states=("pending","verified","sent"),limit=100):
    marks=",".join("?"*len(states))
    return [dict(x) for x in c.execute(f"""SELECT ca.*,ob.origin,ob.destination,ob.departure_date,ob.return_date,ob.price_eur,ob.carrier,ob.source,ob.stops,ob.cabin,ob.baggage,ob.link,ob.details,ob.collected_at FROM candidates ca JOIN observations ob ON ca.observation_id=ob.id WHERE ca.state IN ({marks}) ORDER BY ca.score DESC,ca.id DESC LIMIT ?""",(*states,limit)).fetchall()]

def verify_candidate(c,identifier,price):
    rows=[x for x in list_candidates(c,("pending",),999999) if x["id"]==identifier]
    if not rows: raise ValueError("Candidate not pending")
    o=rows[0]
    t=dt.datetime.fromisoformat(o["collected_at"].replace("Z","+00:00"))
    if now()-t>dt.timedelta(minutes=60): raise ValueError("Stale quote")
    if not o["link"] or not 0<price<=o["price_eur"]*1.05: raise ValueError("Quote price/link mismatch")
    with c:c.execute("UPDATE candidates SET state='verified',checked_price_eur=?,checked_at=? WHERE id=?",(price,stamp(),identifier))
    return {"id":identifier,"state":"verified"}

def record_run(c,source,success,count,message=""):
    with c:c.execute("INSERT INTO source_runs(source,checked_at,successful,count,message) VALUES (?,?,?,?,?)",(source,stamp(),int(success),count,message[:400]))
