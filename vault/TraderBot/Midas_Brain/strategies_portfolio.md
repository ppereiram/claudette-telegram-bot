---
name: strategies_portfolio
description: Params detallados de cada estrategia del portafolio MNQ — confirmados, descartados, en optimización
type: project
---

# Portafolio de Estrategias — Params Completos

## Rankings (actualizado 06/03/2026)
| Strategy | PF | R² | Sortino | MaxDD (Apex) | Contratos | Profit/mes |
|----------|----|----|---------|--------------|-----------|------------|
| StatMeanCross_v1 (Renko 35) | 2.56 | 0.98 | ⭐38.73 | $2,668 | 20ct | $4,092 |
| EMATrendRenko_v1 (Renko 35) | 2.29 | 0.90 | 6.75 | $7,460 | 20ct | $4,825 |
| OrderFlowReversal_v1 (Renko 45) | 2.20 | 0.94 | 5.80 | $5,146 | 15ct | $2,831 |
| BreadButter_ULTRA (Renko 35) | 2.03 | 0.96 | 18.52 | $6,903 | 9ct | $9,378 |
| OpeningRange_v1 (1-min) | 1.98 | 0.90 | 1.33 | $6,930 | 9ct | $1,251 |
| PivotTrendBreak_v1 (Renko 25) | 1.92 | 0.96 | 8.50 | $2,730 | 20ct | $2,305 |
| BreadButter_SCALPER (Renko 30) | 1.74 | 0.98 | 4.13 | $6,924 | 6ct | $3,679 |
| MomentumZ_v1 (Renko 45) | 1.74 | 0.95 | 3.89 | $7,194 | 16ct | $3,390 |
| NYOpenBlast_v2 (1-min) | 1.73 | 0.93 | 1.04 | $4,484 | 7ct | $570 |
| SuperTrendWave (Renko 40) | 1.69 | 0.96 | 2.57 | $6,722 | 5ct | $2,697 |
| ABCDHarmonic_v1 (Renko 35) | 1.54 | 0.96 | 5.05 | $6,945 | 15ct | $3,120 |
| LWDonchianBreak_v1 (15-min) | 1.61 | 0.84 | 1.09 | $6,156 | 6ct | $522 |
| DarvasBox_v1 (Renko 30) | 1.35 | 0.92 | 3.92 | $7,476 | 9ct | $2,426 |
| BreadButter_v5_Apex (2-min) | 1.34 | 0.95 | 1.68 | $6,510 | 3ct | $873 |
| VWAPOrderBlock_v1 (5-min) | 1.79 | — | — | $6,810 | 9ct | $1,255 |
| VWAPFlux_v1 (5-min) | 2.08 | 0.91 | 0.94 | $6,900 | 20ct | $960 |
| PivotReverse_v1 | ⚠️1.36* | 0.86* | 0.62* | $11,980* | pendiente | pendiente |

---

## StatMeanCross_v1 — MEJOR ESTRATEGIA ⭐⭐ (Renko 35, 06/03/2026)
- **Concepto**: TP/SL estadístico basado en MFE histórico rolling — sabe cuánto se aleja el precio de la EMA
- **Params**: EMA=21, ATR=21, MfeWindow=30, MinSampleSize=10, TpPercentile=0.70, SlFraction=0.40, WarmupFallbackATR=2, MinVolRatio=1.0, MaxTrades=1/día, 9:30-15:30 ET, AllowShort=ON
- **Edge**: Brick=35 fijo → distribución MFE estable → TP estadístico es señal real, no ruido
- **MaxDD/ct=$133** = MÍNIMO del portafolio | **Sortino=38.73** = MÁXIMO del portafolio
- **Sizing**: 20ct → MaxDD=$2,668. Teórico: 56ct — limitado por liquidez MNQ
- **Archivo**: `Strategies/StatMeanCross_v1.cs`

