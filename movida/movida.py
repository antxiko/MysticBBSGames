#!/usr/bin/env python3
"""Movida - aventura conversacional castiza-punk del Madrid del 85.

Sabado noche. Despertaste tarde, hay after legendario en una nave de Vallecas, club
kinky-punk. Para entrar el portero te pedira tres cosas. Tienes la noche por delante.
"""
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


COLS = 80
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_TOP = 10
ASCENDING = True  # True si menos = mejor

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
    p = "".join(COLORES[e] for e in estilos if e in COLORES)
    return f"{p}{txt}{RESET}" if p else str(txt)


def cls():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def pwrap(texto, ancho=COLS - 2, color=None):
    """Imprime texto envuelto a ancho dado."""
    import textwrap
    for parrafo in texto.split("\n"):
        if not parrafo.strip():
            print()
            continue
        for ln in textwrap.wrap(parrafo, width=ancho):
            print(c(ln, color) if color else ln)


# ---------- ITEMS ----------

ITEMS = {
    "vinilo": {
        "nombre": "vinilo",
        "desc": "Un single de los Sex Pistols. Rayado, salta a la mitad de 'Anarchy in the UK'. Vale algo si lo vendes a un coleccionista.",
        "alias": ["vinilo", "disco", "pistols", "single"],
    },
    "chupa": {
        "nombre": "chupa de cuero",
        "desc": "Tu chupa de cuero. Lleva chapas de los Stooges, los Eskorbuto y un imperdible cosido en la solapa. Marca personalidad.",
        "alias": ["chupa", "chaqueta", "cazadora", "cuero"],
    },
    "porro": {
        "nombre": "porro a medias",
        "desc": "Un canuto a medio fumar que dejo Marichu en el cenicero. Aun tira.",
        "alias": ["porro", "canuto", "petardo"],
    },
    "maquillaje": {
        "nombre": "pintalabios",
        "desc": "Un pintalabios rojo Helena Rubinstein, casi nuevo. De Marichu.",
        "alias": ["maquillaje", "pintalabios", "barra", "labial"],
    },
    "baraja": {
        "nombre": "baraja de poker",
        "desc": "Una baraja de poker pringosa de cerveza. 52 cartas, todas.",
        "alias": ["baraja", "cartas"],
    },
    "sortija": {
        "nombre": "sortija de plata",
        "desc": "Sortija de plata pesada, con una calavera tallada. Lo dejaria todo cualquier coleccionista por esto.",
        "alias": ["sortija", "anillo"],
    },
    "libro": {
        "nombre": "libro firmado",
        "desc": "Edicion de bolsillo de 'La colmena' de Camilo Jose Cela, firmada con su apellido garabateado en la portadilla. Vale una fortuna pequeña.",
        "alias": ["libro", "cela", "colmena"],
    },
    "vibrador": {
        "nombre": "vibrador rosa",
        "desc": "Vibrador rosa chillon. Made in Sweden 1975, leyenda urbana entre coleccionistas kinky. Aun funciona.",
        "alias": ["vibrador", "consolador", "juguete"],
    },
}


def item_por_alias(palabra):
    """Devuelve la key del item que matchea con la palabra dada, o None."""
    palabra = palabra.lower().strip()
    if not palabra:
        return None
    for k, it in ITEMS.items():
        if palabra == k or palabra in it["alias"]:
            return k
    return None


# ---------- HABITACIONES ----------

