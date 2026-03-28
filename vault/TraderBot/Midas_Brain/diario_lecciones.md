---
name: diario_lecciones
description: Diario de trading con lecciones documentadas para educación del brain Midas — patrones de pérdida, correlaciones, insights de mercado
type: project
---

# Diario de Lecciones — Educación del Brain Midas
> Período: 02/03/2026 – 26/03/2026 | 18 días hábiles | 900+ trades | P&L acumulado: ~+$1,200 (parcial)
> Fuente de verdad: CSV exportado de NinjaTrader 8 (NO los strategies_pnl.json — fueron borrados por bug en auto_push_pnl.bat el 20/03)

---

## LECCIÓN 01 — 17/03/2026: Correlación Catastrófica ⚠️
**P&L del día: -$8,906** (2do peor día del período)

**Qué pasó exactamente:**
- 10:05 AM: StatMeanCross + EMATrendRenko + BreadButter_v5_Apex entraron **Long simultáneamente**
- El mercado estaba bajista intraday todo el día
- Todos perdieron juntos. PivotReverse Short también falló. Solo BreadButter_SCALPER terminó positivo

**Contexto de mercado:**
- tide_score nocturno = 0.8 (swim_ok=True) → el monitor NO detectó el peligro
- trend_4H=Bull pero intraday era claramente bajista
- El tide_score se calculaba 1x/día al EOD → ventana ciega de 4-7 horas intraday

**Raíz técnica de la correlación:**
- StatMeanCross usa EMA(21) para crossover
- EMATrendRenko usa EMA(21) como soporte/resistencia
- **Misma EMA(21) = misma señal en el mismo brick de Renko 35** → correlación estructural, no accidental

**Correctivos diseñados:**
- KDL Capa 6 (Correlación de Portafolio): si N estrategias están en mismo lado simultáneamente → reducir sizing o bloquear tardías
- KDL Gate 2.5 (Trend Phase Detector): slope del EMA habría detectado "Continue bajista" a las 10:05 AM → bloqueado todos los longs
- Market Monitor intraday (cada 60s): habrían detectado divergencia entre tide_4H y tendencia 1H real
- **market_breadth_score** (ES+YM+RTY): si los 3 también bajistas → bloquear longs en NQ independientemente del tide_score

**Regla Midas derivada:**
> Si 2+ estrategias están en el mismo lado simultáneamente Y trend_phase = CONTINUE en dirección opuesta → bloquear las tardías, reducir sizing 50%

---

## LECCIÓN 02 — 20/03/2026: Correlación Confirmada — Patrón Sistémico 🔄
**P&L del día: +$1,616** (salvado por DarvasBox +$2,168 y BBv5 supervisado +$4,200)

**Qué pasó exactamente (AM):**
- **9:46:32 AM** — StatMeanCross y EMATrendRenko dispararon SHORT simultáneamente
- Misma barra exacta, mismo lado, ambos perdieron (-$820 combinado)
- Mismo patrón del 17/03 pero en dirección opuesta (shorts en vez de longs)

**Confirmación del patrón:**
- 17/03: longs correlacionados → pérdida
- 20/03: shorts correlacionados → pérdida
- **El patrón aparece en AMBAS direcciones → es sistémico, no casualidad**
- Ya son 3 eventos de correlación documentados en el período (11/03, 17/03, 20/03)

**Qué salvó el día (PM):**
- DarvasBox Short: +$2,168 (estrategia descorrelacionada — no usa EMA(21))
- BreadButter_v5_Apex Short supervisado: +$4,200 (ver Lección 03)

**Regla Midas derivada:**
> La correlación StatMean+EMATrend es estructural (misma EMA base). En producción, tratar estas dos como UN SOLO SLOT de trade cuando coincidan en la misma barra

---

## LECCIÓN 03 — 20/03/2026: El Valor de la Supervisión Humana 👤
**Evento: BreadButter_v5_Apex Short 2:01 PM → cierre manual 2:51 PM → +$4,200**

**Qué pasó:**
- BBv5 tomó Short a las 2:01 PM (precio: 24,203)
- Usuario supervisó y cerró manualmente a 2:51 PM (precio: 24,097)
- Exit type = "Close" (manual) vs exit automático habitual
- MFE alcanzado: $3,269 | ETD: $543 | La supervisión capturó casi todo el MFE

**Por qué el humano fue mejor que el algoritmo:**
- Mercado claramente bajista todo el día (24,450 → 24,090 de AM a PM)
- ConvictionScore alto en esa dirección (short alineado con tendencia del día)
- En tendencia diaria clara + alta convicción → dejar correr más del target automático

**Qué aprende Midas de este trade:**
- RL/PPO (Capa 11 — Mayo 2026) aprenderá exactamente esta decisión: cuándo ajustar el trailing vs cuándo salir fijo
- Señal: trend_1D=bajista + trend_4H=bajista + ConvictionScore alto → extender target o usar trailing agresivo
- El exit_type="Close" con P&L positivo + ETD bajo = label de "salida óptima" para el modelo

**Regla Midas derivada:**
> En días con tendencia diaria clara (tide_score < -1.5 o > +1.5) + todos los TFs alineados → activar trailing agresivo en vez de profit target fijo. El algoritmo debería hacer lo que hizo el humano ese día.

---

## LECCIÓN 04 — 06/03/2026: El Día más Duro sin Análisis Forense ⚠️
**P&L del día: -$11,920** (PEOR DÍA DEL PERÍODO — mayor que 17/03)

**Qué pasó:**
- Pérdida catastrófica. B&Bv5 fue identificado como el swing factor principal
- Llegó ANTES de que las lecciones de correlación fueran formalmente registradas
- Sin análisis forense detallado disponible (el 17/03 sí tiene análisis completo)

**Contexto:**
- Probable régimen de alta volatilidad o evento macro sin filtro activo
- El tide_score nocturno no capturó el riesgo intraday (mismo bug que el 17/03)
- Posible día de noticias extremas (06/03 fue un viernes — potencialmente datos económicos)

