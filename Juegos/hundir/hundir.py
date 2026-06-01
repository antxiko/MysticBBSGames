#!/usr/bin/env python3
"""Hundir la Flota BBS - clon turn-based del clasico en 80x24."""
import os
import random
import sys
import time

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
GRID_N = 10
MAX_TOP = 10
ASCENDING = False  # mas score = mejor

WATER = '.'
SHIP = 'S'

V_UNKNOWN = 0
V_MISS = 1
V_HIT = 2
V_SUNK = 3

FLOTA = [
    ("Portaaviones", 5),
    ("Acorazado",    4),
    ("Crucero",      3),
    ("Submarino",    3),
    ("Destructor",   2),
]
TOTAL_BARCO_CELDAS = sum(l for _, l in FLOTA)

# Layout
LEFT_LABEL_COL = 3
LEFT_GRID_COL = 6
LEFT_TITLE_COL = 8
RIGHT_LABEL_COL = 43
RIGHT_GRID_COL = 46
RIGHT_TITLE_COL = 48
COLHEAD_ROW = 4
GRID_ROW0 = 5  # 1-indexed
STATUS_ROW = 17
INFO_ROW = 19


COLORES = {
    "rojo":     "\x1b[31m",
    "verde":    "\x1b[32m",
    "amar":     "\x1b[33m",
    "azul":     "\x1b[34m",
    "magenta":  "\x1b[35m",
    "cyan":     "\x1b[36m",
    "blanco":   "\x1b[37m",
    "rojoB":    "\x1b[1;31m",
    "verdeB":   "\x1b[1;32m",
    "amarB":    "\x1b[1;33m",
    "azulB":    "\x1b[1;34m",
    "magentaB": "\x1b[1;35m",
    "cyanB":    "\x1b[1;36m",
    "blancoB":  "\x1b[1;37m",
    "bold":     "\x1b[1m",
    "dim":      "\x1b[2m",
    "reverso":  "\x1b[7m",
}
RESET = "\x1b[0m"


def c(txt, *estilos):
    if not estilos:
        return str(txt)
    pre = "".join(COLORES[e] for e in estilos if e in COLORES)
    return f"{pre}{txt}{RESET}" if pre else str(txt)


def at(row, col):
    return f"\x1b[{row};{col}H"


def cls():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


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


def leer_tecla():
    """Bloqueante. Decodifica flechas en \\x1b[A/B/C/D."""
    if not TERMIOS_OK:
        return None
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        if not ready:
            return ch
        nxt = sys.stdin.read(1)
        if nxt != "[":
            return ch
        ready2, _, _ = select.select([sys.stdin], [], [], 0.05)
        if not ready2:
            return ch
        arr = sys.stdin.read(1)
        return f"\x1b[{arr}"
    return ch


# ---------- estado de juego ----------

def grid_nuevo():
    return [[WATER] * GRID_N for _ in range(GRID_N)]


def view_nueva():
    return [[V_UNKNOWN] * GRID_N for _ in range(GRID_N)]


def vecinos_8(r, col):
    return [(r + dr, col + dc)
            for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (dr, dc) != (0, 0)]


def vecinos_4(r, col):
    return [(r - 1, col), (r + 1, col), (r, col - 1), (r, col + 1)]


