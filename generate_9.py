#!/usr/bin/env python3
"""
Punteirolos 9.0 — Generador automático
Liga FPL #42303 — Temporada 2026/27
Ejecuta: python generate_9.py
Genera: index.html con todos los datos actualizados
"""

import json, time, urllib.request, base64
from pathlib import Path
from datetime import datetime

LEAGUE_ID = 42303
SEASON    = "2026-27"
FPL_BASE  = "https://fantasy.premierleague.com/api"
HEADERS   = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://fantasy.premierleague.com/",
}

def fpl(path, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(FPL_BASE + path, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            print(f"  ⚠ Intento {i+1}: {e}")
            if i < retries - 1: time.sleep(3)
    raise Exception(f"Fallo en {path}")

def main():
    print(f"🚀 Punteirolos 9.0 — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 50)

    # 1. Clasificación
    print("📡 Clasificación...")
    sd = fpl(f"/leagues-h2h/{LEAGUE_ID}/standings/")
    teams = sd["standings"]["results"]
    league_name = sd["league"]["name"]
    print(f"  {league_name} — {len(teams)} equipos")

    # 2. Partidos H2H
    print("📡 Partidos...")
    all_matches = []
    page = 1
    while True:
        d = fpl(f"/leagues-h2h-matches/league/{LEAGUE_ID}/?page={page}")
        played = [m for m in d["results"] if m["entry_1_points"] + m["entry_2_points"] > 0]
        all_matches.extend(played)
        print(f"  Página {page}: {len(played)} partidos")
        if not d["has_next"]: break
        page += 1
        time.sleep(0.5)

    # Jornada actual
    current_gw = max((m["event"] for m in all_matches), default=1)
    print(f"  Jornada actual: GW{current_gw}")

    # 3. Splash image base64
    splash_b64 = ""
    for name in ["splash.png", "splash.jpg"]:
        p = Path(__file__).parent / name
        if p.exists():
            splash_b64 = base64.b64encode(p.read_bytes()).decode()
            print(f"  Splash: {name} ({len(splash_b64)//1024} KB)")
            break

    # 4. Construir JS
    teams_js = "const TEAMS = [\n" + ",\n".join(
        f'  {{e:{t["entry"]},n:{json.dumps(t["entry_name"])},p:{json.dumps(t["player_name"])},'
        f'r:{t["rank"]},w:{t["matches_won"]},d:{t["matches_drawn"]},l:{t["matches_lost"]},'
        f'pts:{t["points_for"]}}}'
        for t in teams
    ) + "\n];"

    matches_js = "const MATCHES = [\n" + ",\n".join(
        f'  [{m["entry_1_entry"]},{m["entry_1_points"]},{m["entry_2_entry"]},{m["entry_2_points"]},{m["event"]}]'
        for m in all_matches
    ) + "\n];"

    gw_js = f"const CURRENT_GW = {current_gw};"
    updated_js = f'const LAST_UPDATED = "{datetime.now().strftime("%d/%m/%Y %H:%M")}";'
    splash_js = f'const SPLASH_B64 = "{splash_b64}";'

    # 5. Generar HTML desde template
    print("📄 Generando HTML...")
    template = Path(__file__).parent / "template.html"
    html = template.read_text(encoding="utf-8")
    html = html.replace("%%TEAMS_JS%%", teams_js)
    html = html.replace("%%MATCHES_JS%%", matches_js)
    html = html.replace("%%CURRENT_GW%%", str(current_gw))
    html = html.replace("%%LAST_UPDATED%%", datetime.now().strftime("%d/%m/%Y %H:%M"))
    html = html.replace("%%SPLASH_B64%%", splash_b64)

    out = Path(__file__).parent / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  ✅ index.html — {len(html)//1024} KB")
    print("🎉 ¡Listo!")

if __name__ == "__main__":
    main()