**Lo que habría ayudado:**
- Portfolio Stop Global ($LimiteDiario) habría cortado las pérdidas
- KDL Gate 2.5 podría haber detectado el momentum adverso
- News Filter: si hubo evento macro → bloquear entradas ±30min
- market_breadth_score: si ES/YM/RTY también en caída libre → max_sizing reducido

**Regla Midas derivada:**
> Portfolio Stop Global es CRÍTICO. Implementar en Semana 2 Abril. Si pérdida combinada del día > $LimiteDiario → publicar STOP_ALL, todas las estrategias consultan antes de entrar

---

## LECCIÓN 06 — 23/03/2026: Inactividad Masiva — Probable Rollover de Contrato 🔄
**P&L del día: -$7 (solo SuperTrendWave operó — errático)**

**Qué pasó:**
- De 17 estrategias activas, solo SimSuperTrendWave disparó (3 trades, -$7 total)
- Todas las demás registraron $0 — sin señales en todo el día
- SuperTrendWave operó de forma atípica: abrió 3 posiciones simultáneas (1+2+2 contratos) en la misma barra de las 1:55 PM y cerró todas juntas por Stop Loss a las 2:07 PM
- El usuario pregunta si algún cambio en el brain del viernes causó la inactividad

**Hipótesis más probable — Rollover MNQ 03-26 → MNQ 06-26:**
- El instrumento en el CSV es "MNQ 06-26" (contrato de Junio 2026)
- El contrato de Marzo 2026 expiró — el rollover típico de MNQ es la 2da semana de Marzo
- Las estrategias con barras Renko pierden su historial al cambiar de contrato: el brick size se recalcula sobre datos nuevos, las EMAs se reinician, el VWAP empieza desde 0
- En Renko especialmente: hasta que se construyen suficientes bricks con el nuevo contrato, muchas estrategias no generan señales válidas
- Ya estaba documentado en MEMORY.md: "Rollover MNQ cambia datos Renko → re-validar estrategias con nuevo contrato"

**Sobre el brain del viernes:**
- No hubo cambios en el código de las estrategias NT8 el viernes
- Los cambios del viernes fueron solo en los archivos de memoria del brain (arquitectura RL) — no afectan la ejecución de NT8
- La inactividad es interna a NinjaTrader, no del brain Python

**Por qué SuperTrendWave sí operó (y mal):**
- SuperTrendWave puede usar timeframe estándar (no Renko) o Renko con brick pequeño
- Al abrir 3 posiciones simultáneas en la misma barra: comportamiento de "restart" tras rollover — la estrategia vio una señal en la primera barra del nuevo contrato y entró en múltiples capas
- Stop Loss en la misma barra = probable stop demasiado ajustado en el primer brick del nuevo contrato

**Acción requerida:**
- Verificar en NT8 que todas las estrategias apuntan al contrato MNQ 06-26
- Re-cargar las estrategias Renko para que reconstruyan el historial de bricks con el nuevo contrato
- Esperar 1-2 días de trading para que las EMAs se estabilicen en el nuevo contrato antes de evaluar señales

**Regla Midas derivada:**
> Rollover de contrato = día de mantenimiento obligatorio. La semana del rollover (~2da semana de Marzo, Junio, Septiembre, Diciembre) NO contar los $0 como "sin señal" — es silencio técnico, no de mercado. Marcar en el calendario y excluir del análisis de frecuencia de Markov.

---

## LECCIÓN 08 — 26/03/2026: El Día del Gap — Caos en los Primeros 90 Minutos ⚡
**P&L parcial (hasta 11:17 AM): -$2,262.90** | Día aún abierto

**Contexto crítico de mercado:**
- Cierre 25/03: 24,213.75
- Apertura 26/03: ~24,100
- **GAP DOWN: -113 puntos (-0.47%)** antes de la apertura
- tide_score previo: -0.40 (bear 1D, breadth -3) → la macro YA advertía

**Cronología del caos (primeros 90 minutos):**
```
09:32  ABCDHarmonic LONG 24104  → stop -$36 (mercado seguía cayendo)
09:35  StatMean SHORT 24105     → stop en 09:37 -$463 (mercado rebotó)
09:35  EMATrend SHORT 24105     → stop en 09:37 -$553 (mismo rebote)
09:37  PivotReverse SHORT 24112 → stop en 09:43 -$42 (casi breakeven)
09:42  DarvasBox LONG 24105     → PROFIT TARGET 24175 en 09:45 +$2,757 ✅
09:53  MomentumZ LONG 24210     → stop -$571 (pullback post-bounce)
10:05  DarvasBox SHORT 24180    → stop 24204 -$969 (mercado siguió subiendo)
10:08  DarvasBox SHORT 24183    → stop 24226 -$1,740 (mercado ↑ a 24226)
10:15  SuperTrendWave LONG 24218→ stop 24185 -$330 (mercado cayó de nuevo)
11:13  BB_SCALPER SHORT 24098   → stop -$314 (mercado en 24098 — volvió al gap)
```

**Desglose por estrategia (hoy):**
| Estrategia | P&L | Observación |
|---|---|---|
| DarvasBox Long (09:42) | **+$2,757** | Único ganador — capturó el bounce del gap |
| EMATrendRenko Short | **-$553** | Entró en la dirección del gap, whipsawed |
| StatMeanCross Short | **-$463** | Mismo: gap direction → whipsaw |
| MomentumZ Long | **-$571** | Persiguió el bounce, que ya había terminado |
| DarvasBox Short (x2) | **-$2,710** | Intentó la continuación bajista, mercado siguió up |
| SuperTrendWave Long | **-$330** | Siguió el momentum alcista del bounce, se revirtió |
| BB_SCALPER Short | **-$314** | Short correcto de dirección pero timing malo |
| PivotReverse Short | **-$42** | Casi breakeven — stops casi no se movieron |

