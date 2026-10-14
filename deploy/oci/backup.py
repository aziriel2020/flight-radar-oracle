import sqlite3,datetime as dt, pathlib
src=pathlib.Path("/var/lib/flight-radar/flight_radar.sqlite")
dest=pathlib.Path("/var/lib/flight-radar/backups")
dest.mkdir(parents=True,exist_ok=True)
target=dest/("flight-radar-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".sqlite")
with sqlite3.connect(src) as source,sqlite3.connect(target) as target_conn: source.backup(target_conn)
cutoff=dt.datetime.now(dt.timezone.utc).timestamp()-14*86400
for p in dest.glob("flight-radar-*.sqlite"):
 if p.stat().st_mtime<cutoff:p.unlink()
print(target)
