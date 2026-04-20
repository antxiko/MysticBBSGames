#!/usr/bin/env python3
"""DopePython - clon de Dope Wars en espanol."""
import random
import sys

try:
    sys.stdout.reconfigure(encoding="cp437", errors="replace")
except Exception:
    pass

DIAS_TOTAL = 30
EFECTIVO_INICIAL = 2000
DEUDA_INICIAL = 5500
MALETIN_INICIAL = 100
SALUD_MAX = 100
INTERES_DEUDA = 0.10
INTERES_BANCO = 0.05

DROGAS = {
    "Cocaina":  (15000, 29000),
    "Heroina":  (5000, 13000),
    "Acido":    (1000, 4500),
    "Hierba":   (300, 900),
    "Speed":    (70, 250),
    "Ludes":    (10, 60),
    "PCP":      (1000, 2500),
    "Percocet": (40, 120),
    "Hongos":   (600, 1300),
    "Opio":     (540, 1250),
    "Morfina":  (2500, 6000),
    "Extasis":  (1500, 4400),
}

BARRIOS = ["Bronx", "Ghetto", "Central Park", "Manhattan", "Coney Island", "Brooklyn"]
BARRIO_BANCO = "Bronx"

EVENTOS_MERCADO_SPIKE = [
    "La policia confisco un cargamento de {droga}. Los precios se disparan!",
    "Un cartel ha monopolizado la {droga}. Precio por las nubes.",
    "Protestas por la escasez de {droga}.",
    "Tormenta en la costa: los barcos con {droga} no llegan.",
]

EVENTOS_MERCADO_CRASH = [
    "Llego un alijo enorme de {droga}. Precios por el suelo!",
    "La DEA incauto un laboratorio. Inundacion de {droga} barata.",
    "Escandalo sanitario con la {droga}: todos quieren venderla.",
    "Cargamento perdido de {droga} aparecido en el puerto.",
]

NOTICIAS_PLANAS = [
    "El Senador McCarthy III propone pena capital para camellos.",
    "Los yuppies de Wall Street no sueltan la cocaina.",
    "Huelga de basureros: las calles apestan.",
    "El Papa visita NY: patrullas policiales reforzadas.",
    "La mafia italiana negocia con los cubanos en Miami.",
    "Un rapero de Queens dice tu nombre en su nuevo disco.",
    "Confirmado: Elvis sigue vivo y vende Speed en Memphis.",
    "Lluvia de meteoros esta noche. Quedate en casa.",
    "Nueva moda: chalecos de cuero. A la gente le sobra la pasta.",
    "Apagon en Brooklyn. Saqueos hasta el amanecer.",
    "Los cientificos dicen que las drogas son malas. Quien lo diria.",
    "La CIA acusada de meter coca en los barrios negros.",
]

TITULARES_DIA = [
    "Daily News",
    "New York Post",
    "El Diario",
    "The Village Voice",
    "The Ghetto Gazette",
]

COSTE_HP_HOSPITAL = 50

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

TONO_BARRIO = {
    "Bronx":        "amar",
    "Ghetto":       "rojo",
    "Central Park": "verde",
    "Manhattan":    "cyanB",
    "Coney Island": "magenta",
    "Brooklyn":     "azul",
}


def c(txt, *estilos):
    if not estilos:
        return str(txt)
    for e in estilos:
        if e in COLORES:
            return f"{COLORES[e]}{txt}{RESET}"
    return str(txt)


def color_salud(salud):
    if salud <= 30:
        return "rojoB"
    if salud <= 60:
        return "amar"
    return "verdeB"


def barra_salud(salud, ancho=10):
    llenos = max(0, min(ancho, round(salud * ancho / SALUD_MAX)))
    vacios = ancho - llenos
    col = color_salud(salud)
    return c("[", "dim") + c("\u2588" * llenos, col) + c("\u2591" * vacios, "dim") + c("]", "dim")


def cls():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def pausa(msg=None):
    if msg is None:
        msg = " " + c("-- Pulsa Enter --", "bold") + " "
    try:
        input(msg)
    except EOFError:
        pass


def pedir(msg):
    try:
        return input(msg).strip()
    except EOFError:
        return ""