---

### LECCIÓN 08-A: El GAP — El Enemigo de las Estrategias de Momentum 💥

**Qué es un "Gap Day":**
- NQ abre 100+ puntos lejos del cierre anterior
- Los primeros 15-20 minutos son un campo minado de whipsaws
- El mercado tiene que "decidir": ¿llenar el gap (rebote) o continuarlo (fuga)?
- TODAS las estrategias de momentum leen el gap como señal → TODAS entran en la misma dirección → TODAS se exponen a ser whipsawed si el mercado elige la otra opción

**Lo que pasó exactamente hoy:**
1. Gap DOWN de 113 puntos → StatMean y EMATrend vieron el bear momentum → SHORT inmediato
2. El mercado hizo "bounce" (intento de llenar el gap) → StatMean y EMATrend paradas en 90 segundos
3. DarvasBox vio el mismo bounce → LONG → profit target +$2,757 (capturó 70 puntos)
4. DarvasBox entonces buscó la continuación SHORT (lógica: gap down = tendencia bajista) → el mercado siguió subiendo hasta 24226 → dos stops consecutivos
5. SuperTrendWave siguió el momentum alcista del bounce → el mercado revirtió y bajó de nuevo

**La estructura completa del día:**
```
24213 (cierre ayer)
  ↓ Gap DOWN overnight
24100 (apertura)
  ↓ primer movimiento: caída a 24087
  ↑ BOUNCE: sube a 24226 (rebote de 139 puntos desde el mínimo)
  ↓ REVERSAL: vuelve a 24098 (sigue el gap original)
```
Mercado tipo "N invertida" — el peor patrón para estrategias tendenciales.

**Regla Midas derivada — GAP FILTER:**
> Si `precio_apertura - precio_cierre_ayer > 50 puntos` (en cualquier dirección) → **GAP DAY activo**.
> En GAP DAY:
> - Primeros 15 minutos: SIZE×0.25 en TODAS las estrategias
> - Bloquear estrategias de momentum puro (StatMean, EMATrend) hasta que el rango de los primeros 15 min se consolide
> - Solo DarvasBox y PivotReverse operan normalmente (tienen lógica de profit target que aguanta la volatilidad)
> - Activar `condition_map.py` flag: `gap_day=True`

---

### LECCIÓN 08-B: StatMean y EMATrend — El Talón de Aquiles en Gaps ⚠️

**El patrón específico:**
- 09:35:23 StatMean SHORT — 09:37:01 stop = **98 segundos de vida**
- 09:35:23 EMATrend SHORT — 09:37:13 stop = **110 segundos de vida**
- Ambas entraron en el MISMO brick de Renko → correlación estructural EMA(21) confirmada una vez más
- Ambas murieron en el mismo bounce → -$1,016 en 2 minutos

**Por qué ocurre:** Renko 35 construye un brick bajista cuando el mercado cae 35 puntos. En un gap de 113 puntos, el primer brick de apertura es gigante y bajista → señal inmediata. Pero ese mismo brick absorbe todo el movimiento overnight → el siguiente movimiento probable es la corrección (bounce).

**Regla Midas derivada:**
> StatMean y EMATrend NO operan en la primera barra de Renko después de un gap >50 puntos. El primer brick de gap es "precio de descubrimiento", no señal de trend. Esperar al segundo brick confirmatorio.

---

### LECCIÓN 08-C: DarvasBox — El Único que Leyó Bien el Gap 🎯

**Lo que hizo bien:**
DarvasBox entró LONG a 24105 → profit target 24175. Capturó exactamente el bounce del gap (la tendencia de "gap fill" — el mercado intentó volver a 24213).

**Por qué DarvasBox funcionó y StatMean no:**
- StatMean sigue momentum → entró SHORT porque el gap era bajista → whipsaw
- DarvasBox usa ruptura de range (Darvas Box) → esperó que se formara un box en el rango de los primeros minutos → entró en la dirección de la ruptura del box (que fue alcista, hacia el gap fill)
- **DarvasBox es estructural, StatMean es momentum** → en gaps, la estructura manda antes que el momentum

**El "error" de DarvasBox:**
Después de ganar el Long, intentó SHORT dos veces (24180 y 24183) esperando la continuación bajista del gap. El mercado siguió subiendo hasta 24226. Perdió $2,710 — más del doble de lo que ganó.

**Regla Midas derivada:**
> Después de que DarvasBox capture el bounce del gap (Long en gap-down), NO intentar el Short en la misma sesión hasta que `tide_score_intraday` confirme nuevo impulso bajista via VWAP SD Bands. El bounce puede ser más fuerte de lo esperado.

---

### LECCIÓN 08-D: La Señal que Midas No Tiene Todavía 🔔

**El problema fundamental de hoy:** Midas no tenía información del gap al momento de las entradas.

El `market_monitor_logger.py` corre a las 4:30 PM ET del día anterior. Para las 9:35 AM de hoy, el tide_score de ayer (-0.40) es lo único disponible. Pero la condición crítica era:

```
GAP_SIZE = abs(precio_apertura - precio_cierre_ayer)
GAP_SIZE = |24100 - 24213| = 113 puntos ← esta información NO existía en el brain
```

Esta es la pieza que falta: un **pre-market check** que calcule el gap antes de que abran las estrategias.

**Cómo implementarlo (simple, sin infraestructura nueva):**
```python
# En market_monitor_logger.py — agregar función:
def check_pre_market_gap(ticker="NQ=F") -> dict:
    df = yf.download(ticker, period="2d", interval="1d")
    prev_close = df["Close"].iloc[-2]
    # Precio pre-mercado via ticker "NQ=F" a las 9:25 AM ET
    pre_market = yf.download(ticker, period="1d", interval="5m")["Close"].iloc[-1]
    gap = pre_market - prev_close
    return {
        "gap_points": round(gap, 2),
        "gap_pct": round(gap / prev_close * 100, 3),
        "gap_day": abs(gap) > 50,
        "gap_direction": "up" if gap > 0 else "down"
    }
```
Esto correría a las 9:25 AM ET (antes de apertura) y generaría `gap_day=True/False` en el JSON del día.

