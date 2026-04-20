#!/usr/bin/env python3
"""Wordle BBS - adivina la palabra de 5 letras en 6 intentos."""
import os
import random
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="cp437", errors="replace")
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(SCRIPT_DIR, "wordle_scores.txt")
MAX_TOP = 10

LARGO = 5
INTENTOS_MAX = 6
COLS = 80

PALABRAS = [
    "CASAS","PERRO","GATOS","MESAS","SILLA","LIBRO","NOCHE","TARDE","RELOJ","PLAYA",
    "MONTE","PIZZA","FUEGO","TIGRE","ZORRO","TRIGO","MANGO","LIMON","MELON","YOGUR",
    "SERIE","LAPIZ","NIEVE","CAMPO","MUNDO","CALLE","CARTA","BOLSA","MOTOR","LETRA",
    "LISTA","DATOS","VERSO","BINGO","NORTE","VERDE","NEGRO","SUAVE","DULCE","GORDO",
    "LARGO","CORTO","NUEVO","POBRE","FIRME","MALOS","ROJOS","BUENA","SABIO","DUROS",
    "FALSO","TONTO","LENTO","ANDAR","BEBER","COMER","SALIR","SUBIR","PASAR","DECIR",
    "TOCAR","JUGAR","AMIGO","ARENA","BAHIA","BANCO","BARBA","BARCO","BARRO","BESOS",
    "BOTON","BRAVO","BROMA","BROTE","BUENO","CABLE","CAFES","CAIDA","CAJAS","CANTO",
    "CARAS","CARGA","CERCA","CERDO","CIELO","CORAL","COSTA","CRUEL","CUBOS","CULPA",
    "DEBIL","DELTA","DIEZA","DIGNO","DOBLE","DOLAR","DOLOR","DRAMA","DUCHA","DUENA",
    "ECHAR","ENERO","ENTRE","ERROR","EXITO","FAMAS","FELIZ","FERIA","FICHA","FINCA",
    "FLOTA","FORMA","FRESA","FRUTA","FUMAR","FUSIL","GANAR","GASES","GENTE","GORRA",
    "GRADO","GRANO","GRATO","GRAVE","GRISA","GRUPO","GUANT","GUAPO","HABLA","HACIA",
    "HIELO","HIJOS","HORNO","HUEVO","HUMOR","IDEAS","IGUAL","JAMON","JARRA","JINET",
    "JOVEN","JUEGO","JUSTO","LABIO","LADRO","LAGOS","LARVA","LATIN","LAVAR","LIBRE",
    "LIMPI","LOCAL","LUCES","LUJOS","LUMBR","MADRE","MAGIA","MALOS","MANGA","MAPAS",
    "MARCA","MEDIA","MIELO","MIRAR","MODOS","MULTA","MUROS","NACER","NARIZ","NEVAD",
    "NINOS","NIVEL","NOVIA","NUBES","NUNCA","OBESO","OBRAR","OLORA","OPERA","ORDEN",
    "PADRE","PAGAR","PALMA","PAPEL","PARTE","PASTA","PATIO","PAUSA","PECAS","PEDIR",
    "PEINE","PENAS","PERAL","PERLA","PESCA","PIANO","PINZA","PISOS","PLANO","PLATA",
    "PLAZA","POBRE","POCOS","PODER","PONER","POSTA","PRESA","PRIMA","PUEDE","PULPO",
    "PUNTA","PUNTO","QUESO","QUIEN","QUIZA","RADIO","RAMAS","RAZON","REGAR","REGLA",
    "RELOJ","REMAR","RENDI","REZAR","RICOS","RIEGO","RIMAR","RIZOS","ROBAR","ROCAS",
    "ROCIO","ROLLO","ROMPI","ROPAS","ROSAL","ROSCA","RUBIA","RUEDA","RUIDO","SABER",
    "SACAR","SACOS","SALES","SALTO","SALUD","SANOS","SECAR","SEGAR","SEGUI","SELVA",
    "SEMAN","SENAS","SERES","SETAS","SIGNO","SIRVO","SOBRE","SOCIO","SOLES","SOMOS",
    "SONAR","SUAVE","SUEGR","SUMAS","TACOS","TALLA","TANGO","TAPAR","TAPIZ","TAREA",
    "TASAS","TECHO","TEJER","TENER","TEXTO","TIEND","TIERR","TINTA","TOALL","TOCAR",
    "TOCIN","TOMAR","TORRE","TORSO","TOSTE","TRAER","TRAJE","TRAMA","TRATO","TREGU",
    "TRENO","TRIBU","TRONC","TROZO","TRUCO","TUMBA","UBICA","UNICO","VACAS","VAGOS",
    "VANOS","VECES","VELAR","VENAS","VERDE","VERGA","VIAJE","VIEJO","VIENT","VITAL",
    "VIVOS","VOCAL","VOLAR","YATES","YEMAS","ZONAS","ZORRO","ZUMOS",
]