HABITACIONES = {
    "cuarto": {
        "nombre": "Tu cuartucho",
        "desc": ("Tu cuarto del piso compartido de la calle del Pez. Un colchon en el suelo, "
                 "un poster de Sid Vicious pegado con chinchetas, humedad en una esquina y "
                 "un tocadiscos Bettor con un vinilo encima. El despertador marca las 22:00. "
                 "Sabado noche, tienes una noche por delante."),
        "salidas": {"oeste": "salon", "norte": "bano"},
        "items": ["vinilo", "chupa"],
    },
    "bano": {
        "nombre": "Bano del piso",
        "desc": ("Un bano diminuto, azulejos rotos, una bombilla pelona. Espejo manchado. "
                 "En la repisa del lavabo hay un pintalabios."),
        "salidas": {"sur": "cuarto"},
        "items": ["maquillaje"],
    },
    "salon": {
        "nombre": "Salon del piso",
        "desc": ("Salon de piso compartido nivel desastre: ceniceros llenos, una mesa con "
                 "cervezas vacias, un sofa naranja roñoso y Marichu hablando sola con un "
                 "porro en el cenicero. La puerta da al portal."),
        "salidas": {"este": "cuarto", "sur": "portal"},
        "items": ["porro"],
        "npc": "marichu",
    },
    "portal": {
        "nombre": "Portal del edificio",
        "desc": ("Un portal cutre con buzones rotos y olor a meado de gato. La portera "
                 "duerme. La puerta a la calle esta entornada."),
        "salidas": {"norte": "salon", "sur": "calle_pez"},
        "items": [],
    },
    "calle_pez": {
        "nombre": "Calle del Pez",
        "desc": ("La calle del Pez, corazon de Malasaña. Hay punkis fumando en la acera, "
                 "una pareja besandose contra una persiana echada y un perro meando un "
                 "buzon. La noche huele a tabaco negro y aceite quemado."),
        "salidas": {
            "norte": "plaza_2mayo",
            "sur": "gran_via",
            "este": "bar_via_lactea",
            "oeste": "callejon_malasana",
            "arriba": "portal",
        },
        "items": [],
    },
    "plaza_2mayo": {
        "nombre": "Plaza del 2 de Mayo",
        "desc": ("La 2 de Mayo a tope: corros de gente sentada en el suelo, guitarras, "
                 "olor a hachis, una panda de skins jugando al futbol con una lata. "
                 "El Pichi esta apoyado en la estatua, como siempre."),
        "salidas": {"sur": "calle_pez"},
        "items": [],
        "npc": "pichi",
    },
    "bar_via_lactea": {
        "nombre": "Bar La Via Lactea",
        "desc": ("El bar mitico de Malasaña: humo a la altura de los ojos, foto de Iggy "
                 "Pop en la pared, una mesa al fondo con un grupo jugando al poker y el "
                 "Antonio detras de la barra sirviendo cubatas a 200 pelas."),
        "salidas": {"oeste": "calle_pez"},
        "items": [],
        "npc": "antonio",
    },
    "callejon_malasana": {
        "nombre": "Callejon oscuro",
        "desc": ("Un callejon sin salida entre dos edificios, oscuro como boca de lobo. "
                 "Apesta a basura. Algo se mueve al fondo. Pequeña sombra."),
        "salidas": {"este": "calle_pez"},
        "items": [],
    },
    "gran_via": {
        "nombre": "Gran Via",
        "desc": ("La Gran Via a las once: prostitutas en cada portal, taxis amarillos, "
                 "luces de neon del cine Avenida proyectando un anuncio de 'Caso "
                 "cerrado'. Sigue para abajo hasta Sol o tira a Chueca."),
        "salidas": {"norte": "calle_pez", "este": "chueca", "sur": "lavapies"},
        "items": [],
    },
    "chueca": {
        "nombre": "Plaza de Chueca",
        "desc": ("Plaza de Chueca, terraza de un bar con un toldo verde. Tres drag queens "
                 "muy maquilladas estan sentadas en la fuente fumando. Yvonne, la mas "
                 "alta, te clava la mirada al verte llegar."),
        "salidas": {"oeste": "gran_via", "norte": "sex_shop"},
        "items": [],
        "npc": "yvonne",
    },
    "sex_shop": {
        "nombre": "Sex Shop El Templo",
        "desc": ("Una tienda con escaparate tapado por papel kraft. Dentro: una lampara "
                 "roja, estanterias con consoladores y revistas, olor a goma. Casto, el "
                 "dueño, esta detras del mostrador leyendo el Pais."),
        "salidas": {"sur": "chueca", "este": "backroom"},
        "items": [],
        "npc": "casto",
    },
    "backroom": {
        "nombre": "Backroom",
        "desc": ("Una habitacion al fondo del sex shop, separada por una cortina de "
                 "cuentas. Luz roja, un sofa de polipiel, un poster de Tom of Finland. "
                 "Aqui Casto guarda las piezas raras."),
        "salidas": {"oeste": "sex_shop"},
        "items": [],
    },
    "lavapies": {
        "nombre": "Plaza de Lavapies",
        "desc": ("Plaza de Lavapies, gente bebiendo en la calle, un puesto de churros "
                 "humeando, dos guardias paseando con desgana. Las callejuelas se "
                 "ramifican en todas direcciones."),
        "salidas": {
            "norte": "gran_via",
            "oeste": "rastro",
            "este": "casa_murci",
            "sur": "bar_tito",
            "abajo": "boca_metro",
        },
        "items": [],
    },
    "bar_tito": {
        "nombre": "Bar de Tito",
        "desc": ("Un bar de barrio con suelo de baldosa marron, fluorescente roto, una "
                 "tele en blanco y negro con los toros sin sonido. Tito, gordo, calvo y "
                 "con bigote, te recibe sin sonreir desde la barra."),
        "salidas": {"norte": "lavapies"},
        "items": [],
        "npc": "tito",
    },
    "casa_murci": {
        "nombre": "Piso del Murci",
        "desc": ("Un piso compartido en la cuarta planta, sin luz. Telarañas en el techo, "
                 "papel pintado de los 60 medio caido. Murci esta tirado en el sofa, "
                 "los ojos a media asta, viendo Murcia TV en blanco y negro."),
        "salidas": {"oeste": "lavapies"},
        "items": [],
        "npc": "murci",
    },
    "rastro": {
        "nombre": "Sastreria del Rastro",
        "desc": ("Una sastreria diminuta en una calleja del Rastro, abierta de noche "
                 "porque Don Sebas no duerme. Maquinas Singer antiguas, retales por "
                 "todas partes, un maniqui sin cabeza con un esmoquin a medias. Don "
                 "Sebas te observa por encima de las gafas."),
        "salidas": {"este": "lavapies", "sur": "merceria"},
        "items": [],
        "npc": "sebas",
    },
    "merceria": {
        "nombre": "Calle de la merceria",
        "desc": ("Una calleja con una mercería cerrada a cal y canto. En la ventana de "
                 "encima asoma una vieja con un moño y unas bata de cuadros, mirando la "
                 "calle por aburrimiento. Tiene pinta de no dormir nunca."),
        "salidas": {"norte": "rastro"},
        "items": [],
        "npc": "vieja",
    },
    "boca_metro": {
        "nombre": "Boca de metro cerrada",
        "desc": ("Una boca de metro tapiada con tablones medio caidos. Pone 'CERRADO' "
                 "con espray. Por las rendijas sale un eco rumor de musica electronica. "
                 "Un sereno gordo con linterna y porra esta plantado delante."),
        "salidas": {"arriba": "lavapies", "abajo": "tunel"},
        "items": [],
        "npc": "sereno",
    },
    "tunel": {
        "nombre": "Tunel abandonado",
        "desc": ("Un tunel de metro fuera de servicio. Cables sueltos, charcos, eco. "
                 "Alguien ha pintado 'NO FUTURE' con espray morado. La musica viene de "
                 "una puerta de hierro al fondo, con luz roja por las rendijas."),
        "salidas": {"arriba": "boca_metro", "sur": "portero_club"},
        "items": [],
    },
    "portero_club": {
        "nombre": "Puerta del club",
        "desc": ("Una puerta de hierro pintada de negro. Delante, un portero metro "
                 "noventa, calvo, con un pendiente. Se llama Bigote-Polla por algun "
                 "motivo. Te mira de arriba a abajo."),
        "salidas": {"norte": "tunel"},
        "items": [],
        "npc": "portero",
    },
    "interior_club": {
        "nombre": "Interior del After",
        "desc": ("Has entrado. La sala es un sotano enorme con luces estroboscopicas, "
                 "musica electronica a tope, gente vestida de cuero y latex bailando, "
                 "una barra al fondo con bebidas raras y al fondo... la pista del backroom. "
                 "Has llegado al after. Te has ganado la noche."),
        "salidas": {},
        "items": [],
    },
}