---

## LECCIÓN 08 — tarde 26/03/2026: BBv5 salva el día + costo de la intervención manual

**P&L final 26/03: +$1,024.60** (de -$2,262 en la mañana a positivo al cierre)

**Cronología tarde:**
```
13:35  BBv5 Short 23,961 → cierre 23,884  +$3,022 ✅  (caída 77 pts, 50 min)
14:26  BBv5 Short 23,867 → cierre 23,883  -$710  ❌  (rebote técnico)
14:51  Pablo → LONG 23,886 → cierre 23,865  -$897  ← intervención manual
14:56  Short 23,865 → cierre 23,832  +$1,274 ✅
15:06  Short 23,848 → cierre 23,832  +$598  ✅
```

NQ cerró en ~23,832. Caída total del día: 24,213 → 23,832 = **-381 puntos (-1.57%)**.
Context market monitor del día anterior: 1D bear + breadth -3 + RSI 32 → la macro lo decía todo.

Sin la intervención Long: **+$1,657** en lugar de +$1,024. Costo: **-$633**.

---

### LECCIÓN 08-E: BBv5 — El Héroe Silencioso del Portafolio ⚡

**Lo que hizo bien:** Ignoró el caos de la mañana (gap, whipsaws, stops en 98s). Esperó. A las 13:35 el mercado tenía momentum bajista claro y NQ en caída libre → entró Short → capturó 77 puntos con 20 contratos → +$3,022 en 50 minutos.

**Por qué el Filtro Accidental es edge:** La restricción de 1 trade/día la protegió de todo el ruido matutino. Mientras StatMean y EMATrend morían en segundos, BBv5 esperó pacientemente la señal real. El "bug" que nunca se corrige resultó ser el mejor filtro de volatilidad del portafolio — implementación involuntaria del Condition Map.

**Regla Midas derivada:**
> Estrategias con restricción natural de frecuencia (1 trade/día) son más robustas en días volátiles que estrategias de alta frecuencia. El Filtro Accidental de BBv5 = esperar hasta que el mercado muestre dirección real. No corregir nunca.

---

### LECCIÓN 08-F: La Intervención Manual — El Enemigo Dentro 🧠

**Lo que pasó:** BBv5 cerró Short en 23,884 (+$3,022). Micro-rebote de 2 puntos a 23,886. Pablo entró Long. El mercado no rebotó — continuó a 23,865. Pérdida: -$897.

**La psicología exacta:**
1. Trade grande activo (+$3,022) → ansiedad de perderlo → urgencia de "asegurar"
2. Micro-rebote de 2 puntos → cerebro lo lee como "confirmación de bounce"
3. Miedo al "popcorn trade" → acción impulsiva → Long
4. Resultado: creó exactamente lo que temía — cerró el ganador y entró en un perdedor

**La ironía:** El miedo al popcorn trade generó un popcorn trade.

**Regla Midas derivada — MANOS FUERA:**
> Cuando BBv5 (o cualquier estrategia) tiene un trade activo: **cero intervención manual**.
> El Filtro Accidental existe para eliminar exactamente esta tentación.
> La única excepción: Portfolio Stop Nivel 7 (pérdida total día > $5,000).
> **Costo documentado de ignorar esta regla: -$633 en un solo día.**

---

## LECCIÓN 09 — 27/03/2026: Primer Día con Módulo 3 + El Bug del Ejército 🐛
**P&L del día: +$3,431.90** | Semana 4 completa

**Contexto macro (primer día con datos automáticos):**
- tide_score: **-3.0** (full bear — todos los TFs bajistas, breadth -3/3)
- VIX: **31.05 EXTREME** (+3.61 del día anterior)
- Fear & Greed: **10.2 EXTREME_FEAR**
- NQ: 23,500 → 23,313 (-187 puntos en el día)
- Sin eventos económicos high-impact

**Desglose por estrategia:**
| Estrategia | P&L | Observación |
|---|---|---|
| BBv5 | **+$6,103.50** | Short 10:13 → cerró 14:15 (+$5,999) + re-entradas +$104 |
| DarvasBox | **-$904.50** | Bug AllEntries qty=18 — pérdida inflada artificialmente |
| EMATrendRenko | **-$235.80** | Bug AllEntries qty=15 |
| OrderFlowReversal | **-$757.50** | Bug AllEntries qty=3+3+9 |
| PivotTrendBreak | **-$312.00** | Bug AllEntries qty=2+2+2+14 |
| SuperTrendWave | **-$443.00** | Short y Long alternados — net negativo |
| ABCDHarmonic | **-$18.80** | 1 stop normal |

---

### LECCIÓN 09-A: El Bug del Ejército — AllEntries en 4 Estrategias ⚠️

**El patrón en el CSV:**
```
DarvasBox:          qty=1 + qty=1 + qty=18  → 3 órdenes simultáneas 09:59:59
EMATrendRenko:      qty=1 + qty=15          → 2 órdenes simultáneas 10:00:00
OrderFlowReversal:  qty=3 + qty=3 + qty=9  → 3 órdenes simultáneas 11:24:14
PivotTrendBreak:    qty=2+2+2+14           → 4 órdenes simultáneas 11:34:40
```

**Por qué ocurre:** NT8 llama a `OnBarUpdate()` múltiples veces durante la transición
Historical→Realtime. Con `EntryHandling.AllEntries`, cada llamada genera una orden separada.
Con `EntryHandling.UniqueEntries`, la segunda llamada es ignorada si ya hay posición abierta.

**DarvasBox ya fue corregido** (27/03/2026). Las otras 3 estrategias pendientes para el lunes.