def pedir_num(msg, maximo=None):
    s = pedir(msg)
    if not s:
        return 0
    try:
        n = int(s)
    except ValueError:
        return 0
    if n < 0:
        return 0
    if maximo is not None and n > maximo:
        n = maximo
    return n


def pedir_tecla(msg, keys):
    s = pedir(msg).upper()
    if s and s[0] in keys:
        return s[0]
    return ""


def nuevo_estado():
    return {
        "dia": 1,
        "efectivo": EFECTIVO_INICIAL,
        "banco": 0,
        "deuda": DEUDA_INICIAL,
        "salud": SALUD_MAX,
        "balas": 0,
        "maletin": MALETIN_INICIAL,
        "barrio": "Bronx",
        "inventario": {d: 0 for d in DROGAS},
        "precios": {},
        "noticia": "",
    }


def unidades_libres(estado):
    return estado["maletin"] - sum(estado["inventario"].values())


def generar_precios(estado):
    precios = {}
    disponibles = random.sample(list(DROGAS), k=random.randint(6, len(DROGAS)))
    for droga in disponibles:
        lo, hi = DROGAS[droga]
        precios[droga] = random.randint(lo, hi)
    estado["precios"] = precios
    estado["noticia"] = ""

    noticia = ""
    r = random.random()
    if r < 0.25 and precios:
        droga = random.choice(list(precios.keys()))
        precios[droga] = int(DROGAS[droga][1] * random.uniform(2, 4))
        noticia = random.choice(EVENTOS_MERCADO_SPIKE).format(droga=droga)
    elif r < 0.50 and precios:
        droga = random.choice(list(precios.keys()))
        precios[droga] = max(1, int(DROGAS[droga][0] * random.uniform(0.1, 0.4)))
        noticia = random.choice(EVENTOS_MERCADO_CRASH).format(droga=droga)
    elif r < 0.85:
        noticia = random.choice(NOTICIAS_PLANAS)

    if noticia:
        titular = random.choice(TITULARES_DIA)
        estado["noticia"] = f"{titular}: {noticia}"


def dibujar_estado(estado):
    cls()
    doble = "\u2550" * 60
    simple = "\u2500" * 60
    print(c(doble, "dim"))
    dia_txt = c(f"Dia {estado['dia']:>2}/{DIAS_TOTAL}", "bold")
    barrio_raw = f"{estado['barrio']:<14}"
    barrio_txt = c(barrio_raw, TONO_BARRIO.get(estado["barrio"], "blanco"), "bold")
    salud_txt = c(f"{estado['salud']:>3}", color_salud(estado["salud"]), "bold")
    bar = barra_salud(estado["salud"])
    balas_txt = c(str(estado["balas"]), "amarB" if estado["balas"] > 0 else "dim")
    print(f" {dia_txt}   Barrio: {barrio_txt}  Salud: {salud_txt} {bar}  Balas: {balas_txt}")
    efe_raw = f"${estado['efectivo']:<10}"
    ban_raw = f"${estado['banco']:<10}"
    efe = c(efe_raw, "verdeB", "bold")
    ban = c(ban_raw, "verde")
    deu = c(f"${estado['deuda']}", "rojoB" if estado["deuda"] > 0 else "dim")
    print(f" Efectivo: {efe}  Banco: {ban}  Deuda: {deu}")
    usado = sum(estado["inventario"].values())
    print(f" Maletin: {c(usado, 'cyanB')}/{estado['maletin']}")
    print(c(doble, "dim"))
    if estado["noticia"]:
        print(c(f" * {estado['noticia']}", "amarB"))
        print(c(simple, "dim"))
    print(c(" Precios hoy:", "bold"))
    for droga, precio in estado["precios"].items():
        tengo = estado["inventario"][droga]
        extra = c(f"  (tienes {tengo})", "cyan") if tengo else ""
        print(f"   {droga:<10} ${precio:>7}{extra}")
    print(c(simple, "dim"))


def _op(letra, texto):
    return f"[{c(letra, 'amarB', 'bold')}]{texto}"


def menu_principal(estado):
    partes = [_op("C", "omprar"), _op("V", "ender"), _op("J", " Viajar"), _op("R", "esumen")]
    keys = "CVJR"
    if estado["barrio"] == BARRIO_BANCO:
        partes += [_op("$", " Banco"), _op("P", "restamista"), _op("H", "ospital")]
        keys += "$PH"
    partes.append(_op("S", "alir"))
    keys += "S"
    print("  ".join(partes))
    return pedir_tecla(c(" > ", "bold"), keys)