## EMATrendRenko_v1 — CONFIRMADA con RegimeFilter (Renko 35, 05/03/2026) ⭐
- **Params FINAL**: EMA=21, ATR=10, StopATRMult=1.7, ExitATRMult=0.1, MinVolRatio=1.11, MaxTrades=1/día, 9:30-15:30 ET, AllowShort=ON, UseRegimeFilter=ON, RegimeAdxPeriod=14, RegimeThreshold=25
- **RegimeFilter**: ADX+DM sobre 30-min — bloquea longs en Bear, shorts en Bull, ambos en Neutral
- **Impacto filtro**: -14 trades (-3%) pero Sortino 3.44→6.75, MaxDD bajó 17%
- **Sin filtro**: PF=2.16, R²=0.88, Sortino=3.44, MaxDD=$449/ct, 452 trades
- **CORRELACIÓN**: comparte EMA(21) con StatMeanCross → tratar como 1 slot cuando coincidan
- **Archivo**: `Strategies/EMATrendRenko_v1.cs`

## BreadButter_ULTRA — CONFIRMADA (Renko 35, 26/02/2026) ⭐
- **Params**: EMA 3/21, ATR=10, Stop=1xATR, RR=2, Trailing=OFF, 9:00-15:30 ET, AllowShort=ON, todos los setups ON
- **Filtro Accidental ACTIVO**: dailyPnL bug → solo ~1 trade/día. NUNCA corregir.
- **EMA Touch**: el setup dominante — los otros 3 setups no añaden ni degradan PF
- **Brick**: Renko30(Sortino=5.82) < Renko35(Sortino=18.52)✅ < Renko40(MaxDD=$1,446❌)
- **Archivo**: `Strategies/BreadButter_ULTRA.cs` | Reporte: `Reports/03_BreadButter_ULTRA.md`

## BreadButter_SCALPER — CONFIRMADA (Renko 30, 26/02/2026)
- **Params**: MACD 12/26/9, EMA 9/21, ATR=14, Stop=1xATR, RR=1.3, 9:30-14:30 ET, AllowShort=ON
- **Filtro Accidental ACTIVO**: mismo bug que ULTRA → ~1 trade/día. NUNCA corregir.
- **Brick ganador**: Renko30 — único con Longs PF ≈ Shorts PF (1.73 vs 1.75) → robusto
- **Archivo**: `Strategies/BreadButter_SCALPER.cs` | Reporte: `Reports/07_BreadButter_SCALPER.md`

## PivotTrendBreak_v1 — MEJOR ESTRATEGIA APEX por DD (Renko 25)
- **Params**: PivotStrength=3, MinPivotGapTicks=20, MaxPivotAgeBricks=80, StopBufferTicks=4, MinRR=1.5, UseVolumeFilter=ON, VolumePeriod=20, MinVolRatio=1.11, MaxTradesPerDay=1, 9:30-15:30 ET
- **Edge**: SL/TP estructurales (pivots reales) + R:R gate + 1 trade/día = selección implícita
- **MaxDD=$182/ct** → más margen dentro de Apex $7,500 que cualquier otra estrategia
- **Archivo**: `Strategies/PivotTrendBreak_v1.cs`

## OrderFlowReversal_v1 — CONFIRMADA (Renko 45, 01/03/2026) ⭐
- **Concepto**: Absorption → Exhaustion → Push (brick contrario + vol alto) = REVERSAL sin Tick Replay
- **Params**: AbsorptionBricks=2, ExhaustionBricks=2, VolSMAPeriod=20, MinVolRatioPush=1.3, RR=2, BE=1R, StopBuffer=6tk, MaxTrades=1/día, 9:30-15:30 ET
- **Key insight**: AbsorptionBricks=2 vs 3 → Sortino 1.63→5.80, trades 74→232
- **Archivo**: `Strategies/OrderFlowReversal_v1.cs` | Reporte: `Reports/16_OrderFlowReversal_v1.md`

