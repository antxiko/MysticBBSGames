# Maze BBS

Roguelike turn-based de un jugador para Mystic BBS. Mazmorra procedural con descenso hasta el nivel del Dragon, amuleto de victoria, inventario, scrolls y trampas.

## Alcance

- Un solo `maze.py`. Solo stdlib.
- Char-mode via `termios`.
- Shadow buffer para no saturar el modem.
- Top 10 persistente en `maze_scores.txt`.

## UI 80x24

- Cabecera con nivel de mazmorra (`[BOSS]` en rojo al llegar al nivel 10).
- Mapa 76x16.
- Barra de stats con HP coloreado, inventario y flag de `[AMULETO]`.
- Linea de log con el ultimo mensaje.
- Linea de controles.

## Tiles

| Char | Que es            |
|------|-------------------|
| `@`  | Tu (verde normal / ambar si llevas el amuleto) |
| `r`  | Rata              |
| `g`  | Goblin            |
| `s`  | Esqueleto         |
| `G`  | Hobgoblin         |
| `o`  | Orco              |
| `T`  | Troll             |
| `O`  | Ogro              |
| `D`  | Dragon (boss)     |
| `#`  | Muro              |
| `.`  | Suelo             |
| `>`  | Escaleras         |
| `$`  | Oro               |
| `!`  | Pocion            |
| `/`  | Arma (+ATK)       |
| `[`  | Armadura (+DEF)   |
| `?`  | Scroll            |
| `&`  | Amuleto de Yendor |
| `^`  | Trampa (descubierta) |

## Enemigos

| Tipo      | HP  | ATK | DEF | XP  | Oro       |
|-----------|-----|-----|-----|-----|-----------|
| Rata      | 3   | 1   | 0   | 5   | 1-5       |
| Goblin    | 6   | 2   | 1   | 10  | 3-10      |
| Esqueleto | 10  | 3   | 2   | 18  | 5-12      |
| Hobgoblin | 15  | 3   | 1   | 20  | 8-18      |
| Orco      | 12  | 4   | 2   | 25  | 10-25     |
| Troll     | 25  | 6   | 3   | 50  | 25-60     |
| Ogro      | 35  | 8   | 4   | 80  | 40-80     |
| Dragon    | 150 | 15  | 8   | 500 | 200-500   |

Los enemigos escalan por nivel (+1 ATK/+1 DEF/+2 HP cada 2 niveles).

## Items y inventario

- `$` Oro: 5-30 al pisarlo (auto).
- `/` Arma: +1 ATK permanente (auto).
- `[` Armadura: +1 DEF permanente (auto).
- `!` Pocion: va al inventario.
- `?` Scroll: va al inventario. 3 tipos:
  - **Scroll de fuego**: 15 dano a todos enemigos adyacentes.
  - **Scroll de teletransporte**: te mueve a una casilla aleatoria.
  - **Scroll de mapeo**: revela el mapa completo del nivel.
- `&` Amuleto de Yendor: va al inventario; solo aparece en el nivel 10.

Max inventario: 10 items.

## Trampas

Ocultas en el suelo (invisibles hasta que las pisas). Dos tipos:
- **Pinchos**: 3-8 dano.
- **Teletransporte**: te tira a otra casilla.

Al descubrirlas aparecen como `^` coloreado.

## Mazmorra

- Grid 76x16. 6-10 habitaciones conectadas con pasillos en L.
- Niveles 1-9: escaleras `>` para bajar al siguiente nivel.
- Nivel 10 (Boss): spawn del Dragon + amuleto, sin escaleras hacia abajo.
- Tras conseguir el amuleto, las escaleras suben (`<`): cada uso te sube un nivel. Llegar al nivel 0 = victoria.

## Mecanica

### Combate
Dano = max(1, atk_atacante - def_defensor). Bump-to-attack: mueves hacia enemigo = atacas.

### Nivel del jugador
Sube cada `50 * nivel_actual` XP: +5 HP max, +1 ATK, +1 DEF cada dos niveles, HP restaurado al maximo.

### Victoria
Matar al Dragon, coger el Amuleto, volver a la superficie (nivel 0). Bonus +1000 puntos.

### Puntuacion final
`oro + xp * 2 + 1000 si victoria`.

## Controles

- `W A S D` o flechas: mover (bump a enemigo = atacar).
- `.` / `espacio`: esperar un turno.
- `>` / `<`: usar escaleras (baja sin amuleto, sube con amuleto).
- `i`: abrir inventario. Dentro, `1-9` para usar item, `ESC`/`Q` para cerrar.
- `Q`: salir de la partida.