def accion_comprar(estado):
    if not estado["precios"]:
        print(" No hay nada a la venta hoy."); pausa(); return
    print(" Que droga? (numero/nombre, vacio=cancelar)")
    for i, d in enumerate(estado["precios"], 1):
        print(f"   {i}) {d}")
    s = pedir(" > ")
    if not s:
        return
    droga = None
    if s.isdigit():
        idx = int(s) - 1
        lista = list(estado["precios"])
        if 0 <= idx < len(lista):
            droga = lista[idx]
    else:
        for d in estado["precios"]:
            if d.lower().startswith(s.lower()):
                droga = d; break
    if droga is None:
        print(c(" Droga no reconocida.", "rojoB")); pausa(); return
    precio = estado["precios"][droga]
    max_por_dinero = estado["efectivo"] // precio
    max_por_espacio = unidades_libres(estado)
    maximo = min(max_por_dinero, max_por_espacio)
    if maximo <= 0:
        print(c(" No puedes comprar (sin efectivo o sin espacio).", "rojoB")); pausa(); return
    n = pedir_num(f" Cuantas unidades de {droga}? (max {maximo}): ", maximo)
    if n <= 0:
        return
    estado["efectivo"] -= n * precio
    estado["inventario"][droga] += n


def accion_vender(estado):
    vendibles = {d: q for d, q in estado["inventario"].items() if q > 0 and d in estado["precios"]}
    if not vendibles:
        print(" No tienes nada que se compre aqui hoy."); pausa(); return
    print(" Que droga vendes?")
    lista = list(vendibles)
    for i, d in enumerate(lista, 1):
        print(f"   {i}) {d} x{vendibles[d]}  @ ${estado['precios'][d]}")
    s = pedir(" > ")
    if not s:
        return
    droga = None
    if s.isdigit():
        idx = int(s) - 1
        if 0 <= idx < len(lista):
            droga = lista[idx]
    else:
        for d in lista:
            if d.lower().startswith(s.lower()):
                droga = d; break
    if droga is None:
        print(c(" Droga no reconocida.", "rojoB")); pausa(); return
    maximo = estado["inventario"][droga]
    n = pedir_num(f" Cuantas vendes? (max {maximo}): ", maximo)
    if n <= 0:
        return
    estado["efectivo"] += n * estado["precios"][droga]
    estado["inventario"][droga] -= n


def accion_banco(estado):
    print(f" Saldo banco: ${estado['banco']}  Efectivo: ${estado['efectivo']}")
    op = pedir_tecla(" [" + c("D", "amarB", "bold") + "]epositar  ["
                     + c("R", "amarB", "bold") + "]etirar  ["
                     + c("X", "amarB", "bold") + "] volver: ", "DRX")
    if op == "D":
        n = pedir_num(f" Cuanto depositas? (max ${estado['efectivo']}): ", estado["efectivo"])
        estado["efectivo"] -= n; estado["banco"] += n
    elif op == "R":
        n = pedir_num(f" Cuanto retiras? (max ${estado['banco']}): ", estado["banco"])
        estado["banco"] -= n; estado["efectivo"] += n


def accion_prestamista(estado):
    print(f" Deuda: ${estado['deuda']}  Efectivo: ${estado['efectivo']}")
    if estado["deuda"] <= 0:
        print(" No debes nada."); pausa(); return
    maximo = min(estado["deuda"], estado["efectivo"])
    if maximo <= 0:
        print(c(" No tienes efectivo para pagar.", "rojoB")); pausa(); return
    n = pedir_num(f" Cuanto pagas? (max ${maximo}): ", maximo)
    estado["efectivo"] -= n; estado["deuda"] -= n


