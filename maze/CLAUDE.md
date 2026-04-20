# Maze BBS

Roguelike turn-based de un jugador para Mystic BBS. Mazmorra procedural, descender niveles, matar bichos, coger loot, morir con estilo.

## Alcance

- Un solo `maze.py`. Solo stdlib.
- Char-mode via `termios` (como snake/buscaminas).
- **Shadow buffer** para no saturar el modem — solo se emiten las celdas que cambian.
- Top 10 persistente en `maze_scores.txt`.

## UI

80x24, con:
- Cabecera con nivel de mazmorra
- Mapa 76x16
- Barra de stats
- Linea de log (ultimo mensaje)
- Linea de controles
- Pie

## Tiles

| Char | Que es      |
|------|-------------|
| `@`  | Tu          |
| `r`  | Rata        |
| `g`  | Goblin      |
| `o`  | Orco        |
| `T`  | Troll       |
| `#`  | Muro        |
| `.`  | Suelo       |
| `>`  | Escaleras abajo |
| `$`  | Oro         |
| `!`  | Pocion (cura)|
| `/`  | Arma (+ATK) |
| `[`  | Armadura (+DEF) |

## Controles

- `W A S D` o flechas: mover. Si avanzas hacia un enemigo, le atacas.
- `.` o `espacio`: esperar un turno.
- `>`: bajar escaleras si estas en ellas.
- `Q`: salir.

## Mecanica

### Stats

Jugador empieza con HP 20/20, ATK 3, DEF 1. Sube nivel cada `50 * nivel_actual` XP: +5 HP max, +1 ATK, +1 DEF cada dos niveles, cura completa.

### Combate

Dano = `max(1, atk_atacante - def_defensor)`. No hay RNG de hit/miss: golpeas, haces dano. Tu pegas al moverte contra enemigo (bump). Enemigos pegan en su turno si estan adyacentes.

### Enemigos

| Tipo   | HP | ATK | DEF | XP | Oro    |
|--------|----|----|-----|-----|--------|
| Rata   | 3  | 1  | 0   | 5   | 1-5    |
| Goblin | 6  | 2  | 1   | 10  | 3-10   |
| Orco   | 12 | 4  | 2   | 25  | 10-25  |
| Troll  | 25 | 6  | 3   | 50  | 25-60  |

### Escalado por nivel

- Nivel 1: ratas, algun goblin.
- Nivel 2-3: goblins, algun orco.
- Nivel 4+: orcos, trolls. Cada +2 niveles suma +1 ATK/+1 DEF a cada enemigo.

### Items

- `$` Oro: 5-30 al pisarlo.
- `!` Pocion: cura 10 HP al pisarla.
- `/` Arma: +1 ATK permanente.
- `[` Armadura: +1 DEF permanente.

## Generacion de mazmorra

- Grid 76x16.
- Placeholder: 6-10 habitaciones rectangulares sin solapar.
- Conecto habitaciones con pasillos en L.
- Jugador en la primera habitacion, escaleras `>` en la ultima.
- Enemigos e items distribuidos en las demas.

## Fin de partida

Cuando HP <= 0. Puntuacion final = `oro + xp * 2`. Top 10 persistente con iniciales de 3 letras.