## ABCDHarmonic_v1 (Renko 35, 26/02/2026)
- **Concepto**: Patrón ABCD armónico en Renko — entrada en PRZ (punto D) con ratios Fibonacci
- **Params**: Quantity=15, TargetRR=4.0, BreakevenR=1.0, MaxTradesPerDay=1, FibMinBC=0.382, FibMaxBC=0.886, FibMinCD=1.130, FibMaxCD=1.618, StopBufferTicks=4, MaxStopATR=3.0, ATRPeriod=14, 9:30-15:30 ET
- **WR=27.81%**, hasta 13 pérdidas consecutivas — psicológicamente exigente
- **Archivo**: `Strategies/ABCDHarmonic_v1.cs` | Reporte: `Reports/15_ABCDHarmonic_v1.md`

## NYOpenBlast_v2 — Params confirmados (1-min, 24/02/2026)
- **Params**: DirectionTime=92900, EntryDeadline=94500, ForceExit=100000, TrendLookback=28, InvertDirection=ON, AllowShort=OFF, MACD Fast=10 Slow=22 Signal=9, Target=450tk, Stop=100tk, BE=OFF
- **AllowShort=OFF FINAL**: shorts R²=0.43, recovery=626 días
- **Salida principal**: ForceExit 10:00 AM, no el profit target
- **Archivo**: `Strategies/NYOpenBlast_v2.cs`

## OpeningRange_v1 (1-min, 24/02/2026)
- **Params**: SessionOpen=83000, ORMinutos=15, Stop=150tk, TargetORMultiple=3x, MinTarget=100tk, BE=100tk, GapMin=1, ForceExit=143000, AllowShort=OFF
- **IMPORTANTE**: OR ocurre 7:30 AM CR = 8:30 ET (PRE-apertura NYSE). NO a las 9:30 ET.
- **Filtro tendencia**: EMA(9) en barras de 15-min (AddDataSeries secundaria)
- **Archivo**: `Strategies/OpeningRange_v1.cs`

## SuperTrendWave v1.1 (Renko 40, papel desde 19/02/2026)
- **Concepto**: SuperTrend como trailing stop puro + piramidación en impulsos
- **Params ganadores**: Renko 40-tick, AllowShort=ON, UsePrimeHoursOnly=ON, ATR=14, Mult=3.0, 5ct
- **PENDIENTE**: Actualizar a Renko 40 + AllowShort=ON tras 1 mes de datos paper
- **Archivo**: `Strategies/SuperTrendWave.cs`

## BreadButter_v5_Apex (2-min, 24/02/2026)
- **Params**: Stop=3ATR, R:R=4, BE=1R, Trailing=OFF, MaxTrades=1/día, EMA 9/15/100, ATR=7, RSI=7, ADX=21/25, RSI Long<65/Short>35, VolMin=0.7x
- **MaxDD/ct=$2,170** → máximo 3ct en Apex $7,500 → Profit/mes=$873
- **Step Lock activo**: desde 09/03/2026 (anti-popcorn)
- **Archivo**: `Strategies/BreadButter_v5_Apex.cs`

## MomentumZ_v1 (Renko 45, 03/03/2026) ⭐ QUANT
- **Concepto**: MomScore = (Close[0]-Close[N])/ATR[0] (AQR/Moskowitz style)
- **Params**: LookbackBars=10, MomThreshold=3.0, TargetRR=3, StopATRMult=1.0, ATR=7, MinVolRatio=1.3, MaxTrades=1/día, 9:30-15:30 ET
- **Archivo**: `Strategies/MomentumZ_v1.cs`

## DarvasBox_v1 (Renko 30, 02/03/2026)
- **Params**: BoxMinBars=2, BoxMaxBars=10, MinBoxTicks=5, MaxBoxTicks=80, RR=3, BE=1R, StopBuffer=3, MaxTrades=3/día, VolPeriod=14, MinVolRatio=1.0, 9:30-15:30 ET
- **Shorts dominan**: Short PF=1.38, R²=0.94 vs Long PF=1.33, R²=0.68
- **Archivo**: `Strategies/DarvasBox_v1.cs`

