#!/usr/bin/env python3
"""BBSATRO - deckbuilder de poker estilo Balatro (fase 1, sin jokers).

Fichero: balatro.py. El juego se muestra como BBSATRO."""
import os
import random
import sys
from collections import Counter
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
SCORES_FILE = os.path.join(SCRIPT_DIR, "bbsatro_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24

MANOS_POR_RONDA = 4
DESCARTES_POR_RONDA = 3
CARTAS_EN_MANO = 8
CARTAS_MAX_JUGADAS = 5

PALOS = ["H", "D", "S", "C"]  # Hearts, Diamonds, Spades, Clubs
RANGOS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]  # 11=J, 12=Q, 13=K, 14=A
RANGO_CHAR = {2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
              10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}

PALO_SYMBOL = {
    "H": "H",
    "D": "D",
    "S": "S",
    "C": "C",
}

NOMBRES_MANO = {
    "carta_alta":       "Carta alta",
    "pareja":           "Pareja",
    "doble_pareja":     "Doble pareja",
    "trio":             "Trio",
    "escalera":         "Escalera",
    "color":            "Color",
    "full":             "Full",
    "poker":            "Poker",
    "escalera_color":   "Escalera de color",
    "escalera_real":    "Escalera real",
}

PUNTOS_MANO = {
    "carta_alta":     (5, 1),
    "pareja":         (10, 2),
    "doble_pareja":   (20, 2),
    "trio":           (30, 3),
    "escalera":       (30, 4),
    "color":          (35, 4),
    "full":           (40, 4),
    "poker":          (60, 7),
    "escalera_color": (100, 8),
    "escalera_real":  (100, 8),
}

VALOR_CARTA = {2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10,
               11: 10, 12: 10, 13: 10, 14: 11}


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
    return sys.stdin.read(1)


# ---------- baraja ----------

def baraja_completa():
    return [(r, p) for r in RANGOS for p in PALOS]


def barajar_mazo():
    mazo = baraja_completa()
    random.shuffle(mazo)
    return mazo


def color_palo(palo):
    return "rojoB" if palo in ("H", "D") else "blancoB"


def carta_str(carta):
    r, p = carta
    return RANGO_CHAR[r] + p


# ---------- evaluador de poker ----------

def evaluar_mano(cartas):
    """Dadas 1-5 cartas, devuelve el tipo de mano (key de PUNTOS_MANO)."""
    if not cartas:
        return "carta_alta"
    rangos = sorted([r for r, _ in cartas], reverse=True)
    palos = [p for _, p in cartas]
    cuentas = Counter(rangos)
    cuentas_sorted = sorted(cuentas.values(), reverse=True)
    n = len(cartas)

    es_color = n == 5 and len(set(palos)) == 1
    es_escalera = False
    if n == 5:
        unicos = sorted(set(rangos), reverse=True)
        if len(unicos) == 5:
            if unicos[0] - unicos[-1] == 4:
                es_escalera = True
            # escalera baja A-2-3-4-5
            if unicos == [14, 5, 4, 3, 2]:
                es_escalera = True

    if es_escalera and es_color:
        if sorted(rangos) == [10, 11, 12, 13, 14]:
            return "escalera_real"
        return "escalera_color"
    if cuentas_sorted[0] == 4:
        return "poker"
    if cuentas_sorted[0] == 3 and cuentas_sorted[1:2] == [2]:
        return "full"
    if es_color:
        return "color"
    if es_escalera:
        return "escalera"
    if cuentas_sorted[0] == 3:
        return "trio"
    if cuentas_sorted[0] == 2 and cuentas_sorted[1:2] == [2]:
        return "doble_pareja"
    if cuentas_sorted[0] == 2:
        return "pareja"
    return "carta_alta"


def puntuar_mano(cartas):
    tipo = evaluar_mano(cartas)
    base_chips, mult = PUNTOS_MANO[tipo]
    suma = sum(VALOR_CARTA[r] for r, _ in cartas)
    chips = base_chips + suma
    return tipo, chips, mult, chips * mult


# ---------- estado de la partida ----------

def objetivo_ronda(ante, ronda):
    """ronda: 0=pequena, 1=grande, 2=boss."""
    mult_ronda = [1.0, 1.5, 2.0][ronda]
    return int(300 * (1.6 ** (ante - 1)) * mult_ronda)


NOMBRE_RONDA = ["Pequena", "Grande", "Boss"]


def nueva_partida():
    return {
        "ante": 1,
        "ronda": 0,  # 0, 1, 2
        "score_total": 0,
    }


def nueva_ronda(partida):
    return {
        "mazo": barajar_mazo(),
        "mano": [],          # cartas actuales en mano
        "seleccion": set(),  # indices seleccionados
        "manos_restantes": MANOS_POR_RONDA,
        "descartes_restantes": DESCARTES_POR_RONDA,
        "score_ronda": 0,
        "objetivo": objetivo_ronda(partida["ante"], partida["ronda"]),
        "msg": "",
    }