# ---------- NPCs y sus dialogos ----------

def dialogo_marichu(est):
    if "marichu_te_aviso" not in est.flags:
        est.flags.add("marichu_te_aviso")
        return ("Marichu te ve y suelta humo: 'Punki, llevas dormido seis horas. "
                "Ha llamado el Pichi: hay after en una nave de Vallecas, club kinky, "
                "se entra por la boca cerrada de Lavapies. Tienes que demostrar al "
                "portero que vales la pena - tres cosas raras y palabra de paso.'\n\n"
                "'Por mi parte: hay porro en el cenicero, no me lo agradezcas. Y "
                "pintate algo que vas mas soso que un funcionario.'")
    return ("Marichu se rie: 'Que pasa, el Sid Vicious sin gomina. Tira pa Lavapies, "
            "anda, que el after cierra a las tantas y tu fauna esta en la calle.'")


def dialogo_pichi(est):
    if "pichi_te_aviso" not in est.flags:
        est.flags.add("pichi_te_aviso")
        est.inventario.add("baraja")
        return ("El Pichi te ve y se rie. Lleva una cresta naranja gigante. 'Punki, "
                "que tarde. El after de Vallecas se monta abajo de Lavapies, en el "
                "tunel viejo. Portero pide tres cosas: algo que llamarian de coleccion "
                "los pijos, dinero - de verdad, no calderilla, minimo cinco mil pelas - "
                "y la palabra de paso. La palabra solo la suelta Don Sebas, en el "
                "Rastro - o convences a Yvonne en Chueca con algo bonito.'\n\n"
                "El Pichi rebusca en el bolsillo y te tira una baraja: 'Toma. Si vas "
                "a La Via Lactea con esto, el Antonio te mete en la timba.'")
    return ("El Pichi suelta humo: 'Tira tira, que el after no espera.'")


def dialogo_antonio(est):
    if "tienes_pelas_suficientes" in est.flags:
        return "Antonio te guiña: 'Buena timba, punki. Tira pa lo tuyo.'"
    if "baraja" in est.inventario:
        return ("Antonio te mira la baraja en la mano: 'Si quieres jugar, sientate en "
                "la mesa del fondo. Se entra con quinientas pelas, el bote se queda "
                "quien gane. (Para jugar: USA BARAJA en este bar.)'")
    return ("Antonio: 'Punki, que va. Tomas algo o te vas? Si tuvieras una baraja te "
            "metiamos en la mesa del fondo.'")


def dialogo_yvonne(est):
    if "yvonne_te_dio_palabra" in est.flags:
        return "Yvonne te lanza un beso: 'Vete a triunfar, princesa.'"
    if "maquillaje" in est.inventario:
        return ("Yvonne pinta sus uñas mientras habla: 'A ver chiquillo, si me pasas "
                "ese pintalabios y me dejas darle una pasada, te susurro la palabra "
                "que necesitas. (DAR PINTALABIOS para entregar.)'")
    return ("Yvonne te mira de arriba a abajo: 'Pichabrava, llegas a Chueca pidiendo "
            "favores y vienes a palo seco. Vuelve cuando tengas algo bonito que "
            "ofrecerle a una señora.'")


def dialogo_casto(est):
    if "vibrador" in est.inventario:
        return "Casto te guiña: 'Disfrutalo, fierecilla. Y traemelo entero si lo devuelves.'"
    if "libro" in est.inventario:
        return ("Casto: 'Pero qué veo. Un Cela firmado de verdad. Trato es trato: te "
                "abro el backroom. La llave esta debajo del mostrador. (USA LLAVE en "
                "el backroom.)'")
    if "casto_oferta_hecha" not in est.flags:
        est.flags.add("casto_oferta_hecha")
        return ("Casto te ve y deja el periodico. 'Mira quien viene a verme. Lo que "
                "buscas pa el portero esta detras de la cortina: tengo el vibrador "
                "rosa del 75, Made in Sweden, original. Vintage del bueno. Te lo "
                "cambio por un libro de Cela firmado - el Tito de Lavapies tenia uno "
                "antes de empeñarlo todo.'")
    return ("Casto: 'Sin libro no hay vibrador, mariquita. Tira p'al bar de Tito.'")


def dialogo_tito(est):
    if "libro" in est.inventario or "tito_te_dio_libro" in est.flags:
        return "Tito apenas levanta la cabeza: 'Trato hecho, punki. Vete.'"
    if "sortija" in est.inventario:
        return ("Tito se incorpora: 'La sortija. Joder, no creia que la recuperaras. "
                "Te debo: tengo un Cela firmado en la trastienda. Damelo y te lo "
                "cambio. (DAR SORTIJA para cerrar el trato.)'")
    if "tito_oferta_hecha" not in est.flags:
        est.flags.add("tito_oferta_hecha")
        return ("Tito te mira sin sonreir: 'Que coño quieres. Mira: si me traes la "
                "sortija que el Murci me birlo el otro dia, te doy un libro firmado "
                "por Cela que tengo guardado. Vive en el cuarto piso de la calle "
                "Argumosa, el Murci.'")
    return ("Tito: 'Sin sortija no hablamos.'")


