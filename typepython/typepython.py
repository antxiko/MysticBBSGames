#!/usr/bin/env python3
"""TypePython - juego de mecanografia estilo typespeed en espanol."""
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(SCRIPT_DIR, "typepython_scores.txt")
MAX_TOP = 10

COLS = 80
ROWS = 24
TOP_ROW = 1
TITLE_ROW = 2
SEP1_ROW = 3
GAME_TOP = 4
GAME_BOTTOM = 17
SEP2_ROW = 18
STATUS_ROW = 19
SEP3_ROW = 20
PROMPT_ROW = 21
BOTTOM_ROW = 22
PROMPT_COL = 3

VIDAS_INICIAL = 3
TICK = 0.05

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
    "azulB":   "\x1b[94m",
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


def clr_line():
    return "\x1b[2K"


def cls():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def show_cursor(v):
    return "\x1b[?25h" if v else "\x1b[?25l"


PALABRAS = [
    "casa", "perro", "gato", "arbol", "libro", "mesa", "silla", "agua", "pan", "sol",
    "luna", "cielo", "mar", "rio", "flor", "hoja", "nube", "viento", "fuego", "tierra",
    "aire", "nieve", "lluvia", "monte", "playa", "bosque", "selva", "campo", "ciudad",
    "pueblo", "calle", "puente", "torre", "muro", "puerta", "ventana", "techo", "suelo",
    "cama", "cocina", "salon", "pared", "espejo", "cuadro", "lampara", "cortina",
    "reloj", "telefono", "pantalla", "teclado", "raton", "disco", "cable", "luz",
    "sombra", "negro", "blanco", "rojo", "azul", "verde", "amarillo", "naranja",
    "violeta", "rosa", "marron", "gris", "oro", "plata", "cobre", "hierro", "metal",
    "madera", "piedra", "cristal", "papel", "tela", "cuero", "plastico", "goma",
    "jabon", "sal", "azucar", "harina", "aceite", "leche", "queso", "huevo", "carne",
    "pescado", "fruta", "manzana", "pera", "limon", "uva", "fresa", "cereza", "melon",
    "coco", "mango", "tomate", "patata", "cebolla", "ajo", "arroz", "trigo", "lenteja",
    "nuez", "cacao", "cafe", "vino", "copa", "vaso", "taza", "plato", "tenedor",
    "cuchara", "cuchillo", "sarten", "horno", "nevera", "plancha", "manta", "almohada",
    "zapato", "pantalon", "camisa", "chaqueta", "abrigo", "bufanda", "gorro", "guante",
    "gafas", "bolso", "maleta", "mochila", "paraguas", "linterna", "mapa", "brujula",
    "cuerda", "martillo", "clavo", "sierra", "pala", "jardin", "granja", "carretera",
    "tunel", "avion", "tren", "coche", "moto", "barco", "taxi", "camion",
    "musica", "cancion", "guitarra", "piano", "bateria", "flauta", "trompeta", "violin",
    "pelicula", "cine", "teatro", "libro", "revista", "diario", "noticia", "historia",
    "rey", "reina", "juez", "policia", "bombero", "medico", "enfermero", "cocinero",
    "maestro", "alumno", "amigo", "vecino", "padre", "madre", "hijo", "hija",
    "hermano", "tio", "abuelo", "primo", "novio", "esposa", "bebe", "nino",
    "saltar", "correr", "andar", "nadar", "volar", "dormir", "comer", "beber",
    "leer", "escribir", "hablar", "cantar", "bailar", "pensar", "reir", "llorar",
    "mirar", "buscar", "encontrar", "abrir", "cerrar", "romper", "arreglar", "limpiar",
    "rapido", "lento", "grande", "pequeno", "alto", "bajo", "fuerte", "debil",
    "viejo", "joven", "nuevo", "bonito", "feo", "dulce", "salado", "amargo",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "lunes", "martes", "jueves", "viernes", "sabado", "domingo", "hoy", "manana",
    "ayer", "siempre", "nunca", "tarde", "pronto", "aqui", "alli", "cerca",
    "lejos", "arriba", "abajo", "dentro", "fuera", "delante", "detras", "izquierda",
]


