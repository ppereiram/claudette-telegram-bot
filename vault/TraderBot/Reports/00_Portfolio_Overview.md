# Portfolio Overview — MNQ Algo Trading
> Última actualización: 01/03/2026

## Índice de documentos
- [[03_BreadButter_ULTRA]] — JOYA DE LA CORONA: Sortino=18.52, $9,378/mes
- [[12_PivotTrendBreak_v1]] — ⭐ Sortino=8.50, $2,305/mes
- [[16_OrderFlowReversal_v1]] — Order Flow Renko 45-tick, Sortino=5.80, $2,831/mes ← NUEVO
- [[15_ABCDHarmonic_v1]] — Patrón ABCD Renko 35-tick (Sortino=5.05, $3,120/mes)
- [[07_BreadButter_SCALPER]] — MACD+EMA Renko 30-tick (Sortino=4.13, $3,679/mes)
- [[02_SuperTrendWave]] — Trend-following Renko (paper trading activo)
- [[05_OpeningRange_v1]] — Rango de apertura OR (PF=1.98)
- [[06_VWAPOrderBlock_v1]] — Sniper institucional VWAP+OB (PF=1.79)
- [[14_VWAPFlux_v1]] — VWAP Pullback + Volume Surge (PF=2.08, muestra baja)
- [[04_NYOpenBlast_v2]] — Momentum apertura NY (PF=1.73)
- [[01_BreadButter_v5_Apex]] — Estrategia base EMA (PF=1.34)
- [[17_LWDonchianBreak_v1]] — Larry Williams Donchian Channel Breakout semanal (PF=1.61)
- [[13_PivotReverse_v1]] — Doble Techo/Piso (en optimización)
- [[08_BreadButterBALANCED]] — Edge de competición long/short (experimental)
- [[09_Estrategias_Descartadas]] — Experimentos fallidos y lecciones
- [[10_Insights_MNQ]] — Patrones aprendidos sobre el instrumento
- [[11_Roadmap_2026]] — Mejoras pendientes y próximos pasos

---

