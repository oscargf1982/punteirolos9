#!/usr/bin/env python3
"""
Punteirolos 9.0 - Generador automatico
Liga FPL #42303 - Temporada 2026/27
Genera index.html directamente sin template ni placeholders
"""
import json, time, urllib.request, base64, re
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

def build_teams_js(teams):
    lines = []
    for t in teams:
        # Use json.dumps for safe string escaping
        name   = json.dumps(t["entry_name"])
        player = json.dumps(t["player_name"])
        lines.append(
            f'  {{e:{t["entry"]},n:{name},p:{player},'
            f'r:{t["rank"]},w:{t["matches_won"]},d:{t["matches_drawn"]},'
            f'l:{t["matches_lost"]},pts:{t["points_for"]}}}'
        )
    return "const TEAMS=[\n" + ",\n".join(lines) + "\n];"

def build_matches_js(matches):
    lines = [
        f'[{m["entry_1_entry"]},{m["entry_1_points"]},'
        f'{m["entry_2_entry"]},{m["entry_2_points"]},{m["event"]}]'
        for m in matches
    ]
    return "const MATCHES=[\n  " + ",\n  ".join(lines) + "\n];"

def build_chips_js(teams, chips_data):
    parts = []
    for t in teams:
        entry = str(t["entry"])
        chips = chips_data.get(entry, [])
        chip_items = []
        for ch in chips:
            chip_items.append(f'{{name:"{ch["name"]}",event:{ch["event"]}}}')
        chip_list = ",".join(chip_items)
        parts.append(f'  {entry}:[{chip_list}]')
    return "{\n" + ",\n".join(parts) + "\n  }"

def main():
    print(f"Punteirolos 9.0 - {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # 1. Clasificacion
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
        entry = str(team["entry"])
        try:
            hist = fpl(f"/entry/{team['entry']}/history/")
            chips_data[entry] = [
                {"name": c["name"], "event": c["event"]}
                for c in hist.get("chips", [])
            ]
        except Exception as e:
            chips_data[entry] = []
            print(f"  Error chips {team['entry_name']}: {e}")
        time.sleep(0.4)
    print(f"  Chips OK para {len(chips_data)} equipos")

    # 4. Construir bloques JS
    teams_js   = build_teams_js(teams)
    matches_js = build_matches_js(all_matches)
    chips_js   = build_chips_js(teams, chips_data)
    gw_js      = f"const CURRENT_GW={current_gw};"
    updated    = datetime.now().strftime("%d/%m/%Y %H:%M")

    # 5. Leer HTML base (el index.html actual o el html guardado)
    base_path = Path(__file__).parent / "base.html"
    if not base_path.exists():
        print("ERROR: falta base.html en el repo")
        return

    html = base_path.read_text(encoding="utf-8")

    # 6. Reemplazar bloques de datos usando marcadores de linea
    # Reemplazar TEAMS
    html = re.sub(r'const TEAMS=\[[\s\S]*?\];', teams_js, html)
    # Reemplazar MATCHES
    html = re.sub(r'const MATCHES=\[[\s\S]*?\];', matches_js, html)
    # Reemplazar CURRENT_GW
    html = re.sub(r'const CURRENT_GW=\d+;', gw_js, html)
    # Reemplazar CHIPS_USED
    html = re.sub(r'const CHIPS_USED = \{[\s\S]*?\n  \};',
                  f'const CHIPS_USED = {chips_js};', html)
    # Actualizar fecha en hero-sub
    html = re.sub(
        r'Liga #42303 · [^<]+',
        f'Liga #42303 · Actualizado: {updated}',
        html
    )

    # 7. Guardar index.html
    out = Path(__file__).parent / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  index.html generado: {len(html)//1024} KB")
    print("Listo!")

if __name__ == "__main__":
    main()
