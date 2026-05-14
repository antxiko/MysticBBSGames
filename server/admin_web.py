"""Panel web de administracion del scoreboard.

Vive bajo /admin. Auth: HTTP Basic Auth contra la tabla `admin` de la DB.

Para crear/actualizar el password de un admin:
    python -m server.admin set-admin <username>
(se pide la pass por stdin sin echo)
"""
from __future__ import annotations

import re
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import db

router = APIRouter(prefix="/admin", tags=["admin"])
_security = HTTPBasic()

VALID_SHORT_RE = re.compile(r"^[A-Z0-9]{1,16}$")


def check_admin(creds: HTTPBasicCredentials = Depends(_security)):
    """Verifica credenciales contra la DB."""
    row = db.find_admin(creds.username)
    if row is None or not db.verify_password(creds.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": 'Basic realm="BBS Scores Admin"'},
        )
    return row


# --- HTML helpers ---

PAGE_CSS = """
body { background:#0a0a0a; color:#e0e0e0; font-family:'Courier New',Monaco,monospace; padding:2em; max-width:1100px; margin:0 auto; }
h1 { color:#ff66ff; border-bottom:1px solid #ff66ff; padding-bottom:0.3em; letter-spacing:0.05em; }
h2 { color:#66ccff; margin-top:2em; }
a { color:#66ccff; }
table { border-collapse:collapse; margin:1em 0; width:100%; }
th, td { border:1px solid #333; padding:0.5em 1em; text-align:left; vertical-align:middle; }
th { background:#1a1a1a; color:#ffcc66; text-transform:uppercase; font-size:0.85em; letter-spacing:0.1em; }
tr:hover td { background:#141414; }
button, input[type=submit] { background:#ff66ff; color:#000; border:0; padding:0.4em 0.9em; cursor:pointer; font-family:inherit; font-size:0.9em; margin-right:0.3em; }
button:hover, input[type=submit]:hover { background:#ff99ff; }
button.danger { background:#ff3333; color:#fff; }
button.danger:hover { background:#ff6666; }
button.warn { background:#ff9933; color:#000; }
button.ok { background:#66ff66; color:#000; }
input[type=text], input[type=password] { background:#1a1a1a; color:#fff; border:1px solid #444; padding:0.4em 0.6em; font-family:inherit; font-size:1em; }
input[type=text]:focus, input[type=password]:focus { border-color:#ff66ff; outline:none; }
.disabled { color:#666; }
.token { background:#000; color:#66ff66; padding:1em; border:2px dashed #66ff66; word-break:break-all; font-size:1.05em; margin:1em 0; }
.alert-ok { background:#0a2300; border-left:4px solid #66ff66; padding:1em; margin:1em 0; }
.alert-warn { background:#2a1a00; border-left:4px solid #ff9933; padding:1em; margin:1em 0; }
.alert-err { background:#2a0000; border-left:4px solid #ff3333; padding:1em; margin:1em 0; color:#ff9999; }
form { display:inline-block; }
form.block { display:block; margin:1em 0; }
.muted { color:#666; font-size:0.85em; }
.logo { color:#ff66ff; font-weight:bold; letter-spacing:0.2em; }
hr { border:0; border-top:1px solid #333; margin:2em 0; }
"""

def page(title: str, body: str, admin_user: str | None = None) -> str:
    footer = ""
    if admin_user:
        footer = f'<hr><p class="muted">Conectado como <b>{_esc(admin_user)}</b>. ' \
                 f'<a href="/admin/">Volver al panel</a></p>'
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{_esc(title)} - BBS Scores Admin</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<h1><span class="logo">[BBS SCORES]</span> {_esc(title)}</h1>
{body}
{footer}
</body>
</html>"""


def _esc(s: str | None) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


# --- routes ---

@router.get("/", response_class=HTMLResponse)
async def home(admin=Depends(check_admin)):
    bbses = db.list_bbses()
    rows_html = []
    for b in bbses:
        enabled = bool(b["enabled"])
        cnt = db.count_scores_for_bbs(b["id"])
        estado = ('<span style="color:#66ff66">activa</span>'
                  if enabled else '<span class="disabled">DESACTIVADA</span>')
        toggle_action = "disable" if enabled else "enable"
        toggle_label = "Desactivar" if enabled else "Activar"
        toggle_class = "warn" if enabled else "ok"
        short = _esc(b["short_name"])
        rows_html.append(f"""<tr>
    <td><b>{short}</b></td>
    <td>{_esc(b['full_name'])}</td>
    <td>{estado}</td>
    <td>{cnt}</td>
    <td>{_esc(b['created_at'])}</td>
    <td>
        <form method="post" action="/admin/{short}/{toggle_action}">
            <button class="{toggle_class}">{toggle_label}</button>
        </form>
        <form method="post" action="/admin/{short}/rotate" onsubmit="return confirm('Rotar token de {short}? El anterior dejara de funcionar.')">
            <button>Rotar token</button>
        </form>
        <form method="get" action="/admin/{short}/delete">
            <button class="danger">Borrar</button>
        </form>
    </td>
</tr>""")
    table = ("\n".join(rows_html)
             if rows_html else
             '<tr><td colspan="6" class="muted">No hay BBSes registradas todavia.</td></tr>')
    body = f"""
<h2>BBSes registradas</h2>
<table>
    <tr>
        <th>Short</th><th>Nombre completo</th><th>Estado</th><th>Scores</th><th>Creada</th><th>Acciones</th>
    </tr>
    {table}
</table>

