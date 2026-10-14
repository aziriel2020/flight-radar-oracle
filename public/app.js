(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const origin = $("#origin"), destination = $("#destination"), departure = $("#departure"), returned = $("#return");
  const form = $("#flight-form"), error = $("#form-error"), offers = $("#offers"), feedState = $("#feed-state");
  const codes = ["LIS","OPO","BCN","MAD","FCO","ATH","RAK","JFK","BKK","NRT"];
  const european = new Set(["LIS","OPO","BCN","MAD","FCO","ATH"]);
  const routeNames = {LIS:"Lisbonne",OPO:"Porto",BCN:"Barcelone",MAD:"Madrid",FCO:"Rome",ATH:"Athènes",RAK:"Marrakech",JFK:"New York",BKK:"Bangkok",NRT:"Tokyo"};
  const fmt = (day) => {
    const yyyy = day.getFullYear(), mm = String(day.getMonth()+1).padStart(2,"0"), dd = String(day.getDate()).padStart(2,"0");
    return yyyy+"-"+mm+"-"+dd;
  };
  const addDays=(date,n)=>{const t=new Date(date.getTime());t.setDate(t.getDate()+n);return t;};
  const today=new Date();
  today.setHours(12,0,0,0);
  departure.min=fmt(today);
  departure.value=fmt(addDays(today,35));
  returned.value=fmt(addDays(today,42));
  returned.min=departure.value;
  $("#year").textContent=String(new Date().getFullYear());

  departure.addEventListener("change",()=> {
    returned.min=departure.value;
    if(returned.value <= departure.value || !returned.value) {
      const d=new Date(departure.value+"T12:00:00");
      if(!Number.isNaN(d.getTime()))returned.value=fmt(addDays(d,7));
    }
  });
  const choiceKey="flight-radar-last-search";
  try {
    const saved=JSON.parse(localStorage.getItem(choiceKey)||"null");
    if(saved && saved.origin && saved.destination) {
      if([...origin.options].some(o=>o.value===saved.origin))origin.value=saved.origin;
      if([...destination.options].some(o=>o.value===saved.destination))destination.value=saved.destination;
    }
  }catch{}

  function search(event) {
    event.preventDefault();
    error.textContent="";
    const from=origin.value;
    let to=destination.value;
    if(to==="ANY") {
      const possible=codes.filter(x=>x!==from);
      to=possible[Math.floor(Math.random()*possible.length)];
      destination.value=to;
    }
    if(from===to){error.textContent="Sélectionne deux aéroports différents.";return;}
    const leave=departure.value, back=returned.value;
    if(!leave || !back || back<=leave || leave<fmt(today)){
      error.textContent="Vérifie tes dates : le retour doit être après le départ.";return;
    }
    try{localStorage.setItem(choiceKey,JSON.stringify({origin:from,destination:to}));}catch{}
    const query="Flights from "+from+" to "+to+" on "+leave+" return "+back+" 1 adult round trip";
    const url="https://www.google.com/travel/flights?hl=fr&curr=EUR&q="+encodeURIComponent(query);
    const win=window.open(url,"_blank","noopener,noreferrer");
    if(!win)window.location.assign(url);
  }
  form.addEventListener("submit",search);
  document.querySelectorAll("[data-destination]").forEach(button=>{
    button.addEventListener("click",()=>{
      destination.value=button.dataset.destination;
      $("#explorer").scrollIntoView({behavior:"smooth"});
      destination.focus({preventScroll:true});
    });
  });
  let available=[],activeFilter="ALL";
  function node(tag,cls,content){
    const x=document.createElement(tag);
    if(cls)x.className=cls;
    if(content!==undefined)x.textContent=String(content);
    return x;
  }
  function showEmpty(message) {
    offers.replaceChildren();
    const box=node("div","empty-state");
    box.append(node("span","empty-symbol","✳"));
    box.append(node("strong","", "AUCUNE OFFRE VÉRIFIÉE POUR LE MOMENT."));
    box.append(node("p","",message || "Les tarifs fiables apparaîtront ici quand la collecte sera opérationnelle. En attendant, recherche des billets directement sur Google Flights."));
    const link=node("a","","Explorer les destinations ↗");
    link.href="#explorer";box.append(link);offers.append(box);
  }
  function render(){
    const data=available.filter(o=>activeFilter==="ALL" || (activeFilter==="EUROPE"?european.has(o.destination):!european.has(o.destination)));
    if(!data.length){showEmpty(activeFilter==="ALL"?"Aucune observation récente n'est publiée actuellement. Le collecteur automatique peut nécessiter plusieurs cycles.":"Aucun tarif observé dans cette catégorie.");return;}
    const grid=node("div","deal-grid");
    for(const offer of data){
      const card=node("article","deal"),route=node("div","deal-route");
      route.append(node("span","",offer.origin+" → "+offer.destination));route.append(node("span","","✈"));card.append(route);
      const pretty=routeNames[offer.destination] || offer.destination;
      card.append(node("div","deal-date",pretty+" · "+offer.departure_date+" — "+offer.return_date));
      const price=node("div","deal-price");
      const num=new Intl.NumberFormat("fr-BE",{maximumFractionDigits:0}).format(offer.price_eur);
      price.append(node("span","",num+" €"));price.append(node("small",""," / prix indicatif"));card.append(price);
      card.append(node("div","deal-date",offer.carrier+(offer.verified?" · Vérifié : ":" · Observé : ")+new Date(offer.checked_at).toLocaleTimeString("fr-BE",{hour:"2-digit",minute:"2-digit"})));
      const footer=node("div","deal-footer");
      const score=node("span","deal-score",offer.potential_deal&&offer.saving_pct>0?"Signal −"+offer.saving_pct+" % (observé)":offer.verified?"Prix revérifié":"Prix observé · à confirmer");footer.append(score);
      if(offer.link && /^https:\/\//.test(offer.link)){
        const link=node("a","","Revérifier le prix ↗");
        link.href=offer.link;link.rel="noopener noreferrer";link.target="_blank";footer.append(link);
      }
      card.append(footer);grid.append(card);
    }
    offers.replaceChildren(grid);
  }
  document.querySelectorAll("[data-filter]").forEach(button=>{
    button.addEventListener("click",()=>{
      activeFilter=button.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach(b=>{
        const active=b===button;
        b.classList.toggle("active",active);
        b.setAttribute("aria-pressed",String(active));
      });render();
    });
  });
  fetch("/api/deals",{cache:"no-store"}).then(async response=>{
    if(!response.ok)throw Error("Service indisponible");
    const payload=await response.json();
    available=Array.isArray(payload.offers)?payload.offers.filter(o=>
      typeof o.origin==="string" && /^[A-Z]{3}$/.test(o.origin) &&
      typeof o.destination==="string" && /^[A-Z]{3}$/.test(o.destination) &&
      Number.isFinite(o.price_eur) && o.price_eur>0 &&
      !Number.isNaN(Date.parse(o.checked_at))
    ):[];
    if(payload.connected){feedState.textContent=payload.status==="ok"?"● Collecte active · prix indicatifs":payload.status==="partial"?"● Collecte partielle · prix indicatifs":payload.status==="not_started"?"● Première collecte en attente":"● Collecteur indisponible";}
    else {feedState.textContent="● Source de tarifs indisponible";}
    render();
  }).catch(()=>{
    feedState.textContent="● Service des tarifs temporairement indisponible";
    showEmpty("La connexion aux prix vérifiés est momentanément indisponible. Tu peux toujours chercher un vol sur Google Flights.");
  });
})();
