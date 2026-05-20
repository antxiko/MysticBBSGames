# Pacman BBS

Clon cenital del clasico Pacman, en modo texto 80x24. Maze 28x11 en coords
logicas; cada celda logica = sprite 2x2 en terminal. Asi solo cambian
~20-40 celdas por frame de render (5 sprites moviendose).

## Alcance

- Un solo `pacman.py`. Solo stdlib.
- Char-mode con `termios` + select para input no bloqueante.
- Shadow buffer diferencial para BBS.
- Top 10 local + global.

## Mecanica

- Pacman come puntos `·` (+10 pts) y power pellets `●` (+50 pts).
- Power pellet activa modo "asustado" 6 segundos: los fantasmas se vuelven
  azules, pacman puede comerlos (+200 pts cada uno), respawnean en el
  centro.
- 3 vidas. Colision con fantasma sin power = pierdes vida + reset
  posiciones iniciales.
- Al comer todos los puntos, siguiente nivel (mismo maze por ahora).

## Sprites 2x2

Cada personaje ocupa una celda logica (2x2 terminal cells):

- Pacman: amarillo, con animacion abierto/cerrado y direccion (wedge).
- Fantasmas: rojo (Blinky), magenta (Pinky), cyan (Inky), verde (Clyde).
- Asustados: azul brillante.

## IA fantasmas

Cada tick (180ms), cada fantasma:
1. Sin marcha atras (salvo callejon).
2. 70% chase (minimizar distancia Manhattan a pacman) + 30% random.
3. En modo asustado: huyen (maximizar distancia a pacman).

## Controles

- `W A S D` o flechas: mover.
- `Q`: salir.

## Puntuacion

- Cada partida: score acumulado.
- Top 10 local + global (`bbs_scores`).
