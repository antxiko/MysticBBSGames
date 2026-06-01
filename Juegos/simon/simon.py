#!/usr/bin/env python3
"""Simon BBS - Simon dice. Memoriza y repite la secuencia que se ilumina."""
import math
import os
import random
import sys
import time
from datetime import date

# Cliente compartido para scores: vive en la raiz del repo.
_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)                    # flat: bbs_scores en la misma carpeta
sys.path.insert(0, os.path.dirname(_d))   # subdirs: bbs_scores un nivel arriba
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
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_TOP = 10
ASCENDING = False  # True si menos = mejor

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


def leer_tecla_bloqueante():
    """Lee una tecla bloqueando. Devuelve la tecla en minuscula o "" si EOF."""
    try:
        ch = sys.stdin.read(1)
    except Exception:
        return ""
    if not ch:
        return ""
    if ch == "\x1b":
        try:
            ready, _, _ = select.select([sys.stdin], [], [], 0.01)
            if ready:
                nxt = sys.stdin.read(1)
                if nxt == "[":
                    arr = sys.stdin.read(1)
                    return f"\x1b[{arr}"
        except Exception:
            pass
        return ch
    return ch


def leer_tecla_noblock():
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    return leer_tecla_bloqueante()


# ---------- cuadrantes ----------
# 4 cuadrantes 2x2: indice 0..3 = TL, TR, BL, BR.
# Mapeo de teclas tipo QWAS sobre el teclado fisico para que la posicion sea intuitiva.

CUADRANTES = [
    {
        "nombre": "ROJO",   "tecla": "Q",
        "row": 3, "col": 1, "h": 8, "w": 38,
        "color": "rojo", "colorB": "rojoB",
    },
    {
        "nombre": "VERDE",  "tecla": "W",
        "row": 3, "col": 41, "h": 8, "w": 38,
        "color": "verde", "colorB": "verdeB",
    },
    {
        "nombre": "AZUL",   "tecla": "A",
        "row": 12, "col": 1, "h": 8, "w": 38,
        "color": "azul", "colorB": "azulB",
    },
    {
        "nombre": "AMARILLO", "tecla": "S",
        "row": 12, "col": 41, "h": 8, "w": 38,
        "color": "amar", "colorB": "amarB",
    },
]

TECLA_A_CUADRANTE = {
    "q": 0, "Q": 0,
    "w": 1, "W": 1,
    "a": 2, "A": 2,
    "s": 3, "S": 3,
}


def pintar_cuadrante(frame, idx, iluminado):
    """Pinta el cuadrante idx; iluminado True = relleno brillante."""
    q = CUADRANTES[idx]
    color = q["colorB"] if iluminado else q["color"]
    fill_char = "█" if iluminado else "░"
    r0, c0, h, w = q["row"], q["col"], q["h"], q["w"]
    # bordes en CP437 doble
    for r in range(r0, r0 + h):
        for c_ in range(c0, c0 + w):
            if r == r0:
                if c_ == c0:
                    set_cell(frame, r, c_, "╔", color)
                elif c_ == c0 + w - 1:
                    set_cell(frame, r, c_, "╗", color)
                else:
                    set_cell(frame, r, c_, "═", color)
            elif r == r0 + h - 1:
                if c_ == c0:
                    set_cell(frame, r, c_, "╚", color)
                elif c_ == c0 + w - 1:
                    set_cell(frame, r, c_, "╝", color)
                else:
                    set_cell(frame, r, c_, "═", color)
            elif c_ == c0 or c_ == c0 + w - 1:
                set_cell(frame, r, c_, "║", color)
            else:
                set_cell(frame, r, c_, fill_char, color)
    # etiqueta centrada
    etiqueta = f" {q['nombre']} [{q['tecla']}] "
    er = r0 + h // 2
    ec = c0 + (w - len(etiqueta)) // 2
    estilo = (color, "bold") if iluminado else (color,)
    # fondo: si iluminado usamos blanco brillante sobre el color base
    color_txt = "blancoB" if iluminado else q["colorB"]
    set_text(frame, er, ec, etiqueta, color_txt, "bold")


