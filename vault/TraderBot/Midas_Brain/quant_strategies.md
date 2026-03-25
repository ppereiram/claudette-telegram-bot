# Quant Strategies & Kelly Criterion

## Kelly Criterion — Portafolio Completo
Formula: f* = WR - (1-WR)/b  donde b = avg_win/avg_loss
Si no hay b directo: b = PF × (1-WR) / WR

| Estrategia | WR | b (win/loss) | Kelly f* | Half-Kelly | Sizing actual |
|-----------|----|-----------|---------|-----------:|--------------|
| BreadButter_ULTRA | 45.28% | 2.45x* | **22.9%** | 11.5% | 9ct |
| PivotTrendBreak | 46.67% | 2.19x | **22.3%** | 11.2% | 20ct |
| OrderFlowReversal | 40.52% | 3.23x* | **22.1%** | 11.1% | 15ct |
| BreadButter_SCALPER | 44.95% | 2.13x* | **19.1%** | 9.6% | 6ct |
| VWAPOrderBlock | 38.54% | 2.86x | **17.1%** | 8.6% | 9ct |
| ABCDHarmonic | 27.81% | 4.00x | **9.8%** | 4.9% | 15ct |
| BreadButter_v5 | 33.57% | 2.65x | **8.5%** | 4.3% | 3ct |
| DarvasBox | 22.07% | 4.77x | **5.7%** | 2.9% | 9ct |

*b derivado de PF: b = PF × (1-WR) / WR

## Insight clave: ¿Qué nos dice Kelly?
1. ULTRA, PivotTrend, OrderFlow → f*>22%: edge muy fuerte, sizing agresivo justificado
2. ABCD, BB_v5, Darvas → f*<10%: edge existe pero menor; sizing conservador correcto
3. Current Apex sizing es más conservador que Kelly puro → correcto dada la restricción de DD
4. Implicación portfolio: priorizar capital en ULTRA+PivotTrend+OrderFlow (mayor Kelly)

## Contracts = Kelly × Capital / avg_loss_per_contract
Para Apex: Capital = $7,500 (max DD allowance), no el account total
Ejemplo PivotTrendBreak: avg_loss ≈ $44/ct, f*=22.3%
→ Kelly contracts = (22.3% × $7,500) / $44 ≈ 38ct (teórico)
→ Pero limitado por MaxDD histórico: $182/ct × 38ct = $6,916 ✅ (coincide!)
→ La restricción Apex hace que el sizing sea aprox. la mitad del Kelly teórico → Half-Kelly natural

## Roadmap Quant
1. ✅ KalmanZScore_v1 — Mean reversion (Kalman + Z-score) → DESCARTADA como standalone; pendiente como filtro
2. ✅ MomentumZ_v1 — Time-series momentum normalizado por volatilidad → **CONFIRMADA** Renko 45
3. ✅ ML Meta-Labeling BBv5 — Python ZMQ bridge conectado a BBv5 (04/03/2026) → ver abajo
4. ⬜ Expandir ML a otras estrategias (ULTRA, OrderFlow) con sus propios meta_brain
5. ⬜ KalmanTrendNQ — Kalman 2D velocity como señal de tendencia → backtest pendiente (ver Estrategias Grok/KalmanTrendNQ.cs)
6. ⬜ NQ-ES Statistical Arb — beta rolling OLS + OU spread → pendiente adaptar a MNQ/MES (ver Estrategias Grok/NQ_ES_Spread.cs)
7. ⬜ HMM Regime Filter — Hidden Markov Model 3 estados (trend/range/highvol) → Python side
8. ⬜ Portfolio Kelly Allocation — auto-sizing dinámico por estrategia

## ML Meta-Labeling — Arquitectura (04/03/2026)
**Concepto**: No predecir precio. Predecir si la señal de una estrategia específica GANARÁ o PERDERÁ dado el contexto del mercado en ese momento.

### Pipeline
```
NT8 (BBv5) detecta señal → ZMQ → Python (meta_brain_bbv5.py) → allow/block → NT8 ejecuta
                                          ↓
                             Log: [contexto_entrada + resultado]
                                          ↓
                         Cada 20 trades → reentrenar modelo
```

### Archivos clave
- `Bot_Quant_IA/meta_brain_bbv5.py` — Python ZMQ server, puerto 5556
- `Strategies/BreadButter_v5_Apex.cs` — parámetro `UseMLFilter` (default OFF para backtests)
- `Bot_Quant_IA/trade_log_bbv5.csv` — log acumulativo de trades con contexto
- `Bot_Quant_IA/modelo_meta_bbv5.pkl` — modelo entrenado en trade outcomes (se crea automáticamente)

### Features del meta-model (context at entry)
- `direction` (1=Long, -1=Short), `signal_type` (0=Cross, 1=Pullback)
- `rsi`, `adx`, `vol_ratio` — indicadores de BBv5 en momento de entrada
- `dist_htf` — (Close - EMA100) / Close (% distancia de tendencia)
- `ema_slope` — pendiente EMA9 normalizada por ATR
- `hour`, `minute`, `day_of_week` — contexto temporal