def dialogo_murci(est):
    if "murci_te_dio_sortija" in est.flags:
        return "Murci masculla algo y vuelve a la tele."
    if "porro" in est.inventario:
        return ("Murci abre un ojo: 'Eso es un porro? Punki, dame eso. Si me lo das, "
                "te doy lo que sea. Tengo una sortija del Tito por ahi, en el cajon. "
                "(DAR PORRO para canjear.)'")
    return ("Murci esta tirado, los ojos a media asta. 'Que te pasa nano. Aqui no "
            "hay na que rascar. Llevate algo? Tu di que si tienes algo de hierba y "
            "hablamos.'")


def dialogo_sebas(est):
    if "yvonne_te_dio_palabra" in est.flags or "sebas_te_dio_palabra" in est.flags:
        return "Don Sebas asiente: 'Suerte ahi abajo.'"
    if "sebas_te_examino" not in est.flags:
        est.flags.add("sebas_te_examino")
        return ("Don Sebas baja las gafas: 'Tu eres el chico de Marichu. Buscas la "
                "palabra. La sabe la Yvonne en Chueca tambien, si te llevas con ella. "
                "O te la doy yo si me arreglas un asunto con la vieja de la merceria - "
                "tira para la calle de abajo, esta en la ventana, no abre. Si te "
                "consigues que te tire la tela del bies te susurro la palabra al "
                "vuelta.'")
    return ("Don Sebas: 'Tela del bies, hijo. O hablate con la Yvonne. No te llevo a "
            "tomar por culo, pero me ocupas la trastienda.'")


def dialogo_vieja(est):
    if "vieja_te_tiro_tela" in est.flags:
        return "La vieja te saluda con la mano y se mete pa dentro."
    return ("La vieja te mira y suelta un suspiro larguisimo: 'Ay, hijo, vete a "
            "dormir que estas en edad. No abro a estas horas. Si quieres algo te "
            "lo digo de aqui arriba: que necesitas?'\n\n"
            "(Esta vieja parece imposible. La Yvonne sabra otro camino.)")


def dialogo_sereno(est):
    if "sereno_paso_libre" in est.flags:
        return "El sereno bosteza y mira a otro lado."
    return ("El sereno te mira con cara de palo: 'Aqui no se baja, niño. Cierre "
            "oficial. (Si tienes la palabra de paso, intenta USARLA aqui o pasa "
            "directamente cuando la sepas: ir abajo.)'")


def dialogo_portero(est):
    cumplidos = []
    falta = []
    if "vibrador" in est.inventario:
        cumplidos.append("el juguete vintage")
    else:
        falta.append("algo raro de coleccionista")
    if est.pelas >= 5000:
        cumplidos.append("la pasta")
    else:
        falta.append("cinco mil pelas")
    if "yvonne_te_dio_palabra" in est.flags or "sebas_te_dio_palabra" in est.flags:
        cumplidos.append("la palabra")
    else:
        falta.append("la palabra de paso")
    if not falta:
        est.flags.add("portero_te_dejo_pasar")
        return ("Bigote-Polla te repasa de arriba abajo. 'Joder, lo traes todo. "
                "Cinco mil cuesta, dame la pasta y pasa. (DAR PELAS o USA PELAS aqui.)'")
    return ("Bigote-Polla te mira: 'Sin chorradas, punki. Necesito tres cosas y a "
            "ti te falta: " + ", ".join(falta) + ". Vuelve cuando lo tengas.'")


DIALOGOS = {
    "marichu": dialogo_marichu,
    "pichi": dialogo_pichi,
    "antonio": dialogo_antonio,
    "yvonne": dialogo_yvonne,
    "casto": dialogo_casto,
    "tito": dialogo_tito,
    "murci": dialogo_murci,
    "sebas": dialogo_sebas,
    "vieja": dialogo_vieja,
    "sereno": dialogo_sereno,
    "portero": dialogo_portero,
}


# ---------- ESTADO ----------

class Estado:
    def __init__(self):
        self.ubicacion = "cuarto"
        self.inventario = set()
        self.pelas = 500
        self.flags = set()
        self.turnos = 0
        self.fin = None  # "exito", "fracaso", "muerto"

    def tiene(self, k):
        return k in self.inventario


# ---------- HELPERS ----------

DIRECCIONES_ALIAS = {
    "n": "norte", "norte": "norte",
    "s": "sur", "sur": "sur",
    "e": "este", "este": "este",
    "o": "oeste", "oeste": "oeste", "w": "oeste",
    "ar": "arriba", "arriba": "arriba", "up": "arriba",
    "ab": "abajo", "abajo": "abajo", "down": "abajo",
}

VERBO_ALIAS = {
    "i": "inventario", "inv": "inventario", "inventario": "inventario",
    "m": "mirar", "mira": "mirar", "mirar": "mirar", "ver": "mirar",
    "ex": "examinar", "examina": "examinar", "examinar": "examinar",
    "coger": "coger", "pillar": "coger", "birlar": "coger", "agarrar": "coger",
    "soltar": "dejar", "dejar": "dejar", "tirar": "dejar",
    "hablar": "hablar", "habla": "hablar", "preguntar": "hablar",
    "dar": "dar", "entregar": "dar", "regalar": "dar", "ofrecer": "dar",
    "usar": "usar", "usa": "usar", "abrir": "usar",
    "ir": "ir", "andar": "ir", "caminar": "ir", "moverse": "ir",
    "leer": "leer",
    "fumar": "fumar",
    "salir": "salir", "quit": "salir",
    "ayuda": "ayuda", "help": "ayuda", "?": "ayuda",
    "esperar": "esperar", "espera": "esperar",
    "pegar": "pegar",
}


