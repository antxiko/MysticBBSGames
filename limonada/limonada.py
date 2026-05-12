#!/usr/bin/env python3
"""Limonada BBS - clon de Lemonade Stand en castellano."""
import os
import random
import sys
from datetime import date

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


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(SCRIPT_DIR, "limonada_scores.txt")
MAX_TOP = 10

COLS = 80
DIAS_TOTAL = 30
DINERO_INICIAL = 200      # 200 centimos = $2.00
COSTE_VASO = 2            # centimos
COSTE_ANUNCIO = 15        # centimos

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


def cls():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


CLIMAS = {
    "soleado":  {"texto": "Soleado",  "color": "amarB",    "mod": 15,  "desc": "Dia perfecto para vender limonada."},
    "caluroso": {"texto": "Caluroso", "color": "rojoB",    "mod": 30,  "desc": "Hace un calor tremendo, la gente esta sedienta."},
    "nublado":  {"texto": "Nublado",  "color": "blanco",   "mod": 0,   "desc": "Cielo cubierto. Demanda normal."},
    "lluvia":   {"texto": "Lluvia",   "color": "azulB",    "mod": -25, "desc": "Llueve. Pocos compradores en la calle."},
    "tormenta": {"texto": "Tormenta", "color": "magentaB", "mod": -90, "desc": "Tormenta fuerte. Nadie sale a la calle."},
}

EVENTOS = [
    ("Festival local en tu barrio!",              "demanda_x2"),
    ("Una manifestacion bloquea la calle",        "demanda_0"),
    ("Un youtuber recomienda tu puesto",          "demanda_x15"),
    ("Apagon general. Sin nevera para el hielo",  "demanda_0"),
    ("Tu abuela trae a su grupo de petanca",      "demanda_plus20"),
    ("Un perro vuelca tu mesa",                   "perder_la_mitad"),
    ("Un turista paga el doble por nostalgia",    "precio_x15"),
    ("Inspeccion sanitaria sorpresa",             "multa_30"),
]


# ---------- escenarios meteo ----------

def clima_aleatorio(nivel_dia):
    """Mas tormentas hacia el final, pero variable."""
    pool = ["soleado", "soleado", "caluroso", "nublado", "nublado", "lluvia"]
    if nivel_dia > 10:
        pool.append("tormenta")
    if nivel_dia > 20:
        pool.append("tormenta")
    return random.choice(pool)


# ---------- io ----------

def pedir_num(prompt, minimo, maximo, default=None):
    while True:
        suf = f" [{default}]" if default is not None else ""
        try:
            s = input(f"  {prompt}{suf}: ").strip()
        except EOFError:
            return default if default is not None else minimo
        if s == "" and default is not None:
            return default
        try:
            n = int(s)
        except ValueError:
            print(c("    Numero invalido.", "rojoB"))
            continue
        if n < minimo:
            print(c(f"    Minimo permitido: {minimo}.", "rojoB"))
            continue
        if n > maximo:
            print(c(f"    Maximo permitido: {maximo}.", "rojoB"))
            continue
        return n


def fmt_dinero(centimos):
    """Devuelve formato $X.XX a partir de centimos enteros."""
    signo = "-" if centimos < 0 else ""
    cent = abs(centimos)
    return f"{signo}${cent // 100}.{cent % 100:02d}"


# ---------- pantallas ----------

