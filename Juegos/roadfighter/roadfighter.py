#!/usr/bin/env python3
"""Road Fighter BBS - racer cenital con curvas horizontales, esquiva enemigos."""
import math
import os
import random
import sys
import time
from datetime import date

# Cliente compartido para scores: vive en la raiz del repo.
_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)                    # flat: bbs_scores en la misma carpeta
sys.path.insert(0, os.path.dirname(_d))   # subdirs: bbs_scores un nivel arriba
import bbs_scores  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="cp437", errors="replace")
except Exception:
    pass


def configurar_backspace():
    try:
        import termios
        fd = sys.stdin.fileno()
        attrs = termios.tcgetattr(fd)
        attrs[6][termios.VERASE] = b"\x08"
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
    except Exception:
        pass


configurar_backspace()


try:
    import termios
    import tty
    import select
    TERMIOS_OK = True
except ImportError:
    TERMIOS_OK = False


COLS = 80
ROWS = 24

# Carretera (columnas base, sin curva)
ROAD_LEFT = 22
ROAD_RIGHT = 57
ROAD_W = ROAD_RIGHT - ROAD_LEFT + 1
ROAD_CENTER = (ROAD_LEFT + ROAD_RIGHT) // 2

# Sprites 3 cols x 3 filas
SPRITE_W = 3
SPRITE_H = 3
PLAYER_Y = 19  # fila top del sprite del jugador
PLAYER_CX_OFFSET = 1  # centro del sprite respecto a su top-left col

# HUD
HUD_TOP = 22
HUD_BOT = 23

TIEMPO_TOTAL = 60.0
SPEED_INI = 50.0
SPEED_MAX = 280.0
SPEED_ACEL = 35.0
SPEED_ROZA = 12.0
SPEED_FREN = 130.0
SPEED_OFFROAD_MAX = 90.0
SPEED_OFFROAD_DRAG = 220.0
STEER_VEL = 32.0  # cols/seg al maximo

SPEED_TRAS_CHOQUE = 30.0

ENEMY_SPAWN_MIN = 0.35
ENEMY_SPAWN_MAX = 1.10
ENEMY_SPEED_MIN_FACTOR = 0.10
ENEMY_SPEED_MAX_FACTOR = 0.55
MAX_ENEMIES = 2

FPS = 20
FRAME_DT = 1.0 / FPS
SCENERY_SPAWN_MIN = 0.18
SCENERY_SPAWN_MAX = 0.50

# Conversion de speed a world-units por frame y a metros mostrados
WORLD_SCALE = 0.15
DIST_SCALE = 0.10

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_TOP = 10
ASCENDING = False  # True si menos = mejor

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
            if y == SHADOW_ROWS - 1 and x == SHADOW_COLS - 1:
                continue
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


def entrar_cbreak():
    if not TERMIOS_OK:
        return None
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        mode = termios.tcgetattr(fd)
        mode[3] &= ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSAFLUSH, mode)
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


def leer_tecla_noblock():
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        ready2, _, _ = select.select([sys.stdin], [], [], 0.01)
        if not ready2:
            return ch
        nxt = sys.stdin.read(1)
        if nxt != "[":
            return ch
        ready3, _, _ = select.select([sys.stdin], [], [], 0.01)
        if not ready3:
            return ch
        arr = sys.stdin.read(1)
        return f"\x1b[{arr}"
    return ch


# ---------- curva de la carretera ----------

def curva_horizontal(world_y):
    """Desplazamiento horizontal del centro de la carretera para una posicion world_y.
    Suma de dos senos para que la curva sea variada y no repetitiva obvia."""
    return math.sin(world_y * 0.035) * 7.0 + math.sin(world_y * 0.012) * 4.0


# ---------- sprites ----------

CAR_SPRITE = [
    "▟█▙",
    "███",
    "▜█▛",
]
TREE_SPRITE = [
    " ▲ ",
    "▲█▲",
    " █ ",
]
HOUSE_SPRITE = [
    "▟▀▙",
    "███",
    "█▌█",
]
ROCK_SPRITE = [
    " ▄ ",
    "▟█▙",
    "▀▀▀",
]

