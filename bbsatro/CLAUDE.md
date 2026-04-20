# BBSATRO

Version "deckbuilder" inspirada en Balatro, adaptada a door de Mystic BBS. Juegas manos de poker para superar una puntuacion objetivo en cada ronda. Sobrevivir todas las antes posibles.

## Alcance FASE 1 (sin jokers)

- Un solo `balatro.py` (el nombre del fichero es ese, el juego se muestra como "BBSATRO"). Solo stdlib.
- Shadow buffer para no saturar modem.
- Char-mode con `termios`.
- Baraja estandar 52 cartas, 4 palos.
- 8 cartas en mano.
- Por ronda: 4 manos para jugar, 3 descartes.
- Selecciona 1-5 cartas, pulsa `P` para jugarlas como mano de poker.
- La mano se evalua (Pareja, Escalera, Color, etc.) y puntua como `Chips * Mult`.
- Supera el objetivo de la ronda para avanzar. Si no, game over.
- Top 10 por puntuacion total acumulada.

## Sin jokers (de momento)

Los jokers son el corazon del roguelike Balatro. Dejados fuera de la fase 1 para acotar alcance. Se pueden anadir despues como extras que modifican el scoring.

## Progresion

- Cada **ante** tiene 3 rondas: Pequena, Grande, Boss.
- Objetivo escala exponencialmente: `target = 300 * 1.6^(ante-1) * [1.0, 1.5, 2.0][ronda]`.
- Al pasar una ante entera, subes a la siguiente. No hay limite — sobrevive lo que puedas.

## Manos de poker

| Mano               | Chips base | Mult base |
|--------------------|-----------|----------|
| Carta alta         | 5         | 1        |
| Pareja             | 10        | 2        |
| Doble pareja       | 20        | 2        |
| Trio               | 30        | 3        |
| Escalera           | 30        | 4        |
| Color              | 35        | 4        |
| Full               | 40        | 4        |
| Poker              | 60        | 7        |
| Escalera de color  | 100       | 8        |
| Escalera real      | 100       | 8        |

Chips totales = chips base + suma de valores de cartas jugadas (A=11, K/Q/J=10, resto = su numero).

Score = Chips * Mult.

## Controles

- `1 2 3 4 5 6 7 8`: seleccionar/deseleccionar carta.
- `P`: jugar las cartas seleccionadas.
- `D`: descartar las cartas seleccionadas (vuelve a robar para tener 8 en mano; cuesta 1 descarte).
- `Q`: salir.

## Graficos

Cartas con representacion 2-char: rango (A/K/Q/J/T/2-9) + palo (H/D/S/C), con color por palo (rojo para H/D, blanco para S/C). Cajas con CP437 doble.
