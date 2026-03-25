# VolumeProfile_POC_v1 — Reporte de Desarrollo

> Estado: ❌ DESCARTADA — POC sintético sin Tick Replay insuficiente para el edge
> Chart: 15-min | MNQ | mejor resultado encontrado

---

## Concepto

El **POC (Point of Control)** es el precio donde se negoció más volumen en la sesión — el "precio justo" del mercado según los participantes institucionales. A diferencia del VWAP (promedio ponderado), el POC es el nivel de **máxima aceptación** de precio.

Los grandes jugadores defenden el POC como referencia: si el precio retrocede al POC después de haberse alejado, suelen absorber posiciones allí, generando rebotes estructurales.

```
Precio sobre POC N barras → pullback al POC (zona ±PocZoneTicks) → cierre SOBRE POC → LONG
Precio bajo POC N barras  → rebote al POC (zona ±PocZoneTicks) → cierre BAJO  POC → SHORT
```

**Diferencia con VWAPFlux_v1**:
| Característica | VWAPFlux_v1 | VolumeProfile_POC_v1 |
|---|---|---|
| Ancla | VWAP (precio promedio ponderado) | POC (precio de máximo volumen) |
| Cálculo | Continuo durante la sesión | Histograma acumulado tick-by-tick |
| Dirección | Long only | Long + Short según posición vs POC |
| Señal | Pullback a banda VWAP ±0.5σ | Test del POC desde arriba/abajo |

**Diferencia clave**: VWAP es la media ponderada (podría nunca ser "tocado" exactamente). El POC es el nivel discreto más negociado — más específico como soporte/resistencia.

---

## Cálculo del POC (sin Tick Replay)

Sin acceso a datos tick-by-tick, se distribuye el volumen de cada barra uniformemente entre Low y High (1 bucket por tick de precio):

```
Por cada barra:
  volPerTick = Volume[0] / (highTick - lowTick)
  Para cada tick i entre lowTick y highTick:
    volByTick[i] += volPerTick

POC = tick con mayor volByTick acumulado desde PocTrackStart
```

Esta aproximación asume distribución uniforme de volumen dentro del rango de la barra. En barras de 5-min con movimiento moderado (típico en MNQ), es una buena aproximación. En barras con gaps extremos, puede subestimar el volumen en el extremo del rango.

**Reset del histograma**: cada vez que `etDate != pocSessionDate` y `etTime >= PocTrackStart` → se limpia el diccionario y se empieza a acumular de nuevo.

---

## Lógica de Entrada

### Separación "contexto" vs "señal"

El streak de barras usa `Close[1]` (barra anterior) para contar cuántas barras PREVIAS estuvieron sobre/bajo el POC. La barra actual es exclusivamente la barra de "señal". Esto evita que la señal se cuente a sí misma como contexto.

### LONG
1. `barsAbovePoc >= MinBarsInTrend` — N barras PREVIAS cerraron sobre POC
2. `Low[0] <= pocPrice + PocZoneTicks × TickSize` — barra actual toca zona POC
3. `Close[0] > pocPrice` — cierra sobre POC (se defiende)
4. `Volume[0] >= SMA(Volume, 20)[0] × MinVolRatio` — convicción
5. `(Close[0] - SL) <= MaxStopATR × ATR(14)[0]` — stop razonable
6. **SL**: `pocPrice - StopBufferTicks × TickSize` (estructural: bajo el POC)
7. **TP**: `entry + (entry - SL) × TargetRR`

### SHORT (espejo)
1. `barsBelowPoc >= MinBarsInTrend`
2. `High[0] >= pocPrice - PocZoneTicks × TickSize`
3. `Close[0] < pocPrice`
4. Volumen confirma
5. **SL**: `pocPrice + StopBufferTicks × TickSize`

---

## Parámetros Iniciales para Backtest

```
Chart: 5-min MNQ, ETH session

1. POC Settings
   PocTrackStart  = 90000   // 9:00 ET — 30 min para estabilizar antes de operar
   PocZoneTicks   = 6       // tolerancia de ±6 ticks = ±$1.50
   MinBarsInTrend = 3       // 3 barras = 15 min sobre/bajo POC

2. Risk / Reward
   TargetRR        = 3.0
   BreakevenR      = 1.0
   StopBufferTicks = 5
   MaxStopATR      = 3.0    // skip si stop > 3×ATR desde entry

3. Volume Filter
   UseVolumeFilter = true
   VolumePeriod    = 20
   MinVolRatio     = 1.2

4. Trade Management
   MaxTradesPerDay = 1
   Quantity        = 1
   AllowLong       = true
   AllowShort      = true   // probar también Long-only

5. Horario (ET)
   PrimeStart = 93000       // 9:30 AM
   PrimeEnd   = 153000      // 3:30 PM
```

