# Breakout BBS

Clon de Breakout/Arkanoid en modo texto para Mystic BBS. Paleta abajo, bola que rebota, muro de ladrillos arriba. Rompes ladrillos, ganas puntos, no dejes que la bola caiga.

## Alcance

- Un solo `breakout.py`. Solo stdlib.
- Char-mode con `termios` + tick loop con `select`.
- Shadow buffer (con skip de esquina inferior-derecha) para no saturar el modem.
- Top 10 en `breakout_scores.txt`.

## Mecanica

- Area de juego dentro de marco CP437. Paleta en la fila inferior, ladrillos en las 6-8 superiores.
- 6 filas de ladrillos × 38 ladrillos por fila = 228 ladrillos. Cada uno 2 chars de ancho.
- Bola se mueve 1 celda por tick (dx, dy en {-1, +1}). Rebota en muros (reversa x), techo (reversa y), paleta (reversa y) y ladrillos (reversa y, ladrillo destruido).
- Paleta de 7 cells. Posicion del impacto en la paleta inclina la trayectoria: tercio izquierdo dx=-1, derecho dx=+1, centro mantiene.
- Vidas: 3. Cae bola = pierde vida.
- Niveles: al limpiar todos los ladrillos, siguiente nivel con bola mas rapida.

## Puntuacion

Por fila (de arriba a abajo): 50, 40, 30, 20, 15, 10 puntos. Mas tochos los de arriba.

## Controles

- `A` / `D` o flechas: mover paleta izquierda / derecha.
- `Espacio`: servir bola (al inicio del nivel o tras perder vida, la bola se sostiene en la paleta).
- `Q`: salir.

## Graficos

- Marco: `╔═╗║╚╝` doble en blanco.
- Ladrillo: 2 chars `██` coloreados por fila.
- Paleta: `═══════` (7 chars) en cyan brillante.
- Bola: `●` (CP437 0x07? probable no imprimible, alt `O` o `*`). Usaremos `O` en blanco brillante para evitar issues.
