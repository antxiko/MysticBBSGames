"""Pagina publica del scoreboard. Sin auth.

Rutas:
  /                          -> landing con stats + lista de juegos
  /leaderboard/{game}        -> top de un juego con tabs week/month/all
"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Annotated

from . import db

router = APIRouter(tags=["public"])

VALID_GAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")

# Juegos que ordenan ASC (menos = mejor). Permite a la UI saber como mostrar.
# Esta lista es solo para presentacion; el server no la usa para nada que afecte
# a la API. Puede vaciarse y todo seguira funcionando.
ASC_GAMES = {"movida", "wordle"}


PAGE_CSS = """
body { background:#0a0a0a; color:#e0e0e0; font-family:'Courier New',Monaco,monospace; padding:2em; max-width:1100px; margin:0 auto; }
h1 { color:#ff66ff; border-bottom:1px solid #ff66ff; padding-bottom:0.3em; letter-spacing:0.05em; }
h2 { color:#66ccff; margin-top:2em; }
a { color:#66ccff; text-decoration:none; }
a:hover { color:#ff99ff; text-decoration:underline; }
table { border-collapse:collapse; margin:1em 0; width:100%; }
th, td { border:1px solid #333; padding:0.5em 1em; text-align:left; vertical-align:middle; }
th { background:#1a1a1a; color:#ffcc66; text-transform:uppercase; font-size:0.85em; letter-spacing:0.1em; }
tr:hover td { background:#141414; }
.stats { display:flex; gap:2em; margin:1em 0; }
.stat { background:#1a1a1a; padding:1em 1.5em; border-left:4px solid #ff66ff; }
.stat .num { font-size:1.8em; color:#ffcc66; font-weight:bold; }
.stat .label { font-size:0.8em; color:#888; text-transform:uppercase; letter-spacing:0.1em; }
.tabs { margin:1em 0; }
.tab { display:inline-block; padding:0.5em 1.2em; background:#1a1a1a; color:#888; text-decoration:none; margin-right:0.3em; border-bottom:2px solid transparent; }
.tab:hover { color:#fff; background:#222; }
.tab.active { color:#ff66ff; border-bottom-color:#ff66ff; background:#0a0a0a; }
.empty { color:#666; font-style:italic; padding:2em; text-align:center; }
.pos { color:#ffcc66; font-weight:bold; }
.pos-1 { color:#ffaa00; font-size:1.1em; }
.pos-2 { color:#cccccc; }
.pos-3 { color:#cd7f32; }
.handle { color:#fff; font-weight:bold; }
.bbs-tag { color:#66ccff; font-size:0.85em; }
.muted { color:#666; font-size:0.85em; }
.logo { color:#ff66ff; font-weight:bold; letter-spacing:0.2em; }
hr { border:0; border-top:1px solid #333; margin:2em 0; }
"""


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{_esc(title)} - BBS Scores</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{PAGE_CSS}</style>
</head>
<body>
<h1><a href="/" style="color:inherit; text-decoration:none"><span class="logo">[BBS SCORES]</span></a> {_esc(title)}</h1>
{body}
<hr>
<p class="muted">Scoreboard global entre BBSes para los juegos de
<a href="https://github.com/antxiko/MysticBBSGames">MysticBBSGames</a>.
API publica: <code>GET /api/scores/&lt;game&gt;?scope=global&period=all|week|month</code>.</p>
</body>
</html>"""


def game_display_name(slug: str) -> str:
    """Nombre legible a partir del slug del juego. Mapeo minimo, transparente."""
    overrides = {
        "balatro": "BBSATRO",
        "dopepython": "DopePython",
        "typepython": "Typespeed",
        "roadfighter": "Road Fighter",
        "puyopuyo": "Puyo Puyo",
        "2048": "2048",
    }
    return overrides.get(slug, slug.capitalize())


def _row_pos_class(i: int) -> str:
    if i == 1:
        return "pos pos-1"
    if i == 2:
        return "pos pos-2"
    if i == 3:
        return "pos pos-3"
    return "pos"


# --- routes ---

@router.get("/", response_class=HTMLResponse)
async def home():
    stats = db.stats_globales()
    games = db.list_games()

    # Para cada juego, top 1 all-time
    cards = []
    for g in games:
        ascending = g in ASC_GAMES
        top = db.top_scores_global(g, limit=1, ascending=ascending, period="all")
        if not top:
            continue
        e = top[0]
        unit = ("turnos" if g == "movida" else
                "intentos" if g == "wordle" else "pts")
        cards.append(f"""<tr>
    <td><a href="/leaderboard/{_esc(g)}/"><b>{_esc(game_display_name(g))}</b></a></td>
    <td><span class="handle">{_esc(e['handle'])}</span><span class="bbs-tag">@{_esc(e['bbs_short_name'])}</span></td>
    <td>{e['score']} {unit}</td>
    <td><a href="/leaderboard/{_esc(g)}/">Ranking &rarr;</a></td>
</tr>""")

    if not cards:
        games_html = '<p class="empty">No hay scores todavia. Ponte a jugar.</p>'
    else:
        games_html = f"""<table>
<tr><th>Juego</th><th>Lider</th><th>Score</th><th></th></tr>
{''.join(cards)}
</table>"""

    body = f"""
<div class="stats">
    <div class="stat"><div class="num">{stats['bbs_activas']}</div><div class="label">BBSes activas</div></div>
    <div class="stat"><div class="num">{stats['juegos']}</div><div class="label">Juegos con scores</div></div>
    <div class="stat"><div class="num">{stats['scores_total']}</div><div class="label">Scores totales</div></div>
</div>

<h2>Top mundial por juego (all-time)</h2>
{games_html}
"""
    return HTMLResponse(page("Ranking", body))


@router.get("/leaderboard/{game}", response_class=HTMLResponse)
@router.get("/leaderboard/{game}/", response_class=HTMLResponse)
async def leaderboard(
    game: str,
    period: Annotated[str, Query(pattern="^(all|week|month)$")] = "all",
):
    if not VALID_GAME_RE.match(game):
        raise HTTPException(400, "invalid game name")

    ascending = game in ASC_GAMES
    rows = db.top_scores_global(game, limit=25, ascending=ascending, period=period)
    name = game_display_name(game)

    # Tabs
    def tab(label: str, val: str) -> str:
        active = "active" if val == period else ""
        return f'<a href="/leaderboard/{_esc(game)}/?period={val}" class="tab {active}">{_esc(label)}</a>'

    tabs_html = (
        f'<div class="tabs">'
        f'{tab("Esta semana", "week")}'
        f'{tab("Este mes", "month")}'
        f'{tab("Todos los tiempos", "all")}'
        f'</div>'
    )

    unit = ("turnos" if game == "movida" else
            "intentos" if game == "wordle" else "pts")

    if not rows:
        period_label = {"week": "esta semana", "month": "este mes", "all": "nunca"}[period]
        table_html = f'<p class="empty">Nadie ha jugado {period_label}.</p>'
    else:
        body_rows = []
        for i, r in enumerate(rows, 1):
            cls = _row_pos_class(i)
            body_rows.append(f"""<tr>
    <td class="{cls}">{i}</td>
    <td><span class="handle">{_esc(r['handle'])}</span><span class="bbs-tag">@{_esc(r['bbs_short_name'])}</span></td>
    <td><b>{r['score']}</b> {unit}</td>
    <td class="muted">{_esc(r['created_at'][:10])}</td>
</tr>""")
        table_html = f"""<table>
<tr><th>Pos</th><th>Jugador</th><th>Score</th><th>Fecha</th></tr>
{''.join(body_rows)}
</table>"""

    body = f"""
<p><a href="/">&larr; Volver al indice</a></p>
{tabs_html}
{table_html}
"""
    return HTMLResponse(page(f"Ranking {name}", body))