def colocar_flota():
    """Coloca la flota random, sin solapar y sin tocarse (8-vecinos).
    Devuelve (grid, ships). Reintenta el layout entero si se atasca."""
    for _ in range(50):
        grid = grid_nuevo()
        ships = []
        ok_layout = True
        for nombre, length in FLOTA:
            placed = False
            for _ in range(2000):
                horizontal = random.choice([True, False])
                if horizontal:
                    r = random.randint(0, GRID_N - 1)
                    col = random.randint(0, GRID_N - length)
                    cells = [(r, col + i) for i in range(length)]
                else:
                    r = random.randint(0, GRID_N - length)
                    col = random.randint(0, GRID_N - 1)
                    cells = [(r + i, col) for i in range(length)]
                if any(grid[rr][cc] != WATER for rr, cc in cells):
                    continue
                # no-touching
                touches = False
                for rr, cc in cells:
                    for nr, nc in vecinos_8(rr, cc):
                        if 0 <= nr < GRID_N and 0 <= nc < GRID_N:
                            if grid[nr][nc] == SHIP:
                                touches = True
                                break
                    if touches:
                        break
                if touches:
                    continue
                for rr, cc in cells:
                    grid[rr][cc] = SHIP
                ships.append({
                    "nombre": nombre,
                    "largo": length,
                    "celdas": cells,
                    "hits": set(),
                    "hundido": False,
                })
                placed = True
                break
            if not placed:
                ok_layout = False
                break
        if ok_layout:
            return grid, ships
    raise RuntimeError("No se pudo colocar la flota")


def disparar(grid, ships, view, r, col):
    """Aplica un disparo en (r,col). Devuelve ('miss'|'hit'|'sunk', ship_or_none)."""
    if grid[r][col] == SHIP:
        for s in ships:
            if (r, col) in s["celdas"]:
                s["hits"].add((r, col))
                if len(s["hits"]) == s["largo"]:
                    s["hundido"] = True
                    for cr, cc in s["celdas"]:
                        view[cr][cc] = V_SUNK
                    return ("sunk", s)
                view[r][col] = V_HIT
                return ("hit", s)
    view[r][col] = V_MISS
    return ("miss", None)


# ---------- IA ----------

def ia_nueva():
    return {
        "shots": set(),
        "pending": [],     # cola de targets prometedores
        "in_progress": [], # impactos del barco actual sin hundir
    }


def ia_elige(ia):
    """Devuelve (r, col) para disparar. Saca de pending si hay; si no, random."""
    while ia["pending"]:
        r, col = ia["pending"].pop(0)
        if (r, col) not in ia["shots"] and 0 <= r < GRID_N and 0 <= col < GRID_N:
            ia["shots"].add((r, col))
            return r, col
    # random
    while True:
        r = random.randint(0, GRID_N - 1)
        col = random.randint(0, GRID_N - 1)
        if (r, col) not in ia["shots"]:
            ia["shots"].add((r, col))
            return r, col


def ia_resultado(ia, r, col, resultado):
    """resultado: 'miss', 'hit', 'sunk'. Actualiza estado interno."""
    if resultado == "hit":
        ia["in_progress"].append((r, col))
        # Si tenemos 2+ hits alineados, priorizar los extremos en esa direccion
        if len(ia["in_progress"]) >= 2:
            rs = [h[0] for h in ia["in_progress"]]
            cs = [h[1] for h in ia["in_progress"]]
            if all(rr == rs[0] for rr in rs):
                # horizontal: extender a izq y dcha
                cmin, cmax = min(cs), max(cs)
                candidatos = [(rs[0], cmin - 1), (rs[0], cmax + 1)]
            elif all(cc == cs[0] for cc in cs):
                cmin, cmax = min(rs), max(rs)
                candidatos = [(cmin - 1, cs[0]), (cmax + 1, cs[0])]
            else:
                candidatos = vecinos_4(r, col)
        else:
            candidatos = vecinos_4(r, col)
        # encolar al principio (prioridad)
        nuevos = []
        for nr, nc in candidatos:
            if 0 <= nr < GRID_N and 0 <= nc < GRID_N and (nr, nc) not in ia["shots"]:
                nuevos.append((nr, nc))
        random.shuffle(nuevos)
        ia["pending"] = nuevos + ia["pending"]
    elif resultado == "sunk":
        ia["in_progress"] = []
        ia["pending"] = []


# ---------- render ----------

