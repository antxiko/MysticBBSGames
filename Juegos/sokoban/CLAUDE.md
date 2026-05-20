# Sokoban BBS

Clon de Sokoban (Hiroyuki Imabayashi, 1981) en modo texto para Mystic BBS. Empujas cajas para colocarlas en las marcas. Solo puedes empujar (no tirar) una caja a la vez.

## Alcance

- Un solo `sokoban.py`. Solo stdlib.
- Char-mode con `termios`.
- Shadow buffer para diff-rendering.
- Top 10 en `sokoban_scores.txt` (por niveles superados + movimientos).
- 154 niveles del set publico de Nicolas Musacchio (MIT licensed), de dificultad creciente.
  Fuente: https://github.com/nMusacchio/sokoban

## Mecanica

- Tablero de tamano variable por nivel.
- `@` jugador, `$` caja, `.` marca de destino, `#` muro.
- `*` caja sobre marca, `+` jugador sobre marca.
- Mover en una direccion: si hay caja delante, empujas (caja se mueve esa direccion); si detras de la caja hay otra caja o muro, no se puede empujar.
- Victoria del nivel: todas las cajas sobre marcas.

## Controles

- `W A S D` o flechas: mover (con empuje automatico si toca caja).
- `R`: reiniciar nivel.
- `U`: deshacer ultimo movimiento (sin limite).
- `N`: pasar de nivel (sin puntuar el actual).
- `Q`: abandonar.

## Graficos

- Muro: `█` en azul oscuro (estilo paredes de mazmorra).
- Suelo: espacio en negro.
- Marca: `·` en rojo (dim).
- Caja sin colocar: `█` ambar.
- Caja en marca: `█` verde brillante.
- Jugador: `@` cyan brillante.

## Puntuacion

- Cada nivel resuelto: +100 puntos - movimientos usados (minimo 10).
- Score total = suma a lo largo de la partida.
- Mostrar mejor puntuacion por nivel guardada.
