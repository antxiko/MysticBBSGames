# Instalacion del scoreboard server en un VPS

Esta guia monta el servidor de scores compartido (FastAPI + SQLite) en un VPS
Linux. Una vez en pie, cualquier BBS del mundo que tenga estos juegos puede
registrarse, mandar puntuaciones y consultar el ranking global. Incluye:

- API REST publica y autenticada.
- Panel admin web en `/admin/` para gestionar BBSes y scores.
- Ranking publico web en `/` con filtros semana/mes/all-time.

Demo desplegada: **https://scores.nosignalbbs.com**.

## Resumen

- Servicio FastAPI escuchando en `127.0.0.1:8765` (no choca con puertos comunes
  de Mystic BBS: 22 ssh, 23 telnet, 8080, 9876).
- Base de datos SQLite en un solo fichero (`data/scores.db`).
- Reverse proxy con HTTPS publico: **Caddy** (recomendado, auto-HTTPS via
  Let's Encrypt) o nginx + certbot.
- Gestion via CLI (`python -m server.admin ...`) o panel web (`/admin/`).
- Systemd unit para arranque automatico.

## Requisitos

- VPS con Linux (Debian/Ubuntu testeado; cualquier distro con systemd vale).
- Python 3.10 o superior (recomendado 3.11+).
- Acceso root o sudo.
- (Opcional) un dominio o subdominio apuntando a la IP del VPS para HTTPS.
- (Opcional) nginx instalado.

## Paso 1: usuario dedicado

Crea un usuario sin shell para correr el servicio:

```bash
sudo useradd -r -s /usr/sbin/nologin -d /opt/bbs-scores bbs-scores
sudo mkdir -p /opt/bbs-scores
sudo chown bbs-scores:bbs-scores /opt/bbs-scores
```

## Paso 2: subir el codigo

Clona el repo o sube solo el directorio `server/`:

```bash
# Opcion A: clonar todo el repo (mas simple)
sudo -u bbs-scores git clone https://github.com/antxiko/MysticBBSGames.git /opt/bbs-scores/repo

# Opcion B: solo el server (rsync desde tu maquina)
rsync -a server/ user@tu-vps:/tmp/bbs-scores-server/
sudo mv /tmp/bbs-scores-server /opt/bbs-scores/server
sudo chown -R bbs-scores:bbs-scores /opt/bbs-scores
```

A partir de aqui asumo que tienes `/opt/bbs-scores/server/`. Si usaste la
opcion A, los paths serian `/opt/bbs-scores/repo/server/`. Adapta segun.

## Paso 3: venv y dependencias

```bash
sudo -u bbs-scores python3 -m venv /opt/bbs-scores/venv
sudo -u bbs-scores /opt/bbs-scores/venv/bin/pip install --upgrade pip
sudo -u bbs-scores /opt/bbs-scores/venv/bin/pip install -r /opt/bbs-scores/server/requirements.txt
```

## Paso 4: inicializar la base de datos

```bash
sudo -u bbs-scores mkdir -p /opt/bbs-scores/data
cd /opt/bbs-scores
# El siguiente comando crea la DB automaticamente:
sudo -u bbs-scores ./venv/bin/python -m server.admin list-bbs
# Salida esperada: "(no hay BBSes registradas)"
```

## Paso 5: arranque manual (smoke test)

```bash
cd /opt/bbs-scores
sudo -u bbs-scores ./venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8765
```

En otra terminal:

```bash
curl -sS http://127.0.0.1:8765/api/health
# {"status":"ok"}
```

Para. Vamos a montarlo como servicio.

## Paso 6: systemd

```bash
sudo cp /opt/bbs-scores/server/bbs-scores.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bbs-scores
sudo systemctl status bbs-scores
```

Logs:
```bash
sudo journalctl -u bbs-scores -f
```

## Paso 7: HTTPS publico

Tienes que exponer el server a internet con HTTPS (los tokens viajan en
claro si no). Dos opciones segun lo que ya tengas en el VPS:

### Opcion A: Caddy (recomendado, auto-HTTPS via Let's Encrypt)

Si ya tienes Caddy corriendo (sirve algun site web del 80/443):

```bash
# Añadir un bloque al final del Caddyfile - es ADDITIVE
sudo tee -a /etc/caddy/Caddyfile > /dev/null <<'EOF'

# BBS Scores - scoreboard global
scores.tudominio.com {
    reverse_proxy 127.0.0.1:8765
}
EOF
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
# Caddy negocia el cert con Let's Encrypt automaticamente.
sudo journalctl -u caddy --since "1 minute ago" --no-pager | tail -10
```

### Opcion B: nginx + certbot

Si prefieres nginx:

```bash
sudo apt install nginx certbot python3-certbot-nginx
sudo cp /opt/bbs-scores/repo/server/nginx.conf.example /etc/nginx/sites-available/bbs-scores
sudo nano /etc/nginx/sites-available/bbs-scores
# Cambia 'scores.tudominio.com' por tu dominio real.
sudo ln -s /etc/nginx/sites-available/bbs-scores /etc/nginx/sites-enabled/
sudo certbot --nginx -d scores.tudominio.com
sudo nginx -t && sudo systemctl reload nginx
```

Aniade tambien la zona de rate-limit en `/etc/nginx/nginx.conf` dentro de `http {...}`:
```
limit_req_zone $binary_remote_addr zone=submitlim:10m rate=30r/m;
```

### Sin reverse proxy (exponer puerto directo)

Si prefieres no usar reverse proxy, edita el `bbs-scores.service` y cambia:
```
ExecStart=/opt/bbs-scores/venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 8765
```
Reinicia el servicio (`sudo systemctl daemon-reload && sudo systemctl restart bbs-scores`)
y abre el puerto 8765 en el firewall del VPS. Los tokens viajaran en claro
asi que no recomendado para produccion.

## Paso 8: registrar BBSes

Por cada BBS que vaya a participar, ejecuta:

```bash
cd /opt/bbs-scores
sudo -u bbs-scores ./venv/bin/python -m server.admin add-bbs VALAR "Valar BBS"
```

Salida:
```
BBS registrada con id=1 short_name=VALAR

TOKEN (apuntalo, no se podra recuperar):
  abc123def456...
```

Manda ese token al SysOp de la BBS por canal seguro. Lo necesitara en su
`scores_config.json`. Si se le pierde:

```bash
sudo -u bbs-scores ./venv/bin/python -m server.admin rotate-token VALAR
# imprime un token nuevo y desactiva el viejo
```

Otros comandos:
```bash
./venv/bin/python -m server.admin list-bbs
./venv/bin/python -m server.admin disable-bbs VALAR
./venv/bin/python -m server.admin enable-bbs VALAR
./venv/bin/python -m server.admin delete-bbs VALAR  # pide "SI" para confirmar
```

## Paso 9: panel admin web

Para gestionar las BBSes desde el navegador en lugar del CLI, crea un admin
del panel web:

```bash
cd /opt/bbs-scores/repo
sudo -u bbs-scores env BBS_SCORES_DB=/opt/bbs-scores/data/scores.db \
  /opt/bbs-scores/venv/bin/python -m server.admin set-admin antxiko
# te pide la pass por stdin dos veces, sin echo
```

La password se guarda hasheada con PBKDF2-HMAC-SHA256 + salt aleatoria
de 16 bytes, 100k iteraciones.

Despues abre **https://scores.tudominio.com/admin/** en el navegador.
El navegador te pedira usuario y pass via HTTP Basic Auth. Una vez dentro:

- Listado de BBSes con estado, scores acumulados, fecha.
- Form para añadir BBS nueva (muestra el token recien generado).
- Botones por BBS: Desactivar / Reactivar / Rotar token / Borrar.
- Enlace **"Gestionar scores individuales"** que lleva a `/admin/scores/`
  donde puedes filtrar por juego/BBS/iniciales y borrar scores sueltos
  (util para limpiar tests o cheating).

Para rotar la password de un admin: ejecuta el mismo `set-admin` otra vez.
Para listar admins: `python -m server.admin list-admin`.

## Paso 10: ranking publico web

No hace falta configuracion: una vez levantado el server, el ranking
publico esta en la raiz del dominio:

- **https://scores.tudominio.com/** — landing con stats y top mundial por juego.
- **https://scores.tudominio.com/leaderboard/&lt;game&gt;/** — top 25 con tabs
  semana / mes / todos los tiempos.

## Paso 11: backups

La DB es un fichero unico. Un cron diario lo respalda:

```bash
sudo crontab -e -u bbs-scores
# añade:
0 4 * * * sqlite3 /opt/bbs-scores/data/scores.db ".backup /opt/bbs-scores/data/scores-$(date +\%F).db" && find /opt/bbs-scores/data -name 'scores-*.db' -mtime +14 -delete
```

## Comprobacion final

Desde tu maquina local:
```bash
# Health
curl https://scores.tudominio.com/api/health

# Top de un juego (vacio si nadie ha jugado aun)
curl 'https://scores.tudominio.com/api/scores/dino?scope=global&limit=5'

# Mandar un score (sustituye TOKEN)
curl -X POST https://scores.tudominio.com/api/scores \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"game":"dino","handle":"TST","score":1000}'

# Ver que aparece
curl 'https://scores.tudominio.com/api/scores/dino?scope=global&limit=5'
```

Si todo eso funciona, el servidor esta listo. Ahora cada BBS debe configurar
su cliente segun [INSTALL_MYSTIC.md](INSTALL_MYSTIC.md).

## Troubleshooting

- **systemctl status muestra fallo**: `journalctl -u bbs-scores -n 50` da el
  error. Lo mas comun: permisos en `/opt/bbs-scores/data/` (chown -R bbs-scores).
- **401 Unauthorized al hacer POST**: el token no coincide con ninguna BBS, o
  la BBS esta desactivada. Revisa con `list-bbs`.
- **Tokens no funcionan despues de rotate**: el cache de TLS de Cloudflare
  u otros CDNs puede mantener viejas respuestas; espera o purga.
- **DB locked**: SQLite es single-writer. Si tienes muchos submits concurrentes,
  considera subir a PostgreSQL (no incluido en v1).
