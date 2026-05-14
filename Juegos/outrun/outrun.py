#!/usr/bin/env python3
"""Outrun BBS - racer pseudo-3D en ASCII con perspectiva de carretera."""
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
HORIZON = 8
ROAD_BOT = 18
HUD_TOP = 22
HUD_BOT = 23

ROAD_HALF_W_NEAR = 28
TIEMPO_TOTAL = 90.0

SPEED_MAX = 240.0
SPEED_ACEL = 80.0
SPEED_FREN = 140.0
SPEED_ROZA = 20.0
SPEED_OFFROAD_MAX = 70.0
SPEED_OFFROAD_FREN = 220.0

STEER_VEL = 1.6
STEER_DECAY = 0.85
CURVA_DRIFT = 0.0015

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


# ---------- pista ----------

class TrackState:
    """Curvatura objetivo que cambia cada pocos segundos, suavizada hacia el actual."""
    def __init__(self):
        self.current = 0.0
        self.target = 0.0
        self.t_left = 0.0

    def tick(self, dt):
        self.t_left -= dt
        if self.t_left <= 0:
            opts = [-2.4, -1.5, -0.8, 0.0, 0.0, 0.0, 0.8, 1.5, 2.4]
            self.target = random.choice(opts)
            self.t_left = random.uniform(2.5, 5.0)
        # smooth lerp hacia target
        self.current += (self.target - self.current) * (dt * 0.8)


# ---------- render ----------

COCHE = [
    "  ▄███▄  ",
    " ██▀█▀██ ",
    "█████████",
    " █▀█▀█▀█ ",
]

ARBOL = [
    " ▲ ",
    "▲▲▲",
    " █ ",
]


