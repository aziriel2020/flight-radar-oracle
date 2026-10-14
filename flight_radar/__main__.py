import argparse, datetime as dt, json, os, sys, urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from html import escape
from pathlib import Path
from .engine import Offer,connect,ingest,list_candidates,verify_candidate,record_run,now,stamp
from .sources import load_json,make_plan,fast_flights_search

def options(path):
    p=Path(path)
    if not p.exists():raise SystemExit("Configuration not found: "+path)
    return json.loads(p.read_text(encoding="utf-8"))

def scan(c,rows,conf):
    return [ingest(c,o,min_days=conf["minimum_history_days"],min_saving_pct=conf["discount_threshold_pct"]/100,min_savings_eur=conf["minimum_saving_eur"]) for o in rows]

def demo(c,conf):
    departure=str((now()+dt.timedelta(days=65)).date()); back=str((now()+dt.timedelta(days=72)).date())
    historical=[360,365,355,352,367,354,350,359,358,361]
    for i,price in enumerate(historical):
        o=Offer("BRU","LIS",departure,back,price,"DEMO","DEMO_NON_REEL",link="https://www.google.com/travel/flights",collected_at=stamp(now()-dt.timedelta(days=len(historical)-i)))
        ingest(c,o,min_days=conf["minimum_history_days"])
    result=scan(c,[Offer("BRU","LIS",departure,back,179,"DEMO","DEMO_NON_REEL",link="https://www.google.com/travel/flights")],conf)
    record_run(c,"DEMO_NON_REEL",True,11)
    print(json.dumps({"DEMO_SYNTHETIQUE":True,"result":result},indent=2,ensure_ascii=False))

def notify(c,send=False):
    token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    if send and (not token or not chat):raise ValueError("Telegram credentials are missing")
    sent=0
    for d in list_candidates(c,("verified",),100):
        if d["source"]=="DEMO_NON_REEL":continue
        t=dt.datetime.fromisoformat(d["checked_at"].replace("Z","+00:00")) if d["checked_at"] else None
        if not t or now()-t>dt.timedelta(minutes=60):continue
        msg=f"✈️ {d['origin']} → {d['destination']} {d['departure_date']} : {d['checked_price_eur']} EUR, -{d['saving_pct']}% historique. Vérifiez : {d['link']}"
        if not send:print("[DRY-RUN] "+msg);continue
        url="https://api.telegram.org/bot"+token+"/sendMessage"
        req=urllib.request.Request(url,data=json.dumps({"chat_id":chat,"text":msg}).encode(),headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req,timeout=20) as r:
            if not json.loads(r.read()).get("ok"):raise RuntimeError("Telegram send failed")
        with c:c.execute("UPDATE candidates SET state='sent',sent_at=? WHERE id=?",(stamp(),d["id"]))
        sent+=1
    print("sent:",sent)

HTML="""<!doctype html><html lang='fr'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Flight Radar</title><style>
body{background:#0b1321;color:#e6f1fc;font:16px system-ui;margin:0;padding:28px}main{max-width:1100px;margin:auto}
h1{font-size:clamp(2.5rem,8vw,5rem);letter-spacing:-.07em;margin:1rem 0}em{color:#57d9c6;font-style:normal}
p{color:#9eafbf}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}
article{background:#132138;border:1px solid #263b53;padding:20px;border-radius:18px}b{font-size:1.6rem}
small{display:block;color:#9eafbf;margin:7px 0}a{color:#8edce7}</style>
<main><p>SELF-HOSTED FLIGHT INTELLIGENCE</p><h1>Flight Radar<em>.</em></h1><p>Détection des prix et historique. Les offres doivent être vérifiées avant réservation.</p><div id='cards' class='cards'></div>
<p>Une source expérimentale non officielle peut être limitée. Les offres de démonstration ne sont pas réelles.</p></main><script>
(async()=>{let d=await (await fetch('/api/deals')).json();let root=document.getElementById('cards');if(!d.offers.length){root.textContent='Historique en construction : aucune offre détectée.';return}
for(let o of d.offers){let el=document.createElement('article');let h=document.createElement('h2');h.textContent=o.origin+' → '+o.destination;el.append(h);
for(let s of [o.price_eur+' EUR','Baisse historique : '+o.saving_pct+' %',o.departure_date+' / '+o.return_date,'État : '+o.state,'Source : '+o.source]){let x=document.createElement('small');x.textContent=s;el.append(x)}
if(o.link){let a=document.createElement('a');a.textContent='Rechercher et vérifier';a.href=o.link;a.rel='noopener noreferrer';a.target='_blank';el.append(a)}root.append(el)}
})()</script></html>"""

