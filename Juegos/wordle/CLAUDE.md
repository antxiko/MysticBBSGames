# Wordle BBS

Clon de Wordle en espanol, pensado como door para Mystic BBS. 5 letras, 6 intentos, feedback por color.

## Alcance

- **Un solo script**: `wordle.py`. Solo stdlib.
- **Python externo** como los demas juegos. stdout reconfigurado a CP437.
- **Input line-mode** con `input()` — no hace falta real-time.
- **Top 10** persistente en `wordle_scores.txt`.
- Palabras: ASCII mayusculas, 5 letras, sin tildes ni enes.

## Reglas

- Se sortea palabra secreta de una lista de ~150 palabras espanolas de 5 letras.
- Jugador tiene 6 intentos para acertarla.
- Tras cada intento, cada letra recibe un color:
  - **Verde**: letra correcta en la posicion correcta.
  - **Amarillo**: letra en la palabra pero en otra posicion.
  - **Gris**: letra no esta en la palabra.
- Se repinta el teclado con los colores acumulados.
- Puntuacion: `(7 - intentos_usados) * 100` al ganar. 0 al perder.
- Se puede jugar varias partidas en la misma sesion; al salir, se actualiza top 10.

## Graficos

Celdas coloreadas por estado (ANSI bg). Teclado visible con estado de cada letra.
