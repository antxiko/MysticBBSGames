# 2048 BBS

Clon del puzzle clasico 2048 para Mystic BBS. Combina baldosas de potencias de 2 deslizando con WASD hasta llegar a 2048 (o seguir hasta lo que aguantes).

## Alcance

- Un solo `dosmil.py` (el nombre del fichero evita empezar por digito; el juego se muestra como "2048 BBS"). Solo stdlib.
- Char-mode con `termios`.
- Shadow buffer para diff-rendering.
- Top 10 en `dosmil_scores.txt`.

## Mecanica

- Tablero 4x4. Empiezas con 2 baldosas (2 con 90% / 4 con 10%).
- Cada movimiento: todas las baldosas deslizan en la direccion elegida; las adyacentes iguales se fusionan en una del doble valor.
- Cada fusion suma el valor resultante a tu puntuacion.
- Tras cada movimiento valido (que cambie el tablero), aparece una baldosa nueva.
- Llegas a 2048 y aparece mensaje de victoria, pero puedes seguir jugando.
- Game over: no quedan movimientos posibles (sin huecos y sin pares adyacentes).

## Controles

- `W A S D` o flechas: deslizar.
- `R`: reiniciar partida.
- `Q`: salir (guarda top 10).

## Graficos

- Baldosas 8x3 con bordes CP437 (`┌─┐│└┘`).
- Color por valor escalando del blanco al verde brillante segun potencia:

| Valor | Color           |
|-------|-----------------|
| vacio | dim             |
| 2     | blanco          |
| 4     | amarillo claro  |
| 8     | cyan claro      |
| 16    | cyan            |
| 32    | amarillo        |
| 64    | rojo claro      |
| 128   | rojo            |
| 256   | magenta         |
| 512   | magenta claro   |
| 1024  | verde claro     |
| 2048+ | verde brillante (negrita) |