def dibujar_marco():
    linea_d = "\u2550" * (COLS - 2)
    linea_s = "\u2500" * (COLS - 2)
    lateral = c("\u2551", "verdeB")
    hueco = " " * (COLS - 2)

    # top border
    sys.stdout.write(at(TOP_ROW, 1) + c("\u2554" + linea_d + "\u2557", "verdeB"))
    # title row
    titulo = "Typespeed BBS - teclea rapido o muere"
    pad_l = (COLS - 2 - len(titulo)) // 2
    pad_r = (COLS - 2) - pad_l - len(titulo)
    sys.stdout.write(at(TITLE_ROW, 1) + lateral + " " * pad_l + c(titulo, "amarB", "bold") + " " * pad_r + lateral)
    # sep under title
    sys.stdout.write(at(SEP1_ROW, 1) + c("\u2560" + linea_d + "\u2563", "verdeB"))
    # game area limpia
    for y in range(GAME_TOP, GAME_BOTTOM + 1):
        sys.stdout.write(at(y, 1) + lateral + hueco + lateral)
    # sep antes de status
    sys.stdout.write(at(SEP2_ROW, 1) + c("\u2560" + linea_d + "\u2563", "verdeB"))
    # status row
    sys.stdout.write(at(STATUS_ROW, 1) + lateral + hueco + lateral)
    # sep antes de prompt
    sys.stdout.write(at(SEP3_ROW, 1) + c("\u2560" + linea_s + "\u2563", "verdeB"))
    # prompt row
    sys.stdout.write(at(PROMPT_ROW, 1) + lateral + " > " + " " * (COLS - 5) + lateral)
    # bottom border
    sys.stdout.write(at(BOTTOM_ROW, 1) + c("\u255A" + linea_d + "\u255D", "verdeB"))
    sys.stdout.flush()


def render_status(puntos, nivel, vidas, palabras_ok):
    vivas = c("\u2665 " * vidas, "rojoB", "bold")
    muertas = c("\u2665 " * (VIDAS_INICIAL - vidas), "dim")
    corazones = vivas + muertas
    texto = (
        f" Puntos: {c(str(puntos).rjust(6), 'verdeB', 'bold')}  "
        f" Nivel: {c(str(nivel).rjust(2), 'amarB', 'bold')}  "
        f" Aciertos: {c(str(palabras_ok).rjust(4), 'cyanB')}  "
        f" Vidas: {corazones}"
    )
    sys.stdout.write(at(STATUS_ROW, 3) + clr_line()[:0] + texto)


def render_frame(palabras, puntos, nivel, vidas, palabras_ok):
    buf = "\x1b[s"
    # limpiar area de juego (interior del marco)
    for y in range(GAME_TOP, GAME_BOTTOM + 1):
        buf += at(y, 2) + " " * (COLS - 2)
    # pintar palabras
    for p in palabras:
        x = int(p["x"])
        if x < 2 or x >= COLS - 1:
            continue
        max_len = (COLS - 1) - x
        w = p["word"][:max_len]
        buf += at(p["y"], x) + c(w, "amarB", "bold")
    # status
    buf += at(STATUS_ROW, 2) + " " * (COLS - 2)
    vivas = c("\u2588" * vidas, "rojoB", "bold")
    muertas = c("\u2588" * (VIDAS_INICIAL - vidas), "dim")
    corazones = vivas + muertas
    linea_estado = (
        f" Puntos: {c(str(puntos).rjust(6), 'verdeB', 'bold')}  "
        f"Nivel: {c(str(nivel).rjust(2), 'amarB', 'bold')}  "
        f"Aciertos: {c(str(palabras_ok).rjust(4), 'cyanB')}  "
        f"Vidas: {corazones}"
    )
    buf += at(STATUS_ROW, 3) + linea_estado
    buf += "\x1b[u"
    sys.stdout.write(buf)
    sys.stdout.flush()


