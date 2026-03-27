---
name: manual_buenas_practicas
description: Manual de reglas operativas derivadas de datos reales de paper trading — cada regla tiene una pérdida real detrás. Este es el escudo para Darwin/X.
type: project
---

# Manual de Buenas Prácticas — Midas Bot
> **Origen:** 18+ días de paper trading, 900+ trades, 8 lecciones documentadas con pérdidas reales
> **Propósito:** Cada regla aquí evita pérdidas reales cuando se opere con capital externo
> **Filosofía:** *Que lo pierdan todo en papel para que no lo pierdan en real*

---

## NIVEL 1 — REGLAS DE ORO (nunca romper)

Estas reglas no tienen excepción. Si el brain las viola, algo está mal en el código.

| # | Regla | Origen | Costo si se ignora |
|---|---|---|---|
| G1 | `Slippage = 1` en todas las estrategias | Estándar desde 26/02 | Backtests irreales |
| G2 | Nunca corregir el Filtro Accidental (ULTRA/SCALPER) | Diseño intencional | Perder el edge real |
| G3 | Longs+Shorts combinados, nunca separar | Validado en backtest | Pérdida del edge competitivo |
| G4 | Backtests siempre con comisiones | Estándar | Sobreestimar edge |
| G5 | R² > 0.85 mínimo para entrar al portafolio | Criterio cuantitativo | Estrategias sin edge estadístico |
| G6 | MaxDD debe caber en Apex $7,500 | Restricción de cuenta | Blown account |
| G7 | Tiempos siempre en ET (`GetEtTime()`) | Estándar código | Desfases en señales |
| G8 | `market_monitor_logger.py` CADA DÍA sin excepción | Combustible Markov | Dataset incompleto → Markov ciego |

---

## NIVEL 2 — FILTROS DE CONTEXTO (cuándo NO operar)

### F1 — GAP FILTER (derivado Lección 08, 26/03/2026)
**Condición:** `abs(precio_apertura - precio_cierre_ayer) > 50 puntos`

```
gap_day = True
```

**Reglas cuando gap_day=True:**
- Primeros 15 minutos: SIZE × 0.25 en TODAS las estrategias
- StatMeanCross y EMATrendRenko: NO operan en primera barra Renko post-gap
- Esperar al segundo brick Renko confirmatorio antes de cualquier entrada momentum
- DarvasBox y PivotReverse: operan normal (lógica estructural, no momentum)
- Después de capturar bounce en gap-down: NO short hasta VWAP_intraday confirma nueva tendencia

**Por qué:** En gap de 113 pts (26/03), StatMean+EMATrend SHORT murieron en 98 segundos (-$1,016). El primer brick de gap es precio de descubrimiento, no señal de trend.

**Implementación:** `check_pre_market_gap()` en `market_monitor_logger.py` a las 9:25 AM ET

---

### F2 — TIDE FILTER (derivado Lección 01+07, múltiples días)
**Condición:** `tide_score` calculado por `market_monitor_logger.py`

| tide_score | Estado | Acción |
|---|---|---|
| > +1.0 | Bull fuerte | Solo longs, shorts con size×0.5 |
| +0.4 a +1.0 | Bull moderado | Longs normal, shorts con filtro adicional |
| -0.4 a +0.4 | Conflicto / neutral | SIZE×0.5 todo el portafolio |
| -0.4 a -1.0 | Bear moderado | Shorts normal, longs con filtro adicional |
| < -1.0 | Bear fuerte | Solo shorts, longs con size×0.5 |

**Nota crítica:** `swim_ok=False` NO significa "no tradear". Significa "mercado conflictivo → size reducido". El 25/03 fue el mejor día con swim_ok=False (+$5,318).

---

### F3 — CHOPPINESS FILTER (derivado Lección 01)
**Condición:** `choppiness_15M > 61.8` (rough)

```
sea_state = "rough" → SIZE×0.25 en estrategias de momentum
```

Este es el único caso donde "no tradear" es la respuesta correcta para StatMean/EMA.
Gap + rough = SIZE×0.10 o pausa total para momentum.

---

### F4 — ROLLOVER FILTER (derivado Lección 06, 16/03/2026)
**Condición:** Semana de rollover de contrato (~2da semana de Marzo/Junio/Sep/Dic)

- No evaluar días $0 como "sin señal" durante rollover — es silencio técnico
- Excluir semana de rollover del análisis de frecuencia de Markov
- Re-cargar estrategias Renko después de rollover — esperar 1-2 días para estabilización de EMAs
- Marcar en calendario: semana del rollover = mantenimiento obligatorio

---

### F5 — DIRECTIONAL FILTER para SHORTS (derivado Lección 04, 24/03/2026)
**Diagnóstico:** Shorts = -$9,095 en 23 días (PF=0.80). Longs = +$7,248 (PF=1.17).

