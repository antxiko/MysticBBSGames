#!/usr/bin/env python3
"""Maze BBS - roguelike turn-based de un jugador."""
import os
import random
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="cp437", errors="replace")
except Exception:
    pass

try:
    import termios
    import tty
    TERMIOS_OK = True
except ImportError:
    TERMIOS_OK = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(SCRIPT_DIR, "maze_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24
MAP_W = 76
MAP_H = 16
MAP_X0 = 2  # col 0-based dentro del shadow buffer donde empieza el mapa
MAP_Y0 = 2

ROW_TITLE = 0
ROW_SEP1 = 1
ROW_MAP_TOP = MAP_Y0
ROW_MAP_BOT = MAP_Y0 + MAP_H - 1
ROW_SEP2 = ROW_MAP_BOT + 1
ROW_STATS = ROW_SEP2 + 1
ROW_SEP3 = ROW_STATS + 1
ROW_LOG = ROW_SEP3 + 1
ROW_SEP4 = ROW_LOG + 1
ROW_CTRL = ROW_SEP4 + 1

TILE_WALL = 0
TILE_FLOOR = 1

FOV_RADIO = 8

COLORES = {
    "rojo":    "\x1b[31m",
    "verde":   "\x1b[32m",
    "amar":    "\x1b[33m",
    "azul":    "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan":    "\x1b[36m",
    "blanco":  "\x1b[37m",
    "rojoB":   "\x1b[1;31m",
    "verdeB":  "\x1b[1;32m",
    "amarB":   "\x1b[1;33m",
    "azulB":   "\x1b[1;34m",
    "magentaB":"\x1b[1;35m",
    "cyanB":   "\x1b[1;36m",
    "blancoB": "\x1b[1;37m",
    "bold":    "\x1b[1m",
    "dim":     "\x1b[2m",
    "reverso": "\x1b[7m",
}
RESET = "\x1b[0m"


def c(txt, *estilos):
    if not estilos:
        return str(txt)
    prefijo = "".join(COLORES[e] for e in estilos if e in COLORES)
    if not prefijo:
        return str(txt)
    return f"{prefijo}{txt}{RESET}"


def at(row, col):
    return f"\x1b[{row};{col}H"


# ---------- shadow buffer ----------

SHADOW_ROWS = 24
SHADOW_COLS = 80
_shadow = [[" "] * SHADOW_COLS for _ in range(SHADOW_ROWS)]


def reset_shadow():
    global _shadow
    _shadow = [[" "] * SHADOW_COLS for _ in range(SHADOW_ROWS)]


def frame_nuevo():
    return [[" "] * SHADOW_COLS for _ in range(SHADOW_ROWS)]


def set_cell(frame, y, x, ch, *estilos):
    if not (0 <= y < SHADOW_ROWS and 0 <= x < SHADOW_COLS):
        return
    prefijo = "".join(COLORES[e] for e in estilos if e in COLORES)
    frame[y][x] = f"{prefijo}{ch}{RESET}" if prefijo else ch


def set_text(frame, y, x, texto, *estilos):
    prefijo = "".join(COLORES[e] for e in estilos if e in COLORES)
    sufijo = RESET if prefijo else ""
    for i, ch in enumerate(texto):
        cx = x + i
        if 0 <= y < SHADOW_ROWS and 0 <= cx < SHADOW_COLS:
            frame[y][cx] = f"{prefijo}{ch}{sufijo}" if prefijo else ch


def flush_frame(frame):
    global _shadow
    out = []
    for y in range(SHADOW_ROWS):
        for x in range(SHADOW_COLS):
            if frame[y][x] != _shadow[y][x]:
                out.append(at(y + 1, x + 1) + frame[y][x])
                _shadow[y][x] = frame[y][x]
    if out:
        sys.stdout.write("".join(out))
        sys.stdout.flush()


def cls():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()
    reset_shadow()


def show_cursor(v):
    return "\x1b[?25h" if v else "\x1b[?25l"


# ---------- terminal raw ----------

def entrar_cbreak():
    if not TERMIOS_OK:
        return None
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        return old
    except Exception:
        return None


def restaurar_terminal(old):
    if old is None or not TERMIOS_OK:
        return
    try:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
    except Exception:
        pass


def leer_tecla():
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        import select
        ready, _, _ = select.select([sys.stdin], [], [], 0.01)
        if not ready:
            return ch
        nxt = sys.stdin.read(1)
        if nxt != "[":
            return ch
        ready2, _, _ = select.select([sys.stdin], [], [], 0.01)
        if not ready2:
            return ch
        arr = sys.stdin.read(1)
        return f"\x1b[{arr}"
    return ch


# ---------- datos enemigos e items ----------

TIPOS_ENEMIGO = {
    "rata":      {"ch": "r", "hp": 3,   "atk": 1,  "def": 0, "xp": 5,   "oro": (1, 5),     "col": "amar"},
    "goblin":    {"ch": "g", "hp": 6,   "atk": 2,  "def": 1, "xp": 10,  "oro": (3, 10),    "col": "verde"},
    "esqueleto": {"ch": "s", "hp": 10,  "atk": 3,  "def": 2, "xp": 18,  "oro": (5, 12),    "col": "blancoB"},
    "hobgoblin": {"ch": "G", "hp": 15,  "atk": 3,  "def": 1, "xp": 20,  "oro": (8, 18),    "col": "verdeB"},
    "orco":      {"ch": "o", "hp": 12,  "atk": 4,  "def": 2, "xp": 25,  "oro": (10, 25),   "col": "rojo"},
    "troll":     {"ch": "T", "hp": 25,  "atk": 6,  "def": 3, "xp": 50,  "oro": (25, 60),   "col": "rojoB"},
    "ogro":      {"ch": "O", "hp": 35,  "atk": 8,  "def": 4, "xp": 80,  "oro": (40, 80),   "col": "magentaB"},
    "dragon":    {"ch": "D", "hp": 150, "atk": 15, "def": 8, "xp": 500, "oro": (200, 500), "col": "rojoB"},
}

TIPOS_ITEM = {
    "oro":          {"ch": "$", "col": "amarB"},
    "pocion":       {"ch": "!", "col": "rojoB"},
    "arma":         {"ch": "/", "col": "cyanB"},
    "armadura":     {"ch": "[", "col": "magentaB"},
    "scroll_fuego": {"ch": "?", "col": "rojoB"},
    "scroll_tp":    {"ch": "?", "col": "magentaB"},
    "scroll_mapa":  {"ch": "?", "col": "amarB"},
    "amuleto":      {"ch": "&", "col": "amarB"},
}

# Items que van al inventario en vez de auto-usarse
ITEMS_INVENTARIO = {"pocion", "scroll_fuego", "scroll_tp", "scroll_mapa", "amuleto"}
MAX_INVENTARIO = 10

TIPOS_TRAMPA = {
    "pinchos":  {"ch": "^", "col": "rojoB", "descripcion": "Pinchos", "dano": (3, 8)},
    "tp_trampa": {"ch": "^", "col": "cyanB", "descripcion": "Teletransporte", "dano": (0, 0)},
}

NIVEL_BOSS = 10  # en ese nivel aparece el dragon con el amuleto


def tabla_spawn(nivel):
    """Devuelve (tipo, count) de enemigos. Nivel 10 = solo dragon (boss)."""
    if nivel >= NIVEL_BOSS:
        # solo el dragon + unos cuantos orcos guardianes
        return [("orco", 2), ("troll", 1), ("dragon", 1)]
    if nivel == 1:
        return [("rata", 5), ("goblin", 2)]
    if nivel == 2:
        return [("rata", 3), ("goblin", 4), ("esqueleto", 1)]
    if nivel == 3:
        return [("goblin", 3), ("esqueleto", 2), ("hobgoblin", 1)]
    if nivel == 4:
        return [("esqueleto", 2), ("hobgoblin", 2), ("orco", 2)]
    if nivel == 5:
        return [("hobgoblin", 2), ("orco", 3), ("troll", 1)]
    if nivel == 6:
        return [("orco", 3), ("troll", 2), ("ogro", 1)]
    if nivel == 7:
        return [("orco", 2), ("troll", 2), ("ogro", 2)]
    # niveles 8-9: muchos duros
    return [("troll", 2), ("ogro", 2 + (nivel - 8))]


def escalar_enemigo(base, nivel):
    """Aplica bonus por nivel al enemigo."""
    e = dict(base)
    bonus = max(0, (nivel - 1) // 2)
    e["atk"] += bonus
    e["def"] += bonus
    e["hp"] += bonus * 2
    e["hp_max"] = e["hp"]
    return e


# ---------- generacion de mazmorra ----------

def solapa(a, b, margen=1):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 + margen < bx1 or bx2 + margen < ax1 or ay2 + margen < by1 or by2 + margen < ay1)


def centro(r):
    x1, y1, x2, y2 = r
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def tallar_habitacion(mapa, r):
    x1, y1, x2, y2 = r
    for y in range(y1 + 1, y2):
        for x in range(x1 + 1, x2):
            mapa[y][x] = TILE_FLOOR


def tallar_tunel(mapa, a, b):
    ax, ay = a
    bx, by = b
    if random.random() < 0.5:
        for x in range(min(ax, bx), max(ax, bx) + 1):
            mapa[ay][x] = TILE_FLOOR
        for y in range(min(ay, by), max(ay, by) + 1):
            mapa[y][bx] = TILE_FLOOR
    else:
        for y in range(min(ay, by), max(ay, by) + 1):
            mapa[y][ax] = TILE_FLOOR
        for x in range(min(ax, bx), max(ax, bx) + 1):
            mapa[by][x] = TILE_FLOOR


def celda_aleatoria_en(room):
    x1, y1, x2, y2 = room
    return (random.randint(x1 + 1, x2 - 1), random.randint(y1 + 1, y2 - 1))


def generar_mazmorra(nivel):
    mapa = [[TILE_WALL] * MAP_W for _ in range(MAP_H)]
    rooms = []
    intentos = 40
    n_rooms_objetivo = random.randint(6, 10)
    for _ in range(intentos):
        if len(rooms) >= n_rooms_objetivo:
            break
        w = random.randint(4, 10)
        h = random.randint(3, 5)
        x1 = random.randint(1, MAP_W - w - 2)
        y1 = random.randint(1, MAP_H - h - 2)
        nueva = (x1, y1, x1 + w, y1 + h)
        if any(solapa(nueva, r) for r in rooms):
            continue
        rooms.append(nueva)
        tallar_habitacion(mapa, nueva)
    for i in range(1, len(rooms)):
        tallar_tunel(mapa, centro(rooms[i - 1]), centro(rooms[i]))

    # jugador en la primera habitacion
    pjx, pjy = centro(rooms[0])
    # escaleras en la ultima
    escx, escy = centro(rooms[-1])

    enemigos = []
    ocupadas = {(pjx, pjy), (escx, escy)}
    tabla = tabla_spawn(nivel)
    for tipo, cantidad in tabla:
        base = TIPOS_ENEMIGO[tipo]
        for _ in range(cantidad):
            for _intento in range(20):
                if len(rooms) < 2:
                    break
                room = random.choice(rooms[1:])  # no en la habitacion inicial
                ex, ey = celda_aleatoria_en(room)
                if (ex, ey) in ocupadas:
                    continue
                if mapa[ey][ex] != TILE_FLOOR:
                    continue
                e = escalar_enemigo(base, nivel)
                e["x"] = ex
                e["y"] = ey
                e["tipo"] = tipo
                enemigos.append(e)
                ocupadas.add((ex, ey))
                break

    items = []
    trampas = []

    def spawn_item(tipo):
        for _intento in range(20):
            room = random.choice(rooms)
            ix, iy = celda_aleatoria_en(room)
            if (ix, iy) in ocupadas or mapa[iy][ix] != TILE_FLOOR:
                continue
            items.append({"x": ix, "y": iy, "tipo": tipo})
            ocupadas.add((ix, iy))
            break

    def spawn_trampa(tipo):
        for _intento in range(20):
            room = random.choice(rooms)
            tx, ty = celda_aleatoria_en(room)
            if (tx, ty) in ocupadas or mapa[ty][tx] != TILE_FLOOR:
                continue
            trampas.append({"x": tx, "y": ty, "tipo": tipo, "descubierta": False})
            ocupadas.add((tx, ty))
            break

    # Items por nivel
    spawn_item("pocion")
    if nivel >= 3:
        spawn_item("pocion")  # 2 pociones en niveles avanzados
    for _ in range(random.randint(1, 3)):
        spawn_item("oro")
    if random.random() < 0.35:
        spawn_item("arma")
    if random.random() < 0.35:
        spawn_item("armadura")
    # scrolls
    if random.random() < 0.30:
        spawn_item(random.choice(["scroll_fuego", "scroll_tp", "scroll_mapa"]))
    if nivel >= 4 and random.random() < 0.25:
        spawn_item(random.choice(["scroll_fuego", "scroll_tp", "scroll_mapa"]))

    # Amuleto: se coloca en el nivel del boss
    if nivel == NIVEL_BOSS:
        spawn_item("amuleto")

    # Trampas: probabilidad creciente con el nivel
    n_trampas = max(0, min(6, nivel // 2 + random.randint(0, 1)))
    for _ in range(n_trampas):
        spawn_trampa(random.choice(list(TIPOS_TRAMPA.keys())))

    # Escaleras: ninguna en el nivel boss (tienes que matar al dragon + volver)
    # En niveles normales hay escaleras abajo
    stairs = (escx, escy) if nivel < NIVEL_BOSS else None

    return {
        "mapa": mapa,
        "rooms": rooms,
        "enemigos": enemigos,
        "items": items,
        "trampas": trampas,
        "stairs": stairs,
        "player_start": (pjx, pjy),
        "visto": set(),          # celdas que hemos visto alguna vez
        "mapa_revelado": False,  # scroll de mapeo lo pone True
    }


# ---------- estado del jugador ----------

def nuevo_jugador():
    return {
        "x": 0, "y": 0,
        "hp": 20, "hp_max": 20,
        "atk": 3, "def": 1,
        "xp": 0, "nivel": 1,
        "oro": 0,
        "inventario": [],  # lista de strings de tipos de item
        "amuleto": False,
    }


def xp_para_subir(nivel):
    return nivel * 50


def subir_nivel_si(player, log):
    while player["xp"] >= xp_para_subir(player["nivel"]):
        player["xp"] -= xp_para_subir(player["nivel"])
        player["nivel"] += 1
        player["hp_max"] += 5
        player["atk"] += 1
        if player["nivel"] % 2 == 0:
            player["def"] += 1
        player["hp"] = player["hp_max"]
        log.append(f"Subes al nivel {player['nivel']}! +5 HP max, +1 ATK.")


# ---------- render ----------

def render(estado, log, nivel_mazmorra):
    frame = frame_nuevo()

    # cabecera
    es_boss = nivel_mazmorra >= NIVEL_BOSS
    titulo = f" MAZE BBS   Mazmorra nivel {nivel_mazmorra}{'  [BOSS]' if es_boss else ''} "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, ROW_TITLE, 0, "\u2550" * pad_l, "blancoB")
    set_text(frame, ROW_TITLE, pad_l, titulo, "rojoB" if es_boss else "amarB", "bold")
    set_text(frame, ROW_TITLE, pad_l + len(titulo), "\u2550" * (COLS - pad_l - len(titulo)), "blancoB")

    # separador
    set_text(frame, ROW_SEP1, 0, "\u2500" * COLS, "dim")

    # FOV
    mapa = estado["mapa"]
    p = estado["player"]
    visible = calcular_fov(mapa, p["x"], p["y"], FOV_RADIO)
    visto = estado["visto"]
    visto |= visible
    revelado = estado.get("mapa_revelado", False)

    # mapa base segun visibilidad
    for y in range(MAP_H):
        for x in range(MAP_W):
            en_vista = (x, y) in visible
            en_memoria = (x, y) in visto or revelado
            if mapa[y][x] == TILE_WALL:
                if en_vista:
                    set_cell(frame, MAP_Y0 + y, MAP_X0 + x, "#", "blanco")
                elif en_memoria:
                    set_cell(frame, MAP_Y0 + y, MAP_X0 + x, "#", "dim")
                # else: espacio (no dibujar)
            else:
                if en_vista:
                    set_cell(frame, MAP_Y0 + y, MAP_X0 + x, ".", "dim")
                # fuera de vista el suelo no se dibuja (solo muros se recuerdan)

    # trampas descubiertas (solo si visibles o en memoria)
    for t in estado.get("trampas", []):
        if not t["descubierta"]:
            continue
        if (t["x"], t["y"]) in visto or revelado:
            td = TIPOS_TRAMPA[t["tipo"]]
            col = td["col"] if (t["x"], t["y"]) in visible else "dim"
            set_cell(frame, MAP_Y0 + t["y"], MAP_X0 + t["x"], td["ch"], col, "bold")

    # escaleras (solo si las hemos visto)
    if estado.get("stairs"):
        esx, esy = estado["stairs"]
        if (esx, esy) in visto or revelado:
            col = "amarB" if (esx, esy) in visible else "dim"
            set_cell(frame, MAP_Y0 + esy, MAP_X0 + esx, ">", col, "bold")

    # items (solo visibles ahora)
    for it in estado["items"]:
        if (it["x"], it["y"]) not in visible:
            continue
        t = TIPOS_ITEM[it["tipo"]]
        set_cell(frame, MAP_Y0 + it["y"], MAP_X0 + it["x"], t["ch"], t["col"], "bold")

    # enemigos (solo visibles ahora, no recordados)
    for e in estado["enemigos"]:
        if (e["x"], e["y"]) not in visible:
            continue
        set_cell(frame, MAP_Y0 + e["y"], MAP_X0 + e["x"], e["ch"], TIPOS_ENEMIGO[e["tipo"]]["col"], "bold")

    # player
    col_player = "amarB" if p.get("amuleto") else "verdeB"
    set_cell(frame, MAP_Y0 + p["y"], MAP_X0 + p["x"], "@", col_player, "bold")

    # separador stats
    set_text(frame, ROW_SEP2, 0, "\u2500" * COLS, "dim")

    # stats
    hp_col = "verdeB" if p["hp"] > p["hp_max"] * 0.6 else ("amarB" if p["hp"] > p["hp_max"] * 0.3 else "rojoB")
    amu = "  [AMULETO]" if p.get("amuleto") else ""
    stats = (
        f" HP: {p['hp']}/{p['hp_max']}  ATK: {p['atk']}  DEF: {p['def']}  "
        f"XP: {p['xp']}/{xp_para_subir(p['nivel'])}  Lvl: {p['nivel']}  Oro: {p['oro']}  Inv: {len(p['inventario'])}/{MAX_INVENTARIO}{amu}"
    )
    set_text(frame, ROW_STATS, 0, stats, "blanco")
    hp_str = f"{p['hp']}/{p['hp_max']}"
    set_text(frame, ROW_STATS, 5, hp_str, hp_col, "bold")
    oro_col_x = stats.index("Oro:") + 5
    set_text(frame, ROW_STATS, oro_col_x, str(p['oro']), "amarB", "bold")
    if amu:
        amu_x = stats.index("[AMULETO]")
        set_text(frame, ROW_STATS, amu_x, "[AMULETO]", "amarB", "bold")

    # separador log
    set_text(frame, ROW_SEP3, 0, "\u2500" * COLS, "dim")

    # log (ultima linea)
    msg = log[-1] if log else ""
    msg = msg[:COLS - 2]
    set_text(frame, ROW_LOG, 1, msg, "cyanB")

    # separador ctrl
    set_text(frame, ROW_SEP4, 0, "\u2500" * COLS, "dim")

    # controles
    ctrl = " WASD mover    .  esperar    > escaleras    i inventario    Q  salir "
    set_text(frame, ROW_CTRL, (COLS - len(ctrl)) // 2, ctrl, "dim")

    flush_frame(frame)


# Descripciones para la pantalla de inventario
DESC_ITEM = {
    "pocion":       "Cura 10 HP",
    "scroll_fuego": "Dano 15 a enemigos adyacentes",
    "scroll_tp":    "Teletransporte aleatorio",
    "scroll_mapa":  "Revela todo el mapa",
    "amuleto":      "Llevalo al nivel 1 para ganar",
}


def render_inventario(estado):
    frame = frame_nuevo()
    titulo = " INVENTARIO "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, 0, 0, "\u2550" * pad_l, "blancoB")
    set_text(frame, 0, pad_l, titulo, "amarB", "bold")
    set_text(frame, 0, pad_l + len(titulo), "\u2550" * (COLS - pad_l - len(titulo)), "blancoB")

    p = estado["player"]
    set_text(frame, 2, 2, f"Objetos ({len(p['inventario'])}/{MAX_INVENTARIO}):", "cyanB", "bold")

    y = 4
    if not p["inventario"]:
        set_text(frame, y, 4, "(inventario vacio)", "dim")
    else:
        for i, tipo in enumerate(p["inventario"]):
            if i >= 9:
                break
            nombre = NOMBRES_ITEM.get(tipo, tipo)
            desc = DESC_ITEM.get(tipo, "")
            set_text(frame, y, 4, f"{i+1}) {nombre}", "verdeB", "bold")
            set_text(frame, y, 30, desc, "blanco")
            y += 1

    set_text(frame, 22, (COLS - 36) // 2, " 1-9 usar    ESC/I/Q volver ", "dim")
    flush_frame(frame)


# ---------- movimiento y combate ----------

def en_mapa(x, y):
    return 0 <= x < MAP_W and 0 <= y < MAP_H


def linea_libre(mapa, x1, y1, x2, y2):
    """Bresenham: devuelve True si no hay muro entre (x1,y1) y (x2,y2).
    El destino puede ser muro sin bloquear (vemos el propio muro)."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    x, y = x1, y1
    while True:
        if (x, y) == (x2, y2):
            return True
        if (x, y) != (x1, y1) and mapa[y][x] == TILE_WALL:
            return False
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def calcular_fov(mapa, px, py, radio=FOV_RADIO):
    """Devuelve set de (x, y) visibles desde (px, py)."""
    visible = {(px, py)}
    r2 = radio * radio
    for y in range(max(0, py - radio), min(MAP_H, py + radio + 1)):
        for x in range(max(0, px - radio), min(MAP_W, px + radio + 1)):
            if (x - px) ** 2 + (y - py) ** 2 > r2:
                continue
            if linea_libre(mapa, px, py, x, y):
                visible.add((x, y))
    return visible


def enemigo_en(estado, x, y):
    for e in estado["enemigos"]:
        if e["x"] == x and e["y"] == y:
            return e
    return None


def item_en(estado, x, y):
    for it in estado["items"]:
        if it["x"] == x and it["y"] == y:
            return it
    return None


def atacar_jugador_a_enemigo(estado, enemigo, log):
    p = estado["player"]
    dano = max(1, p["atk"] - enemigo["def"])
    enemigo["hp"] -= dano
    if enemigo["hp"] <= 0:
        xp_ganado = enemigo["xp"]
        lo, hi = TIPOS_ENEMIGO[enemigo["tipo"]]["oro"]
        oro = random.randint(lo, hi)
        p["xp"] += xp_ganado
        p["oro"] += oro
        log.append(f"Matas al {enemigo['tipo']}: +{xp_ganado} XP, +{oro} oro.")
        estado["enemigos"].remove(enemigo)
        subir_nivel_si(p, log)
    else:
        log.append(f"Atacas al {enemigo['tipo']}: -{dano} HP. ({enemigo['hp']}/{enemigo['hp_max']})")


def atacar_enemigo_a_jugador(estado, enemigo, log):
    p = estado["player"]
    dano = max(1, enemigo["atk"] - p["def"])
    p["hp"] -= dano
    log.append(f"El {enemigo['tipo']} te ataca: -{dano} HP.")


NOMBRES_ITEM = {
    "pocion":       "Pocion",
    "scroll_fuego": "Scroll de fuego",
    "scroll_tp":    "Scroll de teletransporte",
    "scroll_mapa":  "Scroll de mapeo",
    "amuleto":      "Amuleto de Yendor",
}


def recoger_item(estado, it, log):
    p = estado["player"]
    tipo = it["tipo"]
    if tipo == "oro":
        ganado = random.randint(5, 30)
        p["oro"] += ganado
        log.append(f"Coges {ganado} de oro.")
    elif tipo == "arma":
        p["atk"] += 1
        log.append(f"Nueva arma! +1 ATK (ahora {p['atk']}).")
    elif tipo == "armadura":
        p["def"] += 1
        log.append(f"Nueva armadura! +1 DEF (ahora {p['def']}).")
    elif tipo == "amuleto":
        p["amuleto"] = True
        p["inventario"].append(tipo)
        log.append("¡Coges el AMULETO DE YENDOR! Vuelve a la superficie.")
    elif tipo in ITEMS_INVENTARIO:
        if len(p["inventario"]) >= MAX_INVENTARIO:
            log.append(f"Tu bolsa esta llena. Dejas el {NOMBRES_ITEM.get(tipo, tipo)}.")
            return
        p["inventario"].append(tipo)
        log.append(f"Guardas {NOMBRES_ITEM.get(tipo, tipo)}. (inv: {len(p['inventario'])}/{MAX_INVENTARIO})")
    estado["items"].remove(it)


def usar_item(estado, idx, log):
    """Usa el item del inventario en indice idx. Devuelve True si se uso."""
    p = estado["player"]
    if idx < 0 or idx >= len(p["inventario"]):
        return False
    tipo = p["inventario"][idx]
    if tipo == "pocion":
        cura = 10
        p["hp"] = min(p["hp_max"], p["hp"] + cura)
        log.append(f"Bebes una pocion. +{cura} HP.")
        p["inventario"].pop(idx)
        return True
    if tipo == "scroll_fuego":
        # dano a todos enemigos adyacentes
        dano = 15
        victimas = []
        for e in list(estado["enemigos"]):
            if adyacente(e["x"], e["y"], p["x"], p["y"]):
                e["hp"] -= dano
                victimas.append(e["tipo"])
                if e["hp"] <= 0:
                    lo, hi = TIPOS_ENEMIGO[e["tipo"]]["oro"]
                    p["xp"] += e["xp"]
                    p["oro"] += random.randint(lo, hi)
                    estado["enemigos"].remove(e)
        if victimas:
            log.append(f"Lanzas bola de fuego: {dano} dano a {len(victimas)} enemigos.")
            subir_nivel_si(p, log)
        else:
            log.append("Lanzas bola de fuego, pero no hay nadie alrededor.")
        p["inventario"].pop(idx)
        return True
    if tipo == "scroll_tp":
        # teletransporte a casilla de suelo aleatoria segura
        candidatas = []
        for y in range(MAP_H):
            for x in range(MAP_W):
                if estado["mapa"][y][x] == TILE_FLOOR and not enemigo_en(estado, x, y) and (x, y) != (p["x"], p["y"]):
                    candidatas.append((x, y))
        if candidatas:
            p["x"], p["y"] = random.choice(candidatas)
            log.append("Desapareces en una nube de humo. Apareces en otro lugar.")
        p["inventario"].pop(idx)
        return True
    if tipo == "scroll_mapa":
        estado["mapa_revelado"] = True
        log.append("El mapa del nivel se te revela.")
        p["inventario"].pop(idx)
        return True
    if tipo == "amuleto":
        log.append("El amuleto resplandece. No lo puedes 'usar'; llevalo a la salida.")
        return False
    return False


def trampa_en(estado, x, y):
    for t in estado.get("trampas", []):
        if t["x"] == x and t["y"] == y:
            return t
    return None


def pisar_trampa(estado, trampa, log):
    p = estado["player"]
    trampa["descubierta"] = True
    tipo = trampa["tipo"]
    if tipo == "pinchos":
        lo, hi = TIPOS_TRAMPA[tipo]["dano"]
        dano = random.randint(lo, hi)
        p["hp"] -= dano
        log.append(f"Pinchos te atraviesan el pie: -{dano} HP.")
    elif tipo == "tp_trampa":
        candidatas = []
        for y in range(MAP_H):
            for x in range(MAP_W):
                if estado["mapa"][y][x] == TILE_FLOOR and not enemigo_en(estado, x, y) and (x, y) != (p["x"], p["y"]):
                    candidatas.append((x, y))
        if candidatas:
            p["x"], p["y"] = random.choice(candidatas)
            log.append("Pisas una losa y apareces en otro lado.")


def mover_jugador(estado, dx, dy, log):
    p = estado["player"]
    nx, ny = p["x"] + dx, p["y"] + dy
    if not en_mapa(nx, ny):
        return False
    if estado["mapa"][ny][nx] == TILE_WALL:
        return False
    enemigo = enemigo_en(estado, nx, ny)
    if enemigo:
        atacar_jugador_a_enemigo(estado, enemigo, log)
        return True
    p["x"], p["y"] = nx, ny
    it = item_en(estado, nx, ny)
    if it:
        recoger_item(estado, it, log)
    tr = trampa_en(estado, p["x"], p["y"])
    if tr:
        pisar_trampa(estado, tr, log)
    return True


def adyacente(a_x, a_y, b_x, b_y):
    return abs(a_x - b_x) <= 1 and abs(a_y - b_y) <= 1 and (a_x, a_y) != (b_x, b_y)


def turno_enemigos(estado, log):
    p = estado["player"]
    for e in list(estado["enemigos"]):
        if e["hp"] <= 0:
            continue
        if adyacente(e["x"], e["y"], p["x"], p["y"]):
            atacar_enemigo_a_jugador(estado, e, log)
            if p["hp"] <= 0:
                return
            continue
        dist = abs(e["x"] - p["x"]) + abs(e["y"] - p["y"])
        if dist > 8:
            continue
        # mover hacia el jugador
        dx = 1 if p["x"] > e["x"] else (-1 if p["x"] < e["x"] else 0)
        dy = 1 if p["y"] > e["y"] else (-1 if p["y"] < e["y"] else 0)
        if abs(p["x"] - e["x"]) > abs(p["y"] - e["y"]):
            dy = 0
        else:
            dx = 0
        nx, ny = e["x"] + dx, e["y"] + dy
        if not en_mapa(nx, ny):
            continue
        if estado["mapa"][ny][nx] == TILE_WALL:
            continue
        if (nx, ny) == (p["x"], p["y"]):
            continue
        if any(o is not e and o["x"] == nx and o["y"] == ny for o in estado["enemigos"]):
            continue
        e["x"], e["y"] = nx, ny


# ---------- scores y splash ----------

def cargar_scores():
    if not os.path.exists(SCORES_FILE):
        return []
    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            out = []
            for linea in f:
                parts = linea.strip().split(";")
                if len(parts) == 4:
                    nombre, puntos, nivel, fecha = parts
                    try:
                        out.append((nombre, int(puntos), int(nivel), fecha))
                    except ValueError:
                        continue
            return sorted(out, key=lambda x: -x[1])[:MAX_TOP]
    except OSError:
        return []


def guardar_score(nombre, puntos, nivel):
    scores = cargar_scores()
    scores.append((nombre, puntos, nivel, date.today().isoformat()))
    scores = sorted(scores, key=lambda x: -x[1])[:MAX_TOP]
    try:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            for n, p, nv, fe in scores:
                f.write(f"{n};{p};{nv};{fe}\n")
    except OSError:
        pass
    return scores


def es_top(puntos):
    if puntos <= 0:
        return False
    scores = cargar_scores()
    if len(scores) < MAX_TOP:
        return True
    return puntos > scores[-1][1]


LOGO_MAZE = [
    "\u2588\u2588\u2588\u2557   \u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u255A\u2550\u2550\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D",
    "\u2588\u2588\u2554\u2588\u2588\u2588\u2588\u2554\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551  \u2588\u2588\u2588\u2554\u255D \u2588\u2588\u2588\u2588\u2588\u2557  ",
    "\u2588\u2588\u2551\u255A\u2588\u2588\u2554\u255D\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551 \u2588\u2588\u2588\u2554\u255D  \u2588\u2588\u2554\u2550\u2550\u255D  ",
    "\u2588\u2588\u2551 \u255A\u2550\u255D \u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u255A\u2550\u255D     \u255A\u2550\u255D\u255A\u2550\u255D  \u255A\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D",
]

LOGO_BBS = [
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u255A\u2550\u2550\u2550\u2550\u2588\u2588\u2551",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551",
    "\u255A\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D",
]


def _caja_linea_splash(texto, ancho, color_txt, color_caja="verdeB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("\u2551", color_caja) + cuerpo + c("\u2551", color_caja)


def splash():
    cls()
    sys.stdout.write(show_cursor(True))
    ancho = 60
    print()
    print(c("\u2554" + "\u2550" * ancho + "\u2557", "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_MAZE:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Roguelike turn-based de un jugador", ancho, "cyanB"))
    print(_caja_linea_splash("Baja niveles, mata bichos, coge loot.", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("\u255A" + "\u2550" * ancho + "\u255D", "verdeB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_final(player, nivel_mazmorra, victoria):
    sys.stdout.write(show_cursor(True))
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "\u2550" * ancho
    color_marco = "verdeB" if victoria else "rojoB"
    lado = c("\u2551", color_marco)
    bonus_victoria = 1000 if victoria else 0
    puntos = player["oro"] + player["xp"] * 2 + bonus_victoria

    def fila_centrada(texto, *estilos):
        pad_total = ancho - len(texto)
        pad_l = pad_total // 2
        pad_r = pad_total - pad_l
        return margen + lado + " " * pad_l + c(texto, *estilos) + " " * pad_r + lado

    def fila_kv(label, val, col):
        prefijo = f"  {label}"
        plano = prefijo + val
        pad = ancho - len(plano)
        return margen + lado + prefijo + c(val, col, "bold") + " " * pad + lado

    print(margen + c("\u2554" + linea + "\u2557", color_marco))
    titulo = "¡VICTORIA! Escapaste con el Amuleto" if victoria else "HAS MUERTO"
    print(fila_centrada(titulo, "bold"))
    print(margen + c("\u2560" + linea + "\u2563", color_marco))
    print(fila_kv("Nivel mas profundo : ", str(nivel_mazmorra).rjust(18), "amarB"))
    print(fila_kv("Nivel jugador      : ", str(player["nivel"]).rjust(18), "amarB"))
    print(fila_kv("XP acumulado       : ", str(player["xp"]).rjust(18), "cyanB"))
    print(fila_kv("Oro                : ", str(player["oro"]).rjust(18), "amarB"))
    if victoria:
        print(fila_kv("Bonus victoria     : ", "1000".rjust(18), "verdeB"))
    print(fila_kv("Puntuacion         : ", str(puntos).rjust(18), "verdeB"))
    print(margen + c("\u255A" + linea + "\u255D", color_marco))
    print()

    if es_top(puntos) or victoria:
        if es_top(puntos):
            print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
        nombre = ""
        while not nombre:
            try:
                raw = input(margen + "  Iniciales (3 letras): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalpha())[:3].ljust(3, "A")
        scores = guardar_score(nombre, puntos, nivel_mazmorra)
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("\u2500" * ancho, "dim"))
    for i, (n, p, nv, fe) in enumerate(scores, 1):
        color = "amarB" if p == puntos else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(6), color)}  Nv.{nv:<2}  {c(fe, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- main ----------

def abrir_inventario(estado, log):
    """Pantalla modal de inventario. Devuelve True si se uso un item (consume turno)."""
    while True:
        render_inventario(estado)
        tecla = leer_tecla()
        if tecla in ("\x1b", "q", "Q", "i", "I"):
            return False
        if tecla in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            idx = int(tecla) - 1
            if usar_item(estado, idx, log):
                return True


def jugar():
    player = nuevo_jugador()
    nivel_mazmorra = 1
    estado = generar_mazmorra(nivel_mazmorra)
    player["x"], player["y"] = estado["player_start"]
    estado["player"] = player
    log = ["Bienvenido a la mazmorra. Busca el Amuleto de Yendor."]

    cls()
    sys.stdout.write(show_cursor(False))
    render(estado, log, nivel_mazmorra)

    victoria = False

    while player["hp"] > 0:
        tecla = leer_tecla()
        dx, dy = 0, 0
        accion = False
        usar_escaleras = False
        if tecla in ("w", "W", "\x1b[A"):
            dy = -1
        elif tecla in ("s", "S", "\x1b[B"):
            dy = 1
        elif tecla in ("a", "A", "\x1b[D"):
            dx = -1
        elif tecla in ("d", "D", "\x1b[C"):
            dx = 1
        elif tecla in (".", " "):
            accion = True
        elif tecla in (">", "<"):
            usar_escaleras = True
        elif tecla in ("i", "I"):
            cls()  # reset shadow para la pantalla modal
            uso = abrir_inventario(estado, log)
            cls()  # reset al volver al juego
            render(estado, log, nivel_mazmorra)
            if uso:
                accion = True
                if player["hp"] > 0:
                    turno_enemigos(estado, log)
                render(estado, log, nivel_mazmorra)
            continue
        elif tecla in ("q", "Q", "\x03"):
            return player, nivel_mazmorra, victoria
        else:
            continue

        if usar_escaleras:
            if estado.get("stairs") and (player["x"], player["y"]) == estado["stairs"]:
                if player.get("amuleto"):
                    # SUBIR hacia la salida
                    nivel_mazmorra -= 1
                    if nivel_mazmorra < 1:
                        victoria = True
                        log.append("¡Escapas a la superficie con el Amuleto! VICTORIA.")
                        break
                    estado = generar_mazmorra(nivel_mazmorra)
                    player["x"], player["y"] = estado["player_start"]
                    estado["player"] = player
                    log.append(f"Subes al nivel {nivel_mazmorra}.")
                else:
                    # BAJAR al siguiente nivel
                    nivel_mazmorra += 1
                    estado = generar_mazmorra(nivel_mazmorra)
                    player["x"], player["y"] = estado["player_start"]
                    estado["player"] = player
                    log.append(f"Bajas al nivel {nivel_mazmorra} de la mazmorra.")
                cls()
                render(estado, log, nivel_mazmorra)
                continue
            else:
                log.append("No hay escaleras aqui.")
                render(estado, log, nivel_mazmorra)
                continue

        if dx != 0 or dy != 0:
            movido = mover_jugador(estado, dx, dy, log)
            if not movido:
                render(estado, log, nivel_mazmorra)
                continue
            accion = True

        if accion:
            if player["hp"] > 0:
                turno_enemigos(estado, log)
        render(estado, log, nivel_mazmorra)

    return player, nivel_mazmorra, victoria


def main():
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. Maze necesita un TTY.")
        return
    try:
        restaurar_terminal(old)
        splash()
        while True:
            old2 = entrar_cbreak()
            player, nivel_mazmorra, victoria = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            if player["hp"] <= 0 or victoria:
                pantalla_final(player, nivel_mazmorra, victoria)
            try:
                raw = input("\n  Otra partida? [S/N]: ").strip().upper()
            except EOFError:
                raw = "N"
            if not raw.startswith("S"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            restaurar_terminal(old)
        except Exception:
            pass
        sys.stdout.write(show_cursor(True))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