def accion_hospital(estado):
    falta = SALUD_MAX - estado["salud"]
    salud_txt = c(f"{estado['salud']}/{SALUD_MAX}", color_salud(estado["salud"]), "bold")
    print(f" Clinica privada del Bronx. Tu salud: {salud_txt}  {barra_salud(estado['salud'])}")
    if falta <= 0:
        print(" Estas como nuevo. Largate de aqui.")
        pausa(); return
    max_por_dinero = estado["efectivo"] // COSTE_HP_HOSPITAL
    maximo = min(falta, max_por_dinero)
    print(f" Cada punto de salud cuesta ${COSTE_HP_HOSPITAL}. Te faltan {falta}.")
    if maximo <= 0:
        print(c(" No tienes ni para una tirita.", "rojoB"))
        pausa(); return
    n = pedir_num(f" Cuantos puntos curar? (max {maximo}, vacio=cancelar): ", maximo)
    if n <= 0:
        return
    estado["efectivo"] -= n * COSTE_HP_HOSPITAL
    estado["salud"] += n
    print(c(f" Curado +{n} ({n * COSTE_HP_HOSPITAL}$).", "verdeB"))
    pausa()


def resumen(estado):
    cls()
    print(c(" Resumen de inventario:", "bold"))
    total = 0
    for droga, q in estado["inventario"].items():
        if q > 0:
            print(f"   {droga:<10} x{q}")
            total += q
    if total == 0:
        print(c("   (maletin vacio)", "dim"))
    print("")
    efe = c(f"${estado['efectivo']}", "verdeB")
    ban = c(f"${estado['banco']}", "verde")
    deu = c(f"${estado['deuda']}", "rojoB")
    sal = c(str(estado["salud"]), color_salud(estado["salud"]))
    print(f" Efectivo: {efe}")
    print(f" Banco:    {ban}")
    print(f" Deuda:    {deu}")
    print(f" Salud:    {sal}   Balas: {estado['balas']}")
    pausa()


def combate_policia(estado):
    policias = random.randint(2, 6)
    print(c(f" !! {policias} policias te han visto y vienen a por ti !!", "rojoB", "bold"))
    while policias > 0 and estado["salud"] > 0:
        pol = c(str(policias), "rojoB", "bold")
        sal = c(str(estado["salud"]), color_salud(estado["salud"]), "bold")
        bal = c(str(estado["balas"]), "amarB")
        print(f" Policias: {pol}   Tu salud: {sal}   Balas: {bal}")
        if estado["balas"] <= 0:
            op = "H"
        else:
            op = pedir_tecla(f" [{c('L','amarB','bold')}]uchar o [{c('H','amarB','bold')}]uir: ", "LH")
        if op == "L" and estado["balas"] > 0:
            estado["balas"] -= 1
            if random.random() < 0.5:
                policias -= 1
                print(c(" Le diste a un policia!", "verdeB"))
            else:
                print(c(" Fallaste.", "dim"))
            if policias > 0 and random.random() < 0.4:
                dano = random.randint(5, 20)
                estado["salud"] -= dano
                print(c(f" Te alcanzaron: -{dano} salud.", "rojoB"))
        else:
            if random.random() < 0.6:
                print(c(" Conseguiste huir.", "verdeB"))
                return
            dano = random.randint(3, 15)
            estado["salud"] -= dano
            print(c(f" No escapaste: -{dano} salud.", "rojoB"))
        pausa()
    if estado["salud"] <= 0:
        return
    print(c(" Acabaste con los policias!", "verdeB", "bold")); pausa()


def prompt_si_no(msg):
    r = pedir_tecla(msg + f" [{c('S','amarB','bold')}]i / [{c('N','amarB','bold')}]o: ", "SN")
    return r == "S"


