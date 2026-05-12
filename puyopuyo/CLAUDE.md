# Puyo Puyo BBS

Clon de Puyo Puyo (Sega/Compile) en modo texto para Mystic BBS. Pares de puyos de colores caen al tablero; al juntar 4 o mas del mismo color conectados se eliminan en cascada con cadenas que multiplican la puntuacion.

## Alcance

- Un solo `puyopuyo.py`. Solo stdlib.
- Char-mode con `termios` + tick loop con `select`.
- Shadow buffer para diff-rendering.
- Top 10 en `puyopuyo_scores.txt`.

## Mecanica

- Tablero 6 cols x 12 filas.
- 5 colores de puyo (rojo, verde, azul, amarillo, magenta).
- Cada pieza es un par de puyos (color del pivote + color del eje), con el eje arriba del pivote por defecto.
- El par cae automaticamente. Velocidad sube con el nivel.
- Al asentarse, cada puyo cae a su columna por gravedad (pueden quedar a alturas distintas).
- Se buscan grupos de 4+ puyos del mismo color conectados (4-conectividad).
- Cada grupo se elimina. Tras eliminar, gravedad. Si surgen nuevos grupos, cadena -> mas puntos.
- Puntuacion por paso de cadena: `count * 10 * 2^(cadena-1)`.
- Subes nivel cada 30 puyos eliminados; cada nivel acelera la caida.
- Game over si la nueva pieza no cabe en la zona superior.

## Controles

- `A` / `D` o flechas: mover izquierda / derecha.
- `W` / `arriba`: rotar par (eje gira en sentido horario alrededor del pivote).
- `S` / `abajo`: soft drop (caida rapida mientras se mantiene pulsado).
- `Espacio`: hard drop (instantaneo al fondo).
- `Q`: salir.

## Graficos

- Cada puyo se renderiza como `██` (2 chars de `█` CP437) coloreados por su tipo.
- Frame del tablero con bordes CP437 dobles.
- Preview de siguiente pieza a la derecha.
- HUD con puntuacion, nivel, cadena actual y puyos eliminados.