def pintar_cabecera(frame, nivel, mejor):
    """Cabecera con nivel actual y mejor puntuacion."""
    titulo = " SIMON BBS - repite la secuencia "
    set_text(frame, 1, (COLS - len(titulo)) // 2, titulo, "magentaB", "bold")
    set_text(frame, 1, 2, f"NIVEL {nivel:>3}", "amarB", "bold")
    set_text(frame, 1, COLS - 13, f"MEJOR {mejor:>3}", "cyanB", "bold")


def pintar_pie(frame, msg, msg_color="blanco"):
    set_text(frame, 21, (COLS - len(msg)) // 2, msg, msg_color, "bold")


def render_estado(iluminado, nivel, mejor, msg, msg_color="blanco"):
    """Renderiza un frame con un cuadrante (o ninguno) iluminado."""
    frame = frame_nuevo()
    pintar_cabecera(frame, nivel, mejor)
    for i in range(4):
        pintar_cuadrante(frame, i, iluminado == i)
    pintar_pie(frame, msg, msg_color)
    flush_frame(frame)


# ---------- partida ----------

def velocidad_para_nivel(nivel):
    """Tiempos (encendido, apagado) en segundos. Cuanto mas alto el nivel, mas rapido."""
    base_on = max(0.18, 0.60 - nivel * 0.015)
    base_off = max(0.07, 0.20 - nivel * 0.008)
    return base_on, base_off


def reproducir_secuencia(secuencia, nivel, mejor):
    on_t, off_t = velocidad_para_nivel(nivel)
    render_estado(None, nivel, mejor, "Mira atento...", "amarB")
    time.sleep(0.8)
    for q in secuencia:
        render_estado(q, nivel, mejor, "Mira atento...", "amarB")
        time.sleep(on_t)
        render_estado(None, nivel, mejor, "Mira atento...", "amarB")
        time.sleep(off_t)


def turno_jugador(secuencia, nivel, mejor):
    """Devuelve True si acerto toda la secuencia, False si se equivoca o sale."""
    render_estado(None, nivel, mejor, "Tu turno - pulsa QWAS", "verdeB")
    for esperado in secuencia:
        tecla = ""
        while True:
            t = leer_tecla_bloqueante()
            if t == "\x03" or t == "\x1b":
                # Ctrl-C o ESC = abandonar partida
                return False
            if t in TECLA_A_CUADRANTE:
                tecla = t
                break
            # cualquier otra tecla se ignora
        idx = TECLA_A_CUADRANTE[tecla]
        # flash breve del cuadrante pulsado
        on_t, off_t = velocidad_para_nivel(nivel)
        render_estado(idx, nivel, mejor, "Tu turno - pulsa QWAS", "verdeB")
        time.sleep(max(0.10, on_t * 0.6))
        render_estado(None, nivel, mejor, "Tu turno - pulsa QWAS", "verdeB")
        if idx != esperado:
            return False
        time.sleep(0.05)
    return True


def jugar(mejor_previo):
    cls()
    sys.stdout.write(show_cursor(False))
    secuencia = []
    nivel = 0
    mejor = mejor_previo
    while True:
        nivel += 1
        secuencia.append(random.randint(0, 3))
        reproducir_secuencia(secuencia, nivel, mejor)
        ok = turno_jugador(secuencia, nivel, mejor)
        if not ok:
            # animacion de error: cuadrante correcto destellando 3 veces
            esperado = secuencia[-1] if secuencia else 0
            for _ in range(3):
                render_estado(esperado, nivel, mejor, "¡FALLASTE!", "rojoB")
                time.sleep(0.18)
                render_estado(None, nivel, mejor, "¡FALLASTE!", "rojoB")
                time.sleep(0.12)
            return nivel - 1  # nivel alcanzado (el que completaste antes del fallo)
        # acertaste, sigue
        if nivel > mejor:
            mejor = nivel
        render_estado(None, nivel, mejor, "¡Bien! Siguiente nivel...", "verdeB")
        time.sleep(0.7)



# ---------- splash y final ----------

LOGO_SIMON = [
    "███████╗██╗███╗   ███╗ ██████╗ ███╗   ██╗",
    "██╔════╝██║████╗ ████║██╔═══██╗████╗  ██║",
    "███████╗██║██╔████╔██║██║   ██║██╔██╗ ██║",
    "╚════██║██║██║╚██╔╝██║██║   ██║██║╚██╗██║",
    "███████║██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║",
    "╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝",
]


def _caja_linea(texto, ancho, color_txt, color_caja="magentaB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


MANUAL_LINEAS = [
    ('PREMISA', 'cyanB', 'bold'),
    '  Simon dice. La maquina ilumina una secuencia de cuadrantes',
    '  de colores. Tu la repites en el mismo orden.',
    '  Cada nivel acertado añade un paso y aumenta la velocidad.',
    '',
    ('CONTROLES (char-mode)', 'cyanB', 'bold'),
    '  Las teclas QWAS estan en disposicion 2x2 sobre el teclado,',
    '  igual que los cuadrantes en la pantalla:',
    '',
    '    Q = ROJO       W = VERDE',
    '    A = AZUL       S = AMARILLO',
    '',
    '  ESC / Ctrl-C    abandonar partida',
    '',
    ('MECANICA', 'cyanB', 'bold'),
    '  Cada nivel: la secuencia aumenta en 1 y el tiempo de flash baja.',
    '  Un fallo termina la partida.',
    '',
    ('OBJETIVO', 'cyanB', 'bold'),
    '  Llegar lo mas lejos posible. Top 10 por nivel alcanzado.',
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - SIMON BBS".ljust(70), "cyanB", "bold"))
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
    ancho = 60
    print()
    print(c("╔" + "═" * ancho + "╗", "magentaB"))
    print(_caja_linea("", ancho, "blanco"))
    for ln in LOGO_SIMON:
        print(_caja_linea(ln, ancho, "amarB"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Memoriza y repite la secuencia de colores", ancho, "cyanB"))
    print(_caja_linea("Cada acierto sube un nivel - cada nivel mas rapido", ancho, "blanco"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Q = ROJO    W = VERDE", ancho, "rojoB"))
    print(_caja_linea("A = AZUL    S = AMARILLO", ancho, "azulB"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("ESC para abandonar la partida", ancho, "dim"))
    print(_caja_linea("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "magentaB"))
    msg = "[Enter] empezar     [M] manual"
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        raw = input("")
    except EOFError:
        return
    if raw.strip().lower() == "m":
        mostrar_manual()


def pantalla_final(nivel, top_entered, scores, nombre_guardado=None):
    sys.stdout.write(show_cursor(True))
    cls()
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    lado = c("║", "magentaB")
    print(margen + c("╔" + linea + "╗", "magentaB"))
    print(margen + lado + c(" FIN DE PARTIDA ".center(ancho), "amarB", "bold") + lado)
    print(margen + c("╠" + linea + "╣", "magentaB"))
    print(margen + lado + f"  Nivel alcanzado : {c(str(nivel).rjust(15) + '  ', 'cyanB', 'bold')}".ljust(ancho + 15) + lado)
    if top_entered:
        print(margen + lado + c("  ¡NUEVO RECORD!".center(ancho), "amarB", "bold") + lado)
    print(margen + c("╠" + linea + "╣", "magentaB"))
    print(margen + lado + c(" TOP 10 ".center(ancho), "cyanB", "bold") + lado)
    for i in range(MAX_TOP):
        if i < len(scores):
            n, p, d = scores[i]
            destacado = (nombre_guardado and n == nombre_guardado and p == nivel)
            estilo = ("amarB", "bold") if destacado else ("blanco",)
            ln_txt = f"  {i + 1:>2}. {n}   nivel {p:>3}   {d}"
            print(margen + lado + c(ln_txt.ljust(ancho), *estilo) + lado)
        else:
            print(margen + lado + " " * ancho + lado)
    print(margen + c("╚" + linea + "╝", "magentaB"))
    print()


# ---------- main ----------

def main():
    if not TERMIOS_OK:
        print("Simon necesita un TTY con termios.")
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
            mejor = (bbs_scores.top_local(limit=1, ascending=ASCENDING)[0].score if bbs_scores.top_local(limit=1, ascending=ASCENDING) else 0)
            nivel = jugar(mejor)
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            scores = [(e.handle, e.score, e.date) for e in bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)]
            top = bbs_scores.entra_en_top_local(nivel, max_top=MAX_TOP, ascending=ASCENDING)
            nombre_guardado = None
            if top and nivel > 0:
                ancho = 50
                margen = " " * ((COLS - (ancho + 2)) // 2)
                print()
                print(margen + c("  ¡Has entrado en el TOP 10!", "amarB", "bold"))
                nombre = ""
                while not nombre:
                    try:
                        raw = input(margen + "  Iniciales (3 chars): ").strip().upper()
                    except EOFError:
                        raw = "AAA"
                    nombre = "".join(ch for ch in raw if ch.isalnum())[:3].ljust(3, "A")
                bbs_scores.save_local(nombre, nivel, max_top=MAX_TOP, ascending=ASCENDING)
                bbs_scores.submit(nombre, nivel)
                bbs_scores.invalidate_cache()
                scores = [(e.handle, e.score, e.date) for e in bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)]
                nombre_guardado = nombre
            pantalla_final(nivel, top, scores, nombre_guardado)
            # Toggle [L]ocal / [G]lobal del top mundial
            while True:
                try:
                    _r = input(c("\n  [L] local   [G] global   [Enter] continuar: ", "dim")).strip().upper()
                except EOFError:
                    break
                if _r not in ("L", "G"):
                    break
                _modo = "local" if _r == "L" else "global"
                cls()  # toggle redibuja limpio
                print()
                _scores_e, _titulo, _ = bbs_scores.get_top_for_mode(_modo, limit=MAX_TOP, ascending=ASCENDING)
                print()
                print(c("  " + _titulo.strip(), "cyanB", "bold"))
                print(c("  " + "-" * 50, "dim"))
                _handle_w = max(14, max((len(_e.display_handle if _modo == "global" else _e.handle) for _e in _scores_e), default=14))
                for _i, _e in enumerate(_scores_e, 1):
                    _et = _e.display_handle if _modo == "global" else _e.handle
                    print(f"  {_i:>2}. {_et:{_handle_w}}  {str(_e.score).rjust(8)}  {_e.date}")
                print()

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
