# LWDonchianBreak_v1
> Larry Williams — Donchian Channel Breakout semanal en 15-min | `Strategies/LWDonchianBreak_v1.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (con comm) | **1.61** |
| R² | **0.84** |
| Sortino Ratio | **1.09** |
| Net total (3 años, 1ct) | $3,257.70 |
| Profit/mes (6ct) | **$522** |
| MaxDD (1ct) | **$1,026.40** |
| MaxDD (6ct) | **$6,156** ✅ |
| Trades totales (3 años) | 162 (0.21/día) |
| WR | 35.19% |
| Win/loss ratio | 2.96x |
| Chart | 15-min MNQ |

**Breakout semanal de canal de precio puro.** El Donchian Channel de 133 barras en 15-min captura exactamente ~1 semana de trading (133×15min ÷ 390min/día = 5.1 días). Cuando el precio rompe el máximo semanal con momentum (Williams %R > -50) y volumen, la señal es institucional. Única estrategia de breakout de canal en el portafolio — diversificación genuina.

---

## Concepto y edge

### Larry Williams y el breakout semanal

Larry Williams convirtió $10,000 en $1.1 millón (+11,300%) en 12 meses en el World Cup Trading Championship. Enseñó la misma estrategia a su hija Michelle Williams, quien ganó el campeonato de 1997. El concepto base es el **Donchian Channel Breakout**: entrar cuando el precio rompe el máximo/mínimo de N períodos.

El Donchian Channel (creado por Richard Donchian) es el indicador que usaron los famosos "Turtle Traders" de Richard Dennis en los años 80. Larry Williams lo adaptó con filtros de momentum y volumen.

### Los 3 filtros

```
LONG (todos deben cumplirse simultáneamente):
  1. Close[0] > Donchian.Upper[1]   → Precio rompe máximo de 1 semana
  2. Williams %R > -50              → Momentum en zona alcista (upper half -100 to 0)
  3. Volume > VolSMA + Close > Open → Volumen real + vela alcista confirma
