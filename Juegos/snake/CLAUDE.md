# Snake BBS

Snake clasico en modo texto, pensado como door para Mystic BBS. Serpiente que come comida, crece, muere si choca con la pared o consigo misma.

## Alcance

- **Un solo script**: `snake.py`. Solo stdlib.
- **Python externo** lanzado por Mystic (igual que `dopepython.py` y `typepython.py`).
- **UI 80x24** con ANSI crudo, stdout reconfigurado a CP437.
- **Real-time** a ~10 FPS. Input char-a-char con `termios` en modo cbreak.
- **Top 10** persistente en `scores.txt` junto al script.

## Controles

- `WASD` o flechas para girar.
- `Q` para salir.

## Mecanica

- Serpiente empieza con 4 segmentos, moviendose a la derecha.
- Come el `*` de comida: +1 segmento, +10 puntos.
- Muere al chocar con el marco o consigo misma.
- Velocidad: 10 ticks/seg al inicio, +5% cada 5 comidas. Max 20 ticks/seg.
- Sin reversa: si va a la derecha, `a` no hace nada.

## Graficos

- Cabeza: `█` verde brillante.
- Cuerpo: `█` verde.
- Comida: `*` rojo brillante.
- Marco: `╔═╗║╚╝` CP437 doble, colores blanco/dim.

## Compatibilidad

`termios` puede fallar si stdin no es TTY. En ese caso salimos con mensaje de error: snake no tiene sentido sin input char-a-char.