def robar(ronda_st):
    """Rellena la mano hasta CARTAS_EN_MANO desde el mazo."""
    while len(ronda_st["mano"]) < CARTAS_EN_MANO and ronda_st["mazo"]:
        ronda_st["mano"].append(ronda_st["mazo"].pop())


# ---------- render ----------

ROW_TITLE = 0
ROW_SEP1 = 1
ROW_INFO1 = 2
ROW_INFO2 = 3
ROW_SEP2 = 4
# Fila 5 reservada para el "lift" de las cartas seleccionadas
ROW_CARTA_Y = 6          # top de carta NO seleccionada
# Cartas ocupan 5 filas: normal 6-10, seleccionada 5-9
ROW_CARTAS_IDX = 11      # numeros 1-8 bajo las cartas
ROW_SEP3 = 13
ROW_PREVIEW = 14
ROW_PREVIEW2 = 15
ROW_SEP4 = 17
ROW_MSG = 18
ROW_SEP5 = 20
ROW_CTRL = 21

CARTA_ANCHO = 7
CARTA_ALTO = 5
CARTA_GAP = 1


def _dibujar_carta(frame, y_base, x, carta, seleccionada):
    r, p = carta
    rango_s = RANGO_CHAR[r]
    palo_ch = PALO_SYMBOL[p]
    col_palo = color_palo(p)
    col_borde = "amarB" if seleccionada else "blancoB"
    y = y_base - 1 if seleccionada else y_base

    # borde superior
    set_cell(frame, y, x, "\u250C", col_borde)
    for cx in range(x + 1, x + CARTA_ANCHO - 1):
        set_cell(frame, y, cx, "\u2500", col_borde)
    set_cell(frame, y, x + CARTA_ANCHO - 1, "\u2510", col_borde)

    # fila 1: rango arriba-izquierda
    set_cell(frame, y + 1, x, "\u2502", col_borde)
    set_cell(frame, y + 1, x + 1, rango_s, col_palo, "bold")
    for cx in range(x + 2, x + CARTA_ANCHO - 1):
        set_cell(frame, y + 1, cx, " ")
    set_cell(frame, y + 1, x + CARTA_ANCHO - 1, "\u2502", col_borde)

    # fila 2: palo centrado
    set_cell(frame, y + 2, x, "\u2502", col_borde)
    for cx in range(x + 1, x + CARTA_ANCHO - 1):
        set_cell(frame, y + 2, cx, " ")
    set_cell(frame, y + 2, x + CARTA_ANCHO // 2, palo_ch, col_palo, "bold")
    set_cell(frame, y + 2, x + CARTA_ANCHO - 1, "\u2502", col_borde)

    # fila 3: rango abajo-derecha
    set_cell(frame, y + 3, x, "\u2502", col_borde)
    for cx in range(x + 1, x + CARTA_ANCHO - 1):
        set_cell(frame, y + 3, cx, " ")
    set_cell(frame, y + 3, x + CARTA_ANCHO - 2, rango_s, col_palo, "bold")
    set_cell(frame, y + 3, x + CARTA_ANCHO - 1, "\u2502", col_borde)

    # borde inferior
    set_cell(frame, y + 4, x, "\u2514", col_borde)
    for cx in range(x + 1, x + CARTA_ANCHO - 1):
        set_cell(frame, y + 4, cx, "\u2500", col_borde)
    set_cell(frame, y + 4, x + CARTA_ANCHO - 1, "\u2518", col_borde)


def render(partida, ronda_st):
    frame = frame_nuevo()

    # titulo
    titulo = f" BBSATRO   Ante {partida['ante']}   Ronda: {NOMBRE_RONDA[partida['ronda']]} "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, ROW_TITLE, 0, "\u2550" * pad_l, "blancoB")
    set_text(frame, ROW_TITLE, pad_l, titulo, "amarB", "bold")
    set_text(frame, ROW_TITLE, pad_l + len(titulo), "\u2550" * (COLS - pad_l - len(titulo)), "blancoB")

    set_text(frame, ROW_SEP1, 0, "\u2500" * COLS, "dim")

    # info row 1: objetivo, puntuacion ronda
    obj = ronda_st["objetivo"]
    score = ronda_st["score_ronda"]
    col_score = "verdeB" if score >= obj else ("amarB" if score > 0 else "blanco")
    info1 = f" Objetivo: {obj}      Puntos ronda: {score}      Total: {partida['score_total']}"
    set_text(frame, ROW_INFO1, 0, info1, "blanco")
    set_text(frame, ROW_INFO1, 11, str(obj), "rojoB", "bold")
    idx_score = info1.index("Puntos ronda:") + len("Puntos ronda: ")
    set_text(frame, ROW_INFO1, idx_score, str(score), col_score, "bold")
    idx_total = info1.index("Total:") + len("Total: ")
    set_text(frame, ROW_INFO1, idx_total, str(partida["score_total"]), "cyanB")

    # info row 2: manos/descartes
    info2 = f" Manos restantes: {ronda_st['manos_restantes']}/{MANOS_POR_RONDA}      Descartes: {ronda_st['descartes_restantes']}/{DESCARTES_POR_RONDA}"
    set_text(frame, ROW_INFO2, 0, info2, "blanco")
    set_text(frame, ROW_INFO2, 18, str(ronda_st["manos_restantes"]), "amarB", "bold")
    idx_d = info2.index("Descartes:") + len("Descartes: ")
    set_text(frame, ROW_INFO2, idx_d, str(ronda_st["descartes_restantes"]), "cyanB", "bold")

    set_text(frame, ROW_SEP2, 0, "\u2500" * COLS, "dim")

    # cartas: grid 7x5 con bordes CP437. Seleccionadas levantadas 1 fila.
    mano = ronda_st["mano"]
    n = len(mano)
    paso = CARTA_ANCHO + CARTA_GAP
    ancho_cartas = n * paso - CARTA_GAP
    sangria = (COLS - ancho_cartas) // 2

    for i in range(n):
        col = sangria + i * paso
        carta = mano[i]
        seleccionada = i in ronda_st["seleccion"]
        _dibujar_carta(frame, ROW_CARTA_Y, col, carta, seleccionada)
        # indice bajo la carta (alineado al centro, col + 3)
        set_cell(frame, ROW_CARTAS_IDX, col + 3, str(i + 1), "amarB", "bold")

    set_text(frame, ROW_SEP3, 0, "\u2500" * COLS, "dim")

    # preview: si hay seleccion, mostrar tipo de mano y puntos potenciales
    if ronda_st["seleccion"]:
        sel_cartas = [mano[i] for i in sorted(ronda_st["seleccion"])]
        tipo, chips, mult, total = puntuar_mano(sel_cartas)
        texto_tipo = f" Mano: {NOMBRES_MANO[tipo]}"
        set_text(frame, ROW_PREVIEW, 0, texto_tipo, "cyanB", "bold")
        texto_puntos = f" Chips: {chips}   Mult: {mult}   = {total}"
        set_text(frame, ROW_PREVIEW2, 0, texto_puntos, "verdeB")
    else:
        set_text(frame, ROW_PREVIEW, 0, " Selecciona 1-5 cartas para ver su valor", "dim")

    set_text(frame, ROW_SEP4, 0, "\u2500" * COLS, "dim")

    # mensaje
    if ronda_st["msg"]:
        texto = ronda_st["msg"][:COLS - 2]
        set_text(frame, ROW_MSG, 1, texto, "amarB", "bold")

    set_text(frame, ROW_SEP5, 0, "\u2500" * COLS, "dim")

    # controles
    ctrl = " 1-8 seleccionar    P jugar mano    D descartar seleccion    Q salir "
    set_text(frame, ROW_CTRL, (COLS - len(ctrl)) // 2, ctrl, "dim")

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
                    nombre, puntos, ante, fecha = parts
                    try:
                        out.append((nombre, int(puntos), int(ante), fecha))
                    except ValueError:
                        continue
            return sorted(out, key=lambda x: -x[1])[:MAX_TOP]
    except OSError:
        return []


def guardar_score(nombre, puntos, ante):
    scores = cargar_scores()
    scores.append((nombre, puntos, ante, date.today().isoformat()))
    scores = sorted(scores, key=lambda x: -x[1])[:MAX_TOP]
    try:
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            for n, p, a, fe in scores:
                f.write(f"{n};{p};{a};{fe}\n")
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

LOGO_BBSATRO = [
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2557 ",
    "\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u255A\u2550\u2550\u2588\u2588\u2554\u2550\u2550\u255D\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2551  \u2588\u2588\u2551",
    "\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551",
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2551  \u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551  \u2588\u2588\u2551\u255A\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D",
    "\u255A\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u255D  \u255A\u2550\u255D   \u255A\u2550\u255D   \u255A\u2550\u255D  \u255A\u2550\u255D \u255A\u2550\u2550\u2550\u2550\u2550\u255D ",
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
    ancho = 62
    print()
    print(c("\u2554" + "\u2550" * ancho + "\u2557", "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBSATRO:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Deckbuilder de poker estilo Balatro", ancho, "cyanB"))
    print(_caja_linea_splash("Supera el objetivo cada ronda con tus manos.", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("\u255A" + "\u2550" * ancho + "\u255D", "verdeB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_final(partida, ronda_st, victoria):
    sys.stdout.write(show_cursor(True))
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "\u2550" * ancho
    color_caja = "verdeB" if victoria else "rojoB"
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

    print(margen + c("\u2554" + linea + "\u2557", color_caja))
    titulo = "ABANDONASTE" if victoria else "GAME OVER"
    print(fila_centrada(titulo, "bold"))
    print(margen + c("\u2560" + linea + "\u2563", color_caja))
    print(fila_kv("Ante alcanzado : ", str(partida["ante"]).rjust(20), "amarB"))
    print(fila_kv("Ronda          : ", NOMBRE_RONDA[partida["ronda"]].rjust(20), "amarB"))
    print(fila_kv("Puntuacion     : ", str(partida["score_total"]).rjust(20), "verdeB"))
    print(margen + c("\u255A" + linea + "\u255D", color_caja))
    print()

    if es_top(partida["score_total"]):
        print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
        nombre = ""
        while not nombre:
            try:
                raw = input(margen + "  Iniciales (3 letras): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalpha())[:3].ljust(3, "A")
        scores = guardar_score(nombre, partida["score_total"], partida["ante"])
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("\u2500" * ancho, "dim"))
    for i, (n, p, a, fe) in enumerate(scores, 1):
        color = "amarB" if p == partida["score_total"] else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(8), color)}  Ante {a:<2}  {c(fe, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- loop de juego ----------

def jugar_ronda(partida):
    ronda_st = nueva_ronda(partida)
    robar(ronda_st)

    while True:
        render(partida, ronda_st)
        if ronda_st["score_ronda"] >= ronda_st["objetivo"]:
            return "ganada"
        if ronda_st["manos_restantes"] <= 0:
            return "perdida"

        tecla = leer_tecla()
        if tecla in ("q", "Q", "\x03"):
            return "salir"
        if tecla in ("1", "2", "3", "4", "5", "6", "7", "8"):
            idx = int(tecla) - 1
            if 0 <= idx < len(ronda_st["mano"]):
                if idx in ronda_st["seleccion"]:
                    ronda_st["seleccion"].remove(idx)
                else:
                    if len(ronda_st["seleccion"]) >= CARTAS_MAX_JUGADAS:
                        ronda_st["msg"] = "Maximo 5 cartas seleccionadas."
                    else:
                        ronda_st["seleccion"].add(idx)
        elif tecla in ("p", "P"):
            if not ronda_st["seleccion"]:
                ronda_st["msg"] = "Selecciona al menos una carta antes de jugar."
                continue
            sel_sorted = sorted(ronda_st["seleccion"])
            sel_cartas = [ronda_st["mano"][i] for i in sel_sorted]
            tipo, chips, mult, total = puntuar_mano(sel_cartas)
            ronda_st["score_ronda"] += total
            ronda_st["msg"] = f"Juegas {NOMBRES_MANO[tipo]}: {chips} x {mult} = {total} puntos."
            # eliminar cartas jugadas de la mano
            ronda_st["mano"] = [cc for i, cc in enumerate(ronda_st["mano"]) if i not in ronda_st["seleccion"]]
            ronda_st["seleccion"] = set()
            ronda_st["manos_restantes"] -= 1
            robar(ronda_st)
        elif tecla in ("d", "D"):
            if not ronda_st["seleccion"]:
                ronda_st["msg"] = "Selecciona cartas para descartar."
                continue
            if ronda_st["descartes_restantes"] <= 0:
                ronda_st["msg"] = "Ya no tienes descartes."
                continue
            ronda_st["mano"] = [cc for i, cc in enumerate(ronda_st["mano"]) if i not in ronda_st["seleccion"]]
            ronda_st["seleccion"] = set()
            ronda_st["descartes_restantes"] -= 1
            robar(ronda_st)
            ronda_st["msg"] = "Cartas descartadas."


def jugar():
    partida = nueva_partida()
    cls()
    sys.stdout.write(show_cursor(False))

    while True:
        resultado = jugar_ronda(partida)
        if resultado == "salir":
            return partida, "salir"
        if resultado == "perdida":
            return partida, "perdida"
        # ronda ganada
        partida["score_total"] += 1  # placeholder: bonus simbolico por pasar ronda
        partida["ronda"] += 1
        if partida["ronda"] >= 3:
            partida["ronda"] = 0
            partida["ante"] += 1


def main():
    if not TERMIOS_OK:
        print("Este terminal no soporta el modo requerido (termios).")
        return
    old = entrar_cbreak()
    if old is None:
        print("No se pudo entrar en modo cbreak. BBSATRO necesita un TTY.")
        return
    try:
        restaurar_terminal(old)
        splash()
        while True:
            old2 = entrar_cbreak()
            partida, motivo = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            pantalla_final(partida, None, motivo == "salir")
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
