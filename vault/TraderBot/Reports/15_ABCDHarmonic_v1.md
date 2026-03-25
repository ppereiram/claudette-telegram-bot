# ABCDHarmonic_v1
> Patrón ABCD Armónico en Renko 35-tick — Entrada en la PRZ (Potential Reversal Zone) | `Strategies/ABCDHarmonic_v1.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (con comm) | **1.54** |
| R² | **0.96** |
| Sortino Ratio | **5.05** |
| Net total (3 años, 1ct) | $7,482 |
| Profit/mes (15ct) | **$3,120** |
| MaxDD (1ct) | **$463** |
| MaxDD (15ct) | **$6,945** ✅ |
| Trades totales (3 años) | 392 (0.52/día) |
| Chart | Renko 35-tick MNQ |

**Sniper de reversiones armónicas.** El patrón ABCD en Renko elimina el ruido temporal y detecta estructuras de Fibonacci puras. PF=1.54 con R²=0.96 y Sortino=5.05 — segunda estrategia del portafolio por Sortino, tercera por profit mensual.

---

## Concepto y edge

### El patrón ABCD Armónico

El ABCD es el patrón harmónico más simple y más consistente del análisis técnico. En lugar de anticipar una reversión, espera que el precio **dibuje la estructura completa** y entra solo en el punto D — la Potential Reversal Zone (PRZ):

```
BULLISH ABCD:
  A ──→ (swing HIGH)
        ↘
          B ─→ (swing LOW)
               ↗
             C ─→ (swing HIGH, más bajo que A)
                  ↘
                    D → COMPRAR (swing LOW, más bajo que B)

Condición estructural: A > C > B > D
Ratios Fibonacci:  BC/AB ∈ [0.382, 0.886]
                   CD/BC ∈ [1.130, 1.618]
```

```
BEARISH ABCD:
  A ──→ (swing LOW)
        ↗
          B ─→ (swing HIGH)
               ↘
             C ─→ (swing LOW, más alto que A)
                  ↗
                    D → VENDER (swing HIGH, más alto que B)

Condición estructural: D > B > C > A
Mismos ratios Fibonacci
```

### Por qué Renko elimina el ruido

En velas temporales (1-min, 5-min), los swings incluyen ruido intrabar — un spike de 10 ticks puede generar un "swing" falso que arruina el patrón. En Renko, cada brick requiere un movimiento mínimo fijo para formarse. Un cambio de dirección de brick = swing confirmado real.

Con Renko 35-tick:
- Cada swing representa **mínimo 35 ticks de movimiento** ($35 por contrato)
- Los pivots son estructurales, no temporales
- Los ratios Fibonacci se aplican sobre movimientos reales, no sobre fluctuaciones

### Por qué Combined (Long + Short) supera Shorts-only

A diferencia de otras estrategias del portafolio donde los shorts tienen R² débil, el ABCD en Renko funciona en ambas direcciones porque:
1. **El patrón es simétrico** — no depende del sesgo alcista del mercado, sino de la estructura del precio
2. **Los longs "rellenan los valles"** de la equity curve — en períodos donde los shorts fallan, los longs compensan
3. **Resultado**: Sortino combinado=5.05 vs Shorts-only Sortino=2.72 con casi el mismo PF

---

## Evolución del backtest — Cómo se llegó a los params ganadores

### Iteración 1 — Brick size

| Brick Size | Trades | R² | Sortino | Resultado |
|---|---|---|---|---|
| Renko 25-tick | 360 | 0.69 | — | ❌ Pivots demasiado pequeños, demasiado ruido |
| Renko 30-tick | 420 | 0.94 | — | ✅ Mejora notable |
| **Renko 35-tick** | **392** | **0.96** | **6.28** | ✅ **Sweet spot** |
| Renko 40-tick | similar | — | — | Similar a Renko 35 |

**Insight**: Igual que PivotTrendBreak (Renko 25) y SuperTrendWave (Renko 40), cada estrategia tiene su brick size óptimo. Renko 35 da suficiente estructura sin sacrificar trades.

### Iteración 2 — Dirección

| Configuración | PF | R² | Sortino | MaxDD |
|---|---|---|---|---|
| Shorts only | 1.33 | 0.95 | 2.72 | — |
| **Long + Short combined** | **1.36** | **0.96** | **6.28** | — |

Combined wins: R² idéntico, Sortino 2.3× mejor. Los longs no diluyen el edge — lo complementan.

### Iteración 3 — Target R:R

| TargetRR | PF | R² | Sortino | Profit/mes (1ct) |
|---|---|---|---|---|
| 2.0 | 1.36 | 0.96 | 6.28 | $166 |
| 3.5 | 1.44 | 0.95 | 3.38 | $166 |
| **4.0** | **1.54** | **0.96** | **5.05** | **$208** |

**El mismo que PivotTrendBreak, VWAPOrderBlock y VWAPFlux**: RR=4.0 es el sweet spot del portafolio. A este RR, los mismos 392 trades generan más profit porque los ganadores crecen sin que los perdedores se multipliquen.

---

## Parámetros ganadores

### Trade Management
| Parámetro | Valor | Descripción |
|---|---|---|
| Quantity | 15 | 15ct → MaxDD $6,945 ≤ Apex $7,500 |
| MaxTradesPerDay | 1 | Solo la mejor señal del día |
| TargetRR | 4.0 | Confirmado óptimo — PF=1.54, Sortino=5.05 |
| BreakevenR | 1.0 | Mueve stop a entrada al llegar a 1R |

### Ratios Fibonacci
| Parámetro | Valor | Descripción |
|---|---|---|
| FibMinBC | 0.382 | BC/AB mínimo — retroceso mínimo de BC |
| FibMaxBC | 0.886 | BC/AB máximo — retroceso máximo de BC |
| FibMinCD | 1.130 | CD/BC mínimo — extensión mínima de D más allá de B |
| FibMaxCD | 1.618 | CD/BC máximo — extensión máxima (Golden Ratio) |

Los rangos [0.382-0.886] y [1.13-1.618] son los estándares del análisis harmónico clásico (Gartley, Bat, Butterfly y Crab quedan incluidos dentro de estos rangos cuando el patrón es un ABCD simple).

### Stop / Target
| Parámetro | Valor | Descripción |
|---|---|---|
| ATRPeriod | 14 | Periodo del ATR para filtro de tamaño de stop |
| StopBufferTicks | 4 | Buffer debajo/encima del punto D (SL estructural) |
| MaxStopATR | 3.0 | Rechaza trades con SL > 3×ATR |

### Filtros
| Parámetro | Valor |
|---|---|
| AllowLong | ON |
| AllowShort | ON |
| UsePrimeHoursOnly | ON |
| StartTime | 93000 (9:30 ET) |
| EndTime | 153000 (15:30 ET) |

---

## Lógica de detección (Renko)

La clave técnica de esta estrategia es la **detección de swings en Renko sin indicadores**:

```csharp
bool currUp = Close[0] > Open[0];  // true = brick alcista
bool prevUp = Close[1] > Open[1];