# Quitar duplicados y palabras que no sean 5 letras alfabeticas mayusculas
PALABRAS = sorted(set(p for p in PALABRAS if len(p) == LARGO and p.isalpha()))

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
    "cyanB":   "\x1b[1;36m",
    "bold":    "\x1b[1m",
    "dim":     "\x1b[2m",
}
RESET = "\x1b[0m"

# Celdas coloreadas por estado (fondo + primer plano + negrita)
CELDA = {
    "acierto": "\x1b[42;30;1m",   # fondo verde, texto negro, negrita
    "parcial": "\x1b[43;30;1m",   # fondo amarillo, texto negro, negrita
    "fallo":   "\x1b[40;1;37m",    # fondo gris oscuro, texto blanco
    "nada":    "\x1b[47;30m",     # fondo gris claro, texto negro (teclado sin usar)
    "vacio":   "\x1b[40;37;2m",   # fondo negro, texto gris (celda aun no jugada)
}


def c(txt, *estilos):
    if not estilos:
        return str(txt)
    for e in estilos:
        if e in COLORES:
            return f"{COLORES[e]}{txt}{RESET}"
    return str(txt)


def celda(letra, estado):
    prefijo = CELDA.get(estado, CELDA["vacio"])
    return f"{prefijo} {letra} {RESET}"


def cls():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def evaluar(intento, objetivo):
    """Devuelve lista de estados por cada letra: acierto / parcial / fallo."""
    estados = ["fallo"] * LARGO
    restantes = list(objetivo)
    # 1er pase: aciertos
    for i, ch in enumerate(intento):
        if ch == objetivo[i]:
            estados[i] = "acierto"
            restantes[i] = None
    # 2o pase: parciales
    for i, ch in enumerate(intento):
        if estados[i] == "fallo" and ch in restantes:
            estados[i] = "parcial"
            restantes[restantes.index(ch)] = None
    return estados


def actualizar_teclado(estado_letra, palabra, estados):
    prioridad = {"acierto": 3, "parcial": 2, "fallo": 1, "nada": 0}
    for ch, est in zip(palabra, estados):
        actual = estado_letra.get(ch, "nada")
        if prioridad[est] > prioridad[actual]:
            estado_letra[ch] = est


def dibujar_titulo():
    titulo = "WORDLE BBS"
    sub = "Adivina la palabra secreta en 6 intentos"
    print(c(titulo.center(COLS), "amarB", "bold"))
    print(c(sub.center(COLS), "dim"))
    print()


