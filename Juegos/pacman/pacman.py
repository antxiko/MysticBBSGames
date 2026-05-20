#!/usr/bin/env python3
"""Pacman BBS - clon cenital del clasico.

Cada personaje (pacman + 4 fantasmas) es un sprite 2x2 = 4 chars. Render
diferencial: solo se reemiten celdas que cambian (pacman + fantasmas
moviendose + puntos comidos + HUD). Maze estatico tras dibujarlo una vez.
"""
import math
import os
import random
import sys
import time
from datetime import date

_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)
sys.path.insert(0, os.path.dirname(_d))
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
MAX_TOP = 10
ASCENDING = False  # mas score = mejor

# Maze logical 28x10. Cada celda logica = 2x2 terminal.
# El maze ocupa: cols 0..55 (28*2), rows 2..21 (10*2)
# Margen: cols 56..79 para HUD lateral. row 0-1 HUD top, row 22-23 footer.
#
# Caracteres:
#  '#' muro
#  '.' punto (10 pts)
#  'o' power pellet (50 pts, asusta fantasmas)
#  ' ' empty (suelo, sin nada)
#  '-' puerta de la casa de fantasmas (atraviesan ellos, no pacman)
#  'P' posicion inicial de pacman
#  'G' posicion inicial de un fantasma

MAZE_RAW = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "#.####.##.########.##.####.#",
    "#.####.##.G G G GP.##.####.#",
    "############################",
]
# 11 filas logicas x 28 cols logicas. La fila 9 tiene G's (fantasmas) y P (pacman).

MAZE_W = 28
MAZE_H = 11

# Offsets de pintura: el maze empieza en terminal col COL0, row ROW0
COL0 = (COLS - MAZE_W * 2) // 2  # centrado: (80-56)/2 = 12
ROW0 = 1  # justo bajo el HUD

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
    return f"{prefijo}{txt}{RESET}" if prefijo else str(txt)


def at(row, col):
    return f"\x1b[{row};{col}H"


# Shadow buffer
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


# ---------- maze + estado ----------

def parsear_maze():
    """Devuelve (grid, pacman_start, ghost_starts).
    grid es lista de listas: grid[y][x] in {'#','.','o',' '}.
    Pacman start y ghost starts en coords logicas (x, y)."""
    grid = []
    pacman_start = None
    ghost_starts = []
    for y, ln in enumerate(MAZE_RAW):
        row = []
        for x, ch in enumerate(ln):
            if ch == 'P':
                pacman_start = (x, y)
                row.append(' ')
            elif ch == 'G':
                ghost_starts.append((x, y))
                row.append(' ')
            else:
                row.append(ch)
        grid.append(row)
    return grid, pacman_start, ghost_starts


# ---------- pintar elementos ----------

def pintar_pared(frame, x_log, y_log):
    """Pinta una pared 2x2 en posicion logica."""
    tx = COL0 + x_log * 2
    ty = ROW0 + y_log * 2
    set_cell(frame, ty, tx, "█", "azulB")
    set_cell(frame, ty, tx + 1, "█", "azulB")
    set_cell(frame, ty + 1, tx, "█", "azulB")
    set_cell(frame, ty + 1, tx + 1, "█", "azulB")


def pintar_punto(frame, x_log, y_log):
    """Pinta un punto pequeño en el centro de la celda 2x2."""
    tx = COL0 + x_log * 2
    ty = ROW0 + y_log * 2
    set_cell(frame, ty, tx, "·", "blanco")


def pintar_pellet(frame, x_log, y_log):
    """Power pellet: cuadrado relleno en la celda 2x2."""
    tx = COL0 + x_log * 2
    ty = ROW0 + y_log * 2
    set_cell(frame, ty, tx, "●", "amarB")


def borrar_celda(frame, x_log, y_log):
    """Limpia los 4 chars de una celda logica."""
    tx = COL0 + x_log * 2
    ty = ROW0 + y_log * 2
    set_cell(frame, ty, tx, " ")
    set_cell(frame, ty, tx + 1, " ")
    set_cell(frame, ty + 1, tx, " ")
    set_cell(frame, ty + 1, tx + 1, " ")