```

### Por qué 15-min y no 5-min

El backtest confirma que 5-min no funciona en MNQ con esta estrategia:
- 5-min, Donchian=96 (8h): PF=1.07, R²=0.25, Sortino=0.29 ❌
- 5-min, Donchian=96, Stop=1.5: PF=0.74 (pérdida) ❌❌

**El 15-min elimina el ruido intrabar.** En MNQ, el nivel de volatilidad de 5-min genera demasiadas roturas de canal falsas. A 15-min, cada barra requiere un movimiento más sostenido, y el Donchian captura estructura real.

### Por qué Donchian=133 (el "breakout semanal")

| Donchian | Barras × 15min | Lookback real | PF | R² |
|---|---|---|---|---|
| 96 | 1,440 min | ~1 día | 1.07 ❌ | 0.25 |
| **133** | **1,995 min** | **~5 días = 1 semana** | **1.61** | **0.84** |
| 150 | 2,250 min | ~6 días | 1.43 | 0.88 |

El "sweet spot" es el breakout **semanal**. Romper el máximo de la semana anterior es un nivel que los traders institucionales observan. No es overfitting: es una razón conceptual.

### Por qué AllowShort=OFF

En los 5 backtests realizados con diferentes configuraciones, los shorts aportaron exactamente **$0.00** en todos los casos. MNQ (Nasdaq) tiene un sesgo estructural alcista: los breakouts bajistas en una semana se recuperan con frecuencia, mientras que los alcistas tienen follow-through real.

---

## Evolución del backtest — Cómo se llegó a los params ganadores

### Iteración 1 — Timeframe

| Timeframe | Resultado |
|---|---|
| 5-min (diseño original) | PF=1.07, R²=0.25 ❌ — demasiado ruido |
| **15-min** | **PF=1.57-1.61, R²=0.84-0.85** ✅ |

### Iteración 2 — Donchian Period

| Donchian | Timeframe | PF | R² | Sortino |
|---|---|---|---|---|
| 96 | 15-min | ~1.07 | 0.25 | — |
| **133** | **15-min** | **1.61** | **0.84** | **1.09** |
| 150 | 15-min | 1.43-1.60 | 0.86-0.88 | 0.66-0.96 |

133 domina: mayor PF con R² aceptable.

### Iteración 3 — Stop / RR

| Stop | RR | MaxTrades | PF | R² | Sortino | MaxDD |
|---|---|---|---|---|---|---|
| 0.8 | 3 | 3 | 1.57 | 0.85 | 1.12 | $1,157 |
| **0.8** | **3** | **1** | **1.61** | **0.84** | **1.09** | **$1,026** |
| 1.5 | 3 | 1 | 0.74 | 0.70 | -0.38 | $4,998 ❌ |
| 1.5 | 4 | 1 | 1.43 | 0.88 | 0.66 | $1,220 |
| 1.0 | 3 | 1 | 1.60 | 0.86 | 0.96 | $1,376 |

**Stop=0.8 ATR en 15-min** (no en 5-min): el ATR de 15-min es ~3× más amplio que el de 5-min, así que 0.8× ATR(15-min) equivale a ~2.4× ATR(5-min). No es un stop ajustado en términos absolutos.

**MaxTrades=1** vs MaxTrades=3: PF mejora (1.61 vs 1.57), MaxDD baja ($1,026 vs $1,157). Los trade extras del MaxTrades=3 son señales de menor calidad.

---

## Parámetros ganadores

### Trade Management
| Parámetro | Valor | Descripción |
|---|---|---|
| Quantity | 6 | 6ct → MaxDD $6,156 ≤ Apex $7,500 |
| MaxTradesPerDay | 1 | Solo la mejor señal del día |

### Donchian Channel
| Parámetro | Valor | Descripción |
|---|---|---|
| DonchianPeriod | 133 | 133×15min = ~5 días = breakout semanal |

### Williams %R (LWTI)
| Parámetro | Valor | Descripción |
|---|---|---|
| WilliamsRPeriod | 21 | Momentum: >-50 = alcista, <-50 = bajista |

### Volume
| Parámetro | Valor | Descripción |
|---|---|---|
| VolumeMAPeriod | 20 | Volumen por encima de promedio 20 barras |

### Stop / Target
| Parámetro | Valor | Descripción |
|---|---|---|
| ATRPeriod | 7 | Periodo ATR para stop dinámico |
| StopMultiple | 0.8 | Stop = 0.8× ATR(15-min) |
| TargetRR | 3.0 | Target = 3× stop |
| BreakevenR | 1.0 | Mueve stop a entrada al alcanzar 1R |

### Filtros
| Parámetro | Valor |
|---|---|
| AllowLong | ON |
| AllowShort | **OFF** — $0 en todos los backtest |
| UsePrimeHoursOnly | ON |
| StartTime | 93000 (9:30 ET) |
| EndTime | 153000 (15:30 ET) |

---

## Fortalezas

- **Concepto sólido** — el breakout semanal de Donchian es la base de las "Turtle Traders" y Larry Williams
- **Diversificación genuina** — único en el portafolio (canal de precio puro vs pivots estructurales)
- **162 trades** — muestra estadísticamente significativa
- **AllowShort=OFF confirmado** — consistente con el bias alcista de MNQ
- **Intraday 100%** — `IsExitOnSessionCloseStrategy=true`, compatible Apex

## Debilidades / Riesgos

- **R²=0.84** — por debajo del ideal >0.90 del portafolio; equity curve con más rugosidad
- **Sortino=1.09** — el más bajo de las estrategias activas del portafolio
- **Recovery time ~266 días** — casi 9 meses para recuperar MaxDD
- **MaxDD $1,026/ct** — limita a 6 contratos para Apex ($6,156 MaxDD)
- **$522/mes** — contribución modesta vs costo de gestión

---

## Análisis de correlación

| Par | Correlación estimada | Motivo |
|---|---|---|
| LWDonchian / PivotTrendBreak | Baja | Ambos son breakout, pero Donchian = canal de precio vs pivots estructurales |
| LWDonchian / ABCDHarmonic | Muy baja | Breakout vs reversal. Renko vs 15-min |
| LWDonchian / VWAPOrderBlock | Baja | Breakout semanal vs order block + VWAP |
| LWDonchian / OpeningRange | Baja | Horario solapado pero lógica opuesta |
| LWDonchian / todo | **Baja-Media** | Único Donchian Channel en el portafolio |

---

## Sizing para Apex

| Contratos | Net/mes | MaxDD | Viable Apex |
|---|---|---|---|
| 4 | $348 | $4,106 | ✅ muy cómodo |
| 5 | $435 | $5,132 | ✅ |
| **6** | **$522** | **$6,156** | ✅ **recomendado** |
| 7 | $609 | $7,182 | ⚠️ límite |
| 8 | $696 | $8,211 | ❌ supera $7,500 |

---

## Rol en el portafolio

Esta es la **única estrategia de breakout de canal** del portafolio. PivotTrendBreak rompe pivots estructurales (mínimos/máximos recientes con lógica de swing); LWDonchianBreak rompe el canal de precio puro de la semana anterior — dos edges conceptualmente distintos. La correlación entre ellos es baja a pesar de ser ambos "breakout strategies."

Calificada como **estrategia tier-2**: PF sólido, concepto válido, pero R²=0.84 y Sortino=1.09 son los más bajos de las estrategias activas. Contribución modesta ($522/mes) pero diversificación real.

---

## Próximos pasos

1. Activar en paper trading (15-min MNQ, 1 contrato)
2. Verificar que las señales de entrada visualmente coinciden con breakouts semanales en el chart
3. Tras 1 mes de datos paper, comparar WR y R/R reales vs backtest
4. Si paper es consistente → subir a 6 contratos live
