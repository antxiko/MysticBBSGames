# Buscaminas BBS

El clasico buscaminas adaptado a modo texto para Mystic BBS. Cursor con WASD/flechas, espacio para revelar, F para bandera.

## Alcance

- Un solo `buscaminas.py`. Solo stdlib.
- Python externo como los demas juegos. stdout a CP437.
- Char-mode con `termios` + `tty.setcbreak` (igual que snake).
- Top 10 persistente en `buscaminas_scores.txt`.

## Dificultades

| Nivel       | Grid   | Minas |
|-------------|--------|-------|
| Principiante| 9x9    | 10    |
| Intermedio  | 16x16  | 40    |
| Experto     | 30x16  | 99    |

## Controles

- `W A S D` o flechas: mover cursor.
- `ESPACIO`: revelar la casilla bajo el cursor.
- `F`: alternar bandera.
- `Q`: salir.

## Mecanica

- La primera casilla revelada nunca es mina: las minas se colocan tras el primer click, evitando la casilla clickada y sus 8 vecinas.
- Si revelas una casilla con 0 minas adyacentes, se propaga flood-fill a todas las vecinas sin minas.
- Revelar una mina = derrota. Se muestran todas las minas.
- Victoria: todas las casillas sin mina reveladas.
- Cronometro: arranca con el primer click.
- Puntuacion: mayor al ganar mas rapido. `max(0, 1000 - segundos) * multiplicador_dificultad`.

## Graficos

- Casilla oculta: `░` (CP437 0xB0).
- Casilla revelada sin adyacentes: espacio.
- Numero 1-8: coloreado (1 azul, 2 verde, 3 rojo, 4 azul oscuro, 5 rojo oscuro, 6 cyan, 7 magenta, 8 blanco).
- Bandera: `P` en rojo brillante (puro ASCII, compatible).
- Mina revelada: `*` en rojo brillante.
- Cursor: reverse video sobre la casilla actual.
