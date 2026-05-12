#!/usr/bin/env python3
"""Catacumba BBS - dungeon pseudo-3D en ASCII con raycasting."""
import math
import os
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
MAPA = [
    "############",
    "#..........#",
    "#.##.###.#.#",
    "#..#...#.#.#",
    "#.##.#.#.#.#",
    "#....#.....#",
    "#.##.##.####",
    "#..#.......#",
    "#..####.##.#",
    "#......#...#",
    "#E#####..###",
    "############",
]
# Posicion inicial del jugador
PLAYER_START_X = 1.5
PLAYER_START_Y = 1.5

FOV = math.pi / 3.0  # 60 grados
MAX_DIST = 16.0

VEL_MOV = 0.15
VEL_ROT = 0.10

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


def lanzar_rayo(px, py, angulo):
    """DDA raycasting. Devuelve (distancia, tipo) donde tipo=0 muro normal, 1 salida."""
    cos_a = math.cos(angulo)
    sin_a = math.sin(angulo)
    # paso fino para no perder muros
    paso = 0.05
    d = 0.0
    while d < MAX_DIST:
        d += paso
        tx = px + cos_a * d
        ty = py + sin_a * d
        mx = int(tx)
        my = int(ty)
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
    """Devuelve (char, color) segun distancia."""
    if tipo == 1:
        # salida en magenta/verde brillante
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


# ---------- render ----------

