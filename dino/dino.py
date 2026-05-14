#!/usr/bin/env python3
"""Dino BBS - clon del runner del dinosaurio de Chrome offline.

Salta sobre los cactus que vienen por la derecha. La velocidad sube con el tiempo.
Optimizado para BBS: solo se mueven los cactus y la animacion de patas del dino,
el resto de la pantalla es estatica.
"""
import math
import os
import random
import sys
import time
from datetime import date

# Cliente compartido para scores: vive en la raiz del repo.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
GROUND_ROW = 18  # fila donde se pinta la linea de suelo
DINO_X = 6  # columna izquierda del sprite del dino
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_TOP = 10

# fisicas
GRAVITY = 40.0
JUMP_VEL = 22.0
SPEED_INI = 14.0  # cols/seg al comienzo
SPEED_MAX = 38.0
SPEED_ACEL = 0.8  # cols/seg^2 - de 14 a 38 en ~30s

# spawn
SPAWN_MIN = 1.1
SPAWN_MAX = 2.6
SPAWN_GAP_MIN_COLS = 12  # distancia minima entre cactus al spawnear
MAX_CACTUS = 2  # como mucho 2 cactus simultaneos en pantalla

FPS = 20
FRAME_DT = 1.0 / FPS

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


# Shadow buffer
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


# ---------- sprites ----------
# Dino 5 cols x 4 filas. Bottom row es la fila de patas (sobre el suelo).

DINO_RUN_1 = [
    "  ▄██▄",
    " ████▄",
    "▐████ ",
    " █  █ ",
]
DINO_RUN_2 = [
    "  ▄██▄",
    " ████▄",
    "▐████ ",
    "  █  █",
]
DINO_JUMP = [
    "  ▄██▄",
    " ████▄",
    "▐████ ",
    " █▀▀█ ",
]
DINO_MUERTO = [
    "  ▄██▄",
    " ██x█▄",
    "▐████ ",
    " █  █ ",
]
DINO_W = 6
DINO_H = 4

# Cactus de tres tamaños. Bottom-aligned a row 17 (3 filas por encima del suelo).

CACTUS_S = [
    " █ ",
    "███",
    " █ ",
]
CACTUS_M = [
    "█ █",
    "███",
    " █ ",
]
CACTUS_L = [
    "█ █ █",
    "█████",
    "  █  ",
]
CACTUS_TIPOS = {
    "small":  {"sprite": CACTUS_S, "w": 3},
    "medium": {"sprite": CACTUS_M, "w": 3},
    "large":  {"sprite": CACTUS_L, "w": 5},
}


# ---------- render ----------

def pintar_sprite(frame, x, y, sprite, color):
    for j, ln in enumerate(sprite):
        for i, ch in enumerate(ln):
            if ch != " ":
                set_cell(frame, y + j, x + i, ch, color)


def render(frame, dino_y, dino_state, obstaculos, score, hi_score, speed):
    # HUD
    set_text(frame, 0, 1, "DINO BBS", "verdeB", "bold")
    set_text(frame, 0, 40, f"HI {hi_score:05d}", "amarB")
    set_text(frame, 0, 60, f"SCORE {score:05d}", "blancoB", "bold")

    # cielo: blank (frame_nuevo ya da espacios)
    # nube estatica decorativa
    nube_y = 4
    nube_x = 50
    set_text(frame, nube_y, nube_x, "  ▄▄▄▄  ", "dim")
    set_text(frame, nube_y + 1, nube_x, " ██████ ", "dim")

    # dino: bottom-aligned a row 17 (justo encima del suelo)
    dino_bottom = 17
    dino_top = dino_bottom - DINO_H + 1 - int(round(dino_y))
    if dino_state == "muerto":
        sprite = DINO_MUERTO
        color = "rojoB"
    elif dino_state == "jump":
        sprite = DINO_JUMP
        color = "verdeB"
    elif dino_state == "run1":
        sprite = DINO_RUN_1
        color = "verdeB"
    else:
        sprite = DINO_RUN_2
        color = "verdeB"
    pintar_sprite(frame, DINO_X, dino_top, sprite, color)

    # cactus
    for o in obstaculos:
        ox = int(round(o["x"]))
        tipo = CACTUS_TIPOS[o["tipo"]]
        sprite = tipo["sprite"]
        # bottom-aligned a row 17
        top = 17 - len(sprite) + 1
        # clip to COLS
        for j, ln in enumerate(sprite):
            for i, ch in enumerate(ln):
                if ch == " ":
                    continue
                sx = ox + i
                if 0 <= sx < COLS:
                    set_cell(frame, top + j, sx, ch, "verde", "bold")

    # suelo: una linea estatica de _ a row 18 (no scroll = 0 celdas cambiando)
    for x_ in range(COLS):
        set_cell(frame, GROUND_ROW, x_, "_", "blanco")

    # footer
    set_text(frame, 22, 0, "═" * COLS, "magenta")
    set_text(frame, 23, 1, "Espacio = saltar    Q = salir", "dim")
    set_text(frame, 23, COLS - 14, f"Vel {speed:>4.1f}", "dim")


