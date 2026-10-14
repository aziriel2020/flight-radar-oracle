"""Generate copyright-clean, disk-stored 1600x900 destination illustrations.

These are original vector placeholders (not photographic claims). License: own source.
No remote image provider, keys or paid storage needed for two beta testers.
"""
from __future__ import annotations
import argparse
import html
from pathlib import Path

CITIES = {
    "LIS": ("LISBON", "PORTUGAL", "#164f5c", "#66b2ad", "#d8ffad"),
    "OPO": ("PORTO", "PORTUGAL", "#24455d", "#8faac0", "#f6c679"),
    "BCN": ("BARCELONA", "SPAIN", "#704e56", "#f0aa72", "#fee2a5"),
    "MAD": ("MADRID", "SPAIN", "#654e5b", "#cb8da0", "#fbde98"),
    "FCO": ("ROME", "ITALY", "#3d4b63", "#e5a47f", "#f3e0bb"),
    "ATH": ("ATHENS", "GREECE", "#315a76", "#8bcbd0", "#faf5bd"),
    "RAK": ("MARRAKECH", "MOROCCO", "#77443d", "#e4a36c", "#ffe2a9"),
    "JFK": ("NEW YORK", "USA", "#252d59", "#766cac", "#ebbf8f"),
    "BKK": ("BANGKOK", "THAILAND", "#32566a", "#96b6a9", "#ffeeaf"),
    "NRT": ("TOKYO", "JAPAN", "#423c69", "#ae86a7", "#ffbdb2"),
    "BRU": ("BRUSSELS", "BELGIUM", "#35515b", "#7cb7b3", "#ddf4b1"),
    "CRL": ("CHARLEROI", "BELGIUM", "#34515a", "#7cb3a8", "#def0b1"),
    "CDG": ("PARIS", "FRANCE", "#374a6c", "#a6b8cf", "#e7e7c6"),
    "ORY": ("PARIS", "FRANCE", "#374a6c", "#a6b8cf", "#e7e7c6"),
    "AMS": ("AMSTERDAM", "NETHERLANDS", "#355564", "#81c3bc", "#f3e2b0"),
    "EIN": ("EINDHOVEN", "NETHERLANDS", "#355564", "#81c3bc", "#f3e2b0"),
    "LIL": ("LILLE", "FRANCE", "#514763", "#b0abc5", "#ebc49f"),
    "DUS": ("DUSSELDORF", "GERMANY", "#405568", "#9abcb8", "#e9d99f"),
}

def svg(code, name, country, dark, mid, accent):
    city = html.escape(name)
    country = html.escape(country)
    label = html.escape(code)
    buildings = "".join(
        f'<rect x="{x}" y="{510+(i*37)%120}" width="{105+(i*29)%72}" height="390" rx="3" fill="#091c2d" opacity="{0.45+i*.045:.2f}"/>'
        for i, x in enumerate((0,125,270,430,610,790,950,1150,1350,1520))
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900" role="img" aria-label="Illustration graphique de {city}">
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{dark}"/><stop offset=".6" stop-color="{mid}"/><stop offset="1" stop-color="#091c2d"/></linearGradient>
 <radialGradient id="halo"><stop offset="0" stop-color="{accent}" stop-opacity=".8"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>
 <pattern id="dots" width="50" height="50" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#fff" opacity=".17"/></pattern>
</defs>
<rect width="1600" height="900" fill="url(#sky)"/>
<rect width="1600" height="900" fill="url(#dots)"/>
<circle cx="1140" cy="330" r="370" fill="url(#halo)"/>
<circle cx="1140" cy="330" r="167" fill="none" stroke="{accent}" stroke-width="2" opacity=".65"/>
<circle cx="1140" cy="330" r="198" fill="none" stroke="{accent}" stroke-width="1" opacity=".2"/>
<path d="M0 645 C410 580 740 705 1600 562 L1600 900 L0 900Z" fill="#0b2536" opacity=".45"/>
{buildings}
<path d="M0 795 Q730 695 1600 765 L1600 900 L0 900Z" fill="#061521" opacity=".86"/>
<path d="M1015 148 Q1260 240 1430 90" fill="none" stroke="{accent}" stroke-width="3" stroke-dasharray="7 14" opacity=".85"/>
<g font-family="Arial, sans-serif">
 <text x="80" y="94" fill="{accent}" font-size="25" font-weight="bold" letter-spacing="9">FLIGHT / RADAR</text>
 <text x="80" y="635" fill="white" font-size="{82 if len(name)>10 else 116}" font-weight="bold" letter-spacing="-4">{city}</text>
 <text x="85" y="690" fill="{accent}" font-size="33" letter-spacing="12">{country}  /  {label}</text>
 <text x="85" y="832" fill="white" opacity=".65" font-size="20" letter-spacing="5">DISCOVER MORE.  FLY SMARTER.</text>
</g>
</svg>'''

def generate(folder):
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    for code, params in CITIES.items():
        (target / (code + ".svg")).write_text(svg(code, *params), encoding="utf-8")
    return len(CITIES)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="/var/lib/flight-radar/images/destinations")
    args = ap.parse_args()
    print(f"Generated {generate(args.output)} local SVG illustrations")
