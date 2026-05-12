# Catacumba BBS

Pseudo-3D first-person dungeon en ASCII puro con raycasting tipo Wolfenstein 3D. Te mueves por una mazmorra y ves las paredes en perspectiva, en una pantalla de 80x24 de un BBS. Es una **locura tecnica** que el modem aguanta gracias al shadow buffer diferencial.

## Alcance

- Un solo `catacumba.py`. Solo stdlib.
- Char-mode con `termios` + tick loop con `select`.
- Shadow buffer (con skip de esquina) para diff-rendering.
- Sin top 10 (es exploracion, no puntuacion).

## Mecanica

- Mazmorra 12x12 con muros y suelo. Empiezas en la entrada, la salida `E` esta en algun rincon.
- Vista 3D: 78 cols x 18 filas de raycasting + 4 filas de HUD/mini-mapa.
- Para cada columna del area de juego se lanza un rayo desde la posicion del jugador. La distancia al primer muro determina la altura de la "tira" de pared en esa columna.
- Shading por distancia: cerca `█`, medio `▓`, lejos `▒`, muy lejos `░`.
- Mini-mapa abajo a la derecha mostrando el laberinto, tu posicion `@` y la salida `E`.

## Controles

- `W` / flecha arriba: avanzar.
- `S` / flecha abajo: retroceder.
- `A` / flecha izquierda: rotar a la izquierda.
- `D` / flecha derecha: rotar a la derecha.
- `Q`: salir.

## Algoritmo (resumen)

Para cada columna `c` del area 3D:
1. Angulo del rayo = `player_angle - FOV/2 + (c / W) * FOV`.
2. Avanza el rayo en pasitos hasta tocar muro (`MAP[y][x] == '#'`).
3. Distancia = ese paso. Corregir el fish-eye multiplicando por `cos(angulo - player_angle)`.
4. Altura de la "tira" = `H * factor / dist`, clampada al alto del area.
5. Pintar la tira centrada en la columna con el shade que toca por distancia.

Cielo/suelo: arriba en azul oscuro, abajo en marron, paredes en gris/blanco shaded.
