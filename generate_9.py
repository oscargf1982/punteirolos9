#!/usr/bin/env python3
"""
Punteirolos 9.0 — Generador automático
Liga FPL #42303 — Temporada 2026/27
"""
import json, time, urllib.request, base64
from pathlib import Path
from datetime import datetime

LEAGUE_ID = 42303
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
            print(f"  Intento {i+1} fallido: {e}")
            if i < retries - 1: time.sleep(3)
    raise Exception(f"Fallo en {path}")

def main():
    print(f"Punteirolos 9.0 — {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # 1. Clasificación
    print("Clasificacion...")
    sd = fpl(f"/leagues-h2h/{LEAGUE_ID}/standings/")
    teams = sd["standings"]["results"]
    print(f"  {len(teams)} equipos")

    # 2. Partidos H2H
    print("Partidos...")
    all_matches = []
    page = 1
    while True:
        d = fpl(f"/leagues-h2h-matches/league/{LEAGUE_ID}/?page={page}")
        played = [m for m in d["results"] if m["entry_1_points"] + m["entry_2_points"] > 0]
        all_matches.extend(played)
        print(f"  Pagina {page}: {len(played)} partidos")
        if not d["has_next"]: break
        page += 1
        time.sleep(0.5)

    current_gw = max((m["event"] for m in all_matches), default=1)
    print(f"  GW actual: {current_gw}")

    # 3. Chips
    print("Chips...")
    chips_data = {}
    for team in teams:
        entry = team["entry"]
        try:
            hist = fpl(f"/entry/{entry}/history/")
            chips_data[str(entry)] = [
                {"name": c["name"], "event": c["event"]}
                for c in hist.get("chips", [])
            ]
        except:
            chips_data[str(entry)] = []
        time.sleep(0.4)
    print(f"  Chips obtenidos para {len(chips_data)} equipos")

    # 4. Splash
    splash_b64 = ""
    for name in ["splash.png", "splash.jpg"]:
        p = Path(__file__).parent / name
        if p.exists():
            splash_b64 = base64.b64encode(p.read_bytes()).decode()
            print(f"  Splash: {name}")
            break

    # 5. Construir bloques JS
    teams_lines = []
    for t in teams:
        line = (
            f'  {{e:{t["entry"]},'
            f'n:{json.dumps(t["entry_name"], ensure_ascii=False)},'
            f'p:{json.dumps(t["player_name"], ensure_ascii=False)},'
            f'r:{t["rank"]},'
            f'w:{t["matches_won"]},'
            f'd:{t["matches_drawn"]},'
            f'l:{t["matches_lost"]},'
            f'pts:{t["points_for"]}}}'
        )
        teams_lines.append(line)
    teams_js = "const TEAMS=[\n" + ",\n".join(teams_lines) + "\n];"

    match_lines = []
    for m in all_matches:
        match_lines.append(
            f'[{m["entry_1_entry"]},{m["entry_1_points"]},'
            f'{m["entry_2_entry"]},{m["entry_2_points"]},{m["event"]}]'
        )
    matches_js = "const MATCHES=[\n  " + ",\n  ".join(match_lines) + "\n];"

    chips_js = json.dumps(chips_data, ensure_ascii=False)
    last_updated = datetime.now().strftime("%d/%m/%Y %H:%M")

    # 6. Leer template y sustituir
    print("Generando HTML...")
    template_path = Path(__file__).parent / "template.html"
    html = template_path.read_text(encoding="utf-8")

    html = html.replace("%%TEAMS_JS%%",     teams_js)
    html = html.replace("%%MATCHES_JS%%",   matches_js)
    html = html.replace("%%CURRENT_GW%%",   str(current_gw))
    html = html.replace("%%LAST_UPDATED%%", last_updated)
    html = html.replace("%%CHIPS_JS%%",     chips_js)
    html = html.replace("%%SPLASH_B64%%",   splash_b64)

    # Verificar que no quedan placeholders sin sustituir
    remaining = [p for p in ["%%TEAMS_JS%%","%%MATCHES_JS%%","%%CURRENT_GW%%",
                              "%%LAST_UPDATED%%","%%CHIPS_JS%%","%%SPLASH_B64%%"]
                 if p in html]
    if remaining:
        print(f"  AVISO: placeholders sin sustituir: {remaining}")
    else:
        print("  Todos los placeholders sustituidos OK")

    out = Path(__file__).parent / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  index.html generado: {len(html)//1024} KB")
    print("Listo!")

if __name__ == "__main__":
    main()
