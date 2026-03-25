# KeltnerFlow_v1 — Reporte de Desarrollo

> Estado: ❌ DESCARTADA — Sortino insuficiente (0.35 vs mínimo 2.0)
> Chart: 10-min | MNQ | Short-only (mejor configuración encontrada)

---

## Concepto

Keltner Channel como estructura de volatilidad adaptativa — el precio revierte desde la banda cuando hay una confluencia de:
1. **Tendencia**: EMA central con pendiente definida (no mercado lateral)
2. **Toque de banda**: precio toca la banda y recupera (pin-bar estructural)
3. **Volume Delta**: presión direccional confirma el rechazo (compradores/vendedores reales)

```
Tendencia (EMA slope) → Pullback a banda → Pin-bar + Delta fuerte → ENTRY
```

**Diferencia con VWAPFlux_v1**:
| Característica | VWAPFlux_v1 | KeltnerFlow_v1 |
|---|---|---|
| Ancla | VWAP (precio-volumen) | Keltner (volatilidad, EMA + ATR) |
| Dirección | Long only | Long + Short según tendencia |
| Filtro estructura | No | Filtro de ruido ATR activo |
| Frecuencia esperada | 1 trade/14 días | Mayor — bandas se adaptan a volatilidad |

---

## Lógica de Entrada

### LONG
1. `EMA[0] > EMA[TrendConfirmBars]` — EMA con pendiente alcista
2. `Low[0] <= LowerBand` — barra toca o penetra la banda inferior
3. `Close[0] > LowerBand` — recupera por encima (pin-bar sobre banda)
4. `Close[0] > Open[0]` — barra cierra alcista
5. `barDelta >= max(|deltaSma| × ratio, minDeltaAbs)` — presión compradora real
6. `stopDist = Close[0] - swingLow <= ATR × MaxStopATR` — SL estructural razonable

### SHORT (espejo)
1. `EMA[0] < EMA[TrendConfirmBars]` — EMA con pendiente bajista
2. `High[0] >= UpperBand` — barra toca la banda superior
3. `Close[0] < UpperBand` — recupera por debajo
4. `Close[0] < Open[0]` — barra cierra bajista
5. Delta negativo confirma

---

## Filtro de Ruido (Skip Noise)

```
Si ATR(14)[0] < SMA(ATR(14), 50)[0] × MinATRRatio → mercado sin estructura → NO operar
```

- `ATR actual` = volatilidad reciente (últimos 14 × 5-min = 70 minutos)
- `ATR SMA50` = baseline de volatilidad (últimas 250 minutos ≈ 4 horas)
- Si el mercado está más quieto que el 70% de la baseline → chop → skip

---

## Delta Sintético

Sin Bid/Ask real (como VWAPFlux):
```
Barra alcista (Close ≥ Open) → barDelta = +Volume
Barra bajista (Close < Open) → barDelta = -Volume
```

Rolling SMA circular (DeltaSMAPeriod barras):
- `deltaSma > 0` → flujo reciente comprador
- `deltaSma < 0` → flujo reciente vendedor

Condición: `|barDelta| ≥ max(|deltaSma| × MinDeltaRatio, MinDeltaAbs)`
Interpretación: la barra de entrada tiene presión notable vs el promedio reciente.

---

## Parámetros Iniciales para Backtest

```
Chart: 5-min MNQ

1. Keltner Channel
   KeltnerPeriod     = 20      // EMA central
   KeltnerMultiplier = 2.0     // bandas = EMA ± 2×ATR
   ATRPeriod         = 14      // ATR para las bandas
   TrendConfirmBars  = 3       // 3 barras = 15 min de pendiente

2. Noise Filter
   UseNoiseFilter = true
   MinATRRatio    = 0.7        // ATR actual ≥ 70% del baseline

3. Volume Delta
   DeltaSMAPeriod = 20         // SMA de 20 barras = 100 minutos
   MinDeltaRatio  = 1.3        // delta barra ≥ 1.3× SMA
   MinDeltaAbs    = 0          // sin mínimo absoluto (probar 500-1000 si muestra baja)

4. Risk / Reward
   TargetRR        = 3.0       // probar 2.0, 3.5, 4.0
   BreakevenR      = 1.0
   StopBufferTicks = 5
   MaxStopATR      = 3.0
   SwingLookback   = 10        // últimas 10 barras = 50 minutos

5. Trade Management
   MaxTradesPerDay = 1
   Quantity        = 1 contrato (ajustar tras ver MaxDD/ct)
   AllowLong       = true
   AllowShort      = true      // testear también Long-only

6. Horario (ET)
   PrimeStart = 93000          // 9:30 AM
   PrimeEnd   = 153000         // 3:30 PM
```

