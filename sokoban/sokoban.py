#!/usr/bin/env python3
"""Sokoban BBS - empuja cajas a las marcas."""
import os
import sys
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
SCORES_FILE = os.path.join(SCRIPT_DIR, "sokoban_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24

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
            # Saltar la esquina inferior-derecha: escribir ahi provoca auto-wrap
            # del terminal a una fila que no existe y hace scroll de toda la pantalla.
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


# ---------- terminal ----------

def entrar_cbreak():
    if not TERMIOS_OK:
        return None
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        # forzar echo off explicitamente (algunas versiones de tty.setcbreak lo dejan on)
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


def leer_tecla():
    ch = sys.stdin.read(1)
    if ch == "\x1b":
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


# ---------- niveles ----------

# Cada nivel: (nombre, grid_string)
# Caracteres de entrada:
#   #  muro
#   ' ' suelo
#   .  marca (suelo destino)
#   $  caja sobre suelo
#   *  caja sobre marca
#   @  jugador sobre suelo
#   +  jugador sobre marca

LEVELS = [
    ("Primer empujon", """
########
#      #
# @$  .#
#      #
########
"""),
    ("Doble objetivo", """
#########
#       #
# .$ $. #
#       #
#   @   #
#       #
#########
"""),
    ("Sube y empuja", """
##########
#   .    #
#        #
#   $    #
#        #
#   @    #
#        #
##########
"""),
    ("Cuatro esquinas", """
##########
#.      .#
#        #
#  $  $  #
#   @    #
#  $  $  #
#        #
#.      .#
##########
"""),
    ("El callejon", """
##########
#        #
#### ### #
#   @    #
# $ ##   #
#   ##.. #
###  $   #
#        #
##########
"""),
    ("Tres en raya", """
#########
# ..... #
# $$$$$ #
#       #
#   @   #
#########
"""),
    ("Pasillos", """
###########
#         #
# # # # # #
# .       #
# # # # # #
# $       #
# # # # # #
#@        #
###########
"""),
    ("Apretado", """
########
#  .   #
# .$$  #
# $@.  #
#  .$  #
#      #
########
"""),
    ("Cuadrado magico", """
##########
#        #
#  ....  #
#        #
#  $$$$  #
#        #
#   @    #
##########
"""),
    ("Largo viaje", """
##############
#            #
#  $.        #
#  $.        #
#  $.        #
#  $.        #
#@           #
#            #
##############
"""),
]


def parse_level(grid_str):
    """Devuelve dict con mapa (matriz de tiles base), boxes, targets, player."""
    lines = [l for l in grid_str.split("\n") if l]
    # ajustar todas las filas a la misma longitud
    maxw = max(len(l) for l in lines)
    lines = [l + " " * (maxw - len(l)) for l in lines]
    mapa = []
    targets = set()
    boxes = set()
    player = None
    for y, line in enumerate(lines):
        row = []
        for x, ch in enumerate(line):
            if ch == "#":
                row.append("#")
            else:
                row.append(" ")
                if ch in (".", "*", "+"):
                    targets.add((x, y))
                if ch in ("$", "*"):
                    boxes.add((x, y))
                if ch in ("@", "+"):
                    player = (x, y)
        mapa.append(row)
    if player is None:
        raise ValueError("Nivel sin jugador")
    return {"mapa": mapa, "targets": frozenset(targets), "boxes": boxes,
            "player": player, "w": maxw, "h": len(lines)}


# ---------- logica ----------

DELTAS = {
    "arr": (0, -1),
    "abj": (0, 1),
    "izq": (-1, 0),
    "der": (1, 0),
}


def mover(state, direccion):
    """Aplica movimiento. Devuelve True si fue valido (modifica state).
    Antes de modificar, snapshotea (player, boxes_frozen) en state['undo']."""
    dx, dy = DELTAS[direccion]
    px, py = state["player"]
    nx, ny = px + dx, py + dy
    h = state["h"]; w = state["w"]
    if not (0 <= nx < w and 0 <= ny < h):
        return False
    if state["mapa"][ny][nx] == "#":
        return False
    snapshot_boxes = frozenset(state["boxes"])
    snapshot_player = state["player"]
    if (nx, ny) in state["boxes"]:
        bx, by = nx + dx, ny + dy
        if not (0 <= bx < w and 0 <= by < h):
            return False
        if state["mapa"][by][bx] == "#":
            return False
        if (bx, by) in state["boxes"]:
            return False
        state["boxes"].remove((nx, ny))
        state["boxes"].add((bx, by))
    state["player"] = (nx, ny)
    state.setdefault("undo", []).append((snapshot_player, snapshot_boxes))
    state["movs"] = state.get("movs", 0) + 1
    return True


def deshacer(state):
    if not state.get("undo"):
        return False
    player, boxes = state["undo"].pop()
    state["player"] = player
    state["boxes"] = set(boxes)
    state["movs"] = max(0, state.get("movs", 0) - 1)
    return True


def ganado(state):
    return state["boxes"] == set(state["targets"])


# ---------- render ----------

def render(state, nivel_idx, nivel_nombre, score_total, movs, msg=None):
    frame = frame_nuevo()

    # titulo
    titulo = f" SOKOBAN BBS  -  Nivel {nivel_idx + 1}/{len(LEVELS)}: \"{nivel_nombre}\" "
    if len(titulo) > COLS - 2:
        titulo = titulo[:COLS - 5] + "... "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, 0, 0, "═" * pad_l, "blancoB")
    set_text(frame, 0, pad_l, titulo, "amarB", "bold")
    set_text(frame, 0, pad_l + len(titulo), "═" * (COLS - pad_l - len(titulo)), "blancoB")

    # mapa centrado
    w = state["w"]
    h = state["h"]
    map_y0 = max(3, (ROWS - h) // 2 - 1)
    map_x0 = max(2, (COLS - w) // 2)

    mapa = state["mapa"]
    boxes = state["boxes"]
    targets = state["targets"]
    px, py = state["player"]

    for y in range(h):
        for x in range(w):
            cx, cy = map_x0 + x, map_y0 + y
            base = mapa[y][x]
            es_marca = (x, y) in targets
            es_caja = (x, y) in boxes
            es_jug = (x, y) == (px, py)
            if base == "#":
                set_cell(frame, cy, cx, "█", "azul")
            elif es_jug:
                if es_marca:
                    set_cell(frame, cy, cx, "@", "cyanB", "bold")
                else:
                    set_cell(frame, cy, cx, "@", "cyanB", "bold")
            elif es_caja:
                if es_marca:
                    set_cell(frame, cy, cx, "█", "verdeB", "bold")
                else:
                    set_cell(frame, cy, cx, "█", "amarB", "bold")
            elif es_marca:
                set_cell(frame, cy, cx, "·", "rojo")
            # else: suelo (espacio en blanco, ya esta limpio)

    # status
    cajas_colocadas = sum(1 for b in boxes if b in targets)
    total_cajas = len(boxes)
    stats = f" Movs: {movs}   Cajas: {cajas_colocadas}/{total_cajas}   Score total: {score_total} "
    set_text(frame, ROWS - 3, 0, "─" * COLS, "dim")
    sx = (COLS - len(stats)) // 2
    set_text(frame, ROWS - 2, 0, " " * COLS, "blanco")
    set_text(frame, ROWS - 2, sx, stats, "blanco")
    set_text(frame, ROWS - 2, sx + 7, str(movs), "amarB", "bold")
    idx_caja = stats.index("Cajas:") + 7
    set_text(frame, ROWS - 2, sx + idx_caja, f"{cajas_colocadas}/{total_cajas}",
             "verdeB" if cajas_colocadas == total_cajas else "cyanB", "bold")
    idx_score = stats.index("Score total:") + 13
    set_text(frame, ROWS - 2, sx + idx_score, str(score_total), "verdeB", "bold")

    set_text(frame, ROWS - 1, 0, "─" * COLS, "dim")
    ctrl = " WASD mover    R reset    U undo    N saltar    Q salir "
    set_text(frame, ROWS - 1, (COLS - len(ctrl)) // 2, ctrl, "dim")

    if msg:
        set_text(frame, map_y0 + h + 1, (COLS - len(msg)) // 2, msg, "amarB", "bold")

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
                if len(parts) == 4:
                    nombre, puntos, niveles, fecha = parts
                    try:
                        out.append((nombre, int(puntos), int(niveles), fecha))
                    except ValueError:
                        continue
            return sorted(out, key=lambda x: -x[1])[:MAX_TOP]
    except OSError:
        return []


def guardar_score(nombre, puntos, niveles):
    scores = cargar_scores()
    scores.append((nombre, puntos, niveles, date.today().isoformat()))
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


# ---------- splash y final ----------

LOGO_SOKOBAN = [
    "███████╗ ██████╗ ██╗  ██╗ ██████╗ ██████╗  █████╗ ███╗   ██╗",
    "██╔════╝██╔═══██╗██║ ██╔╝██╔═══██╗██╔══██╗██╔══██╗████╗  ██║",
    "███████╗██║   ██║█████╔╝ ██║   ██║██████╔╝███████║██╔██╗ ██║",
    "╚════██║██║   ██║██╔═██╗ ██║   ██║██╔══██╗██╔══██║██║╚██╗██║",
    "███████║╚██████╔╝██║  ██╗╚██████╔╝██████╔╝██║  ██║██║ ╚████║",
    "╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝",
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


MANUAL_LINEAS = [
    ('PREMISA', 'cyanB', 'bold'),
    '  Clon de Sokoban. 10 niveles a mano de dificultad creciente.',
    '  Empujas cajas hacia las marcas. No puedes tirar de las cajas.',
    '',
    ('CONTROLES (char-mode)', 'cyanB', 'bold'),
    '  W A S D / flechas    mover',
    '  U                    undo (deshacer ultimo movimiento)',
    '  R                    reiniciar nivel',
    '  N                    saltar al siguiente nivel',
    '  Q                    salir',
    '',
    ('TILES', 'cyanB', 'bold'),
    '  @ tu     # muro     . suelo     $ caja     o marca',
    '  Caja sobre marca = caja iluminada.',
    '',
    ('PUNTUACION', 'cyanB', 'bold'),
    '  Por nivel: 100 - movimientos (minimo 10).',
    '  Total acumulado de todos los niveles completados.',
    '  Top 10 persistente.',
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - SOKOBAN BBS".ljust(70), "cyanB", "bold"))
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
    ancho = 70
    print()
    print(c("╔" + "═" * ancho + "╗", "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_SOKOBAN:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Empuja las cajas hasta las marcas", ancho, "cyanB"))
    print(_caja_linea_splash("Solo empujar, nunca tirar. Pensar antes de empujar.", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "verdeB"))
    msg = "[Enter] empezar     [M] manual"
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        raw = input("")
    except EOFError:
        return
    if raw.strip().lower() == "m":
        mostrar_manual()


def pantalla_final(score_total, niveles_resueltos, abandono):
    sys.stdout.write(show_cursor(True))
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    color_caja = "verdeB" if niveles_resueltos == len(LEVELS) else ("amarB" if niveles_resueltos > 0 else "rojoB")
    lado = c("║", color_caja)

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

    print(margen + c("╔" + linea + "╗", color_caja))
    if niveles_resueltos == len(LEVELS):
        titulo = "¡HAS COMPLETADO TODOS LOS NIVELES!"
    elif abandono:
        titulo = "ABANDONASTE"
    else:
        titulo = "FIN DE PARTIDA"
    print(fila_centrada(titulo, "bold"))
    print(margen + c("╠" + linea + "╣", color_caja))
    print(fila_kv("Niveles resueltos : ", f"{niveles_resueltos}/{len(LEVELS)}".rjust(18), "verdeB"))
    print(fila_kv("Puntuacion total  : ", str(score_total).rjust(18), "amarB"))
    print(margen + c("╚" + linea + "╝", color_caja))
    print()

    if es_top(score_total):
        print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
        nombre = ""
        while not nombre:
            try:
                raw = input(margen + "  Iniciales (3 chars): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalnum())[:3].ljust(3, "A")
        scores = guardar_score(nombre, score_total, niveles_resueltos)
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("─" * ancho, "dim"))
    for i, (n, p, nv, fe) in enumerate(scores, 1):
        color = "amarB" if p == score_total else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(6), color)}  Nv.{nv:<2}  {c(fe, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- juego ----------

def jugar_nivel(idx, score_total_actual):
    """Devuelve (resuelto_bool, movs, abandono_bool, saltar_bool)."""
    nombre, grid_str = LEVELS[idx]
    state = parse_level(grid_str)
    msg = None

    cls()
    while True:
        render(state, idx, nombre, score_total_actual, state.get("movs", 0), msg)
        msg = None
        if ganado(state):
            render(state, idx, nombre, score_total_actual, state.get("movs", 0),
                   msg="¡Nivel completado!")
            import time
            time.sleep(1.0)
            return True, state.get("movs", 0), False, False

        tecla = leer_tecla()
        if tecla in ("q", "Q", "\x03"):
            return False, state.get("movs", 0), True, False
        elif tecla in ("w", "W", "\x1b[A"):
            if not mover(state, "arr"):
                msg = "No se puede."
        elif tecla in ("s", "S", "\x1b[B"):
            if not mover(state, "abj"):
                msg = "No se puede."
        elif tecla in ("a", "A", "\x1b[D"):
            if not mover(state, "izq"):
                msg = "No se puede."
        elif tecla in ("d", "D", "\x1b[C"):
            if not mover(state, "der"):
                msg = "No se puede."
        elif tecla in ("r", "R"):
            state = parse_level(grid_str)
            msg = "Nivel reiniciado."
        elif tecla in ("u", "U"):
            if not deshacer(state):
                msg = "No hay nada que deshacer."
        elif tecla in ("n", "N"):
            return False, state.get("movs", 0), False, True


def jugar():
    score_total = 0
    niveles_resueltos = 0
    cls()
    sys.stdout.write(show_cursor(False))

    for idx in range(len(LEVELS)):
        resuelto, movs, abandono, saltar = jugar_nivel(idx, score_total)
        if abandono:
            return score_total, niveles_resueltos, True
        if saltar:
            continue
        if resuelto:
            niveles_resueltos += 1
            bono = max(10, 100 - movs)
            score_total += bono
    return score_total, niveles_resueltos, False


def main():
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. Sokoban necesita un TTY.")
        return
    try:
        restaurar_terminal(old)
        splash()
        while True:
            old2 = entrar_cbreak()
            score, niveles, abandono = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            pantalla_final(score, niveles, abandono)
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
