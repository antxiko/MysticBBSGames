# TypePython

Clon de `typespeed` (juego clasico de mecanografia de Linux) en espanol, pensado como door para Mystic BBS. Las palabras aparecen por la izquierda y se mueven hacia la derecha; el jugador las teclea (con Enter) antes de que crucen el borde derecho.

## Alcance

- **Un solo script**: `typepython.py`. Solo stdlib.
- **Python puro** lanzado como proceso externo (igual que `dopepython.py`). Sin `mystic_bbs`.
- **UI 80x24** con ANSI crudo en strings, stdout reconfigurado a CP437.
- **Sesion infinita** hasta perder las 3 vidas.
- **Top 10 persistente** en `scores.txt` junto al script.

## Arquitectura de I/O en tiempo real

Input no bloqueante sobre `stdin` con `fcntl` (O_NONBLOCK). El loop principal tickea a ~20 Hz (50 ms):

1. Spawn palabra nueva si toca.
2. Mover palabras existentes segun su intervalo.
3. Detectar cruce de borde derecho (pierde vida, desaparece).
4. Render del frame (solo area de juego + barra de estado, respetando la linea de prompt abajo con save/restore cursor).
5. Leer lo que haya llegado por stdin. Extraer lineas completas (terminadas en `\n`). Por cada linea: comprobar si hay palabra visible que coincida, puntuar, eliminar.
6. Dormir hasta el siguiente tick.

## Mecanica

- Palabras en espanol neutras, **ASCII only** (sin tildes ni enes). ~150 en el array.
- Nivel empieza en 1. Sube cada 10 palabras acertadas.
- Puntos = longitud palabra * nivel.
- Cada nivel: intervalo de movimiento baja 50 ms (min 100 ms), intervalo de spawn baja 200 ms (min 500 ms).
- 3 vidas. Pierde una por palabra cruzando el borde.

## Top 10

Fichero `scores.txt`, una linea por puntuacion:

```
NOMBRE;PUNTOS;FECHA
```

Nombre 3 caracteres en mayusculas (estilo arcade). Fecha ISO yyyy-mm-dd.