**Estrategias que NO pueden operar en Short sin filtro direccional:**
- PivotReverse_v1: Ambidiestra — SHORT solo si tide_score < -0.5 + VWAP_intraday bajista
- DarvasBox_v1: SHORT solo si tide_score < -0.3 + no es gap day
- SuperTrendWave: SHORT solo si trend_4H = bear

**Regla simple hasta implementar VWAP_intraday:**
> Si `tide_score > 0` → bloquear nuevos shorts en PivotReverse, DarvasBox, SuperTrendWave

---

## NIVEL 3 — GESTIÓN DE CORRELACIÓN

### C1 — StatMean + EMATrend = 1 SLOT (derivado Lección 01+05)
**Regla:** StatMeanCross_v1 y EMATrendRenko_v1 comparten EMA(21) → correlación estructural, no accidental.

Cuando ambas disparan en la misma dirección simultáneamente:
- Tratar como UNA posición, no dos
- Si el Brain asigna SIZE=20 al portafolio → StatMean+EMA juntos = máximo 10 contratos totales

**Costo histórico de ignorar:** 17/03 -$8,906 (lección 01), 26/03 -$1,016 en 98s (lección 08)

---

### C2 — UNITS CORRELATION CAP (derivado Turtle/Lección 08)
**Regla:** Máximo 6 unidades correlacionadas activas simultáneamente.

```csharp
// En NinjaTrader C# — global portfolio check
int MaxCorrelatedUnits = 6;
```

Si en el momento de una señal ya hay 6+ posiciones en la misma dirección macro → no entrar.

**Costo histórico:** 17/03 — StatMean+EMA+BBv5 Long simultáneos → -$8,906

---

### C3 — NO MISMO EVENTO = MISMA PÉRDIDA (derivado Lección 01+08)
**Regla:** Si dos estrategias entran en el mismo brick de Renko → misma señal → misma pérdida.

Verificar antes de ejecutar: ¿entró otra estrategia en los últimos 30 segundos en la misma dirección?
Si sí → tamaño reducido al 50% para la segunda estrategia.

---

## NIVEL 4 — GESTIÓN DE TAMAÑO (SIZING)

### S1 — COMEBACK RATIO (derivado Survival Guide/Lección 08)
**Fórmula:** CR = 1/(1-loss_pct) - 1

| DD actual | CR necesario para recover | Size permitido |
|---|---|---|
| 5% | 5.3% | Normal |
| 10% | 11.1% | Normal |
| 20% | 25% | SIZE×0.75 |
| 30% | 42.9% | SIZE×0.50 |
| 40% | 66.7% | SIZE×0.25 |
| 50% | 100% | Pausa — revisar |

Aplicar sobre DD intraday desde el high del día (no desde equity total).

---

### S2 — SIZE POR CONTEXTO (consolidado)
| Condición | Size multiplier |
|---|---|
| Normal (swim_ok=True, no gap, ci<61.8) | 1.0x |
| swim_ok=False (conflicto) | 0.5x |
| gap_day=True (primeros 15 min) | 0.25x |
| sea_state=rough | 0.25x |
| gap_day + rough | 0.10x o pausa |
| DD intraday > 30% | 0.50x |
| DD intraday > 40% | 0.25x |
| Rollover week | 0.50x |

---

## NIVEL 4B — REGLA DE NO INTERVENCIÓN MANUAL

**Origen:** 26/03/2026 — BBv5 Short +$3,022 → Pablo entró Long manual → -$897. Costo: -$633.

| Situación | Regla |
|---|---|
| Trade activo en cualquier estrategia | Cero intervención. Manos fuera. |
| Ganador grande corriendo (popcorn) | No cerrar manualmente — dejar el sistema operar |
| Micro-rebote después de un Short | No es señal de Long — puede ser trampa |
| Única excepción válida | Portfolio Stop Nivel 7 (pérdida día > $5,000) |

**Por qué:** El miedo al "popcorn trade" (ver un ganador grande evaporarse) es la emoción más costosa del trading intraday. Genera exactamente lo que teme: cierra el ganador y abre un perdedor.

**Costo documentado:** -$633 en una sola intervención (26/03/2026). En real money × 10 contratos = -$6,330.

---

## NIVEL 5 — PATRONES POR ESTRATEGIA

### StatMeanCross_v1
**Setup ideal:** Gap apertura + momentum confirmado en primera barra Renko = condición óptima
- Si tide_score > 0 + apertura con momentum → NO filtrar, dejar operar full size
- MAE máximo en setup ideal: $30 por contrato
- **NO operar:** Primera barra post-gap >50 pts, sea_state=rough, tide_score opuesto a dirección

### EMATrendRenko_v1
- Correlacionada estructuralmente con StatMean (EMA(21))
- Tratar siempre como 1 slot conjunto con StatMean
- **NO operar:** mismas condiciones que StatMean

