#!/usr/bin/env python3
"""Snake BBS - clon del Snake clasico en modo texto."""
import os
import random
import select
import sys
import time
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
SCORES_FILE = os.path.join(SCRIPT_DIR, "snake_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24

TOP_ROW = 1
GAME_TOP = 2
GAME_BOTTOM = 20
SEP1_ROW = 21
STATUS_ROW = 22
BOTTOM_ROW = 23
GRID_LEFT = 2
GRID_RIGHT = COLS - 1

PUNTOS_POR_COMIDA = 10
LONGITUD_INICIAL = 4

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

REVERSO = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

COLORES = {
    "rojo":    "\x1b[31m",
    "verde":   "\x1b[32m",
    "amar":    "\x1b[33m",
    "azul":    "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan":    "\x1b[36m",
    "blanco":  "\x1b[37m",
    "rojoB":   "\x1b[91m",
    "verdeB":  "\x1b[92m",
    "amarB":   "\x1b[93m",
    "cyanB":   "\x1b[96m",
    "bold":    "\x1b[1m",
    "dim":     "\x1b[2m",
}
RESET = "\x1b[0m"


def c(txt, *estilos):
    if not estilos:
        return str(txt)
    for e in estilos:
        if e in COLORES:
            return f"{COLORES[e]}{txt}{RESET}"
    return str(txt)


def at(row, col):
    return f"\x1b[{row};{col}H"


def cls():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


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


def leer_tecla_no_bloq():
    """Devuelve el caracter disponible (o secuencia de flecha) o None."""
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        # posible secuencia de flecha: ESC [ X
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


# ---------- dibujo ----------

def dibujar_marco():
    doble = "\u2550" * (COLS - 2)
    linea_s = "\u2500" * (COLS - 2)
    lado = c("\u2551", "blanco")
    titulo = " Snake BBS "
    pad_l = (COLS - 2 - len(titulo)) // 2
    pad_r = (COLS - 2) - pad_l - len(titulo)
    cabecera = "\u2550" * pad_l + titulo + "\u2550" * pad_r
    sys.stdout.write(at(TOP_ROW, 1) + c("\u2554" + cabecera + "\u2557", "blanco"))
    hueco = " " * (COLS - 2)
    for y in range(GAME_TOP, GAME_BOTTOM + 1):
        sys.stdout.write(at(y, 1) + lado + hueco + lado)
    sys.stdout.write(at(SEP1_ROW, 1) + c("\u2560" + doble + "\u2563", "blanco"))
    sys.stdout.write(at(STATUS_ROW, 1) + lado + hueco + lado)
    sys.stdout.write(at(BOTTOM_ROW, 1) + c("\u255A" + doble + "\u255D", "blanco"))
    # pie fuera del marco
    pie = " WASD o flechas para mover   |   Q para salir "
    sys.stdout.write(at(BOTTOM_ROW + 1, (COLS - len(pie)) // 2) + c(pie, "dim"))
    sys.stdout.flush()


def render_frame(snake, comida, puntos, mejor, antiguo_snake, antigua_comida):
    buf = "\x1b[s"
    # borrar segmentos antiguos que ya no estan
    nuevos = set(snake)
    for seg in antiguo_snake:
        if seg not in nuevos:
            x, y = seg
            buf += at(y, x) + " "
    # borrar comida antigua si ha cambiado
    if antigua_comida is not None and antigua_comida != comida:
        x, y = antigua_comida
        buf += at(y, x) + " "
    # dibujar snake: cabeza brillante, cuerpo verde normal
    if snake:
        for seg in snake[1:]:
            x, y = seg
            buf += at(y, x) + c("\u2588", "verde")
        x, y = snake[0]
        buf += at(y, x) + c("\u2588", "verdeB", "bold")
    # dibujar comida
    if comida is not None:
        x, y = comida
        buf += at(y, x) + c("*", "rojoB", "bold")
    # status
    buf += at(STATUS_ROW, 2) + " " * (COLS - 2)
    estado = (
        f" Puntos: {c(str(puntos).rjust(5), 'verdeB', 'bold')}  "
        f"Longitud: {c(str(len(snake)).rjust(3), 'cyanB')}  "
        f"Mejor: {c(str(mejor).rjust(5), 'amarB')}"
    )
    buf += at(STATUS_ROW, 3) + estado
    buf += "\x1b[u"
    sys.stdout.write(buf)
    sys.stdout.flush()


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
    scores = cargar_scores()
    if puntos <= 0:
        return False
    if len(scores) < MAX_TOP:
        return True
    return puntos > scores[-1][1]


# ---------- splash y final ----------

LOGO_SNAKE = [
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2557   \u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557  \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551 \u2588\u2588\u2554\u255D\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2554\u2588\u2588\u2557 \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2554\u255D \u2588\u2588\u2588\u2588\u2588\u2557  ",
    "\u255A\u2550\u2550\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2551\u255A\u2588\u2588\u2557\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u255D  ",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551 \u255A\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D\u255A\u2550\u255D  \u255A\u2550\u2550\u2550\u255D\u255A\u2550\u255D  \u255A\u2550\u255D\u255A\u2550\u255D  \u255A\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D",
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
    ancho = 60
    print()
    print(c("\u2554" + "\u2550" * ancho + "\u2557", "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_SNAKE:
        print(_caja_linea_splash(ln, ancho, "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("El clasico Snake en ANSI", ancho, "cyanB"))
    print(_caja_linea_splash("Come, crece, no choques.", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("\u255A" + "\u2550" * ancho + "\u255D", "verdeB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_final(puntos, longitud, muerte):
    cls()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "\u2550" * ancho
    lado = c("\u2551", "rojoB")

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

    print()
    print(margen + c("\u2554" + linea + "\u2557", "rojoB"))
    print(fila_centrada("GAME OVER", "bold"))
    print(margen + c("\u2560" + linea + "\u2563", "rojoB"))
    print(fila_centrada(muerte, "amar"))
    print(margen + c("\u2560" + linea + "\u2563", "rojoB"))
    print(fila_kv("Puntos finales : ", str(puntos).rjust(10), "verdeB"))
    print(fila_kv("Longitud final : ", str(longitud).rjust(10), "cyanB"))
    print(margen + c("\u255A" + linea + "\u255D", "rojoB"))
    print()

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
        scores = guardar_score(nombre, puntos)
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("\u2500" * ancho, "dim"))
    for i, (n, p, d) in enumerate(scores, 1):
        color = "amarB" if p == puntos else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(8), color)}  {c(d, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- juego ----------

def nueva_comida(snake):
    ocupados = set(snake)
    while True:
        x = random.randint(GRID_LEFT, GRID_RIGHT)
        y = random.randint(GAME_TOP, GAME_BOTTOM)
        if (x, y) not in ocupados:
            return (x, y)


def jugar():
    # Snake inicial en el centro, moviendose a la derecha
    cx = COLS // 2
    cy = (GAME_TOP + GAME_BOTTOM) // 2
    snake = [(cx - i, cy) for i in range(LONGITUD_INICIAL)]
    direccion = RIGHT
    pendiente = RIGHT  # direccion solicitada para el proximo tick
    comida = nueva_comida(snake)
    puntos = 0
    mejor = mejor_score()
    comidas = 0
    tick_seg = 0.15

    antiguo_snake = []
    antigua_comida = None

    cls()
    sys.stdout.write(show_cursor(False))
    dibujar_marco()
    render_frame(snake, comida, puntos, mejor, antiguo_snake, antigua_comida)
    antiguo_snake = list(snake)
    antigua_comida = comida

    muerte = "Te estampaste contra la pared"

    while True:
        inicio = time.time()

        # leer todas las teclas pendientes (solo guardamos la ultima valida)
        while True:
            tecla = leer_tecla_no_bloq()
            if tecla is None:
                break
            nueva = None
            if tecla in ("w", "W", "\x1b[A"):
                nueva = UP
            elif tecla in ("s", "S", "\x1b[B"):
                nueva = DOWN
            elif tecla in ("a", "A", "\x1b[D"):
                nueva = LEFT
            elif tecla in ("d", "D", "\x1b[C"):
                nueva = RIGHT
            elif tecla in ("q", "Q", "\x03"):
                muerte = "Abandonaste"
                return puntos, len(snake), muerte
            if nueva and nueva != REVERSO.get(direccion):
                pendiente = nueva

        direccion = pendiente
        dx, dy = direccion
        cabeza = snake[0]
        nueva_cabeza = (cabeza[0] + dx, cabeza[1] + dy)

        # colision con pared
        if (nueva_cabeza[0] < GRID_LEFT or nueva_cabeza[0] > GRID_RIGHT or
                nueva_cabeza[1] < GAME_TOP or nueva_cabeza[1] > GAME_BOTTOM):
            return puntos, len(snake), muerte

        # colision consigo mismo
        if nueva_cabeza in snake[:-1]:
            muerte = "Te has mordido la cola"
            return puntos, len(snake), muerte

        snake.insert(0, nueva_cabeza)

        if nueva_cabeza == comida:
            puntos += PUNTOS_POR_COMIDA
            comidas += 1
            comida = nueva_comida(snake)
            if comidas % 5 == 0:
                tick_seg = max(0.05, tick_seg * 0.95)
        else:
            snake.pop()

        render_frame(snake, comida, puntos, mejor, antiguo_snake, antigua_comida)
        antiguo_snake = list(snake)
        antigua_comida = comida

        resto = tick_seg - (time.time() - inicio)
        if resto > 0:
            time.sleep(resto)


if __name__ == "__main__":
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        sys.exit(1)
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. Snake necesita un TTY.")
        sys.exit(1)
    try:
        splash()
        puntos, longitud, muerte = jugar()
        sys.stdout.write(show_cursor(True))
        sys.stdout.flush()
        # Volvemos a modo linea para pedir iniciales sin drama
        restaurar_terminal(old)
        old = None
        pantalla_final(puntos, longitud, muerte)
    except KeyboardInterrupt:
        pass
    finally:
        if old is not None:
            restaurar_terminal(old)
        sys.stdout.write(show_cursor(True))
        sys.stdout.flush()
