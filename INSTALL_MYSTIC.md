# Instalacion de los juegos en Mystic BBS

Esta guia es para SysOps que quieren añadir los juegos como doors externos
en Mystic BBS, opcionalmente con scoreboard global compartido entre BBSes.

## Resumen

- Cada juego es un solo script Python que se lanza como door externo.
- Sin scoreboard global, cada juego funciona standalone con su top local.
- Con scoreboard global, el SysOp del VPS te da un token y los juegos
  envian/leen scores del servidor central. El top 10 local se mantiene
  ademas, accesible con la tecla `L` en la pantalla de fin de partida.
- Solo standard library de Python + (opcional) acceso de salida a internet
  para el scoreboard global.

## Requisitos

- Mystic BBS instalado y funcionando.
- Python 3.7 o superior accesible desde la maquina de Mystic (Linux: ya esta).
- ANSI-BBS en el perfil de usuario, ancho 80, color activado.
- (Opcional) salida HTTPS a tu servidor de scores para el scoreboard global.

## Paso 1: clonar el repo

Donde quieras dentro de la maquina de Mystic. Tipicamente:

```bash
cd /mystic/doors/   # o donde tengas tus doors
git clone https://github.com/antxiko/MysticBBSGames.git
cd MysticBBSGames
```

A partir de ahora asumo que el repo esta en `/mystic/doors/MysticBBSGames/`.
Adapta los paths a tu instalacion.

## Paso 2: probar un juego localmente

Antes de tocar Mystic, verifica que Python puede correr los juegos:

```bash
python3 /mystic/doors/MysticBBSGames/dino/dino.py
```

Si arranca y muestra el splash con el logo de DINO BBS, todo bien. Pulsa `Q`
o Ctrl-C para salir.

## Paso 3 (opcional): configurar scoreboard global

Para que los scores se sincronicen con un servidor central (compartido entre
otras BBSes), pide a quien administra el VPS de scores que te de:

- La URL del servidor (ej. `https://scores.tudominio.com`)
- Un nombre corto para tu BBS (ej. `VALAR`)
- Un token (string largo) personal de tu BBS

Crea el fichero `scores_config.json` en la raiz del repo:

```bash
cd /mystic/doors/MysticBBSGames
cp scores_config.json.example scores_config.json
nano scores_config.json
```

Rellena con los datos que te dieron:

```json
{
  "server_url": "https://scores.tudominio.com",
  "bbs_short_name": "VALAR",
  "full_name": "Valar BBS",
  "api_token": "abc123def456...",
  "timeout_seconds": 2.0,
  "cache_seconds": 60
}
```

Verifica:

```bash
python3 bbs_scores.py
# Salida esperada:
# Config: server=https://scores.tudominio.com bbs=VALAR
# online_enabled=True, ping=True
# Local dino top: []
```

Si `ping=False`, comprueba que la URL es correcta y que tu maquina tiene
salida HTTPS hacia ese dominio. Si no quieres scoreboard global, omite este
paso y los juegos funcionaran solo con el top local.

## Paso 4: configurar un door en Mystic

Mystic lanza cada juego como subproceso. La configuracion exacta depende de
tu version de Mystic. En general:

- **Comando**: `python3 /mystic/doors/MysticBBSGames/dino/dino.py`
- **Emulation**: ANSI-BBS
- **Width**: 80
- **Color**: SI
- **Native**: SI (los scripts heredan stdin/stdout del usuario)

### Ejemplo con `dino`

En el menu editor de Mystic, añade un door con:
- **Display**: `DINO - salta cactus`
- **Command type**: External program
- **Command**: `python3 /mystic/doors/MysticBBSGames/dino/dino.py`
- **Hotkey**: `D` (o lo que prefieras)

Asegurate de que el usuario `mystic` (o el que tengas) tiene permiso de
lectura/ejecucion en el repo:

```bash
sudo chown -R mystic:mystic /mystic/doors/MysticBBSGames
```

Y de escritura en el directorio de cada juego (para los `*_scores.txt`):
ya esta cubierto al ser su `chown`.

### Repite por cada juego

Cada juego tiene su propio entry point:

