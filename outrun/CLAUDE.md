# Outrun BBS

Racer pseudo-3D en ASCII puro inspirado en *Out Run* (Sega, 1986) y *Pole Position* (Namco, 1982). Carretera con perspectiva, horizonte, curvas que se interpolan por filas, sol al fondo y rayas blancas que vuelan a 200 km/h por la pantalla.

## Alcance

- Un solo `outrun.py`. Solo stdlib.
- Char-mode con `termios` + tick loop con `select`.
- Shadow buffer diferencial para no saturar el modem.
- Top 10 persistente en `outrun_scores.txt`.

## Mecanica

- **Tiempo total**: 90 segundos. Time-attack puro: cuando llega a 0, termina la carrera.
- **Puntuacion** = distancia recorrida en metros (escalado interno).
- **Curvatura**: la pista tiene una curva objetivo que cambia cada 2.5-5.0s a un valor aleatorio (-2.4 a +2.4) con lerp suave entre transiciones, asi que las curvas se sienten progresivas.
- **Drift en curva**: en una curva la inercia te empuja al exterior. Si no compensas con A/D acabas en la hierba.
- **Fuera de pista**: velocidad maxima 70 km/h y frena con fuerza brutal hasta llegar a ese tope. Mensaje "¡FUERA DE PISTA!" parpadeando.

## Render

80x24. Distribucion vertical:
- Filas 0-7: cielo (gradiente azul -> magenta) con sol amarillo.
- Fila 8: linea de horizonte.
- Filas 9-18: carretera con perspectiva.
- Filas 19-21: coche del jugador (sprite 9x3 con bloques CP437).
- Fila 22: separador.
- Fila 23: HUD con velocidad, distancia, tiempo, controles.

### Algoritmo de perspectiva

Para cada fila del area de carretera (de abajo arriba, de cerca a lejos):
1. `dy = fila - HORIZON` (1 a 10).
2. Acumular `dx += curva` y `x_off += dx`. Esto da la curva cuadratica clasica.
3. Half-width de la carretera en esa fila = `ROAD_HALF_W_NEAR * dy / max_dy`.
4. Centro en pantalla = `COLS/2 + x_off*0.06 - player_off * half_w * scale`.

Despues se pinta de **lejos a cerca** para que las filas cercanas tapen a las lejanas.

Por fila, segun `dy`:
- Hierba a izquierda/derecha con checkerboard 2-tonos verde que cicla con `z_pos` (efecto de scroll).
- Arcen estrecho con stripes rojo/blanco alternando con `z_pos` (efecto de velocidad).
- Linea central discontinua que avanza con `z_pos`.
- Asfalto en distintos tonos segun lejania (`▒`, `░`, dim/normal).

## Controles

- `W` / flecha arriba: acelerar.
- `S` / flecha abajo: frenar.
- `A` / flecha izquierda: girar a la izquierda.
- `D` / flecha derecha: girar a la derecha.
- `Q`: abandonar carrera (puntua lo recorrido).

## Constantes ajustables

| Constante           | Valor      | Que hace |
|---------------------|------------|----------|
| `TIEMPO_TOTAL`      | 90.0       | Segundos de carrera. |
| `SPEED_MAX`         | 240.0      | Velocidad maxima en pista. |
| `SPEED_OFFROAD_MAX` | 70.0       | Velocidad maxima fuera de pista. |
| `ROAD_HALF_W_NEAR`  | 28         | Semianchura de la carretera al borde inferior. |
| `CURVA_DRIFT`       | 0.0015     | Cuanto te tira la curva hacia fuera (por unidad de speed). |

## Estado

Real-time a ~30 FPS. Funciona en local. Pendiente probar en Mystic.