def mostrar_habitacion(est, breve=False):
    h = HABITACIONES[est.ubicacion]
    print()
    print(c("─" * COLS, "magenta"))
    print(c(" " + h["nombre"].upper(), "amarB", "bold"))
    print(c("─" * COLS, "magenta"))
    if not breve:
        pwrap(h["desc"])
    items = [k for k in h["items"] if k != "_taken"]
    if items:
        nombres = ", ".join(ITEMS[k]["nombre"] for k in items)
        print(c(f"\nVes aqui: {nombres}.", "cyanB"))
    npc = h.get("npc")
    if npc:
        print(c(f"Hay alguien aqui: {npc.capitalize()}.", "verdeB"))
    salidas = ", ".join(h["salidas"].keys())
    print(c(f"\nSalidas: {salidas}", "dim"))


# ---------- ACCIONES ----------

def accion_ir(est, obj):
    h = HABITACIONES[est.ubicacion]
    d = DIRECCIONES_ALIAS.get(obj)
    if d and d in h["salidas"]:
        destino = h["salidas"][d]
        # logica especial: bajar al tunel requiere palabra (a traves del sereno)
        if est.ubicacion == "boca_metro" and d == "abajo":
            if "yvonne_te_dio_palabra" in est.flags or "sebas_te_dio_palabra" in est.flags:
                est.flags.add("sereno_paso_libre")
                print(c("Sueltas la palabra de paso entre dientes. El sereno se aparta "
                        "sin levantar la vista. Bajas al tunel.", "verdeB"))
            else:
                print(c("El sereno te corta el paso con la porra. 'Sin palabra no hay "
                        "fiesta.'", "rojoB"))
                return
        est.ubicacion = destino
        mostrar_habitacion(est)
        chequear_eventos(est)
        return
    # nombre directo de habitacion?
    for k, dest in h["salidas"].items():
        if obj.lower() in HABITACIONES[dest]["nombre"].lower():
            est.ubicacion = dest
            mostrar_habitacion(est)
            chequear_eventos(est)
            return
    print(c("No puedes ir por ahi.", "dim"))


def accion_coger(est, obj):
    if not obj:
        print(c("Coger que?", "dim"))
        return
    h = HABITACIONES[est.ubicacion]
    k = item_por_alias(obj)
    if k and k in h["items"]:
        h["items"].remove(k)
        est.inventario.add(k)
        print(c(f"Coges {ITEMS[k]['nombre']}.", "verdeB"))
        return
    print(c("No veo eso por aqui.", "dim"))


def accion_dejar(est, obj):
    k = item_por_alias(obj)
    if k and k in est.inventario:
        est.inventario.remove(k)
        HABITACIONES[est.ubicacion]["items"].append(k)
        print(c(f"Dejas {ITEMS[k]['nombre']} en el suelo.", "verdeB"))
        return
    print(c("No llevas eso.", "dim"))


def accion_mirar(est, obj):
    if not obj:
        mostrar_habitacion(est)
        return
    k = item_por_alias(obj)
    if k:
        if k in est.inventario or k in HABITACIONES[est.ubicacion]["items"]:
            pwrap(ITEMS[k]["desc"])
            return
    print(c("No ves eso aqui.", "dim"))


def accion_examinar(est, obj):
    accion_mirar(est, obj)


def accion_inventario(est, obj):
    if not est.inventario:
        print(c("No llevas nada en los bolsillos.", "dim"))
    else:
        nombres = ", ".join(ITEMS[k]["nombre"] for k in est.inventario)
        print(c(f"Llevas: {nombres}.", "cyanB"))
    print(c(f"Pelas: {est.pelas}", "amarB"))


def accion_hablar(est, obj):
    h = HABITACIONES[est.ubicacion]
    npc = h.get("npc")
    if not npc:
        print(c("No hay nadie con quien hablar aqui.", "dim"))
        return
    texto = DIALOGOS[npc](est)
    print()
    pwrap(texto, color="blancoB")


def accion_dar(est, obj):
    if not obj:
        print(c("Dar que?", "dim"))
        return
    # parsing "dar X a Y" o solo "dar X"
    palabras = obj.split()
    if "a" in palabras:
        idx = palabras.index("a")
        item_part = " ".join(palabras[:idx])
    else:
        item_part = obj
    k = item_por_alias(item_part)
    if not k:
        # quizas es pelas
        if item_part in ("pelas", "dinero", "pasta"):
            return _dar_pelas(est)
        print(c("No llevas eso.", "dim"))
        return
    if k not in est.inventario:
        print(c("No llevas eso.", "dim"))
        return
    h = HABITACIONES[est.ubicacion]
    npc = h.get("npc")
    if not npc:
        print(c("No hay nadie a quien darselo.", "dim"))
        return
    # tabla de canjes
    return _resolver_canje(est, npc, k)