**Impacto real del bug:**
- DarvasBox perdió -$904.50 (con qty=18 real serían ~$50 normales → pérdida inflada ~18x)
- Las 4 estrategias con bug perdieron un total de **-$2,209.80**
- Sin el bug, el día habría sido **+$5,641** en lugar de +$3,431

---

### LECCIÓN 09-B: La Paradoja del Módulo 3 — avoid_shorts vs tide_score ⚡

**El conflicto del día:**
- `macro_context.avoid_shorts = True` (VIX EXTREME + Fear EXTREME → lógica defensiva)
- `tide_score = -3.0` (full bear — dirección bajista confirmada en todos los TFs)
- **Resultado real**: BBv5 SHORT fue el gran ganador del día (+$6,103)

**El insight:** `avoid_shorts` está diseñado para proteger de shorts aleatorios en pánico de mercado.
Pero cuando `tide_score = -3.0`, el mercado NO está en pánico aleatorio — está en tendencia bajista
estructurada. El VIX EXTREME y el F&G=10 SON la explicación de la caída, no una señal de reversal.

**Regla Midas derivada — corrección al Módulo 3:**
> `avoid_shorts` se aplica SOLO cuando `tide_score > -1.5`.
> Si `tide_score <= -2.0`, la tendencia bajista domina sobre el VIX — los shorts estructurales
> (BBv5, estrategias con filtro) siguen siendo válidos. El pánico extremo en tendencia = aceleración,
> no reversal. Ajustar lógica en `compute_macro_context()` el lunes.

---

### LECCIÓN 09-C: BBv5 Re-entradas Post-Cierre — Comportamiento a Investigar 🔍

**Lo que muestra el CSV:**
- Trades 26-28: Short 10:13 AM → 14:15 PM → **+$5,999** (con nombre "BreadButter_v5_Apex")
- Trades 29-38: Múltiples entradas 14:22-15:09 → **+$104 neto** (SIN nombre de estrategia)

**Hipótesis:** El Filtro Accidental cerró el primer trade (1 trade/día). Las re-entradas posteriores
son del mismo bot pero sin el nombre registrado correctamente en NT8 — posible comportamiento
en `State.Transition` tras el cierre manual del primer trade.

**Acción pendiente el lunes:** Revisar el código de BBv5 — ¿hay lógica de re-entrada después
del MaxDailyLoss? ¿El Filtro Accidental se resetea en el mismo día?

---

### LECCIÓN 09-D: Módulo 3 Funcionó — Con Un Ajuste Pendiente ✅

**Lo que entregó correctamente:**
- VIX=31.05 → EXTREME ✓
- F&G=10.2 → EXTREME_FEAR ✓
- Sin eventos económicos hoy → no_trade_windows vacías ✓
- Encodig issue menor: "â sin shorts" en el JSON (carácter → se perdió en Windows UTF-8)

**El único error de lógica**: `trade_mode = "LONG_ONLY_REDUCED"` cuando en realidad
el mercado era full bear. El modo correcto con `tide_score=-3.0` sería `"SHORT_STRUCTURAL"`.

**Fix para el lunes:** añadir `tide_score` como input a `compute_macro_context()` para
cruzar el régimen macro con el régimen técnico antes de asignar `trade_mode`.

---

## LECCIÓN 07 — 25/03/2026: El Día que Todo Encajó ✅
**P&L del día: +$5,318.10** (mejor día desde el inicio del período actual)

**Desglose por estrategia:**
| Estrategia | Dirección | P&L | Observación |
|---|---|---|---|
| StatMeanCross_v1 | Long × 17 entradas | **+$953.50** | Todas en Profit Target en 1 min |
| PivotReverse_v1 | Long × 12 entradas | **+$3,106.00** | Todas en Profit Target — ayer fue Short y perdió $1,048 |
| DarvasBox 2do batch | Short × 15 entradas | **+$2,675.50** | 09:47 — mercado cayó 67 puntos |
| DarvasBox 3er batch | Short × 16 entradas | **+$2,805.50** | 10:59 — mercado cayó 71 puntos |
| SuperTrendWave Short | Short × 2 entradas | **+$383.00** | Tarde — mercado bajó, Short funcionó |
| DarvasBox 1er batch | Short × 3 entradas | **-$1,013.00** | 09:33 — entró early, mercado no había revertido |
| SuperTrendWave Long | Long × 5 entradas | **-$852.00** | Mañana — luchó contra la caída |
| OrderFlowReversal | Long × 3 entradas | **-$758.00** | Tarde — mercado seguía cayendo |
| NYOpenBlast_v2 | Long × 3 entradas | **-$536.50** | Apertura — paró sobre el impulso inicial |
| MomentumZ_v1 | Long × 4 entradas | **-$496.80** | Apertura — paró inmediatamente |
| BreadButter_SCALPER | Long × 3 entradas | **-$354.00** | Apertura — 1 barra, stop |
| BreadButter_ULTRA | Short × 3 entradas | **-$241.00** | Apertura — 1 barra, stop |
| PivotTrendBreak | Long × 3 entradas | **-$323.00** | Paró en 1 barra |
| EMATrendRenko | Long × 3 entradas | **-$1.80** | Breakeven — EMA Exit |

**Estructura del mercado hoy:**
- Apertura gap up → rally 24425 → 24467+
- Reversión brusca → caída a 24367 (9:52) ← DarvasBox 2do batch
- Rebote → 24505 (10:35)
- Segunda caída → 24412 (11:10) ← DarvasBox 3er batch
- Rebote → nueva caída tarde → 24330 ← OFR Long falló
- Día volátil bidireccional con dos drops pronunciados intraday

---

### LECCIÓN 07-A: StatMeanCross — El Setup de Apertura Perfecto 🎯
**Lo que pasó:** 17 entradas simultáneas en Long a las 09:30, TODAS en Profit Target a las 09:31 (1 minuto).

**Condición**: Gap up en apertura + primer brick Renko confirmando momentum alcista → StatMean entra masivamente Long

