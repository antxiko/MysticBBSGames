#!/usr/bin/env python3
"""Catacumba BBS - dungeon pseudo-3D en ASCII con raycasting, ratas y disparos."""
import math
import os
import random
import sys
import time
from datetime import date

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

# Area 3D
VIEW_W = 78
VIEW_H = 18
VIEW_X0 = 1
VIEW_Y0 = 1

# Mini-mapa: bloque abajo a la derecha
MAP_W = 12
MAP_H = 12
MAPA = []  # se rellena en cada partida
PLAYER_START_X = 1.5
PLAYER_START_Y = 1.5

FOV = math.pi / 3.0  # 60 grados
MAX_DIST = 16.0

VEL_MOV = 0.15
VEL_ROT = 0.10

# --- enemigos ---
NUM_ENEMIGOS = 6
PLAYER_HP_INI = 100
DANO_RATA = 8
RANGO_ATAQUE = 0.9
RANGO_DISPARO = 12.0
ANCHO_HITBOX = 0.35
COOLDOWN_DISPARO_TICKS = 8

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


# ---------- terminal raw ----------

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


# ---------- raycasting ----------

def es_muro(mx, my):
    if mx < 0 or mx >= MAP_W or my < 0 or my >= MAP_H:
        return True
    return MAPA[my][mx] == "#"


def es_salida(mx, my):
    if mx < 0 or mx >= MAP_W or my < 0 or my >= MAP_H:
        return False
    return MAPA[my][mx] == "E"


def lanzar_rayo(px, py, angulo, visto=None):
    """DDA raycasting. Devuelve (distancia, tipo). Si pasas un set 'visto', anota cada celda cruzada."""
    cos_a = math.cos(angulo)
    sin_a = math.sin(angulo)
    paso = 0.05
    d = 0.0
    ultimo = (-1, -1)
    while d < MAX_DIST:
        d += paso
        tx = px + cos_a * d
        ty = py + sin_a * d
        mx = int(tx)
        my = int(ty)
        if (mx, my) != ultimo:
            ultimo = (mx, my)
            if visto is not None and 0 <= mx < MAP_W and 0 <= my < MAP_H:
                visto.add((mx, my))
        if 0 <= mx < MAP_W and 0 <= my < MAP_H:
            ch = MAPA[my][mx]
            if ch == "#":
                return d, 0
            if ch == "E":
                return d, 1
        else:
            return d, 0
    return MAX_DIST, 0


def shade_char(dist, tipo):
    if tipo == 1:
        if dist < 3:
            return "█", "verdeB"
        if dist < 6:
            return "▓", "verdeB"
        if dist < 10:
            return "▒", "verde"
        return "░", "verde"
    if dist < 2:
        return "█", "blancoB"
    if dist < 4:
        return "▓", "blanco"
    if dist < 7:
        return "▒", "blanco"
    if dist < 11:
        return "░", "blanco"
    return "░", "dim"


# ---------- generador procedural ----------