def pintar_pacman(frame, x_log, y_log, direccion, frame_tick):
    """Pacman 2x2 amarillo. Direccion: (dx, dy). frame_tick alterna abierto/cerrado."""
    tx = COL0 + x_log * 2
    ty = ROW0 + y_log * 2
    abierto = (frame_tick // 3) % 2 == 0
    color = "amarB"
    if not abierto:
        # Cerrado: cuadrado lleno
        set_cell(frame, ty, tx, "█", color)
        set_cell(frame, ty, tx + 1, "█", color)
        set_cell(frame, ty + 1, tx, "█", color)
        set_cell(frame, ty + 1, tx + 1, "█", color)
        return
    # Abierto: media-pacman segun direccion
    dx, dy = direccion
    if dx > 0:  # derecha
        set_cell(frame, ty, tx, "█", color)
        set_cell(frame, ty, tx + 1, "▖", color)
        set_cell(frame, ty + 1, tx, "█", color)
        set_cell(frame, ty + 1, tx + 1, "▘", color)
    elif dx < 0:  # izquierda
        set_cell(frame, ty, tx, "▗", color)
        set_cell(frame, ty, tx + 1, "█", color)
        set_cell(frame, ty + 1, tx, "▝", color)
        set_cell(frame, ty + 1, tx + 1, "█", color)
    elif dy > 0:  # abajo
        set_cell(frame, ty, tx, "█", color)
        set_cell(frame, ty, tx + 1, "█", color)
        set_cell(frame, ty + 1, tx, "▘", color)
        set_cell(frame, ty + 1, tx + 1, "▝", color)
    else:  # arriba o quieto
        set_cell(frame, ty, tx, "▖", color)
        set_cell(frame, ty, tx + 1, "▗", color)
        set_cell(frame, ty + 1, tx, "█", color)
        set_cell(frame, ty + 1, tx + 1, "█", color)


GHOST_COLORS = ["rojoB", "magentaB", "cyanB", "verdeB"]
GHOST_NAMES = ["BLIN", "PINK", "INKY", "CLYD"]


def pintar_fantasma(frame, x_log, y_log, color, asustado=False):
    """Fantasma 2x2: redondeado por arriba, ondulado por abajo."""
    tx = COL0 + x_log * 2
    ty = ROW0 + y_log * 2
    col = "azulB" if asustado else color
    # Top: cabeza redondeada (parecido a un casco)
    set_cell(frame, ty, tx, "▟", col)
    set_cell(frame, ty, tx + 1, "▙", col)
    # Bottom: dos patas/ojos
    set_cell(frame, ty + 1, tx, "▀", col)
    set_cell(frame, ty + 1, tx + 1, "▀", col)


# ---------- render inicial del maze ----------

def render_maze_estatico(frame, grid):
    """Pinta paredes, puntos y pellets. Una sola vez por nivel."""
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == '#':
                pintar_pared(frame, x, y)
            elif ch == '.':
                pintar_punto(frame, x, y)
            elif ch == 'o':
                pintar_pellet(frame, x, y)


def render_hud(frame, score, lives, level):
    """HUD en row 0."""
    set_text(frame, 0, 1, "PACMAN BBS", "amarB", "bold")
    set_text(frame, 0, 18, f"SCORE {score:>5}", "blancoB", "bold")
    set_text(frame, 0, 36, "LIVES ", "blanco")
    set_text(frame, 0, 42, "♥ " * lives, "rojoB", "bold")
    set_text(frame, 0, 58, f"NIVEL {level}", "cyanB", "bold")


def render_footer(frame, mensaje=None):
    set_text(frame, 23, 0, "─" * COLS, "dim")
    ctrl = " WASD/flechas mover    Q salir "
    set_text(frame, 23, (COLS - len(ctrl)) // 2, ctrl, "dim")
    if mensaje:
        set_text(frame, 22, (COLS - len(mensaje)) // 2, mensaje, "amarB", "bold")


# ---------- logica del juego ----------

def es_pared(grid, x, y):
    if not (0 <= y < len(grid) and 0 <= x < len(grid[0])):
        return True
    return grid[y][x] == '#'


def vecinos_libres(grid, x, y, exclude_dir=None):
    """Lista de (dx, dy) que no son paredes desde (x, y)."""
    res = []
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        if exclude_dir and (dx, dy) == exclude_dir:
            continue
        if not es_pared(grid, x + dx, y + dy):
            res.append((dx, dy))
    return res


def distancia(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def mover_fantasma(grid, ghost, pacman_pos, asustado):
    """Mueve un fantasma. Mantiene direccion si puede, en intersecciones decide.
    Comportamiento basico: chase con algo de aleatoriedad. Asustado = huye."""
    x, y, dx, dy = ghost["x"], ghost["y"], ghost["dx"], ghost["dy"]
    # opciones: no dar marcha atras salvo si es la unica opcion
    inverse = (-dx, -dy) if (dx, dy) != (0, 0) else None
    opts = vecinos_libres(grid, x, y, exclude_dir=inverse)
    if not opts:
        opts = vecinos_libres(grid, x, y)
    if not opts:
        return  # atrapado
    # Heuristica
    if asustado:
        # huir = maximizar distancia a pacman
        best = max(opts, key=lambda d: distancia((x + d[0], y + d[1]), pacman_pos))
    else:
        if random.random() < 0.7:
            # chase: minimizar distancia a pacman
            best = min(opts, key=lambda d: distancia((x + d[0], y + d[1]), pacman_pos))
        else:
            best = random.choice(opts)
    ghost["dx"], ghost["dy"] = best
    ghost["x"] += best[0]
    ghost["y"] += best[1]


def jugar():
    cls()
    sys.stdout.write(show_cursor(False))
    grid, pac_start, ghost_starts = parsear_maze()
    score = 0
    lives = 3
    level = 1
    puntos_totales = sum(row.count('.') + row.count('o') for row in grid)

    def resetear_personajes():
        return {
            "pacman": {"x": pac_start[0], "y": pac_start[1], "dx": -1, "dy": 0, "next_dx": 0, "next_dy": 0},
            "ghosts": [
                {"x": gx, "y": gy, "dx": 0, "dy": -1, "color": GHOST_COLORS[i % 4]}
                for i, (gx, gy) in enumerate(ghost_starts)
            ],
        }

    state = resetear_personajes()
    asustado_hasta = 0.0
    t_ultimo_paso = time.time()
    PASO_DT = 0.12  # 8 movimientos por segundo
    GHOST_DT = 0.18  # los fantasmas algo mas lentos
    t_ultimo_ghost = time.time()
    frame_tick = 0
    mensaje = None
    msg_expira = 0.0

    # Render inicial: maze estatico
    frame = frame_nuevo()
    render_maze_estatico(frame, grid)
    render_hud(frame, score, lives, level)
    render_footer(frame)
    pintar_pacman(frame, state["pacman"]["x"], state["pacman"]["y"],
                  (state["pacman"]["dx"], state["pacman"]["dy"]), frame_tick)
    for g in state["ghosts"]:
        pintar_fantasma(frame, g["x"], g["y"], g["color"])
    flush_frame(frame)

    while True:
        now = time.time()
        asustado = now < asustado_hasta

        # Leer teclas
        while True:
            tecla = leer_tecla_noblock()
            if tecla is None:
                break
            if tecla in ("q", "Q", "\x03"):
                return score, level
            if tecla in ("w", "W", "\x1b[A"):
                state["pacman"]["next_dx"], state["pacman"]["next_dy"] = 0, -1
            elif tecla in ("s", "S", "\x1b[B"):
                state["pacman"]["next_dx"], state["pacman"]["next_dy"] = 0, 1
            elif tecla in ("a", "A", "\x1b[D"):
                state["pacman"]["next_dx"], state["pacman"]["next_dy"] = -1, 0
            elif tecla in ("d", "D", "\x1b[C"):
                state["pacman"]["next_dx"], state["pacman"]["next_dy"] = 1, 0

        # Tick pacman
        if now - t_ultimo_paso >= PASO_DT:
            t_ultimo_paso = now
            frame_tick += 1
            pac = state["pacman"]
            # intentar cambiar a next_dir si es posible
            if (pac["next_dx"], pac["next_dy"]) != (0, 0):
                nx, ny = pac["x"] + pac["next_dx"], pac["y"] + pac["next_dy"]
                if not es_pared(grid, nx, ny):
                    pac["dx"], pac["dy"] = pac["next_dx"], pac["next_dy"]
                    pac["next_dx"], pac["next_dy"] = 0, 0
            # mover en direccion actual si se puede
            old_pos = (pac["x"], pac["y"])
            nx, ny = pac["x"] + pac["dx"], pac["y"] + pac["dy"]
            if not es_pared(grid, nx, ny):
                pac["x"], pac["y"] = nx, ny
                # comer
                celda = grid[ny][nx]
                if celda == '.':
                    grid[ny][nx] = ' '
                    score += 10
                    puntos_totales -= 1
                elif celda == 'o':
                    grid[ny][nx] = ' '
                    score += 50
                    puntos_totales -= 1
                    asustado_hasta = now + 6.0
                    mensaje = "¡FANTASMAS ASUSTADOS!"
                    msg_expira = now + 2.0

            # Repintar pacman
            frame = frame_nuevo()
            # Solo modificamos lo necesario, pero re-pintamos full por simpleza
            # (el shadow buffer hace diff)
            render_maze_estatico(frame, grid)
            render_hud(frame, score, lives, level)
            render_footer(frame, mensaje if now < msg_expira else None)
            pintar_pacman(frame, pac["x"], pac["y"], (pac["dx"], pac["dy"]), frame_tick)
            for g in state["ghosts"]:
                pintar_fantasma(frame, g["x"], g["y"], g["color"], asustado)
            flush_frame(frame)

        # Tick fantasmas
        if now - t_ultimo_ghost >= GHOST_DT:
            t_ultimo_ghost = now
            for g in state["ghosts"]:
                mover_fantasma(grid, g, (state["pacman"]["x"], state["pacman"]["y"]), asustado)
            # repintar tras mover fantasmas
            frame = frame_nuevo()
            render_maze_estatico(frame, grid)
            render_hud(frame, score, lives, level)
            render_footer(frame, mensaje if now < msg_expira else None)
            pintar_pacman(frame, state["pacman"]["x"], state["pacman"]["y"],
                          (state["pacman"]["dx"], state["pacman"]["dy"]), frame_tick)
            for g in state["ghosts"]:
                pintar_fantasma(frame, g["x"], g["y"], g["color"], asustado)
            flush_frame(frame)

        # Colisiones
        for g in state["ghosts"]:
            if (g["x"], g["y"]) == (state["pacman"]["x"], state["pacman"]["y"]):
                if asustado:
                    # comer fantasma
                    score += 200
                    # reset al inicio
                    gi = state["ghosts"].index(g)
                    gx, gy = ghost_starts[gi % len(ghost_starts)]
                    g["x"], g["y"] = gx, gy
                    mensaje = "+200"
                    msg_expira = now + 1.0
                else:
                    lives -= 1
                    if lives <= 0:
                        return score, level
                    # reset todos
                    state = resetear_personajes()
                    mensaje = f"¡VIDAS RESTANTES: {lives}!"
                    msg_expira = now + 1.5
                    time.sleep(1.0)
                    break

        # Win?
        if puntos_totales <= 0:
            level += 1
            grid, _, _ = parsear_maze()
            puntos_totales = sum(row.count('.') + row.count('o') for row in grid)
            state = resetear_personajes()
            mensaje = f"¡NIVEL {level}!"
            msg_expira = now + 1.5
            time.sleep(1.0)
            cls()

        # FPS limit
        time.sleep(0.03)


# ---------- splash + manual + scores ----------

LOGO = [
    "██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗",
    "██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║",
    "██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║",
    "██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║",
    "██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║",
    "╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝",
]

MANUAL_LINEAS = [
    ("PREMISA", "cyanB", "bold"),
    "  Pacman BBS - laberinto cenital con 4 fantasmas.",
    "  Come todos los puntos sin que te pillen.",
    "  4 power pellets (●) hacen huir a los fantasmas brevemente.",
    "",
    ("CONTROLES", "cyanB", "bold"),
    "  WASD / flechas    mover",
    "  Q                 salir",
    "",
    ("MECANICA", "cyanB", "bold"),
    "  Cada punto      +10 pts",
    "  Power pellet    +50 pts + 6s de fantasmas asustados",
    "  Fantasma comido +200 pts (durante asustado)",
    "  3 vidas. Te pillan = pierdes una vida.",
    "  Al comer todos los puntos, nivel siguiente.",
    "",
    ("OBJETIVO", "cyanB", "bold"),
    "  Maximo score posible. Top 10 global y local.",
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - PACMAN BBS".ljust(70), "cyanB", "bold"))
    print(c("=" * 70, "cyanB"))
    print()
    for ln in MANUAL_LINEAS:
        if isinstance(ln, tuple):
            print(c(*ln))
        else:
            print(ln)
    print()
    print(c("-" * 70, "dim"))
    try:
        input(c("  Pulsa Enter para volver al menu...", "amarB"))
    except EOFError:
        pass


def _caja(texto, ancho, color_txt, color_caja="amarB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


def splash():
    cls()
    sys.stdout.write(show_cursor(True))
    ancho = 60
    print()
    print(c("╔" + "═" * ancho + "╗", "amarB"))
    print(_caja("", ancho, "blanco"))
    for ln in LOGO:
        print(_caja(ln, ancho, "amarB"))
    print(_caja("", ancho, "blanco"))
    print(_caja("Clasico cenital. Come puntos, esquiva fantasmas.", ancho, "cyanB"))
    print(_caja("", ancho, "blanco"))
    print(_caja("WASD mover    Q salir", ancho, "blanco"))
    print(_caja("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "amarB"))
    msg = "[Enter] empezar     [M] manual"
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        raw = input("")
    except EOFError:
        return
    if raw.strip().lower() == "m":
        mostrar_manual()


def pantalla_final(score, level):
    ancho = 56
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    lado = c("║", "amarB")

    def dibujar_resumen():
        cls()
        print()
        print(margen + c("╔" + linea + "╗", "amarB"))
        print(margen + lado + c(" GAME OVER ".center(ancho), "rojoB", "bold") + lado)
        print(margen + c("╠" + linea + "╣", "amarB"))
        print(margen + lado + f"  Score        : {c(str(score).rjust(15) + '  ', 'verdeB', 'bold')}".ljust(ancho + 15) + lado)
        print(margen + lado + f"  Nivel        : {c(str(level).rjust(15) + '  ', 'cyanB', 'bold')}".ljust(ancho + 15) + lado)
        print(margen + c("╚" + linea + "╝", "amarB"))
        print()

    dibujar_resumen()
    nombre_guardado = None
    if bbs_scores.entra_en_top_local(score, max_top=MAX_TOP, ascending=ASCENDING) and score > 0:
        print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
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
        nombre_guardado = nombre

    modo = "local"
    while True:
        dibujar_resumen()
        if nombre_guardado:
            print(margen + c(f"  [Acabas de entrar en el TOP como {nombre_guardado}]", "amarB"))
            print()
        scores_e, titulo, _ = bbs_scores.get_top_for_mode(modo, limit=MAX_TOP, ascending=ASCENDING)
        print(margen + c(f" {titulo.strip()}".ljust(ancho), "bold"))
        print(margen + c("─" * ancho, "dim"))
        for i, e in enumerate(scores_e, 1):
            etiqueta = e.display_handle if modo == "global" else e.handle
            color = "amarB" if e.score == score else "blanco"
            print(margen + f"  {i:>2}. {c(etiqueta.ljust(14), color, 'bold')} {c(str(e.score).rjust(8), color)}  {c(e.date, 'dim')}")
        print()
        try:
            raw = input(margen + c("  [L] local   [G] global   [Enter] continuar: ", "dim")).strip().upper()
        except EOFError:
            break
        if raw == "L":
            modo = "local"
            continue
        if raw == "G":
            modo = "global"
            continue
        break


def main():
    if not TERMIOS_OK:
        print("Pacman necesita un TTY con termios.")
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
            score, level = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            pantalla_final(score, level)
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