**Por qué funciona así:** StatMean usa EMA(21) en Renko 35 — cuando el mercado abre con gap y el primer brick es alcista, la EMA ya está en pendiente positiva del overnight → señal inmediata y fuerte → targets alcanzados antes de que aparezca counter-pressure

**Regla Midas derivada:**
> Gap apertura + momentum confirmado en primera barra Renko = condición ideal para StatMean. Si tide_score es positivo en ese momento → no filtrar, dejar operar. StatMean en esta condición captura $950+ sin exposición relevante (MAE máximo $30).

---

### LECCIÓN 07-B: PivotReverse — La Estrategia Ambidiestra 🔄
**Lo que pasó:** Ayer 24/03 fue Short y perdió -$1,048. Hoy fue Long y ganó +$3,106.

**Interpretación crítica:** La estrategia NO está rota. Tiene edge en ambas direcciones — simplemente necesita coincidir con la dirección del mercado. El 24/03 el mercado subía → el short falló. Hoy el mercado también subía en esa ventana → el long arrasó.

**El problema que confirma:** PivotReverse no tiene filtro de tendencia diaria. Entra donde detecta el "pivot" pero no sabe si la tendencia macro apoya esa dirección. Cuando acierta la dirección: win masivo (+$3,106 con 12 entradas). Cuando se equivoca: pérdida igualmente masiva (-$1,048 ayer).

**Regla Midas derivada:**
> PivotReverse tiene uno de los win rates más altos del portafolio CUANDO está alineada con tide_score. Sin filtro = moneda al aire con tamaño grande. Con VWAP SD Bands intraday (B6-0a) habría confirmado Long hoy y bloqueado Short ayer. Prioridad de implementación confirmada.

---

### LECCIÓN 07-C: DarvasBox — El Edge de la Persistencia 💎
**Lo que pasó:**
- 09:33 Short → stop loss (-$1,013) — mercado no había revertido aún
- 09:47 Short → profit target (+$2,675) — mercado cayó 67 puntos
- 10:59 Short → profit target (+$2,805) — mercado cayó 71 puntos
- **Net DarvasBox hoy: +$4,467**

**Patrón identificado:** DarvasBox sigue intentando en la misma dirección después de un stop. La primera entrada es la "sonda" — si el mercado no confirma inmediatamente, para. La segunda o tercera entrada en la misma sesión, con más confirmación de precio, captura el movimiento real. El stop inicial es el "costo de sondeo".

**Por qué el batch Short funcionó:** El mercado en los dos drops intraday cayó ~67-71 puntos. Eso es $134-142 por contrato en MNQ. Con 15-20+ contratos simultáneos, el profit target se alcanza en minutos.

**Regla Midas derivada:**
> DarvasBox tiene resiliencia incorporada — el primer stop no es señal de fallo de la estrategia, es parte del proceso de detección. Si la dirección es correcta (shorts en caída, longs en rally), la estrategia recupera y genera retornos asimétricos. El brain NO debe penalizar a DarvasBox en TfT por stops iniciales si los siguientes entries en la misma dirección son ganadores.

---

### LECCIÓN 07-D: Alineación vs Desalineación — La Diferencia Real 🧭
**Resumen del patrón de hoy:**

Los ganadores de hoy (+$9,923 bruto) tenían algo en común:
- StatMean Long → mercado subió en apertura ✅ alineado
- PivotReverse Long → mercado subía en ventana 10:09-10:22 ✅ alineado
- DarvasBox Short → mercado cayó en ambos drops ✅ alineado
- SuperTrendWave Short tarde → mercado bajó ✅ alineado

Los perdedores de hoy (-$4,575 bruto) entraron contra el movimiento:
- SuperTrendWave Long → mercado estaba en el drop ❌ desalineado
- MomentumZ Long → apertura justo antes del pullback ❌ desalineado
- NYOpenBlast Long → apertura antes del drop ❌ desalineado
- OFR Long tarde → mercado seguía bajando ❌ desalineado

**La conclusión que confirma la hipótesis central de Midas:**
> El problema nunca fue que las estrategias fueran malas. El problema es que no tienen información de contexto de mercado. El 100% de los ganadores estaban alineados con el movimiento de precio en su ventana. El brain solo necesita saber la dirección del mercado ANTES de que entre la señal.

---

## LECCIÓN 06b — 23/03/2026: Ranking de Estrategias (Semana 3) 📊
**Fuente: Screenshot NT8 Accounts — ordenado de más perdedor a más ganador (desde $100k inicio)**

| Estrategia | Equity actual | P&L neto | Observación |
|---|---|---|---|
| SimPivotTrendBreak | $93,215.50 | **-$6,784.50** | Peor del portafolio — revisar |
| SimEMATrendRenko_v1 | $97,277.50 | **-$2,722.50** | Correlacionada con StatMean |
| SimSuperTrendWave | $97,329.00 | **-$2,671.00** | Lección 06 — rollover |
| SimVAWAPOrderBlock | $97,639.50 | **-$2,360.50** | Por debajo de R²>0.85 threshold |
| SimStatMeanCross_v1 | $97,734.50 | **-$2,265.50** | Correlacionada con EMATrend |
| SimBreadButter_ULTRA | $99,278.00 | **-$722.00** | Filtro Accidental activo — normal |
| SimVWAPFlux_v1 | $99,751.10 | **-$248.90** | Neutral |
| SimOpeningRange_v1 | $99,754.20 | **-$245.80** | Neutral |
| SimOrderFlowReversal | $99,768.50 | **-$231.50** | Neutral |
| SimBreadButter_SCALPER | $99,918.00 | **-$82.00** | Filtro Accidental activo — normal |
| SimABCDHarmonic_v1 | $99,924.70 | **-$75.30** | Neutral |
| Sim101 | $100,000.00 | $0.00 | Sin trades aún |
| SimLWDonchianBreak_v | $100,665.80 | **+$665.80** | Positivo |
| SimNYOpenBlast_v2 | $101,302.00 | **+$1,302.00** | Positivo |
| SimMomentumZ_v1 | $101,603.30 | **+$1,603.30** | Positivo |
| SimBreadButter_v5_Apex | $101,767.70 | **+$1,767.70** | Positivo — Step Lock activo |
| SimPivotReverse_V1 | $103,034.50 | **+$3,034.50** | Sorpresa positiva |
| SimDarvasBox_v1 | $113,412.00 | **+$13,412.00** | OUTLIER — dominando el portafolio |

