# VWAPFlux_v1
> VWAP Pullback + Volume Surge institucional | `Strategies/VWAPFlux_v1.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (con comm) | **2.08** |
| R² | **0.91** |
| Sortino Ratio | **0.94** |
| Net total (3 años, 1ct) | $1,766 |
| Profit/mes (20ct) | **$960** |
| MaxDD (1ct) | **$345** |
| MaxDD (20ct) | **$6,900** ✅ |
| Win Rate | 43.64% |
| Win/Loss Ratio | 2.69x |
| Trades totales (3 años) | 55 (0.07/día) |
| Chart | 5-min MNQ |

**Sniper de pullbacks VWAP.** PF=2.08 con muestra baja (55 trades). Altamente selectivo — 1 trade cada ~14 días. Complementa el portafolio por su descorrelación total.

---

## Concepto y edge

### VWAP como imán institucional

El VWAP (Volume Weighted Average Price) es el precio promedio ponderado por volumen del día. Los algoritmos institucionales lo usan constantemente como referencia:
- Ejecutan órdenes grandes en múltiples trozos cerca del VWAP (estrategias TWAP/VWAP)
- Cuando el precio se aleja del VWAP, eventualmente es "atraído" de vuelta

### El patrón "Flux"

Inspirado en el indicador comercial ninZa.co "VWAP Flux":

```
1. Precio sube con fuerza sobre VWAP + 0.5σ durante ≥5 velas (25 min)
   → Tendencia alcista confirmada

2. Precio retrocede a la zona ±0.5σ alrededor del VWAP
   → Pullback a soporte institucional

3. Aparece vela alcista de ALTO VOLUMEN en la zona
   (volumen > 1.5× promedio de las últimas 20 velas)
   → Instituciones comprando en el soporte = señal VF

4. LONG → SL en swing low estructural, TP = 4R
```

### Delta sintético

En lugar de requerir datos de bid/ask volume (VolumeUp/VolumeDown), se usa un proxy:
- Vela alcista (Close ≥ Open) → Delta = +Volume (presión compradora)
- Vela bajista (Close < Open) → Delta = -Volume (presión vendedora)

Este enfoque funciona con datos estándar NT8 y produce resultados equivalentes a delta real en backtesting.

### Por qué solo LONG

Los shorts (precio bajo VWAP rebotando hacia él) tienen R²=0.03 en MNQ — curva completamente aleatoria. MNQ tiene un sesgo estructural alcista que hace que los pullbacks al VWAP en tendencia alcista sean mucho más fiables que los rebotes bajistas.

---

## Evolución del backtest — Cómo se llegó a los params ganadores

| Iteración | Chart | Long/Short | TargetRR | PF | Resultado |
|---|---|---|---|---|---|
| 1 (inicial) | 15-min | Both | 2.5 | 1.35 | Shorts R²=0.03 ❌ |
| 2 | 1-min | Both | 2.5 | 0.81 | Demasiado ruido ❌ |
| 3 | 5-min | Both | 2.0 | 1.35 | Shorts siguen sin edge |
| 4 | 5-min | Long only | 2.0 | **1.75** | R²=0.91 ✅ |
| 5 | 5-min | Long only | 3.5 | **2.05** | Mejor ✅ |
| **6 (final)** | **5-min** | **Long only** | **4.0** | **2.08** | **Óptimo** ✅ |

**Insight clave**: RR=3.5 → RR=4.0 da los mismos 55 trades con los mismos 24 ganadores. El plateau se alcanzó en RR=4.0, igual que BreadButter_v5.

---

## Parámetros ganadores

### Trade Management
| Parámetro | Valor | Descripción |
|---|---|---|
| Quantity | 20 | 20ct → MaxDD $6,900 ≤ Apex $7,500 |
| MaxTradesPerDay | 1 | Solo la mejor señal del día |
| TargetRR | 4.0 | Confirmado óptimo — PF=2.08 |
| BreakevenR | 1.0 | Mueve stop a entrada al llegar a 1R |

### VWAP
| Parámetro | Valor | Descripción |
|---|---|---|
| NearBandSigma | 0.5 | Zona estricta — solo entradas muy cerca del VWAP |
| MinBarsInTrend | 5 | 25 min de tendencia confirmada antes del pullback |

### Volume Delta
| Parámetro | Valor | Descripción |
|---|---|---|
| DeltaSmaPeriod | 20 | Promedio de las últimas 20 velas |
| MinDeltaRatio | 1.5 | Volumen debe ser 1.5× el promedio |
| MinDeltaAbs | 0 | Sin filtro de mínimo absoluto |

### Stop/Target
| Parámetro | Valor | Descripción |
|---|---|---|
| ATRPeriod | 14 | — |
| SwingLookback | 10 | Velas atrás para buscar swing low (SL estructural) |
| MaxStopATR | 4.0 | Rechaza trades con SL > 4×ATR |
| StopBufferTicks | 5 | Buffer debajo del swing low |

### Filtros
| Parámetro | Valor |
|---|---|
| AllowLong | ON |
| AllowShort | **OFF** (R²=0.03 en test) |
| UsePrimeHoursOnly | ON |
| StartTime | 93000 (9:30 ET) |
| EndTime | 153000 (15:30 ET) |

---

## Fortalezas

- **PF=2.08** — segundo PF más alto del portafolio
- **R²=0.91** — curva de equity sólida, crecimiento consistente
- **MaxDD=$345/ct** — el segundo más bajo después de PivotTrendBreak ($182/ct)
- **Sin datos especiales** — funciona con cualquier provider NT8 estándar
- **Concepto institucional genuino** — el VWAP pullback es un setup real de traders profesionales
- **Descorrelación total** — 1 trade cada 14 días, lógica completamente diferente al resto del portafolio

## Debilidades / Riesgos

- **55 trades en 3 años** — la muestra más baja del portafolio. Un PF=2.08 con 55 trades tiene un intervalo de confianza amplio
- **0.07 trades/día** — puede pasar 2-3 semanas sin ningún trade
- **Delta sintético** — es una aproximación. Con datos de bid/ask reales el PF podría variar
- **NearBandSigma=0.5** — si el VWAP σ es pequeño en días de bajo volumen, pocas velas califican como "en zona"

---

## Análisis de la muestra baja

Con solo 55 trades, el PF tiene un intervalo de confianza amplio. Estimación conservadora:

| Escenario | PF esperado |
|---|---|
| Optimista (backtest se repite) | 2.08 |
| Conservador (CI 90%) | ~1.50-1.70 |
| Pesimista (over-fit) | ~1.20-1.40 |

**Recomendación**: Tratar el PF real como ~1.60 para sizing conservador, hasta tener más datos en vivo.

---

## Sizing para Apex

| Contratos | Net/mes | MaxDD | Viable Apex |
|---|---|---|---|
| 10 | $480 | $3,450 | ✅ muy cómodo |
| 15 | $720 | $5,175 | ✅ |
| **20** | **$960** | **$6,900** | ✅ **recomendado** |
| 21 | $1,008 | $7,245 | ⚠️ límite |

**Recomendación**: 20 contratos, pero dado el bajo trade count, considerar empezar con 10ct hasta tener datos reales que confirmen el edge.