def _resolver_canje(est, npc, k):
    if npc == "murci" and k == "porro":
        est.inventario.remove("porro")
        est.inventario.add("sortija")
        est.flags.add("murci_te_dio_sortija")
        print(c("Le pasas el porro. Murci sonrie con dos dientes, rebusca en el cajon "
                "y te tira la sortija. 'Buen niño.'", "verdeB"))
        return
    if npc == "tito" and k == "sortija":
        est.inventario.remove("sortija")
        est.inventario.add("libro")
        est.flags.add("tito_te_dio_libro")
        print(c("Tito coge la sortija, la besa y la mete en el delantal. Sale a la "
                "trastienda y vuelve con el libro firmado. 'Vete que tengo cosas.'", "verdeB"))
        return
    if npc == "casto" and k == "libro":
        est.inventario.remove("libro")
        est.inventario.add("vibrador")
        est.flags.add("casto_te_dio_vibrador")
        print(c("Casto agarra el libro con manos temblorosas, lo abre por la firma, "
                "casi llora. Te pasa el vibrador rosa envuelto en una bolsa de "
                "Sepu. 'Esto es historia, niño.'", "verdeB"))
        return
    if npc == "yvonne" and k == "maquillaje":
        est.inventario.remove("maquillaje")
        est.flags.add("yvonne_te_dio_palabra")
        print(c("Yvonne se pinta los labios con tu pintalabios, te mira al espejo "
                "imaginario y se lo guarda. Se inclina y te susurra al oido: "
                "'PUNKARRABIA. Dilo bajito cuando llegues. Y triunfa, mi niño.'", "magentaB"))
        return
    if npc == "portero" and k == "vibrador":
        if est.pelas >= 5000 and ("yvonne_te_dio_palabra" in est.flags or "sebas_te_dio_palabra" in est.flags):
            print(c("Bigote-Polla examina el vibrador, asiente impresionado, se "
                    "guarda las cinco mil pelas en el delantal y te abre la puerta. "
                    "'Adentro, fierecilla.'", "verdeB"))
            est.pelas -= 5000
            est.inventario.remove("vibrador")
            est.ubicacion = "interior_club"
            mostrar_habitacion(est)
            est.fin = "exito"
            return
        else:
            print(c("Bigote-Polla mira el vibrador con interes pero te corta: 'Esto "
                    "esta bien, pero faltan otras cosas. No me hagas perder el "
                    "tiempo.'", "rojoB"))
            return
    print(c(f"A {npc.capitalize()} no parece interesarle.", "dim"))


def _dar_pelas(est):
    h = HABITACIONES[est.ubicacion]
    npc = h.get("npc")
    if npc == "portero":
        if est.pelas < 5000:
            print(c("Bigote-Polla cuenta tu calderilla y se rie. 'Vuelve cuando "
                    "tengas pasta de verdad.'", "rojoB"))
            return
        if "vibrador" not in est.inventario:
            print(c("Bigote-Polla: 'Necesito algo raro tambien, no solo pasta.'", "rojoB"))
            return
        if "yvonne_te_dio_palabra" not in est.flags and "sebas_te_dio_palabra" not in est.flags:
            print(c("Bigote-Polla: 'Y la palabra de paso, punki. Tira de Chueca.'", "rojoB"))
            return
        # todos cumplidos
        est.pelas -= 5000
        est.inventario.remove("vibrador")
        est.ubicacion = "interior_club"
        mostrar_habitacion(est)
        est.fin = "exito"
        return
    print(c("Aqui no.", "dim"))


def accion_usar(est, obj):
    if not obj:
        print(c("Usar que?", "dim"))
        return
    k = item_por_alias(obj)
    if not k:
        # acciones especiales sin item
        if obj in ("tela",):
            print(c("Para conseguir la tela del bies habla con la vieja de la "
                    "merceria - o atajo: convence a Yvonne en Chueca.", "dim"))
            return
        print(c("No tienes eso.", "dim"))
        return
    if k not in est.inventario:
        print(c("No llevas eso.", "dim"))
        return
    # baraja en bar
    if k == "baraja" and est.ubicacion == "bar_via_lactea":
        if "tienes_pelas_suficientes" in est.flags:
            print(c("Ya jugaste tu partida. Antonio te indica que la timba esta "
                    "cerrada por hoy.", "dim"))
            return
        if est.pelas < 500:
            print(c("Antonio te corta: 'Pa entrar a la mesa hacen falta quinientas "
                    "pelas, punki.'", "rojoB"))
            return
        return _jugar_poker(est)
    if k == "vinilo" and est.ubicacion == "rastro":
        est.inventario.remove("vinilo")
        est.pelas += 3000
        print(c("Vendes el vinilo a un buscavidas que pasaba por la sastreria. "
                "Tres mil pelas en la mano.", "verdeB"))
        if est.pelas >= 5000:
            est.flags.add("tienes_pelas_suficientes")
        return
    if k == "chupa":
        print(c("La chupa te queda mejor puesta. No te la quites a menos que "
                "te la pidan.", "dim"))
        return
    print(c("No puedes usar eso aqui.", "dim"))


def _jugar_poker(est):
    import random
    print(c("Te sientas a la mesa. Antonio reparte. Cinco cartas a cada uno. "
            "Suena 'Hotel California' en el tocadiscos del bar.", "amarB"))
    # tirada aleatoria, ponderada
    tirada = random.random()
    if tirada < 0.55:
        # ganas
        est.pelas += 4500  # tu eras 500, ganas 4500 mas
        print(c("Vas de farol con doble pareja y te llevas el bote. Cuatro mil "
                "quinientas pelas.", "verdeB"))
        est.flags.add("tienes_pelas_suficientes")
    elif tirada < 0.85:
        # pierdes algo
        perdida = min(est.pelas, 300)
        est.pelas -= perdida
        print(c(f"Vas con escalera de color, pero el chino del fondo te clava un "
                f"poker. Te bajan {perdida} pelas. Antonio te invita a cubata para "
                f"que no llores.", "rojoB"))
    else:
        # gran palo
        perdida = min(est.pelas, 500)
        est.pelas -= perdida
        print(c(f"Pierdes los {perdida} pavos de la entrada. Antonio te empuja "
                f"fuera de la mesa.", "rojoB"))