def evento_viaje(estado):
    r = random.random()
    if r < 0.12:
        combate_policia(estado)
    elif r < 0.22:
        perdida = random.randint(50, max(100, estado["efectivo"] // 4 or 100))
        perdida = min(perdida, estado["efectivo"])
        estado["efectivo"] -= perdida
        print(c(f" Te asaltaron en la calle. Perdiste ${perdida}.", "rojoB")); pausa()
    elif r < 0.32:
        encontrado = random.randint(100, 800)
        estado["efectivo"] += encontrado
        print(c(f" Encontraste ${encontrado} en un callejon.", "verdeB")); pausa()
    elif r < 0.40 and unidades_libres(estado) > 0:
        droga = random.choice(list(DROGAS))
        cantidad = min(random.randint(2, 8), unidades_libres(estado))
        estado["inventario"][droga] += cantidad
        print(c(f" Encontraste {cantidad} unidades de {droga} tiradas.", "verdeB")); pausa()
    elif r < 0.50:
        extra = random.choice([10, 20, 30])
        precio = extra * random.randint(40, 80)
        print(c(f" Un tipo te ofrece ampliar el maletin +{extra} por ${precio}.", "cyanB"))
        if estado["efectivo"] >= precio and prompt_si_no(""):
            estado["efectivo"] -= precio
            estado["maletin"] += extra
            print(c(" Trato hecho.", "verde")); pausa()
    elif r < 0.58:
        balas = random.randint(3, 8)
        precio = balas * random.randint(80, 150)
        print(c(f" Un traficante te ofrece {balas} balas por ${precio}.", "cyanB"))
        if estado["efectivo"] >= precio and prompt_si_no(""):
            estado["efectivo"] -= precio
            estado["balas"] += balas
            print(c(" Trato hecho.", "verde")); pausa()
    elif r < 0.64:
        cambio = random.choice([-15, -10, 10, 15])
        estado["salud"] = max(1, min(SALUD_MAX, estado["salud"] + cambio))
        signo = "+" if cambio > 0 else ""
        estilo = "verdeB" if cambio > 0 else "rojoB"
        print(c(f" Te comiste unos brownies misteriosos. Salud {signo}{cambio}.", estilo)); pausa()
    elif r < 0.70:
        monto = random.randint(200, 800)
        estado["efectivo"] += monto
        print(c(f" Tu madre te ha mandado un cheque de ${monto}. Que maja.", "verdeB")); pausa()
    elif r < 0.76:
        pide = random.randint(20, 80)
        print(c(f" Un mendigo te tira de la manga: 'colega, {pide} pavos para comer?'", "cyanB"))
        if estado["efectivo"] >= pide and prompt_si_no(""):
            estado["efectivo"] -= pide
            print(c(" Le das la limosna. Karma al alza.", "verde")); pausa()
        else:
            print(c(" Lo ignoras y sigues. El tipo te escupe al pasar.", "dim")); pausa()
    elif r < 0.81:
        dano = random.randint(4, 12)
        estado["salud"] = max(1, estado["salud"] - dano)
        print(c(f" Un perro callejero te muerde en la pierna. -{dano} salud.", "rojoB")); pausa()
    elif r < 0.86:
        print(c(" !! Unos veteranos de Vietnam drogados te confunden con el enemigo !!", "rojoB", "bold"))
        pausa()
        combate_policia(estado)
    elif r < 0.90:
        pago = random.randint(150, 500)
        estado["efectivo"] += pago
        print(c(f" Un periodista del Daily News te paga ${pago} por una historia jugosa.", "verdeB")); pausa()


def viajar(estado):
    print(" A que barrio?")
    destinos = [b for b in BARRIOS if b != estado["barrio"]]
    for i, b in enumerate(destinos, 1):
        print(f"   {i}) {b}")
    s = pedir(" > ")
    if not s.isdigit():
        return False
    idx = int(s) - 1
    if not (0 <= idx < len(destinos)):
        return False
    estado["barrio"] = destinos[idx]
    evento_viaje(estado)
    if estado["salud"] <= 0:
        return True
    avanzar_dia(estado)
    return True


def avanzar_dia(estado):
    estado["dia"] += 1
    estado["deuda"] = int(estado["deuda"] * (1 + INTERES_DEUDA))
    estado["banco"] = int(estado["banco"] * (1 + INTERES_BANCO))
    generar_precios(estado)


def puntaje_final(estado):
    return estado["efectivo"] + estado["banco"] - estado["deuda"]


def pantalla_final(estado, motivo):
    cls()
    ancho = 60
    doble = "\u2550" * ancho
    lado = c("\u2551", "magenta")
    puntaje = puntaje_final(estado)
    estilo_punt = "verdeB" if puntaje > 0 else ("amar" if puntaje == 0 else "rojoB")

    def fila_plana(texto, *estilos):
        pad = ancho - len(texto)
        return lado + c(texto, *estilos) + " " * pad + lado

    def fila_kv(label, val, color_val):
        texto = f" {label}{val}"
        pad = ancho - len(texto)
        return lado + " " + label + c(val, color_val) + " " * pad + lado

    print(c("\u2554" + doble + "\u2557", "magenta"))
    print(fila_plana(f" FIN DE PARTIDA - {motivo}", "bold"))
    print(c("\u2560" + doble + "\u2563", "magenta"))
    print(fila_kv("Efectivo: ", f"${estado['efectivo']}", "verdeB"))
    print(fila_kv("Banco:    ", f"${estado['banco']}", "verde"))
    print(fila_kv("Deuda:    ", f"${estado['deuda']}", "rojoB" if estado["deuda"] > 0 else "dim"))
    print(fila_plana(f" PUNTAJE:  ${puntaje}", estilo_punt, "bold"))
    print(c("\u255A" + doble + "\u255D", "magenta"))
    pausa()


LOGO_DOPE = [
    "  \u2588\u2588\u2588\u2588\u2588\u2588\u2557   \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "  \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D",
    "  \u2588\u2588\u2551  \u2588\u2588\u2551 \u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D \u2588\u2588\u2588\u2588\u2588\u2557  ",
    "  \u2588\u2588\u2551  \u2588\u2588\u2551 \u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2554\u2550\u2550\u2550\u255D  \u2588\u2588\u2554\u2550\u2550\u255D  ",
    "  \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D \u255A\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D \u2588\u2588\u2551      \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "  \u255A\u2550\u2550\u2550\u2550\u2550\u255D   \u255A\u2550\u2550\u2550\u2550\u2550\u255D  \u255A\u2550\u255D      \u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D",
]

LOGO_WARS = [
    "  \u2588\u2588\u2557    \u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "  \u2588\u2588\u2551    \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255D",
    "  \u2588\u2588\u2551 \u2588\u2557 \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
    "  \u2588\u2588\u2551\u2588\u2588\u2588\u2557\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u255A\u2550\u2550\u2550\u2550\u2588\u2588\u2551",
    "  \u255A\u2588\u2588\u2588\u2554\u2588\u2588\u2588\u2554\u255D\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551",
    "   \u255A\u2550\u2550\u2550\u255D\u255A\u2550\u2550\u2550\u255D \u255A\u2550\u255D  \u255A\u2550\u255D\u255A\u2550\u255D  \u255A\u2550\u255D\u255A\u2550\u2550\u2550\u2550\u2550\u2550\u255D",
]


def _caja_linea(texto, ancho, color_txt, color_caja="verdeB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("\u2551", color_caja) + cuerpo + c("\u2551", color_caja)


def splash():
    cls()
    ancho = 60
    print("")
    print(c("\u2554" + "\u2550" * ancho + "\u2557", "verdeB"))
    print(_caja_linea("", ancho, "blanco"))
    for ln in LOGO_DOPE:
        print(_caja_linea(ln, ancho, "amarB"))
    for ln in LOGO_WARS:
        print(_caja_linea(ln, ancho, "amarB"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Clon de Dope Wars / Drug Wars - V2.0", ancho, "cyanB"))
    print(_caja_linea("30 dias. 12 drogas. 6 barrios. Sobrevive.", ancho, "blanco"))
    print(_caja_linea("", ancho, "blanco"))
    print(c("\u255A" + "\u2550" * ancho + "\u255D", "verdeB"))
    print("")
    msg = "Pulsa Enter para empezar..."
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB"))
    try:
        input("")
    except EOFError:
        pass


def jugar():
    random.seed()
    splash()
    estado = nuevo_estado()
    generar_precios(estado)
    while True:
        if estado["salud"] <= 0:
            pantalla_final(estado, "Moriste en la calle")
            return
        if estado["dia"] > DIAS_TOTAL:
            pantalla_final(estado, "Se acabaron los 30 dias")
            return
        dibujar_estado(estado)
        op = menu_principal(estado)
        if op == "C":
            accion_comprar(estado)
        elif op == "V":
            accion_vender(estado)
        elif op == "J":
            viajar(estado)
        elif op == "R":
            resumen(estado)
        elif op == "$" and estado["barrio"] == BARRIO_BANCO:
            accion_banco(estado)
        elif op == "P" and estado["barrio"] == BARRIO_BANCO:
            accion_prestamista(estado)
        elif op == "H" and estado["barrio"] == BARRIO_BANCO:
            accion_hospital(estado)
        elif op == "S":
            if prompt_si_no(" Seguro que quieres salir?"):
                pantalla_final(estado, "Abandonaste la partida")
                return


if __name__ == "__main__":
    try:
        jugar()
    except KeyboardInterrupt:
        print("\n Partida interrumpida.")
        sys.exit(0)
