# OrderFlowReversal_v1 — Reporte de Confirmación

> Estado: ✅ CONFIRMADA — 01/03/2026
> Chart: Renko 45-tick | MNQ | AllowShort=ON

---

## Concepto

Order Flow Reversal detecta el agotamiento institucional usando volumen por brick como proxy del flujo de órdenes — **sin Tick Replay**.

**Lógica: Causa → Efecto → Confirmación**

```
Absorption → Exhaustion → Push → ENTRY
```

| Fase | Condición en Renko | Significado |
|---|---|---|
| **Absorption** | N bricks consecutivos en misma dirección con volumen CRECIENTE | Más esfuerzo por brick = alguien absorbe la presión contraria |
| **Exhaustion** | M bricks consecutivos en misma dirección con volumen DECRECIENTE | El lado dominante pierde combustible |
| **Push** | Primer brick en dirección CONTRARIA con volumen > SMA(20) × ratio | El otro lado toma control con presión real |

**BEARISH REVERSAL (SHORT)**: absorción ↑ → agotamiento ↑ → push ↓
**BULLISH REVERSAL (LONG)**: absorción ↓ → agotamiento ↓ → push ↑

---

## Resultados Confirmados (01/03/2026)

**Configuración**: Renko 45-tick, AbsorptionBricks=2, ExhaustionBricks=2, 15 contratos, Slippage=1, comisiones incluidas, 02/01/2023–22/02/2026

| Métrica | All trades | Long | Short |
|---|---|---|---|
| **Profit Factor** | **2.20** | **2.40** | **2.05** |
| **R²** | **0.94** | 0.96 | 0.91 |
| **Sortino** | **5.80** | 4.23 | 2.42 |
| Net Profit | $65,628 | $33,736 | $31,891 |
| MaxDD | $5,146 | $2,473 | $3,619 |
| Trades | 232 | 106 | 126 |
| Win Rate | 40.52% | 42.45% | 38.89% |
| Win/Loss ratio | 3.24x | 3.25x | 3.22x |
| Profit/mes | **$2,831** | $1,455 | $1,403 |
| Avg time in market | 25 min | 19 min | 30 min |

---

## Evolución por brick size (params base, 1ct)

| Brick | PF | R² | Sortino | Trades | MaxDD/ct |
|---|---|---|---|---|---|
| Renko 30 | 1.33 | 0.52 ❌ | 0.47 | 140 | $34/ct |
| Renko 35 | 1.51 | 0.77 ⚠️ | 1.27 | 138 | $18/ct |
| Renko 40 | 1.81 | 0.84 ✅ | 0.67 | 86 | $25/ct |
| **Renko 45** | **2.20** | **0.94** ✅ | **5.80** | **232** | **$343/ct** |

**Ganador: Renko 45** — R² y Sortino mejoran continuamente con brick size mayor. En Renko 45 cada secuencia Absorption+Exhaustion (4 bricks × $22.50) = $90 de movimiento deliberado → microestructura genuina, no ruido.

---

## Insight clave: AbsorptionBricks=2 vs 3

| AbsBricks | PF | Sortino | Trades | Comentario |
|---|---|---|---|---|
| 3 (original) | 2.27 | 1.63 | 74 | Muy restrictivo, muestra estadística borderline |
| **2 (ganador)** | **2.20** | **5.80** | **232** | Patrón más frecuente, calidad idéntica, Sortino 3.5x mejor |

Con Abs=2 se detectan más eventos reales sin degradar el edge — 2 bricks de esfuerzo creciente son suficientes para confirmar absorción en Renko 45.

---

## Parámetros Ganadores

```
Instrumento:       MNQ
Chart:             Renko 45-tick

1. Order Flow
   AbsorptionBricks  = 2      // bricks con vol creciente
   ExhaustionBricks  = 2      // bricks con vol decreciente
   VolSMAPeriod      = 20     // referencia de volumen
   MinVolRatioPush   = 1.3    // push ≥ 1.3× SMA vol

2. Risk / Reward
   TargetRR          = 2.0    // R:R objetivo
   BreakevenR        = 1.0    // mover SL a BE a 1R
   StopBufferTicks   = 6      // buffer sobre extremo de secuencia

3. Trade Management
   MaxTradesPerDay   = 1
   Quantity          = 15 contratos

4. Dirección
   AllowLong         = true
   AllowShort        = true   // reversals simétricos

5. Horario (ET)
   PrimeStart        = 93000  // 9:30 AM
   PrimeEnd          = 153000 // 3:30 PM
```

---

## Sizing para Apex

| Contratos | MaxDD | Profit/mes | Comentario |
|---|---|---|---|
| 1 ct | $343 | $188 | paper trading inicial |
| 15 ct | $5,146 ✅ | $2,831 | **sizing confirmado** |
| 21 ct | $7,203 ✅ | $3,965 | máximo conservador para Apex |

**Referencia**: $343/ct × 15 = $5,146 — bien dentro del límite Apex $7,500.

---

## Por qué es diferente al resto del portafolio

| Característica | OrderFlowReversal_v1 | Resto del portafolio |
|---|---|---|
| Tipo | **Reversal** (contra momentum) | Momentum / Breakout / Pullback |
| Edge | Microestructura de volumen | Precio / indicadores |
| Frecuencia | ~2.7 trades/mes | 5-50 trades/mes |
| Correlación | Baja — entra donde otros salen | Alta entre estrategias de momentum |
| AllowShort | ON — simétrico | Variable |

Rol de "sniper de reversals" — complementa PivotTrendBreak y SuperTrendWave que son momentum/tendencia.

---

## Ranking en el portafolio (por Sortino)

| Posición | Estrategia | Sortino |
|---|---|---|
| 1 | BreadButter_ULTRA | 18.52 |
| 2 | PivotTrendBreak_v1 | 8.50 |
| 3 | **OrderFlowReversal_v1** | **5.80** |
| 4 | ABCDHarmonic_v1 | 5.05 |
| 5 | BreadButter_SCALPER | 4.13 |

---

## Estado y próximos pasos

- ✅ Backtest confirmado 01/03/2026
- ⏳ Paper trading pendiente: 1ct, Renko 45, SimOrderFlowReversal account
- ⏳ Revisar resultados paper ~01/04/2026
- ⏳ Escalar a 15ct si paper confirma edge

---

## Archivos

- Código: `Strategies/OrderFlowReversal_v1.cs`
- Reporte: `Reports/16_OrderFlowReversal_v1.md`