def accion_leer(est, obj):
    k = item_por_alias(obj)
    if k == "libro" and k in est.inventario:
        pwrap(ITEMS[k]["desc"])
        return
    print(c("Aqui no hay nada que leer.", "dim"))


def accion_fumar(est, obj):
    if "porro" in est.inventario and (not obj or item_por_alias(obj) == "porro"):
        print(c("Te enciendes el porro. Notas como te quedas mas a gusto pero menos "
                "espabilado. Se acaba enseguida.", "magentaB"))
        est.inventario.remove("porro")
        return
    print(c("No tienes nada que fumar.", "dim"))


def accion_pegar(est, obj):
    if est.ubicacion == "callejon_malasana":
        print(c("Sueltas un puñetazo al aire en la oscuridad. Te contestan con tres. "
                "Te trincan, te rajan, te dejan en el suelo. Game over, punki.", "rojoB"))
        est.fin = "muerto"
        return
    if est.ubicacion == "portero_club":
        print(c("Pegas a Bigote-Polla. Antes de que llegue a la cara, te ha tirado al "
                "suelo y te ha pisado la mano. Vuelves a la calle sin entrar y sin "
                "ganas de volver.", "rojoB"))
        est.fin = "fracaso"
        return
    print(c("Aqui no hay a quien pegar.", "dim"))


def accion_esperar(est, obj):
    print(c("Esperas un poco. Pasan unos coches. La noche avanza.", "dim"))


def accion_salir(est, obj):
    print(c("Saliendo. Hasta luego, punki.", "amarB"))
    sys.exit(0)


def accion_ayuda(est, obj):
    print(c("\nVerbos: ir, coger, dejar, mirar, examinar, hablar, dar, usar, leer, "
            "fumar, inventario, esperar, salir.", "cyanB"))
    print(c("Direcciones: norte/n, sur/s, este/e, oeste/o, arriba/ar, abajo/ab.", "cyanB"))
    print(c("Ejemplos: 'coger porro', 'dar porro a murci', 'hablar', 'ir norte', 'n'.", "dim"))


VERBOS = {
    "ir": accion_ir,
    "coger": accion_coger,
    "dejar": accion_dejar,
    "mirar": accion_mirar,
    "examinar": accion_examinar,
    "inventario": accion_inventario,
    "hablar": accion_hablar,
    "dar": accion_dar,
    "usar": accion_usar,
    "leer": accion_leer,
    "fumar": accion_fumar,
    "pegar": accion_pegar,
    "esperar": accion_esperar,
    "ayuda": accion_ayuda,
    "salir": accion_salir,
}


# ---------- EVENTOS y comprobaciones globales ----------

def chequear_eventos(est):
    # actualizacion automatica de flag pelas
    if est.pelas >= 5000:
        est.flags.add("tienes_pelas_suficientes")
    else:
        est.flags.discard("tienes_pelas_suficientes")


# ---------- PARSER ----------

def parse(cmd):
    cmd = cmd.lower().strip()
    if not cmd:
        return None, None
    # direcciones solas
    if cmd in DIRECCIONES_ALIAS:
        return "ir", DIRECCIONES_ALIAS[cmd]
    palabras = cmd.split()
    verbo_raw = palabras[0]
    obj = " ".join(palabras[1:])
    verbo = VERBO_ALIAS.get(verbo_raw)
    if verbo is None:
        return None, cmd
    return verbo, obj


# ---------- SCORES (simple: turnos para ganar; menos turnos = mejor) ----------

# ---------- SPLASH y finales ----------

LOGO_MOVIDA = [
    "███╗   ███╗ ██████╗ ██╗   ██╗██╗██████╗  █████╗ ",
    "████╗ ████║██╔═══██╗██║   ██║██║██╔══██╗██╔══██╗",
    "██╔████╔██║██║   ██║██║   ██║██║██║  ██║███████║",
    "██║╚██╔╝██║██║   ██║╚██╗ ██╔╝██║██║  ██║██╔══██║",
    "██║ ╚═╝ ██║╚██████╔╝ ╚████╔╝ ██║██████╔╝██║  ██║",
    "╚═╝     ╚═╝ ╚═════╝   ╚═══╝  ╚═╝╚═════╝ ╚═╝  ╚═╝",
]


def _caja_linea(texto, ancho, color_txt, color_caja="magentaB"):
    pad = ancho - len(texto)
    pad_l = pad // 2
    pad_r = pad - pad_l
    cuerpo = " " * pad_l + c(texto, color_txt) + " " * pad_r if texto else " " * ancho
    return c("║", color_caja) + cuerpo + c("║", color_caja)


MANUAL_LINEAS = [
    ('PREMISA', 'cyanB', 'bold'),
    '  Aventura conversacional ambientada en Madrid 1985 (la Movida).',
    '  Sabado noche. Hay after kinky-punk secreto en una nave de Vallecas.',
    '  El portero te pide tres cosas para dejarte pasar.',
    '  22 habitaciones, 11 personajes, 3 cadenas de puzzles.',
    '',
    ('CONTROLES (line-mode + Enter)', 'cyanB', 'bold'),
    '  Escribes en español comandos verbo+sustantivo, p.ej:',
    '    coger porro      dar maquillaje      hablar      mirar',
    '    ir norte / n     ir abajo / ab       inventario / i',
    '',
    ('VERBOS', 'cyanB', 'bold'),
    '  ir, coger, dejar, mirar, examinar, inventario, hablar,',
    '  dar, usar, leer, fumar, pegar, esperar, ayuda, salir.',
    '  Sinonimos castizos: pillar, birlar, preguntar, entregar...',
    '',
    ('OBJETIVO', 'cyanB', 'bold'),
    '  Conseguir las 3 cosas para entrar al after:',
    '  un objeto raro, 5.000 pelas y la palabra de paso.',
    '  Top 10 por menor numero de turnos.',
]