---

## Variables a Optimizar en Backtest

| Parámetro | Rango a probar | Motivo |
|---|---|---|
| KeltnerMultiplier | 1.5, 2.0, 2.5 | Ancho de bandas — 2.0 es estándar |
| TargetRR | 2.0, 2.5, 3.0, 3.5, 4.0 | Sweet spot R:R igual que en VWAPFlux |
| TrendConfirmBars | 2, 3, 5, 8 | Sensibilidad a la pendiente |
| MinDeltaRatio | 1.0, 1.3, 1.5, 2.0 | Filtro de calidad de entrada |
| MinATRRatio | 0.5, 0.7, 1.0 | Agresividad del filtro de ruido |
| SwingLookback | 5, 10, 15 | Rango para SL estructural |

---

## Criterios de Validación

Para confirmar la estrategia:
- PF > 1.50 con comisiones y Slippage=1
- R² > 0.85 (curva de equity lineal)
- Sortino > 2.0
- Trades ≥ 150 en 3 años (≥ 50/año)
- MaxDD/ct < $375 (para caber en Apex con 20ct)

---

## Sizing para Apex (estimación)

| Referencia | Contratos | MaxDD estimado | Profit/mes est. |
|---|---|---|---|
| Si MaxDD/ct ≤ $375 | 20 ct | ≤ $7,500 ✅ | por definir |
| Si MaxDD/ct ≤ $500 | 15 ct | ≤ $7,500 ✅ | por definir |

> Cifras especulativas hasta tener el backtest.

---

## Resultados Finales del Backtest (02/03/2026)

### Resumen de tests realizados

| Configuración | Trades | PF | R² | Sortino | Veredicto |
|---|---|---|---|---|---|
| Combined, 5-min, params base | 150-158 | 1.40 | 0.81 | 0.35 | ❌ |
| Long-only, 5-min | ~90 | 1.19 | 0.40 | — | ❌ |
| Short-only, 10-min, ATRMult=1.2 | **60** | **1.63** | **0.87** | **0.35** | ❌ Sortino |
| TrendBars=5 (test extra) | 523 | 0.96 | — | — | ❌ pierde |

### Mejor resultado: Short-only (10-min, 02/01/2023–22/02/2026)

```
Trades:        60 en 3 años (20/año)      ❌ mínimo: 150
PF:            1.63                        ✅
R²:            0.87                        ✅
Sortino:       0.35                        ❌ mínimo: 2.0
MaxDD:         -$8,370 (15ct) = $558/ct
WR:            53.33%
Win/Loss:      1.43x
Profit/mes:    $538 (15ct)
Avg time:      106 min en mercado

Params: ATRMult=1.2, ATR=7, TrendBars=2, ZoneTol=0.5,
        MaxStopATR=3, SwingLookback=3, RR=2, BE=1R,
        MaxTrades=3, AllowShort=ON, AllowLong=OFF
```

### Diagnóstico del Sortino=0.35

El Sortino bajo con WR=53% indica que el BE=1R aplana el P&L — muchos trades salen a 0 sin contribuir al numerador. El win/loss ratio teórico con RR=2 debería dar PF=2.26 (0.53×2 / 0.47×1), pero el real es 1.63 → el BE absorbe la diferencia. La estrategia no genera los R grandes suficientes.

Comparación con la estrategia más débil del portafolio (VWAPFlux):
- VWAPFlux: PF=2.08, Sortino=0.94, 55 trades → en portafolio (aceptada por Sortino)
- KeltnerFlow: PF=1.63, Sortino=0.35, 60 trades → **inferior en todas las métricas**

### Conclusión

El edge SHORT existe (R²=0.87 confirma estructura no aleatoria) pero el riesgo ajustado es pobre. La combinación de pocos trades + Sortino muy bajo hace que no aporte al portafolio. El código queda archivado para referencia.

---

## Estado Final

- ✅ Código creado (02/03/2026): `Strategies/KeltnerFlow_v1.cs`
- ✅ Backtest completado 02/03/2026 — múltiples configuraciones
- ❌ **DESCARTADA**: Sortino=0.35 (mínimo 2.0), muestra insuficiente (60 trades)
- 📁 Código archivado — no proceder a paper trading

---

## Archivos

- Código: `Strategies/KeltnerFlow_v1.cs`
- Reporte: `Reports/18_KeltnerFlow_v1.md`