### PivotReverse_v1
- Ambidiestra con edge real en ambas direcciones cuando alineada
- SHORT: solo si tide_score < -0.5 + confirmación intraday
- LONG: solo si tide_score > 0 + confirmación intraday
- Sin filtro = moneda al aire con tamaño grande (+$3,106 hoy / -$1,048 ayer)

### DarvasBox_v1
- Edge de persistencia: primer stop = "sonda", segunda entrada en misma dirección = real
- En gap-down: LONG es correcto (gap fill). SHORT posterior requiere VWAP confirm.
- No penalizar en TfT por stops iniciales si la dirección final es correcta
- **Cuidado:** Después de 2 stops consecutivos en misma dirección → pausa esa dirección por 30 min

### SuperTrendWave
- Funciona en ambas direcciones cuando mercado tiene tendencia clara
- SHORT: solo si trend_4H = bear
- LONG: solo si trend_4H = bull
- En día conflicto (4H≠1D): size×0.50

### BreadButter_ULTRA / SCALPER
- Filtro Accidental activo → 1 trade/día por diseño → NO tocar
- Losses pequeños son normales — es el costo del "seguro"

### OrderFlowReversal_v1
- No operar contra tendencia macro clara
- Si tide_score bear fuerte → no Long. Si tide_score bull fuerte → no Short.

---

## NIVEL 6 — CHECKLIST PRE-MERCADO (9:25 AM ET)

Ejecutar antes de que abran las estrategias:

```
□ 1. ¿GAP > 50 puntos? → Si sí: gap_day=True, SIZE×0.25 primeros 15 min
□ 2. ¿tide_score de ayer? → Definir sesgo direccional del día
□ 3. ¿sea_state? → Si rough: momentum strategies en pausa
□ 4. ¿Semana de rollover? → Precaución, revisar contratos
□ 5. ¿Noticias macro? (FOMC, NFP, CPI) → SIZE×0.25 o pausa total
□ 6. ¿DD intraday ayer > 30%? → Ajustar sizing según S2
□ 7. ¿breadth_score = -3 + tide_score < 0? → Bear confirmado, no longs agresivos
```

---

## NIVEL 7 — SEÑALES DE ALARMA (Portfolio Stop)

Condiciones que activan pausa de TODO el portafolio:

| Señal | Umbral | Acción |
|---|---|---|
| Pérdida intraday | > $3,000 en < 2 horas | Pausa 1 hora, revisar condiciones |
| Pérdida intraday | > $5,000 cualquier momento | Stop total del día |
| 3+ stops consecutivos en misma dirección | En < 30 minutos | Bloquear esa dirección por 1 hora |
| Correlación activa: 4+ estrategias misma dirección | Simultáneamente | No abrir más en esa dirección |
| Gap + rough + todos los stops en primeros 5 min | Combinado | Stop total del día |

---

## REGISTRO DE DÍAS CRÍTICOS

| Fecha | P&L | Condición | Regla violada | Regla derivada |
|---|---|---|---|---|
| 06/03 | -$11,920 | Sin análisis forense | Portfolio Stop inexistente | G6 + F2 + nivel 7 |
| 17/03 | -$8,906 | StatMean+EMA+BBv5 Long simultáneos | C1+C2 | Correlación = 1 slot |
| 20/03 | -$X,XXX | StatMean+EMA Short simultáneos, bull market | F5 | Directional filter |
| 24/03 | -$2,206 | PivotReverse Short en mercado alcista | F5 | tide_score direccional |
| 25/03 | +$5,318 | DarvasBox+PivotReverse+StatMean alineados | — | Alineación = win |
| 26/03 mañana | -$2,263 | GAP 113pts, momentum strategies en gap direction | F1 | GAP FILTER |
| 26/03 tarde | **+$1,024** (final) | BBv5 Short capturó -381pts del día. Pablo intervino Long → -$633 innecesario | Nivel 4B | NO INTERVENCIÓN MANUAL |

---

## EL OBJETIVO FINAL

Cada regla aquí es una pérdida de papel que no será una pérdida real.

Cuando Midas opere en Apex real → Darwin/X:
- El Gap Filter (F1) habría ahorrado ~$1,000 hoy solo
- El Directional Filter (F5) habría ahorrado -$9,095 en shorts durante marzo
- El Correlation Cap (C2) habría ahorrado -$8,906 el 17/03
- El Portfolio Stop (Nivel 7) habría cortado el -$11,920 del 06/03

**Total protegido por este manual: ~$30,000 en 18 días de paper**

En Apex con capital real, eso habría sido una blown account. En paper, es educación.

> *"El underdog más peligroso es el que no para de aprender."*
> — El que llega a Darwin/X 2027 no es el más listo sino el que más veces falló en papel.