**Insights clave:**
- **DarvasBox +$13,412**: era el "traidor" en TFT (tft=0.25) pero está dominando. Revisar si el comportamiento es consistente o spike. Actualizar TFT multiplier si el rendimiento reciente es real.
- **PivotTrendBreak -$6,784**: peor del portafolio en vivo. En backtests tenía Sortino=8.50 (top 3). Divergencia significativa backtest vs live → candidato a revisar parámetros o excluir.
- **StatMean -$2,265 + EMATrend -$2,722**: juntas suman -$4,987 — la correlación estructural sigue costando. Confirma la urgencia de tratarlas como un solo slot.
- **BBv5_Apex +$1,767 positivo**: con Step Lock activo, se comporta de forma controlada.

---

## LECCIÓN 05 — 11/03/2026: Primer Evento de Correlación Documentado 📝
**Evento: 9:44 AM — StatMeanCross y EMATrendRenko dispararon misma dirección simultáneamente**

**Importancia:**
- Este es el PRIMERO de 3 eventos correlacionados en el período
- Solo 2 estrategias afectadas (vs 3 el 17/03)
- La pérdida fue contenida pero el patrón ya estaba presente
- Confirma que el patrón es sistémico desde el primer día de operativa

**Secuencia de eventos de correlación:**
1. **11/03**: StatMean + EMATrend (2 estrategias, pérdida contenida) → primer aviso
2. **17/03**: StatMean + EMATrend + BBv5 (3 estrategias) → catástrofe -$8,906
3. **20/03**: StatMean + EMATrend (2 estrategias, shorts) → confirmación sistémica

---

## LECCIÓN 06 — 13/03/2026: Cómo funciona el portafolio cuando funciona ⭐
**P&L del día: +$7,191** (MEJOR DÍA DEL PERÍODO)

**Qué pasó:**
- Múltiples estrategias en condiciones favorables, alineadas con el mercado
- Probablemente tendencia clara intraday + sea_state calm o moderate
- B&Bv5 aportó un trade ganador significativo

**Por qué funcionó:**
- Portafolio alineado con tendencia diaria real
- No hubo correlación adversa — cada estrategia capturó su edge independientemente
- Sea state = condiciones óptimas (CI bajo, trending)

**Regla Midas derivada:**
> El portafolio tiene capacidad de generar +$7,000 en un solo día. La diferencia vs -$8,906 es alineación con el mercado + ausencia de correlación. Objetivo de Midas: maximizar días como este, eliminar días como el 17/03.

---

## PATRONES ESTADÍSTICOS DEL PERÍODO

| Semana | Resultado | Evento Notable |
|--------|-----------|----------------|
| S1 (02-06/03) | Dominado por -$11,920 el 06/03 | EMATrend y StatMean confirmadas en backtest |
| S2 (09-13/03) | Recuperación; +$7,191 el 13/03 | 1er evento correlación 11/03; rollover próximo |
| S3 (16-20/03) | -$8,906 el 17/03; +$1,616 el 20/03 | Rollover MNQ 06-26; 2 eventos correlación |
| S4 (21-24/03) | ~-$3,300 aprox | Short bias sistémico; 3 estrategias short vs tendencia alcista |
| **TOTAL** | **-$1,847** | **5 lecciones documentadas — MaxDD -$29,104** |

**Análisis de varianza:**
- **B&Bv5** = factor de swing dominante (días extremos → B&Bv5 involucrado)
- **StatMean + EMATrend** = par de correlación estructural (misma EMA(21) base)
- **Días buenos**: portafolio alineado con tendencia + no correlación + sea_state calm
- **Días malos**: correlación + contra-tendencia + sin Portfolio Stop
- **Bug infraestructura**: tide_score 1x/día → ventana ciega 4-7h intraday → Fix: medir cada 60s

---

## BUG CRÍTICO DE INFRAESTRUCTURA — 20/03/2026
**strategies_pnl_*.json sobreescritos a CERO por auto_push_pnl.bat**
- El script auto_push_pnl.bat borró los datos de P&L histórico al correr
- **Fuente de verdad SIEMPRE: CSV exportado de NinjaTrader 8**
- Los archivos JSON son solo cache, no fuente primaria
- Fix pendiente: auto_push_pnl.bat debe hacer append, no overwrite

---

## LECCIÓN 05 — 24/03/2026: Short Bias Sistémico en Día Alcista ⚠️
**P&L del día: -$1,847.50** | **Período 02-24/03: -$1,847.50 neto (746 trades)**

**Qué pasó exactamente:**
- Mercado alcista todo el día: 24,146 → 24,263 (+117 puntos intraday)
- **PivotReverse_v1** SHORT: 4 entradas simultáneas 11:10 (qty 3+6+3+8 = 20 contratos) → todas stop loss → **-$1,048**
- **DarvasBox_v1** SHORT: 3 entradas simultáneas 09:50 (qty 1+4+15 = 20 contratos) → todas stop loss → **-$953**
- **SuperTrendWave** SHORT: 3 intentos a lo largo del día, todos contra tendencia → **-$624**
- **PivotTrendBreak_v1** LONG: 6 entradas simultáneas todas en Profit Target → **+$636** (leyó bien el día)
- **OrderFlowReversal_v1** LONG: pequeñas ganancias, bien comportado