if (currUp != prevUp)  // cambio de dirección = swing confirmado
{
    var sp = new SwingPoint {
        Price    = Close[1],   // precio del extremo del swing anterior
        BarIndex = CurrentBar - 1,
        IsHigh   = prevUp      // true si el swing previo era alcista (swing HIGH)
    };
    recentSwings.Add(sp);
}
```

En Renko: `Close[1]` del brick anterior **es** el precio exacto del swing (un brick alcista cierra en su máximo; uno bajista cierra en su mínimo). No se necesita ningún indicador de swing adicional.

El sistema mantiene los últimos 8 swings y evalúa el patrón ABCD cada vez que se detecta un nuevo swing (cambio de dirección).

---

## Fortalezas

- **R²=0.96** — segunda curva de equity más lineal del portafolio (empate con PivotTrendBreak)
- **Sortino=5.05** — segunda mejor relación profit/drawdown del portafolio
- **$3,120/mes** — tercer mayor profit mensual del portafolio (15 contratos)
- **Concepto matemático puro** — los ratios Fibonacci son verificables, no hay arbitrariedad
- **Renko = sin ruido temporal** — los swings son estructurales, no artefactos de timeframe
- **Combined L+S** — el patrón ABCD funciona en ambas direcciones, diversificando el edge

## Debilidades / Riesgos

- **PF=1.54 moderado** — el más bajo del grupo de estrategias confirmadas
- **MaxDD=$463/ct** — el más alto por contrato del portafolio (vs $182/ct de PivotTrendBreak)
- **392 trades** — buena muestra estadística, pero concentrada en 3 años de mercado alcista
- **Mismo chart que PivotTrendBreak** — Renko 25 vs Renko 35 operan en similar timeframe estructural. Correlación potencialmente mayor que el resto del portafolio
- **Brick size dependencia** — si la volatilidad del MNQ cambia significativamente, el brick size óptimo puede desplazarse

---

## Análisis de correlación

| Par | Correlación estimada | Motivo |
|---|---|---|
| ABCDHarmonic / PivotTrendBreak | Media-Baja | Mismo instrumento Renko pero lógica opuesta (reversal vs breakout) |
| ABCDHarmonic / SuperTrendWave | Baja | Renko 35 vs Renko 40, trailing vs PRZ |
| ABCDHarmonic / todo lo demás | Muy Baja | Patrón harmónico es independiente de VWAP, OR, momentum |

---

## Sizing para Apex

| Contratos | Net/mes | MaxDD | Viable Apex |
|---|---|---|---|
| 10 | $2,080 | $4,630 | ✅ muy cómodo |
| 12 | $2,494 | $5,556 | ✅ |
| **15** | **$3,120** | **$6,945** | ✅ **recomendado** |
| 16 | $3,326 | $7,408 | ⚠️ límite |
| 17 | $3,534 | $7,871 | ❌ supera $7,500 |

**Recomendación**: 15 contratos máximo. El margen de $555 es ajustado pero viable — el MaxDD de backtest tiende a subestimar el real en live por gaps y slippage.

---

## Relación con PivotTrendBreak_v1

| | ABCDHarmonic_v1 | PivotTrendBreak_v1 |
|---|---|---|
| Chart | Renko 35-tick | Renko 25-tick |
| Setup | Reversal en PRZ (Fibonacci) | Breakout de pivot estructural |
| Señal de entrada | Primer brick en dirección opuesta tras D | Precio rompe swing high/low |
| Dirección | L + S combinado | L + S combinado |
| Sortino | 5.05 | **8.50** |
| PF | 1.54 | **1.92** |
| Profit/mes | $3,120 | **$2,305** |
| Correlación | Media-Baja | — |

Ambas estrategias usan Renko y detectan swings estructurales, pero explotan **el patrón opuesto**: PivotTrendBreak entra cuando el precio rompe un pivot (momentum), ABCDHarmonic entra cuando el precio completa una extensión Fibonacci y revierte (mean-reversion estructural).

---

## Próximos pasos

1. Activar en paper trading (Renko 35-tick, 1 contrato)
2. Verificar que los puntos "D ▲" y "D ▼" aparecen correctamente en el chart
3. Tras 1 mes de datos paper, comparar WR y R/R reales vs backtest
4. Si los resultados paper son consistentes → subir a 15 contratos live
