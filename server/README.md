# BBS Scores - servidor

Servicio FastAPI + SQLite que agrega puntuaciones de los juegos del repo MysticBBSGames
desde varias BBSes. Cada BBS se registra una vez con un token, y luego los juegos
de esa BBS envian scores y consultan los tops global / local.

## Endpoints

| Metodo | Path | Auth | Descripcion |
|--------|------|------|-------------|
| `GET`  | `/api/health` | publico | Healthcheck |
| `POST` | `/api/scores` | Bearer token | Submit de un score |
| `GET`  | `/api/scores/{game}?scope=global&limit=10` | publico | Top N global |
| `GET`  | `/api/scores/{game}?scope=bbs&bbs=VALAR&limit=10` | publico | Top N de una BBS |
| `GET`  | `/api/bbses` | publico | Listar BBSes activas |

El `bbs_id` del que escribe se deduce siempre del token, nunca del body.

### Juegos con orden ascendente

`movida` (menos turnos = mejor) y `wordle` (menos intentos = mejor) ordenan
ascendente. El resto, descendente.

## Deploy en VPS

```bash
# 1) Copia el repo al VPS
sudo useradd -r -s /usr/sbin/nologin -d /opt/bbs-scores bbs-scores
sudo mkdir -p /opt/bbs-scores
sudo chown bbs-scores:bbs-scores /opt/bbs-scores

# 2) Copia el contenido del repo (al menos server/, schema.sql y requirements)
sudo -u bbs-scores rsync -a server/ /opt/bbs-scores/server/

# 3) venv y deps
sudo -u bbs-scores python3 -m venv /opt/bbs-scores/venv
sudo -u bbs-scores /opt/bbs-scores/venv/bin/pip install -r /opt/bbs-scores/server/requirements.txt

# 4) Inicializar DB
sudo -u bbs-scores mkdir -p /opt/bbs-scores/data
cd /opt/bbs-scores && sudo -u bbs-scores ./venv/bin/python -m server.admin list-bbs

# 5) Systemd
sudo cp /opt/bbs-scores/server/bbs-scores.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bbs-scores
sudo systemctl status bbs-scores

# 6) (Opcional) nginx + HTTPS
sudo cp /opt/bbs-scores/server/nginx.conf.example /etc/nginx/sites-available/bbs-scores
# editar dominio y certs
sudo ln -s /etc/nginx/sites-available/bbs-scores /etc/nginx/sites-enabled/
sudo certbot --nginx -d scores.tudominio.com
sudo nginx -t && sudo systemctl reload nginx
```

### Puertos

El servicio FastAPI escucha en `127.0.0.1:8765` por defecto (no choca con tus
puertos en uso: 22 ssh, 23 telnet/mystic, 8080, 9876). Si no usas reverse
proxy, cambia el `--host` en el systemd unit a `0.0.0.0` y abre el firewall.

## Operacion

### Registrar una BBS

```bash
cd /opt/bbs-scores
sudo -u bbs-scores ./venv/bin/python -m server.admin add-bbs VALAR "Valar BBS"
```

Imprime el token plain una unica vez. Apuntalo y metelo en el
`scores_config.json` de la BBS.

### Listar / desactivar / rotar token

```bash
./venv/bin/python -m server.admin list-bbs
./venv/bin/python -m server.admin disable-bbs VALAR
./venv/bin/python -m server.admin enable-bbs VALAR
./venv/bin/python -m server.admin rotate-token VALAR
```

## Dev local

```bash
cd /Users/fx-media/Documents/DopePython
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --reload --host 127.0.0.1 --port 8765

# en otra terminal:
python3 -m server.admin add-bbs TEST "Test BBS"
# (apunta el token, lo usaras abajo)

# Submit
curl -sS -X POST http://127.0.0.1:8765/api/scores \
    -H "Authorization: Bearer EL_TOKEN_QUE_TE_DIO" \
    -H "Content-Type: application/json" \
    -d '{"game":"dino","handle":"AGM","score":156}'

# Top global
curl -sS http://127.0.0.1:8765/api/scores/dino?scope=global
```

## Backup

La DB es un solo fichero (`data/scores.db`). Un cron diario lo copia a otro sitio:

```bash
0 4 * * * sqlite3 /opt/bbs-scores/data/scores.db ".backup /var/backups/scores-$(date +\%F).db"
```