## PivotReverse_v1 — EN OPTIMIZACIÓN (Renko 25)
- **Primer backtest (MinRR=1)**: MaxDD=$11,980 ❌ excede Apex
- **Pendiente**: MinRR=1.5, AllowLong=OFF (shorts only), probar Renko 35-40
- **ALERTA**: Resultados cambian entre MNQ 03-26 y MNQ 06-26 por datos Renko distintos
- **Archivo**: `Strategies/PivotReverse_v1.cs`

---

## El Filtro Accidental — Edge Core de ULTRA y SCALPER
```
dailyPnL += execution.Commission + execution.Order.AverageFillPrice * execution.Quantity
```
- Suma valor nominal (no P&L real) → dispara MaxLoss al primer entry
- Resultado: ~1 trade/día aunque MaxTradesPerDay=25
- **NUNCA corregir** — el PF colapsa a ~1.01 si se arregla (verificado experimentalmente)

## IMPORTANTE: BreadButterBALANCED edge
- Combined PF=1.31 pero separados Long=1.06 / Short=0.97
- El edge viene de la COMPETICIÓN entre señales por el slot del día (selección implícita)

---

## Estrategias Descartadas
- **VolumeProfile_POC_v1**: POC sintético requiere tick data real. PF=1.21, R²=0.65, Sortino=0.46 ❌
- **KeltnerFlow_v1**: PF=1.63, R²=0.87, Sortino=0.35 ❌ (mínimo 2.0), solo 60 trades/3años
- **KalmanZScore_v1**: Mean-reversion no funciona en MNQ 2023-2026 alcista. Usar como filtro de régimen
- **DailyPullback_v1**: Swing trade overnight — incompatible con Apex intraday. Preservar para cuenta no-Apex
- **BBShorts_v1/v2**: PF techo 1.12, curva 2 años en rojo
- **VWAPPulse_v1**: VWAP cross directo demasiado ruidoso. PF=1.33, WR=12.9%, 24 pérdidas consec.
- **EMAIntention_v1**: Concepto discrecional, PF techo 1.06
- **TheStrat_v1**: Nunca rentable, backtest lento — no explorar de nuevo
- **MNQMomentumScalper**: PF=1.03, shelved

---

## Insights Críticos de NinjaTrader
- MNQ retraces ~1.0x ATR → stop < 1.0x = death by stop-outs
- Slippage=1 cuesta ~$15/round trip con 15ct
- NT8 cachea params al recompilar → remove/re-add strategy para refrescar
- Draw.Text: usar overload simple `Draw.Text(this, tag, text, barsAgo, y, brush)` — NO FontFamily overload
- Using directives correctos (de ABCDHarmonic_v1): `NinjaTrader.Cbi` (NO "Ciba"!), agregar `NinjaTrader.NinjaScript.Indicators` y `NinjaTrader.NinjaScript.Strategies`
- `StopTargetHandling.PerEntryExecution` para named signals
- Cache indicators en `State.DataLoaded` (nunca en OnBarUpdate)
- Secondary data series: `AddDataSeries(BarsPeriodType.Minute, 15)` en Configure → `BarsArray[1]`
- **Timezone fix** (23/02/2026): `GetEtTime()` / `GetEtTimeSpan()` — todos los params en ET

## Fix Definitivo de Timezone (aplicado a TODAS — 23/02/2026)
- Backtest NT8: `Time[0]` ya es ET (CME exchange time)
- Live CR: usar `TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone)`
- NYOpenBlast usa `>=` para DirectionTime (más robusto en live)
- OpeningRange: SessionOpen=83000 = 8:30 ET = CME pre-open
