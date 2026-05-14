# BBS Scores - servidor

Servicio FastAPI + SQLite que agrega puntuaciones de los juegos del repo MysticBBSGames
desde varias BBSes. Cada BBS se registra una vez con un token, y luego los juegos
de esa BBS envian scores y consultan los tops global / local.

Incluye:
- **API REST publica + autenticada** para submit y consulta de scores.
- **Panel admin web** en `/admin/` para gestionar BBSes y scores via navegador.
- **Ranking publico web** en `/` y `/leaderboard/<game>/` con filtros temporales.

Demo en vivo: **https://scores.nosignalbbs.com**

## Endpoints

### Publicos (sin auth)

| Metodo | Path | Descripcion |
|--------|------|-------------|
| `GET`  | `/api/health` | Healthcheck |
| `GET`  | `/api/scores/{game}?scope=global&order=desc&period=all&limit=10` | Top N |
| `GET`  | `/api/scores/{game}?scope=bbs&bbs=NOSIGNAL&limit=10` | Top N de una BBS |
| `GET`  | `/api/bbses` | Listar BBSes activas |
| `GET`  | `/` | Landing publica (HTML) con stats + top 1 por juego |
| `GET`  | `/leaderboard/{game}/?period=all\|week\|month` | Top 25 con tabs temporales (HTML) |

`period`: `all` (todo), `week` (ultimos 7 dias), `month` (ultimos 30 dias).
`order`: `desc` (default) o `asc` (para juegos donde menos = mejor: movida, wordle).

### Autenticados con Bearer token de BBS

| Metodo | Path | Descripcion |
|--------|------|-------------|
| `POST` | `/api/scores` | Submit de un score (body con game/handle/score/extra) |

El `bbs_id` se deduce siempre del token, nunca del body (anti spoofing).

### Panel admin web (HTTP Basic Auth)

| Path | Descripcion |
|------|-------------|
| `GET  /admin/` | Listado de BBSes + form de alta + link a scores |
| `POST /admin/add` | Crear BBS (devuelve token one-shot en HTML) |
| `POST /admin/<short>/enable` | Reactivar BBS |
| `POST /admin/<short>/disable` | Desactivar BBS |
| `POST /admin/<short>/rotate` | Rotar token (devuelve uno nuevo) |
| `GET  /admin/<short>/delete` | Confirmacion para borrar |
| `POST /admin/<short>/delete` | Borrar BBS y todos sus scores (cascade) |
| `GET  /admin/scores/?game=X&bbs=Y&handle=Z` | Listar scores con filtros |
| `POST /admin/scores/<id>/delete` | Borrar un score individual |

## Deploy en VPS

Ver [INSTALL_VPS.md](../INSTALL_VPS.md) para guia paso a paso. Resumen:

1. `apt install python3-venv git sqlite3 rsync` (mas nginx/certbot si no usas Caddy).
2. `useradd -r bbs-scores`, clonar repo a `/opt/bbs-scores/repo`.
3. `python3 -m venv venv` + `pip install -r server/requirements.txt`.
4. systemd unit en `bbs-scores.service` (escucha en `127.0.0.1:8765`).
5. **Caddy** (auto-HTTPS) o nginx + certbot delante.
6. `python -m server.admin set-admin <username>` para crear admin del panel.
7. `python -m server.admin add-bbs <SHORT> "<Nombre>"` para registrar la primera BBS.

### Puertos

El servicio FastAPI escucha en `127.0.0.1:8765` por defecto.

## Operacion CLI

```bash
cd /opt/bbs-scores/repo
PYV=/opt/bbs-scores/venv/bin/python
DB=/opt/bbs-scores/data/scores.db
ENV="env BBS_SCORES_DB=$DB"

# Gestion de BBSes
sudo -u bbs-scores $ENV $PYV -m server.admin add-bbs VALAR "Valar BBS"
sudo -u bbs-scores $ENV $PYV -m server.admin list-bbs
sudo -u bbs-scores $ENV $PYV -m server.admin disable-bbs VALAR
sudo -u bbs-scores $ENV $PYV -m server.admin enable-bbs VALAR
sudo -u bbs-scores $ENV $PYV -m server.admin rotate-token VALAR
sudo -u bbs-scores $ENV $PYV -m server.admin delete-bbs VALAR   # pide "SI" para confirmar

# Gestion de admins del panel
sudo -u bbs-scores $ENV $PYV -m server.admin set-admin antxiko   # pide pass sin echo
sudo -u bbs-scores $ENV $PYV -m server.admin list-admin
```

Aunque tambien puedes hacer casi todo desde `/admin/` en el navegador.

## Dev local

```bash
cd /Users/fx-media/Documents/DopePython
python3 -m venv .venv-server && source .venv-server/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --reload --host 127.0.0.1 --port 8765
```

En otra terminal:

```bash
python -m server.admin add-bbs TEST "Test BBS"
python -m server.admin set-admin admin   # te pide pass sin echo
```

Navega a `http://127.0.0.1:8765/` (publico) y `http://127.0.0.1:8765/admin/` (con el admin que creaste).

## Backup

La DB es un solo fichero (`data/scores.db`). Cron diario:

```bash
0 4 * * * sqlite3 /opt/bbs-scores/data/scores.db ".backup /var/backups/scores-$(date +\%F).db"
```

## Identidad

- **BBS**: identificada por `short_name` (mayusculas, ej. `NOSIGNAL`). Cada BBS tiene un token unico (hash SHA-256 almacenado).
- **Admin del panel**: usuario+password (PBKDF2-HMAC-SHA256 con salt, 100k iteraciones).
- **Jugador**: `INICIALES@BBS` (`AGM@NOSIGNAL`). Las iniciales las escribe el jugador, no salen del nombre real de Mystic.