# Scores: delegado al cliente compartido bbs_scores. Dino usa orden descendente.
ASCENDING = False


def mejor_score():
    top = bbs_scores.top_local(limit=1, ascending=ASCENDING)
    return top[0].score if top else 0


# ---------- splash y manual ----------

LOGO_DINO = [
    "██████╗ ██╗███╗   ██╗ ██████╗ ",
    "██╔══██╗██║████╗  ██║██╔═══██╗",
    "██║  ██║██║██╔██╗ ██║██║   ██║",
    "██║  ██║██║██║╚██╗██║██║   ██║",
    "██████╔╝██║██║ ╚████║╚██████╔╝",
    "╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ ",
]


def _caja_linea(texto, ancho, color_txt, color_caja="magentaB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


MANUAL_LINEAS = [
    ("PREMISA", "cyanB", "bold"),
    "  Clon del juego del dinosaurio del Chrome offline.",
    "  Eres un T-Rex corriendo por el desierto. Saltan cactus,",
    "  tienes que esquivarlos. La velocidad sube con el tiempo.",
    "",
    ("CONTROLES (char-mode)", "cyanB", "bold"),
    "  Espacio / W / flecha arriba    saltar",
    "  Q                              salir",
    "",
    ("MECANICA", "cyanB", "bold"),
    "  Salto parabolico (no se mantiene pulsado).",
    "  Solo puedes saltar cuando estas en el suelo.",
    "  Tres tamaños de cactus: pequeño, mediano, grande.",
    "  Cada choque = game over. Una sola vida.",
    "",
    ("OPTIMIZACION BBS", "cyanB", "bold"),
    "  Cielo y suelo estaticos: solo se mueven los cactus,",
    "  el dino y los digitos del score.",
    "",
    ("OBJETIVO", "cyanB", "bold"),
    "  Aguantar lo mas posible. Score = distancia recorrida.",
    "  Top 10 persistente.",
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - DINO BBS".ljust(70), "cyanB", "bold"))
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
    for ln in LOGO_DINO:
        print(_caja_linea(ln, ancho, "verdeB"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Salta cactus. Aguanta. Bate tu record.", ancho, "cyanB"))
    print(_caja_linea("Como cuando se cae internet, pero con BBS.", ancho, "dim"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Espacio = saltar    Q = salir", ancho, "amarB"))
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


def _pintar_top(scores, score, nombre_guardado, ancho, margen, lado, modo_label, modo_color):
    """Pinta la cabecera de la tabla + las 10 filas. scores es list[ScoreEntry]."""
    print(margen + lado + c(modo_label.center(ancho), modo_color, "bold") + lado)
    cfg = bbs_scores.get_config()
    for i in range(MAX_TOP):
        if i < len(scores):
            e = scores[i]
            destacado = (nombre_guardado and e.handle == nombre_guardado
                         and e.score == score
                         and e.bbs_short_name == cfg.bbs_short_name)
            estilo = ("amarB", "bold") if destacado else ("blanco",)
            # En global muestra handle@BBS; en local solo handle.
            es_global = (modo_label.strip().upper().startswith("TOP GLOBAL"))
            etiqueta = e.display_handle if es_global else e.handle
            ln_txt = f"  {i + 1:>2}. {etiqueta:<14} {e.score:>6} pts   {e.date}"
            print(margen + lado + c(ln_txt.ljust(ancho), *estilo) + lado)
        else:
            print(margen + lado + " " * ancho + lado)


def pantalla_final(score, hi_score, top_entered, nombre_guardado=None):
    """Muestra el resumen + top con toggle L/G. Cada iteracion del bucle redibuja."""
    sys.stdout.write(show_cursor(True))
    modo = "local"  # "local" | "global"
    while True:
        cls()
        print()
        ancho = 56
        margen = " " * ((COLS - (ancho + 2)) // 2)
        linea = "═" * ancho
        lado = c("║", "magentaB")
        print(margen + c("╔" + linea + "╗", "magentaB"))
        print(margen + lado + c(" GAME OVER ".center(ancho), "rojoB", "bold") + lado)
        print(margen + c("╠" + linea + "╣", "magentaB"))
        print(margen + lado + f"  Score        : {c(str(score).rjust(15) + '  ', 'cyanB', 'bold')}".ljust(ancho + 15) + lado)
        print(margen + lado + f"  Mejor previo : {c(str(hi_score).rjust(15) + '  ', 'amarB', 'bold')}".ljust(ancho + 15) + lado)
        if top_entered:
            print(margen + lado + c("  ¡NUEVO RECORD!".center(ancho), "amarB", "bold") + lado)
        print(margen + c("╠" + linea + "╣", "magentaB"))

        if modo == "global":
            scores = bbs_scores.top_global(limit=MAX_TOP, ascending=ASCENDING)
            online = bbs_scores.is_online()
            etiqueta = " TOP GLOBAL " if online else " TOP GLOBAL (sin conexion, mostrando local) "
            color = "verdeB" if online else "amarB"
            if not online:
                scores = bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)
        else:
            scores = bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)
            etiqueta = " TOP LOCAL "
            color = "cyanB"

        _pintar_top(scores, score, nombre_guardado, ancho, margen, lado, etiqueta, color)
        print(margen + c("╚" + linea + "╝", "magentaB"))
        print()

        marca_l = ("amarB", "bold") if modo == "local" else ("dim",)
        marca_g = ("amarB", "bold") if modo == "global" else ("dim",)
        hint = (c(" [L] local ", *marca_l) + " " + c(" [G] global ", *marca_g)
                + "   " + c("[Enter] continuar", "blanco"))
        print(margen + "  " + hint)
        try:
            raw = input("").strip().upper()
        except EOFError:
            return
        if raw == "L":
            modo = "local"
            continue
        if raw == "G":
            modo = "global"
            continue
        return


# ---------- juego ----------

def colisiona(dino_y, obstaculos):
    """AABB sencillo. El dino entero se desplaza hacia arriba al saltar."""
    dino_left = DINO_X + 1  # margen para que el morro no golpee
    dino_right = DINO_X + DINO_W - 2
    dino_bottom = 17 - int(round(dino_y))
    dino_top = dino_bottom - DINO_H + 1
    for o in obstaculos:
        tipo = CACTUS_TIPOS[o["tipo"]]
        ox = int(round(o["x"]))
        ow = tipo["w"]
        oh = len(tipo["sprite"])
        cact_left = ox
        cact_right = ox + ow - 1
        cact_top = 17 - oh + 1
        cact_bottom = 17
        if cact_right < dino_left or cact_left > dino_right:
            continue
        if cact_bottom < dino_top or cact_top > dino_bottom:
            continue
        return True
    return False


def jugar(hi_score):
    cls()
    sys.stdout.write(show_cursor(False))

    dino_y = 0.0   # altura sobre el suelo en filas
    dino_vy = 0.0
    on_ground = True
    speed = SPEED_INI
    obstaculos = []
    next_spawn = 1.0
    score_f = 0.0
    t_last = time.time()
    muerto_hasta = None  # tras chocar, deja la frame de muerto unos ms y termina

    while True:
        now = time.time()
        dt = now - t_last
        if dt > 0.1:
            dt = 0.1
        t_last = now

        # input
        salir = False
        while True:
            tecla = leer_tecla_noblock()
            if tecla is None:
                break
            if tecla in ("q", "Q", "\x03"):
                return int(score_f)
            if tecla in (" ", "w", "W", "\x1b[A"):
                if on_ground and muerto_hasta is None:
                    dino_vy = JUMP_VEL
                    on_ground = False

        if muerto_hasta is not None:
            if now >= muerto_hasta:
                return int(score_f)
            # render frame de muerto y seguir esperando
            frame = frame_nuevo()
            render(frame, dino_y, "muerto", obstaculos, int(score_f), hi_score, speed)
            flush_frame(frame)
            rest = FRAME_DT - (time.time() - now)
            if rest > 0:
                time.sleep(rest)
            continue

        # fisica
        dino_vy -= GRAVITY * dt
        dino_y += dino_vy * dt
        if dino_y <= 0:
            dino_y = 0
            dino_vy = 0
            on_ground = True
        else:
            on_ground = False

        # mover cactus
        for o in obstaculos:
            o["x"] -= speed * dt
        obstaculos = [o for o in obstaculos if o["x"] > -6]

        # spawn
        next_spawn -= dt
        if next_spawn <= 0:
            # cap a MAX_CACTUS y gap minimo entre cactus
            ok = len(obstaculos) < MAX_CACTUS
            for o in obstaculos:
                if o["x"] > COLS - SPAWN_GAP_MIN_COLS:
                    ok = False
                    break
            if ok:
                tipo = random.choices(
                    ["small", "medium", "large"],
                    weights=[3, 3, 1],
                )[0]
                obstaculos.append({"x": float(COLS), "tipo": tipo})
            # mas frecuente a alta velocidad
            factor = max(0.4, 1.0 - (speed - SPEED_INI) / (SPEED_MAX - SPEED_INI) * 0.6)
            next_spawn = random.uniform(SPAWN_MIN * factor, SPAWN_MAX * factor)

        # acelerar
        if speed < SPEED_MAX:
            speed = min(SPEED_MAX, speed + SPEED_ACEL * dt)

        # score
        score_f += speed * dt * 0.5

        # colision
        if colisiona(dino_y, obstaculos):
            muerto_hasta = now + 1.2
            continue

        # estado de animacion del dino
        if not on_ground:
            dino_state = "jump"
        else:
            dino_state = "run1" if int(now * 6) % 2 == 0 else "run2"

        # render
        frame = frame_nuevo()
        render(frame, dino_y, dino_state, obstaculos, int(score_f), hi_score, speed)
        flush_frame(frame)
        rest = FRAME_DT - (time.time() - now)
        if rest > 0:
            time.sleep(rest)


def main():
    if not TERMIOS_OK:
        print("Dino necesita un TTY con termios.")
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
            hi = mejor_score()
            score = jugar(hi)
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            top = bbs_scores.entra_en_top_local(score, max_top=MAX_TOP, ascending=ASCENDING)
            nombre_guardado = None
            if score > 0:
                if top:
                    ancho = 50
                    margen = " " * ((COLS - (ancho + 2)) // 2)
                    print()
                    print(margen + c("  ¡Has entrado en el TOP local!", "amarB", "bold"))
                    nombre = ""
                    while not nombre:
                        try:
                            raw = input(margen + "  Iniciales (3 chars): ").strip().upper()
                        except EOFError:
                            raw = "AAA"
                        nombre = "".join(ch for ch in raw if ch.isalnum())[:3].ljust(3, "A")
                    bbs_scores.save_local(nombre, score, max_top=MAX_TOP, ascending=ASCENDING)
                    nombre_guardado = nombre
                else:
                    # No entra en top local, pero mandamos al global igualmente.
                    nombre = "AAA"
                # Submit al servidor (fire-and-forget). Si no hay config = no-op.
                bbs_scores.submit(nombre_guardado or "AAA", score)
                bbs_scores.invalidate_cache(game="dino")
            pantalla_final(score, hi, top, nombre_guardado)
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