def char_para(view_state, hay_barco=False, lado="propio"):
    """Devuelve (ch, color) para una celda."""
    if lado == "propio":
        if view_state == V_UNKNOWN:
            return ("#", "blancoB") if hay_barco else (".", "azul")
        if view_state == V_MISS:
            return ("o", "cyan")
        if view_state == V_HIT:
            return ("X", "rojoB")
        if view_state == V_SUNK:
            return ("#", "rojo")
    else:
        if view_state == V_UNKNOWN:
            return (".", "azul")
        if view_state == V_MISS:
            return ("o", "cyan")
        if view_state == V_HIT:
            return ("X", "rojoB")
        if view_state == V_SUNK:
            return ("#", "rojo")
    return (" ", "blanco")


def pintar_marco():
    """Marco fijo: HUD top, titulos, cabeceras, separadores."""
    cls()
    sys.stdout.write(at(1, 1) + c("HUNDIR LA FLOTA", "amarB", "bold"))
    sys.stdout.write(at(2, 1) + c("─" * COLS, "dim"))
    sys.stdout.write(at(3, LEFT_TITLE_COL) + c("TU FLOTA", "verdeB", "bold"))
    sys.stdout.write(at(3, RIGHT_TITLE_COL) + c("FLOTA ENEMIGA", "rojoB", "bold"))
    head = " ".join(chr(ord('A') + i) for i in range(GRID_N))
    sys.stdout.write(at(COLHEAD_ROW, LEFT_GRID_COL) + c(head, "dim"))
    sys.stdout.write(at(COLHEAD_ROW, RIGHT_GRID_COL) + c(head, "dim"))
    for r in range(GRID_N):
        ty = GRID_ROW0 + r
        lab = f"{r + 1:>2}"
        sys.stdout.write(at(ty, LEFT_LABEL_COL) + c(lab, "dim"))
        sys.stdout.write(at(ty, RIGHT_LABEL_COL) + c(lab, "dim"))
    sys.stdout.write(at(23, 1) + c("─" * COLS, "dim"))


def pintar_hud(score, tiros, turno):
    sys.stdout.write(at(1, 30) + c(f"SCORE {score:>5}", "blancoB", "bold"))
    sys.stdout.write(at(1, 50) + c(f"TIROS {tiros:>3}", "cyanB"))
    txt = "TU TURNO " if turno == "yo" else "TURNO IA"
    color = "verdeB" if turno == "yo" else "rojoB"
    sys.stdout.write(at(1, 65) + c(txt, color, "bold"))


def pintar_grids(player_grid, vista_propia, vista_enemigo, cursor, mostrar_enemigo=False, enemy_grid=None):
    """Repinta ambos grids.

    - LEFT (TU FLOTA): tus barcos + vista_propia (impactos de la IA sobre ti).
    - RIGHT (FLOTA ENEMIGA): vista_enemigo (donde has disparado tu).
    """
    for r in range(GRID_N):
        ty = GRID_ROW0 + r
        for col in range(GRID_N):
            v_p = vista_propia[r][col]
            hay = (player_grid[r][col] == SHIP)
            ch, color = char_para(v_p, hay_barco=hay, lado="propio")
            sys.stdout.write(at(ty, LEFT_GRID_COL + col * 2) + c(ch, color))
            v_e = vista_enemigo[r][col]
            ch2, color2 = char_para(v_e, lado="enemigo")
            if mostrar_enemigo and v_e == V_UNKNOWN and enemy_grid and enemy_grid[r][col] == SHIP:
                # al final de partida revelamos los barcos enemigos no descubiertos
                ch2, color2 = "#", "blancoB"
            if cursor and cursor == (r, col):
                sys.stdout.write(at(ty, RIGHT_GRID_COL + col * 2) + c(ch2, color2, "reverso"))
            else:
                sys.stdout.write(at(ty, RIGHT_GRID_COL + col * 2) + c(ch2, color2))