def render(frame, z_pos, player_off, speed, curve_now, t_left, dist_total, off_road, throttle=0, steer_dir=0, brake_pulse=0.0):
    base_far = ROAD_BOT - HORIZON

    # cielo: gradiente con bandas
    for r in range(HORIZON):
        if r < 2:
            color = "azulB"
            ch = " "
        elif r < 5:
            color = "azul"
            ch = " "
        else:
            color = "magentaB"
            ch = "░"
        for x in range(COLS):
            set_cell(frame, r, x, ch, color)

    # sol en el horizonte (visible si la curva no lo tapa mucho)
    sun_x = COLS // 2 - 4 + int(curve_now * 3)
    for j, ln in enumerate(["  ▄▄▄▄▄  ", " ███████ ", "  ▀▀▀▀▀  "]):
        for k, ch in enumerate(ln):
            if ch != " ":
                set_cell(frame, HORIZON - 3 + j, sun_x + k, ch, "amarB")

    # horizonte
    for x in range(COLS):
        set_cell(frame, HORIZON, x, "─", "magentaB")

    # carretera: acumulo offset de centro fila por fila desde cerca a lejos
    row_data = []
    x_acc = 0.0
    dx = 0.0
    for row in range(ROAD_BOT, HORIZON, -1):
        dx += curve_now
        x_acc += dx
        row_data.append((row, x_acc))

    # render de lejos a cerca
    for row, x_off in reversed(row_data):
        dy = row - HORIZON
        scale = dy / base_far  # 0..1, 1 cerca
        half_w = max(2, int(ROAD_HALF_W_NEAR * scale))
        # x_off acumulado entra como desplazamiento horizontal con factor
        center = COLS // 2 + int(x_off * 0.06) - int(player_off * (ROAD_HALF_W_NEAR - 3) * scale)
        left_road = center - half_w
        right_road = center + half_w

        # fase por z para stripes/checkerboard
        z_world = (15.0 / max(1, dy)) + z_pos
        stripe_phase = int(z_world * 0.6) % 2
        grass_phase = int(z_world * 0.4) % 2
        center_dash = int(z_world * 0.5) % 4

        # color de superficie segun lejania
        if dy < 3:
            asfalto = ("▒", "dim")
        elif dy < 7:
            asfalto = ("░", "dim")
        else:
            asfalto = ("░", "blanco")

        for cc in range(COLS):
            if cc < left_road - 1:
                # hierba izquierda
                offset = ((cc // 5) ^ grass_phase) & 1
                col = "verdeB" if offset else "verde"
                ch = "▓" if dy >= 6 else "▒"
                set_cell(frame, row, cc, ch, col)
            elif cc == left_road - 1 or cc == right_road + 1:
                # arcen estrecho
                col = "rojoB" if stripe_phase == 0 else "blancoB"
                set_cell(frame, row, cc, "█", col)
            elif cc == left_road or cc == right_road:
                # borde de carretera
                col = "blancoB" if stripe_phase == 0 else "rojoB"
                set_cell(frame, row, cc, "█", col)
            elif cc < right_road:
                if cc == center and center_dash < 2 and dy > 2:
                    set_cell(frame, row, cc, "▌", "blancoB")
                else:
                    set_cell(frame, row, cc, asfalto[0], asfalto[1])
            else:
                offset = ((cc // 5) ^ grass_phase) & 1
                col = "verdeB" if offset else "verde"
                ch = "▓" if dy >= 6 else "▒"
                set_cell(frame, row, cc, ch, col)

    # coche del jugador
    car_x = COLS // 2 - 4
    car_y = ROAD_BOT + 1
    color_coche = "rojoB"
    if off_road:
        # parpadeo amarillo si nos hemos salido
        color_coche = "amarB" if (int(time.time() * 8) % 2) else "rojoB"
    for i, line in enumerate(COCHE):
        for j, ch in enumerate(line):
            if ch != " " and 0 <= car_y + i < SHADOW_ROWS:
                set_cell(frame, car_y + i, car_x + j, ch, color_coche)

    # HUD
    set_text(frame, HUD_TOP, 0, "═" * COLS, "magentaB")
    speed_kmh = int(abs(speed))
    speed_color = "verdeB" if speed_kmh < 100 else ("amarB" if speed_kmh < 180 else "rojoB")
    set_text(frame, HUD_BOT, 1, "VEL ", "blanco")
    set_text(frame, HUD_BOT, 5, f"{speed_kmh:>3} km/h", speed_color, "bold")
    # barra de velocidad
    barra_max = 12
    barra_n = min(barra_max, int(speed_kmh * barra_max / SPEED_MAX))
    set_text(frame, HUD_BOT, 16, "[" + "█" * barra_n + "·" * (barra_max - barra_n) + "]", speed_color)

    set_text(frame, HUD_BOT, 33, "DIST ", "blanco")
    set_text(frame, HUD_BOT, 38, f"{int(dist_total):>5}", "cyanB", "bold")

    set_text(frame, HUD_BOT, 50, "TIME ", "blanco")
    t_color = "verdeB" if t_left > 30 else ("amarB" if t_left > 10 else "rojoB")
    set_text(frame, HUD_BOT, 55, f"{int(max(0, t_left)):>3}s", t_color, "bold")

    # indicadores de estado (toggle): W acel, S fren, A izq, D der
    estado_w = ("W", "verdeB", "bold") if throttle == 1 else ("W", "dim")
    estado_s = ("S", "rojoB", "bold") if brake_pulse > 0.1 else ("S", "dim")
    estado_a = ("A", "amarB", "bold") if steer_dir == -1 else ("A", "dim")
    estado_d = ("D", "amarB", "bold") if steer_dir == 1 else ("D", "dim")
    set_text(frame, HUD_BOT, 63, "[", "dim")
    set_text(frame, HUD_BOT, 64, estado_w[0], *estado_w[1:])
    set_text(frame, HUD_BOT, 65, estado_s[0], *estado_s[1:])
    set_text(frame, HUD_BOT, 66, estado_a[0], *estado_a[1:])
    set_text(frame, HUD_BOT, 67, estado_d[0], *estado_d[1:])
    set_text(frame, HUD_BOT, 68, "] Q", "dim")

    if off_road:
        msg = " ¡FUERA DE PISTA! "
        set_text(frame, HUD_TOP, (COLS - len(msg)) // 2, msg, "amarB", "bold")



# ---------- splash y final ----------

LOGO_OUT = [
    " ██████╗ ██╗   ██╗████████╗",
    "██╔═══██╗██║   ██║╚══██╔══╝",
    "██║   ██║██║   ██║   ██║   ",
    "██║   ██║██║   ██║   ██║   ",
    "╚██████╔╝╚██████╔╝   ██║   ",
    " ╚═════╝  ╚═════╝    ╚═╝   ",
]

LOGO_RUN = [
    "██████╗ ██╗   ██╗███╗   ██╗",
    "██╔══██╗██║   ██║████╗  ██║",
    "██████╔╝██║   ██║██╔██╗ ██║",
    "██╔══██╗██║   ██║██║╚██╗██║",
    "██║  ██║╚██████╔╝██║ ╚████║",
    "╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝",
]


def _caja_linea(texto, ancho, color_txt, color_caja="magentaB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


MANUAL_LINEAS = [
    ('PREMISA', 'cyanB', 'bold'),
    '  Racer pseudo-3D inspirado en Out Run (Sega, 1986).',
    '  Carretera con perspectiva, curvas que se interpolan fila a fila.',
    '  Time-attack 90 segundos. Distancia = puntuacion.',
    '',
    ('CONTROLES (toggle / pulso)', 'cyanB', 'bold'),
    '  W   toggle gas (arranca activado, pulsa para soltar)',
    '  S   pulso de freno (cada tap = chorro de freno)',
    '  A   toggle giro izquierda',
    '  D   toggle giro derecha',
    '  Q   salir',
    '',
    ('MECANICA', 'cyanB', 'bold'),
    '  En curva, la inercia te empuja al exterior - compensa con A/D.',
    '  Fuera de pista la velocidad se cae a 70 km/h con frenazo brutal.',
    '  Indicadores [WSAD] en el HUD muestran estado activo.',
    '',
    ('OBJETIVO', 'cyanB', 'bold'),
    '  Maxima distancia en 90s. Top 10 persistente.',
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - OUTRUN BBS".ljust(70), "cyanB", "bold"))
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
    for ln in LOGO_OUT:
        print(_caja_linea(ln, ancho, "amarB"))
    print(_caja_linea("", ancho, "blanco"))
    for ln in LOGO_RUN:
        print(_caja_linea(ln, ancho, "rojoB"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Racer pseudo-3D en ASCII con perspectiva real", ancho, "cyanB"))
    print(_caja_linea("90 segundos. Distancia = puntuacion. A correr.", ancho, "blanco"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("W acelerar    S frenar    A/D girar    Q salir", ancho, "amarB"))
    print(_caja_linea("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "magentaB"))
    msg = "[Enter] arrancar     [M] manual"
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        raw = input("")
    except EOFError:
        return
    if raw.strip().lower() == "m":
        mostrar_manual()


def pantalla_final(dist, top_entered, scores, nombre_guardado=None):
    sys.stdout.write(show_cursor(True))
    cls()
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    lado = c("║", "magentaB")
    print(margen + c("╔" + linea + "╗", "magentaB"))
    print(margen + lado + c(" CARRERA TERMINADA ".center(ancho), "amarB", "bold") + lado)
    print(margen + c("╠" + linea + "╣", "magentaB"))
    print(margen + lado + f"  Distancia recorrida : {c(str(int(dist)).rjust(15) + ' m', 'verdeB', 'bold')}".ljust(ancho + 15) + lado)
    if top_entered:
        print(margen + lado + f"  {c('NUEVO RECORD!'.center(ancho - 4), 'amarB', 'bold')}  " + lado)
    print(margen + c("╠" + linea + "╣", "magentaB"))
    print(margen + lado + c(" TOP 10 ".center(ancho), "cyanB", "bold") + lado)
    for i in range(MAX_TOP):
        if i < len(scores):
            n, p, d = scores[i]
            destacado = (nombre_guardado and n == nombre_guardado and p == int(dist))
            estilo = ("amarB", "bold") if destacado else ("blanco",)
            linea_score = f"  {i + 1:>2}. {n}   {p:>6} m   {d}"
            print(margen + lado + c(linea_score.ljust(ancho), *estilo) + lado)
        else:
            print(margen + lado + " " * ancho + lado)
    print(margen + c("╚" + linea + "╝", "magentaB"))
    print()


# ---------- juego ----------

def jugar():
    cls()
    sys.stdout.write(show_cursor(False))
    track = TrackState()
    z_pos = 0.0
    player_off = 0.0  # -1..1 dentro de pista
    steer = 0.0
    speed = 0.0
    dist_total = 0.0
    t_left = TIEMPO_TOTAL
    t_last = time.time()

    # Estados toggle: terminal no permite key-hold, asi que cada tecla alterna.
    # throttle: 0 rueda libre, 1 acelerando (sticky toggle).
    # steer_dir: -1 izquierda, 0 centro, +1 derecha (sticky toggle).
    # brake_pulse: cada tap de S lo pone a 1.0 y decae rapido. Independiente del gas.
    throttle = 1  # arranca acelerando para no quedarte parado
    steer_dir = 0
    brake_pulse = 0.0

    while True:
        now = time.time()
        dt = now - t_last
        if dt > 0.1:
            dt = 0.1
        t_last = now

        quit_now = False
        while True:
            tecla = leer_tecla_noblock()
            if tecla is None:
                break
            if tecla in ("q", "Q", "\x03"):
                quit_now = True
            elif tecla in ("w", "W", "\x1b[A"):
                throttle = 1 if throttle != 1 else 0
            elif tecla in ("s", "S", "\x1b[B"):
                brake_pulse = 1.0  # tap = pulso de freno, no toca el throttle
            elif tecla in ("a", "A", "\x1b[D"):
                steer_dir = -1 if steer_dir != -1 else 0
            elif tecla in ("d", "D", "\x1b[C"):
                steer_dir = 1 if steer_dir != 1 else 0

        if quit_now:
            return dist_total, t_left

        # actualizar curve
        track.tick(dt)
        curve_now = track.current

        # velocidad: throttle + pulso de freno acumulable
        if throttle == 1:
            speed += SPEED_ACEL * dt
        else:
            speed -= SPEED_ROZA * dt
        if brake_pulse > 0.0:
            speed -= SPEED_FREN * dt * brake_pulse
            brake_pulse = max(0.0, brake_pulse - dt * 2.5)

        off_road = abs(player_off) > 1.0
        if off_road:
            speed -= SPEED_OFFROAD_FREN * dt
            if speed > SPEED_OFFROAD_MAX:
                speed = SPEED_OFFROAD_MAX
        speed = max(0.0, min(SPEED_MAX, speed))

        # steering instantaneo: el wheel se va al maximo en cuanto pulsas A/D
        steer = float(steer_dir)

        # mover lateral, snappy
        player_off += steer * dt * 4.0
        # drift por curva (con dt, antes faltaba y empujaba demasiado)
        player_off += curve_now * CURVA_DRIFT * speed * dt
        player_off = max(-2.0, min(2.0, player_off))

        # avanzar Z
        z_pos += speed * dt * 0.5
        dist_total += speed * dt * 0.1  # metros (escalado)

        # tiempo
        t_left -= dt
        if t_left <= 0:
            t_left = 0
            return dist_total, t_left

        # render
        frame = frame_nuevo()
        render(frame, z_pos, player_off, speed, curve_now, t_left, dist_total, off_road, throttle, steer_dir, brake_pulse)
        flush_frame(frame)
        # objetivo ~30 fps
        rest = 0.033 - (time.time() - now)
        if rest > 0:
            time.sleep(rest)


def main():
    if not TERMIOS_OK:
        print("Outrun necesita un TTY con termios.")
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
            dist, t_left = jugar()
            restaurar_terminal(old2)
            sys.stdout.write(show_cursor(True))
            sys.stdout.flush()
            dist_int = int(dist)
            nombre_guardado = None
            scores = [(e.handle, e.score, e.date) for e in bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)]
            top = bbs_scores.entra_en_top_local(dist_int, max_top=MAX_TOP, ascending=ASCENDING)
            if top and dist_int > 0:
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
                bbs_scores.save_local(nombre, dist_int, max_top=MAX_TOP, ascending=ASCENDING)
                bbs_scores.submit(nombre, dist_int)
                bbs_scores.invalidate_cache()
                scores = [(e.handle, e.score, e.date) for e in bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)]
                nombre_guardado = nombre
            pantalla_final(dist_int, top, scores, nombre_guardado)
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
                for _i, _e in enumerate(_scores_e, 1):
                    _et = _e.display_handle if _modo == "global" else _e.handle
                    print(f"  {_i:>2}. {_et:14}  {str(_e.score).rjust(8)}  {_e.date}")
                print()

            try:
                raw = input("\n  Otra carrera? [S/N]: ").strip().upper()
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
