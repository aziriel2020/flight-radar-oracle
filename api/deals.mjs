// Read-only Vercel API: public GitHub Actions price observations.
// Unofficial provider quotes are only OBSERVED, never booking-verified.
const DEFAULT_FEED="https://raw.githubusercontent.com/aziriel2020/flight-radar-oracle/main/data/market.json";
const AGE_OBSERVED=12*60*60*1000;
const AGE_VERIFIED=60*60*1000;
function trimmed(value,max=100){return typeof value==="string"?value.slice(0,max):"";}
function parseFeed(data){
  const rows=Array.isArray(data)?data:Array.isArray(data?.offers)?data.offers:[];
  const now=Date.now();
  const offers=rows.filter(o=>{
    if (!o || typeof o!=="object" || !["observed","verified"].includes(o.state))return false;
    if(o.source==="DEMO_NON_REEL")return false;
    if(!/^[A-Z]{3}$/.test(o.origin||"") || !/^[A-Z]{3}$/.test(o.destination||""))return false;
    if(!/^\d{4}-\d{2}-\d{2}$/.test(o.departure_date||""))return false;
    const stamp=Date.parse(o.checked_at||"");
    const amount=Number(o.checked_price_eur??o.price_eur);
    return Number.isFinite(stamp) && stamp<=now && now-stamp<=(o.state==="verified"?AGE_VERIFIED:AGE_OBSERVED)
      && Number.isFinite(amount) && amount>0 && amount<=100000;
  }).slice(0,72).map(o=>({
    origin:o.origin,
    destination:o.destination,
    departure_date:o.departure_date,
    return_date:trimmed(o.return_date,10),
    price_eur:Number(o.checked_price_eur??o.price_eur),
    saving_pct:Number.isFinite(Number(o.saving_pct))&&Number(o.evidence_days)>=8?Number(o.saving_pct):null,
    evidence_days:Number(o.evidence_days)||0,
    potential_deal: Boolean(o.potential_deal)&&Number(o.evidence_days)>=8,
    checked_at:o.checked_at,
    verified:o.state==="verified",
    state:o.state,
    carrier:trimmed(o.carrier,70),
    source:trimmed(o.source,80),
    baggage:trimmed(o.baggage,30),
    stops:Number.isFinite(Number(o.stops))?Number(o.stops):null,
    link:typeof o.link==="string"&&/^https:\/\/(?:www\.)?google\.com\/travel\/flights/.test(o.link)?o.link:null,
  }));
  return {
    connected:true,
    status:trimmed(data?.status||"unknown",40),
    lastScan:data?.updated_at||null,
    quotesParsed:Number(data?.scanned_offers)||0,
    totalHistory:Number(data?.history_observations)||0,
    offers
  };
}
export async function GET(){
  const url=process.env.FLIGHT_RADAR_FEED_URL||DEFAULT_FEED;
  if(!/^https:\/\//.test(url))return Response.json({connected:false,offers:[],error:"feed_url_invalid"},{status:503});
  try {
    const headers={Accept:"application/json"};
    if(process.env.FLIGHT_RADAR_FEED_TOKEN)headers.Authorization="Bearer "+process.env.FLIGHT_RADAR_FEED_TOKEN;
    const response=await fetch(url,{headers,cache:"no-store",signal:AbortSignal.timeout(8500)});
    if(!response.ok)throw Error("feed_http_"+response.status);
    if(Number(response.headers.get("content-length")||0)>1024*1024)throw Error("oversized_feed");
    const body=await response.text();
    if(body.length>1024*1024)throw Error("oversized_feed");
    return Response.json(parseFeed(JSON.parse(body)),{headers:{"Cache-Control":"public, s-maxage=180, stale-while-revalidate=180"}});
  }catch {
    return Response.json({connected:false,offers:[],error:"feed_temporarily_unavailable"},{status:503,headers:{"Cache-Control":"no-store"}});
  }
}