| Juego          | Comando                                              |
|----------------|------------------------------------------------------|
| DopePython     | `python3 dope/dopepython.py`                         |
| Typespeed BBS  | `python3 typepython/typepython.py`                   |
| Snake BBS      | `python3 snake/snake.py`                             |
| Wordle BBS     | `python3 wordle/wordle.py`                           |
| Buscaminas BBS | `python3 buscaminas/buscaminas.py`                   |
| Maze BBS       | `python3 maze/maze.py`                               |
| BBSATRO        | `python3 bbsatro/balatro.py`                         |
| 2048 BBS       | `python3 2048/2048.py`                               |
| Puyo Puyo BBS  | `python3 puyopuyo/puyopuyo.py`                       |
| Sokoban BBS    | `python3 sokoban/sokoban.py`                         |
| Breakout BBS   | `python3 breakout/breakout.py`                       |
| Limonada BBS   | `python3 limonada/limonada.py`                       |
| Catacumba BBS  | `python3 catacumba/catacumba.py`                     |
| Outrun BBS     | `python3 outrun/outrun.py`                           |
| Road Fighter   | `python3 roadfighter/roadfighter.py`                 |
| Simon BBS      | `python3 simon/simon.py`                             |
| Movida         | `python3 movida/movida.py`                           |
| Dino BBS       | `python3 dino/dino.py`                               |

(Los paths son relativos al repo.)

## Paso 5: notas sobre tipos de input

Los juegos se dividen en dos categorias:

- **Line-mode** (entrada con `input()`/`print()`, Enter para confirmar):
  DopePython, Typespeed, Wordle, Limonada, Movida. Funcionan en cualquier
  configuracion de door.

- **Char-mode** (input char-a-char via termios + select):
  Snake, Buscaminas, Maze, BBSATRO, 2048, Puyo Puyo, Sokoban, Breakout,
  Catacumba, Outrun, Road Fighter, Simon, Dino. Requieren un TTY real
  (Mystic via PTY funciona en local; revisa que la conexion del usuario
  no este buffereando entradas).

Si un juego char-mode no responde a las teclas, la causa mas comun es que
el door esta lanzado con stdin redirigido en vez de via PTY. En Mystic
selecciona "Native execution" o equivalente.

## Paso 6: testing en directo

Conectate a tu BBS como usuario de prueba y entra al door. El splash deberia
aparecer. Pulsa `M` para ver el manual del juego.

Al perder, en pantalla de fin de partida pulsa:
- `L` para ver el top de tu BBS
- `G` para ver el top global de todas las BBSes
- `Enter` para volver al prompt "Otra partida?"

Si has configurado el scoreboard global y aparece "(sin conexion)" al pulsar
G, es que la maquina no llega al servidor. Comprueba `python3 bbs_scores.py`
desde shell de la maquina BBS.

## Updates

Cuando salga una version nueva del repo:

```bash
cd /mystic/doors/MysticBBSGames
git pull
```

Tu `scores_config.json` queda intacto (esta en `.gitignore`). Tus
`*_scores.txt` tambien (los locales de cada BBS).

## Privacidad y seguridad

- El servidor de scores recibe: nombre del juego, iniciales (3 chars), score,
  fecha, y un `extra` opcional con metadatos (nivel, dificultad, etc).
- **No** recibe IP del usuario que jugo (Mystic lanza el script como door,
  y el script no consulta IP).
- **No** recibe el handle real del usuario en la BBS - solo las 3 iniciales
  que escribe al entrar en el top.
- El token de tu BBS solo lo usas tu (BBS) para postear. Cualquiera con
  acceso al repo y al fichero `scores_config.json` puede usarlo. Manten ese
  fichero con permisos restrictivos:
  ```bash
  chmod 600 /mystic/doors/MysticBBSGames/scores_config.json
  ```

## Sin scoreboard global

Si decides no participar en el global, **no crees** `scores_config.json` (o
dejalo con `server_url` y `api_token` vacios). Todos los juegos seguiran
funcionando con sus tops locales en cada `<juego>/<juego>_scores.txt`.
La tecla `G` mostrara "(sin conexion - mostrando local)" como fallback.

## Troubleshooting

- **El juego sale a los pocos segundos sin error**: probablemente Python no
  tiene un TTY real. Mira los logs de Mystic.
- **Backspace manda `^H`**: ya lo tenemos handled con `termios.VERASE` en
  `configurar_backspace()`. Si sigue dando, abre issue en GitHub.
- **No aparecen colores**: verifica que el cliente del usuario tiene
  ANSI-BBS y CP437 activado.
- **El score se guarda pero no aparece en TOP GLOBAL**: 
  1. `python3 bbs_scores.py` desde la shell - si `online_enabled=False`, falta
     o esta vacio el `scores_config.json`.
  2. Comprueba que el token es correcto (admin del VPS puede confirmar).
  3. Mira si hay `pending_submissions.jsonl` en la raiz - significa que hay
     submits que no han subido aun (red). Se reintentan al siguiente submit.
