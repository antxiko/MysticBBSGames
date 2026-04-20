# BBSATRO

Deckbuilder de poker inspirado en Balatro, adaptado a door de Mystic BBS. Juegas manos de poker para superar una puntuacion objetivo en cada ronda, con jokers que modifican el scoring, tienda entre rondas, boss blinds, y upgrade automatico de manos.

## Alcance

- Un solo `balatro.py` (el nombre del fichero es ese, el juego se muestra como "BBSATRO"). Solo stdlib.
- Shadow buffer para no saturar modem.
- Char-mode con `termios`.
- Baraja estandar 52 cartas, 4 palos (H D S C, colores rojo/blanco).
- 8 cartas en mano, seleccionas 1-5 para jugar.
- Por ronda: 4 manos, 3 descartes.
- Sistema de antes con 3 rondas cada una (Pequena, Grande, Boss); objetivo exponencial.
- Top 10 por puntuacion total acumulada en `bbsatro_scores.txt`.

## Cartas visuales

Cartas 7x5 con bordes CP437 `┌─┐│└┘`. Las seleccionadas se levantan una fila y cambian a borde amarillo. Rango arriba-izq y abajo-dcha, palo en el centro. Palos con letras (H D S C) coloreadas (rojo H/D, blanco S/C).

## Economia

- Oro inicial: 4.
- Ganas oro al pasar una ronda: base 3 + 1 por cada mano sin usar + 1 por cada descarte sin usar + interes 1 por cada 5 oro (cap 5).
- Gastas en la tienda para comprar jokers o rerollear.

## Jokers

20 jokers con efectos variados. Max 5 en inventario. Se aplican automaticamente en cada mano jugada.

Categorias:
- **Mult plano**: Joker (+4 Mult).
- **Mult condicional**: Jolly (+8 Mult si pareja), Zany (trio), Mad (doble pareja), Crazy (escalera), Droll (color).
- **Mult por palo**: Greedy (diamante), Lusty (corazon), Wrathful (pica), Gluttonous (trebol).
- **Chips condicional**: Sly (pareja), Wily (trio), Clever (doble), Devious (escalera), Crafty (color), Banner (por descarte restante).
- **Especiales**: Abstract (mult por joker), Misprint (mult aleatorio), Raised Fist (mult por carta baja), Even Steven (mult por carta par).

## Upgrade de manos

Cada vez que juegas un tipo de mano, ese tipo sube de nivel automaticamente. Niveles superiores dan +chips y +mult base extra (bonus por tipo: pareja +15/+1 por nivel, escalera +30/+3, poker +30/+3, etc.). Incentiva jugar la misma mano para escalar.

## Boss blinds

En la tercera ronda de cada ante (Boss), un efecto aleatorio de 5 posibles:
- **The Hook**: Tras cada mano jugada, se descartan 2 cartas al azar de tu mano.
- **The Ox**: Cada mano jugada te cuesta $3.
- **The Club**: Los treboles no puntuan.
- **The Plant**: Cartas de rango menor que 8 no puntuan.
- **The Needle**: Solo 1 mano para jugar en esta ronda.

## Tienda

Entre rondas ves la tienda con 2 jokers aleatorios (no repetidos de los que ya tengas). Puedes comprarlos si tienes oro y slots, o hacer reroll (precio empieza en $1 y sube con cada reroll).

## Controles

### En juego
- `1` `2` `3` `4` `5` `6` `7` `8`: seleccionar/deseleccionar carta.
- `P`: jugar las cartas seleccionadas.
- `D`: descartar las cartas seleccionadas.
- `Q`: salir.

### En tienda
- `1` o `2`: comprar el joker numero 1 o 2.
- `R`: rerollear los jokers (cuesta oro).
- `ENTER`/`ESC`/`Q`: continuar a la siguiente ronda.