<h2>Registrar nueva BBS</h2>
<form method="post" action="/admin/add" class="block">
    <p>
        <label>Short name <span class="muted">(mayusculas y numeros, sin espacios, max 16):</span></label><br>
        <input type="text" name="short_name" required pattern="[A-Za-z0-9]+" maxlength="16">
    </p>
    <p>
        <label>Nombre completo:</label><br>
        <input type="text" name="full_name" maxlength="100" style="width:30em">
    </p>
    <p><input type="submit" value="Crear y generar token"></p>
</form>

<h2>Notas</h2>
<ul>
    <li><b>Desactivar</b>: la BBS deja de aceptar submits pero los scores quedan.</li>
    <li><b>Rotar token</b>: invalida el token actual al instante y genera uno nuevo.
        El SysOp tiene que actualizar su <code>scores_config.json</code>.</li>
    <li><b>Borrar</b>: elimina la BBS Y todos sus scores (cascade). Irreversible.</li>
</ul>
"""
    return page("Panel", body, admin["username"])


@router.post("/add", response_class=HTMLResponse)
async def add_bbs(
    short_name: str = Form(...),
    full_name: str = Form(""),
    admin=Depends(check_admin),
):
    short = short_name.strip().upper()
    if not VALID_SHORT_RE.match(short):
        body = (f'<div class="alert-err">Short name "{_esc(short)}" invalido. '
                f'Solo letras y numeros, max 16 chars.</div>'
                f'<p><a href="/admin/">Volver</a></p>')
        return HTMLResponse(page("Error", body, admin["username"]), status_code=400)
    if db.find_bbs_by_short_name(short):
        body = (f'<div class="alert-err">Ya existe una BBS con short name "{_esc(short)}".</div>'
                f'<p><a href="/admin/">Volver</a></p>')
        return HTMLResponse(page("Error", body, admin["username"]), status_code=409)
    token = secrets.token_urlsafe(32)
    db.insert_bbs(short, full_name.strip() or short, db.hash_token(token))
    body = f"""
<div class="alert-ok">BBS <b>{_esc(short)}</b> registrada correctamente.</div>
<p>Token generado (apuntalo, no se mostrara otra vez):</p>
<div class="token">{_esc(token)}</div>
<div class="alert-warn">Este token solo se muestra aqui. Si se pierde, usa "Rotar token" para generar uno nuevo.</div>
<p>Para configurar la BBS, pasale al SysOp:</p>
<pre>{{
  "server_url": "https://scores.nosignalbbs.com",
  "bbs_short_name": "{_esc(short)}",
  "full_name": "{_esc(full_name or short)}",
  "api_token": "{_esc(token)}",
  "timeout_seconds": 2.0,
  "cache_seconds": 60
}}</pre>
<p><a href="/admin/">Volver al panel</a></p>
"""
    return HTMLResponse(page(f"BBS {short} creada", body, admin["username"]))


@router.post("/{short}/enable", response_class=HTMLResponse)
async def enable(short: str, admin=Depends(check_admin)):
    db.set_bbs_enabled(short.upper(), True)
    return RedirectResponse("/admin/", status_code=303)


@router.post("/{short}/disable", response_class=HTMLResponse)
async def disable(short: str, admin=Depends(check_admin)):
    db.set_bbs_enabled(short.upper(), False)
    return RedirectResponse("/admin/", status_code=303)


@router.post("/{short}/rotate", response_class=HTMLResponse)
async def rotate(short: str, admin=Depends(check_admin)):
    short = short.upper()
    if not db.find_bbs_by_short_name(short):
        raise HTTPException(404, f"BBS '{short}' no existe")
    token = secrets.token_urlsafe(32)
    db.update_bbs_token(short, db.hash_token(token))
    body = f"""
<div class="alert-ok">Token rotado para <b>{_esc(short)}</b>. El anterior queda invalidado.</div>
<div class="token">{_esc(token)}</div>
<div class="alert-warn">Pasale este token nuevo al SysOp por canal seguro. Su <code>scores_config.json</code> tiene que actualizarse con este valor.</div>
<p><a href="/admin/">Volver al panel</a></p>
"""
    return HTMLResponse(page(f"Token rotado: {short}", body, admin["username"]))


@router.get("/{short}/delete", response_class=HTMLResponse)
async def delete_confirm(short: str, admin=Depends(check_admin)):
    short = short.upper()
    bbs = db.find_bbs_by_short_name(short)
    if bbs is None:
        raise HTTPException(404, f"BBS '{short}' no existe")
    cnt = db.count_scores_for_bbs(bbs["id"])
    body = f"""
<div class="alert-warn">Vas a borrar la BBS <b>{_esc(short)}</b> ({_esc(bbs['full_name'])}).</div>
<p>Esto eliminara tambien sus <b>{cnt}</b> scores. La operacion es <b>irreversible</b>.</p>
<form method="post" action="/admin/{_esc(short)}/delete">
    <button class="danger">Si, borrar para siempre</button>
</form>
<form method="get" action="/admin/">
    <button>Cancelar</button>
</form>
"""
    return HTMLResponse(page(f"Borrar BBS {short}", body, admin["username"]))


@router.post("/{short}/delete", response_class=HTMLResponse)
async def delete_do(short: str, admin=Depends(check_admin)):
    ok, scores_count = db.delete_bbs(short.upper())
    if not ok:
        raise HTTPException(404, f"BBS '{short}' no existe")
    body = f"""
<div class="alert-ok">BBS <b>{_esc(short.upper())}</b> eliminada junto con {scores_count} scores.</div>
<p><a href="/admin/">Volver al panel</a></p>
"""
    return HTMLResponse(page(f"BBS {short.upper()} borrada", body, admin["username"]))