LOGO_TYPESPEED = [
    "\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2557   \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557 ",
    "\u255A\u2550\u2550\u2588\u2588\u2554\u2550\u2550\u255D\u255A\u2588\u2588\u2557 \u2588\u2588\u2554\u255D\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557",
    "   \u2588\u2588\u2551    \u255A\u2588\u2588\u2588\u2588\u2554\u255D \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551  \u2588\u2588\u2551",
    "   \u2588\u2588\u2551     \u255A\u2588\u2588\u2554\u255D  \u2588\u2588\u2554\u2550\u2550\u2550\u255D \u2588\u2588\u2554\u2550\u2550\u255D  \u255A\u2550\u2550\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2550\u255D \u2588\u2588\u2554\u2550\u2550\u255D  \u2588\u2588\u2554\u2550\u2550\u255D  \u2588\u2588\u2551  \u2588\u2588\u2551",
    "   \u2588\u2588\u2551      \u2588\u2588\u2551   \u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D",
    "   \u255A\u2550\u255D      \u255A\u2550\u255D   \u255A\u2550\u255D     \u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D\u255A\u2550\u255D     \u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u255D ",
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
    ancho = 76
    print()
    print(c("\u2554" + "\u2550" * ancho + "\u2557", "verdeB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_TYPESPEED:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Clon de typespeed en espanol", ancho, "cyanB"))
    print(_caja_linea_splash("Teclea las palabras antes de que crucen la pantalla", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("\u255A" + "\u2550" * ancho + "\u255D", "verdeB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


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


def es_top(puntos):
    scores = cargar_scores()
    if len(scores) < MAX_TOP:
        return True
    return puntos > scores[-1][1]


def pantalla_final(puntos, nivel, aciertos):
    cls()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "\u2550" * ancho
    lado = c("\u2551", "rojoB")

    def fila_kv(label, val, col):
        prefijo = f"  {label}"
        plano = prefijo + val
        pad = ancho - len(plano)
        return margen + lado + prefijo + c(val, col, "bold") + " " * pad + lado

    def fila_centrada(texto, *estilos):
        pad_total = ancho - len(texto)
        pad_l = pad_total // 2
        pad_r = pad_total - pad_l
        return margen + lado + " " * pad_l + c(texto, *estilos) + " " * pad_r + lado

    print()
    print(margen + c("\u2554" + linea + "\u2557", "rojoB"))
    print(fila_centrada("FIN DE LA PARTIDA", "bold"))
    print(margen + c("\u2560" + linea + "\u2563", "rojoB"))
    print(fila_kv("Puntos finales : ", str(puntos).rjust(10), "verdeB"))
    print(fila_kv("Nivel alcanzado: ", str(nivel).rjust(10), "amarB"))
    print(fila_kv("Palabras OK    : ", str(aciertos).rjust(10), "cyanB"))
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
    print(margen + c("  TOP 10".ljust(ancho) , "bold"))
    print(margen + c("\u2500" * ancho, "dim"))
    for i, (n, p, d) in enumerate(scores, 1):
        color = "amarB" if p == puntos else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(8), color)}  {c(d, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


def jugar():
    cls()
    sys.stdout.write(show_cursor(False))
    dibujar_marco()

    palabras = []
    puntos = 0
    nivel = 1
    vidas = VIDAS_INICIAL
    aciertos = 0
    vel_cols_seg = 3.0
    spawn_cada = 3.0
    ultimo_spawn = 0.0

    sys.stdout.write(at(PROMPT_ROW, PROMPT_COL) + "> ")
    sys.stdout.flush()

    try:
        while vidas > 0:
            tick_start = time.time()

            if tick_start - ultimo_spawn > spawn_cada:
                usadas = {p["y"] for p in palabras}
                libres = [y for y in range(GAME_TOP, GAME_BOTTOM + 1) if y not in usadas]
                if libres:
                    palabras.append({
                        "word": random.choice(PALABRAS),
                        "x": 2.0,
                        "y": random.choice(libres),
                    })
                    ultimo_spawn = tick_start

            for p in palabras[:]:
                p["x"] += vel_cols_seg * TICK
                if int(p["x"]) + len(p["word"]) > COLS - 1:
                    vidas -= 1
                    palabras.remove(p)

            render_frame(palabras, puntos, nivel, vidas, aciertos)

            resto = TICK - (time.time() - tick_start)
            if resto > 0:
                ready, _, _ = select.select([sys.stdin], [], [], resto)
                if ready:
                    linea = sys.stdin.readline()
                    if not linea:
                        vidas = 0
                        break
                    palabra = linea.strip().lower()
                    if palabra == "salir":
                        vidas = 0
                        break
                    if palabra:
                        for p in palabras[:]:
                            if p["word"].lower() == palabra:
                                puntos += len(p["word"]) * nivel
                                aciertos += 1
                                palabras.remove(p)
                                if aciertos % 10 == 0:
                                    nivel += 1
                                    vel_cols_seg = min(15.0, vel_cols_seg + 0.5)
                                    spawn_cada = max(0.8, spawn_cada - 0.25)
                                break
                    sys.stdout.write(at(PROMPT_ROW, PROMPT_COL) + "> " + " " * (COLS - PROMPT_COL - 4))
                    sys.stdout.write(at(PROMPT_ROW, PROMPT_COL + 2))
                    sys.stdout.flush()

    finally:
        sys.stdout.write(show_cursor(True))
        sys.stdout.flush()

    sys.stdout.write(at(ROWS, 1))
    pantalla_final(puntos, nivel, aciertos)


if __name__ == "__main__":
    try:
        splash()
        jugar()
    except KeyboardInterrupt:
        sys.stdout.write(show_cursor(True) + "\n")
        sys.stdout.flush()
        sys.exit(0)
