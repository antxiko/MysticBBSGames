#!/usr/bin/env python3
"""BBSATRO - deckbuilder de poker estilo Balatro.

Incluye 20 jokers, tienda entre rondas, upgrade de manos automatico y
boss blinds con efectos especiales en la ronda final de cada ante.
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

# Bonus por nivel de cada tipo de mano: (chips_por_nivel, mult_por_nivel)
NIVEL_HAND_BONUS = {
    "carta_alta":     (10, 1),
    "pareja":         (15, 1),
    "doble_pareja":   (20, 1),
    "trio":           (20, 2),
    "escalera":       (30, 3),
    "color":          (15, 2),
    "full":           (25, 2),
    "poker":          (30, 3),
    "escalera_color": (40, 4),
    "escalera_real":  (40, 4),
}

# Jokers: id -> (nombre, descripcion corta, precio, clave de efecto)
JOKERS = {
    "joker":        {"nombre": "Joker",        "desc": "+4 Mult",                         "precio": 2, "efecto": "mult_plano_4"},
    "jolly":        {"nombre": "Jolly",        "desc": "+8 Mult si pareja",               "precio": 3, "efecto": "mult_si_pareja_8"},
    "zany":         {"nombre": "Zany",         "desc": "+12 Mult si trio",                "precio": 4, "efecto": "mult_si_trio_12"},
    "mad":          {"nombre": "Mad",          "desc": "+10 Mult si doble pareja",        "precio": 4, "efecto": "mult_si_doble_10"},
    "crazy":        {"nombre": "Crazy",        "desc": "+12 Mult si escalera",            "precio": 4, "efecto": "mult_si_escalera_12"},
    "droll":        {"nombre": "Droll",        "desc": "+10 Mult si color",               "precio": 4, "efecto": "mult_si_color_10"},
    "greedy":       {"nombre": "Greedy",       "desc": "+3 Mult por diamante",            "precio": 5, "efecto": "mult_por_diamante_3"},
    "lusty":        {"nombre": "Lusty",        "desc": "+3 Mult por corazon",             "precio": 5, "efecto": "mult_por_corazon_3"},
    "wrathful":     {"nombre": "Wrathful",     "desc": "+3 Mult por pica",                "precio": 5, "efecto": "mult_por_pica_3"},
    "gluttonous":   {"nombre": "Gluttonous",   "desc": "+3 Mult por trebol",              "precio": 5, "efecto": "mult_por_trebol_3"},
    "sly":          {"nombre": "Sly",          "desc": "+50 Chips si pareja",             "precio": 3, "efecto": "chips_si_pareja_50"},
    "wily":         {"nombre": "Wily",         "desc": "+100 Chips si trio",              "precio": 4, "efecto": "chips_si_trio_100"},
    "clever":       {"nombre": "Clever",       "desc": "+80 Chips si doble pareja",       "precio": 4, "efecto": "chips_si_doble_80"},
    "devious":      {"nombre": "Devious",      "desc": "+100 Chips si escalera",          "precio": 4, "efecto": "chips_si_escalera_100"},
    "crafty":       {"nombre": "Crafty",       "desc": "+80 Chips si color",              "precio": 4, "efecto": "chips_si_color_80"},
    "banner":       {"nombre": "Banner",       "desc": "+30 Chips por descarte restante", "precio": 5, "efecto": "chips_por_descarte_30"},
    "abstract":     {"nombre": "Abstract",     "desc": "+3 Mult por joker que tengas",    "precio": 4, "efecto": "mult_por_joker_3"},
    "misprint":     {"nombre": "Misprint",     "desc": "+0-23 Mult aleatorio",            "precio": 3, "efecto": "mult_aleatorio_23"},
    "raised_fist":  {"nombre": "Raised Fist",  "desc": "+2*valor de tu carta mas baja",   "precio": 5, "efecto": "mult_carta_baja_2"},
    "even_steven":  {"nombre": "Even Steven",  "desc": "+4 Mult por carta par jugada",    "precio": 4, "efecto": "mult_par_4"},
}

MAX_JOKERS = 5

# Boss blinds: efectos especiales que solo aparecen en ronda 2 (Boss)
BOSS_BLINDS = {
    "the_hook":   {"nombre": "The Hook",   "desc": "Tras cada mano, descarta 2 cartas al azar"},
    "the_ox":     {"nombre": "The Ox",     "desc": "Cada mano jugada te cuesta $3"},
    "the_club":   {"nombre": "The Club",   "desc": "Los treboles no puntuan"},
    "the_plant":  {"nombre": "The Plant",  "desc": "Cartas de rango <8 no puntuan"},
    "the_needle": {"nombre": "The Needle", "desc": "Solo 1 mano para jugar"},
}

# Economia
ORO_INICIAL = 4
ORO_BASE_POR_RONDA = 3
ORO_INTERES_CAP = 5  # max $5 de interes
RERROLL_PRECIO_INICIAL = 1
TIENDA_JOKERS_POR_TIRADA = 2


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
    """Puntuacion base, sin contexto (usado en preview cuando no hay partida)."""
    tipo = evaluar_mano(cartas)
    base_chips, mult = PUNTOS_MANO[tipo]
    suma = sum(VALOR_CARTA[r] for r, _ in cartas)
    chips = base_chips + suma
    return tipo, chips, mult, chips * mult


# tipos de mano que contienen cada sub-tipo
TIPOS_CON_PAREJA = {"pareja", "doble_pareja", "trio", "full", "poker"}
TIPOS_CON_TRIO = {"trio", "full", "poker"}
TIPOS_CON_DOBLE = {"doble_pareja", "full"}
TIPOS_CON_ESCALERA = {"escalera", "escalera_color", "escalera_real"}
TIPOS_CON_COLOR = {"color", "escalera_color", "escalera_real"}


def aplicar_jokers(partida, ronda_st, sel_cartas, tipo, chips, mult):
    for j in partida["jokers"]:
        ef = j["efecto"]
        if ef == "mult_plano_4":
            mult += 4
        elif ef == "mult_si_pareja_8" and tipo in TIPOS_CON_PAREJA:
            mult += 8
        elif ef == "mult_si_trio_12" and tipo in TIPOS_CON_TRIO:
            mult += 12
        elif ef == "mult_si_doble_10" and tipo in TIPOS_CON_DOBLE:
            mult += 10
        elif ef == "mult_si_escalera_12" and tipo in TIPOS_CON_ESCALERA:
            mult += 12
        elif ef == "mult_si_color_10" and tipo in TIPOS_CON_COLOR:
            mult += 10
        elif ef == "mult_por_diamante_3":
            for r, p in sel_cartas:
                if p == "D":
                    mult += 3
        elif ef == "mult_por_corazon_3":
            for r, p in sel_cartas:
                if p == "H":
                    mult += 3
        elif ef == "mult_por_pica_3":
            for r, p in sel_cartas:
                if p == "S":
                    mult += 3
        elif ef == "mult_por_trebol_3":
            for r, p in sel_cartas:
                if p == "C":
                    mult += 3
        elif ef == "chips_si_pareja_50" and tipo in TIPOS_CON_PAREJA:
            chips += 50
        elif ef == "chips_si_trio_100" and tipo in TIPOS_CON_TRIO:
            chips += 100
        elif ef == "chips_si_doble_80" and tipo in TIPOS_CON_DOBLE:
            chips += 80
        elif ef == "chips_si_escalera_100" and tipo in TIPOS_CON_ESCALERA:
            chips += 100
        elif ef == "chips_si_color_80" and tipo in TIPOS_CON_COLOR:
            chips += 80
        elif ef == "chips_por_descarte_30":
            chips += 30 * ronda_st["descartes_restantes"]
        elif ef == "mult_por_joker_3":
            mult += 3 * len(partida["jokers"])
        elif ef == "mult_aleatorio_23":
            mult += random.randint(0, 23)
        elif ef == "mult_carta_baja_2":
            if sel_cartas:
                mn = min(VALOR_CARTA[r] for r, _ in sel_cartas)
                mult += 2 * mn
        elif ef == "mult_par_4":
            for r, _ in sel_cartas:
                if r % 2 == 0 and r <= 10:
                    mult += 4
    return chips, mult


def puntuar_jugada(partida, ronda_st, sel_cartas):
    """Puntuacion completa con niveles de mano, jokers y efectos de boss."""
    tipo = evaluar_mano(sel_cartas)
    base_chips, base_mult = PUNTOS_MANO[tipo]
    nivel = partida["niveles_mano"].get(tipo, 1)
    bc_nivel, bm_nivel = NIVEL_HAND_BONUS[tipo]
    chips = base_chips + bc_nivel * (nivel - 1)
    mult = base_mult + bm_nivel * (nivel - 1)

    boss = ronda_st.get("boss_efecto")
    for r, p in sel_cartas:
        if boss == "the_club" and p == "C":
            continue
        if boss == "the_plant" and r < 8:
            continue
        chips += VALOR_CARTA[r]

    chips, mult = aplicar_jokers(partida, ronda_st, sel_cartas, tipo, chips, mult)
    return tipo, chips, mult, int(chips * mult)


# ---------- estado de la partida ----------

def objetivo_ronda(ante, ronda):
    """ronda: 0=pequena, 1=grande, 2=boss."""
    mult_ronda = [1.0, 1.5, 2.0][ronda]
    return int(300 * (1.6 ** (ante - 1)) * mult_ronda)


NOMBRE_RONDA = ["Pequena", "Grande", "Boss"]


def nueva_partida():
    return {
        "ante": 1,
        "ronda": 0,  # 0=pequena, 1=grande, 2=boss
        "score_total": 0,
        "oro": ORO_INICIAL,
        "jokers": [],   # lista de dicts con 'id', 'nombre', 'desc', 'efecto', 'precio'
        "niveles_mano": {t: 1 for t in PUNTOS_MANO},
        "rerolls_tienda": 0,  # cuentas para escalar el precio del reroll en la tienda actual
    }


def nueva_ronda(partida):
    manos_ini = MANOS_POR_RONDA
    boss_efecto = None
    if partida["ronda"] == 2:
        boss_efecto = random.choice(list(BOSS_BLINDS.keys()))
        if boss_efecto == "the_needle":
            manos_ini = 1
    return {
        "mazo": barajar_mazo(),
        "mano": [],
        "seleccion": set(),
        "manos_restantes": manos_ini,
        "descartes_restantes": DESCARTES_POR_RONDA,
        "score_ronda": 0,
        "objetivo": objetivo_ronda(partida["ante"], partida["ronda"]),
        "msg": "",
        "boss_efecto": boss_efecto,
    }


def calcular_oro_ronda(partida, ronda_st):
    """Devuelve lista de (concepto, cantidad) y total."""
    base = ORO_BASE_POR_RONDA
    bonus_manos = ronda_st["manos_restantes"]
    bonus_descartes = ronda_st["descartes_restantes"]
    interes = min(ORO_INTERES_CAP, partida["oro"] // 5)
    desglose = [
        ("Base por pasar", base),
        ("Manos sin usar", bonus_manos),
        ("Descartes sin usar", bonus_descartes),
        ("Interes (1$ por cada 5$)", interes),
    ]
    return desglose, base + bonus_manos + bonus_descartes + interes


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

    # titulo con boss suffix
    boss = ronda_st.get("boss_efecto")
    suf = f" [{BOSS_BLINDS[boss]['nombre']}]" if boss else ""
    titulo = f" BBSATRO   Ante {partida['ante']}   Ronda: {NOMBRE_RONDA[partida['ronda']]}{suf} "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, ROW_TITLE, 0, "\u2550" * pad_l, "blancoB")
    set_text(frame, ROW_TITLE, pad_l, titulo, "amarB", "bold")
    set_text(frame, ROW_TITLE, pad_l + len(titulo), "\u2550" * (COLS - pad_l - len(titulo)), "blancoB")

    set_text(frame, ROW_SEP1, 0, "\u2500" * COLS, "dim")

    # info row 1: objetivo | score ronda | manos | descartes | oro
    obj = ronda_st["objetivo"]
    score = ronda_st["score_ronda"]
    col_score = "verdeB" if score >= obj else ("amarB" if score > 0 else "blanco")
    x = 1
    set_text(frame, ROW_INFO1, x, "Obj:", "blanco"); x += 5
    set_text(frame, ROW_INFO1, x, str(obj), "rojoB", "bold"); x += len(str(obj)) + 3
    set_text(frame, ROW_INFO1, x, "Score:", "blanco"); x += 7
    set_text(frame, ROW_INFO1, x, str(score), col_score, "bold"); x += len(str(score)) + 3
    set_text(frame, ROW_INFO1, x, f"Manos: {ronda_st['manos_restantes']}/{MANOS_POR_RONDA}", "amarB"); x += 11
    set_text(frame, ROW_INFO1, x, f"Desc: {ronda_st['descartes_restantes']}/{DESCARTES_POR_RONDA}", "cyanB"); x += 10
    set_text(frame, ROW_INFO1, x, f"Oro: ${partida['oro']}", "amarB", "bold")

    # info row 2: jokers | boss desc
    x = 1
    set_text(frame, ROW_INFO2, x, f"Jokers ({len(partida['jokers'])}/{MAX_JOKERS}):", "blanco"); x += 14
    if partida["jokers"]:
        for j in partida["jokers"]:
            etiq = f"[{j['nombre']}]"
            set_text(frame, ROW_INFO2, x, etiq, "magentaB", "bold")
            x += len(etiq) + 1
    else:
        set_text(frame, ROW_INFO2, x, "(ninguno)", "dim"); x += 10
    if boss:
        bdesc = f"  BOSS: {BOSS_BLINDS[boss]['desc']}"
        x_boss = max(x + 1, COLS - len(bdesc) - 1)
        set_text(frame, ROW_INFO2, x_boss, bdesc, "rojoB")

    set_text(frame, ROW_SEP2, 0, "\u2500" * COLS, "dim")

    # cartas
    mano = ronda_st["mano"]
    n = len(mano)
    paso = CARTA_ANCHO + CARTA_GAP
    ancho_cartas = n * paso - CARTA_GAP
    sangria = (COLS - ancho_cartas) // 2
    for i in range(n):
        col = sangria + i * paso
        seleccionada = i in ronda_st["seleccion"]
        _dibujar_carta(frame, ROW_CARTA_Y, col, mano[i], seleccionada)
        set_cell(frame, ROW_CARTAS_IDX, col + 3, str(i + 1), "amarB", "bold")

    set_text(frame, ROW_SEP3, 0, "\u2500" * COLS, "dim")

    # preview
    if ronda_st["seleccion"]:
        sel_cartas = [mano[i] for i in sorted(ronda_st["seleccion"])]
        tipo, chips, mult, total = puntuar_jugada(partida, ronda_st, sel_cartas)
        nivel = partida["niveles_mano"].get(tipo, 1)
        texto_tipo = f" Mano: {NOMBRES_MANO[tipo]}   (nivel {nivel})"
        set_text(frame, ROW_PREVIEW, 0, texto_tipo, "cyanB", "bold")
        texto_puntos = f" Chips: {chips}   Mult: {mult}   = {total}"
        set_text(frame, ROW_PREVIEW2, 0, texto_puntos, "verdeB")
    else:
        set_text(frame, ROW_PREVIEW, 0, " Selecciona 1-5 cartas para ver su valor", "dim")

    set_text(frame, ROW_SEP4, 0, "\u2500" * COLS, "dim")

    if ronda_st["msg"]:
        texto = ronda_st["msg"][:COLS - 2]
        set_text(frame, ROW_MSG, 1, texto, "amarB", "bold")

    set_text(frame, ROW_SEP5, 0, "\u2500" * COLS, "dim")

    ctrl = " 1-8 seleccionar    P jugar    D descartar    Q salir "
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
            return "ganada", ronda_st
        if ronda_st["manos_restantes"] <= 0:
            return "perdida", ronda_st

        tecla = leer_tecla()
        if tecla in ("q", "Q", "\x03"):
            return "salir", ronda_st
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
            # sube nivel de la mano ANTES de puntuar (la jugada actual se beneficia)
            tipo_previo = evaluar_mano(sel_cartas)
            partida["niveles_mano"][tipo_previo] = partida["niveles_mano"].get(tipo_previo, 1) + 1
            tipo, chips, mult, total = puntuar_jugada(partida, ronda_st, sel_cartas)
            ronda_st["score_ronda"] += total
            ronda_st["msg"] = f"Juegas {NOMBRES_MANO[tipo]}: {chips} x {mult} = {total} pts."
            # eliminar cartas jugadas
            ronda_st["mano"] = [cc for i, cc in enumerate(ronda_st["mano"]) if i not in ronda_st["seleccion"]]
            ronda_st["seleccion"] = set()
            ronda_st["manos_restantes"] -= 1
            # boss effects post-mano
            boss = ronda_st.get("boss_efecto")
            if boss == "the_ox":
                partida["oro"] = max(0, partida["oro"] - 3)
                ronda_st["msg"] += "  (The Ox: -$3)"
            robar(ronda_st)
            if boss == "the_hook" and ronda_st["mano"]:
                descartar = min(2, len(ronda_st["mano"]))
                idxs = random.sample(range(len(ronda_st["mano"])), descartar)
                ronda_st["mano"] = [cc for i, cc in enumerate(ronda_st["mano"]) if i not in idxs]
                robar(ronda_st)
                ronda_st["msg"] += f"  (The Hook: -{descartar} cartas al azar)"
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


def render_tienda(partida, tienda_jokers, desglose_oro, mensaje=None):
    frame = frame_nuevo()

    titulo = " TIENDA "
    pad_l = (COLS - len(titulo)) // 2
    set_text(frame, 0, 0, "\u2550" * pad_l, "blancoB")
    set_text(frame, 0, pad_l, titulo, "amarB", "bold")
    set_text(frame, 0, pad_l + len(titulo), "\u2550" * (COLS - pad_l - len(titulo)), "blancoB")

    y = 2
    if desglose_oro:
        set_text(frame, y, 2, "Has ganado esta ronda:", "cyanB", "bold")
        y += 1
        for concepto, cant in desglose_oro:
            set_text(frame, y, 4, concepto + ":", "blanco")
            set_text(frame, y, 30, f"+${cant}", "amarB", "bold")
            y += 1
        total = sum(cc for _, cc in desglose_oro)
        set_text(frame, y, 4, "TOTAL:", "blanco", "bold")
        set_text(frame, y, 30, f"+${total}", "verdeB", "bold")
        y += 2
    set_text(frame, y, 2, f"Oro actual: ${partida['oro']}", "amarB", "bold")
    y += 2

    set_text(frame, y, 2, "JOKERS EN VENTA:", "cyanB", "bold")
    y += 1
    if not tienda_jokers:
        set_text(frame, y, 4, "(sin jokers disponibles)", "dim")
        y += 2
    else:
        for i, j_id in enumerate(tienda_jokers):
            jd = JOKERS[j_id]
            ya_tengo = any(j["id"] == j_id for j in partida["jokers"])
            puedo = (partida["oro"] >= jd["precio"]
                     and len(partida["jokers"]) < MAX_JOKERS
                     and not ya_tengo)
            col = "verdeB" if puedo else "dim"
            set_text(frame, y, 4, f"{i+1}) [{jd['nombre']}]", col, "bold")
            set_text(frame, y, 28, jd["desc"], "blanco")
            set_text(frame, y, 66, f"${jd['precio']}", col, "bold")
            y += 1
        y += 1

    set_text(frame, y, 2, f"Tus jokers ({len(partida['jokers'])}/{MAX_JOKERS}):", "magentaB", "bold")
    y += 1
    if partida["jokers"]:
        for j in partida["jokers"]:
            set_text(frame, y, 4, f"- {j['nombre']}: {j['desc']}", "blanco")
            y += 1
    else:
        set_text(frame, y, 4, "(ninguno)", "dim")
        y += 1

    if mensaje:
        set_text(frame, 21, 2, mensaje, "amarB", "bold")

    precio_rr = RERROLL_PRECIO_INICIAL + partida.get("rerolls_tienda", 0)
    ctrl = f" 1/2 comprar    R reroll (${precio_rr})    ENTER continuar "
    set_text(frame, 22, (COLS - len(ctrl)) // 2, ctrl, "dim")

    flush_frame(frame)


def tienda(partida, desglose_oro):
    def _disponibles():
        return [j_id for j_id in JOKERS if not any(j["id"] == j_id for j in partida["jokers"])]

    partida["rerolls_tienda"] = 0
    disp = _disponibles()
    tienda_jokers = random.sample(disp, min(TIENDA_JOKERS_POR_TIRADA, len(disp)))
    mensaje = None

    while True:
        render_tienda(partida, tienda_jokers, desglose_oro, mensaje)
        mensaje = None
        tecla = leer_tecla()
        if tecla in ("\r", "\n", " ", "q", "Q", "\x1b"):
            return
        if tecla in ("1", "2") and int(tecla) - 1 < len(tienda_jokers):
            idx = int(tecla) - 1
            j_id = tienda_jokers[idx]
            jd = JOKERS[j_id]
            if any(j["id"] == j_id for j in partida["jokers"]):
                mensaje = "Ya tienes ese joker."
                continue
            if len(partida["jokers"]) >= MAX_JOKERS:
                mensaje = "Slots de jokers llenos."
                continue
            if partida["oro"] < jd["precio"]:
                mensaje = "No tienes oro suficiente."
                continue
            partida["oro"] -= jd["precio"]
            partida["jokers"].append({"id": j_id, **jd})
            tienda_jokers.pop(idx)
            mensaje = f"Comprado: {jd['nombre']}"
        elif tecla in ("r", "R"):
            precio_rr = RERROLL_PRECIO_INICIAL + partida["rerolls_tienda"]
            if partida["oro"] < precio_rr:
                mensaje = "No tienes oro para reroll."
                continue
            partida["oro"] -= precio_rr
            partida["rerolls_tienda"] += 1
            disp = _disponibles()
            tienda_jokers = random.sample(disp, min(TIENDA_JOKERS_POR_TIRADA, len(disp)))
            mensaje = "Nuevos jokers."


def jugar():
    partida = nueva_partida()
    cls()
    sys.stdout.write(show_cursor(False))

    while True:
        resultado, ronda_st = jugar_ronda(partida)
        if resultado == "salir":
            return partida, "salir"
        if resultado == "perdida":
            return partida, "perdida"
        # ronda ganada
        partida["score_total"] += ronda_st["score_ronda"]
        desglose, total_oro = calcular_oro_ronda(partida, ronda_st)
        partida["oro"] += total_oro
        # tienda entre rondas
        cls()
        tienda(partida, desglose)
        cls()
        # avanzar ronda/ante
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
