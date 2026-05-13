#!/usr/bin/env python3
"""2048 BBS - clon de 2048 en modo texto para Mystic BBS."""
import os
import random
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
    TERMIOS_OK = True
except ImportError:
    TERMIOS_OK = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(SCRIPT_DIR, "2048_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24

CELL_W = 8
CELL_H = 3
GRID_N = 4

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

COLOR_VALOR = {
    0:    ("dim",),
    2:    ("blanco",),
    4:    ("amarB",),
    8:    ("cyanB",),
    16:   ("cyan",),
    32:   ("amar",),
    64:   ("rojoB",),
    128:  ("rojo",),
    256:  ("magenta",),
    512:  ("magentaB",),
    1024: ("verde",),
    2048: ("verdeB", "bold"),
}


def c(txt, *estilos):
    if not estilos:
        return str(txt)
    prefijo = "".join(COLORES[e] for e in estilos if e in COLORES)
    if not prefijo:
        return str(txt)
    return f"{prefijo}{txt}{RESET}"


def color_celda(valor):
    if valor in COLOR_VALOR:
        return COLOR_VALOR[valor]
    if valor > 2048:
        return ("verdeB", "bold")
    return ("blanco",)


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
            # del terminal a una fila que no existe y hace scroll.
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


# ---------- logica ----------

def nuevo_tablero():
    t = [[0] * GRID_N for _ in range(GRID_N)]
    spawn(t)
    spawn(t)
    return t


def spawn(t):
    vacias = [(y, x) for y in range(GRID_N) for x in range(GRID_N) if t[y][x] == 0]
    if not vacias:
        return False
    y, x = random.choice(vacias)
    t[y][x] = 4 if random.random() < 0.1 else 2
    return True


def _mover_fila_izq(fila):
    """Devuelve (nueva_fila, puntos_ganados)."""
    no_ceros = [v for v in fila if v != 0]
    merged = []
    puntos = 0
    i = 0
    while i < len(no_ceros):
        if i + 1 < len(no_ceros) and no_ceros[i] == no_ceros[i + 1]:
            v = no_ceros[i] * 2
            merged.append(v)
            puntos += v
            i += 2
        else:
            merged.append(no_ceros[i])
            i += 1
    while len(merged) < len(fila):
        merged.append(0)
    return merged, puntos


def mover(t, direccion):
    """Devuelve (nuevo_tablero, puntos, cambio_bool)."""
    if direccion == "izq":
        nuevo = []
        puntos = 0
        for fila in t:
            nf, p = _mover_fila_izq(fila)
            nuevo.append(nf)
            puntos += p
    elif direccion == "der":
        nuevo = []
        puntos = 0
        for fila in t:
            nf, p = _mover_fila_izq(list(reversed(fila)))
            nuevo.append(list(reversed(nf)))
            puntos += p
    elif direccion == "arr":
        tras = [list(col) for col in zip(*t)]
        movido = []
        puntos = 0
        for fila in tras:
            nf, p = _mover_fila_izq(fila)
            movido.append(nf)
            puntos += p
        nuevo = [list(col) for col in zip(*movido)]
    elif direccion == "abj":
        tras = [list(col) for col in zip(*t)]
        movido = []
        puntos = 0
        for fila in tras:
            nf, p = _mover_fila_izq(list(reversed(fila)))
            movido.append(list(reversed(nf)))
            puntos += p
        nuevo = [list(col) for col in zip(*movido)]
    else:
        return t, 0, False
    cambio = nuevo != t
    return nuevo, puntos, cambio


def hay_movimientos(t):
    for fila in t:
        if 0 in fila:
            return True
    for y in range(GRID_N):
        for x in range(GRID_N):
            if x + 1 < GRID_N and t[y][x] == t[y][x + 1]:
                return True
            if y + 1 < GRID_N and t[y][x] == t[y + 1][x]:
                return True
    return False


def hay_2048(t):
    return any(v >= 2048 for fila in t for v in fila)


# ---------- render ----------

GRID_ANCHO = CELL_W * GRID_N + (GRID_N + 1)  # 4*8 + 5 = 37
GRID_ALTO = CELL_H * GRID_N + (GRID_N + 1)   # 4*3 + 5 = 17
GRID_X0 = (COLS - GRID_ANCHO) // 2            # ~21
GRID_Y0 = 4


def render(t, score, best, ganado_flag, msg=None):
    frame = frame_nuevo()

    # titulo
    titulo = " 2048 BBS "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, 0, 0, "═" * pad_l, "blancoB")
    set_text(frame, 0, pad_l, titulo, "amarB", "bold")
    set_text(frame, 0, pad_l + len(titulo), "═" * (COLS - pad_l - len(titulo)), "blancoB")

    # score
    info = f" Score: {score}     Best: {best}"
    if ganado_flag:
        info += "     [2048!]"
    set_text(frame, 2, (COLS - len(info)) // 2, info, "blanco")
    # recolorear cabeceras
    x = (COLS - len(info)) // 2
    set_text(frame, 2, x + 8, str(score), "verdeB", "bold")
    idx_best = info.index("Best:") + 6
    set_text(frame, 2, x + idx_best, str(best), "amarB")
    if ganado_flag:
        idx_g = info.index("[2048!]")
        set_text(frame, 2, x + idx_g, "[2048!]", "verdeB", "bold")

    # grid
    for gy in range(GRID_N):
        for gx in range(GRID_N):
            cell_y = GRID_Y0 + gy * (CELL_H + 1)
            cell_x = GRID_X0 + gx * (CELL_W + 1)
            _dibujar_celda(frame, cell_y, cell_x, t[gy][gx])

    # bordes del grid (intersecciones y separadores)
    # Lo hacemos sobreescribiendo las esquinas/cruces donde tocan
    _dibujar_bordes_grid(frame)

    # mensaje opcional
    if msg:
        set_text(frame, 22, (COLS - len(msg)) // 2, msg, "amarB", "bold")

    # controles
    ctrl = " WASD/flechas deslizar    R reiniciar    Q salir "
    set_text(frame, 23, (COLS - len(ctrl)) // 2, ctrl, "dim")

    flush_frame(frame)


def _dibujar_celda(frame, y0, x0, valor):
    estilos = color_celda(valor)
    # bordes
    set_cell(frame, y0, x0, "┌", "dim")
    set_cell(frame, y0, x0 + CELL_W, "┐", "dim")
    set_cell(frame, y0 + CELL_H, x0, "└", "dim")
    set_cell(frame, y0 + CELL_H, x0 + CELL_W, "┘", "dim")
    for cx in range(x0 + 1, x0 + CELL_W):
        set_cell(frame, y0, cx, "─", "dim")
        set_cell(frame, y0 + CELL_H, cx, "─", "dim")
    for cy in range(y0 + 1, y0 + CELL_H):
        set_cell(frame, cy, x0, "│", "dim")
        set_cell(frame, cy, x0 + CELL_W, "│", "dim")
    # interior
    for cy in range(y0 + 1, y0 + CELL_H):
        for cx in range(x0 + 1, x0 + CELL_W):
            set_cell(frame, cy, cx, " ")
    # valor centrado
    if valor != 0:
        s = str(valor)
        text_y = y0 + CELL_H // 2
        text_x = x0 + (CELL_W - len(s)) // 2 + (1 if (CELL_W - len(s)) % 2 else 0)
        # ajuste: queremos centrado dentro del interior (x0+1 .. x0+CELL_W-1)
        text_x = x0 + 1 + ((CELL_W - 1) - len(s)) // 2
        set_text(frame, text_y, text_x, s, *estilos)


def _dibujar_bordes_grid(frame):
    """Cruces y T en intersecciones del grid 4x4."""
    for gy in range(1, GRID_N):
        cy = GRID_Y0 + gy * (CELL_H + 1) - 1
        # mejor: las intersecciones internas, no las dibujamos como cruces — el solapado de celdas hace
        # que cada celda tenga sus bordes propios. Visualmente queda como cajas separadas,
        # lo cual es OK estilo "tiles flotantes" de 2048.
        pass


def render_pausa(msg):
    """Pinta solo el mensaje sin tocar el resto."""
    pass


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


def mejor_score():
    scores = cargar_scores()
    return scores[0][1] if scores else 0


def es_top(puntos):
    if puntos <= 0:
        return False
    scores = cargar_scores()
    if len(scores) < MAX_TOP:
        return True
    return puntos > scores[-1][1]


# ---------- splash y pantalla final ----------

LOGO_2048 = [
    "██████╗  ██████╗ ██╗  ██╗ █████╗ ",
    "╚════██╗██╔═══██╗██║  ██║██╔══██╗",
    " █████╔╝██║   ██║███████║╚█████╔╝",
    "██╔═══╝ ██║   ██║╚════██║██╔══██╗",
    "███████╗╚██████╔╝     ██║╚█████╔╝",
    "╚══════╝ ╚═════╝      ╚═╝ ╚════╝ ",
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
    ancho = 60
    print()
    print(c("╔" + "═" * ancho + "╗", "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_2048:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Combina baldosas hasta llegar a 2048", ancho, "cyanB"))
    print(_caja_linea_splash("WASD o flechas para deslizar.", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "verdeB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_final(score, mejor_anterior, max_baldosa, victoria):
    sys.stdout.write(show_cursor(True))
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    color_caja = "verdeB" if victoria else "rojoB"
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
    titulo = "FIN DE PARTIDA" if not victoria else "ABANDONASTE CON LA CABEZA ALTA"
    print(fila_centrada(titulo, "bold"))
    print(margen + c("╠" + linea + "╣", color_caja))
    print(fila_kv("Puntuacion final  : ", str(score).rjust(18), "verdeB"))
    print(fila_kv("Baldosa mas alta  : ", str(max_baldosa).rjust(18), "amarB"))
    print(fila_kv("Mejor anterior    : ", str(mejor_anterior).rjust(18), "cyanB"))
    print(margen + c("╚" + linea + "╝", color_caja))
    print()

    if es_top(score):
        print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
        nombre = ""
        while not nombre:
            try:
                raw = input(margen + "  Iniciales (3 chars): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalnum())[:3].ljust(3, "A")
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

def jugar():
    cls()
    sys.stdout.write(show_cursor(False))
    tablero = nuevo_tablero()
    score = 0
    best = mejor_score()
    ganado_flag = False  # si ya hemos llegado a 2048 mostrar bandera
    msg = "Mueve con WASD o flechas"

    while True:
        render(tablero, score, best, ganado_flag, msg)
        msg = None
        tecla = leer_tecla()
        if tecla in ("q", "Q", "\x03"):
            return tablero, score, ganado_flag
        if tecla in ("r", "R"):
            tablero = nuevo_tablero()
            score = 0
            ganado_flag = False
            msg = "Tablero reiniciado."
            continue
        direccion = None
        if tecla in ("w", "W", "\x1b[A"):
            direccion = "arr"
        elif tecla in ("s", "S", "\x1b[B"):
            direccion = "abj"
        elif tecla in ("a", "A", "\x1b[D"):
            direccion = "izq"
        elif tecla in ("d", "D", "\x1b[C"):
            direccion = "der"
        if direccion is None:
            continue
        tablero, puntos, cambio = mover(tablero, direccion)
        if cambio:
            score += puntos
            spawn(tablero)
            if not ganado_flag and hay_2048(tablero):
                ganado_flag = True
                msg = "¡Has llegado a 2048! Puedes seguir jugando."
            if not hay_movimientos(tablero):
                render(tablero, score, best, ganado_flag, "Sin movimientos. Game over.")
                import time
                time.sleep(1.0)
                return tablero, score, ganado_flag


def main():
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. 2048 necesita un TTY.")
        return
    try:
        restaurar_terminal(old)
        splash()
        while True:
            old2 = entrar_cbreak()
            tablero, score, ganado_flag = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            best_anterior = mejor_score()
            max_baldosa = max(v for fila in tablero for v in fila)
            pantalla_final(score, best_anterior, max_baldosa, ganado_flag)
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