## Instrumento
- **MNQ** — Micro E-mini Nasdaq 100 Futures
- TickSize = 0.25 | PointValue = $2 | TickValue = $0.50
- Plataforma: NinjaTrader 8 (NinjaScript / C#)
- Cuenta objetivo: Apex Trader Funding ($50k, MaxDD $2,500/día, $7,500 global)

---

## Rankings del portafolio (con comisiones) — actualizado 01/03/2026

| # | Estrategia | PF | R² | Sortino | MaxDD Apex | Ct | Profit/mes | Chart | Estado |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **BreadButter_ULTRA** | **2.03** | **0.96** | **18.52** | $6,903 | 9 | **$9,378** | Renko 35 | 📝 Paper |
| 2 | **PivotTrendBreak_v1** | **1.92** | **0.96** | **8.50** | $2,730 | 20 | **$2,305** | Renko 25 | ✅ Activa |
| 3 | **OrderFlowReversal_v1** | **2.20** | **0.94** | **5.80** | $5,146 | 15 | **$2,831** | Renko 45 | 📝 Paper |
| 4 | **ABCDHarmonic_v1** | 1.54 | **0.96** | 5.05 | $6,945 | 15 | **$3,120** | Renko 35 | 📝 Paper |
| 5 | **BreadButter_SCALPER** | **1.74** | **0.98** | **4.13** | $6,924 | 6 | **$3,679** | Renko 30 | 📝 Paper |
| 6 | SuperTrendWave | 1.69 | 0.96 | 2.57 | $6,722 | 5 | $2,697 | Renko 40 | 📝 Paper |
| 7 | BreadButter_v5_Apex | 1.34 | 0.95 | 1.68 | $6,510 | 3 | $873 | 2-min | ✅ Activa |
| 8 | OpeningRange_v1 | **1.98** | 0.90 | 1.33 | $6,930 | 9 | $1,251 | 1-min | ✅ Activa |
| 9 | NYOpenBlast_v2 | 1.73 | 0.93 | 1.04 | $4,484 | 7 | $570 | 1-min | ✅ Activa |
| 10 | VWAPFlux_v1 | **2.08** | 0.91 | 0.94 | $6,900 | 20 | $960 | 5-min | ✅ Activa* |
| 11 | VWAPOrderBlock_v1 | 1.79 | — | — | $6,810 | 9 | $1,255 | 5-min | ✅ Activa |
| 12 | **LWDonchianBreak_v1** | 1.61 | 0.84 | 1.09 | $6,156 | 6 | $522 | 15-min | 📝 Paper |
| 13 | PivotReverse_v1 | — | — | — | — | — | pendiente | Renko 25 | 🔬 Optimizando |

> *VWAPFlux_v1: PF=2.08 con solo 55 trades — muestra baja, tratar con cautela
> OrderFlowReversal_v1: confirmada 01/03/2026 en Renko 45, AbsBricks=2. Reversal sniper descorrelacionado del resto del portafolio.

---

## Proyección de ingresos mensuales — Apex (por estrategia individual)

| Estrategia | Contratos | Profit/mes | MaxDD Apex | Margen restante |
|---|---|---|---|---|
| **BreadButter_ULTRA** | **9** | **$9,378** | **$6,903** | **$597 ⚠️** |
| PivotTrendBreak_v1 | 20 | **$2,305** | $2,730 | $4,770 ✅ |
| **OrderFlowReversal_v1** | **15** | **$2,831** | **$5,146** | **$2,354 ✅** |
| ABCDHarmonic_v1 | 15 | **$3,120** | $6,945 | $555 ⚠️ |
| **BreadButter_SCALPER** | **6** | **$3,679** | **$6,924** | **$576 ⚠️** |
| SuperTrendWave | 5 | $2,697 | $6,722 | $778 ⚠️ |
| OpeningRange_v1 | 9 | $1,251 | $6,930 | $570 ⚠️ |
| VWAPFlux_v1 | 20 | $960 | $6,900 | $600 ⚠️ |
| NYOpenBlast_v2 | 7 | $570 | $4,484 | $3,016 ✅ |
| VWAPOrderBlock_v1 | 9 | $1,255 | $6,810 | $690 ⚠️ |
| BreadButter_v5_Apex | 3 | $873 | $6,510 | $990 ⚠️ |
| **LWDonchianBreak_v1** | **6** | **$522** | **$6,156** | **$1,344 ✅** |

> Nota: cifras de backtest. Aplicar descuento 30-50% para expectativa realista en live.

---

## Horarios de operación combinados

```
07:30 CT — OpeningRange_v1 calcula OR (07:30-07:45 CT = 08:30-08:45 ET)
08:00 CT — BreadButter_ULTRA inicia (Renko 35, desde 9:00 ET)
08:29 CT — NYOpenBlast_v2 detecta dirección (= 09:29 ET)
08:30 CT — PivotTrendBreak_v1 activo (Renko 25-tick)
08:30 CT — ABCDHarmonic_v1 activo (Renko 35-tick)
08:30 CT — BreadButter_SCALPER activo (Renko 30-tick)
08:30 CT — LWDonchianBreak_v1 activo (15-min)
08:30 CT — VWAPFlux_v1 activo (5-min)
08:30 CT — VWAPOrderBlock_v1 activo (5-min)
08:30 CT — SuperTrendWave activo (Renko 40-tick)
08:30 CT — BreadButter_v5_Apex activo (2-min)
07:45 CT — OpeningRange_v1 puede entrar trades
09:00 CT — NYOpenBlast_v2 ForceExit (= 10:00 ET)
13:30 CT — BreadButter_SCALPER cierre (14:30 ET)
13:30 CT — BreadButter_ULTRA cierre (14:30 ET)
13:30 CT — OpeningRange_v1 ForceExit (= 14:30 ET)
14:30 CT — Cierre general de todas las estrategias (= 15:30 ET)
```

> Nota: todos los params internos de las estrategias están en hora ET.

---

## Análisis de correlación (cualitativo)

| Par | Correlación | Motivo |
|---|---|---|
| PivotTrendBreak / SuperTrendWave | Baja | Mismo chart Renko pero lógica opuesta (breakout vs trailing) |
| PivotTrendBreak / ABCDHarmonic | Media-Baja | Renko similar (25 vs 35) pero reversal vs breakout |
| ABCDHarmonic / SuperTrendWave | Baja | Renko 35 vs Renko 40, harmónico vs trailing |
| VWAPFlux / VWAPOrderBlock | Media | Ambos usan VWAP pero señal diferente |
| NYOpenBlast / OpeningRange | Baja | Misma ventana horaria, lógica opuesta |
| **BreadButter_ULTRA / SCALPER** | **Media** | Ambos EMA-based con filtro accidental, horario solapado |
| **BreadButter_ULTRA / ABCDHarmonic** | **Baja** | Renko 35 compartido pero lógica radicalmente distinta |
| PivotTrendBreak / todo | **Muy baja** | Renko elimina correlación temporal |
| VWAPFlux / todo | **Muy baja** | 1 trade/14 días — prácticamente independiente |
| ABCDHarmonic / todo | **Baja** | Patrón harmónico Fibonacci, independiente de VWAP/OR/momentum |
| **LWDonchianBreak / todo** | **Baja** | Único Donchian Channel del portafolio — breakout semanal puro |
| **OrderFlowReversal / todo** | **Muy baja** | Reversal puro — entra donde los momentum salen. Descorrelacionado por naturaleza |

---

## Estado del portafolio: 01/03/2026

- **Paper trading activo**: SuperTrendWave (desde 19/02/2026, 1ct), BreadButter_v5_Apex (activa)
- **Confirmadas en backtest (pendiente paper trading)**:
  - **BreadButter_ULTRA** (Renko 35) ⭐ — $9,378/mes, Sortino=18.52
  - **OrderFlowReversal_v1** (Renko 45) ← NUEVO — $2,831/mes, Sortino=5.80
  - **BreadButter_SCALPER** (Renko 30) — $3,679/mes, Sortino=4.13
  - **ABCDHarmonic_v1** (Renko 35) — $3,120/mes, Sortino=5.05
  - LWDonchianBreak_v1 (15-min) — $522/mes
- **En optimización**: PivotReverse_v1 (pendiente backtest)
- **Pendiente paper** (todas con 1ct):
  - OrderFlowReversal_v1 → 1ct (Renko 45)
  - BreadButter_ULTRA → 1ct (Renko 35)
  - BreadButter_SCALPER → 1ct (Renko 30)
  - ABCDHarmonic_v1 → 1ct (Renko 35)
  - LWDonchianBreak_v1 → 1ct (15-min)
- **Agenda**: Revisar SuperTrendWave en ~20/03/2026 con datos paper. Siguiente estrategia: KeltnerFlow_v1

---

## Principios del portafolio

1. **Automatización total** — sin intervención manual durante trading hours
2. **Cada estrategia tiene un edge conceptual claro** — no spaghetti de indicadores
3. **Backtest con comisiones siempre** — PF sin comisiones es inútil
4. **MaxDD respeta límites Apex** — $7,500 global por estrategia
5. **Descorrelación** — mejor portafolio = estrategias con edge independiente
6. **R² > 0.85 como requisito mínimo** — curva de equity debe ser lineal y creciente
7. **Muestra mínima ~55 trades** — bajo ese umbral, cualquier PF tiene demasiada incertidumbre
8. **Slippage=1 en todos los backtests** — Slippage=0 invalida los resultados
