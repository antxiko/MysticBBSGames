#!/usr/bin/env python3
"""Buscaminas BBS - el clasico buscaminas en modo texto."""
import os
import random
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
SCORES_FILE = os.path.join(SCRIPT_DIR, "buscaminas_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24

DIFICULTADES = [
    ("Principiante", 9, 9, 10, 1),
    ("Intermedio",   16, 16, 40, 2),
    ("Experto",      30, 16, 99, 3),
]

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

COLOR_NUMERO = {
    1: "azulB",
    2: "verdeB",
    3: "rojoB",
    4: "azul",
    5: "rojo",
    6: "cyanB",
    7: "magentaB",
    8: "blancoB",
}


def c(txt, *estilos):
    if not estilos:
        return str(txt)
    prefijo = ""
    for e in estilos:
        if e in COLORES:
            prefijo += COLORES[e]
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


def set_text(frame, y, x, texto, *estilos):
    """Escribe texto en frame[y][x:]. Cada char ocupa una celda con sus estilos."""
    prefijo = "".join(COLORES[e] for e in estilos if e in COLORES)
    sufijo = RESET if prefijo else ""
    for i, ch in enumerate(texto):
        cx = x + i
        if 0 <= y < SHADOW_ROWS and 0 <= cx < SHADOW_COLS:
            frame[y][cx] = f"{prefijo}{ch}{sufijo}" if prefijo else ch


def flush_frame(frame):
    """Emite solo las celdas que cambian respecto al shadow."""
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
    """Bloquea hasta recibir una tecla. Devuelve string: letra normal o '\\x1b[A' para flecha."""
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


# ---------- tablero ----------

def crear_tablero(filas, cols):
    return [[{"mina": False, "adj": 0, "rev": False, "flag": False}
             for _ in range(cols)] for _ in range(filas)]


def colocar_minas(tablero, filas, cols, n_minas, libre_x, libre_y):
    """Coloca minas aleatoriamente excluyendo la zona 3x3 alrededor de (libre_x, libre_y)."""
    prohibidas = set()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ny, nx = libre_y + dy, libre_x + dx
            if 0 <= ny < filas and 0 <= nx < cols:
                prohibidas.add((nx, ny))
    candidatas = [(x, y) for y in range(filas) for x in range(cols) if (x, y) not in prohibidas]
    if n_minas > len(candidatas):
        n_minas = len(candidatas)
    for x, y in random.sample(candidatas, n_minas):
        tablero[y][x]["mina"] = True
    # calcular adyacentes
    for y in range(filas):
        for x in range(cols):
            if tablero[y][x]["mina"]:
                continue
            adj = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < filas and 0 <= nx < cols and tablero[ny][nx]["mina"]:
                        adj += 1
            tablero[y][x]["adj"] = adj


def revelar(tablero, filas, cols, x, y):
    """Revela con flood-fill desde (x, y). Devuelve True si se revelo una mina."""
    celda = tablero[y][x]
    if celda["flag"] or celda["rev"]:
        return False
    if celda["mina"]:
        celda["rev"] = True
        return True
    pila = [(x, y)]
    while pila:
        cx, cy = pila.pop()
        c0 = tablero[cy][cx]
        if c0["rev"] or c0["flag"] or c0["mina"]:
            continue
        c0["rev"] = True
        if c0["adj"] == 0:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < filas and 0 <= nx < cols:
                        pila.append((nx, ny))
    return False


def todos_revelados(tablero, filas, cols):
    for y in range(filas):
        for x in range(cols):
            c0 = tablero[y][x]
            if not c0["mina"] and not c0["rev"]:
                return False
    return True


def contar_banderas(tablero, filas, cols):
    total = 0
    for y in range(filas):
        for x in range(cols):
            if tablero[y][x]["flag"]:
                total += 1
    return total


# ---------- render ----------

def char_celda(celda, mostrar_minas=False):
    """Devuelve el par (caracter, estilos) para una celda."""
    if mostrar_minas and celda["mina"]:
        return ("*", ("rojoB", "bold"))
    if celda["flag"]:
        return ("P", ("rojoB", "bold"))
    if not celda["rev"]:
        return ("\u2591", ("dim",))
    if celda["mina"]:
        return ("*", ("rojoB", "bold"))
    if celda["adj"] == 0:
        return (" ", ())
    color = COLOR_NUMERO.get(celda["adj"], "blanco")
    return (str(celda["adj"]), (color, "bold"))


def render(tablero, filas, cols, cur_x, cur_y, dificultad, minas_total, t_ini, mensaje=None, mostrar_minas=False):
    frame = frame_nuevo()
    nombre_dif = dificultad[0]
    nombre = f" Buscaminas BBS ({nombre_dif}) "
    pad_l = (COLS - len(nombre)) // 2
    pad_r = COLS - pad_l - len(nombre)
    # cabecera: guiones + titulo + guiones
    set_text(frame, 0, 0, "\u2550" * pad_l, "blancoB")
    set_text(frame, 0, pad_l, nombre, "blancoB", "bold")
    set_text(frame, 0, pad_l + len(nombre), "\u2550" * pad_r, "blancoB")

    # grid
    banderas = contar_banderas(tablero, filas, cols)
    tiempo = int(time.time() - t_ini) if t_ini else 0
    ancho_grid = cols * 2
    sangria = (COLS - ancho_grid) // 2
    y_base = 2
    for y in range(filas):
        for x in range(cols):
            ch, estilos = char_celda(tablero[y][x], mostrar_minas)
            col = sangria + x * 2
            if x == cur_x and y == cur_y and not mostrar_minas:
                set_text(frame, y_base + y, col, ch, "reverso")
                set_text(frame, y_base + y, col + 1, " ", "reverso")
            else:
                set_text(frame, y_base + y, col, ch, *estilos)
                # segunda columna de la celda: espacio limpio

    # status bar
    y_status = y_base + filas + 1
    restan_minas = minas_total - banderas
    texto_status = f" Minas: {restan_minas:>3}  Banderas: {banderas:>3}  Tiempo: {tiempo:>4}s"
    x_status = (COLS - len(texto_status)) // 2
    set_text(frame, y_status, x_status, texto_status, "blanco")
    # recolorear los valores
    set_text(frame, y_status, x_status + 8, f"{restan_minas:>3}", "rojoB", "bold")
    set_text(frame, y_status, x_status + 23, f"{banderas:>3}", "amarB")
    set_text(frame, y_status, x_status + 36, f"{tiempo:>4}s", "cyanB")

    # pie
    y_pie = y_status + 2
    pie = " WASD/flechas mover    ESPACIO revelar    F bandera    Q salir "
    x_pie = (COLS - len(pie)) // 2
    set_text(frame, y_pie, x_pie, pie, "dim")

    # mensaje
    if mensaje:
        y_msg = y_pie + 2
        x_msg = (COLS - len(mensaje)) // 2
        set_text(frame, y_msg, x_msg, mensaje, "amarB", "bold")

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
                    nombre, puntos, dif, fecha = parts
                    try:
                        out.append((nombre, int(puntos), dif, fecha))
                    except ValueError:
                        continue
            return sorted(out, key=lambda x: -x[1])[:MAX_TOP]
    except OSError:
        return []


def guardar_score(nombre, puntos, dif):
    scores = cargar_scores()
    scores.append((nombre, puntos, dif, date.today().isoformat()))
    scores = sorted(scores, key=lambda x: -x[1])[:MAX_TOP]
    try:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            for n, p, d, fe in scores:
                f.write(f"{n};{p};{d};{fe}\n")
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


# ---------- splash y menu ----------

LOGO_BUSCA = [
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557   \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2557 ",
    "\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551",
    "\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u255A\u2550\u2550\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u255A\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u255A\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551",
    "\u255A\u2550\u2550\u2550\u2550\u2550\u255D  \u255A\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u2550\u2550\u2550\u2550\u255D\u255A\u2550\u255D  \u255A\u2550\u255D",
]

LOGO_MINAS = [
    "\u2588\u2588\u2588\u2557   \u2588\u2588\u2588\u2557\u2588\u2588\u2557\u2588\u2588\u2588\u2557   \u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D",
    "\u2588\u2588\u2554\u2588\u2588\u2588\u2588\u2554\u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2554\u2588\u2588\u2557 \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u2588\u2588\u2551\u255A\u2588\u2588\u2554\u255D\u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551\u255A\u2588\u2588\u2557\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551\u255A\u2550\u2550\u2550\u2550\u2588\u2588\u2551",
    "\u2588\u2588\u2551 \u255A\u2550\u255D \u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551 \u255A\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551",
    "\u255A\u2550\u255D     \u255A\u2550\u255D\u255A\u2550\u255D\u255A\u2550\u255D  \u255A\u2550\u2550\u2550\u255D\u255A\u2550\u255D  \u255A\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D",
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
    for ln in LOGO_BUSCA:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_MINAS:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("El clasico Buscaminas para Mystic BBS", ancho, "cyanB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("\u255A" + "\u2550" * ancho + "\u255D", "verdeB"))
    print()
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def menu_dificultad():
    """Elige dificultad con cursor. Devuelve la tupla de DIFICULTADES o None."""
    sel = 0
    while True:
        cls()
        sys.stdout.write(show_cursor(False))
        titulo = " Elige dificultad "
        print(c(titulo.center(COLS), "amarB", "bold"))
        print()
        for i, (nombre, filas, cols_, minas, _) in enumerate(DIFICULTADES):
            texto = f"{nombre:<14} {cols_}x{filas}   {minas} minas"
            if i == sel:
                linea = "  > " + c(texto, "amarB", "bold") + " <"
            else:
                linea = "    " + c(texto, "blanco")
            print(linea.center(COLS + 30))  # visual rough center
        print()
        print(c("  W/S o flechas para elegir, ENTER para empezar, Q para salir".center(COLS), "dim"))
        sys.stdout.flush()
        tecla = leer_tecla()
        if tecla in ("w", "W", "\x1b[A"):
            sel = (sel - 1) % len(DIFICULTADES)
        elif tecla in ("s", "S", "\x1b[B"):
            sel = (sel + 1) % len(DIFICULTADES)
        elif tecla in ("\r", "\n"):
            return DIFICULTADES[sel]
        elif tecla in ("q", "Q", "\x03"):
            return None


# ---------- pantalla final ----------

def pantalla_final(gano, puntos, tiempo, dif_nombre):
    sys.stdout.write(show_cursor(True))
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "\u2550" * ancho
    color_caja = "verdeB" if gano else "rojoB"
    lado = c("\u2551", color_caja)

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

    titulo = "¡VICTORIA!" if gano else "BOOM - GAME OVER"
    print(margen + c("\u2554" + linea + "\u2557", color_caja))
    print(fila_centrada(titulo, "bold"))
    print(margen + c("\u2560" + linea + "\u2563", color_caja))
    print(fila_kv("Dificultad : ", dif_nombre.rjust(20), "amarB"))
    print(fila_kv("Tiempo     : ", f"{tiempo}s".rjust(20), "cyanB"))
    print(fila_kv("Puntos     : ", str(puntos).rjust(20), "verdeB" if gano else "rojoB"))
    print(margen + c("\u255A" + linea + "\u255D", color_caja))
    print()

    if gano and es_top(puntos):
        print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
        nombre = ""
        while not nombre:
            try:
                raw = input(margen + "  Iniciales (3 letras): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalpha())[:3].ljust(3, "A")
        scores = guardar_score(nombre, puntos, dif_nombre)
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("\u2500" * ancho, "dim"))
    for i, (n, p, d, fe) in enumerate(scores, 1):
        color = "amarB" if p == puntos else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(6), color)}  {d[:12]:<12}  {c(fe, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- juego ----------

def jugar_partida(dificultad):
    nombre, cols_, filas, minas_total, mult = dificultad
    tablero = crear_tablero(filas, cols_)
    primer_click = True
    cur_x = cols_ // 2
    cur_y = filas // 2
    t_ini = None
    mensaje = None
    gano = False

    cls()
    sys.stdout.write(show_cursor(False))

    while True:
        render(tablero, filas, cols_, cur_x, cur_y, dificultad, minas_total, t_ini, mensaje)
        mensaje = None
        tecla = leer_tecla()
        if tecla in ("q", "Q", "\x03"):
            return False, 0, 0
        elif tecla in ("w", "W", "\x1b[A"):
            cur_y = (cur_y - 1) % filas
        elif tecla in ("s", "S", "\x1b[B"):
            cur_y = (cur_y + 1) % filas
        elif tecla in ("a", "A", "\x1b[D"):
            cur_x = (cur_x - 1) % cols_
        elif tecla in ("d", "D", "\x1b[C"):
            cur_x = (cur_x + 1) % cols_
        elif tecla in ("f", "F"):
            c0 = tablero[cur_y][cur_x]
            if not c0["rev"]:
                c0["flag"] = not c0["flag"]
        elif tecla == " ":
            c0 = tablero[cur_y][cur_x]
            if c0["flag"] or c0["rev"]:
                continue
            if primer_click:
                colocar_minas(tablero, filas, cols_, minas_total, cur_x, cur_y)
                primer_click = False
                t_ini = time.time()
            mina_revelada = revelar(tablero, filas, cols_, cur_x, cur_y)
            if mina_revelada:
                # mostrar todas las minas
                for y in range(filas):
                    for x in range(cols_):
                        if tablero[y][x]["mina"]:
                            tablero[y][x]["rev"] = True
                render(tablero, filas, cols_, cur_x, cur_y, dificultad, minas_total, t_ini, "Has pisado una mina", mostrar_minas=True)
                time.sleep(1.5)
                tiempo = int(time.time() - t_ini) if t_ini else 0
                return False, 0, tiempo
            if todos_revelados(tablero, filas, cols_):
                gano = True
                break

    tiempo = int(time.time() - t_ini) if t_ini else 0
    render(tablero, filas, cols_, cur_x, cur_y, dificultad, minas_total, t_ini, "¡VICTORIA!")
    puntos = max(0, 1000 - tiempo) * mult
    return True, puntos, tiempo


def main():
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. Buscaminas necesita un TTY.")
        return
    try:
        # splash pide Enter (linea normal); necesitamos restaurar modo temporalmente
        restaurar_terminal(old)
        splash()
        while True:
            # volver a char-mode para el menu
            old2 = entrar_cbreak()
            dif = menu_dificultad()
            if dif is None:
                break
            gano, puntos, tiempo = jugar_partida(dif)
            # pantalla_final usa input(), volver a linea
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            pantalla_final(gano, puntos, tiempo, dif[0])
            # preguntar otra vez
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