def serve(db,host,port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/","/index.html"):body=HTML.encode();mime="text/html; charset=utf-8"
            elif self.path=="/health":body=b'{"ok":true}';mime="application/json"
            elif self.path=="/api/deals":
                with connect(db) as c:rows=list_candidates(c,limit=150)
                body=json.dumps({"offers":rows},ensure_ascii=False).encode();mime="application/json"
            else:self.send_error(404);return
            self.send_response(200);self.send_header("Content-Type",mime);self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    ThreadingHTTPServer((host,port),Handler).serve_forever()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",default="flight_radar.sqlite");ap.add_argument("--config",default="config.json")
    s=ap.add_subparsers(dest="cmd",required=True)
    for name in ("init","demo","report","plan"):s.add_parser(name)
    p=s.add_parser("scan");p.add_argument("--source",choices=["json","fast-flights"],required=True);p.add_argument("--file");p.add_argument("--allow-unofficial-collection",action="store_true");p.add_argument("--limit",type=int)
    p=s.add_parser("verify");p.add_argument("candidate_id",type=int);p.add_argument("--price",type=float,required=True)
    p=s.add_parser("reject");p.add_argument("candidate_id",type=int)
    p=s.add_parser("notify");p.add_argument("--send",action="store_true")
    p=s.add_parser("serve");p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",default=8080,type=int)
    args=ap.parse_args();conf=options(args.config)
    with connect(args.db) as c:
        if args.cmd=="init":print("Database initialized:",args.db)
        elif args.cmd=="demo":demo(c,conf)
        elif args.cmd=="plan":print(json.dumps(make_plan(conf["origins"],conf["destinations"],conf["days_ahead"],conf["stays"],conf["searches_per_run"]),indent=2))
        elif args.cmd=="report":print(json.dumps(list_candidates(c),indent=2))
        elif args.cmd=="verify":print(verify_candidate(c,args.candidate_id,args.price))
        elif args.cmd=="reject":
            with c:c.execute("UPDATE candidates SET state='rejected' WHERE id=? AND state='pending'",(args.candidate_id,))
        elif args.cmd=="notify":notify(c,args.send)
        elif args.cmd=="scan":
            if args.source=="json":
                if not args.file:ap.error("--file required")
                rows=load_json(args.file);print(json.dumps(scan(c,rows,conf),indent=2));record_run(c,"json",True,len(rows))
            else:
                if not args.allow_unofficial_collection:ap.error("Explicit consent for unofficial access required")
                plan=make_plan(conf["origins"],conf["destinations"],conf["days_ahead"],conf["stays"],args.limit or conf["searches_per_run"])
                for origin,dest,out,ret in plan:
                    try:
                        rows=fast_flights_search(origin,dest,out,ret)
                        print(origin,dest,len(rows),scan(c,rows,conf))
                        record_run(c,"fast-flights",True,len(rows))
                    except Exception as e:
                        print("Scan failed:",type(e).__name__,str(e),file=sys.stderr)
                        record_run(c,"fast-flights",False,0,str(e))
        elif args.cmd=="serve":serve(args.db,args.host,args.port)
if __name__=="__main__":main()