---

## Variables a Optimizar en Backtest

| Parámetro | Rango a probar | Motivo |
|---|---|---|
| PocZoneTicks | 4, 6, 8, 12 | Tolerancia del toque — más grande = más trades |
| MinBarsInTrend | 2, 3, 5 | Definición de "tendencia" antes del test |
| TargetRR | 2.0, 3.0, 4.0 | Sweet spot igual que otras estrategias |
| MinVolRatio | 1.0, 1.2, 1.5 | Agresividad del filtro de volumen |
| MaxStopATR | 2.0, 3.0, 4.0 | Trade-off calidad vs frecuencia |
| MaxTradesPerDay | 1, 2 | Más trades vs más selectividad |
| AllowShort | ON/OFF | MNQ alcista — verificar si shorts ayudan |
| PocTrackStart | 83000, 90000 | Incluir pre-market o no |

---

## Criterios de Validación

- PF > 1.50 con comisiones y Slippage=1
- R² > 0.85
- Sortino > 2.0
- Trades ≥ 100 en 3 años (POC = máx 1 nivel/día, frecuencia natural baja)
- MaxDD/ct razonable para caber en Apex

> Nota: se acepta menor frecuencia que otras estrategias (similar a VWAPFlux con 55 trades)
> porque el POC tiene alta especificidad como nivel institucional.

---

## Por Qué Tiene Edge Potencial en MNQ

1. **Institucionales usan el POC**: es el precio donde se negoció más — ahí tienen posiciones, ahí van a defender
2. **Nivel dinámico**: a diferencia de pivots estáticos, el POC refleja el volumen real del día
3. **SL estructural**: el stop está BAJO el POC (si el POC cae, la tesis es incorrecta)
4. **Complementa el portafolio**: POC es diferente a VWAP, pivots, Darvas, y order flow — añade diversificación conceptual

---

## Resultados del Backtest (02/03/2026)

### Mejor resultado encontrado (15-min, params base)

```
Params: PocTrackStart=90000, PocZone=6tk, MinBarsInTrend=3,
        RR=4, BE=1R, StopBuffer=4, MaxStopATR=2,
        MaxTrades=1, VolRatio=1.18, 9:30-15:30 ET

Trades:    456 total (Long=423, Short=33)   ← desequilibrio severo
PF:        1.21  (Long=1.17 | Short=1.68)  ❌
R²:        0.65  (Long=0.51 | Short=0.76)  ❌
Sortino:   0.46                             ❌ (mínimo 2.0)
MaxDD:     -$1,294.20 (1ct)
WR:        23.46%  Win/Loss: 3.95x
Profit/mes: $78.45 (1ct)
```

### Diagnóstico

**Problema Long (423 trades, PF=1.17)**: En un mercado alcista como MNQ 2023-2026, siempre hay 3+ barras consecutivas sobre el POC → `MinBarsInTrend=3` está activo permanentemente → la estrategia se convierte en "compra cada pullback en bull market". El PF=1.17 apenas cubre comisiones; sin edge real.

**Problema estructural del POC sintético**: Al distribuir el volumen uniformemente entre Low y High, el POC calculado puede estar a varios ticks del POC real. Con una zona de solo 6 ticks, el precio puede no tocar la zona sintética aunque sí toque el POC real. Esto genera señales perdidas y falsas simultáneamente.

**Short (33 trades, PF=1.68)**: El único lado con algo de edge, pero la muestra es demasiado pequeña (33 trades) y R²=0.76 está bajo el umbral.

### Conclusión: DESCARTADA

El concepto POC como S/R tiene edge institucional real, pero requiere **Tick Replay** para calcular el POC con precisión suficiente para este tipo de entrada. Sin datos tick-by-tick, la aproximación sintética es demasiado cruda.

Requisitos para revisar en el futuro:
- Activar Tick Replay en NinjaTrader 8 (recurso computacional elevado)
- O usar el indicador nativo de NT8 `VolumeProfile` con datos de Tick Replay habilitados

---

## Estado Final

- ✅ Código creado (02/03/2026): `Strategies/VolumeProfile_POC_v1.cs`
- ✅ Backtest completado 02/03/2026 — mejor resultado: PF=1.21, R²=0.65, Sortino=0.46
- ❌ **DESCARTADA**: todas las métricas bajo umbral mínimo. POC sintético sin Tick Replay es insuficiente
- 📁 Código archivado — no proceder a paper trading

---

## Archivos

- Código: `Strategies/VolumeProfile_POC_v1.cs`
- Reporte: `Reports/20_VolumeProfile_POC_v1.md`