def pintar_info(player_ships, enemy_ships):
    enemy_alive = sum(1 for s in enemy_ships if not s["hundido"])
    player_alive = sum(1 for s in player_ships if not s["hundido"])
    sys.stdout.write(at(INFO_ROW, 2)
        + c(f"Enemigos hundidos: {len(enemy_ships) - enemy_alive}/{len(enemy_ships)}".ljust(36), "rojoB"))
    sys.stdout.write(at(INFO_ROW, 42)
        + c(f"Tus barcos hundidos: {len(player_ships) - player_alive}/{len(player_ships)}", "verdeB"))


def pintar_status(mensaje, color="amarB"):
    sys.stdout.write(at(STATUS_ROW, 2) + c(mensaje.ljust(COLS - 4), color, "bold"))


def pintar_footer(texto):
    sys.stdout.write(at(24, 1) + c(texto.center(COLS - 1), "dim"))


def coord_legible(r, col):
    return f"{chr(ord('A') + col)}{r + 1}"


# ---------- pantalla de colocacion ----------

def pantalla_colocacion():
    """Genera flota, deja al jugador re-tirar con R o aceptar con ENTER."""
    while True:
        grid, ships = colocar_flota()
        cls()
        sys.stdout.write(show_cursor(False))
        sys.stdout.write(at(1, 1) + c("HUNDIR LA FLOTA - colocacion", "amarB", "bold"))
        sys.stdout.write(at(2, 1) + c("─" * COLS, "dim"))
        sys.stdout.write(at(3, 4) + c("Esta sera tu flota:", "blancoB"))
        head = " ".join(chr(ord('A') + i) for i in range(GRID_N))
        sys.stdout.write(at(COLHEAD_ROW, LEFT_GRID_COL) + c(head, "dim"))
        for r in range(GRID_N):
            ty = GRID_ROW0 + r
            sys.stdout.write(at(ty, LEFT_LABEL_COL) + c(f"{r + 1:>2}", "dim"))
            for col in range(GRID_N):
                hay = (grid[r][col] == SHIP)
                ch, color = ("#", "blancoB") if hay else (".", "azul")
                sys.stdout.write(at(ty, LEFT_GRID_COL + col * 2) + c(ch, color))
        # lista barcos
        for i, s in enumerate(ships):
            sys.stdout.write(at(GRID_ROW0 + i, 35)
                             + c(f"{s['nombre']:<14} {'#' * s['largo']}", "blanco"))
        sys.stdout.write(at(23, 1) + c("─" * COLS, "dim"))
        sys.stdout.write(at(24, 1)
                         + c(" [R] otra colocacion    [ENTER] confirmar    [Q] salir ".center(COLS - 1), "amarB"))
        sys.stdout.flush()
        while True:
            t = leer_tecla()
            if t in ("q", "Q", "\x03"):
                return None
            if t in ("r", "R"):
                break
            if t in ("\r", "\n"):
                return grid, ships


# ---------- loop principal ----------