def cabecera(dia, dinero):
    cls()
    linea = "═" * 60
    sangria = " " * ((COLS - 62) // 2)
    print()
    print(sangria + c("╔" + linea + "╗", "amarB"))
    titulo = f"PUESTO DE LIMONADA  -  Dia {dia} de {DIAS_TOTAL}"
    pad = (60 - len(titulo)) // 2
    print(sangria + c("║", "amarB") + " " * pad + c(titulo, "amarB", "bold") + " " * (60 - pad - len(titulo)) + c("║", "amarB"))
    dinero_txt = f"Caja: {fmt_dinero(dinero)}"
    pad = (60 - len(dinero_txt)) // 2
    print(sangria + c("║", "amarB") + " " * pad + c(dinero_txt, "verdeB", "bold") + " " * (60 - pad - len(dinero_txt)) + c("║", "amarB"))
    print(sangria + c("╚" + linea + "╝", "amarB"))


def pantalla_meteo(clima):
    info = CLIMAS[clima]
    print()
    print("  " + c("PARTE METEOROLOGICO", "bold"))
    print("  " + c("─" * 30, "dim"))
    print("  Tiempo previsto: " + c(info["texto"].upper(), info["color"], "bold"))
    print("  " + c(info["desc"], "dim"))
    print()


def pantalla_costes():
    print("  " + c("COSTES DE HOY", "bold"))
    print("  " + c("─" * 30, "dim"))
    print(f"  Coste por vaso preparado: {c(fmt_dinero(COSTE_VASO), 'cyanB')}")
    print(f"  Coste por anuncio:        {c(fmt_dinero(COSTE_ANUNCIO), 'cyanB')}")
    print()


def pedir_decisiones(dinero):
    print("  " + c("DECISIONES DE HOY", "bold"))
    print("  " + c("─" * 30, "dim"))
    # vasos: maximo limitado por dinero
    max_vasos = dinero // COSTE_VASO
    vasos = pedir_num(f"¿Cuantos vasos preparas? (max {max_vasos})", 0, max_vasos, default=0)
    # precio
    precio = pedir_num("¿Precio por vaso en centimos? (1-30)", 1, 30, default=10)
    # anuncios
    presupuesto_restante = dinero - vasos * COSTE_VASO
    max_anuncios = presupuesto_restante // COSTE_ANUNCIO
    anuncios = pedir_num(f"¿Cuantos anuncios? (max {max_anuncios})", 0, max_anuncios, default=0)
    return vasos, precio, anuncios


# ---------- simulacion ----------

def factor_precio(precio):
    if precio <= 5:
        return 1.3
    if precio <= 10:
        return 1.0
    if precio <= 15:
        return 0.6
    if precio <= 20:
        return 0.3
    return 0.1


def bono_anuncios(n):
    # diminishing returns
    if n <= 0:
        return 0
    if n <= 5:
        return n * 4
    return 20 + (n - 5) * 2


def aplicar_evento(demanda, vasos, precio, evento_tipo):
    """Modifica demanda/vasos/precio segun el evento. Devuelve (demanda, vasos, precio, multa)."""
    multa = 0
    if evento_tipo == "demanda_x2":
        demanda = int(demanda * 2)
    elif evento_tipo == "demanda_0":
        demanda = 0
    elif evento_tipo == "demanda_x15":
        demanda = int(demanda * 1.5)
    elif evento_tipo == "demanda_plus20":
        demanda += 20
    elif evento_tipo == "perder_la_mitad":
        vasos = vasos // 2
    elif evento_tipo == "precio_x15":
        precio = int(precio * 1.5)
    elif evento_tipo == "multa_30":
        multa = 30
    return demanda, vasos, precio, multa


def simular_dia(clima, vasos, precio, anuncios):
    """Devuelve dict con resultados del dia."""
    base = 30
    mod_clima = CLIMAS[clima]["mod"]
    demanda = (base + mod_clima) * factor_precio(precio) + bono_anuncios(anuncios)
    demanda = max(0, int(demanda + random.randint(-5, 5)))

    # Posible evento (~1 de cada 5 dias)
    evento_msg = None
    multa = 0
    if random.random() < 0.20:
        msg, tipo = random.choice(EVENTOS)
        evento_msg = msg
        demanda, vasos, precio, multa = aplicar_evento(demanda, vasos, precio, tipo)

    vendidos = min(vasos, demanda)
    ingresos = vendidos * precio
    coste_vasos = vasos * COSTE_VASO  # se pagan los preparados, vendidos o no
    coste_anuncios_total = anuncios * COSTE_ANUNCIO
    beneficio = ingresos - coste_vasos - coste_anuncios_total - multa

    return {
        "demanda": demanda,
        "vendidos": vendidos,
        "vasos": vasos,
        "precio": precio,
        "ingresos": ingresos,
        "coste_vasos": coste_vasos,
        "coste_anuncios": coste_anuncios_total,
        "multa": multa,
        "beneficio": beneficio,
        "evento_msg": evento_msg,
    }


def pantalla_resultados(res, dia, dinero_tras):
    print()
    print("  " + c("RESULTADOS DEL DIA", "bold"))
    print("  " + c("─" * 30, "dim"))
    if res["evento_msg"]:
        print("  " + c(f"* {res['evento_msg']}", "magentaB", "bold"))
        print()
    print(f"  Demanda en la calle :    {c(str(res['demanda']), 'cyanB')}")
    print(f"  Vasos preparados    :    {c(str(res['vasos']), 'blanco')}")
    print(f"  Vasos vendidos      :    {c(str(res['vendidos']), 'verdeB', 'bold')}")
    if res["vasos"] > res["vendidos"]:
        sobras = res["vasos"] - res["vendidos"]
        print(c(f"     (te sobraron {sobras} vasos — limonada para ti)", "dim"))
    if res["demanda"] > res["vasos"]:
        perdidos = res["demanda"] - res["vasos"]
        print(c(f"     (te quedaste corto: {perdidos} clientes se fueron sin servir)", "dim"))
    print()
    print(f"  Ingresos            :    {c(fmt_dinero(res['ingresos']), 'verdeB', 'bold')}")
    print(f"  Coste de vasos      :   -{fmt_dinero(res['coste_vasos'])}")
    print(f"  Coste de anuncios   :   -{fmt_dinero(res['coste_anuncios'])}")
    if res["multa"] > 0:
        print(f"  Multas              :   {c('-' + fmt_dinero(res['multa']), 'rojoB')}")
    print("  " + c("─" * 30, "dim"))
    color_ben = "verdeB" if res["beneficio"] >= 0 else "rojoB"
    print(f"  Beneficio del dia   :    {c(fmt_dinero(res['beneficio']), color_ben, 'bold')}")
    print()
    print(f"  Caja al cerrar dia {dia} : {c(fmt_dinero(dinero_tras), 'amarB', 'bold')}")
    print()
    try:
        input("  " + c("Pulsa Enter para el siguiente dia...", "dim"))
    except EOFError:
        pass


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


# ---------- splash y final ----------

LOGO_LIMONADA = [
    "██╗     ██╗███╗   ███╗ ██████╗ ███╗   ██╗ █████╗ ██████╗  █████╗ ",
    "██║     ██║████╗ ████║██╔═══██╗████╗  ██║██╔══██╗██╔══██╗██╔══██╗",
    "██║     ██║██╔████╔██║██║   ██║██╔██╗ ██║███████║██║  ██║███████║",
    "██║     ██║██║╚██╔╝██║██║   ██║██║╚██╗██║██╔══██║██║  ██║██╔══██║",
    "███████╗██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║  ██║██████╔╝██║  ██║",
    "╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝",
]

LOGO_BBS = [
    "██████╗ ██████╗ ███████╗",
    "██╔══██╗██╔══██╗██╔════╝",
    "██████╔╝██████╔╝███████╗",
    "██╔══██╗██╔══██╗╚════██║",
    "██████╔╝██████╔╝███████║",
    "╚═════╝ ╚═════╝ ╚══════╝",
]


def _caja_linea_splash(texto, ancho, color_txt, color_caja="amarB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


def splash():
    cls()
    ancho = 70
    print()
    print(c("╔" + "═" * ancho + "╗", "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_LIMONADA:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    for ln in LOGO_BBS:
        print(_caja_linea_splash(ln, ancho, "amarB"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(_caja_linea_splash("Lleva tu puesto de limonada 30 dias.", ancho, "cyanB"))
    print(_caja_linea_splash("Hazte rico vendiendo vasos a 10 centimos.", ancho, "blanco"))
    print(_caja_linea_splash("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "amarB"))
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        input("")
    except EOFError:
        pass


def pantalla_final(dinero, dias_completos):
    cls()
    print()
    ancho = 50
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    color_caja = "verdeB" if dinero >= DINERO_INICIAL else "rojoB"
    lado = c("║", color_caja)

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

    print(margen + c("╔" + linea + "╗", color_caja))
    titulo = "TEMPORADA TERMINADA" if dias_completos else "BANCARROTA"
    print(fila_centrada(titulo, "bold"))
    print(margen + c("╠" + linea + "╣", color_caja))
    print(fila_kv("Dias jugados   : ", str(dias_completos).rjust(20), "amarB"))
    print(fila_kv("Caja final     : ", fmt_dinero(dinero).rjust(20),
                  "verdeB" if dinero >= DINERO_INICIAL else "rojoB"))
    delta = dinero - DINERO_INICIAL
    print(fila_kv("Variacion      : ",
                  (("+" if delta >= 0 else "") + fmt_dinero(delta)).rjust(20),
                  "verdeB" if delta >= 0 else "rojoB"))
    print(margen + c("╚" + linea + "╝", color_caja))
    print()

    if es_top(dinero):
        print(margen + c("  [ENTRAS EN EL TOP 10]", "amarB", "bold"))
        print()
        nombre = ""
        while not nombre:
            try:
                raw = input(margen + "  Iniciales (3 letras): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalpha())[:3].ljust(3, "A")
        scores = guardar_score(nombre, dinero)
    else:
        scores = cargar_scores()

    print()
    print(margen + c("  TOP 10".ljust(ancho), "bold"))
    print(margen + c("─" * ancho, "dim"))
    for i, (n, p, d) in enumerate(scores, 1):
        color = "amarB" if p == dinero else "blanco"
        print(margen + f"  {i:>2}. {c(n, color, 'bold')}  {c(fmt_dinero(p).rjust(10), color)}  {c(d, 'dim')}")
    print()
    try:
        input(margen + c("  Pulsa Enter para salir...", "dim"))
    except EOFError:
        pass


# ---------- juego ----------

def jugar():
    dinero = DINERO_INICIAL
    dias_jugados = 0
    for dia in range(1, DIAS_TOTAL + 1):
        if dinero < COSTE_VASO:
            # bancarrota
            return dinero, dias_jugados, False
        cabecera(dia, dinero)
        clima = clima_aleatorio(dia)
        pantalla_meteo(clima)
        pantalla_costes()
        vasos, precio, anuncios = pedir_decisiones(dinero)
        res = simular_dia(clima, vasos, precio, anuncios)
        dinero += res["beneficio"]
        if dinero < 0:
            dinero = 0
        pantalla_resultados(res, dia, dinero)
        dias_jugados = dia
    return dinero, dias_jugados, True


def main():
    try:
        splash()
        while True:
            dinero, dias, completo = jugar()
            pantalla_final(dinero, dias)
            try:
                raw = input("\n  Otra temporada? [S/N]: ").strip().upper()
            except EOFError:
                raw = "N"
            if not raw.startswith("S"):
                break
    except KeyboardInterrupt:
        print("\nAdios.")


if __name__ == "__main__":
    main()