def mostrar_manual():
    cls()
    print()
    print(c("=" * 70, "cyanB"))
    print(c("  MANUAL - MOVIDA".ljust(70), "cyanB", "bold"))
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
    ancho = 60
    print()
    print(c("╔" + "═" * ancho + "╗", "magentaB"))
    print(_caja_linea("", ancho, "blanco"))
    for ln in LOGO_MOVIDA:
        print(_caja_linea(ln, ancho, "magentaB"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Madrid 1985 - aventura conversacional", ancho, "cyanB"))
    print(_caja_linea("Una noche en la Movida. Llega al after kinky-punk.", ancho, "blanco"))
    print(_caja_linea("", ancho, "blanco"))
    print(_caja_linea("Comandos: ir, coger, hablar, dar, usar, mirar...", ancho, "amarB"))
    print(_caja_linea("Escribe AYUDA en cualquier momento.", ancho, "dim"))
    print(_caja_linea("", ancho, "blanco"))
    print(c("╚" + "═" * ancho + "╝", "magentaB"))
    msg = "[Enter] empezar la noche     [M] manual"
    print(" " * ((ancho + 2 - len(msg)) // 2) + c(msg, "amarB", "bold"))
    try:
        raw = input("")
    except EOFError:
        return
    if raw.strip().lower() == "m":
        mostrar_manual()


def pantalla_final(est):
    print()
    ancho = 56
    margen = " " * ((COLS - (ancho + 2)) // 2)
    linea = "═" * ancho
    if est.fin == "exito":
        color = "verdeB"
        titulo = " HAS ENTRADO AL AFTER "
        texto = ("Has entrado en el club. La noche te ha aceptado. Bailas hasta el "
                 "amanecer entre cuero, latex y luces estroboscopicas. Te lo has ganado.")
    elif est.fin == "fracaso":
        color = "amarB"
        titulo = " LA NOCHE NO ACABO BIEN "
        texto = ("Te quedaste fuera. Vuelves a Malasaña arrastrando los pies, "
                 "preguntandote en que te equivocaste. Otra vez sera, punki.")
    else:
        color = "rojoB"
        titulo = " GAME OVER "
        texto = ("Te tumbaron en el callejon de Malasaña. Despiertas en el hospital "
                 "de la Princesa, dolorido. Mala noche, punki.")
    lado = c("║", color)
    print(margen + c("╔" + linea + "╗", color))
    print(margen + lado + c(titulo.center(ancho), color, "bold") + lado)
    print(margen + c("╠" + linea + "╣", color))
    for ln_t in texto.split(". "):
        # wrap a ancho-4
        import textwrap
        for w in textwrap.wrap(ln_t.strip() + ".", width=ancho - 4):
            print(margen + lado + "  " + c(w.ljust(ancho - 4), "blanco") + "  " + lado)
    print(margen + c("╠" + linea + "╣", color))
    print(margen + lado + f"  Turnos: {est.turnos:>4}".ljust(ancho + 2) + lado)
    print(margen + c("╚" + linea + "╝", color))
    print()


# ---------- MAIN ----------

def main():
    splash()
    cls()
    est = Estado()
    mostrar_habitacion(est)
    while est.fin is None:
        try:
            raw = input(c("\n> ", "amarB"))
        except (EOFError, KeyboardInterrupt):
            print()
            return
        verbo, obj = parse(raw)
        if verbo is None:
            if obj:
                print(c("No te entiendo. Escribe AYUDA si te has perdido.", "dim"))
            continue
        VERBOS[verbo](est, obj or "")
        est.turnos += 1
        chequear_eventos(est)
    pantalla_final(est)
    if est.fin == "exito":
        scores = [(e.handle, e.score, e.date) for e in bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)]
        if bbs_scores.entra_en_top_local(est.turnos, max_top=MAX_TOP, ascending=ASCENDING):
            print(c("¡Has entrado en el TOP 10!", "amarB", "bold"))
            try:
                raw = input("  Iniciales (3 chars): ").strip().upper()
            except EOFError:
                raw = "AAA"
            nombre = "".join(ch for ch in raw if ch.isalnum())[:3].ljust(3, "A")
            bbs_scores.save_local(nombre, est.turnos, max_top=MAX_TOP, ascending=ASCENDING)
            bbs_scores.submit(nombre, est.turnos)
            bbs_scores.invalidate_cache()
            scores = [(e.handle, e.score, e.date) for e in bbs_scores.top_local(limit=MAX_TOP, ascending=ASCENDING)]
        # Toggle [L]ocal / [G]lobal del top mundial
        modo = "local"
        while True:
            _scores_e, _titulo, _ = bbs_scores.get_top_for_mode(modo, limit=MAX_TOP, ascending=ASCENDING)
            print(c(f"\n  {_titulo.strip()} (menos turnos = mejor):", "cyanB", "bold"))
            for _i, _e in enumerate(_scores_e, 1):
                _et = _e.display_handle if modo == "global" else _e.handle
                print(c(f"  {_i:>2}. {_et:<14}  {_e.score:>4} turnos   {_e.date}", "blanco"))
            try:
                _r = input(c("\n  [L] local   [G] global   [Enter] continuar: ", "dim")).strip().upper()
            except EOFError:
                break
            if _r == "L":
                modo = "local"
                continue
            if _r == "G":
                modo = "global"
                continue
            break
    print()


if __name__ == "__main__":
    main()