### Fases del modelo
- **Fase 1** (0-30 trades): Filtro heurístico (ADX sanity + RSI extremos). Log acumulando.
- **Fase 2** (30+ trades): Random Forest entrenado en trade outcomes reales de BBv5. Se reentrena cada 20 trades nuevos.
- **Fail-safe**: Si Python no responde en 500ms → permite el trade (NT8 no se bloquea)

### Dato clave de entrenamiento
- NO usar paper trading de 3 días. Exportar 3 años de backtest de BBv5 desde NT8:
  Strategy Analyzer → Performance → Export CSV → `trade_history_bbv5.csv`
- Pero ese CSV solo tiene precio/tiempo/resultado, no contexto de indicadores
- Contexto viene del logging en vivo/paper → necesita 30+ trades acumulados
- Por eso Fase 1 usa heurísticas mientras se acumula data real

### Por qué 69.71% en 1-min NO es el modelo a usar
- El RF base predice dirección de BARRA (short horizon, ~2 min)
- El meta-model predice si el TRADE de BBv5 ganará (mucho más útil, horizonte horas)
- Features completamente distintas — no se pueden mezclar
- El RF base sirve como sanity check de régimen, no como gating directo

## Conceptos Quant de IAs (Gemini/Grok) — rescatados
### Shannon Entropy como filtro de régimen
- `H = -sum(p_i * log2(p_i))` sobre distribución de retornos recientes
- H alto (>2.8) = mercado aleatorio/chop → no operar
- H bajo (<1.5) = estructura direccional → operar
- Implementado en `quant_brain.py`, función `calcular_entropia_shannon()`

### Kalman 2D (position + velocity)
- Estado `[precio, velocidad]` con matriz 2x2
- `velocity > 0` = trend alcista detectado sin lag
- Opuesto al KalmanZScore (que era mean-reversion) — este es trend-following
- Código completo en `Bot_Quant_IA/Estrategias Grok/KalmanTrendNQ.cs`
- **Pendiente backtest** — probablemente funciona en MNQ bull 2023-2026

### OU (Ornstein-Uhlenbeck) — Half-life
- Modelo estocástico para mean-reversion: `dx = θ(μ-x)dt + σdW`
- `half-life = ln(2)/θ` — tiempo que tarda en revertir el 50%
- Solo entrar si half-life < horizonte de holding
- Código en `Bot_Quant_IA/Estrategias Grok/OU_VWAP_NQ.cs`
- Aplicar solo en rangos (ADX<20) — complemento al HMM regime filter

### NQ-ES Cointegración
- `spread = NQ - β×ES` donde β ≈ 1.65-1.68 (rolling OLS 200 barras)
- Entra cuando spread > 2.5σ desviación, sale al cruzar media
- Market-neutral → funciona en crashes (2020, 2022)
- Requiere adaptar para MNQ ($2/pt) vs MES ($5/pt) antes de backtest
- Código completo en `Bot_Quant_IA/Estrategias Grok/NQ_ES_Spread.cs`

## KalmanZScore_v1 — DESCARTADA como standalone
- Archivo: `Strategies/KalmanZScore_v1.cs`
- Concepto: Kalman estima precio justo → Z-score de desviación → entrada contrarian cuando Z > ±ZEntry sigmas
- Resultado: Mejor config = 15-min Long-only PF=1.47, R²=0.69, Sortino=0.39, **64 trades/3años** ❌
- Motivo falla: Mean-reversion no funciona en MNQ 2023-2026 (bull trend estructural). ADX<25 deja muy pocos trades.
- Mejor uso futuro: Como **filtro de régimen** sobre estrategias existentes (no como señal de entrada independiente)

## MomentumZ_v1 — CONFIRMADA (Renko 45, 03/03/2026)
- Archivo: `Strategies/MomentumZ_v1.cs` — Reporte: `Reports/21_MomentumZ_v1.md`
- Concepto: `MomScore = (Close[0] - Close[N]) / ATR[0]` = cuántos ATRs se movió el precio en N barras
- Equivalente intradiario del Sharpe ratio de momentum de AQR/Moskowitz
- **Params ganadores**: LookbackBars=10, MomThreshold=3.0, TargetRR=3, StopATRMult=1.0, ATRPeriod=7, MinVolRatio=1.3
- **Resultados (Renko 45)**: PF=1.74, R²=0.95, Sortino=3.89, MaxDD=$449/ct
  - Long PF=1.86, Short PF=1.59 — ambas direcciones positivas
- **Sizing**: 16ct → MaxDD=$7,194 ✅ → Profit/mes≈$3,390
- **Optimización clave** (de peor a mejor): RR=2→3 (+PF), ATR=14→7 (+Sortino), StopATR=1.5→1.0 (+R²), MinVol=1.2→1.3 (final)
- **Brick sizes testados**: Todos probados — Renko 45 ganador
