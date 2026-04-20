# Juegos BBS en Python

Coleccion de juegos en modo texto escritos en Python puro, pensados como *doors* para [Mystic BBS](https://www.mysticbbs.com/) pero jugables tambien en cualquier terminal ANSI local.

Todos comparten el mismo patron:

- Un unico `.py` por juego, solo con la libreria estandar.
- UI 80x24 con caracteres CP437 (bordes dobles, bloques, sombras).
- Colores ANSI clasicos (SGR 30-37 + bold) — compatibles con NetRunner, MuffinTerm y demas clientes BBS.
- `stdout` reconfigurado a `cp437` para que Mystic los pinte correctamente.
- **Shadow buffer** en los juegos con render frecuente: solo se emiten las celdas que cambian.
- Top 10 persistente en un `*_scores.txt` junto al script.

## Juegos

### [dope/](dope/) - DopePython

Clon de *Dope Wars / Drug Wars* (John E. Dell, 1984). 30 dias, 12 drogas, 6 barrios de Nueva York. Compra, vende, viaja, evita a la policia, paga al prestamista, pide credito. Objetivo: acabar con la mayor cantidad de dinero posible.

```
python3 dope/dopepython.py
```

### [typepython/](typepython/) - Typespeed BBS

Clon de `typespeed` (el clasico juego de mecanografia de Linux). Las palabras aparecen por la izquierda y cruzan la pantalla; tecleala con Enter antes de que lleguen al borde derecho. 3 vidas, velocidad creciente, palabras en espanol.

```
python3 typepython/typepython.py
```

### [snake/](snake/) - Snake BBS

El Snake de toda la vida. Input char-a-char con `termios` para leer WASD y flechas sin Enter. Real-time a 10 FPS con render incremental (zero parpadeo).

```
python3 snake/snake.py
```

### [wordle/](wordle/) - Wordle BBS

Wordle en espanol: adivina la palabra de 5 letras en 6 intentos. Feedback por letra con colores de fondo ANSI. Teclado visible en pantalla con el estado acumulado. ~300 palabras en el diccionario.

```
python3 wordle/wordle.py
```

### [buscaminas/](buscaminas/) - Buscaminas BBS

El Buscaminas clasico. Cursor con WASD/flechas, espacio para revelar, F para bandera. Tres dificultades: Principiante (9x9), Intermedio (16x16), Experto (30x16). Primera casilla revelada nunca es mina. Shadow buffer para render eficiente.

```
python3 buscaminas/buscaminas.py
```

### [maze/](maze/) - Maze BBS

Roguelike turn-based de un jugador. Mazmorra procedural, 8 tipos de enemigos (rata, goblin, esqueleto, hobgoblin, orco, troll, ogro, dragon como boss), items, scrolls (fuego/teletransporte/mapeo), trampas, inventario de 10 slots. Combate bump-to-attack, subes de nivel con XP, bajas 10 niveles hasta el Dragon para recuperar el Amuleto de Yendor y volver a la superficie. Victoria + bonus.

```
python3 maze/maze.py
```

### [bbsatro/](bbsatro/) - BBSATRO (balatro.py)

Deckbuilder inspirado en Balatro. Juegas manos de poker para superar una puntuacion objetivo cada ronda. 52 cartas, 8 en mano con render visual (cartas 7x5 con bordes CP437 y palos coloreados). 20 jokers comprables en la tienda que modifican chips/mult. 5 boss blinds con efectos especiales. Upgrade automatico de tipos de mano al jugarlos. Economia con oro e interes.

```
python3 bbsatro/balatro.py
```

## Requisitos

- Python 3.7+ (para `sys.stdout.reconfigure`).
- Terminal ANSI/CP437. En Mystic se lanza como door externo (`python3 ruta/juego.py`).
- `snake.py`, `buscaminas.py`, `maze.py` y `balatro.py` requieren TTY con `termios` (Unix / Mystic via PTY) para input char-a-char.

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
| Maze BBS       | turn-based roguelike  | char-mode     | en pruebas        |
| BBSATRO        | turn-based cartas     | char-mode     | en pruebas        |

## Licencia

MIT. Ver [LICENSE](LICENSE).
