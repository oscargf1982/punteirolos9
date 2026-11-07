#!/usr/bin/env python3
"""
Punteirolos 9.0 - Generador automatico
Liga FPL #42303 - Temporada 2026/27
Un solo archivo. Sin templates. Sin placeholders.
Genera index.html con clasificacion, estadisticas y la pestana "La jornada".
"""
import json, time, urllib.request, urllib.error
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

def fpl_optional(path):
    """Peticion tolerante a fallos: devuelve None si el dato aun no existe
    (por ejemplo, los equipos de una jornada no son publicos antes del deadline)."""
    for _ in range(2):
        try:
            req = urllib.request.Request(FPL_BASE + path, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            print(f"  HTTP {e.code} en {path}")
        except Exception as e:
            print(f"  Fallo en {path}: {e}")
        time.sleep(2)
    return None

def js_str(s):
    """Convierte string Python a string JS seguro"""
    return json.dumps(str(s), ensure_ascii=False)

def build_teams_js(teams):
    lines = []
    for t in teams:
        lines.append(
            f'  {{e:{t["entry"]},n:{js_str(t["entry_name"])},p:{js_str(t["player_name"])},'
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
        items = ",".join(f'{{name:{js_str(c["name"])},event:{c["event"]}}}' for c in chips)
        parts.append(f'  {entry}:[{items}]')
    return "{\n" + ",\n".join(parts) + "\n}"

# --- HTML de la pagina (CSS + estructura) -----------------------------------
HTML_TOP = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>Punteirolos 9.0</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --purple:#37003c;--cyan:#00ff87;--pink:#ff2882;
  --bord:rgba(0,255,135,.18);
  --text:#fff;--text2:#d0b0e0;--text3:#9070a0;
  --r:14px;--rs:10px;
}
html{scroll-behavior:smooth;font-size:16px}
body{
  min-height:100vh;
  background:linear-gradient(180deg,#37003c 0%,#1c0028 40%,#0e0018 100%);
  color:var(--text);font-family:'Outfit',sans-serif;
  overflow-x:hidden;
  padding-bottom:calc(70px + env(safe-area-inset-bottom));
}
::-webkit-scrollbar{display:none}
.hero{padding:28px 16px 20px;text-align:center}
.hero-badge{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,var(--cyan),var(--pink));border-radius:50px;padding:6px 18px;font-size:11px;font-family:'Space Mono',monospace;letter-spacing:.15em;text-transform:uppercase;color:#37003c;font-weight:700;margin-bottom:16px}
.hero h1{font-size:42px;font-weight:900;letter-spacing:-.03em;line-height:1;background:linear-gradient(135deg,#fff 0%,var(--cyan) 55%,var(--pink) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:6px}
.hero-sub{color:var(--text3);font-size:13px;font-family:'Space Mono',monospace;margin-bottom:20px}
.live-pill{display:inline-flex;align-items:center;gap:7px;background:rgba(0,255,135,.1);border:1px solid rgba(0,255,135,.3);border-radius:50px;padding:6px 16px;font-size:13px;font-weight:700;color:var(--cyan);font-family:'Space Mono',monospace;margin-bottom:20px}
.live-dot{width:8px;height:8px;background:var(--cyan);border-radius:50%;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}
.hstrip{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:6px}
.hstat{background:rgba(0,255,135,.06);border:1px solid rgba(0,255,135,.15);border-radius:var(--r);padding:16px 12px;text-align:center}
.hstat-icon{font-size:24px;margin-bottom:6px}
.hstat-val{font-size:24px;font-weight:900;font-family:'Space Mono',monospace;color:var(--cyan);line-height:1}
.hstat-lbl{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.07em;margin-top:5px}
.hstat-sub{font-size:13px;color:var(--text2);margin-top:3px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nav{position:fixed;bottom:0;left:0;right:0;z-index:100;background:rgba(28,0,40,.96);border-top:1px solid rgba(0,255,135,.15);backdrop-filter:blur(24px);display:flex;padding-bottom:env(safe-area-inset-bottom)}
.nb{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;padding:10px 2px 8px;cursor:pointer;border:none;background:transparent;color:var(--text3);font-family:'Outfit',sans-serif;font-size:10px;font-weight:600;letter-spacing:.03em;text-transform:uppercase;transition:color .2s;-webkit-tap-highlight-color:transparent}
.nb-icon{font-size:22px;transition:transform .2s}
.nb.on{color:var(--cyan)}
.nb.on .nb-icon{transform:translateY(-2px)}
.panel{display:none;padding:0 16px;animation:fu .25s ease}
.panel.on{display:block}
@keyframes fu{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.stitle{font-size:11px;font-family:'Space Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--cyan);opacity:.8;margin:24px 0 12px;display:flex;align-items:center;gap:10px}
.stitle::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,rgba(0,255,135,.3),transparent)}
.card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r);padding:18px 16px;margin-bottom:12px;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--cyan),var(--pink),transparent)}
.ch{display:flex;align-items:center;gap:10px;margin-bottom:16px}
.ci{font-size:20px}
.ct{font-size:12px;font-family:'Space Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--text3)}
.podium{display:grid;grid-template-columns:1fr 1.08fr 1fr;gap:8px;margin-bottom:16px;align-items:end}
.pod{border-radius:var(--r);padding:20px 10px 16px;text-align:center}
.pod-1{background:linear-gradient(160deg,rgba(0,255,135,.15),rgba(55,0,60,.4));border:1px solid rgba(0,255,135,.4);box-shadow:0 0 30px rgba(0,255,135,.1)}
.pod-2{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12)}
.pod-3{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08)}
.pod-crown{font-size:28px;display:block;margin-bottom:6px}
.pod-name{font-size:13px;font-weight:800;color:#fff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pod-player{font-size:11px;color:var(--text3);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pod-pts{font-size:26px;font-weight:900;font-family:'Space Mono',monospace;margin:10px 0 4px;line-height:1}
.pod-1 .pod-pts{color:var(--cyan)}
.pod-2 .pod-pts{color:#c0c0c0}
.pod-3 .pod-pts{color:#cd7f32}
.pod-rec{font-size:11px;color:var(--text3)}
.srow{display:flex;align-items:center;gap:10px;padding:12px 14px;border-radius:var(--rs);margin-bottom:4px;transition:background .15s}
.srow:active{background:rgba(255,255,255,.04)}
.spos{width:22px;text-align:center;font-size:13px;font-weight:700;color:var(--text3);flex-shrink:0;font-family:'Space Mono',monospace}
.smom{font-size:16px;flex-shrink:0;width:22px;text-align:center}
.sname{flex:1;font-size:15px;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.splayer{font-size:11px;color:var(--text3);margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.srec{font-family:'Space Mono',monospace;font-size:11px;white-space:nowrap;flex-shrink:0;color:var(--text3)}
.spts{font-family:'Space Mono',monospace;font-weight:700;font-size:17px;color:var(--cyan);min-width:36px;text-align:right;flex-shrink:0}
.bar{margin-bottom:14px}
.bar-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.bar-name{font-size:14px;font-weight:700;color:var(--text);max-width:62%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-val{font-size:18px;font-weight:900;font-family:'Space Mono',monospace}
.bar-sub{font-size:11px;color:var(--text3);margin-left:3px}
.bar-track{height:6px;background:rgba(255,255,255,.08);border-radius:3px;overflow:hidden}
.bar-fill{height:100%;border-radius:3px;transition:width .9s cubic-bezier(.4,0,.2,1)}
.rec{border-radius:var(--rs);padding:16px;margin-bottom:10px}
.rec.cyan{background:rgba(0,255,135,.07);border:1px solid rgba(0,255,135,.2)}
.rec.pink{background:rgba(255,40,130,.07);border:1px solid rgba(255,40,130,.2)}
.rec.blue{background:rgba(56,189,248,.06);border:1px solid rgba(56,189,248,.2)}
.rec-lbl{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--text3);margin-bottom:6px;font-family:'Space Mono',monospace}
.rec-val{font-size:24px;font-weight:900;font-family:'Space Mono',monospace}
.rec-sub{font-size:13px;color:var(--text2);margin-top:4px}
.strow{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.05)}
.stname{flex:1;font-size:15px;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.stbadge{font-family:'Space Mono',monospace;font-size:13px;font-weight:700;padding:5px 14px;border-radius:50px;flex-shrink:0}
.stbadge.win{background:rgba(0,255,135,.1);color:var(--cyan);border:1px solid rgba(0,255,135,.25)}
.stbadge.lose{background:rgba(255,40,130,.1);color:var(--pink);border:1px solid rgba(255,40,130,.25)}
.badge-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.badge-card{background:rgba(0,255,135,.04);border:1px solid rgba(0,255,135,.18);border-radius:var(--r);padding:18px 14px;text-align:center}
.badge-icon{font-size:36px;display:block;margin-bottom:8px}
.badge-name{font-size:12px;font-weight:800;color:var(--cyan);text-transform:uppercase;letter-spacing:.05em}
.badge-owner{font-size:14px;color:var(--text);margin-top:4px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.badge-desc{font-size:11px;color:var(--text3);margin-top:3px}
.gw-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r);margin-bottom:12px;overflow:hidden}
.gw-header{background:rgba(0,255,135,.08);padding:12px 16px;font-size:12px;font-family:'Space Mono',monospace;color:var(--cyan);font-weight:700;letter-spacing:.1em}
.match{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;padding:13px 16px;border-bottom:1px solid rgba(255,255,255,.04)}
.match:last-child{border-bottom:none}
.mt{font-size:14px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mt.left{text-align:right}
.mt.right{text-align:left}
.ms{font-family:'Space Mono',monospace;font-size:16px;font-weight:900;text-align:center;white-space:nowrap;padding:0 4px}
.cmp-selects{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px}
.cmp-sel{background:rgba(255,255,255,.08);border:1px solid var(--bord);border-radius:var(--rs);padding:14px 12px;color:var(--text);font-family:'Outfit',sans-serif;font-size:14px;font-weight:700;cursor:pointer;width:100%;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%2300ff87' fill='none' stroke-width='2'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;padding-right:34px}
.cmp-row{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.05)}
.cmp-lbl{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.07em;text-align:center;font-family:'Space Mono',monospace;white-space:nowrap}
.cmp-val{font-size:18px;font-weight:900;font-family:'Space Mono',monospace;text-align:center}
.cmp-val.w{color:var(--cyan)}.cmp-val.l{color:var(--text3)}
.h2h-item{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px}
.narr{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r);padding:20px 16px;margin-bottom:12px}
.narr p{font-size:15px;color:var(--text2);line-height:1.75;margin-bottom:12px}
.narr p:last-child{margin-bottom:0}
.narr strong{color:#fff;font-weight:800}
.headline{display:flex;gap:14px;background:rgba(0,255,135,.04);border:1px solid rgba(0,255,135,.1);border-radius:var(--r);padding:16px;margin-bottom:10px;border-left:4px solid var(--pink)}
.headline.cy{border-left-color:var(--cyan)}
.hl-emoji{font-size:30px;flex-shrink:0;line-height:1}
.hl-title{font-size:16px;font-weight:800;color:#fff;margin-bottom:5px;line-height:1.3}
.hl-sub{font-size:13px;color:var(--text2);line-height:1.5}
.award-row{display:flex;align-items:flex-start;gap:14px;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.05)}
.award-icon{font-size:26px;flex-shrink:0}
.award-lbl{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.07em;font-family:'Space Mono',monospace}
.award-val{font-size:16px;font-weight:800;color:#fff;margin-top:3px}
.award-sub{font-size:12px;color:var(--text3);margin-top:2px}
.chart-wrap{position:relative;height:240px;margin-top:8px}
.match-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r);margin-bottom:10px;overflow:hidden}
.match-card-header{padding:10px 16px;font-size:11px;font-family:'Space Mono',monospace;font-weight:700;letter-spacing:.08em}
.match-card-body{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;padding:14px 16px}
.diana-row{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.05)}
/* ===== LA JORNADA ===== */
.nav{overflow-x:auto}
.nb{flex:1 0 44px;min-width:44px;font-size:9.5px;letter-spacing:0;padding:10px 0 8px}
#jornada-root{max-width:900px;margin:0 auto}
.jmsg{font-size:14px;color:var(--text2);line-height:1.6;padding:2px 2px 12px}
.jmsg b{color:#fff}
.jduel{margin-bottom:14px;border-radius:var(--r);overflow:hidden;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1)}
.jduel>summary,.jsum{list-style:none;cursor:pointer;display:grid;grid-template-columns:1fr auto 1fr 16px;gap:8px;align-items:center;padding:14px;-webkit-tap-highlight-color:transparent}
.jsum{grid-template-columns:1fr auto 1fr;cursor:default}
.jduel>summary::-webkit-details-marker{display:none}
.jduel>summary::after{content:'▾';grid-column:4;color:var(--cyan);font-size:14px;transition:transform .2s}
.jduel[open]>summary::after{transform:rotate(180deg)}
.js-side{min-width:0}
.js-side.r{text-align:right}
.js-nm{font-size:16px;font-weight:900;color:#fff;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.js-tm{font-size:11px;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.js-sc{font-family:'Space Mono',monospace;font-weight:700;font-size:16px;color:var(--text3);white-space:nowrap}
.js-sc b{font-size:22px;color:var(--text2)}
.js-sc b.w{color:var(--cyan)}

.jbody{background:#0b0620}
.jbanner{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:4px;padding:16px 8px 12px;background:radial-gradient(ellipse at 50% 0,#33186e 0,#0b0620 70%)}
.jb{min-width:0;color:#fff;text-align:center;padding:6px 10px 5px;transform:skewX(-7deg)}
.jb>*{transform:skewX(7deg)}
.jb.red{background:linear-gradient(90deg,#a30d1d,#ff3b4a);clip-path:polygon(0 14%,5% 0,100% 8%,96% 100%,2% 90%)}
.jb.blue{background:linear-gradient(90deg,#1e40af,#3b82f6);clip-path:polygon(4% 8%,100% 0,95% 92%,0 100%)}
.jb-n{font-size:24px;font-weight:900;font-style:italic;text-transform:uppercase;letter-spacing:-.02em;line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.jb-t{font-size:10px;font-weight:700;opacity:.9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.jb-c{display:inline-block;margin-top:2px;font-size:10px;font-weight:800;background:rgba(0,0,0,.35);border-radius:20px;padding:1px 8px}
.jb-vs{font-size:28px;font-weight:900;font-style:italic;color:#fff;text-shadow:2px 2px 0 #e11d48,-2px -2px 0 #3b82f6;padding:0 4px}

.jpitches{display:grid;grid-template-columns:1fr;gap:10px;padding-bottom:10px}
.jpl{display:flex;justify-content:space-between;padding:7px 12px;font-size:12px;font-weight:800;text-transform:uppercase;color:#fff;font-family:'Space Mono',monospace}
.jpl.red{background:#a30d1d}
.jpl.blue{background:#1e40af}
.jpitch{position:relative;padding:20px 2px 14px;overflow:hidden;background:linear-gradient(180deg,rgba(255,255,255,.1),rgba(255,255,255,0) 35%,rgba(0,0,0,.12)),repeating-linear-gradient(180deg,#0fa24e 0 46px,#0a8f41 46px 92px);box-shadow:inset 3px 0 0 -1px rgba(255,255,255,.55),inset -3px 0 0 -1px rgba(255,255,255,.55)}
.jpitch::before{content:'';position:absolute;top:0;left:50%;width:66%;height:92px;transform:translateX(-50%);border:2px solid rgba(255,255,255,.75);border-top:0;pointer-events:none}
.jpitch::after{content:'';position:absolute;top:0;left:50%;width:32%;height:36px;transform:translateX(-50%);border:2px solid rgba(255,255,255,.75);border-top:0;pointer-events:none}
.jarc{position:absolute;left:50%;bottom:-70px;width:150px;height:150px;transform:translateX(-50%);border:2px solid rgba(255,255,255,.7);border-radius:50%;pointer-events:none}
.jarc::before{content:'';position:absolute;left:50%;top:-2px;width:300%;height:2px;transform:translateX(-50%);background:rgba(255,255,255,.7)}
.jpitch .jmsg{color:#fff;text-align:center}
.jrow{display:flex;justify-content:space-evenly;align-items:flex-start;margin:12px 0;position:relative;z-index:1}
.jt{position:relative;width:62px;flex:0 0 auto;text-align:center}
.jsv{display:block;width:52px;height:46px;margin:0 auto;filter:drop-shadow(0 2px 2px rgba(0,0,0,.4))}
.jn{background:#fff;color:#1c0028;border-radius:6px;padding:3px 3px 2px;margin:-3px auto 0;max-width:66px;line-height:1.15;position:relative}
.jn b{display:block;font-size:11px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.jn small{display:block;font-size:10px;font-weight:700;color:#5a3a78;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.jn.played{background:#f5f0ff}
.jn.played small{background:#1c0028;color:#fff;border-radius:4px;margin-top:1px}
.jbadge{position:absolute;top:-6px;right:2px;z-index:2;min-width:22px;height:22px;padding:0 3px;border-radius:50%;background:#7c3aed;color:#fff;font-size:12px;font-weight:900;display:flex;align-items:center;justify-content:center;border:2px solid #fff;font-family:'Space Mono',monospace}
.jcap{position:absolute;top:-4px;left:2px;z-index:2;background:#37003c;color:#fff;font-size:10px;font-weight:900;border-radius:9px;min-width:18px;height:18px;padding:0 4px;display:flex;align-items:center;justify-content:center;border:1.5px solid #fff}
.jreprow{display:flex;justify-content:center;gap:8px;flex-wrap:wrap;padding:8px 6px 2px;position:relative;z-index:1}
.jreprow .jt{border:2px dashed rgba(255,255,255,.4);border-radius:10px;padding:6px 2px 4px;background:rgba(0,0,0,.2)}
.jt.jrep{opacity:.55;filter:grayscale(1)}
.jx{position:absolute;top:10px;left:50%;transform:translateX(-50%);font-size:22px;color:#fff;font-weight:900;text-shadow:0 0 3px #000;z-index:2}

.jfoot{display:grid;grid-template-columns:1fr;gap:8px;padding:6px 12px 14px}
.jf{background:#160a3a;border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:10px 12px;font-size:12px;color:var(--text2);line-height:1.6}
.jf b{color:#fff}
.jf small{color:var(--text3)}
.jf .pos{color:var(--cyan);font-family:'Space Mono',monospace;font-size:14px}
.jf .neg{color:var(--pink);font-family:'Space Mono',monospace;font-size:14px}
.jf.mid{text-align:center;font-weight:900;color:#fff;font-size:15px;display:flex;align-items:center;justify-content:center}
.jt:not(.jrep){background:rgba(0,80,30,.38);border:1px solid rgba(0,0,0,.18);border-radius:6px;padding:4px 0 0;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.jt:not(.jrep) .jn{border-radius:0 0 7px 7px;margin:2px 0 0;max-width:none}
.jfichas{display:grid;grid-template-columns:1fr;gap:10px;padding:0 10px 12px}
.jficha{background:#120a33;border:1px solid rgba(255,255,255,.12);border-radius:12px;overflow:hidden}
.jficha>summary{list-style:none;cursor:pointer;padding:10px 12px;font-weight:900;font-size:13px;color:#fff;display:flex;justify-content:space-between;align-items:center;gap:8px;-webkit-tap-highlight-color:transparent}
.jficha.red>summary{border-left:4px solid #ff3b4a}
.jficha.blue>summary{border-left:4px solid #3b82f6}
.jficha>summary::-webkit-details-marker{display:none}
.jficha>summary::after{content:'▾';color:var(--cyan);font-size:13px;transition:transform .2s}
.jficha[open]>summary::after{transform:rotate(180deg)}
.jficha>summary span:first-child{flex:1;min-width:0}
.jpos{font-family:'Space Mono',monospace;color:var(--cyan)}
.jtiles{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;padding:0 10px 8px}
.jtile{background:rgba(255,255,255,.06);border-radius:8px;padding:7px 4px;text-align:center;min-width:0}
.jtile b{display:block;font-family:'Space Mono',monospace;font-size:16px;color:#fff;white-space:nowrap}
.jtile span{display:block;font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.04em;margin-top:2px}
.jlines{padding:0 12px 10px;font-size:13px;color:var(--text2);line-height:1.5}
.jlines>div{padding:6px 0;border-top:1px solid rgba(255,255,255,.07)}
.jlines .k{display:block;font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;font-family:'Space Mono',monospace;margin-bottom:3px}
.jchip{display:inline-block;margin:2px 4px 2px 0;padding:3px 9px;border-radius:20px;background:rgba(255,255,255,.1);font-size:12px;font-weight:700;color:#fff}
.jchip.w{background:rgba(0,255,135,.16);color:var(--cyan)}
.jchip.l{background:rgba(255,40,130,.16);color:var(--pink)}
.jchip.p{background:rgba(255,215,0,.16);color:#ffd700}
.jrec{display:inline-block;margin:2px 4px 2px 0;padding:3px 9px;border-radius:8px;background:rgba(255,215,0,.14);color:#ffd700;font-size:12px;font-weight:700}
@media(min-width:720px){
  .jfichas{grid-template-columns:1fr 1fr}

  .jpitches{grid-template-columns:1fr 1fr}
  .jfoot{grid-template-columns:1.2fr .8fr 1.2fr}
  .jt{width:76px}
  .jsv{width:58px;height:51px}
}
</style>
</head>
<body>
<div class="hero">
  <div class="hero-badge">⚽ Punteirolos 9.0 · 2026/27</div>
  <h1>PUNTEIROLOS<br>9.0</h1>
  <p class="hero-sub">Liga #42303 · Actualizado: {updated}</p>
  <div class="live-pill"><span class="live-dot"></span>EN CURSO · GW {gw}</div>
  <div class="hstrip" id="hstrip"></div>
</div>

<div class="panel on" id="panel-home">
  <div class="stitle">🏆 Clasificación</div>
  <div class="card"><div class="podium" id="podium"></div><div id="standings"></div></div>
  <div class="stitle">📅 Últimos partidos</div>
  <div id="recent"></div>
</div>
<div class="panel" id="panel-stats">
  <div class="stitle">📊 Puntos</div>
  <div class="card"><div class="ch"><span class="ci">📈</span><span class="ct">Total acumulado</span></div><div id="bar-pts"></div></div>
  <div class="card"><div class="ch"><span class="ci">📉</span><span class="ct">Promedio por jornada</span></div><div id="bar-avg"></div></div>
  <div class="card"><div class="ch"><span class="ci">🎯</span><span class="ct">Mejor jornada individual</span></div><div id="bar-best"></div></div>
  <div class="stitle">⚔️ H2H</div>
  <div class="card"><div class="ch"><span class="ci">😰</span><span class="ct">Victorias por ≤4 puntos</span></div><div id="bar-cw"></div></div>
  <div class="card"><div class="ch"><span class="ci">💥</span><span class="ct">Domadas de +20 puntos</span></div><div id="bar-bw"></div></div>
  <div class="card"><div class="ch"><span class="ci">💔</span><span class="ct">Derrotas por ≤4 puntos</span></div><div id="bar-cl"></div></div>
  <div class="stitle">📋 Récords</div>
  <div id="records"></div>
  <div class="card"><div class="ch"><span class="ci">😵</span><span class="ct">El más gafado</span></div><p style="font-size:13px;color:var(--text3);margin-bottom:14px">Puntos acumulados perdiendo</p><div id="bar-lp"></div></div>
  <div class="stitle">🧮 Matriz todos contra todos</div>
  <div class="card"><div class="ch"><span class="ci">🧮</span><span class="ct">Victorias por puntuación relativa</span></div>
  <p style="font-size:13px;color:var(--text3);margin-bottom:12px">Cada celda: en cuántas jornadas la fila habría ganado a la columna comparando sus puntos de esa jornada (victorias–derrotas). Sin rival fijo: mide quién es mejor de verdad, sin suerte del sorteo.</p>
  <div id="matrix" style="overflow-x:auto"></div></div>
</div>
<div class="panel" id="panel-streaks">
  <div class="stitle">🔥 Rachas</div>
  <div class="card"><div class="ch"><span class="ci">🔥</span><span class="ct">Mejor racha de victorias</span></div><div id="str-win"></div></div>
  <div class="card"><div class="ch"><span class="ci">❄️</span><span class="ct">Peor racha de derrotas</span></div><div id="str-lose"></div></div>
  <div class="stitle">📐 Análisis</div>
  <div class="card"><div class="ch"><span class="ci">🎲</span><span class="ct">% victorias H2H</span></div><div id="bar-wpct"></div></div>
  <div class="card"><div class="ch"><span class="ci">🌪️</span><span class="ct">Más caótico (σ)</span></div><div id="bar-chaos"></div></div>
  <div class="card"><div class="ch"><span class="ci">🍀</span><span class="ct">Suerte — ganó por debajo de la media</span></div><div id="bar-luck"></div></div>
  <div class="card"><div class="ch"><span class="ci">😤</span><span class="ct">Mala suerte — perdió por encima de la media</span></div><div id="bar-unluck"></div></div>
  <div class="card"><div class="ch"><span class="ci">⚖️</span><span class="ct">Balance neto de suerte</span></div><div id="bar-netluck"></div></div>
  <div class="stitle">🏅 Logros</div>
  <div class="badge-grid" id="badges"></div>
</div>
<div class="panel" id="panel-charts">
  <div class="stitle">📈 Posición por jornada</div>
  <div class="card"><div class="chart-wrap"><canvas id="rankChart"></canvas></div></div>
  <div class="stitle">💰 Puntos acumulados</div>
  <div class="card"><div class="chart-wrap"><canvas id="ptsChart"></canvas></div></div>
</div>
<div class="panel" id="panel-compare">
  <div class="stitle">🆚 Cara a cara</div>
  <div class="card">
    <div class="cmp-selects"><select class="cmp-sel" id="cmp1"></select><select class="cmp-sel" id="cmp2"></select></div>
    <div id="cmp-out"></div>
  </div>
</div>
<div class="panel" id="panel-narrative">
  <div class="stitle">📰 La temporada</div>
  <div class="narr" id="narr"></div>
  <div class="stitle">💥 Titulares</div>
  <div id="headlines"></div>
</div>
<div class="panel" id="panel-awards">
  <div class="stitle">🏅 Premios</div>
  <div class="card"><div id="awards"></div></div>
  <div class="stitle">🔥 Partidos TOP</div>
  <p style="font-size:13px;color:var(--text3);margin-bottom:14px">Mayor suma de puntos entre los dos equipos</p>
  <div id="matches-top"></div>
  <div class="stitle">💩 Partidos Brocescos</div>
  <p style="font-size:13px;color:var(--text3);margin-bottom:14px">Menor suma de puntos entre los dos equipos</p>
  <div id="matches-broce"></div>
  <div class="stitle">🎯 Managers en la diana</div>
  <p style="font-size:13px;color:var(--text3);margin-bottom:14px">Managers que han recibido más chips en contra</p>
  <div id="diana"></div>
</div>

<div class="panel" id="panel-jornada">
  <div class="stitle">⚽ La jornada</div>
  <div id="jornada-root"><p class="jmsg">Cargando duelos…</p></div>
</div>

<nav class="nav">
  <button class="nb on" data-p="home"><span class="nb-icon">🏠</span>Inicio</button>
  <button class="nb" data-p="jornada"><span class="nb-icon">⚽</span>Jornada</button>
  <button class="nb" data-p="stats"><span class="nb-icon">📊</span>Stats</button>
  <button class="nb" data-p="streaks"><span class="nb-icon">🔥</span>Rachas</button>
  <button class="nb" data-p="charts"><span class="nb-icon">📈</span>Gráf.</button>
  <button class="nb" data-p="compare"><span class="nb-icon">🆚</span>H2H</button>
  <button class="nb" data-p="narrative"><span class="nb-icon">📰</span>Hist.</button>
  <button class="nb" data-p="awards"><span class="nb-icon">🏅</span>Premios</button>
</nav>

'''

# --- JS principal (estadisticas, graficos, premios...) ----------------------
JS_LOGIC = r'''
// Compute stats
const st={};
TEAMS.forEach(t=>{
  st[t.e]={n:t.n,p:t.p,w:t.w,d:t.d,l:t.l,pts:t.pts,
    cw:0,bw:0,cl:0,hs:0,lp:0,total:0,luck:0,unluck:0,scores:[],res:[]};
});
const byGW={};
MATCHES.forEach(([e1,s1,e2,s2,gw])=>{
  if(!byGW[gw])byGW[gw]=[];
  byGW[gw].push([e1,s1,e2,s2]);
});
let bestM={n:'',v:0,gw:0},worstM={n:'',v:999,gw:0},bigW={w:'',l:'',d:0,gw:0,ws:0,ls:0};
const tight=[];
MATCHES.forEach(([e1,s1,e2,s2,gw])=>{
  const diff=Math.abs(s1-s2);
  const gwMs=byGW[gw]||[];
  const allSc=gwMs.flatMap(m=>[m[1],m[3]]);
  const avg=allSc.reduce((a,b)=>a+b,0)/Math.max(allSc.length,1);
  [[e1,s1,e2,s2],[e2,s2,e1,s1]].forEach(([me,my,,op])=>{
    if(!st[me])return;
    st[me].total++;st[me].scores.push(my);
    if(my>st[me].hs)st[me].hs=my;
    if(my>op){st[me].res.push('W');if(diff<=4)st[me].cw++;if(diff>=20)st[me].bw++;}
    else if(my<op){st[me].res.push('L');if(diff<=4)st[me].cl++;st[me].lp+=my;}
    else st[me].res.push('D');
  });
  if(s1>s2&&s1<avg)st[e1].luck++;
  if(s2>s1&&s2<avg)st[e2].luck++;
  if(s1<s2&&s1>avg)st[e1].unluck++;
  if(s2<s1&&s2>avg)st[e2].unluck++;
  const mx=Math.max(s1,s2),mn=Math.min(s1,s2);
  if(mx>bestM.v)bestM={n:s1>=s2?(st[e1]?.n||''):(st[e2]?.n||''),v:mx,gw};
  if(mn<worstM.v)worstM={n:s1<=s2?(st[e1]?.n||''):(st[e2]?.n||''),v:mn,gw};
  if(diff>bigW.d)bigW={w:s1>s2?(st[e1]?.n||''):(st[e2]?.n||''),l:s1>s2?(st[e2]?.n||''):(st[e1]?.n||''),d:diff,gw,ws:mx,ls:mn};
  if(diff<=4)tight.push({a:st[e1]?.n||'',s1,b:st[e2]?.n||'',s2,diff,gw});
});
function std(a){if(!a.length)return 0;const m=a.reduce((x,y)=>x+y,0)/a.length;return Math.sqrt(a.reduce((x,y)=>x+(y-m)**2,0)/a.length)}
TEAMS.forEach(t=>{st[t.e].std=Math.round(std(st[t.e].scores));st[t.e].avg=st[t.e].total>0?(t.pts/st[t.e].total).toFixed(1):0});
function streaks(){
  const r={};
  TEAMS.forEach(t=>{let bW=0,cW=0,bL=0,cL=0;st[t.e].res.forEach(x=>{if(x==='W'){cW++;bW=Math.max(bW,cW);cL=0}else if(x==='L'){cL++;bL=Math.max(bL,cL);cW=0}else{cW=0;cL=0}});r[t.e]={bW,bL};});
  return r;
}
const STR=streaks();
function mom(e){const r=st[e].res.slice(-3);const w=r.filter(x=>x==='W').length;
  if(w===3)return'🔥';if(w===0&&r.length>=3)return'☠️';if(w>=2)return'📈';return'➡️';}
const sd=(arr,k)=>[...arr].sort((a,b)=>parseFloat(st[b.e][k])-parseFloat(st[a.e][k]));
function bar(name,val,pct,color,sub='',delay=0){
  return `<div class="bar" style="animation-delay:${delay}ms">
    <div class="bar-top"><span class="bar-name" title="${name}">${name}</span>
    <div><span class="bar-val" style="color:${color}">${val}</span>${sub?`<span class="bar-sub">${sub}</span>`:''}
    </div></div>
    <div class="bar-track"><div class="bar-fill" style="width:${Math.min(pct,100)}%;background:${color}"></div></div>
  </div>`;
}
function renderBars(id,items,key,color,sub=''){
  const mx=Math.max(...items.map(t=>parseFloat(st[t.e][key])),1);
  document.getElementById(id).innerHTML=items.slice(0,12).map((t,i)=>
    bar(t.n,st[t.e][key],(parseFloat(st[t.e][key])/mx)*100,color,sub,i*35)).join('');
}

// Hero
const swArr=[...TEAMS].sort((a,b)=>STR[b.e].bW-STR[a.e].bW);
document.getElementById('hstrip').innerHTML=`
  <div class="hstat"><div class="hstat-icon">🏆</div><div class="hstat-val">${TEAMS[0].pts}</div><div class="hstat-lbl">Líder</div><div class="hstat-sub">${TEAMS[0].n}</div></div>
  <div class="hstat"><div class="hstat-icon">🎯</div><div class="hstat-val">${bestM.v}</div><div class="hstat-lbl">Récord GW</div><div class="hstat-sub">${bestM.n} · GW${bestM.gw}</div></div>`;

// Podium
const podOrder=[TEAMS[1],TEAMS[0],TEAMS[2]];
document.getElementById('podium').innerHTML=podOrder.map((t,i)=>`
  <div class="pod pod-${i===1?1:i===0?2:3}">
    <span class="pod-crown">${['🥈','👑','🥉'][i]}</span>
    <div class="pod-name">${t.n}</div><div class="pod-player">${t.p}</div>
    <div class="pod-pts">${t.pts}</div>
    <div class="pod-rec">${t.w}V ${t.d}E ${t.l}D</div>
  </div>`).join('');

// Standings
document.getElementById('standings').innerHTML=TEAMS.slice(3).map((t,i)=>`
  <div class="srow">
    <span class="spos">${i+4}</span><span class="smom">${mom(t.e)}</span>
    <div style="flex:1;min-width:0"><div class="sname">${t.n}</div><div class="splayer">${t.p}</div></div>
    <span class="srec"><span style="color:#00ff87">${t.w}V</span> <span style="color:#ff2882">${t.l}D</span></span>
    <span class="spts">${t.pts}</span>
  </div>`).join('');

// Recent matches
document.getElementById('recent').innerHTML=[...new Set(MATCHES.map(m=>m[4]))].sort((a,b)=>b-a).slice(0,2).map(gw=>`
  <div class="gw-card">
    <div class="gw-header">⚽ JORNADA ${gw}</div>
    ${(byGW[gw]||[]).map(([e1,s1,e2,s2])=>{
      const n1=st[e1]?.n||'',n2=st[e2]?.n||'';
      const wl=s1>s2?'left':s1<s2?'right':'draw';
      const c1=wl==='left'?'var(--cyan)':wl==='right'?'var(--text3)':'#aaa';
      const c2=wl==='right'?'var(--cyan)':wl==='left'?'var(--text3)':'#aaa';
      return `<div class="match">
        <span class="mt left" style="color:${c1};font-weight:${wl==='left'?800:600}">${n1}</span>
        <span class="ms"><span style="color:${c1}">${s1}</span>–<span style="color:${c2}">${s2}</span></span>
        <span class="mt right" style="color:${c2};font-weight:${wl==='right'?800:600}">${n2}</span>
      </div>`;
    }).join('')}
  </div>`).join('');

// Stats
const ptMax=Math.max(...TEAMS.map(t=>t.pts));
document.getElementById('bar-pts').innerHTML=[...TEAMS].sort((a,b)=>b.pts-a.pts).map((t,i)=>bar(t.n,t.pts,(t.pts/ptMax)*100,'#00ff87','pts',i*35)).join('');
const avArr=[...TEAMS].sort((a,b)=>parseFloat(st[b.e].avg)-parseFloat(st[a.e].avg));
const avMx=parseFloat(st[avArr[0].e].avg);
document.getElementById('bar-avg').innerHTML=avArr.map((t,i)=>bar(t.n,st[t.e].avg,(parseFloat(st[t.e].avg)/avMx)*100,'#00e87a','pts/GW',i*35)).join('');
renderBars('bar-best',sd(TEAMS,'hs'),'hs','#ff2882','pts');
renderBars('bar-cw',sd(TEAMS,'cw'),'cw','#00ff87','partidos');
renderBars('bar-bw',sd(TEAMS,'bw'),'bw','#ff2882','domadas');
renderBars('bar-cl',sd(TEAMS,'cl'),'cl','#ff2882','partidos');
renderBars('bar-lp',sd(TEAMS,'lp'),'lp','#ff2882','pts');
document.getElementById('records').innerHTML=`
  <div class="rec cyan"><div class="rec-lbl">🏅 Mayor puntuación en una jornada</div><div class="rec-val" style="color:var(--cyan)">${bestM.v} pts</div><div class="rec-sub">${bestM.n} · GW${bestM.gw}</div></div>
  <div class="rec pink"><div class="rec-lbl">😬 Menor puntuación en una jornada</div><div class="rec-val" style="color:var(--pink)">${worstM.v} pts</div><div class="rec-sub">${worstM.n} · GW${worstM.gw}</div></div>
  <div class="rec blue"><div class="rec-lbl">💥 MAYOR DOMADA</div><div class="rec-val" style="color:#38bdf8">+${bigW.d} pts</div><div class="rec-sub">${bigW.w} ${bigW.ws}–${bigW.ls} ${bigW.l} · GW${bigW.gw}</div></div>`;


// Matriz todos contra todos (puntuacion relativa por jornada)
(function(){
  const sc={};
  TEAMS.forEach(t=>{sc[t.e]={};});
  MATCHES.forEach(([e1,s1,e2,s2,gw])=>{
    if(!(s1>0||s2>0)) return;
    if(sc[e1]) sc[e1][gw]=s1;
    if(sc[e2]) sc[e2][gw]=s2;
  });
  const T=[...TEAMS];
  const W={},cell={};
  T.forEach(a=>{W[a.e]={w:0,d:0,l:0};cell[a.e]={};});
  T.forEach(a=>T.forEach(b=>{
    if(a.e===b.e) return;
    let w=0,d=0,l=0;
    Object.keys(sc[a.e]).forEach(g=>{
      const y=sc[b.e][g]; if(y===undefined) return;
      const x=sc[a.e][g];
      if(x>y) w++; else if(x<y) l++; else d++;
    });
    cell[a.e][b.e]={w,d,l};
    W[a.e].w+=w;W[a.e].d+=d;W[a.e].l+=l;
  }));
  T.sort((a,b)=>(W[b.e].w-W[b.e].l)-(W[a.e].w-W[a.e].l)||W[b.e].w-W[a.e].w);
  const ab=n=>String(n).slice(0,3).toUpperCase();
  let h='<table style="border-collapse:collapse;font-size:11px;min-width:100%;text-align:center">';
  h+='<tr><th style="text-align:left;padding:4px 6px;position:sticky;left:0;background:var(--bg,#1a0a2e)"></th>'+T.map(t=>'<th style="padding:4px 3px;color:var(--text3)" title="'+t.n+'">'+ab(t.n)+'</th>').join('')+'<th style="padding:4px 6px;color:var(--cyan)">V-E-D</th></tr>';
  T.forEach(a=>{
    h+='<tr><td style="text-align:left;padding:5px 6px;font-weight:700;white-space:nowrap;position:sticky;left:0;background:var(--bg,#1a0a2e)">'+a.n+'</td>';
    T.forEach(b=>{
      if(a.e===b.e){h+='<td style="background:rgba(255,255,255,.05)">·</td>';return;}
      const c=cell[a.e][b.e];
      const col=c.w>c.l?'rgba(0,255,135,.2)':c.w<c.l?'rgba(255,40,130,.2)':'rgba(255,255,255,.08)';
      h+='<td style="padding:5px 3px;background:'+col+';font-family:Space Mono,monospace">'+c.w+'–'+c.l+'</td>';
    });
    const r=W[a.e];
    h+='<td style="padding:5px 6px;font-weight:800;color:var(--cyan);font-family:Space Mono,monospace;white-space:nowrap">'+r.w+'-'+r.d+'-'+r.l+'</td></tr>';
  });
  h+='</table>';
  document.getElementById('matrix').innerHTML=h;
})();

// Streaks
document.getElementById('str-win').innerHTML=[...TEAMS].sort((a,b)=>STR[b.e].bW-STR[a.e].bW).map(t=>`
  <div class="strow"><span class="stname">${t.n}<br><span style="font-size:11px;color:var(--text3);font-weight:400">${t.p}</span></span>
  <span class="stbadge win">🔥 ${STR[t.e].bW} seguidas</span></div>`).join('');
document.getElementById('str-lose').innerHTML=[...TEAMS].sort((a,b)=>STR[b.e].bL-STR[a.e].bL).map(t=>`
  <div class="strow"><span class="stname">${t.n}<br><span style="font-size:11px;color:var(--text3);font-weight:400">${t.p}</span></span>
  <span class="stbadge lose">💀 ${STR[t.e].bL} seguidas</span></div>`).join('');
const wpArr=[...TEAMS].sort((a,b)=>(b.w/(b.w+b.d+b.l))-(a.w/(a.w+a.d+a.l)));
document.getElementById('bar-wpct').innerHTML=wpArr.map((t,i)=>{const p=Math.round(t.w/(t.w+t.d+t.l)*100);return bar(t.n,p+'%',p,i===0?'#00ff87':'#ff2882','',i*35)}).join('');
const stdArr=[...TEAMS].sort((a,b)=>st[b.e].std-st[a.e].std);
const stdMx=st[stdArr[0].e].std;
document.getElementById('bar-chaos').innerHTML=stdArr.map((t,i)=>bar(t.n,st[t.e].std,(st[t.e].std/stdMx)*100,'#ff2882','σ',i*35)).join('');
const lkArr=[...TEAMS].sort((a,b)=>st[b.e].luck-st[a.e].luck);
const lkMx=Math.max(...TEAMS.map(t=>st[t.e].luck),1);
document.getElementById('bar-luck').innerHTML=lkArr.map((t,i)=>bar(t.n,st[t.e].luck,(st[t.e].luck/lkMx)*100,'#00ff87','victorias con suerte',i*35)).join('');
const ulArr=[...TEAMS].sort((a,b)=>st[b.e].unluck-st[a.e].unluck);
const ulMx=Math.max(...TEAMS.map(t=>st[t.e].unluck),1);
document.getElementById('bar-unluck').innerHTML=ulArr.map((t,i)=>bar(t.n,st[t.e].unluck,(st[t.e].unluck/ulMx)*100,'#ff2882','derrotas con mala suerte',i*35)).join('');
const netArr=[...TEAMS].map(t=>Object.assign({},t,{net:st[t.e].luck-st[t.e].unluck})).sort((a,b)=>b.net-a.net);
const netMx=Math.max(...netArr.map(t=>Math.abs(t.net)),1);
document.getElementById('bar-netluck').innerHTML=netArr.map((t,i)=>{const v=t.net;const color=v>0?'#00ff87':v<0?'#ff2882':'#888';return bar(t.n,v>0?'+'+v:String(v),(Math.abs(v)/netMx)*100,color,'balance',i*35)}).join('');

// Badges
const cArr=[...TEAMS].filter(t=>st[t.e].total>=2).sort((a,b)=>st[a.e].std-st[b.e].std);
document.getElementById('badges').innerHTML=[
  {i:'👑',n:'Líder',o:TEAMS[0].n,d:`${TEAMS[0].pts} pts`},
  {i:'🎯',n:'Cañonero',o:sd(TEAMS,'pts')[0].n,d:'Más puntos totales'},
  {i:'😰',n:'Rey del susto',o:sd(TEAMS,'cw')[0].n,d:`${st[sd(TEAMS,'cw')[0].e].cw} victorias ≤4 pts`},
  {i:'💥',n:'Aplastador',o:sd(TEAMS,'bw')[0].n,d:`${st[sd(TEAMS,'bw')[0].e].bw} domadas +20`},
  {i:'🔥',n:'En racha',o:swArr[0].n,d:`${STR[swArr[0].e].bW} victorias seguidas`},
  {i:'🍀',n:'Más suerte',o:lkArr[0].n,d:`${st[lkArr[0].e].luck} victorias bajo la media`},
  {i:'😤',n:'Más gafado',o:ulArr[0].n,d:`${st[ulArr[0].e].unluck} derrotas sobre la media`},
  {i:'💀',n:'Farolillo',o:TEAMS[TEAMS.length-1].n,d:`${TEAMS[TEAMS.length-1].w}V · ${TEAMS[TEAMS.length-1].pts} pts`},
].map(b=>`<div class="badge-card"><span class="badge-icon">${b.i}</span><div class="badge-name">${b.n}</div><div class="badge-owner">${b.o}</div><div class="badge-desc">${b.d}</div></div>`).join('');

// Charts
let chartsOK=false;
function buildCharts(){
  chartsOK=true;
  const gws=Object.keys(byGW).map(Number).sort((a,b)=>a-b);
  const cum={};TEAMS.forEach(t=>{cum[t.e]=[]});
  const run={};TEAMS.forEach(t=>{run[t.e]=0});
  gws.forEach(gw=>{
    (byGW[gw]||[]).forEach(([e1,s1,e2,s2])=>{run[e1]=(run[e1]||0)+s1;run[e2]=(run[e2]||0)+s2});
    TEAMS.forEach(t=>{cum[t.e].push(run[t.e]||0)});
  });
  const rankByGW={};TEAMS.forEach(t=>{rankByGW[t.e]=[]});
  gws.forEach((gw,gi)=>{
    const snap=TEAMS.map(t=>{const o={};o.e=t.e;o.p=cum[t.e][gi]||0;return o;}).sort((a,b)=>b.p-a.p);
    snap.forEach((s,ri)=>{rankByGW[s.e].push(ri+1)});
  });
  const pal=['#00ff87','#ff2882','#38bdf8','#ffd700','#c084fc','#fb923c','#4ade80','#f472b6','#60a5fa','#facc15','#34d399','#ff6b35','#818cf8','#a3e635','#67e8f9','#d946ef','#fdba74','#10b981','#fb7185','#38bdf8'];
  const labels=gws.map(g=>`GW${g}`);
  const base={responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#9070a0',font:{size:10},boxWidth:10,padding:8}}},scales:{x:{ticks:{color:'#9070a0',maxTicksLimit:8,maxRotation:0},grid:{color:'rgba(0,255,135,.05)'}},y:{ticks:{color:'#9070a0'},grid:{color:'rgba(0,255,135,.05)'}}}}
  new Chart(document.getElementById('rankChart'),{type:'line',data:{labels,datasets:TEAMS.slice(0,8).map((t,i)=>({label:t.n,data:rankByGW[t.e],borderColor:pal[i],backgroundColor:'transparent',borderWidth:2,pointRadius:2,tension:.35}))},options:{...base,scales:{...base.scales,y:{...base.scales.y,reverse:true,min:1,max:20}}}})
  new Chart(document.getElementById('ptsChart'),{type:'line',data:{labels,datasets:TEAMS.slice(0,6).map((t,i)=>({label:t.n,data:cum[t.e],borderColor:pal[i],backgroundColor:pal[i]+'12',borderWidth:2,pointRadius:2,tension:.35,fill:false}))},options:base})
}

// Comparador
let cmpOK=false;
function buildCmp(){
  cmpOK=true;
  ['cmp1','cmp2'].forEach((id,idx)=>{
    document.getElementById(id).innerHTML=TEAMS.map((t,i)=>`<option value="${t.e}" ${i===idx?'selected':''}>${t.n}</option>`).join('');
  });
  renderCmp();
  document.getElementById('cmp1').addEventListener('change',renderCmp);
  document.getElementById('cmp2').addEventListener('change',renderCmp);
}
function renderCmp(){
  const e1=parseInt(document.getElementById('cmp1').value),e2=parseInt(document.getElementById('cmp2').value);
  const t1=TEAMS.find(t=>t.e===e1),t2=TEAMS.find(t=>t.e===e2);
  if(!t1||!t2||e1===e2){document.getElementById('cmp-out').innerHTML='<p style="text-align:center;color:var(--text3);padding:20px">Selecciona dos equipos distintos</p>';return}
  const s1=st[e1],s2=st[e2];
  const h2hMs=MATCHES.filter(m=>(m[0]===e1&&m[2]===e2)||(m[0]===e2&&m[2]===e1));
  let hw1=0,hw2=0;
  h2hMs.forEach(([a,sa,b,sb])=>{a===e1?(sa>sb?hw1++:sb>sa?hw2++:0):(sb>sa?hw1++:sa>sb?hw2++:0)});
  function row(l,v1,v2,hi=true){
    const w1=hi?parseFloat(v1)>parseFloat(v2):parseFloat(v1)<parseFloat(v2);
    const w2=hi?parseFloat(v2)>parseFloat(v1):parseFloat(v2)<parseFloat(v1);
    return `<div class="cmp-row"><div class="cmp-val ${w1?'w':w2?'l':''}" style="text-align:right">${v1}</div><div class="cmp-lbl">${l}</div><div class="cmp-val ${w2?'w':w1?'l':''}">${v2}</div></div>`;
  }
  document.getElementById('cmp-out').innerHTML=`
    <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:8px;margin-bottom:18px;padding:14px 12px;background:rgba(0,255,135,.06);border-radius:var(--rs)">
      <div style="text-align:right"><div style="font-size:15px;font-weight:800;color:#fff">${t1.n}</div><div style="font-size:12px;color:var(--text3);margin-top:2px">${t1.p}</div></div>
      <div style="font-size:22px;align-self:center">🆚</div>
      <div><div style="font-size:15px;font-weight:800;color:#fff">${t2.n}</div><div style="font-size:12px;color:var(--text3);margin-top:2px">${t2.p}</div></div>
    </div>
    ${row('Posición',t1.r,t2.r,false)}${row('Victorias',t1.w,t2.w)}${row('Puntos',t1.pts,t2.pts)}
    ${row('Promedio',s1.avg,s2.avg)}${row('Mejor jornada',s1.hs,s2.hs)}${row('Consist. σ',s1.std,s2.std,false)}
    <div style="margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,.06)">
      <div style="font-size:9px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;font-family:'Space Mono',monospace">H2H directo (${h2hMs.length} partidos)</div>
      <div style="display:flex;justify-content:center;gap:24px;margin-bottom:16px;align-items:center">
        <span style="font-size:32px;font-weight:900;font-family:'Space Mono',monospace;color:${hw1>hw2?'var(--cyan)':'var(--text3)'}">${hw1}</span>
        <span style="color:var(--text3)">–</span>
        <span style="font-size:32px;font-weight:900;font-family:'Space Mono',monospace;color:${hw2>hw1?'var(--cyan)':'var(--text3)'}">${hw2}</span>
      </div>
      ${h2hMs.map(([a,sa,b,sb,gw])=>{const my=a===e1?sa:sb,op=a===e1?sb:sa,res=my>op?'🟢':my<op?'🔴':'🟡';
        return `<div class="h2h-item"><span style="color:var(--text3);font-family:'Space Mono',monospace;font-size:12px">GW${gw}</span><span>${res} <b style="color:#fff">${t1.n}</b> <span style="font-family:'Space Mono',monospace;font-weight:700;color:${my>op?'var(--cyan)':my<op?'var(--pink)':'#aaa'}">${my}–${op}</span> <b style="color:#fff">${t2.n}</b></span></div>`;
      }).join('')}
    </div>`;
}

// Narrative
const cm=tight.sort((a,b)=>a.diff-b.diff)[0];
document.getElementById('narr').innerHTML=`
  <p><strong>${TEAMS[0].n}</strong> (${TEAMS[0].p}) lidera la Punteirolos 9.0 con ${TEAMS[0].pts} puntos tras ${CURRENT_GW-1} jornadas. Solo ${TEAMS[0].pts-TEAMS[1].pts} pts le separan de <strong>${TEAMS[1].n}</strong>.</p>
  <p>El récord es de <strong>${bestM.v} pts</strong> firmado por <strong>${bestM.n}</strong> en la GW${bestM.gw}. La paliza más grande: <strong>${bigW.w}</strong> ganó a <strong>${bigW.l}</strong> por +${bigW.d} pts en GW${bigW.gw}.</p>
  <p>Partido más igualado: <strong>${cm?.a}</strong> vs <strong>${cm?.b}</strong> — ${cm?.diff} pt de diferencia en GW${cm?.gw}. <strong>${TEAMS[TEAMS.length-1].n}</strong> sigue sin ganar ningún partido.</p>`;
document.getElementById('headlines').innerHTML=[
  {i:'👑',c:'cy',t:`${TEAMS[0].n} lidera la liga`,s:`${TEAMS[0].pts} pts, ${TEAMS[0].w}V. Ventaja de ${TEAMS[0].pts-TEAMS[1].pts} pts sobre ${TEAMS[1].n}.`},
  {i:'🎯',c:'',t:`Récord: ${bestM.v} pts en GW${bestM.gw}`,s:`${bestM.n} marcó la mayor puntuación de la temporada.`},
  {i:'💥',c:'',t:`Paliza de +${bigW.d} pts en GW${bigW.gw}`,s:`${bigW.w} venció a ${bigW.l}: ${bigW.ws}–${bigW.ls}.`},
  {i:'😰',c:'',t:`Solo ${cm?.diff} pt entre ${cm?.a} y ${cm?.b}`,s:`El más igualado, en GW${cm?.gw}.`},
  {i:'🔥',c:'cy',t:`${swArr[0].n} con racha de ${STR[swArr[0].e].bW} victorias`,s:`La mejor racha de la temporada.`},
  {i:'💀',c:'',t:`${TEAMS[TEAMS.length-1].n} sin victorias`,s:`${TEAMS[TEAMS.length-1].n} es el único con 0 victorias tras ${CURRENT_GW-1} jornadas.`},
].map(h=>`<div class="headline ${h.c}"><span class="hl-emoji">${h.i}</span><div><div class="hl-title">${h.t}</div><div class="hl-sub">${h.s}</div></div></div>`).join('');

// Awards
document.getElementById('awards').innerHTML=[
  {i:'👑',l:'Líder actual',v:TEAMS[0].n,s:`${TEAMS[0].w}V ${TEAMS[0].d}E ${TEAMS[0].l}D · ${TEAMS[0].pts} pts`},
  {i:'📊',l:'Más puntos acumulados',v:sd(TEAMS,'pts')[0].n,s:`${sd(TEAMS,'pts')[0].pts} pts`},
  {i:'🎯',l:'Récord de jornada',v:sd(TEAMS,'hs')[0].n,s:`${st[sd(TEAMS,'hs')[0].e].hs} pts · GW${bestM.gw}`},
  {i:'😰',l:'Rey del susto',v:sd(TEAMS,'cw')[0].n,s:`${st[sd(TEAMS,'cw')[0].e].cw} victorias ≤4 pts`},
  {i:'💥',l:'Rey de las palizas',v:sd(TEAMS,'bw')[0].n,s:`${st[sd(TEAMS,'bw')[0].e].bw} domadas +20 pts`},
  {i:'💔',l:'Más derrotas ajustadas',v:sd(TEAMS,'cl')[0].n,s:`${st[sd(TEAMS,'cl')[0].e].cl} derrotas ≤4 pts`},
  {i:'🔥',l:'Mejor racha',v:swArr[0].n,s:`${STR[swArr[0].e].bW} victorias consecutivas`},
  {i:'🍀',l:'El más afortunado',v:lkArr[0].n,s:`${st[lkArr[0].e].luck} victorias con suerte`},
  {i:'😤',l:'El más gafado',v:ulArr[0].n,s:`${st[ulArr[0].e].unluck} derrotas con mala suerte`},
  {i:'⚡',l:'Victoria más amplia',v:bigW.w,s:`+${bigW.d} pts vs ${bigW.l} · GW${bigW.gw}`},
  {i:'💀',l:'Farolillo rojo',v:TEAMS[TEAMS.length-1].n,s:`${TEAMS[TEAMS.length-1].w}V · ${TEAMS[TEAMS.length-1].pts} pts`},
].map(a=>`<div class="award-row"><span class="award-icon">${a.i}</span><div style="flex:1;min-width:0"><div class="award-lbl">${a.l}</div><div class="award-val">${a.v}</div><div class="award-sub">${a.s}</div></div></div>`).join('');

// Partidos TOP y Brocescos
(function(){
  const medals=['🥇','🥈','🥉','4️⃣','5️⃣'];
  function matchCard(e1,s1,e2,s2,gw,rank,color){
    const n1=st[e1]?.n||'',n2=st[e2]?.n||'';
    const wl=s1>s2?'left':s1<s2?'right':'draw';
    const c1=wl==='left'?'var(--cyan)':'var(--text3)';
    const c2=wl==='right'?'var(--cyan)':'var(--text3)';
    return `<div class="match-card">
      <div class="match-card-header" style="background:${color}15;color:${color}">${rank} ${s1+s2} pts totales · GW${gw}</div>
      <div class="match-card-body">
        <span style="font-size:14px;font-weight:700;text-align:right;color:${c1};overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${n1}</span>
        <span style="font-family:'Space Mono',monospace;font-size:17px;font-weight:900;text-align:center"><span style="color:${c1}">${s1}</span>–<span style="color:${c2}">${s2}</span></span>
        <span style="font-size:14px;font-weight:700;color:${c2};overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${n2}</span>
      </div>
    </div>`;
  }
  const sorted=[...MATCHES].sort((a,b)=>(b[1]+b[3])-(a[1]+a[3]));
  document.getElementById('matches-top').innerHTML=sorted.slice(0,5).map(([e1,s1,e2,s2,gw],i)=>matchCard(e1,s1,e2,s2,gw,medals[i],'#00ff87')).join('');
  document.getElementById('matches-broce').innerHTML=[...sorted].reverse().slice(0,5).map(([e1,s1,e2,s2,gw],i)=>matchCard(e1,s1,e2,s2,gw,['💩','💩💩','💩💩💩','😴','😴😴'][i],'#ff2882')).join('');
})();

// Managers en la diana
(function(){
  const gwOpp={};
  MATCHES.forEach(([e1,s1,e2,s2,gw])=>{
    if(!gwOpp[gw])gwOpp[gw]={};
    gwOpp[gw][e1]=e2;gwOpp[gw][e2]=e1;
  });
  const received={};
  Object.entries(CHIPS_USED).forEach(([entryStr,chips])=>{
    const entry=parseInt(entryStr);
    chips.forEach(({name,event:gw})=>{
      if(!gwOpp[gw]||gwOpp[gw][entry]===undefined)return;
      const opp=gwOpp[gw][entry];
      if(!received[opp])received[opp]=[];
      const m=MATCHES.find(m=>m[4]===gw&&((m[0]===entry&&m[2]===opp)||(m[0]===opp&&m[2]===entry)));
      if(!m)return;
      const [e1,s1,e2,s2]=m;
      const ws=e1===entry?s1:s2,os=e1===entry?s2:s1;
      received[opp].push({chip:name,user:entry,gw,ws,os});
    });
  });
  const sorted=Object.entries(received).sort((a,b)=>b[1].length-a[1].length);
  if(!sorted.length){
    document.getElementById('diana').innerHTML='<p style="color:var(--text3);font-size:14px;padding:16px">Aún no hay chips usados esta temporada.</p>';
    return;
  }
  document.getElementById('diana').innerHTML=sorted.map(([oppStr,chips])=>{
    const opp=parseInt(oppStr);
    const oppName=st[opp]?.n||oppStr;
    const wins=chips.filter(c=>c.ws>c.os).length;
    const total=chips.length;
    const survived=total-wins;
    const hColor=wins===total?'var(--pink)':wins===0?'var(--cyan)':'#ffd700';
    const hText=wins===total?'No salvó ninguna 😢':wins===0?'¡Las sobrevivió todas! 💪':`Salvó ${survived} de ${total} 😅`;
    return `<div class="card" style="border-color:${hColor}30">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div><div style="font-size:16px;font-weight:800">🎯 ${oppName}</div>
        <div style="font-size:12px;color:var(--text3);margin-top:2px">${total} chip${total>1?'s':''} recibido${total>1?'s':''}</div></div>
        <div style="font-size:12px;font-weight:700;color:${hColor};text-align:right">${hText}</div>
      </div>
      ${chips.map(c=>{
        const chipUser=st[c.user]?.n||c.user;
        const won=c.ws>c.os;
        const cc=CHIP_COLORS[c.chip]||'#888';
        return `<div class="diana-row">
          <div style="background:${cc}20;border:1px solid ${cc}40;border-radius:8px;padding:5px 10px;font-size:12px;font-weight:700;color:${cc};white-space:nowrap;flex-shrink:0">${CHIP_LABELS[c.chip]||c.chip}</div>
          <div style="flex:1;min-width:0;margin-left:4px">
            <div style="font-size:13px;color:var(--text2)"><b style="color:#fff">${chipUser}</b> ${won?'le ganó':'le perdió'} con <b style="font-family:'Space Mono',monospace;color:${won?'var(--pink)':'var(--cyan)'}">${c.ws}–${c.os}</b></div>
            <div style="font-size:11px;color:var(--text3)">GW${c.gw}</div>
          </div>
          <div style="font-size:22px">${won?'❌':'✅'}</div>
        </div>`;
      }).join('')}
    </div>`;
  }).join('');
})();

// Nav
document.querySelectorAll('.nb').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.nb').forEach(b=>b.classList.remove('on'));
    document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));
    btn.classList.add('on');
    document.getElementById('panel-'+btn.dataset.p).classList.add('on');
    if(btn.dataset.p==='charts'&&!chartsOK)buildCharts();
    if(btn.dataset.p==='compare'&&!cmpOK)buildCmp();
    window.scrollTo(0,0);
  });
});'''

# --- JS de la pestana "La jornada" (va en su propio <script>, aislado) ------
JORNADA_JS = r'''(function(){
  const root=document.getElementById('jornada-root');
  if(!root) return;
  try{
    const J=JORNADA;
    const PL=J.players||{}, FX=J.fx||{};
    const T={};TEAMS.forEach(t=>{T[t.e]=t;});
    const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    const fname=e=>T[e]?String(T[e].p).split(' ')[0].toUpperCase():'?';
    const tname=e=>T[e]?T[e].n:'';
    const fmt=n=>n<0?'−'+Math.abs(n):String(n);

    // Equipaciones: b=cuerpo, s=mangas, t=cuello y puños, p=patrón (stripes|pin), q=color del patrón, w=ancho.
    // Solo colores y dibujo de la prenda: sin escudos, patrocinadores ni marcas.
    const CLUB={
      ARS:{b:'#ef0107',s:'#ffffff',t:'#ffffff'}, AVL:{b:'#6c1d45',s:'#95bfe5',t:'#95bfe5'},
      BOU:{b:'#e62333',t:'#111111',p:'stripes',q:'#111111',w:5.5}, BRE:{b:'#e30613',t:'#111111',p:'stripes',q:'#ffffff',w:5.5},
      BHA:{b:'#0057b8',t:'#ffffff',p:'pin',q:'#ffffff',w:1.5}, BUR:{b:'#6c1d45',s:'#99d6ea',t:'#99d6ea'},
      CHE:{b:'#1d4fb8',t:'#ffffff'}, COV:{b:'#5bb8e8',t:'#ffffff'},
      CRY:{b:'#1b458f',t:'#c4122e',p:'stripes',q:'#c4122e',w:5.5}, EVE:{b:'#1f4fb0',t:'#ffffff'},
      FUL:{b:'#ffffff',t:'#111111'}, HUL:{b:'#f5a31a',t:'#111111',p:'stripes',q:'#1a1a1a',w:3.5},
      IPS:{b:'#1747a8',t:'#ffffff'}, LEE:{b:'#ffffff',t:'#f2c200'},
      LEI:{b:'#0b3a9a',t:'#fdbe11'}, LIV:{b:'#b5132b',t:'#f2e9d0'},
      MCI:{b:'#6cabdd',t:'#ffffff',fade:1}, MUN:{b:'#c8102e',s:'#c8102e',t:'#111111'},
      NEW:{b:'#f5f5f5',t:'#111111',p:'stripes',q:'#1a1a1a',w:6}, NFO:{b:'#d90f1a',t:'#ffffff'},
      SOU:{b:'#d71920',t:'#111111',p:'stripes',q:'#ffffff',w:6}, SUN:{b:'#e8222f',t:'#111111',p:'stripes',q:'#ffffff',w:6},
      TOT:{b:'#ffffff',t:'#132257'}, WHU:{b:'#7a263a',s:'#1bb1e7',t:'#1bb1e7'},
      WOL:{b:'#fdb913',t:'#111111'}, WBA:{b:'#122f67',t:'#ffffff',p:'stripes',q:'#ffffff',w:6},
      MID:{b:'#c8102e',t:'#ffffff'}, MIL:{b:'#0a2a6e',t:'#ffffff'}
    };
    // Porteros: manga larga y un color por club
    const GKC=[['#e9ecef','#6b7280'],['#ec4899','#7a1b4d'],['#f5c518','#7a5b00'],['#22c55e','#0f5132'],['#38bdf8','#0b4a6f']];
    const GKCLUB={ARS:['#e9ecef','#6b7280'],BHA:['#ec4899','#7a1b4d'],LEE:['#35c35a','#0f5132'],HUL:['#6b7280','#374151'],
      EVE:['#b5f01c','#4d7c0f'],TOT:['#f0509b','#9d174d'],LIV:['#14532d','#052e16'],FUL:['#38bdf8','#0b4a6f'],
      BRE:['#d8a4f0','#7e22ce'],MCI:['#e8482c','#7f1d1d'],AVL:['#f5c518','#7a5b00']};
    let jid=0;
    // Camiseta realista: hombros con costura, mangas (a veces de otro color), cuello, puños,
    // pliegues, sombra bajo los brazos, trama de tejido y brillo en los hombros
    function jersey(tid,gk){
      const code=(J.tshort||{})[tid]||'';
      let c=CLUB[code];
      if(gk){const g=GKCLUB[code]||GKC[tid%GKC.length]; c={b:g[0],t:g[1]};}
      else if(!c){const h=(tid*47)%360; c={b:'hsl('+h+',65%,48%)',t:'#ffffff'};}
      const B=c.b, S=c.s||c.b, T=c.t||'#fff', id='jc'+(jid++);
      const torso='M20 4 C26 10 38 10 44 4 L50 8 L50 57 Q32 61 14 57 L14 8 Z';
      const slv=gk?'M20 4 L9 8 L-2 44 L9 48 L14 30 L14 8 Z':'M20 4 L9 8 L-1 31 L10 36 L14 27 L14 8 Z';
      const cuff=gk?'M-2.5 45.5 L9.5 49.5':'M-1.5 32.5 L10.5 37.5';
      const mir='translate(64 0) scale(-1 1)';
      let pat='';
      if(c.p==='stripes'){for(let x=-4;x<70;x+=2*c.w) pat+='<rect x="'+x+'" y="0" width="'+c.w+'" height="62" fill="'+c.q+'"/>';}
      if(c.p==='pin'){for(let x=-3;x<70;x+=5) pat+='<rect x="'+x+'" y="0" width="'+c.w+'" height="62" fill="'+c.q+'" opacity=".85"/>';}
      const sl=(x)=>'<g'+(x?' transform="'+mir+'"':'')+'>'
        +(S!==B?'<path d="'+slv+'" fill="'+S+'"/>':'')
        +'<path d="'+cuff+'" stroke="'+T+'" stroke-width="4.4" fill="none"/>'
        +'<path d="M20 4 L9 8 M14 8 L14 27" stroke="rgba(0,0,0,.35)" stroke-width=".8" fill="none"/>'
        +'<path d="M10 14 L4 30" stroke="rgba(0,0,0,.12)" stroke-width="2.5" fill="none"/></g>';
      return '<svg class="jsv" viewBox="-3 0 70 62" aria-hidden="true"><defs>'
        +'<clipPath id="'+id+'c"><path d="'+torso+'"/><path d="'+slv+'"/><path d="'+slv+'" transform="'+mir+'"/></clipPath>'
        +'<linearGradient id="'+id+'g" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".32"/><stop offset=".22" stop-color="#000" stop-opacity="0"/><stop offset=".55" stop-color="#fff" stop-opacity=".1"/><stop offset=".78" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".34"/></linearGradient>'
        +'<linearGradient id="'+id+'v" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".16"/><stop offset=".35" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></linearGradient>'
        +'<linearGradient id="'+id+'f" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".75"/></linearGradient>'
        +'<pattern id="'+id+'t" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="1" fill="#000" opacity=".07"/></pattern></defs>'
        +'<g clip-path="url(#'+id+'c)"><rect x="-3" width="70" height="62" fill="'+B+'"/>'+pat
        +sl(0)+sl(1)
        +'<path d="M20 12 Q18 36 17 56 M44 12 Q46 36 47 56" stroke="rgba(0,0,0,.10)" stroke-width="3" fill="none"/>'
        +'<path d="M32 14 L32 58" stroke="rgba(255,255,255,.07)" stroke-width="5" fill="none"/>'
        +'<rect x="-3" width="70" height="62" fill="url(#'+id+'g)"/><rect x="-3" width="70" height="62" fill="url(#'+id+'v)"/>'
        +(c.fade?'<rect x="-3" y="26" width="70" height="36" fill="url(#'+id+'f)"/>':'')
        +'<rect x="-3" width="70" height="62" fill="url(#'+id+'t)"/>'
        +'<path d="M14 54 Q32 58 50 54" stroke="rgba(0,0,0,.2)" stroke-width="1.2" fill="none"/></g>'
        +'<path d="'+torso+'" fill="none" stroke="rgba(0,0,0,.45)" stroke-width=".9"/>'
        +'<path d="'+slv+'" fill="none" stroke="rgba(0,0,0,.45)" stroke-width=".9"/><path d="'+slv+'" transform="'+mir+'" fill="none" stroke="rgba(0,0,0,.45)" stroke-width=".9"/>'
        +'<path d="M20 4 C26 10 38 10 44 4" fill="none" stroke="'+T+'" stroke-width="3.4" stroke-linecap="round"/>'
        +'<path d="M21.5 5.8 C27 11 37 11 42.5 5.8" fill="none" stroke="rgba(0,0,0,.4)" stroke-width=".8"/>'
        +'<path d="M20.5 3 C26 8 38 8 43.5 3" fill="none" stroke="rgba(255,255,255,.3)" stroke-width=".7"/></svg>';
    }

    // Jugador del once: camiseta + nombre + rival (o "ya jugó" con sus puntos)
    function tile(x){
      const p=PL[x[0]]; if(!p) return '';
      const name=p[0], tid=p[1], pts=p[3];
      const f=FX[tid]||[];
      const started=f.some(m=>m[2]>=1);
      const done=f.length>0&&f.every(m=>m[2]===2);
      let sub;
      if(!f.length) sub='sin partido';
      else if(done) sub='(ya jugó)';
      else if(started) sub='(en juego)';
      else sub=f.map(m=>m[0]+' ('+m[1]+')').join(' · ');
      const cap=x[2]?(x[1]>=3?'3C':'C'):(x[3]?'V':'');
      return '<div class="jt">'
        +(started?'<span class="jbadge">'+pts+'</span>':'')
        +(cap?'<span class="jcap">'+cap+'</span>':'')
        +jersey(tid,x[5]===1)
        +'<div class="jn'+(started?' played':'')+'"><b>'+esc(name)+'</b><small>'+esc(sub)+'</small></div></div>';
    }
    // Jugador repetido (lo tienen los dos): hueco tachado
    function repTile(id){
      const p=PL[id]; if(!p) return '';
      return '<div class="jt jrep">'+jersey(p[1],p[2]===1)+'<span class="jx">✕</span>'
        +'<div class="jn"><b>'+esc(p[0])+'</b></div></div>';
    }

    const xi=pk=>pk.p.filter(x=>x[1]>0);
    const score=(list,pk)=>list.reduce((s,x)=>{const p=PL[x[0]];return s+(p?p[3]*x[1]:0);},0)-(pk.cost||0);
    const chipTag=pk=>{
      const l=(pk&&pk.chip)?(CHIPN[pk.chip]||pk.chip):'';
      return l?'<div class="jb-c">'+esc(l)+'</div>':'';
    };

    function pitch(e,list,common,cls,sc){
      const rows=[1,2,3,4].map(t=>{
        const items=list.filter(x=>x[5]===t).sort((a,b)=>a[4]-b[4]);
        return items.length?'<div class="jrow">'+items.map(tile).join('')+'</div>':'';
      }).join('');
      const rep=common.length?'<div class="jreprow">'+common.map(repTile).join('')+'</div>':'';
      return '<div><div class="jpl '+cls+'"><span>'+esc(fname(e))+'</span><span>'+fmt(sc)+' pts</span></div>'
        +'<div class="jpitch"><i class="jarc"></i>'+(rows||'<p class="jmsg">Sin jugadores distintos</p>')+rep+'</div></div>';
    }

    function foot(a,b,pa,pb,sa,sb,common){
      const names=common.map(id=>PL[id]?esc(PL[id][0]):'').filter(Boolean);
      const line=(e,pk,sc)=>esc(fname(e))+' está en <b class="'+(sc<0?'neg':'pos')+'">'+fmt(sc)+'</b>'
        +(pk.cost>0?' <small>(incluye −'+pk.cost+' por '+pk.hits+' fichaje'+(pk.hits===1?'':'s')+')</small>':'');
      return '<div class="jfoot">'
        +'<div class="jf"><b>Jugadores repetidos</b> (no cuentan en el duelo)<br>'+(names.length?names.join(' · '):'Ninguno')+'</div>'
        +'<div class="jf mid">⚽ Duelo sin repetidos</div>'
        +'<div class="jf">'+line(a,pa,sa)+'<br>'+line(b,pb,sb)+'</div></div>';
    }

    // ---- Datos curiosos del manager (usa las estadísticas que ya calcula la web principal) ----
    const SC=(typeof st!=='undefined')?st:{};
    const STRK=(typeof STR!=='undefined')?STR:{};
    const CHIPS=(typeof CHIPS_USED!=='undefined')?CHIPS_USED:{};
    const CHIPN={wildcard:'Wildcard',freehit:'Free Hit','3xc':'Triple Capitán',bboost:'Bench Boost'};
    const HIST={}, OPP={}, RECV={};
    TEAMS.forEach(t=>{HIST[t.e]=[];RECV[t.e]=[];});
    MATCHES.forEach(m=>{
      const e1=m[0],s1=m[1],e2=m[2],s2=m[3],gw=m[4];
      if(HIST[e1]) HIST[e1].push({gw:gw,my:s1,op:s2,vs:e2});
      if(HIST[e2]) HIST[e2].push({gw:gw,my:s2,op:s1,vs:e1});
      (OPP[gw]=OPP[gw]||{})[e1]=e2; OPP[gw][e2]=e1;
    });
    Object.keys(HIST).forEach(k=>HIST[k].sort((a,b)=>a.gw-b.gw));
    (J.duels||[]).forEach(d=>{(OPP[J.gw]=OPP[J.gw]||{})[d[0]]=d[1]; OPP[J.gw][d[1]]=d[0];});
    const resOf=(e,gw)=>{const h=(HIST[e]||[]).find(x=>x.gw===gw);return h?(h.my>h.op?'W':(h.my<h.op?'L':'D')):'P';};
    // chips recibidos: el rival de cada manager en la jornada en la que usó el chip
    Object.keys(CHIPS).forEach(k=>{
      const u=+k;
      (CHIPS[k]||[]).forEach(c=>{
        const o=(OPP[c.event]||{})[u];
        if(o&&RECV[o]) RECV[o].push({chip:c.name,from:u,gw:c.event,res:resOf(u,c.event)});
      });
    });
    const LEAD=[
      ['hs','Mejor jornada de la liga'],['avg','Mejor promedio por jornada'],['bw','Más domadas (+20)'],
      ['cw','Rey del susto (victorias ≤4)'],['cl','Más derrotas ajustadas (≤4)'],['luck','Más afortunado'],
      ['unluck','Más gafado'],['std','Más caótico']
    ];
    const lead={};
    LEAD.forEach(l=>{lead[l[0]]=Math.max.apply(null,TEAMS.map(t=>parseFloat((SC[t.e]||{})[l[0]])||0));});
    const leadW=Math.max.apply(null,TEAMS.map(t=>(STRK[t.e]||{}).bW||0));
    const leadL=Math.max.apply(null,TEAMS.map(t=>(STRK[t.e]||{}).bL||0));
    const pl=(n,s,p)=>n+' '+(n===1?s:p);
    const RES={W:['ganó','w'],L:['perdió','l'],D:['empató',''],P:['en juego','p']};
    function curStreak(h){
      if(!h.length) return 'sin partidos aún';
      const kind=x=>x.my>x.op?'W':(x.my<x.op?'L':'D');
      const r=kind(h[h.length-1]);
      let n=0;
      for(let i=h.length-1;i>=0;i--){ if(kind(h[i])===r) n++; else break; }
      return r==='W'?pl(n,'victoria seguida','victorias seguidas'):(r==='L'?pl(n,'derrota seguida','derrotas seguidas'):pl(n,'empate seguido','empates seguidos'));
    }
    function ficha(e,cls){
      const t=T[e]; if(!t) return '';
      const s=SC[e]||{}, k=STRK[e]||{bW:0,bL:0}, h=HIST[e]||[];
      const lp=t.w*3+t.d;
      let best=null, worst=null, big=null;
      h.forEach(x=>{
        if(!best||x.my>best.my) best=x;
        if(!worst||x.my<worst.my) worst=x;
        const dd=x.my-x.op;
        if(dd>0&&(!big||dd>big.dd)) big={dd:dd,gw:x.gw,vs:x.vs};
      });
      const used=(CHIPS[e]||[]).map(c=>{
        const r=RES[resOf(e,c.event)];
        return '<span class="jchip '+r[1]+'">'+esc(CHIPN[c.name]||c.name)+' · GW'+c.event+' · '+r[0]+'</span>';
      }).join('');
      // el chip lo usó el rival: si el rival ganó, este manager perdió
      const recv=(RECV[e]||[]).map(c=>{
        const r=c.res==='W'?['perdió','l']:(c.res==='L'?['sobrevivió','w']:(c.res==='D'?['empató','']:['en juego','p']));
        return '<span class="jchip '+r[1]+'">'+esc(CHIPN[c.chip]||c.chip)+' de '+esc(fname(c.from))+' · GW'+c.gw+' · '+r[0]+'</span>';
      }).join('');
      const tags=[];
      LEAD.forEach(l=>{const v=parseFloat(s[l[0]])||0; if(v>0&&v===lead[l[0]]) tags.push(l[1]+(l[0]==='hs'?' ('+v+' pts)':''));});
      if(k.bW>0&&k.bW===leadW) tags.push('Mejor racha de victorias ('+k.bW+')');
      if(k.bL>0&&k.bL===leadL) tags.push('Peor racha de derrotas ('+k.bL+')');
      const tiles=[['#'+t.r,'Posición'],[lp,'Pts liga'],[t.pts,'Pts totales'],[t.w+'-'+t.d+'-'+t.l,'V-E-D'],[s.avg||'–','Media/GW'],[best?best.my:'–','Mejor GW']];
      const line=(label,body)=>'<div><span class="k">'+label+'</span>'+body+'</div>';
      return '<details class="jficha '+cls+'" open><summary><span>Datos curiosos de '+esc(fname(e))+'</span><span class="jpos">#'+t.r+'</span></summary>'
        +'<div class="jtiles">'+tiles.map(x=>'<div class="jtile"><b>'+esc(x[0])+'</b><span>'+x[1]+'</span></div>').join('')+'</div>'
        +'<div class="jlines">'
        +line('Racha',esc(curStreak(h))+' · mejor: '+pl(k.bW,'victoria','victorias')+' · peor: '+pl(k.bL,'derrota','derrotas'))
        +line('Mejor y peor jornada',best?best.my+' pts (GW'+best.gw+') · '+worst.my+' pts (GW'+worst.gw+')':'sin datos')
        +line('Mayor victoria',big?'+'+big.dd+' pts a '+esc(fname(big.vs))+' (GW'+big.gw+')':'aún sin victorias')
        +line('Chips usados',used||'ninguno')
        +line('Chips recibidos',recv||'ninguno')
        +line('Domadas y ajustados','domadas (+20): '+(s.bw||0)+' · victorias ≤4: '+(s.cw||0)+' · derrotas ≤4: '+(s.cl||0))
        +line('Suerte',(s.luck||0)+' victorias con suerte · '+(s.unluck||0)+' derrotas con mala suerte')
        +line('Récords',tags.length?tags.map(x=>'<span class="jrec">'+esc(x)+'</span>').join(''):'sin récords todavía')
        +'</div></details>';
    }

    let html='<p class="jmsg"><b>Jornada '+J.gw+'</b> · datos a '+esc(J.updated)+'.</p>';
    if(J.available){
      html+='<p class="jmsg">Los jugadores que tienen <b>los dos</b> managers en su once no cuentan en el duelo. Marcador orientativo: puntos de los jugadores distintos (con capitán) menos las penalizaciones por fichajes, sin contar suplentes automáticos.</p>';
    }
    if(J.note) html+='<p class="jmsg">'+esc(J.note)+'</p>';
    if(!J.duels.length){
      root.innerHTML=html+'<p class="jmsg">Todavía no hay duelos para esta jornada.</p>';
      return;
    }

    J.duels.forEach((d,i)=>{
      const a=d[0], b=d[1];
      const pa=J.picks[a], pb=J.picks[b];
      const both=!!(pa&&pb);
      let sa=0, sb=0, body='';
      if(both){
        const xa=xi(pa), xb=xi(pb);
        const setA=new Set(xa.map(x=>x[0])), setB=new Set(xb.map(x=>x[0]));
        const common=[...setA].filter(id=>setB.has(id));
        const onlyA=xa.filter(x=>!setB.has(x[0])), onlyB=xb.filter(x=>!setA.has(x[0]));
        sa=score(onlyA,pa); sb=score(onlyB,pb);
        body='<div class="jbody"><div class="jbanner">'
          +'<div class="jb red"><div class="jb-n">'+esc(fname(a))+'</div><div class="jb-t">'+esc(tname(a))+'</div>'+chipTag(pa)+'</div>'
          +'<div class="jb-vs">VS</div>'
          +'<div class="jb blue"><div class="jb-n">'+esc(fname(b))+'</div><div class="jb-t">'+esc(tname(b))+'</div>'+chipTag(pb)+'</div></div>'
          +'<div class="jfichas">'+ficha(a,'red')+ficha(b,'blue')+'</div>'+'<div class="jpitches">'+pitch(a,onlyA,common,'red',sa)+pitch(b,onlyB,common,'blue',sb)+'</div>'
          +foot(a,b,pa,pb,sa,sb,common)+'</div>';
      }
      const mid=both
        ?'<b class="'+(sa>sb?'w':'')+'">'+fmt(sa)+'</b> – <b class="'+(sb>sa?'w':'')+'">'+fmt(sb)+'</b>'
        :'vs';
      const sum='<div class="js-side"><div class="js-nm">'+esc(fname(a))+'</div><div class="js-tm">'+esc(tname(a))+'</div></div>'
        +'<div class="js-sc">'+mid+'</div>'
        +'<div class="js-side r"><div class="js-nm">'+esc(fname(b))+'</div><div class="js-tm">'+esc(tname(b))+'</div></div>';
      if(both) html+='<details class="jduel"'+(i===0?' open':'')+'><summary>'+sum+'</summary>'+body+'</details>';
      else html+='<div class="jduel nodet"><div class="jsum">'+sum+'</div></div>';
    });
    root.innerHTML=html;
  }catch(err){
    console.error(err);
    root.innerHTML='<p class="jmsg">No se pudo dibujar la jornada en este momento.</p>';
  }
})();'''

def es_jugado(m):
    """Un partido H2H esta resuelto si alguien ha ganado, empatado o perdido."""
    return (m["entry_1_win"] + m["entry_1_draw"] + m["entry_1_loss"] +
            m["entry_2_win"] + m["entry_2_draw"] + m["entry_2_loss"]) > 0

def pick_target_gw(bootstrap, fallback):
    """Jornada que muestra 'La jornada': la que esta en juego; si ya termino, la siguiente."""
    if not bootstrap:
        return fallback
    events = bootstrap.get("events", [])
    cur = next((e for e in events if e.get("is_current")), None)
    nxt = next((e for e in events if e.get("is_next")), None)
    if cur and not cur.get("finished"):
        return cur["id"]
    if nxt:
        return nxt["id"]
    return cur["id"] if cur else fallback

def build_jornada(bootstrap, teams, gw_matches, gw, updated):
    info = {
        "gw": gw, "updated": updated, "available": False, "note": "",
        "duels": [[m["entry_1_entry"], m["entry_2_entry"]] for m in gw_matches],
        "picks": {}, "players": {}, "fx": {}, "tshort": {},
    }
    if not bootstrap:
        info["note"] = "No se pudieron leer los datos de FPL en esta actualización."
        return info

    short = {t["id"]: t["short_name"] for t in bootstrap.get("teams", [])}
    elements = {e["id"]: e for e in bootstrap.get("elements", [])}

    # Partidos de la Premier en esa jornada (0 = sin empezar, 1 = en juego, 2 = terminado)
    fixtures = fpl_optional(f"/fixtures/?event={gw}") or []
    for f in fixtures:
        state = 2 if (f.get("finished") or f.get("finished_provisional")) else (1 if f.get("started") else 0)
        info["fx"].setdefault(f["team_h"], []).append([short.get(f["team_a"], "?"), "H", state])
        info["fx"].setdefault(f["team_a"], []).append([short.get(f["team_h"], "?"), "A", state])

    # Onces de cada manager (solo son publicos cuando pasa el deadline de la jornada)
    for t in teams:
        data = fpl_optional(f"/entry/{t['entry']}/event/{gw}/picks/")
        if data is None:
            if not info["picks"]:
                break  # si el primero no existe, aun no son publicos: no insistimos
            continue
        eh = data.get("entry_history") or {}
        info["picks"][t["entry"]] = {
            "chip": data.get("active_chip"),
            "hits": eh.get("event_transfers", 0),
            "cost": eh.get("event_transfers_cost", 0),
            # [jugador, multiplicador, capitan, vice, posicion en el once, tipo (1 POR, 2 DEF, 3 MED, 4 DEL)]
            "p": [[p["element"], p["multiplier"], 1 if p["is_captain"] else 0,
                   1 if p["is_vice_captain"] else 0, p["position"], p["element_type"]]
                  for p in data.get("picks", [])],
        }
        time.sleep(0.3)

    if info["picks"]:
        info["available"] = True
        used = {p[0] for pk in info["picks"].values() for p in pk["p"]}
        for eid in used:
            e = elements.get(eid)
            if e:
                info["players"][eid] = [e["web_name"], e["team"], e["element_type"], e.get("event_points", 0)]
                info["tshort"][e["team"]] = short.get(e["team"], "")
        missing = len(teams) - len(info["picks"])
        if missing:
            info["note"] = f"Faltan los equipos de {missing} manager(s); esos duelos se muestran sin onces."
    else:
        info["note"] = (f"Los equipos de la jornada {gw} se publican cuando pasa el deadline. "
                        "Aquí tienes los emparejamientos; los onces aparecerán en la próxima actualización "
                        "(martes y sábado) o al lanzar el workflow a mano.")
    return info

def generate_html(teams_js, matches_js, gw, chips_js, updated, jornada=None):
    data_js = (
        teams_js + "\n" +
        matches_js + "\n" +
        f"const CURRENT_GW={gw};\n" +
        f"const CHIPS_USED={chips_js};\n" +
        'const CHIP_LABELS={wildcard:"Wildcard \U0001f0cf",freehit:"Free Hit \U0001f193","3xc":"Triple Cap ⚡",bboost:"Bench Boost \U0001f680"};\n' +
        'const CHIP_COLORS={wildcard:"#ffd700",freehit:"#00ff87","3xc":"#ff2882",bboost:"#38bdf8"};\n'
    )
    top = HTML_TOP.replace("{updated}", updated).replace("{gw}", str(gw))
    html = top + "<script>\n" + data_js + JS_LOGIC + "\n</script>\n"

    # Segundo <script>, aislado: si algo fallara aqui, el resto de la web sigue funcionando
    if jornada is None:
        jornada = {"gw": gw, "updated": updated, "available": False, "note": "", "duels": [],
                   "picks": {}, "players": {}, "fx": {}, "tshort": {}}
    payload = json.dumps(jornada, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html += "<script>\nconst JORNADA=" + payload + ";\n" + JORNADA_JS + "\n</script>\n</body>\n</html>"
    return html

def main():
    updated = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"Punteirolos 9.0 - {updated}")

    # 1. Clasificacion
    print("Clasificacion...")
    sd = fpl(f"/leagues-h2h/{LEAGUE_ID}/standings/")
    teams = sd["standings"]["results"]
    print(f"  {len(teams)} equipos")

    # 2. Partidos H2H (guardamos todos; los resueltos alimentan las estadisticas)
    print("Partidos...")
    raw_matches = []
    page = 1
    while True:
        d = fpl(f"/leagues-h2h-matches/league/{LEAGUE_ID}/?page={page}")
        raw_matches.extend(d["results"])
        print(f"  Pagina {page}: {len(d['results'])} partidos")
        if not d["has_next"]: break
        page += 1
        time.sleep(0.5)
    all_matches = [m for m in raw_matches if es_jugado(m)]
    print(f"  Resueltos: {len(all_matches)}")

    # 3. Jornada actual (bootstrap-static)
    bootstrap = None
    try:
        bootstrap = fpl("/bootstrap-static/")
    except Exception as e:
        print(f"  No se pudo leer bootstrap-static: {e}")
    current_gw = max((m["event"] for m in all_matches), default=1)
    if bootstrap:
        events = bootstrap.get("events", [])
        cur = (next((e["id"] for e in events if e.get("is_current")), None)
               or next((e["id"] for e in events if e.get("is_next")), None))
        if cur:
            current_gw = cur
    print(f"  GW actual: {current_gw}")

    # 4. Chips
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
            print(f"  Error {team['entry_name']}: {e}")
        time.sleep(0.4)
    print("  Chips OK")

    # 5. La jornada: duelos con los onces de cada manager
    print("La jornada...")
    target_gw = pick_target_gw(bootstrap, current_gw)
    gw_matches = [m for m in raw_matches if m["event"] == target_gw and m.get("entry_2_entry")]
    jornada = build_jornada(bootstrap, teams, gw_matches, target_gw, updated)
    print(f"  GW{target_gw}: {len(jornada['duels'])} duelos, onces de {len(jornada['picks'])} managers")

    # 6. Generar HTML
    print("Generando HTML...")
    html = generate_html(
        build_teams_js(teams), build_matches_js(all_matches), current_gw,
        build_chips_js(teams, chips_data), updated, jornada,
    )
    out = Path(__file__).parent / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  index.html: {len(html)//1024} KB")
    print("Listo!")

if __name__ == "__main__":
    main()
