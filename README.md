# Juegos BBS en Python

Coleccion de **18 juegos** en modo texto escritos en Python puro, pensados como *doors* para [Mystic BBS](https://www.mysticbbs.com/) pero jugables tambien en cualquier terminal ANSI local. Incluye **scoreboard global online** con servidor compartido entre BBSes, panel admin web y ranking publico con filtros temporales.

Demo en vivo: **https://scores.nosignalbbs.com** (No Signal BBS).

Todos los juegos comparten el mismo patron:

- Un unico `.py` por juego, solo con la libreria estandar.
- UI 80x24 con caracteres CP437 (bordes dobles, bloques, sombras).
- Colores ANSI clasicos (SGR 30-37 + bold) — compatibles con NetRunner, MuffinTerm y demas clientes BBS.
- `stdout` reconfigurado a `cp437` para que Mystic los pinte correctamente.
- **Shadow buffer** en los juegos con render frecuente: solo se emiten las celdas que cambian.
- Top 10 local persistente en un `*_scores.txt` junto al script.
- **Toggle `[L]` local / `[G]` global** en pantalla de fin de partida (16 juegos integrados).
- **Manual del juego** accesible con tecla `M` desde el splash de cada juego.

## Juegos

### [Juegos/dope/](Juegos/dope/) - DopePython

Clon de *Dope Wars / Drug Wars* (John E. Dell, 1984). 30 dias, 12 drogas, 6 barrios de Nueva York. Compra, vende, viaja, evita a la policia, paga al prestamista, pide credito. Objetivo: acabar con la mayor cantidad de dinero posible.

```
python3 Juegos/dope/dopepython.py
```

### [Juegos/typepython/](Juegos/typepython/) - Typespeed BBS

Clon de `typespeed` (el clasico juego de mecanografia de Linux). Las palabras aparecen por la izquierda y cruzan la pantalla; tecleala con Enter antes de que lleguen al borde derecho. 3 vidas, velocidad creciente, palabras en espanol.

```
python3 Juegos/typepython/typepython.py
```

### [Juegos/snake/](Juegos/snake/) - Snake BBS

El Snake de toda la vida. Input char-a-char con `termios` para leer WASD y flechas sin Enter. Real-time a 10 FPS con render incremental (zero parpadeo).

```
python3 Juegos/snake/snake.py
```

### [Juegos/wordle/](Juegos/wordle/) - Wordle BBS

Wordle en espanol: adivina la palabra de 5 letras en 6 intentos. Feedback por letra con colores de fondo ANSI. Teclado visible en pantalla con el estado acumulado. ~300 palabras en el diccionario.

```
python3 Juegos/wordle/wordle.py
```

### [Juegos/buscaminas/](Juegos/buscaminas/) - Buscaminas BBS

El Buscaminas clasico. Cursor con WASD/flechas, espacio para revelar, F para bandera. Tres dificultades: Principiante (9x9), Intermedio (16x16), Experto (30x16). Primera casilla revelada nunca es mina. Shadow buffer para render eficiente.

```
python3 Juegos/buscaminas/buscaminas.py
```

### [Juegos/maze/](Juegos/maze/) - Maze BBS

Roguelike turn-based de un jugador. Mazmorra procedural, 8 tipos de enemigos (rata, goblin, esqueleto, hobgoblin, orco, troll, ogro, dragon como boss), items, scrolls (fuego/teletransporte/mapeo), trampas, inventario de 10 slots. Combate bump-to-attack, subes de nivel con XP, bajas 10 niveles hasta el Dragon para recuperar el Amuleto de Yendor y volver a la superficie. Victoria + bonus.

```
python3 Juegos/maze/maze.py
```

### [Juegos/bbsatro/](Juegos/bbsatro/) - BBSATRO (balatro.py)

Deckbuilder inspirado en Balatro. Juegas manos de poker para superar una puntuacion objetivo cada ronda. 52 cartas, 8 en mano con render visual (cartas 7x5 con bordes CP437 y palos coloreados). 20 jokers comprables en la tienda que modifican chips/mult. 5 boss blinds con efectos especiales. Upgrade automatico de tipos de mano al jugarlos. Economia con oro e interes.

```
python3 Juegos/bbsatro/balatro.py
```

### [Juegos/2048/](Juegos/2048/) - 2048 BBS

Clon del puzzle 2048. Tablero 4x4, deslizas con WASD/flechas para combinar baldosas de potencias de 2. Cada baldosa con su color (blanco -> amarillo -> rojo -> magenta -> verde brillante a partir de 2048). Bandera de victoria al llegar a 2048 pero puedes seguir jugando.

```
python3 Juegos/2048/2048.py
```

### [Juegos/puyopuyo/](Juegos/puyopuyo/) - Puyo Puyo BBS

Clon de Puyo Puyo. Tablero 6x12 donde caen pares de puyos de 5 colores. 4 o mas del mismo color conectados explotan; al caer puyos sobre los huecos puedes encadenar explosiones, y cada eslabon multiplica la puntuacion. Rotacion, soft drop, hard drop, niveles que aceleran la caida.

```
python3 Juegos/puyopuyo/puyopuyo.py
```

### [Juegos/sokoban/](Juegos/sokoban/) - Sokoban BBS

Clon de Sokoban. 10 niveles hechos a mano de dificultad creciente. Empujas cajas a sus marcas (nunca tirar). Undo ilimitado, reset y saltar nivel. Puntuacion = 100 por nivel - movimientos (minimo 10).

```
python3 Juegos/sokoban/sokoban.py
```

### [Juegos/breakout/](Juegos/breakout/) - Breakout BBS

Clon de Breakout/Arkanoid. Paleta con direccion continua (A/D arranca movimiento, pulsar otra vez para), bola que rebota y muro de 228 ladrillos coloreados por fila (50/40/30/20/15/10 puntos). 3 vidas y niveles cada vez mas rapidos.

```
python3 Juegos/breakout/breakout.py
```

### [Juegos/limonada/](Juegos/limonada/) - Limonada BBS

Clon en castellano del clasico *Lemonade Stand*. Llevas un puesto de limonada durante 30 dias: clima, decisiones de cuantos vasos preparar, precio y publicidad, eventos aleatorios. Empiezas con $2 y compites por la caja mas grande al final.

```
python3 Juegos/limonada/limonada.py
```

### [Juegos/catacumba/](Juegos/catacumba/) - Catacumba BBS

**Dungeon pseudo-3D con raycasting puro en ASCII**. Mazmorra 12x12 procedural (recursive backtracker) que recorres en primera persona; paredes con shading por distancia (`█▓▒░`), niebla de guerra en el mini-mapa (solo ves lo que tus rayos han iluminado), ratas que deambulan y muerden, disparo con SPACE (raycast con hitbox y comprobacion de muros), HP, mira centrada, fogonazo y flash rojo al recibir daño.

```
python3 Juegos/catacumba/catacumba.py
```

### [Juegos/outrun/](Juegos/outrun/) - Outrun BBS

Racer pseudo-3D con perspectiva tipo *Out Run* (Sega 1986). Carretera con horizonte, curvas que se interpolan fila a fila acumulando dx, sol en el fondo y rayas que vuelan. Time-attack 90s, distancia = puntuacion. Toggle de gas con W, pulso de freno con S, A/D giran. Top 10 persistente.

```
python3 Juegos/outrun/outrun.py
```

### [Juegos/roadfighter/](Juegos/roadfighter/) - Road Fighter BBS

Racer cenital tipo *Road Fighter* (Konami 1984). Carretera que serpentea horizontalmente (curvas por seno), scenery (arboles, casas, rocas) volando por los lados como sensacion de velocidad, max 2 coches enemigos simultaneos para no saturar el modem. 60s, esquiva y adelanta. Optimizado para BBS: hierba y arcen estaticos, solo se mueve lo necesario (~68 celdas/frame medias a tope de gas).

```
python3 Juegos/roadfighter/roadfighter.py
```

### [Juegos/simon/](Juegos/simon/) - Simon BBS

Simon dice. 4 cuadrantes gigantes en CP437 (ROJO, VERDE, AZUL, AMARILLO) con teclas QWAS en disposicion fisica 2x2 sobre el teclado. La maquina ilumina una secuencia, tu la repites. Cada nivel añade un paso y la velocidad sube. Pantalla casi estatica: solo cambia el cuadrante que se ilumina. Top 10.

```
python3 Juegos/simon/simon.py
```

### [Juegos/movida/](Juegos/movida/) - Movida

Aventura conversacional castiza-punk ambientada en Madrid 1985 (la Movida). Sabado noche, after secreto kinky-punk en una nave de Vallecas, y tu sin entrada. 22 habitaciones (Malasaña, Chueca, Lavapies, Rastro), 11 NPCs (Marichu, Pichi, Antonio, Yvonne, Casto, Tito, Murci, Don Sebas, la vieja, el sereno, Bigote-Polla), parser simple verbo-sustantivo con sinonimos, 3 cadenas de puzzles que confluyen: objeto raro (vibrador rosa del 75 vintage), 5000 pelas (poker o reventa) y palabra de paso. Tres finales. Line-mode, jugable en cualquier terminal. Top 10 por turnos.

```
python3 Juegos/movida/movida.py
```

### [Juegos/dino/](Juegos/dino/) - Dino BBS

Clon del runner del dinosaurio de Chrome offline. Saltas con espacio sobre cactus que vienen por la derecha. Suelo estatico, cielo estatico - solo se mueven los cactus, las patas del dino y los digitos del score. ~20 celdas cambiando por frame de media: el mas ligero de todos los real-time del repo, perfecto para BBS por modem.

```
python3 Juegos/dino/dino.py
```

## Scoreboard global online

Los juegos suben las puntuaciones a un servidor central para que varias BBSes se peleen por el top mundial. En el final de partida cada juego muestra `[L] local [G] global [Enter] continuar`. Si no hay config de servidor o no hay conexion, todo cae a modo local solo y el juego sigue funcionando igual.

### Demo en vivo

**https://scores.nosignalbbs.com** — primera BBS registrada: No Signal BBS.

- `/` — landing publica con stats (BBSes activas, juegos, scores totales) y top mundial por juego.
- `/leaderboard/<game>/?period=week|month|all` — top 25 del juego con tabs **Esta semana / Este mes / Todos los tiempos**, primeros tres puestos en oro/plata/bronce.
- `/admin/` — panel de administracion (HTTP Basic Auth). Listar/añadir/desactivar/rotar/borrar BBSes y gestionar scores individuales.
- `/api/scores/<game>?scope=global|bbs&order=desc|asc&period=all|week|month&limit=N` — JSON publico.

### Arquitectura

- **Server**: FastAPI + SQLite en VPS detras de Caddy con HTTPS automatico. Codigo en [server/](server/). Auth por Bearer token de BBS (no se puede spoof, el `bbs_id` lo deduce el server del token siempre). Cascade ON DELETE en scores.
- **Cliente compartido**: [`bbs_scores.py`](Juegos/bbs_scores.py) en Juegos/ junto a los juegos. Auto-detecta el juego desde el nombre del script (transparente: añadir un juego nuevo no requiere tocar nada). Soporta layouts flat o subdirs. Fail-safe: si la red cae, los submits van a `pending_submissions.jsonl` y se reintentan en el siguiente turno.
- **Panel admin web**: HTML server-rendered, dark mono, sin JS (excepto un `confirm()` de seguridad). PBKDF2-HMAC-SHA256 con salt para passwords de admin.
- **Ranking publico web**: misma estetica, sin JS, sin auth, sin cookies. Solo SSR.

### Despliegue

- **Servidor en VPS Linux**: ver [INSTALL_VPS.md](INSTALL_VPS.md). Funciona con Caddy (auto-HTTPS) o nginx + certbot.
- **BBS / Mystic**: ver [INSTALL_MYSTIC.md](INSTALL_MYSTIC.md). Clonar el repo donde Mystic ejecute los doors, dropear `scores_config.json` con el token que te de el admin del VPS, opcional.

### Identidad de jugadores

Los jugadores escriben 3 iniciales en sus tops. En el global aparecen como `INICIALES@BBS` (ej. `AGM@NOSIGNAL`) para distinguir entre BBSes. La BBS no aporta el handle del usuario; las iniciales las escribe el jugador.

### Juegos con orden ASC

`movida` (menos turnos = mejor) y `wordle` (menos intentos = mejor) ordenan ascendente. El resto, descendente. El cliente lo decide en cada llamada (`ascending=True|False`); el servidor no tiene lista de juegos.

## Requisitos

- **Python 3.10+** (los juegos en si funcionan en 3.7+, pero el cliente del scoreboard global `bbs_scores.py` usa generics nativos y union types - `list[X]`, `str | None`).
- Terminal ANSI/CP437. En Mystic se lanza como door externo (`python3 ruta/juego.py`).
- La mayoria de juegos char-mode requieren TTY con `termios` (Unix / Mystic via PTY) para input char-a-char.
- Sin scoreboard global: stdlib pura, cero dependencias.
- Con scoreboard global: stdlib en el cliente, y FastAPI + uvicorn en el server (ver [server/requirements.txt](server/requirements.txt)).

## Deploy en Mystic

Cada script es un proceso externo. Configura la entrada del door en Mystic para lanzar `python3 /ruta/al/juego.py` y asegurate de:

- Perfil del usuario con **ANSI-BBS** como emulation.
- Ancho de terminal 80.
- Color activado.

## Estado de cada juego

| Juego          | Mecanica              | Input         | Probado en Mystic |
|----------------|-----------------------|---------------|-------------------|
| DopePython     | turn-based            | line-mode     | si, OK            |
| Typespeed BBS  | real-time scroll      | line-mode + `select` | si, OK     |
| Snake BBS      | real-time             | char-mode     | si, OK            |
| Wordle BBS     | turn-based            | line-mode     | si, OK            |
| Buscaminas BBS | turn-based            | char-mode     | si, OK            |
| Maze BBS       | turn-based roguelike  | char-mode     | si, OK            |
| BBSATRO        | turn-based cartas     | char-mode     | si, OK            |
| 2048 BBS       | turn-based puzzle     | char-mode     | si, OK            |
| Puyo Puyo BBS  | real-time puzzle      | char-mode     | si, OK            |
| Sokoban BBS    | turn-based puzzle     | char-mode     | si, OK            |
| Breakout BBS   | real-time arcade      | char-mode     | si, OK            |
| Limonada BBS   | turn-based sim        | line-mode     | si, OK            |
| Catacumba BBS  | real-time pseudo-3D   | char-mode     | si, OK            |
| Outrun BBS     | real-time pseudo-3D   | char-mode     | en pruebas        |
| Road Fighter BBS | real-time cenital   | char-mode     | si, OK            |
| Simon BBS      | memoria turn-based    | char-mode     | si, OK            |
| Movida         | aventura conversacional | line-mode   | si, OK            |
| Dino BBS       | real-time runner      | char-mode     | si, OK            |

## Licencia

MIT. Ver [LICENSE](LICENSE).