def render(player, msg=None):
    frame = frame_nuevo()
    px, py = player["x"], player["y"]
    pa = player["angulo"]

    # cielo y suelo de fondo
    medio = VIEW_H // 2
    for col in range(VIEW_W):
        for row in range(VIEW_H):
            sy = VIEW_Y0 + row
            sx = VIEW_X0 + col
            if row < medio:
                # cielo: dim
                set_cell(frame, sy, sx, " ")
            else:
                # suelo: marron leve con shading horizontal
                if row > medio + 4:
                    set_cell(frame, sy, sx, "·", "amar")
                else:
                    set_cell(frame, sy, sx, " ")

    # paredes con raycasting
    for col in range(VIEW_W):
        ang = pa - FOV / 2.0 + (col / VIEW_W) * FOV
        dist, tipo = lanzar_rayo(px, py, ang)
        # correccion fish-eye
        dist = max(0.001, dist * math.cos(ang - pa))
        # altura de la tira
        h = int((VIEW_H * 1.3) / dist)
        h = min(h, VIEW_H)
        top = (VIEW_H - h) // 2
        ch, col_estilo = shade_char(dist, tipo)
        for row in range(top, top + h):
            sy = VIEW_Y0 + row
            sx = VIEW_X0 + col
            set_cell(frame, sy, sx, ch, col_estilo)

    # mini-mapa en esquina superior derecha del area 3D, encima de las paredes
    mm_x = VIEW_X0 + VIEW_W - MAP_W - 1
    mm_y = VIEW_Y0
    for y in range(MAP_H):
        for x in range(MAP_W):
            ch_mapa = MAPA[y][x]
            cell_y = mm_y + y
            cell_x = mm_x + x
            if int(px) == x and int(py) == y:
                set_cell(frame, cell_y, cell_x, "@", "amarB", "bold")
            elif ch_mapa == "#":
                set_cell(frame, cell_y, cell_x, "█", "dim")
            elif ch_mapa == "E":
                set_cell(frame, cell_y, cell_x, "E", "verdeB", "bold")
            else:
                set_cell(frame, cell_y, cell_x, ".", "dim")

    # HUD abajo
    set_text(frame, 21, 0, "─" * (COLS - 1), "dim")
    info = f" Posicion: ({px:.1f}, {py:.1f})    Angulo: {math.degrees(pa):>5.0f}°"
    set_text(frame, 22, 1, info, "blanco")

    if msg:
        set_text(frame, 22, COLS - len(msg) - 1, msg, "amarB", "bold")

    ctrl = " W/S avanzar/retroceder    A/D girar    Q salir "
    set_text(frame, 23, (COLS - len(ctrl)) // 2, ctrl, "dim")

    flush_frame(frame)


# ---------- splash y final ----------

LOGO_CATACUMBA = [
    " ██████╗ █████╗ ████████╗ █████╗  ██████╗██╗   ██╗███╗   ███╗██████╗  █████╗ ",
    "██╔════╝██╔══██╗╚══██╔══╝██╔══██╗██╔════╝██║   ██║████╗ ████║██╔══██╗██╔══██╗",
    "██║     ███████║   ██║   ███████║██║     ██║   ██║██╔████╔██║██████╔╝███████║",
    "██║     ██╔══██║   ██║   ██╔══██║██║     ██║   ██║██║╚██╔╝██║██╔══██╗██╔══██║",
    "╚██████╗██║  ██║   ██║   ██║  ██║╚██████╗╚██████╔╝██║ ╚═╝ ██║██████╔╝██║  ██║",
    " ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝",
]

LOGO_BBS = [
    "██████╗ ██████╗ ███████╗",
    "██╔══██╗██╔══██╗██╔════╝",
    "██████╔╝██████╔╝███████╗",
    "██╔══██╗██╔══██╗╚════██║",
    "██████╔╝██████╔╝███████║",
    "╚═════╝ ╚═════╝ ╚══════╝",
]


def _caja_linea_splash(texto, ancho, color_txt, color_caja="magentaB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


def splash():
    cls()
    sys.stdout.write(show_cursor(True))
    ancho = 78
    print()
    print(c("╔" + "═" * ancho + "╗", "magentaB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_CATACUMBA:
        print(_caja_linea_splash(ln, ancho, "magentaB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "magentaB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Mazmorra pseudo-3D con raycasting en ASCII", ancho, "cyanB"))
    print(_caja_linea_splash("Encuentra la salida E del laberinto", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "magentaB"))
    msg = "Pulsa Enter para entrar a la catacumba..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_victoria(pasos, tiempo):
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
    print(margen + c("╚" + linea + "╝", "verdeB"))
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- juego ----------

def intentar_mover(player, nx, ny):
    """Mueve al jugador si la posicion destino no es muro. Maneja deslizamiento por paredes."""
    # primero probar X
    if not es_muro(int(nx), int(player["y"])):
        player["x"] = nx
    if not es_muro(int(player["x"]), int(ny)):
        player["y"] = ny


def jugar():
    cls()
    sys.stdout.write(show_cursor(False))
    player = {
        "x": PLAYER_START_X,
        "y": PLAYER_START_Y,
        "angulo": 0.0,
    }
    msg = None
    pasos = 0
    t_ini = time.time()

    while True:
        ahora = time.time()

        # leer todas las teclas pendientes
        movido = False
        while True:
            tecla = leer_tecla_noblock()
            if tecla is None:
                break
            if tecla in ("q", "Q", "\x03"):
                return False, pasos, time.time() - t_ini
            elif tecla in ("w", "W", "\x1b[A"):
                nx = player["x"] + math.cos(player["angulo"]) * VEL_MOV
                ny = player["y"] + math.sin(player["angulo"]) * VEL_MOV
                intentar_mover(player, nx, ny)
                movido = True
            elif tecla in ("s", "S", "\x1b[B"):
                nx = player["x"] - math.cos(player["angulo"]) * VEL_MOV
                ny = player["y"] - math.sin(player["angulo"]) * VEL_MOV
                intentar_mover(player, nx, ny)
                movido = True
            elif tecla in ("a", "A", "\x1b[D"):
                player["angulo"] -= VEL_ROT
                movido = True
            elif tecla in ("d", "D", "\x1b[C"):
                player["angulo"] += VEL_ROT
                movido = True

        if movido:
            pasos += 1

        # comprobar salida
        if es_salida(int(player["x"]), int(player["y"])):
            return True, pasos, time.time() - t_ini

        render(player, msg)
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
            ganado, pasos, tiempo = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            if ganado:
                pantalla_victoria(pasos, tiempo)
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