**Patrón nuevo identificado — DIFERENTE al 17/03:**
- El 17/03 fue: múltiples estrategias LONG en día bajista → correlación EMA(21)
- El 24/03 es: múltiples estrategias SHORT en día alcista → **short bias sistémico sin filtro de tendencia**
- No es correlación estructural entre sí — son estrategias independientes que comparten el mismo error: operar short sin confirmar dirección diaria

**Violación de Units Cap (Curtis Faith / B6-0c):**
- PivotReverse: 4 entradas short simultáneas = 4 slots en misma dirección → habría sido bloqueado por MaxCorrelatedUnits=6 parcialmente
- DarvasBox: qty 15 en un solo trade short = concentración extrema
- **La regla de Units Cap no está implementada → costo hoy: ~$2,000**

**El veredicto estadístico del período completo (02-24/03):**

| Dirección | Net Profit | PF | Trades |
|-----------|-----------|-----|--------|
| Longs | **+$7,248** | 1.17 | 372 |
| Shorts | **-$9,095** | 0.80 | 374 |
| **Total** | **-$1,847** | 0.98 | 746 |

→ **Si solo hubiéramos operado longs el período habría sido +$7,248.**
→ Las estrategias short destruyeron el portafolio. PF=0.80 = pérdida garantizada a largo plazo.

**Raíz del problema:**
- PivotReverse, DarvasBox, SuperTrendWave no tienen filtro de tendencia diaria antes de ir short
- tide_score calculado 1x/día al EOD → no disponible intraday cuando se ejecutan las entradas
- Sin VWAP SD Bands intraday → no hay confirmación bearish antes del entry short

**Sobre "el brain llegó y todo empeoró":**
- El brain (market_monitor_logger.py) NO controla las estrategias — solo logea
- Lo que llegó con el brain = **más estrategias short desplegadas en papel**
- La semana 02-08/03 (+$4,516) fue: pocas estrategias, mercado alcista, mayoría longs
- La semana 09-24/03: más estrategias short añadidas + mercado volátil/alcista = shorts fallan
- No es el brain el problema. Es que los shorts no tienen filtro de dirección

**Regla Midas derivada:**
> Antes de cualquier entrada SHORT, verificar: tide_score_intraday < 0 AND VWAP_SD_band < -1σ AND market_breadth < -0.3. Si alguno falla → NO SHORT, esperar o pasar al siguiente día.
> Las estrategias short son estructuralmente peligrosas en tendencia alcista sin filtro. MaxDD del portafolio es SHORT-first.

---

## LECCIÓN 06 — DIAGNÓSTICO PERÍODO COMPLETO 02-24/03/2026
**P&L total: -$1,847 | 746 trades | 23 días hábiles**

**La verdad de los números:**

| Período | Net Profit | PF | Sharpe | Observación |
|---------|-----------|-----|--------|-------------|
| 02-08/03 (sin brain) | +$4,516 | 1.14 | **2.72** | Pocas estrategias, mercado alcista |
| 09-24/03 (con brain) | -$6,363 | <1 | bajo | Más estrategias short + mercado cambia |
| **Total 02-24/03** | **-$1,847** | **0.98** | 0.42 | MaxDD = -$29,104 |

**Por qué el Sharpe de 2.72 en las primeras semanas era ilusorio:**
- Solo 263 trades en la primera semana → muestra pequeña
- Mercado en tendencia alcista → longs ganaron por momentum, no por edge real
- Los shorts tenían PF=0.39 desde semana 1 — siempre fueron malos
- La "llegada del brain" coincidió con mercado más difícil + más estrategias short

**El veredicto honesto:**
- Las estrategias LONG tienen edge real (PF=1.17 en período completo, Sortino>1.0)
- Las estrategias SHORT no tienen filtro de tendencia = P(ruin) alta en bull market
- **Prioridad #1 de Midas antes de Apex**: filtro de tendencia obligatorio para entradas short

**Lo que este período le enseña a Midas:**
1. Patrón SHORT+tendencia alcista = pérdida garantizada → filtrar con tide_score intraday
2. Entradas simultáneas multislot misma dirección = Units Cap violation → implementar AHORA
3. Días buenos del portafolio: TODOS los días con PivotTrendBreak Long acertando tendencia
4. El portafolio puede generar +$7K en longs en 23 días — el edge existe, está en los longs
5. Los -$29K de MaxDD son en gran parte short strategies = si se filtran, MaxDD cae a <$12K estimado

---

## REGLAS DE MIDAS DERIVADAS DEL DIARIO (resumen ejecutivo)

1. **Correlación estructural StatMean+EMATrend**: tratar como 1 slot cuando coincidan en misma barra
2. **Portfolio Stop Global**: implementar antes de cualquier trade en Apex real
3. **market_breadth_score**: ES+YM+RTY deben confirmar dirección antes de full sizing en NQ
4. **tide_score intraday**: medir cada 60s (no 1x/día) para detectar divergencias a tiempo
5. **Tendencia diaria clara + alta convicción**: activar trailing agresivo en vez de TP fijo
6. **Días de noticias**: News Filter obligatorio — bloquear ±30min de eventos macro HIGH impact
7. **B&Bv5 como swing factor**: en días con B&Bv5 con posición abierta grande → sizing conservador en el resto
8. **Filtro short obligatorio**: antes de ANY entrada short verificar tide_score_intraday < 0 + VWAP < -1σ + breadth < -0.3. Sin los 3 → NO SHORT
9. **Units Cap en mismo día**: máximo 2 estrategias short simultáneas (MaxCorrelatedUnits=2 para shorts en bull market)
10. **Las estrategias LONG tienen edge real** (PF=1.17, +$7,248 en 23 días) — protegerlas de las shorts que arrastran el portafolio
11. **Short PF < 1.0 = no opera**: PivotReverse, DarvasBox, SuperTrendWave tienen PF<1.0 en período real → suspender hasta que brain implemente filtro de tendencia