def generar_mapa():
    """Recursive backtracker sobre una cuadricula de celdas en posiciones impares.
    Rellena MAPA global, fija PLAYER_START_*, devuelve la lista de casillas de suelo."""
    global MAPA, PLAYER_START_X, PLAYER_START_Y
    W, H = MAP_W, MAP_H
    m = [['#'] * W for _ in range(H)]
    GW = (W - 1) // 2
    GH = (H - 1) // 2

    def to_xy(cx, cy):
        return cx * 2 + 1, cy * 2 + 1

    stack = [(0, 0)]
    visitado = {(0, 0)}
    sx, sy = to_xy(0, 0)
    m[sy][sx] = '.'
    while stack:
        cx, cy = stack[-1]
        vecinos = []
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < GW and 0 <= ny < GH and (nx, ny) not in visitado:
                vecinos.append((nx, ny))
        if not vecinos:
            stack.pop()
            continue
        nx, ny = random.choice(vecinos)
        visitado.add((nx, ny))
        x1, y1 = to_xy(cx, cy)
        x2, y2 = to_xy(nx, ny)
        m[y2][x2] = '.'
        m[(y1 + y2) // 2][(x1 + x2) // 2] = '.'
        stack.append((nx, ny))

    # tirar un par de muros extra para que haya bucles y no sea un laberinto perfecto
    for _ in range(GW * GH // 3):
        wx = random.randint(1, W - 2)
        wy = random.randint(1, H - 2)
        if m[wy][wx] == '#':
            ad = sum(1 for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
                     if m[wy + dy][wx + dx] == '.')
            if ad >= 2:
                m[wy][wx] = '.'

    # BFS desde el inicio para encontrar la celda mas lejana -> salida
    sx0, sy0 = to_xy(0, 0)
    dist = {(sx0, sy0): 0}
    q = [(sx0, sy0)]
    while q:
        x, y = q.pop(0)
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and m[ny][nx] != '#' and (nx, ny) not in dist:
                dist[(nx, ny)] = dist[(x, y)] + 1
                q.append((nx, ny))
    fx, fy = max(dist, key=lambda p: dist[p])
    m[fy][fx] = 'E'

    MAPA = [''.join(row) for row in m]
    PLAYER_START_X = sx0 + 0.5
    PLAYER_START_Y = sy0 + 0.5
    return [(x, y) for (x, y) in dist.keys() if MAPA[y][x] == '.']


# ---------- enemigos ----------

def crear_enemigos(floor_cells, px, py):
    candidatos = [(x, y) for (x, y) in floor_cells
                  if abs(x - px) + abs(y - py) >= 4]
    random.shuffle(candidatos)
    es = []
    for (x, y) in candidatos[:NUM_ENEMIGOS]:
        es.append({
            "x": x + 0.5,
            "y": y + 0.5,
            "viva": True,
            "cd_mov": random.randint(5, 30),
            "cd_atq": 0,
            "hit_flash": 0,
        })
    return es


def mover_enemigos(enemigos, player):
    for e in enemigos:
        if not e["viva"]:
            continue
        if e["hit_flash"] > 0:
            e["hit_flash"] -= 1
        e["cd_mov"] -= 1
        if e["cd_mov"] > 0:
            continue
        e["cd_mov"] = random.randint(20, 50)
        dx = player["x"] - e["x"]
        dy = player["y"] - e["y"]
        dist2 = dx * dx + dy * dy
        # cuanto mas cerca, mas perseguidor
        if dist2 < 25 and random.random() < 0.7:
            if abs(dx) > abs(dy):
                step = (0.45 if dx > 0 else -0.45, 0.0)
            else:
                step = (0.0, 0.45 if dy > 0 else -0.45)
        else:
            step = random.choice([(0.4, 0.0), (-0.4, 0.0), (0.0, 0.4), (0.0, -0.4)])
        nx = e["x"] + step[0]
        ny = e["y"] + step[1]
        # no se solapan con el jugador ni con otra rata
        if es_muro(int(nx), int(ny)):
            continue
        if abs(nx - player["x"]) < 0.5 and abs(ny - player["y"]) < 0.5:
            continue
        chocho = False
        for o in enemigos:
            if o is e or not o["viva"]:
                continue
            if abs(o["x"] - nx) < 0.6 and abs(o["y"] - ny) < 0.6:
                chocho = True
                break
        if chocho:
            continue
        e["x"] = nx
        e["y"] = ny


def atacar_jugador(enemigos, player):
    """Devuelve True si alguna rata muerde al jugador este tick."""
    mordido = False
    for e in enemigos:
        if not e["viva"]:
            continue
        if e["cd_atq"] > 0:
            e["cd_atq"] -= 1
            continue
        dx = e["x"] - player["x"]
        dy = e["y"] - player["y"]
        if dx * dx + dy * dy < RANGO_ATAQUE * RANGO_ATAQUE:
            player["hp"] -= DANO_RATA
            e["cd_atq"] = 40
            mordido = True
    return mordido


def disparar(player, enemigos):
    """Dispara en la direccion del jugador. Devuelve la rata alcanzada o None."""
    px, py = player["x"], player["y"]
    pa = player["angulo"]
    cos_a = math.cos(pa)
    sin_a = math.sin(pa)
    dist_muro, _ = lanzar_rayo(px, py, pa)
    objetivo = None
    mejor = min(dist_muro, RANGO_DISPARO)
    for e in enemigos:
        if not e["viva"]:
            continue
        dx = e["x"] - px
        dy = e["y"] - py
        forward = dx * cos_a + dy * sin_a
        side = -dx * sin_a + dy * cos_a
        if forward <= 0.1:
            continue
        if abs(side) > ANCHO_HITBOX:
            continue
        if forward < mejor:
            mejor = forward
            objetivo = e
    if objetivo:
        objetivo["viva"] = False
        return objetivo
    return None


# ---------- render ----------

def render(player, enemigos, msg=None, flash_disparo=False, flash_dano=False):
    frame = frame_nuevo()
    px, py = player["x"], player["y"]
    pa = player["angulo"]
    visto = player["visto"]
    visto.add((int(px), int(py)))

    # cielo y suelo de fondo
    medio = VIEW_H // 2
    for col in range(VIEW_W):
        for row in range(VIEW_H):
            sy = VIEW_Y0 + row
            sx = VIEW_X0 + col
            if row < medio:
                set_cell(frame, sy, sx, " ")
            else:
                if row > medio + 4:
                    set_cell(frame, sy, sx, "·", "amar")
                else:
                    set_cell(frame, sy, sx, " ")

    # raycasting de paredes + zbuffer
    zbuf = [MAX_DIST] * VIEW_W
    for col in range(VIEW_W):
        ang = pa - FOV / 2.0 + (col / VIEW_W) * FOV
        dist, tipo = lanzar_rayo(px, py, ang, visto)
        perp = max(0.001, dist * math.cos(ang - pa))
        zbuf[col] = perp
        h = int((VIEW_H * 1.3) / perp)
        h = min(h, VIEW_H)
        top = (VIEW_H - h) // 2
        ch, col_estilo = shade_char(perp, tipo)
        for row in range(top, top + h):
            sy = VIEW_Y0 + row
            sx = VIEW_X0 + col
            set_cell(frame, sy, sx, ch, col_estilo)

    # sprites de enemigos (back-to-front)
    cos_a = math.cos(pa)
    sin_a = math.sin(pa)
    sprites = []
    for e in enemigos:
        if not e["viva"]:
            continue
        dx = e["x"] - px
        dy = e["y"] - py
        forward = dx * cos_a + dy * sin_a
        side = -dx * sin_a + dy * cos_a
        if forward <= 0.3:
            continue
        ang_off = math.atan2(side, forward)
        if abs(ang_off) > FOV / 2 + 0.2:
            continue
        sprites.append((forward, ang_off, e))
    sprites.sort(key=lambda s: -s[0])

    for forward, ang_off, e in sprites:
        screen_col = int((ang_off / FOV + 0.5) * VIEW_W)
        h = int((VIEW_H * 1.0) / forward)
        h = max(2, min(h, VIEW_H - 2))
        w = max(2, h // 2 + 1)
        # rata pegada al suelo
        top = (VIEW_H - h) // 2 + h // 3
        h_eff = h - h // 3
        left = screen_col - w // 2
        if e["hit_flash"] > 0:
            color = "blancoB"
        elif forward < 3:
            color = "rojoB"
        elif forward < 6:
            color = "rojo"
        else:
            color = "magenta"
        for rx in range(w):
            col = left + rx
            if col < 0 or col >= VIEW_W:
                continue
            if forward >= zbuf[col]:
                continue
            for ry in range(h_eff):
                sy = VIEW_Y0 + top + ry
                sx = VIEW_X0 + col
                # ojos amarillos cerca del tope
                if ry == max(1, h_eff // 5) and rx in (max(1, w // 4), w - max(2, w // 4) - 1):
                    set_cell(frame, sy, sx, "·", "amarB", "bold")
                # boquita centrada
                elif ry == max(2, h_eff // 3) and rx == w // 2:
                    set_cell(frame, sy, sx, "ν", color)
                else:
                    set_cell(frame, sy, sx, "▓", color)

    # mira centrada
    cx_mira = VIEW_X0 + VIEW_W // 2
    cy_mira = VIEW_Y0 + VIEW_H // 2
    set_cell(frame, cy_mira, cx_mira - 1, "─", "amarB")
    set_cell(frame, cy_mira, cx_mira + 1, "─", "amarB")
    set_cell(frame, cy_mira - 1, cx_mira, "│", "amarB")
    set_cell(frame, cy_mira + 1, cx_mira, "│", "amarB")

    # fogonazo del disparo
    if flash_disparo:
        for row in range(VIEW_H):
            for col in range(VIEW_W):
                sy = VIEW_Y0 + row
                sx = VIEW_X0 + col
                if random.random() < 0.06:
                    set_cell(frame, sy, sx, "*", "amarB", "bold")

    # flash de dano: tinte rojo en los bordes del area 3D
    if flash_dano:
        for col in range(VIEW_W):
            set_cell(frame, VIEW_Y0, VIEW_X0 + col, "▓", "rojoB")
            set_cell(frame, VIEW_Y0 + VIEW_H - 1, VIEW_X0 + col, "▓", "rojoB")
        for row in range(VIEW_H):
            set_cell(frame, VIEW_Y0 + row, VIEW_X0, "▓", "rojoB")
            set_cell(frame, VIEW_Y0 + row, VIEW_X0 + VIEW_W - 1, "▓", "rojoB")

    # mini-mapa esquina superior derecha (solo celdas vistas)
    mm_x = VIEW_X0 + VIEW_W - MAP_W - 1
    mm_y = VIEW_Y0
    for y in range(MAP_H):
        for x in range(MAP_W):
            cell_y = mm_y + y
            cell_x = mm_x + x
            es_jugador = (int(px) == x and int(py) == y)
            if (x, y) not in visto and not es_jugador:
                continue
            ch_mapa = MAPA[y][x]
            if es_jugador:
                set_cell(frame, cell_y, cell_x, "@", "amarB", "bold")
            elif ch_mapa == "#":
                set_cell(frame, cell_y, cell_x, "█", "blanco")
            elif ch_mapa == "E":
                set_cell(frame, cell_y, cell_x, "E", "verdeB", "bold")
            else:
                # rata visible en el minimapa solo si su celda esta vista
                rata_aqui = False
                for e in enemigos:
                    if e["viva"] and int(e["x"]) == x and int(e["y"]) == y:
                        rata_aqui = True
                        break
                if rata_aqui:
                    set_cell(frame, cell_y, cell_x, "r", "rojoB", "bold")
                else:
                    set_cell(frame, cell_y, cell_x, "·", "dim")

    # HUD inferior
    set_text(frame, 19, 0, "─" * (COLS - 1), "dim")
    hp = max(0, player["hp"])
    hp_color = "verdeB" if hp > 60 else ("amarB" if hp > 30 else "rojoB")
    set_text(frame, 20, 1, "HP:", "blanco")
    set_text(frame, 20, 5, f"{hp:>3}/100", hp_color, "bold")
    vivas = sum(1 for e in enemigos if e["viva"])
    muertas = len(enemigos) - vivas
    set_text(frame, 20, 17, "Bajas:", "blanco")
    set_text(frame, 20, 24, f"{muertas}/{len(enemigos)}", "magentaB", "bold")
    set_text(frame, 20, 33, "Pasos:", "blanco")
    set_text(frame, 20, 40, f"{player['pasos']:>4}", "cyanB", "bold")
    set_text(frame, 20, 48, f"Pos:({px:.1f},{py:.1f})", "dim")

    if msg:
        set_text(frame, 21, max(1, COLS - len(msg) - 1), msg, "amarB", "bold")

    set_text(frame, 22, 0, "─" * (COLS - 1), "dim")
    ctrl = " W/S avanzar  A/D girar  SPACE disparar  Q salir "
    set_text(frame, 23, (COLS - len(ctrl)) // 2, ctrl, "dim")

    flush_frame(frame)


# ---------- splash y final ----------

LOGO_CATA = [
    " ██████╗ █████╗ ████████╗ █████╗ ",
    "██╔════╝██╔══██╗╚══██╔══╝██╔══██╗",
    "██║     ███████║   ██║   ███████║",
    "██║     ██╔══██║   ██║   ██╔══██║",
    "╚██████╗██║  ██║   ██║   ██║  ██║",
    " ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝",
]

LOGO_CUMBA = [
    " ██████╗██╗   ██╗███╗   ███╗██████╗  █████╗ ",
    "██╔════╝██║   ██║████╗ ████║██╔══██╗██╔══██╗",
    "██║     ██║   ██║██╔████╔██║██████╔╝███████║",
    "██║     ██║   ██║██║╚██╔╝██║██╔══██╗██╔══██║",
    "╚██████╗╚██████╔╝██║ ╚═╝ ██║██████╔╝██║  ██║",
    " ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝",
]


def _caja_linea_splash(texto, ancho, color_txt, color_caja="magentaB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


MANUAL_LINEAS = [
    ('PREMISA', 'cyanB', 'bold'),
    '  Dungeon pseudo-3D con raycasting puro en ASCII.',
    '  Mazmorra 12x12 procedural infestada de ratas asesinas.',
    '  Encuentra la salida E sin morir.',
    '',
    ('CONTROLES (char-mode, real-time)', 'cyanB', 'bold'),
    '  W / flecha arriba       avanzar',
    '  S / flecha abajo        retroceder',
    '  A / flecha izquierda    girar a la izquierda',
    '  D / flecha derecha      girar a la derecha',
    '  Espacio                 disparar',
    '  Q                       salir',
    '',
    ('MECANICA', 'cyanB', 'bold'),
    '  Vista 3D 78x18 + minimapa con niebla de guerra.',
    '  Solo ves en el mapa lo que tus rayos han iluminado.',
    '  HP 100. Las ratas muerden -8 HP si estan adyacentes.',
    '  El disparo es un raycast con hitbox 0.35 y respeta muros.',
    '',
    ('OBJETIVO', 'cyanB', 'bold'),
    '  Llegar a la casilla E con HP > 0. Salir vivo, no hay top.',
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - CATACUMBA BBS".ljust(70), "cyanB", "bold"))
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
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_CATA:
        print(_caja_linea_splash(ln, ancho, "magentaB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_CUMBA:
        print(_caja_linea_splash(ln, ancho, "magentaB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Mazmorra pseudo-3D infestada de ratas asesinas", ancho, "cyanB"))
    print(_caja_linea_splash("Encuentra la salida E y procura no morir antes", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("WASD para moverte    SPACE para disparar    Q para huir", ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "magentaB"))
    msg = "[Enter] entrar a la catacumba     [M] manual"
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        raw = input("")
    except EOFError:
        return
    if raw.strip().lower() == "m":
        mostrar_manual()


def pantalla_victoria(pasos, tiempo, kills, total):
    sys.stdout.write(show_cursor(True))
    cls()
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    lado = c("║", "verdeB")
    print(margen + c("╔" + linea + "╗", "verdeB"))
    print(margen + lado + c(" ENCONTRASTE LA SALIDA ".center(ancho), "verdeB", "bold") + lado)
    print(margen + c("╠" + linea + "╣", "verdeB"))
    print(margen + lado + f"  Pasos dados   : {c(str(pasos).rjust(20), 'amarB', 'bold')}".ljust(ancho + 12) + lado)
    print(margen + lado + f"  Tiempo (seg)  : {c(str(int(tiempo)).rjust(20), 'cyanB', 'bold')}".ljust(ancho + 12) + lado)
    print(margen + lado + f"  Ratas muertas : {c(f'{kills}/{total}'.rjust(20), 'magentaB', 'bold')}".ljust(ancho + 12) + lado)
    print(margen + c("╚" + linea + "╝", "verdeB"))
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


def pantalla_derrota(pasos, tiempo, kills, total):
    sys.stdout.write(show_cursor(True))
    cls()
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    lado = c("║", "rojoB")
    print(margen + c("╔" + linea + "╗", "rojoB"))
    print(margen + lado + c(" TE COMIERON LAS RATAS ".center(ancho), "rojoB", "bold") + lado)
    print(margen + c("╠" + linea + "╣", "rojoB"))
    print(margen + lado + f"  Pasos dados   : {c(str(pasos).rjust(20), 'amarB', 'bold')}".ljust(ancho + 12) + lado)
    print(margen + lado + f"  Tiempo (seg)  : {c(str(int(tiempo)).rjust(20), 'cyanB', 'bold')}".ljust(ancho + 12) + lado)
    print(margen + lado + f"  Ratas muertas : {c(f'{kills}/{total}'.rjust(20), 'magentaB', 'bold')}".ljust(ancho + 12) + lado)
    print(margen + c("╚" + linea + "╝", "rojoB"))
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- juego ----------

def intentar_mover(player, nx, ny, enemigos):
    """Mueve al jugador si la posicion destino no es muro ni hay rata."""
    def libre(cx, cy):
        if es_muro(int(cx), int(cy)):
            return False
        for e in enemigos:
            if not e["viva"]:
                continue
            if abs(e["x"] - cx) < 0.5 and abs(e["y"] - cy) < 0.5:
                return False
        return True

    if libre(nx, player["y"]):
        player["x"] = nx
    if libre(player["x"], ny):
        player["y"] = ny


def jugar():
    cls()
    sys.stdout.write(show_cursor(False))
    floor_cells = generar_mapa()
    player = {
        "x": PLAYER_START_X,
        "y": PLAYER_START_Y,
        "angulo": 0.0,
        "hp": PLAYER_HP_INI,
        "pasos": 0,
        "visto": set(),
        "cd_disparo": 0,
    }
    enemigos = crear_enemigos(floor_cells, int(PLAYER_START_X), int(PLAYER_START_Y))
    total_enemigos = len(enemigos)
    msg = None
    msg_expira = 0.0
    flash_disparo_ticks = 0
    flash_dano_ticks = 0
    t_ini = time.time()
    tick = 0

    while True:
        tick += 1
        ahora = time.time()

        movido = False
        while True:
            tecla = leer_tecla_noblock()
            if tecla is None:
                break
            if tecla in ("q", "Q", "\x03"):
                return "huir", player["pasos"], time.time() - t_ini, sum(1 for e in enemigos if not e["viva"]), total_enemigos
            elif tecla in ("w", "W", "\x1b[A"):
                nx = player["x"] + math.cos(player["angulo"]) * VEL_MOV
                ny = player["y"] + math.sin(player["angulo"]) * VEL_MOV
                intentar_mover(player, nx, ny, enemigos)
                movido = True
            elif tecla in ("s", "S", "\x1b[B"):
                nx = player["x"] - math.cos(player["angulo"]) * VEL_MOV
                ny = player["y"] - math.sin(player["angulo"]) * VEL_MOV
                intentar_mover(player, nx, ny, enemigos)
                movido = True
            elif tecla in ("a", "A", "\x1b[D"):
                player["angulo"] -= VEL_ROT
                movido = True
            elif tecla in ("d", "D", "\x1b[C"):
                player["angulo"] += VEL_ROT
                movido = True
            elif tecla == " ":
                if player["cd_disparo"] <= 0:
                    player["cd_disparo"] = COOLDOWN_DISPARO_TICKS
                    flash_disparo_ticks = 2
                    objetivo = disparar(player, enemigos)
                    if objetivo:
                        msg = "¡RATA REVENTADA!"
                        msg_expira = ahora + 1.0
                    else:
                        msg = "Fallaste."
                        msg_expira = ahora + 0.6

        if movido:
            player["pasos"] += 1

        if player["cd_disparo"] > 0:
            player["cd_disparo"] -= 1
        if flash_disparo_ticks > 0:
            flash_disparo_ticks -= 1
        if flash_dano_ticks > 0:
            flash_dano_ticks -= 1

        # IA cada tick
        mover_enemigos(enemigos, player)
        if atacar_jugador(enemigos, player):
            flash_dano_ticks = 3
            msg = "¡TE MUERDE!"
            msg_expira = ahora + 0.8

        if player["hp"] <= 0:
            return "muerto", player["pasos"], time.time() - t_ini, sum(1 for e in enemigos if not e["viva"]), total_enemigos

        if es_salida(int(player["x"]), int(player["y"])):
            return "ganado", player["pasos"], time.time() - t_ini, sum(1 for e in enemigos if not e["viva"]), total_enemigos

        msg_render = msg if ahora < msg_expira else None
        render(player, enemigos, msg_render, flash_disparo_ticks > 0, flash_dano_ticks > 0)
        time.sleep(0.03)


def main():
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. Catacumba necesita un TTY.")
        return
    try:
        restaurar_terminal(old)
        splash()
        while True:
            old2 = entrar_cbreak()
            resultado, pasos, tiempo, kills, total = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            if resultado == "ganado":
                pantalla_victoria(pasos, tiempo, kills, total)
            elif resultado == "muerto":
                pantalla_derrota(pasos, tiempo, kills, total)
            try:
                raw = input("\n  Otra exploracion? [S/N]: ").strip().upper()
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