def jugar():
    res = pantalla_colocacion()
    if res is None:
        return None
    player_grid, player_ships = res
    enemy_grid, enemy_ships = colocar_flota()
    vista_enemigo = view_nueva()  # lo que yo se de la flota enemiga (grid DERECHO)
    vista_propia = view_nueva()   # impactos de la IA sobre mi flota (grid IZQUIERDO)
    ia = ia_nueva()

    score = 0
    tiros = 0
    cursor = [GRID_N // 2, GRID_N // 2]
    mensaje = "¡Empieza la partida! Mueve el cursor y dispara."
    turno = "yo"
    ganador = None

    pintar_marco()
    pintar_hud(score, tiros, turno)
    pintar_grids(player_grid, vista_propia, vista_enemigo, tuple(cursor))
    pintar_info(player_ships, enemy_ships)
    pintar_status(mensaje)
    pintar_footer(" FLECHAS/WASD mover    ESPACIO/ENTER disparar    Q salir ")
    sys.stdout.flush()

    while ganador is None:
        if turno == "yo":
            t = leer_tecla()
            if t in ("q", "Q", "\x03"):
                return score, tiros, False, player_ships, enemy_ships
            if t in ("w", "W", "\x1b[A"):
                cursor[0] = (cursor[0] - 1) % GRID_N
            elif t in ("s", "S", "\x1b[B"):
                cursor[0] = (cursor[0] + 1) % GRID_N
            elif t in ("a", "A", "\x1b[D"):
                cursor[1] = (cursor[1] - 1) % GRID_N
            elif t in ("d", "D", "\x1b[C"):
                cursor[1] = (cursor[1] + 1) % GRID_N
            elif t in (" ", "\r", "\n"):
                r, col = cursor
                if vista_enemigo[r][col] != V_UNKNOWN:
                    mensaje = f"Ya disparaste a {coord_legible(r, col)}. Elige otra."
                else:
                    tiros += 1
                    resultado, ship = disparar(enemy_grid, enemy_ships, vista_enemigo, r, col)
                    if resultado == "miss":
                        mensaje = f"Disparo en {coord_legible(r, col)}: AGUA. Turno enemigo."
                        turno = "ia"
                    elif resultado == "hit":
                        score += 50
                        mensaje = f"¡TOCADO en {coord_legible(r, col)}! +50. Sigues tu."
                    elif resultado == "sunk":
                        score += 50 + 200
                        mensaje = f"¡HUNDIDO {ship['nombre']}! +250. Sigues tu."
                    # comprobar victoria
                    if all(s["hundido"] for s in enemy_ships):
                        score += 500
                        bonus = max(0, 80 - tiros) * 10
                        score += bonus
                        ganador = "yo"
                        mensaje = f"¡VICTORIA! Bonus eficiencia +{bonus}."
            # repintar
            pintar_hud(score, tiros, turno)
            pintar_grids(player_grid, vista_propia, vista_enemigo, tuple(cursor))
            pintar_info(player_ships, enemy_ships)
            pintar_status(mensaje)
            sys.stdout.flush()
        else:
            # Turno IA con pequena pausa para que se vea
            pintar_hud(score, tiros, turno)
            pintar_grids(player_grid, vista_propia, vista_enemigo, tuple(cursor))
            pintar_status("La IA esta apuntando...", "rojoB")
            sys.stdout.flush()
            time.sleep(0.7)
            r, col = ia_elige(ia)
            resultado, ship = disparar(player_grid, player_ships, vista_propia, r, col)
            ia_resultado(ia, r, col, resultado)
            if resultado == "miss":
                mensaje = f"IA dispara a {coord_legible(r, col)}: AGUA. Tu turno."
                turno = "yo"
            elif resultado == "hit":
                mensaje = f"IA acierta en {coord_legible(r, col)}. ¡Le toca otra vez!"
            elif resultado == "sunk":
                mensaje = f"IA HUNDE tu {ship['nombre']}. ¡Sigue tirando!"
            if all(s["hundido"] for s in player_ships):
                ganador = "ia"
                mensaje = "Te han hundido toda la flota. Game over."
            pintar_hud(score, tiros, turno)
            pintar_grids(player_grid, vista_propia, vista_enemigo, tuple(cursor))
            pintar_info(player_ships, enemy_ships)
            pintar_status(mensaje, "rojoB" if turno == "ia" else "amarB")
            sys.stdout.flush()
            if turno == "ia" and ganador is None:
                time.sleep(0.5)

    # Pantalla de fin de partida (revelando flota enemiga restante)
    pintar_marco()
    pintar_hud(score, tiros, "yo" if ganador == "yo" else "ia")
    pintar_grids(player_grid, vista_propia, vista_enemigo, None,
                 mostrar_enemigo=True, enemy_grid=enemy_grid)
    pintar_info(player_ships, enemy_ships)
    pintar_status(mensaje, "verdeB" if ganador == "yo" else "rojoB")
    pintar_footer(" Pulsa ENTER para continuar... ")
    sys.stdout.flush()
    while True:
        t = leer_tecla()
        if t in ("\r", "\n", "q", "Q", "\x03", " "):
            break
    return score, tiros, ganador == "yo", player_ships, enemy_ships


# ---------- splash + manual + scores ----------

LOGO = [
    "██╗  ██╗██╗   ██╗███╗   ██╗██████╗ ██╗██████╗ ",
    "██║  ██║██║   ██║████╗  ██║██╔══██╗██║██╔══██╗",
    "███████║██║   ██║██╔██╗ ██║██║  ██║██║██████╔╝",
    "██╔══██║██║   ██║██║╚██╗██║██║  ██║██║██╔══██╗",
    "██║  ██║╚██████╔╝██║ ╚████║██████╔╝██║██║  ██║",
    "╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚═╝╚═╝  ╚═╝",
]


MANUAL_LINEAS = [
    ("PREMISA", "cyanB", "bold"),
    "  Hundir la Flota - turn-based contra la IA.",
    "  Coloca tu flota, alterna disparos con el enemigo.",
    "  Gana quien hunda primero los 5 barcos del rival.",
    "",
    ("CONTROLES", "cyanB", "bold"),
    "  WASD / flechas   mover cursor por el grid enemigo",
    "  ESPACIO / ENTER  disparar",
    "  R                en colocacion: re-tirar tu flota",
    "  Q                salir",
    "",
    ("MECANICA", "cyanB", "bold"),
    "  Si aciertas, sigues tirando. Si fallas, tira la IA.",
    "  Misma regla para la IA: si te da, dispara otra vez.",
    "  Los barcos no se tocan (siempre hay 1 casilla de agua entre ellos).",
    "",
    ("FLOTA", "cyanB", "bold"),
    "  Portaaviones (5)   Acorazado (4)   Crucero (3)",
    "  Submarino (3)      Destructor (2)",
    "",
    ("PUNTUACION", "cyanB", "bold"),
    "  +50  por cada impacto",
    "  +200 por cada barco hundido",
    "  +500 por ganar la partida",
    "  bonus eficiencia (solo si ganas): max(0, 80-tiros) x 10",
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - HUNDIR LA FLOTA".ljust(70), "cyanB", "bold"))
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
        input(c("  Pulsa Enter para volver...", "amarB"))
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
    print(_caja("Turn-based contra la IA. Hunde la flota primero.", ancho, "cyanB"))
    print(_caja("", ancho, "blanco"))
    print(_caja("WASD/flechas mover  ESPACIO disparar  Q salir", ancho, "blanco"))
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


def pantalla_final(score, tiros, gano):
    ancho = 56
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    lado = c("║", "amarB")

    def dibujar_resumen():
        cls()
        print()
        print(margen + c("╔" + linea + "╗", "amarB"))
        titulo = " ¡VICTORIA! " if gano else " GAME OVER "
        col = "verdeB" if gano else "rojoB"
        print(margen + lado + c(titulo.center(ancho), col, "bold") + lado)
        print(margen + c("╠" + linea + "╣", "amarB"))
        print(margen + lado
              + f"  Score        : {c(str(score).rjust(15) + '  ', 'verdeB', 'bold')}".ljust(ancho + 15)
              + lado)
        print(margen + lado
              + f"  Tiros        : {c(str(tiros).rjust(15) + '  ', 'cyanB', 'bold')}".ljust(ancho + 15)
              + lado)
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
        _handle_w = max(14, max((len(e.display_handle if modo == "global" else e.handle) for e in scores_e), default=14))
        for i, e in enumerate(scores_e, 1):
            etiqueta = e.display_handle if modo == "global" else e.handle
            color = "amarB" if e.score == score else "blanco"
            print(margen
                  + f"  {i:>2}. {c(etiqueta.ljust(_handle_w), color, 'bold')} "
                  + f"{c(str(e.score).rjust(8), color)}  {c(e.date, 'dim')}")
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
        print("Hundir la Flota necesita un TTY con termios.")
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
            resultado = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            if resultado is None:
                break
            score, tiros, gano, _, _ = resultado
            pantalla_final(score, tiros, gano)
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
