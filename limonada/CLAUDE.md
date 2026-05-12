# Limonada BBS

Clon en castellano del clasico *Lemonade Stand* (Bob Jamison, 1973; popularizado por Apple II y MECC). Llevas un puesto de limonada durante 30 dias. Cada dia decides cuantos vasos preparar, a que precio venderlos y cuanto invertir en publicidad. Sobrevive al clima, a los eventos imprevistos y acaba con la mayor cantidad de dinero posible.

## Alcance

- Un solo `limonada.py`. Solo stdlib.
- Line-mode (`input` / `print`) — no requiere `termios`.
- Stdout reconfigurado a CP437.
- Top 10 en `limonada_scores.txt`.

## Mecanica

- Empiezas con $2.00.
- Coste por vaso: $0.02 (limones, agua, azucar, vasos).
- Coste por anuncio: $0.15.
- 30 dias.

### Ciclo diario

1. **Parte meteorologico**: soleado, caluroso, nublado, lluvia, tormenta. Cada uno modifica la demanda.
2. **Tus decisiones**:
   - Vasos a preparar (limitado por presupuesto).
   - Precio por vaso en centimos.
   - Numero de anuncios.
3. **Simulacion del dia**: demanda calculada en base a clima + precio + anuncios + un poco de azar.
4. **Resultados**: vasos vendidos, ingresos, costes, beneficio del dia, dinero acumulado.

### Calculo de demanda

```
base = 30
demanda = (base + clima_mod) * factor_precio + bono_anuncios + ruido
```

- `factor_precio`: 1.3 si <=5c, 1.0 si 6-10c, 0.6 si 11-15c, 0.2 si >15c.
- `bono_anuncios`: hasta +20 con retornos decrecientes.
- `ruido`: aleatorio entre -5 y +5.

### Eventos aleatorios

Aproximadamente 1 dia de cada 5, un evento especial:
- "Festival local": demanda x2.
- "Manifestacion": demanda 0.
- "Recomendacion viral": demanda x1.5.
- "Apagon": no se puede vender hoy.
- "Una abuela compra todo tu stock": vendes todo a precio total.

## Controles

Todo line-mode: introduces los numeros y pulsas Enter. Para el numero de vasos/precio/anuncios el sistema valida que no exceda tu presupuesto.

## Puntuacion

Dinero final en centimos al cabo de los 30 dias. Top 10 persistente.