def dibujar_grid(intentos):
    anc_grid = (LARGO * 3) + (LARGO - 1)  # 3 chars por celda + 1 espacio entre
    sangria = " " * ((COLS - anc_grid) // 2)
    for i in range(INTENTOS_MAX):
        if i < len(intentos):
            palabra, estados = intentos[i]
            linea = " ".join(celda(ch, est) for ch, est in zip(palabra, estados))
        else:
            linea = " ".join(celda(" ", "vacio") for _ in range(LARGO))
        print(sangria + linea)


def dibujar_teclado(estado_letra):
    filas = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
    for fila in filas:
        anc = len(fila) * 3 + (len(fila) - 1)
        sangria = " " * ((COLS - anc) // 2)
        linea = " ".join(celda(ch, estado_letra.get(ch, "nada")) for ch in fila)
        print(sangria + linea)


def mensaje(texto, *estilos):
    print(c(texto.center(COLS), *estilos))


def pedir_intento():
    prompt = "> "
    sangria = " " * ((COLS - 20) // 2)
    try:
        raw = input(sangria + prompt).strip().upper()
    except EOFError:
        return None
    return raw


def pintar_estado(intentos, estado_letra, msg=None, msg_estilo=None):
    cls()
    dibujar_titulo()
    dibujar_grid(intentos)
    print()
    dibujar_teclado(estado_letra)
    print()
    mensaje(f"Intento {len(intentos)}/{INTENTOS_MAX}", "cyanB")
    print()
    if msg:
        if msg_estilo:
            mensaje(msg, *msg_estilo)
        else:
            mensaje(msg)
        print()


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


def es_top(puntos):
    if puntos <= 0:
        return False
    scores = cargar_scores()
    if len(scores) < MAX_TOP:
        return True
    return puntos > scores[-1][1]


# ---------- splash y pantalla final ----------

LOGO_WORDLE = [
    "\u2588\u2588\u2557    \u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "\u2588\u2588\u2551    \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D",
    "\u2588\u2588\u2551 \u2588\u2557 \u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2557  ",
    "\u2588\u2588\u2551\u2588\u2588\u2588\u2557\u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u255D  ",
    "\u255A\u2588\u2588\u2588\u2554\u2588\u2588\u2588\u2554\u255D\u255A\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    " \u255A\u2550\u2550\u255D\u255A\u2550\u2550\u255D  \u255A\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u255D  \u255A\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u255D \u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D",
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
    for ln in LOGO_WORDLE:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Adivina la palabra de 5 letras", ancho, "cyanB"))
    print(_caja_linea_splash("Verde = bien. Amarillo = mal lugar. Gris = no esta.", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("\u255A" + "\u2550" * ancho + "\u255D", "verdeB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_final(puntos_total, partidas, ganadas):
    cls()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "\u2550" * ancho
    lado = c("\u2551", "magenta")

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
    print(margen + c("\u2554" + linea + "\u2557", "magenta"))
    print(fila_centrada("RESUMEN DE SESION", "bold"))
    print(margen + c("\u2560" + linea + "\u2563", "magenta"))
    print(fila_kv("Puntos totales : ", str(puntos_total).rjust(10), "verdeB"))
    print(fila_kv("Partidas       : ", str(partidas).rjust(10), "cyanB"))
    print(fila_kv("Ganadas        : ", str(ganadas).rjust(10), "amarB"))
    print(margen + c("\u255A" + linea + "\u255D", "magenta"))
    print()

    if es_top(puntos_total):
        print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
        nombre = ""
        while not nombre:
            try:
                raw = input(margen + "  Iniciales (3 letras): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalpha())[:3].ljust(3, "A")
        scores = guardar_score(nombre, puntos_total)
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("\u2500" * ancho, "dim"))
    for i, (n, p, d) in enumerate(scores, 1):
        color = "amarB" if p == puntos_total else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(str(p).rjust(8), color)}  {c(d, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- logica de partida ----------

def jugar_partida():
    palabra = random.choice(PALABRAS)
    intentos = []
    estado_letra = {}
    aviso = None
    aviso_estilo = None

    while len(intentos) < INTENTOS_MAX:
        pintar_estado(intentos, estado_letra, aviso, aviso_estilo)
        aviso = None
        aviso_estilo = None
        raw = pedir_intento()
        if raw is None:
            return None, None
        if raw == "SALIR":
            return None, None
        if len(raw) != LARGO or not raw.isalpha():
            aviso = "Debe ser una palabra de 5 letras."
            aviso_estilo = ("rojoB",)
            continue
        estados = evaluar(raw, palabra)
        intentos.append((raw, estados))
        actualizar_teclado(estado_letra, raw, estados)
        if raw == palabra:
            break

    pintar_estado(intentos, estado_letra)
    gano = intentos and intentos[-1][0] == palabra
    if gano:
        puntos = (INTENTOS_MAX + 1 - len(intentos)) * 100
        mensaje(f"GANASTE en {len(intentos)} intentos. +{puntos} puntos.", "verdeB", "bold")
    else:
        puntos = 0
        mensaje(f"Se acabaron los intentos. Era: {palabra}", "rojoB", "bold")
    print()
    return puntos, gano


def otra_partida():
    try:
        raw = input("   Otra partida? [S/N]: ").strip().upper()
    except EOFError:
        return False
    return raw.startswith("S")


def sesion():
    puntos_total = 0
    partidas = 0
    ganadas = 0
    while True:
        res = jugar_partida()
        if res == (None, None):
            break
        puntos, gano = res
        partidas += 1
        puntos_total += puntos
        if gano:
            ganadas += 1
        if not otra_partida():
            break
    pantalla_final(puntos_total, partidas, ganadas)


if __name__ == "__main__":
    try:
        splash()
        sesion()
    except KeyboardInterrupt:
        print("\n")
        sys.exit(0)
