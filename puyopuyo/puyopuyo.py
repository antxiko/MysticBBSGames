#!/usr/bin/env python3
"""Puyo Puyo BBS - clon de Puyo Puyo en modo texto."""
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(SCRIPT_DIR, "puyopuyo_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24

GRID_W = 6
GRID_H = 12

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

# Tipos de puyo: 1-5 (0 = vacio)
COLOR_PUYO = {
    1: "rojoB",
    2: "verdeB",
    3: "azulB",
    4: "amarB",
    5: "magentaB",
}
N_COLORES = 5


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


# ---------- logica ----------

# direcciones del eje (axis) relativo al pivote (pivot):
# 0 = arriba, 1 = derecha, 2 = abajo, 3 = izquierda
def pos_axis(px, py, direccion):
    if direccion == 0:
        return px, py - 1
    if direccion == 1:
        return px + 1, py
    if direccion == 2:
        return px, py + 1
    return px - 1, py


def colision(grid, px, py, direccion):
    """True si la pieza en (px, py) con eje en `direccion` choca."""
    ax, ay = pos_axis(px, py, direccion)
    for x, y in [(px, py), (ax, ay)]:
        if x < 0 or x >= GRID_W:
            return True
        if y >= GRID_H:
            return True
        if y >= 0 and grid[y][x] != 0:
            return True
    return False


def nueva_pieza():
    return {
        "x": GRID_W // 2 - 1,
        "y": 0,
        "dir": 0,
        "color_pivot": random.randint(1, N_COLORES),
        "color_axis": random.randint(1, N_COLORES),
    }


def integrar_pieza(grid, pieza):
    """Coloca la pieza en el grid sin verificar gravedad."""
    px, py = pieza["x"], pieza["y"]
    ax, ay = pos_axis(px, py, pieza["dir"])
    if 0 <= py < GRID_H:
        grid[py][px] = pieza["color_pivot"]
    if 0 <= ay < GRID_H:
        grid[ay][ax] = pieza["color_axis"]


def aplicar_gravedad(grid):
    """Hace caer todos los puyos. Devuelve True si cambio algo."""
    cambio = False
    for x in range(GRID_W):
        col = [grid[y][x] for y in range(GRID_H)]
        no_ceros = [v for v in col if v != 0]
        nuevo = [0] * (GRID_H - len(no_ceros)) + no_ceros
        if nuevo != col:
            cambio = True
        for y in range(GRID_H):
            grid[y][x] = nuevo[y]
    return cambio


def encontrar_grupos(grid):
    """Devuelve lista de grupos (cada grupo = lista de (x,y))."""
    visitados = set()
    grupos = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            if grid[y][x] == 0 or (x, y) in visitados:
                continue
            color = grid[y][x]
            grupo = []
            pila = [(x, y)]
            local_visit = set()
            while pila:
                cx, cy = pila.pop()
                if (cx, cy) in local_visit:
                    continue
                if not (0 <= cx < GRID_W and 0 <= cy < GRID_H):
                    continue
                if grid[cy][cx] != color:
                    continue
                local_visit.add((cx, cy))
                grupo.append((cx, cy))
                pila.extend([(cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)])
            visitados |= local_visit
            if len(grupo) >= 4:
                grupos.append(grupo)
    return grupos


def procesar_cadenas(grid, estado_callback=None):
    """Procesa todas las cadenas. Devuelve (puntos_total, cadena_max, total_eliminados)."""
    cadena = 0
    puntos_total = 0
    total_eliminados = 0
    while True:
        grupos = encontrar_grupos(grid)
        if not grupos:
            break
        cadena += 1
        cleared = sum(len(g) for g in grupos)
        total_eliminados += cleared
        chain_bonus = 2 ** (cadena - 1)
        puntos_total += chain_bonus * cleared * 10
        # animacion: callback antes de borrar para que se vea el grupo
        if estado_callback:
            estado_callback(grid, cadena, "highlight", grupos)
        # limpiar
        for grupo in grupos:
            for x, y in grupo:
                grid[y][x] = 0
        if estado_callback:
            estado_callback(grid, cadena, "cleared", [])
        aplicar_gravedad(grid)
        if estado_callback:
            estado_callback(grid, cadena, "gravity", [])
    return puntos_total, cadena, total_eliminados


# ---------- render ----------

# Posicion del tablero en la pantalla
BOARD_X0 = 16  # columna 0-indexed del marco izquierdo
BOARD_Y0 = 4   # fila del marco superior
PUYO_W = 2     # cada puyo se renderiza con 2 chars

# Total ancho del tablero interno: GRID_W * PUYO_W = 12 chars
# Total filas internas: GRID_H = 12 filas
# Marco: 2 extra ancho, 2 extra alto

NEXT_X0 = BOARD_X0 + GRID_W * PUYO_W + 6
NEXT_Y0 = BOARD_Y0


def _dibujar_marco(frame, x0, y0, ancho, alto, color="blancoB"):
    set_cell(frame, y0, x0, "╔", color)
    set_cell(frame, y0, x0 + ancho - 1, "╗", color)
    set_cell(frame, y0 + alto - 1, x0, "╚", color)
    set_cell(frame, y0 + alto - 1, x0 + ancho - 1, "╝", color)
    for cx in range(x0 + 1, x0 + ancho - 1):
        set_cell(frame, y0, cx, "═", color)
        set_cell(frame, y0 + alto - 1, cx, "═", color)
    for cy in range(y0 + 1, y0 + alto - 1):
        set_cell(frame, cy, x0, "║", color)
        set_cell(frame, cy, x0 + ancho - 1, "║", color)


def _dibujar_puyo(frame, py_y, px_x, color_id, highlight=False):
    """Dibuja un puyo en celda de grid (px_x, py_y) en su posicion de pantalla."""
    if color_id == 0:
        return
    sx = BOARD_X0 + 1 + px_x * PUYO_W
    sy = BOARD_Y0 + 1 + py_y
    estilo = COLOR_PUYO[color_id]
    ch = "█"
    if highlight:
        # parpadeo: invertir o usar dim
        set_cell(frame, sy, sx, ch, estilo, "dim")
        set_cell(frame, sy, sx + 1, ch, estilo, "dim")
    else:
        set_cell(frame, sy, sx, ch, estilo, "bold")
        set_cell(frame, sy, sx + 1, ch, estilo, "bold")


def render(grid, pieza, siguiente, score, nivel, eliminados, cadena_actual=0, msg=None, highlight_cells=None):
    frame = frame_nuevo()

    # titulo
    titulo = " PUYO PUYO BBS "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, 0, 0, "═" * pad_l, "blancoB")
    set_text(frame, 0, pad_l, titulo, "magentaB", "bold")
    set_text(frame, 0, pad_l + len(titulo), "═" * (COLS - pad_l - len(titulo)), "blancoB")

    # tablero
    _dibujar_marco(frame, BOARD_X0, BOARD_Y0, GRID_W * PUYO_W + 2, GRID_H + 2)

    # puyos del grid
    hi_set = set(highlight_cells or [])
    for y in range(GRID_H):
        for x in range(GRID_W):
            v = grid[y][x]
            if v != 0:
                _dibujar_puyo(frame, y, x, v, highlight=(x, y) in hi_set)

    # pieza activa
    if pieza is not None:
        px, py = pieza["x"], pieza["y"]
        if 0 <= py < GRID_H:
            _dibujar_puyo(frame, py, px, pieza["color_pivot"])
        ax, ay = pos_axis(px, py, pieza["dir"])
        if 0 <= ay < GRID_H and 0 <= ax < GRID_W:
            _dibujar_puyo(frame, ay, ax, pieza["color_axis"])

    # next preview
    set_text(frame, NEXT_Y0, NEXT_X0, "Next:", "cyanB", "bold")
    _dibujar_marco(frame, NEXT_X0, NEXT_Y0 + 1, PUYO_W + 2 + 1, 4, "blanco")
    # dibujar siguiente: par vertical (eje arriba, pivot abajo)
    if siguiente is not None:
        c_axis, c_pivot = siguiente
        # dentro del marco preview: filas NEXT_Y0+2, NEXT_Y0+3
        sx = NEXT_X0 + 1
        for cx in (sx, sx + 1):
            set_cell(frame, NEXT_Y0 + 2, cx, "█", COLOR_PUYO[c_axis], "bold")
        for cx in (sx, sx + 1):
            set_cell(frame, NEXT_Y0 + 3, cx, "█", COLOR_PUYO[c_pivot], "bold")

    # HUD a la derecha
    hud_x = NEXT_X0
    hud_y = NEXT_Y0 + 7
    set_text(frame, hud_y,     hud_x, f"Puntos:    {score}", "blanco")
    set_text(frame, hud_y,     hud_x + 11, str(score), "verdeB", "bold")
    set_text(frame, hud_y + 2, hud_x, f"Nivel:     {nivel}", "blanco")
    set_text(frame, hud_y + 2, hud_x + 11, str(nivel), "amarB", "bold")
    set_text(frame, hud_y + 4, hud_x, f"Eliminados:{eliminados}", "blanco")
    set_text(frame, hud_y + 4, hud_x + 11, str(eliminados), "cyanB")
    if cadena_actual >= 2:
        set_text(frame, hud_y + 6, hud_x, f"CADENA x{cadena_actual}!", "rojoB", "bold")

    # mensaje
    if msg:
        set_text(frame, 22, (COLS - len(msg)) // 2, msg, "amarB", "bold")

    # controles
    ctrl = " AD mover    W rotar    S softdrop    SPACE drop    Q salir "
    set_text(frame, 23, (COLS - len(ctrl)) // 2, ctrl, "dim")

    flush_frame(frame)


# ---------- scores ----------

def cargar_scores():
    if not os.path.exists(SCORES_FILE):
        return []
    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            out = []
            for linea in f:
                parts = linea.strip().split(";")
                if len(parts) == 3:
                    nombre, puntos, fecha = parts
                    try:
                        out.append((nombre, int(puntos), fecha))
                    except ValueError:
                        continue
            return sorted(out, key=lambda x: -x[1])[:MAX_TOP]
    except OSError:
        return []


def guardar_score(nombre, puntos):
    scores = cargar_scores()
    scores.append((nombre, puntos, date.today().isoformat()))
    scores = sorted(scores, key=lambda x: -x[1])[:MAX_TOP]
    try:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            for n, p, d in scores:
                f.write(f"{n};{p};{d}\n")
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


# ---------- splash y pantalla final ----------

LOGO_PUYO = [
    "██████╗ ██╗   ██╗██╗   ██╗ ██████╗ ",
    "██╔══██╗██║   ██║╚██╗ ██╔╝██╔══██╗",
    "██████╔╝██║   ██║ ╚████╔╝ ██║  ██║",
    "██╔═══╝ ██║   ██║  ╚██╔╝  ██║  ██║",
    "██║     ╚██████╔╝   ██║   ╚██████╔╝",
    "╚═╝      ╚═════╝    ╚═╝    ╚═════╝ ",
]

LOGO_BBS = [
    "██████╗ ██████╗ ███████╗",
    "██╔══██╗██╔══██╗██╔════╝",
    "██████╔╝██████╔╝███████╗",
    "██╔══██╗██╔══██╗╚════██║",
    "██████╔╝██████╔╝███████║",
    "╚═════╝ ╚═════╝ ╚══════╝",
]


def _caja_linea_splash(texto, ancho, color_txt, color_caja="verdeB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


def splash():
    cls()
    sys.stdout.write(show_cursor(True))
    ancho = 62
    print()
    print(c("╔" + "═" * ancho + "╗", "magentaB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_PUYO:
        print(_caja_linea_splash(ln, ancho, "rojoB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_PUYO:
        print(_caja_linea_splash(ln, ancho, "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Pares de puyos. 4 o mas conectados explotan.", ancho, "cyanB"))
    print(_caja_linea_splash("Encadena explosiones para multiplicar puntos.", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "magentaB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_final(score, nivel, eliminados, max_cadena):
    sys.stdout.write(show_cursor(True))
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    lado = c("║", "rojoB")

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

    print(margen + c("╔" + linea + "╗", "rojoB"))
    print(fila_centrada("GAME OVER", "bold"))
    print(margen + c("╠" + linea + "╣", "rojoB"))
    print(fila_kv("Puntuacion final  : ", str(score).rjust(18), "verdeB"))
    print(fila_kv("Nivel alcanzado   : ", str(nivel).rjust(18), "amarB"))
    print(fila_kv("Puyos eliminados  : ", str(eliminados).rjust(18), "cyanB"))
    print(fila_kv("Cadena maxima     : ", f"x{max_cadena}".rjust(18), "magentaB"))
    print(margen + c("╚" + linea + "╝", "rojoB"))
    print()

    if es_top(score):
        print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
        nombre = ""
        while not nombre:
            try:
                raw = input(margen + "  Iniciales (3 letras): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalpha())[:3].ljust(3, "A")
        scores = guardar_score(nombre, score)
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("─" * ancho, "dim"))
    for i, (n, p, d) in enumerate(scores, 1):
        color = "amarB" if p == score else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(8), color)}  {c(d, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- juego ----------

def velocidad_tick(nivel):
    """Segundos entre caidas de la pieza."""
    return max(0.10, 0.6 - (nivel - 1) * 0.05)


def jugar():
    cls()
    sys.stdout.write(show_cursor(False))
    grid = [[0] * GRID_W for _ in range(GRID_H)]
    pieza = nueva_pieza()
    siguiente = (random.randint(1, N_COLORES), random.randint(1, N_COLORES))
    score = 0
    eliminados = 0
    nivel = 1
    max_cadena = 0

    # Si la pieza inicial colisiona = game over
    if colision(grid, pieza["x"], pieza["y"] + 1, pieza["dir"]):
        # raro, pero por si acaso
        pass

    ultimo_tick = time.time()
    soft_drop = False
    cadena_actual = 0

    while True:
        ahora = time.time()
        intervalo = velocidad_tick(nivel)
        if soft_drop:
            intervalo = min(intervalo, 0.05)

        # leer input no bloqueante
        tecla = leer_tecla_noblock()
        if tecla is not None:
            if tecla in ("q", "Q", "\x03"):
                return score, nivel, eliminados, max_cadena
            elif tecla in ("a", "A", "\x1b[D"):
                if not colision(grid, pieza["x"] - 1, pieza["y"], pieza["dir"]):
                    pieza["x"] -= 1
            elif tecla in ("d", "D", "\x1b[C"):
                if not colision(grid, pieza["x"] + 1, pieza["y"], pieza["dir"]):
                    pieza["x"] += 1
            elif tecla in ("w", "W", "\x1b[A"):
                # rotar horario
                nueva_dir = (pieza["dir"] + 1) % 4
                if not colision(grid, pieza["x"], pieza["y"], nueva_dir):
                    pieza["dir"] = nueva_dir
                else:
                    # wall-kick: probar desplazar pivote
                    for dx in (-1, 1, 0):
                        if dx == 0:
                            continue
                        if not colision(grid, pieza["x"] + dx, pieza["y"], nueva_dir):
                            pieza["x"] += dx
                            pieza["dir"] = nueva_dir
                            break
            elif tecla in ("s", "S", "\x1b[B"):
                soft_drop = True
            elif tecla == " ":
                # hard drop: bajar hasta colisionar
                while not colision(grid, pieza["x"], pieza["y"] + 1, pieza["dir"]):
                    pieza["y"] += 1
                # forzar tick inmediato
                ultimo_tick = ahora - intervalo - 1

        # tick de caida
        if ahora - ultimo_tick >= intervalo:
            ultimo_tick = ahora
            soft_drop = False
            # intentar bajar pieza
            if not colision(grid, pieza["x"], pieza["y"] + 1, pieza["dir"]):
                pieza["y"] += 1
            else:
                # asentar pieza
                integrar_pieza(grid, pieza)
                # gravedad individual (por si axis quedo flotando)
                aplicar_gravedad(grid)
                # procesar cadenas con animacion
                def callback(g, n_cad, fase, grupos):
                    nonlocal cadena_actual
                    if fase == "highlight":
                        cadena_actual = n_cad
                        hi = []
                        for grupo in grupos:
                            hi.extend(grupo)
                        render(g, None, siguiente, score, nivel, eliminados, n_cad, msg=f"CADENA x{n_cad}!", highlight_cells=hi)
                        time.sleep(0.35)
                    elif fase == "cleared":
                        render(g, None, siguiente, score, nivel, eliminados, n_cad, msg=f"CADENA x{n_cad}!")
                        time.sleep(0.15)
                    elif fase == "gravity":
                        render(g, None, siguiente, score, nivel, eliminados, n_cad, msg=f"CADENA x{n_cad}!")
                        time.sleep(0.15)
                pts, cadena_max_local, elim = procesar_cadenas(grid, callback)
                score += pts
                eliminados += elim
                if cadena_max_local > max_cadena:
                    max_cadena = cadena_max_local
                # subir nivel cada 30 eliminados
                nivel = 1 + eliminados // 30
                cadena_actual = 0
                # nueva pieza
                pieza = nueva_pieza()
                pieza["color_pivot"] = siguiente[1]
                pieza["color_axis"] = siguiente[0]
                siguiente = (random.randint(1, N_COLORES), random.randint(1, N_COLORES))
                # game over si la nueva pieza ya colisiona
                if colision(grid, pieza["x"], pieza["y"], pieza["dir"]) or colision(grid, pieza["x"], pieza["y"] + 1, pieza["dir"]):
                    render(grid, pieza, siguiente, score, nivel, eliminados, 0, msg="GAME OVER")
                    time.sleep(1.0)
                    return score, nivel, eliminados, max_cadena

        render(grid, pieza, siguiente, score, nivel, eliminados, cadena_actual)
        # pequeno sleep para no quemar CPU
        time.sleep(0.01)


def main():
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. Puyo Puyo necesita un TTY.")
        return
    try:
        restaurar_terminal(old)
        splash()
        while True:
            old2 = entrar_cbreak()
            score, nivel, eliminados, max_cadena = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            pantalla_final(score, nivel, eliminados, max_cadena)
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
