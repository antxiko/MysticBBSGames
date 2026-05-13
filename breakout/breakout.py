#!/usr/bin/env python3
"""Breakout BBS - paleta, bola, ladrillos."""
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
SCORES_FILE = os.path.join(SCRIPT_DIR, "breakout_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24

# Frame del area de juego
FRAME_TOP = 1
FRAME_BOTTOM = 19  # ANSI 20
FRAME_LEFT = 1
FRAME_RIGHT = 78   # ANSI 79
GAME_W = FRAME_RIGHT - FRAME_LEFT - 1  # 76
GAME_H = FRAME_BOTTOM - FRAME_TOP - 1  # 17
# Coordenadas internas 0-indexed dentro del area: (x, y), x in [0, GAME_W), y in [0, GAME_H)
# Screen col = FRAME_LEFT + 1 + x, screen row = FRAME_TOP + 1 + y

BRICK_ROWS = 6
BRICK_W = 2  # cada ladrillo ocupa 2 cells
BRICKS_PER_ROW = GAME_W // BRICK_W  # 38

PADDLE_W = 7
PADDLE_Y = GAME_H - 1   # ultima fila del area de juego

VIDAS_INICIAL = 3

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

# Colores por fila de ladrillo (de arriba a abajo)
COLOR_FILA = ["rojoB", "magentaB", "amarB", "verdeB", "cyanB", "azulB"]
PUNTOS_FILA = [50, 40, 30, 20, 15, 10]


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
                continue  # evitar auto-wrap scroll
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


# ---------- logica ----------

def crear_ladrillos():
    """Devuelve dict {(x, y): color_idx} con todos los ladrillos del nivel.
    Cada ladrillo ocupa 2 cells horizontales, asi que (x, y) marca el cell izquierdo."""
    bricks = {}
    for row in range(BRICK_ROWS):
        for i in range(BRICKS_PER_ROW):
            bx = i * BRICK_W  # cell izquierdo
            bricks[(bx, row)] = row
    return bricks


def hay_ladrillo(bricks, x, y):
    """Devuelve la clave (left_x, y) si hay ladrillo en cell (x, y), o None."""
    if (x, y) in bricks:
        return (x, y)
    if (x - 1, y) in bricks:
        return (x - 1, y)
    return None


def nuevo_juego():
    return {
        "bricks": crear_ladrillos(),
        "paddle_x": (GAME_W - PADDLE_W) // 2,
        "paddle_dir": 0,          # -1 izquierda, 0 quieta, +1 derecha
        "ball_x": 0.0,
        "ball_y": 0.0,
        "ball_dx": 1,
        "ball_dy": -1,
        "ball_attached": True,    # esperando servir
        "vidas": VIDAS_INICIAL,
        "score": 0,
        "nivel": 1,
        "velocidad": 0.08,        # segundos por tick de bola
    }


def servir_pelota(state):
    state["ball_attached"] = False
    state["ball_dy"] = -1
    state["ball_dx"] = random.choice([-1, 1])


def reset_pelota_en_paleta(state):
    state["ball_attached"] = True
    state["ball_x"] = state["paddle_x"] + PADDLE_W // 2
    state["ball_y"] = PADDLE_Y - 1
    state["paddle_dir"] = 0


def mover_paleta(state, delta):
    nx = state["paddle_x"] + delta
    if nx < 0:
        nx = 0
    if nx + PADDLE_W > GAME_W:
        nx = GAME_W - PADDLE_W
    state["paddle_x"] = nx
    if state["ball_attached"]:
        state["ball_x"] = nx + PADDLE_W // 2


def tick_pelota(state):
    """Avanza la pelota un tick. Devuelve True si se perdio vida, False si todo bien."""
    if state["ball_attached"]:
        return False

    bx = int(state["ball_x"])
    by = int(state["ball_y"])
    dx = state["ball_dx"]
    dy = state["ball_dy"]

    # mover una celda
    nx = bx + dx
    ny = by + dy

    # rebote en paredes laterales
    if nx < 0 or nx >= GAME_W:
        dx = -dx
        nx = bx + dx

    # rebote en techo
    if ny < 0:
        dy = -dy
        ny = by + dy

    # rebote en paleta
    if ny == PADDLE_Y:
        if state["paddle_x"] <= nx < state["paddle_x"] + PADDLE_W:
            # rebote
            dy = -dy
            ny = by + dy
            # ajustar dx segun posicion de impacto en la paleta
            rel = nx - state["paddle_x"]
            if rel < 2:
                dx = -1
            elif rel >= PADDLE_W - 2:
                dx = 1
            # tercio central mantiene dx
        elif ny >= PADDLE_Y + 1:
            # se cayo por debajo de la paleta
            state["vidas"] -= 1
            reset_pelota_en_paleta(state)
            return True

    # rebote en ladrillo
    if 0 <= ny < BRICK_ROWS:
        clave = hay_ladrillo(state["bricks"], nx, ny)
        if clave is not None:
            color_idx = state["bricks"].pop(clave)
            state["score"] += PUNTOS_FILA[color_idx]
            dy = -dy
            ny = by + dy

    # actualizar
    state["ball_x"] = nx
    state["ball_y"] = ny
    state["ball_dx"] = dx
    state["ball_dy"] = dy

    # caer al fondo (por si el rebote en paleta no se detecto bien)
    if ny >= GAME_H:
        state["vidas"] -= 1
        reset_pelota_en_paleta(state)
        return True

    return False


def nivel_completado(state):
    return len(state["bricks"]) == 0


def avanzar_nivel(state):
    state["nivel"] += 1
    state["bricks"] = crear_ladrillos()
    state["velocidad"] = max(0.04, state["velocidad"] * 0.9)
    reset_pelota_en_paleta(state)


# ---------- render ----------

def render(state, msg=None):
    frame = frame_nuevo()

    # titulo
    titulo = " BREAKOUT BBS "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, 0, 0, "═" * pad_l, "blancoB")
    set_text(frame, 0, pad_l, titulo, "amarB", "bold")
    set_text(frame, 0, pad_l + len(titulo), "═" * (COLS - pad_l - len(titulo) - 1), "blancoB")

    # marco del area
    # esquinas y bordes
    set_cell(frame, FRAME_TOP, FRAME_LEFT, "╔", "blanco")
    set_cell(frame, FRAME_TOP, FRAME_RIGHT, "╗", "blanco")
    set_cell(frame, FRAME_BOTTOM, FRAME_LEFT, "╚", "blanco")
    set_cell(frame, FRAME_BOTTOM, FRAME_RIGHT, "╝", "blanco")
    for cx in range(FRAME_LEFT + 1, FRAME_RIGHT):
        set_cell(frame, FRAME_TOP, cx, "═", "blanco")
        set_cell(frame, FRAME_BOTTOM, cx, "═", "blanco")
    for cy in range(FRAME_TOP + 1, FRAME_BOTTOM):
        set_cell(frame, cy, FRAME_LEFT, "║", "blanco")
        set_cell(frame, cy, FRAME_RIGHT, "║", "blanco")

    # ladrillos
    for (bx, by), color_idx in state["bricks"].items():
        col = COLOR_FILA[color_idx]
        sy = FRAME_TOP + 1 + by
        sx_l = FRAME_LEFT + 1 + bx
        set_cell(frame, sy, sx_l, "█", col, "bold")
        set_cell(frame, sy, sx_l + 1, "█", col, "bold")

    # paleta
    py = FRAME_TOP + 1 + PADDLE_Y
    for i in range(PADDLE_W):
        px = FRAME_LEFT + 1 + state["paddle_x"] + i
        set_cell(frame, py, px, "═", "cyanB", "bold")

    # bola
    if state["ball_attached"] or 0 <= state["ball_y"] < GAME_H:
        bsx = FRAME_LEFT + 1 + int(state["ball_x"])
        bsy = FRAME_TOP + 1 + int(state["ball_y"])
        set_cell(frame, bsy, bsx, "O", "blancoB", "bold")

    # HUD
    hud_y = FRAME_BOTTOM + 1
    info = f" Score: {state['score']}    Vidas: {state['vidas']}    Nivel: {state['nivel']}"
    set_text(frame, hud_y, 1, info, "blanco")
    sxoff = info.index("Score:") + 7
    set_text(frame, hud_y, sxoff, str(state['score']), "verdeB", "bold")
    sxoff = info.index("Vidas:") + 7
    set_text(frame, hud_y, sxoff, str(state['vidas']), "rojoB", "bold")
    sxoff = info.index("Nivel:") + 7
    set_text(frame, hud_y, sxoff, str(state['nivel']), "amarB", "bold")

    # mensaje
    if msg:
        set_text(frame, hud_y + 1, (COLS - len(msg)) // 2, msg, "amarB", "bold")

    # controles
    ctrl = " A/D direccion (pulsar otra vez = parar)   ESPACIO servir   Q salir "
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


# ---------- splash y final ----------

LOGO_BREAKOUT = [
    "██████╗ ██████╗ ███████╗ █████╗ ██╗  ██╗ ██████╗ ██╗   ██╗████████╗",
    "██╔══██╗██╔══██╗██╔════╝██╔══██╗██║ ██╔╝██╔═══██╗██║   ██║╚══██╔══╝",
    "██████╔╝██████╔╝█████╗  ███████║█████╔╝ ██║   ██║██║   ██║   ██║   ",
    "██╔══██╗██╔══██╗██╔══╝  ██╔══██║██╔═██╗ ██║   ██║██║   ██║   ██║   ",
    "██████╔╝██║  ██║███████╗██║  ██║██║  ██╗╚██████╔╝╚██████╔╝   ██║   ",
    "╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝   ",
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
    ancho = 74
    print()
    print(c("╔" + "═" * ancho + "╗", "cyanB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BREAKOUT:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Rompe todos los ladrillos sin perder la bola.", ancho, "cyanB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "cyanB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_final(score, nivel):
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
    print(margen + c("╚" + linea + "╝", "rojoB"))
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
        scores = guardar_score(nombre, score, nivel)
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("─" * ancho, "dim"))
    for i, (n, p, nv, fe) in enumerate(scores, 1):
        color = "amarB" if p == score else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(8), color)}  Nv.{nv:<2}  {c(fe, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- juego ----------

def jugar():
    cls()
    sys.stdout.write(show_cursor(False))
    state = nuevo_juego()
    reset_pelota_en_paleta(state)

    msg = "Pulsa ESPACIO para servir la pelota"
    TICK_PADDLE = 0.04  # 25 FPS para la paleta — mas fluido que el de la bola
    ultimo_tick_ball = time.time()
    ultimo_tick_paddle = time.time()

    while state["vidas"] > 0:
        ahora = time.time()

        # leer todas las teclas pendientes
        while True:
            tecla = leer_tecla_noblock()
            if tecla is None:
                break
            if tecla in ("q", "Q", "\x03"):
                return state
            elif tecla in ("a", "A", "\x1b[D"):
                # toggle: si ya va a la izquierda, parar; si no, ir a la izquierda
                state["paddle_dir"] = 0 if state["paddle_dir"] == -1 else -1
            elif tecla in ("d", "D", "\x1b[C"):
                state["paddle_dir"] = 0 if state["paddle_dir"] == 1 else 1
            elif tecla == " ":
                if state["ball_attached"]:
                    servir_pelota(state)
                    msg = None

        # tick paleta (mas rapido que el de la bola para sensacion fluida)
        if ahora - ultimo_tick_paddle >= TICK_PADDLE:
            ultimo_tick_paddle = ahora
            if state["paddle_dir"] != 0:
                mover_paleta(state, state["paddle_dir"])
                # auto-stop al chocar contra pared
                if state["paddle_dir"] < 0 and state["paddle_x"] == 0:
                    state["paddle_dir"] = 0
                elif state["paddle_dir"] > 0 and state["paddle_x"] + PADDLE_W >= GAME_W:
                    state["paddle_dir"] = 0

        # tick bola
        if ahora - ultimo_tick_ball >= state["velocidad"]:
            ultimo_tick_ball = ahora
            perdida = tick_pelota(state)
            if perdida:
                if state["vidas"] > 0:
                    msg = f"Vida perdida! Quedan {state['vidas']}. ESPACIO para servir."
                else:
                    break
            if nivel_completado(state):
                avanzar_nivel(state)
                msg = f"Nivel {state['nivel']}! ESPACIO para servir."

        render(state, msg)
        time.sleep(0.01)

    return state


def main():
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. Breakout necesita un TTY.")
        return
    try:
        restaurar_terminal(old)
        splash()
        while True:
            old2 = entrar_cbreak()
            state = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            pantalla_final(state["score"], state["nivel"])
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
