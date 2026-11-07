"""Decide si hay que actualizar ahora: solo si hay algun partido de la PL en juego.
Usa los horarios oficiales que da la API de FPL (kickoff_time, UTC). Escribe run=true/false."""
import json, os, urllib.request
from datetime import datetime, timedelta, timezone

def get(path):
    req = urllib.request.Request("https://fantasy.premierleague.com/api/" + path, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=20))

def out(v, why):
    print(f"run={v} ({why})")
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"run={v}\n")

try:
    now = datetime.now(timezone.utc)
    ev = get("bootstrap-static/")["events"]
    gws = [e["id"] for e in ev if e.get("is_current") or e.get("is_next")]
    live = None
    for gw in gws:
        for fx in get(f"fixtures/?event={gw}"):
            k = fx.get("kickoff_time")
            if not k: continue
            ko = datetime.fromisoformat(k.replace("Z", "+00:00"))
            if ko - timedelta(minutes=5) <= now <= ko + timedelta(minutes=140):
                live = k
    if live:
        out("true", f"partido en juego, salida {live}")
    else:
        out("false", "sin partidos en juego")
except Exception as e:
    out("true", f"no se pudo consultar ({e}); se actualiza por seguridad")
