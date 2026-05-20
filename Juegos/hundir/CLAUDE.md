# Hundir la Flota BBS

Clon del clasico turn-based contra IA. Dos grids 10x10 lado a lado:
mi flota a la izquierda, lo que se de la enemiga a la derecha. Mueves
cursor con flechas/WASD por el grid enemigo y disparas con ESPACIO.

## Alcance

- Un solo `hundir.py`. Solo stdlib.
- Char-mode con `termios` + `tty.setcbreak` (igual que el resto).
- Top 10 local + global via `bbs_scores`.

## Flota

| Barco        | Casillas |
|--------------|----------|
| Portaaviones | 5        |
| Acorazado    | 4        |
| Crucero      | 3        |
| Submarino    | 3        |
| Destructor   | 2        |
|              | 17 total |

## Colocacion

- Random sin solapar y sin tocarse (8-vecinos): los barcos quedan
  separados al menos por una casilla de agua.
- En la pantalla previa puedes pulsar `R` para volver a tirar la
  colocacion hasta que te guste. `ENTER` confirma.

## Controles

- `W A S D` / flechas: mover cursor por el grid enemigo.
- `ESPACIO` / `ENTER`: disparar a la casilla bajo el cursor.
- `R`: en la pantalla de colocacion, regenerar tu flota.
- `Q`: abandonar.

## Mecanica

- Turnos alternos: tu disparas, luego la IA.
- Tras un impacto sigues TU turno (regla clasica: hit = otro disparo).
- Si fallas, le toca a la IA.
- Mismo principio para la IA: si acierta, sigue tirando.
- Cada disparo solo se gasta una vez (no puedes repetir casilla).

## IA

- "Hunt + target" sin paridad (dificultad media).
- En modo hunt: dispara aleatoriamente entre casillas no probadas.
- Tras un impacto: encola los 4 vecinos ortogonales como targets.
- Al hundir un barco: limpia la cola, vuelve a hunt.
- No conoce dónde estan tus barcos (juega "limpio").

## Puntuacion

- +50 por cada impacto.
- +200 bonus por cada barco enemigo hundido.
- +500 bonus por ganar la partida.
- Bonus eficiencia: `max(0, 80 - tiros) * 10` (solo si ganas).
- Si pierdes, el score se queda en lo que llevabas (impactos + hundidos).

## Graficos

- Agua sin descubrir: `.` en azul dim.
- Mi barco visible: `#` en blanco.
- Agua disparada (miss): `o` en cyan.
- Impacto (hit): `X` en rojo brillante.
- Casilla de barco hundido: `#` en rojo.
- Cursor enemigo: video inverso sobre la casilla actual.
