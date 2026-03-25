# MomentumZ_v1 — Reporte de Estrategia

**Confirmada**: 03/03/2026
**Instrumento**: MNQ (Micro E-mini Nasdaq 100)
**Chart**: Renko 45-tick
**Archivo**: `Strategies/MomentumZ_v1.cs`

---

## Concepto Quant

**MomScore = (Close[ahora] - Close[N barras atrás]) / ATR[0]**

- Mide cuántos ATRs se movió el precio en las últimas N barras
- Equivalente intradiario del **Sharpe ratio de momentum** (AQR/Moskowitz, "Time-Series Momentum")
- Completamente normalizado por volatilidad actual → adapta al régimen automáticamente
- **Sin indicadores técnicos**: solo retornos y volatilidad

### Edge diferencial vs EMA crossover
| | EMA Crossover | MomentumZ |
|---|---|---|
| Mide | Precio absoluto | Retornos (cambio relativo) |
| Normalización | Ninguna | ATR (volatilidad actual) |
| Lag | Alto (EMA es suavizado) | Ninguno — ventana fija N |
| Mercado flat | Entra con ruido | No entra (MomScore ≈ 0) |
| Edge | Técnico | Estadístico/Quant |

---

## Parámetros Ganadores

| Parámetro | Valor |
|-----------|-------|
| LookbackBars | 10 |
| MomThreshold | 3.0 ATRs |
| TargetRR | 3.0 |
| StopATRMult | 1.0 |
| ATRPeriod | **7** |
| VolumePeriod | 20 |
| MinVolRatio | **1.3** |
| MaxTradesPerDay | 1 |
| Quantity | 16 (Apex) |
| AllowLong | ON |
| AllowShort | ON |
| PrimeStart | 93000 (9:30 ET) |
| PrimeEnd | 153000 (15:30 ET) |

---

## Resultados Confirmados (Renko 45, 3 años, Slippage=1)

| Métrica | Valor |
|---------|-------|
| **Profit Factor** | **1.74** |
| **R²** | **0.95** |
| **Sortino Ratio** | **3.89** |
| **Max DD** | ~$449/ct |
| Trades | ~200+/3años |
| Win Rate | ~45% |
| Win/Loss ratio | ~3.0x |

### Por dirección
| Dirección | PF |
|-----------|-----|
| Long | **1.86** |
| Short | **1.59** |
| **Combined** | **1.74** |

**Ambas direcciones positivas** — señal verdaderamente simétrica (a diferencia de estrategias trend-following donde Shorts sufren en MNQ alcista).

---

## Sizing para Apex $7,500

- MaxDD por contrato: ~$449
- Contratos: **16ct** → MaxDD = $7,194 ✅ (dentro de Apex $7,500)
- **Profit/mes estimado: ~$3,390** con 16 contratos

---

## Evolución de Optimización

| Config | RR | StopATR | ATRPeriod | MinVol | PF | Sortino |
|--------|-----|---------|-----------|--------|-----|---------|
| v1 (base) | 2 | 1.5 | 14 | 1.2 | 1.27 | 0.65 |
| v2 | 3 | 1.2 | 14 | 1.2 | 1.42 | 1.52 |
| v3 | 3 | 1.1 | 7 | 1.2 | 1.51 | 1.95 |
| **v4 (ganadora)** | **3** | **1.0** | **7** | **1.3** | **1.74** | **3.89** |

### Insight de optimización
1. **RR 2→3**: Mayor PF (filtro de calidad en targets)
2. **ATRPeriod 14→7**: Mayor Sortino — el ATR corto normaliza mejor en Renko (cada brick es un movimiento completo)
3. **StopATR 1.5→1.0**: Mejor R² — stop más apretado fuerza señales más limpias
4. **MinVol 1.2→1.3**: Pulido final — filtra trades en volumen bajo

---

## Brick Size Comparison

Todos los tamaños de Renko probados (25, 30, 35, 40, 45, 50, 55...). **Renko 45 ganador**.

El Renko 45 es consistente con OrderFlowReversal_v1 (también Renko 45) — sugiere que para MNQ el brick de 45 ticks captura movimientos de calidad sin exceso de ruido.

---

## Posición en el Portafolio

| Aspecto | Valor |
|---------|-------|
| Sortino ranking | #5 (detrás de SCALPER 4.13 y DarvasBox 3.92) |
| R² ranking | #3 (0.95, detrás de SCALPER 0.98) |
| Profit/mes | $3,390 — #4 del portafolio |
| Correlación | Baja con mean-reversion (KalmanZScore opuesto conceptualmente) |
| Correlación | Moderada con PivotTrendBreak (ambos momentum) |

### Rol en el portafolio
- **Momentum puro** sin indicadores técnicos
- Complementa estrategias de mean-reversion y pattern-based
- Bidireccional — opera tanto alcista como bajista por igual
- 1 trade/día → baja rotación, fácil de monitorear

---

## Próximos Pasos

1. **Paper trading**: 1 contrato, Renko 45-tick, params confirmados
2. **Monitorear**: ~20/03/2026 revisar métricas paper vs backtest
3. **Roadmap**: Explorar combinación MomScore + Kalman Z-score como confirmaciónde señal

---

## Notas Técnicas

- `Calculate.OnBarClose` — señal al cierre del brick
- ATR period=7 con Renko: el ATR corto es más representativo porque Renko ya filtra ruido
- `MomScore > MomThreshold` puro — no hay indicadores adicionales en la señal
- Filtro volumen `Volume[0] >= MinVolRatio × SMA(Volume, 20)` es el único filtro de confirmación
- `BarsRequiredToTrade = 50` + `CurrentBar < LookbackBars` como guards iniciales