SCENERY_KINDS = [
    (TREE_SPRITE, "verdeB"),
    (TREE_SPRITE, "verde"),
    (HOUSE_SPRITE, "cyanB"),
    (HOUSE_SPRITE, "magentaB"),
    (ROCK_SPRITE, "blanco"),
]


def pintar_sprite(frame, x, y, sprite, color):
    for j, ln in enumerate(sprite):
        for i, ch in enumerate(ln):
            if ch != " ":
                set_cell(frame, y + j, x + i, ch, color)


# ---------- render ----------

def render(frame, world_offset, player_x, speed, enemies, scenery,
           dist, t_left, overtakes, crashes, throttle, braking, steer_dir,
           hit_flash, off_road):
    # fondo + carretera fila a fila aplicando la curva horizontal a cada fila.
    # Hierba ESTATICA, arcenes ESTATICOS (solid color), solo la linea central scroll.
    lane_phase = int(world_offset * 0.3)  # solo linea central anima
    for row in range(ROWS - 2):
        world_y_row = world_offset + (PLAYER_Y - row)
        offset_curva = int(curva_horizontal(world_y_row))
        left = ROAD_LEFT + offset_curva
        right = ROAD_RIGHT + offset_curva
        lane_w = (right - left - 1) // 3
        c1 = left + lane_w
        c2 = left + 2 * lane_w
        center_on = ((lane_phase + row) % 4) < 2

        for col in range(COLS):
            if col <= left - 2 or col >= right + 2:
                # hierba ESTATICA: checkerboard fijo
                if ((row + col) & 1) == 0:
                    set_cell(frame, row, col, "▒", "verde")
                else:
                    set_cell(frame, row, col, "░", "verde")
            elif col == left - 1 or col == right + 1:
                # arcen ESTATICO solido rojo
                set_cell(frame, row, col, "█", "rojoB")
            elif col == left or col == right:
                set_cell(frame, row, col, "│", "blancoB")
            else:
                if (col == c1 or col == c2) and center_on:
                    set_cell(frame, row, col, "│", "amarB")
                # asfalto: blank por defecto en frame_nuevo

    # scenery: fija en world; su sprite ocupa 3 filas, lo pintamos cuando entra en pantalla
    for s in scenery:
        sy = int(s["y"])
        if -3 <= sy < ROWS - 2:
            pintar_sprite(frame, s["x"], sy, s["sprite"], s["color"])

    # enemigos: siguen el carril relativo al centro de la carretera en su world_y
    for e in enemies:
        ey = int(PLAYER_Y - (e["world_y"] - world_offset))
        if -3 <= ey < ROWS - 2:
            world_y_aqui = world_offset + (PLAYER_Y - ey)
            ex = int(ROAD_CENTER + curva_horizontal(world_y_aqui) + e["lane"]) - 1
            pintar_sprite(frame, ex, ey, CAR_SPRITE, e["color"])

    # jugador
    color_player = "rojoB"
    if hit_flash > 0 and (int(hit_flash * 20) % 2) == 0:
        color_player = "amarB"
    pintar_sprite(frame, int(player_x) - PLAYER_CX_OFFSET, PLAYER_Y, CAR_SPRITE, color_player)

    # HUD
    set_text(frame, HUD_TOP, 0, "═" * COLS, "magentaB")
    speed_kmh = int(speed)
    speed_color = "verdeB" if speed_kmh < 120 else ("amarB" if speed_kmh < 220 else "rojoB")
    set_text(frame, HUD_BOT, 1, "VEL", "blanco")
    set_text(frame, HUD_BOT, 5, f"{speed_kmh:>3}", speed_color, "bold")
    barra_max = 10
    barra_n = min(barra_max, int(speed_kmh * barra_max / SPEED_MAX))
    set_text(frame, HUD_BOT, 9, "[" + "█" * barra_n + "·" * (barra_max - barra_n) + "]", speed_color)

    set_text(frame, HUD_BOT, 22, "DIST", "blanco")
    set_text(frame, HUD_BOT, 27, f"{int(dist):>5}", "cyanB", "bold")

    set_text(frame, HUD_BOT, 36, "ADELANT.", "blanco")
    set_text(frame, HUD_BOT, 45, f"{overtakes:>3}", "verdeB", "bold")

    set_text(frame, HUD_BOT, 51, "CHOQUES", "blanco")
    set_text(frame, HUD_BOT, 59, f"{crashes:>2}", "rojoB", "bold")

    set_text(frame, HUD_BOT, 64, "TIME", "blanco")
    t_color = "verdeB" if t_left > 30 else ("amarB" if t_left > 10 else "rojoB")
    set_text(frame, HUD_BOT, 69, f"{int(max(0, t_left)):>3}s", t_color, "bold")

    # indicadores de estado
    estado_w = ("W", "verdeB", "bold") if throttle == 1 else ("W", "dim")
    estado_s = ("S", "rojoB", "bold") if braking else ("S", "dim")
    estado_a = ("A", "amarB", "bold") if steer_dir == -1 else ("A", "dim")
    estado_d = ("D", "amarB", "bold") if steer_dir == 1 else ("D", "dim")
    set_text(frame, HUD_TOP, 60, "[", "dim")
    set_text(frame, HUD_TOP, 61, estado_w[0], *estado_w[1:])
    set_text(frame, HUD_TOP, 62, estado_s[0], *estado_s[1:])
    set_text(frame, HUD_TOP, 63, estado_a[0], *estado_a[1:])
    set_text(frame, HUD_TOP, 64, estado_d[0], *estado_d[1:])
    set_text(frame, HUD_TOP, 65, "] Q salir", "dim")

    if off_road:
        msg = " ¡FUERA DE PISTA! "
        set_text(frame, HUD_TOP, (COLS - len(msg)) // 2, msg, "amarB", "bold")



# ---------- splash y final ----------

LOGO_ROAD = [
    "██████╗  ██████╗  █████╗ ██████╗ ",
    "██╔══██╗██╔═══██╗██╔══██╗██╔══██╗",
    "██████╔╝██║   ██║███████║██║  ██║",
    "██╔══██╗██║   ██║██╔══██║██║  ██║",
    "██║  ██║╚██████╔╝██║  ██║██████╔╝",
    "╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ ",
]

LOGO_FIGHT = [
    "███████╗██╗ ██████╗ ██╗  ██╗████████╗",
    "██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝",
    "█████╗  ██║██║  ███╗███████║   ██║   ",
    "██╔══╝  ██║██║   ██║██╔══██║   ██║   ",
    "██║     ██║╚██████╔╝██║  ██║   ██║   ",
    "╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ",
]


def _caja_linea(texto, ancho, color_txt, color_caja="magentaB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


MANUAL_LINEAS = [
    ('PREMISA', 'cyanB', 'bold'),
    '  Racer cenital inspirado en Road Fighter (Konami, 1984).',
    '  Carretera que serpentea horizontalmente. Esquiva coches enemigos',
    '  que caen desde arriba. Casas y arboles a los lados marcan velocidad.',
    '  Time-attack 60 segundos.',
    '',
    ('CONTROLES', 'cyanB', 'bold'),
    '  W   toggle gas',
    '  S   pulso de freno',
    '  A   toggle giro izquierda',
    '  D   toggle giro derecha',
    '  Q   salir',
    '',
    ('MECANICA', 'cyanB', 'bold'),
    '  Como mucho 2 enemigos simultaneos para no saturar el modem.',
    '  Choque con enemigo: speed cae a 30 km/h. -80 puntos.',
    '  Adelantar enemigo (que salga por abajo): +50 puntos.',
    '  Fuera de pista: speed cae a 90 km/h.',
    '',
    ('OBJETIVO', 'cyanB', 'bold'),
    '  Score = distancia + adelantamientos*50 - choques*80.',
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - ROAD FIGHTER BBS".ljust(70), "cyanB", "bold"))
    print(c("=" * 70, "cyanB"))
    print()
    for _ln in MANUAL_LINEAS:
        if isinstance(_ln, tuple):
            print(c(*_ln))
        else:
            print(_ln)
    print()
    print(c("-" * 70, "dim"))
    try:
        input(c("  Pulsa Enter para volver al menu...", "amarB"))
    except EOFError:
        pass


def splash():
    cls()
    sys.stdout.write(show_cursor(True))
    ancho = 60
    print()
    print(c("╔" + "═" * ancho + "╗", "magentaB"))
    print(_caja_linea("", ancho, "blanco"))
    for ln in LOGO_ROAD:
        print(_caja_linea(ln, ancho, "rojoB"))
    print(_caja_linea("", ancho, "blanco"))
    for ln in LOGO_FIGHT:
        print(_caja_linea(ln, ancho, "amarB"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Racer cenital con carretera que serpentea", ancho, "cyanB"))
    print(_caja_linea("60s. Esquiva, adelanta, llega lejos.", ancho, "blanco"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("W gas    S freno    A/D girar    Q salir", ancho, "amarB"))
    print(_caja_linea("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "magentaB"))
    msg = "[Enter] arrancar     [M] manual"
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        raw = input("")
    except EOFError:
        return
    if raw.strip().lower() == "m":
        mostrar_manual()


def pantalla_final(dist, overtakes, crashes, score, top_entered, scores, nombre_guardado=None):
    sys.stdout.write(show_cursor(True))
    cls()
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    lado = c("║", "magentaB")
    print(margen + c("╔" + linea + "╗", "magentaB"))
    print(margen + lado + c(" CARRERA TERMINADA ".center(ancho), "amarB", "bold") + lado)
    print(margen + c("╠" + linea + "╣", "magentaB"))
    print(margen + lado + f"  Distancia       : {c(str(int(dist)).rjust(15) + ' m', 'cyanB', 'bold')}".ljust(ancho + 15) + lado)
    print(margen + lado + f"  Adelantamientos : {c(str(overtakes).rjust(15) + '  ', 'verdeB', 'bold')}".ljust(ancho + 15) + lado)
    print(margen + lado + f"  Choques         : {c(str(crashes).rjust(15) + '  ', 'rojoB', 'bold')}".ljust(ancho + 15) + lado)
    print(margen + lado + f"  PUNTUACION      : {c(str(score).rjust(15) + '  ', 'amarB', 'bold')}".ljust(ancho + 15) + lado)
    if top_entered:
        print(margen + lado + c('  ¡NUEVO RECORD!'.center(ancho), 'amarB', 'bold') + lado)
    print(margen + c("╠" + linea + "╣", "magentaB"))
    print(margen + lado + c(" TOP 10 ".center(ancho), "cyanB", "bold") + lado)
    for i in range(MAX_TOP):
        if i < len(scores):
            n, p, d = scores[i]
            destacado = (nombre_guardado and n == nombre_guardado and p == score)
            estilo = ("amarB", "bold") if destacado else ("blanco",)
            ln_txt = f"  {i + 1:>2}. {n}   {p:>6} pts   {d}"
            print(margen + lado + c(ln_txt.ljust(ancho), *estilo) + lado)
        else:
            print(margen + lado + " " * ancho + lado)
    print(margen + c("╚" + linea + "╝", "magentaB"))
    print()


# ---------- juego ----------

def spawn_enemigo(speed_actual, enemies, world_offset):
    """Crea coche enemigo en lo alto, con lane relativa al centro de la carretera."""
    half_w = ROAD_W // 2 - 2
    # evitar superposicion con enemigos lejanos recien spawneados
    lane = random.uniform(-half_w + 1, half_w - 1)
    intentos = 5
    while intentos > 0:
        ok = True
        for e in enemies:
            if (e["world_y"] - world_offset) > PLAYER_Y - 4 and abs(e["lane"] - lane) < 4.0:
                ok = False
                break
        if ok:
            break
        lane = random.uniform(-half_w + 1, half_w - 1)
        intentos -= 1
    espeed = random.uniform(speed_actual * ENEMY_SPEED_MIN_FACTOR,
                            max(speed_actual * ENEMY_SPEED_MIN_FACTOR + 5,
                                speed_actual * ENEMY_SPEED_MAX_FACTOR))
    color = random.choice(["amarB", "cyanB", "magentaB", "verdeB", "blancoB"])
    # spawn por encima del top de la pantalla
    return {"lane": lane, "world_y": world_offset + PLAYER_Y + 3,
            "speed": espeed, "color": color, "overtaken": False}


def spawn_scenery():
    side = random.choice(["left", "right"])
    if side == "left":
        sx = random.randint(1, ROAD_LEFT - 5)
    else:
        sx = random.randint(ROAD_RIGHT + 3, COLS - SPRITE_W - 1)
    sprite, color = random.choice(SCENERY_KINDS)
    return {"x": sx, "y": -3.0, "sprite": sprite, "color": color}


def jugar():
    cls()
    sys.stdout.write(show_cursor(False))

    player_x = float(ROAD_CENTER)
    speed = SPEED_INI
    throttle = 1
    steer_dir = 0
    brake_pulse = 0.0
    dist_total = 0.0
    overtakes = 0
    crashes = 0
    hit_flash = 0.0
    t_left = TIEMPO_TOTAL
    world_offset = 0.0
    enemies = []
    scenery = []
    next_enemy = 0.5
    next_scenery = 0.1

    t_last = time.time()

    while True:
        now = time.time()
        dt = now - t_last
        if dt > 0.1:
            dt = 0.1
        t_last = now

        quit_now = False
        while True:
            tecla = leer_tecla_noblock()
            if tecla is None:
                break
            if tecla in ("q", "Q", "\x03"):
                quit_now = True
            elif tecla in ("w", "W", "\x1b[A"):
                throttle = 1 if throttle != 1 else 0
            elif tecla in ("s", "S", "\x1b[B"):
                brake_pulse = 1.0
            elif tecla in ("a", "A", "\x1b[D"):
                steer_dir = -1 if steer_dir != -1 else 0
            elif tecla in ("d", "D", "\x1b[C"):
                steer_dir = 1 if steer_dir != 1 else 0

        if quit_now:
            score = int(dist_total) + overtakes * 50 - crashes * 80
            return dist_total, overtakes, crashes, max(0, score)

        # velocidad
        if throttle == 1:
            speed += SPEED_ACEL * dt
        else:
            speed -= SPEED_ROZA * dt
        if brake_pulse > 0.0:
            speed -= SPEED_FREN * dt * brake_pulse
            brake_pulse = max(0.0, brake_pulse - dt * 2.5)

        # offroad check: la carretera en la fila del jugador esta curvada
        offset_curva_yo = curva_horizontal(world_offset)
        left_yo = ROAD_LEFT + offset_curva_yo
        right_yo = ROAD_RIGHT + offset_curva_yo
        off_road = (player_x < left_yo + 1 or player_x > right_yo - 1)
        if off_road:
            speed -= SPEED_OFFROAD_DRAG * dt
            if speed > SPEED_OFFROAD_MAX:
                speed = SPEED_OFFROAD_MAX
        speed = max(0.0, min(SPEED_MAX, speed))

        # steering
        player_x += steer_dir * STEER_VEL * dt
        # clamp solo a los limites visibles del escenario, no a la carretera
        player_x = max(2.0, min(float(COLS - 3), player_x))

        # avance del mundo
        world_offset += speed * dt * WORLD_SCALE
        dist_total += speed * dt * DIST_SCALE

        # spawns (cap a MAX_ENEMIES visibles para ahorrar bandwidth)
        next_enemy -= dt
        if next_enemy <= 0:
            if len(enemies) < MAX_ENEMIES:
                enemies.append(spawn_enemigo(speed, enemies, world_offset))
            factor = max(0.4, 1.0 - speed / SPEED_MAX * 0.5)
            next_enemy = random.uniform(ENEMY_SPAWN_MIN * factor, ENEMY_SPAWN_MAX * factor)

        next_scenery -= dt
        if next_scenery <= 0:
            scenery.append(spawn_scenery())
            factor = max(0.3, 1.0 - speed / SPEED_MAX * 0.4)
            next_scenery = random.uniform(SCENERY_SPAWN_MIN * factor, SCENERY_SPAWN_MAX * factor)

        # avanzar entidades
        for e in enemies:
            e["world_y"] += e["speed"] * dt * WORLD_SCALE
        for s in scenery:
            s["y"] += speed * dt * WORLD_SCALE

        # culling + conteo de adelantamientos
        nuevos_enemies = []
        for e in enemies:
            screen_y = PLAYER_Y - (e["world_y"] - world_offset)
            if screen_y > ROWS - 2:
                if not e["overtaken"]:
                    overtakes += 1
                continue
            nuevos_enemies.append(e)
        enemies = nuevos_enemies
        scenery = [s for s in scenery if s["y"] < ROWS - 2]

        # colisiones (en periodo de gracia tras choque no se chequea)
        if hit_flash <= 0:
            px = int(player_x) - PLAYER_CX_OFFSET
            py = PLAYER_Y
            for e in enemies:
                ey = int(PLAYER_Y - (e["world_y"] - world_offset))
                ex = int(ROAD_CENTER + curva_horizontal(world_offset + (PLAYER_Y - ey)) + e["lane"]) - 1
                if (abs(ex - px) < SPRITE_W) and (abs(ey - py) < SPRITE_H):
                    crashes += 1
                    speed = SPEED_TRAS_CHOQUE
                    hit_flash = 0.6
                    e["world_y"] = -1e9
                    break
            enemies = [e for e in enemies if e["world_y"] > -1e8]

        if hit_flash > 0:
            hit_flash = max(0.0, hit_flash - dt)

        # tiempo
        t_left -= dt
        if t_left <= 0:
            t_left = 0
            score = int(dist_total) + overtakes * 50 - crashes * 80
            return dist_total, overtakes, crashes, max(0, score)

        # render
        frame = frame_nuevo()
        render(frame, world_offset, player_x, speed, enemies, scenery,
               dist_total, t_left, overtakes, crashes, throttle, brake_pulse > 0.1,
               steer_dir, hit_flash, off_road)
        flush_frame(frame)

        rest = FRAME_DT - (time.time() - now)
        if rest > 0:
            time.sleep(rest)


def main():
    if not TERMIOS_OK:
        print("Road Fighter necesita un TTY con termios.")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak.")
        return
    try:
        restaurar_terminal(old)
        splash()
        while True:
            old2 = entrar_cbreak()
            dist, overtakes, crashes, score = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            scores = [(e.handle, e.score, e.date) for e in bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)]
            top = bbs_scores.entra_en_top_local(score, max_top=MAX_TOP, ascending=ASCENDING)
            nombre_guardado = None
            if top:
                ancho = 50
                margen = " " * ((COLS - (ancho + 2)) // 2)
                print()
                print(margen + c("  ¡Has entrado en el TOP 10!", "amarB", "bold"))
                nombre = ""
                while not nombre:
                    try:
                        raw = input(margen + "  Iniciales (3 chars): ").strip().upper()
                    except EOFError:
                        raw = "AAA"
                    nombre = "".join(ch for ch in raw if ch.isalnum())[:3].ljust(3, "A")
                bbs_scores.save_local(nombre, score, max_top=MAX_TOP, ascending=ASCENDING)
                bbs_scores.submit(nombre, score)
                bbs_scores.invalidate_cache()
                scores = [(e.handle, e.score, e.date) for e in bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)]
                nombre_guardado = nombre
            pantalla_final(dist, overtakes, crashes, score, top, scores, nombre_guardado)
            # Toggle [L]ocal / [G]lobal del top mundial
            while True:
                try:
                    _r = input(c("\n  [L] local   [G] global   [Enter] continuar: ", "dim")).strip().upper()
                except EOFError:
                    break
                if _r not in ("L", "G"):
                    break
                _modo = "local" if _r == "L" else "global"
                cls()  # toggle redibuja limpio
                print()
                _scores_e, _titulo, _ = bbs_scores.get_top_for_mode(_modo, limit=MAX_TOP, ascending=ASCENDING)
                print()
                print(c("  " + _titulo.strip(), "cyanB", "bold"))
                print(c("  " + "-" * 50, "dim"))
                for _i, _e in enumerate(_scores_e, 1):
                    _et = _e.display_handle if _modo == "global" else _e.handle
                    print(f"  {_i:>2}. {_et:14}  {str(_e.score).rjust(8)}  {_e.date}")
                print()

            try:
                raw = input("\n  Otra carrera? [S/N]: ").strip().upper()
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
