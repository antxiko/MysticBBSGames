# DopePython

Clon simple de *Dope Wars / Drug Wars* en Python puro, ejecutable standalone desde terminal. UI en espanol.

## Mecanicas validadas

### Inicio
- Efectivo: $2.000
- Deuda con Prestamista: $5.500
- Banco: $0
- Maletin: 100 unidades
- Salud: 100
- Balas: 0
- Dia: 1 de 30
- Barrio inicial: Bronx

### Drogas (12)
Cocaina, Heroina, Acido, Hierba, Speed, Ludes, PCP, Percocet, Hongos, Opio, Morfina, Extasis.

Cada una con rango de precio base. Cada dia se reasignan precios aleatorios por barrio dentro del rango.

### Barrios (6)
Bronx, Ghetto, Central Park, Manhattan, Coney Island, Brooklyn.

Banco y Prestamista **solo disponibles en Bronx**.

### Ciclo de turno
1. Mostrar barrio actual y precios del dia.
2. Acciones: **C**omprar / **V**ender / **J** Viajar / **$** Banco / **P**restamista / **R**esumen / **S**alir.
3. Viajar consume 1 dia y dispara posibles eventos aleatorios.

### Economia
- Interes diario compuesto: **10% deuda**, **5% banco**.
- Se aplica al comenzar cada dia nuevo.

### Eventos aleatorios en viaje
- Policia: perseguido. Opciones **L**uchar (requiere balas) o **H**uir (puede perder droga/salud).
- Asaltado (mugged): pierdes efectivo.
- Encuentras droga tirada o dinero.
- Oferta de aumentar maletin (+capacidad por $).
- Oferta de pistola y balas.
- Brownies con hierba: suben/bajan salud.

### Eventos de mercado
- "La policia confisco X" → precio se dispara.
- "Cargamento de Y recien llegado" → precio se desploma.

### Fin de partida
Al terminar dia 30 o al morir (salud 0). Puntaje final = efectivo + banco − deuda.

## Restricciones de diseno (NO cambiar sin pedirlo)

- **Espanol estricto**. Sin chistes, sin anglicismos. "Prestamista", no "Tiburon".
- **No colorear precios** por bargain/spike. El jugador debe aprender los rangos solo.
- **No duplicar info** en pantalla.
- **Teclas no solapadas** entre menu principal y sub-prompts (p.ej. menu usa letras distintas a `A/N` o `L/H` de los prompts internos).

## Alcance explicitamente fuera

- Mystic BBS, bundles, mocks de API embebida.
- Leaderboard global, saves multi-usuario.
- Multijugador.

## Estructura

**Un unico script**: `dopepython.py`. No dividir en modulos. Solo stdlib.

Python puro standalone: `print`, `input`, ANSI crudo en strings (`\x1b[31m...\x1b[0m`). Sin `mystic_bbs`. Mystic lo lanza como proceso externo (`python3 dopepython.py`). Si los ANSI no pintan en el cliente BBS, es asunto de la config del door, no del codigo.
