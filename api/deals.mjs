// Read-only public feed. Accepts only fresh, verified, non-demo flight offers.
// Configure FLIGHT_RADAR_FEED_URL to an HTTPS JSON feed operated by you.
// No persistent writes or browser scraping run within this function.
function normalized(value) {
  const a = Array.isArray(value) ? value : Array.isArray(value?.offers) ? value.offers : [];
  const now = Date.now();
  return a.filter(o => {
    if (!o || typeof o !== "object") return false;
    const checked = Date.parse(o.checked_at || o.verified_at || "");
    return o && o.state === "verified" && o.source !== "DEMO_NON_REEL" &&
      typeof o.origin === "string" && /^[A-Z]{3}$/.test(o.origin) &&
      typeof o.destination === "string" && /^[A-Z]{3}$/.test(o.destination) &&
      Number.isFinite(Number(o.checked_price_eur ?? o.price_eur)) &&
      Number(o.checked_price_eur ?? o.price_eur) > 0 &&
      Number.isFinite(checked) && checked <= now && now - checked <= 60 * 60 * 1000;
  }).slice(0,60).map(o => ({
    origin:o.origin,destination:o.destination,
    departure_date:String(o.departure_date||""),
    return_date:String(o.return_date||""),
    price_eur:Number(o.checked_price_eur ?? o.price_eur),
    savings_pct:Number(o.saving_pct||0),
    carrier:String(o.carrier||"Non précisée").slice(0,60),
    source:String(o.source||"").slice(0,60),
    checked_at:String(o.checked_at||o.verified_at),
    link:(typeof o.link==="string" && /^https:\/\//i.test(o.link))?o.link:null
  }));
}
export async function GET() {
  const url=process.env.FLIGHT_RADAR_FEED_URL;
  if (!url) return Response.json({offers:[],connected:false,message:"Aucune source tarifaire vérifiée connectée."},{headers:{"Cache-Control":"no-store"}});
  if (!/^https:\/\//i.test(url)) return Response.json({offers:[],connected:false,error:"invalid_feed_configuration"},{status:503});
  try {
    const headers={"Accept":"application/json"};
    if (process.env.FLIGHT_RADAR_FEED_TOKEN) headers.Authorization="Bearer "+process.env.FLIGHT_RADAR_FEED_TOKEN;
    const result=await fetch(url,{headers,signal:AbortSignal.timeout(7000),cache:"no-store"});
    if(!result.ok) throw new Error("feed_"+result.status);
    const length=Number(result.headers.get("content-length")||0);
    if(length>1024*1024) throw new Error("feed_too_large");
    const raw=await result.text();
    if(raw.length>1024*1024) throw new Error("feed_too_large");
    return Response.json({offers:normalized(JSON.parse(raw)),connected:true},{headers:{"Cache-Control":"no-store"}});
  }catch {
    return Response.json({offers:[],connected:false,message:"Source indisponible ; aucun tarif non vérifié publié."},{status:503,headers:{"Cache-Control":"no-store"}});
  }
}
