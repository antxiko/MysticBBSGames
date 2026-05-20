#!/usr/bin/env python3
"""Sokoban BBS - empuja cajas a las marcas."""
import os
import sys
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_TOP = 10
ASCENDING = False  # True si menos = mejor

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
    ("Pasaje obligado", """
########
#.    .#
#      #
#  ##  #
# $  $ #
#      #
#  @   #
########
"""),
    ("Cuatro arriba", """
##########
# . . . .#
#        #
#        #
# $ $ $ $#
#        #
#        #
#   @    #
##########
"""),
    ("El nicho", """
########
#  . . #
#  # # #
#  $ $ #
#      #
#  @   #
########
"""),
    ("Cinco apretados", """
###########
# .....   #
#         #
# $$$$$   #
#         #
#         #
#    @    #
###########
"""),
    ("Almacen lleno", """
############
# ........ #
#          #
#          #
# $$$$$$$$ #
#          #
#          #
#     @    #
############
"""),
    ("Patio cuadrado", """
##########
#  ....  #
#  ....  #
#        #
#  $$$$  #
#  $$$$  #
#        #
#  @     #
##########
"""),
    ("Triple paso", """
###########
#.        #
# #####   #
# $       #
# #####   #
#.        #
# #####   #
# $       #
# #####   #
#.        #
# $       #
#   @     #
###########
"""),
    ("Caos ordenado", """
############
# .. .. .. #
#          #
#          #
# $$ $$ $$ #
#          #
#          #
#     @    #
############
"""),
    ("Doble fila", """
##########
# ...... #
#        #
# ...... #
#        #
# $$$$$$ #
#        #
# $$$$$$ #
#        #
#   @    #
##########
"""),
    ("La rambla", """
##############
# .......... #
#            #
#            #
#            #
# $$$$$$$$$$ #
#            #
#            #
#     @      #
##############
"""),
    ("Tres salas", """
###############
#  . #  . #  .#
#    #    #   #
# $  # $  # $ #
#    #    #   #
#  ###  ###   #
#             #
#      @      #
###############
"""),
    ("Esquina dificil", """
##########
# .      #
#        #
#  ###   #
# .  #   #
# $  #   #
#    #   #
#  $@#   #
##########
"""),
    ("Mismo destino", """
###########
# ....... #
#         #
#         #
# $$$$$$$ #
#         #
#         #
#         #
#         #
#         #
#    @    #
###########
"""),
    ("Tablero", """
##########
# . . . .#
# . . . .#
#        #
# $ $ $ $#
# $ $ $ $#
#        #
#   @    #
##########
"""),
    ("La galeria", """
##############
#............#
#            #
#$ $ $ $ $ $ #
#            #
#$ $ $ $ $ $ #
#            #
#      @     #
##############
"""),
    ("Centro y bordes", """
###########
# . . . . #
# . . . . #
# .     . #
#         #
#  $$$$$  #
#  $$$$$  #
#         #
#         #
#    @    #
###########
"""),
    ("Doble paso", """
##############
# .. .. .. ..#
#            #
#            #
# $$ $$ $$ $$#
#            #
#            #
#     @      #
##############
"""),
    ("Cuadricula", """
############
# . .  . . #
#          #
# .      . #
#          #
# $      $ #
#          #
# $ $  $ $ #
#          #
#    @     #
############
"""),
    ("El gran final", """
##############
# ..........#
#           #
#           #
# $$$$$$$$$ #
#           #
# $         #
#           #
#     @     #
##############
"""),
    ("La pesadilla", """
##############
# .. .. .. ..#
# .. .. .. ..#
#            #
#            #
# $$ $$ $$ $$#
# $$ $$ $$ $$#
#            #
#            #
#      @     #
##############
"""),
]
