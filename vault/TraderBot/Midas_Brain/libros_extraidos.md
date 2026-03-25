---
name: libros_extraidos
description: Conceptos extraídos de cada libro de la biblioteca de Pablo — qué se incorporó a Midas y qué quedó pendiente
type: project
---

# Biblioteca de Midas — Conceptos Extraídos por Libro

> Metodología: cada libro se analiza en busca de conceptos NO YA planificados en Midas.
> Solo se incorpora lo que añade una capa nueva real. El ruido se descarta.

---

## LIBRO 1 — "Machine Learning for Algorithmic Trading" (Stefan Jansen, 2nd Ed.)
**Ruta:** `C:\Users\Pablo\Dropbox\0. CREANDO RIQUEZA\QUANTITATIVE FINANCE\`
**Analizado:** 23/03/2026
**Estado:** ✅ 7 conceptos incorporados a brain_midas_arquitectura.md

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Deflated Sharpe Ratio (DSR) | AHORA | deflated_sr.py | 🔲 Pendiente |
| GARCH(1,1) volatility regime | Semana 1 Abril | garch_vol.py | 🔲 Pendiente |
| Information Coefficient (IC) | Semana 2 Abril | tit_for_tat.py (update) | 🔲 Pendiente |
| HRP (Hierarchical Risk Parity) | Semana 3 Abril | hrp_optimizer.py | 🔲 Pendiente |
| Wavelet Denoising de features | Semana 2 Abril | wavelet_filter.py | 🔲 Pendiente |
| Purging + Embargoing en CV | Semana 4 Abril | cv_financial.py | 🔲 Pendiente |
| SHAP Values (explicabilidad RF) | Semana 4 Abril | brain_v2.py (update) | 🔲 Pendiente |
| TimeGAN (datos sintéticos) | Mayo 2026 | timegan_augment.py | 🔲 Pendiente |

**Lo que el libro confirmó como YA correcto en Midas:**
Markov, Kelly, Random Forest, PPO/RL, LSTM/RecurrentPPO, GA, ATR/RSI/VWAP/EMA

---

---

## LIBRO 2 — "Hidden Markov Models in Finance" (Mamon & Erlwein, Springer)
**Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| EM Online con forgetting factor ρ=0.97 | Semana 1 Abril | markov_regime.py (update) | 🔲 |
| Vector observación 3D [ret, \|ret\|, Δvol] | Semana 1 Abril | markov_regime.py | 🔲 |
| Selección n_estados por BIC (óptimo=3 para Nasdaq) | Semana 1 Abril | markov_regime.py | 🔲 |
| Regime Persistence Filter (3 días + umbral 0.65) | Semana 2 Abril | markov_regime.py | 🔲 |
| Kelly-HMM por régimen (half-kelly condicional al estado) | Semana 3 Abril | monte_carlo_sizer.py | 🔲 |

---

## LIBRO 3 — "Active Portfolio Management" (Grinold & Kahn)
**Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Alpha Decay IC-rolling (degradación del edge) | **AHORA** | market_monitor_logger.py | 🔲 |
| Breadth efectivo: N/(1+(N-1)×ρ) ≈ 5.5 para Midas | Semana 1 Abril | hrp_optimizer.py | 🔲 |
| Transfer Coefficient TC: IR = TC×IC×√Breadth | Semana 2 Abril | tit_for_tat.py | 🔲 |
| Signal Combination IC-ponderada (no 1/N) | Semana 2 Abril | brain_v2.py | 🔲 |
| Optimal weights Grinold (λ = aversión al riesgo = Von Neumann) | Semana 3 Abril | regret_engine.py | 🔲 |

---

## LIBRO 4 — "ML for Financial Risk Management with Python" (2022)
**Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Correlation Breakdown EWMA + CUSUM | **AHORA** | correlation_monitor.py | 🔲 |
| CVaR / Expected Shortfall | Semana 2 Abril | monte_carlo_sizer.py | 🔲 |
| Stress Testing escenarios históricos NQ | Semana 2 Abril | stress_tester.py | 🔲 |
| Dynamic Risk Limits HMM (Quiet/Volatile/Crisis) | Semana 2 Abril | regret_engine.py | 🔲 |
| LSTM Drawdown Predictor P(DD > threshold) | Mayo | brain_v3.py | 🔲 |

---

## LIBRO 5 — "From Data to Trade" (Maxim Bouev, 2023)
**Analizado:** 23/03/2026 | **Estado:** ✅ 13 conceptos incorporados (análisis actualizado — contenido options omitido en primera pasada)

**Capa 1 — Infraestructura ML (análisis original):**

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| PSI Drift Detection (feature distribution monitoring) | Semana 2 Abril | autocritica_daily.py | 🔲 |
| Kalman Spread NQ/ES online (market_breadth estacionario) | Semana 1 Abril | market_monitor_logger.py | 🔲 |
| CPCV Purged Walk-Forward (ya en Jansen — confirma) | Semana 4 Abril | cv_financial.py | 🔲 |
| Log-Signature features (Rough Path Theory) | Mayo | brain_v2.py | 🔲 |
| Micro-Price imbalance (order flow sin Level 2) | Mayo | market_monitor_logger.py + NT8 | 🔲 |

**Capa 2 — Options Market Intelligence (análisis profundo 23/03/2026):**

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| VIX Term Structure Slope VTS (VIX3M-VIX)/VIX — leading indicator régimen, antes que GARCH | Semana 1 Abril | vix_term_structure.py | 🔲 **habría prevenido 06/03+17/03** |
| IV Rank + IV Percentile (IVR>70=estrategias reversión; IVR<30=momentum — feature RF) | Semana 1 Abril | iv_rank_monitor.py | 🔲 |
| PCR-Vol + PCR-OI ajustado (QQQ options: PCR>1.3=bullish contrarian; <0.7=bearish) | Semana 2 Abril | options_sentiment.py | 🔲 |
| SKEW Index + 25d Risk Reversal (^SKEW>145 = tail_risk_alto → size×0.50) | Semana 2 Abril | options_sentiment.py | 🔲 |
| Volatility Risk Premium VRP (IV-RV: VRP>5=sobrehedge=bullish; VRP<-2=crash_warning) | Semana 2 Abril | vrp_signal.py | 🔲 |
| IV Surface Slope por DTE (IV_7d/IV_30d>1.15 = evento implícito detectado → size×0.60) | Semana 3 Abril | iv_term_structure.py | 🔲 |
| Gamma Exposure + Gamma Flip level (GEX<0 por debajo flip → no longs) | Semana 3 Abril | gamma_exposure.py | 🔲 |
| Options-Adjusted Momentum OAM (PCR+VRP+momentum combinados → tide_score potenciado) | Semana 4 Abril | options_adjusted_momentum.py | 🔲 |

**Todos los datos via yfinance gratuito:** ^VIX, ^VIX3M, ^SKEW, QQQ options chain

---

## LIBRO 6 — "Quantitative Trading 2nd Ed." (Ernest P. Chan, 2021)
**Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| CUSUM Strategy Breakdown Monitor | **AHORA** | market_monitor_logger.py | 🔲 |
| Kelly Multivariate con matriz de correlación | **AHORA** | monte_carlo_sizer.py | 🔲 |
| Variance Ratio Test (mean reversion vs trend) | Semana 1 Abril | markov_regime.py | 🔲 |
| Kalman Regime Tracker (slope continuo, reemplaza tide_score estático) | Semana 2 Abril | market_monitor_logger.py | 🔲 |
| Marginal IR (criterio de admisión de estrategias al portafolio) | Semana 3 Abril | hrp_optimizer.py | 🔲 |

---

## LIBRO 7 — "Decoding the Quant Market" (Gautier Marti, 2023)
**Analizado:** 23/03/2026 | **Nota:** Libro generado por GPT-4, sin investigación original
**Estado:** ✅ 3 conceptos útiles extraídos (resto era ruido)

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Autoencoder Anomaly Detection (habría parado 06/03 y 17/03) | Semana 1 Abril | anomaly_detector.py | 🔲 |
| SVM Regime Classifier (sin asumir gaussianidad, complementa HMM) | Semana 2 Abril | markov_regime.py | 🔲 |
| Regime-Aware Ensemble (pesos por régimen para cada estrategia) | Semana 4 Abril | brain_v2.py | 🔲 |
| Order Imbalance Score (microestructura intraday) | Mayo | market_monitor_logger.py | 🔲 |

---

---

## LIBRO 8 — "Algorithmic Short-Selling with Python" (Laurent Bernut, 2021)
**Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Triple Screen Score cuantificado (fix ventana ciega tide_score) | **AHORA** | triple_screen_score.py | 🔲 |
| Vol Regime Percentile (percentil 252 días) | Semana 1 Abril | vol_regime_percentile.py | 🔲 |
| Gain-to-Pain Ratio (GPR) como selector de portafolio | Semana 1 Abril | gain_to_pain_selector.py | 🔲 |
| Floor/Ceiling Mean Reversion Score | Semana 2 Abril | floor_ceiling_score.py | 🔲 |
| Crowding/Short Interest Monitor (COT NQ + skew opciones) | Semana 3 Abril | crowding_risk_monitor.py | 🔲 |

---

## LIBRO 9 — "High Probability Trading Strategies" (Robert Miner, 2008)
**Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| DTosc — Dual Timeframe Stochastic | Semana 1 Abril | dtosc_mtf_score.py | 🔲 |
| Momentum Position (MomPos normalizado contra su propio rango) | Semana 1 Abril | momentum_position.py | 🔲 |
| Trade Quality Score TQS (confluencias pre-trade = ConvictionScore) | Semana 2 Abril | trade_quality_score.py | 🔲 |
| Fibonacci Zone Filter (entrada solo en zona ±0.5 ATR de Fibo) | Semana 2 Abril | fibonacci_zone_filter.py | 🔲 |
| Swing ABC Pattern (entry en onda C post-corrección B) | Semana 3 Abril | swing_abc_pattern.py | 🔲 |

---

## LIBRO 10 — "Inside the Black Box" (Rishi K. Narang, 2013)
**Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Signal Half-Life Sizing (OU process → escalar Kelly por half-life) | Semana 1 Abril | monte_carlo_sizer.py | 🔲 |
| Alpha Decay Measurement (ventana temporal de validez de señal individual) | Semana 1 Abril | alpha_decay_analyzer.py | 🔲 |
| Triple Regime Filter (3 capas ortogonales: vol+corr+mom) | Semana 1 Abril | markov_regime.py | 🔲 |
| Model Decay Monitor (rolling t-stat, early warning) | Semana 1 Abril | autocritica_daily.py | 🔲 **CRÍTICO** |
| Alpha Orthogonalizer (PCA + constraint correlación) | Semana 2 Abril | hrp_optimizer.py | 🔲 |
| Factor Risk Model intraday (expo a mom/vol/VWAP por estrategia) | Semana 3 Abril | factor_risk_model.py | 🔲 |
| Robustness Testing Surface (robustness_score = PF_vecinos/PF_óptimo ≥ 0.80) | Semana 4 Abril | robustness_tester.py | 🔲 |
| Implementation Shortfall Tracker | Live trading | execution_tracker.py | 🔲 |

---

## LIBRO 11 — "Modern Time Series Forecasting with Python" (Manu Joseph, 2022)
**Analizado:** 23/03/2026 | **Estado:** ✅ 9 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| STL Seasonality intraday (session_bias_score horario) | Semana 2 Abril | market_monitor_logger.py | 🔲 |
| Global Model Portfolio (pooling cross-estrategias, patrones correlación) | Semana 2 Abril | global_model_portfolio.py | 🔲 |
| PWDA + MDV (métricas P&L para evaluar RF, no accuracy) | Semana 3 Abril | evaluate_brain_v2.py | 🔲 |
| Quantile Loss / Pinball Loss (Q10/Q50/Q90 dinámico → Kelly forward-looking) | Semana 3 Abril | quantile_forecaster.py | 🔲 |
| Conformal Prediction Intervals (IC empíricos agnósticos a distribución) | Semana 1 Abril | conformal_prediction.py | 🔲 |
| Variable Selection Network (VSN del TFT, pesos dinámicos por timestep) | Semana 4 Abril | variable_selection_network.py | 🔲 |
| N-HiTS retornos (multi-rate sampling, supera LSTM en series cortas) | Semana 4 Abril | nhits_signal.py | 🔲 |
| AdaptiveForecaster (SGD online + RF base, corrección de drift) | Semana 4 Abril | adaptive_brain.py | 🔲 |
| ForecastEnsemble meta-learner (Ridge régimen-aware) | Mayo | ensemble_brain.py | 🔲 |

---

## LIBRO 12 — "The Mathematics of Money Management" (Ralph Vince, 1992)
**Analizado:** 23/03/2026 | **Estado:** ✅ 7 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Safe f calibrado a Apex ($7,500 DD, 95% confianza) | **AHORA** | monte_carlo_sizer.py | 🔲 **CRÍTICO** |
| Portfolio Heat Monitor (riesgo activo simultáneo en tiempo real) | **AHORA** | portfolio_heat_monitor.py | 🔲 **URGENTE** |
| Optimal f empírico (distribución real, no gaussiana) | Semana 1 Abril | optimal_f_calculator.py | 🔲 |
| Geometric Mean Maximization (ranking real de estrategias) | Semana 2 Abril | geometric_mean_optimizer.py | 🔲 |
| TWR como función objetivo (penaliza path dependency, vs Sharpe) | Semana 2 Abril | twr_portfolio_optimizer.py | 🔲 |
| Portfolio f conjunto con correlación ajustada | Semana 3 Abril | monte_carlo_sizer.py | 🔲 |
| Leverage Space Surface (superficie n-dimensional TWR conjunto) | Semana 3 Abril | leverage_space_surface.py | 🔲 |

---

## LIBRO 13 — "Advanced Futures Trading Strategies" (Robert Carver, 2023)
**Analizado:** 23/03/2026 | **Estado:** ✅ 9 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| N efectivo de estrategias (máx ~5 independientes en MNQ) | **AHORA** (análisis) | hrp_optimizer.py | 🔲 |
| Correlation Regime Detector (Portfolio Stop dinámico cada 30-60min) | Semana 1 Abril | correlation_monitor.py | 🔲 **URGENTE** |
| Forecast Scaling + Cap (normalizar señales a [-20,+20] antes de combinar) | Semana 1 Abril | forecast_scaling.py | 🔲 |
| Handcrafted Weights (grupos ρ>0.7, peso igual, más robusto que HRP con N<30) | Semana 1 Abril | handcrafted_weights.py | 🔲 |
| Carry/Roll Yield (sizing -50% en semana de rollover NQ) | Semana 1 Abril | market_monitor_logger.py | 🔲 |
| FDM (Forecast Diversification Multiplier) | Semana 2 Abril | hrp_optimizer.py | 🔲 |
| Cost-Adjusted SR (turnover penalty → filtro pre-inclusión de estrategias) | Semana 2 Abril | cost_adjusted_sr.py | 🔲 |
| Vol Targeting (contratos dinámicos EWMA-25, 20% anualizado) | Semana 3 Abril | vol_target_sizing.py | 🔲 |
| Carry Signal (señal trading independiente spot-futuro NQ, combinar con tide_score) | Semana 3 Abril | carry_signal.py | 🔲 |

---

## LIBRO 14 — "Markets in Profile" (James Dalton, 2007)
**Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Open Type Classifier (4 tipos: Drive / Test-Drive / Rejection-Reverse / Auction) | **AHORA** | open_type_classifier.py | 🔲 **URGENTE** |
| Value Area High/Low (VAH/VAL) + POC diario | Semana 1 Abril | market_profile_features.py | 🔲 |
| Initial Balance (IB) predictor del rango del día | Semana 1 Abril | market_profile_features.py | 🔲 |
| Auction Rotation Factor (ARF: rotaciones bi/uni-direccionales → régimen) | Semana 1 Abril | auction_rotation_factor.py | 🔲 |
| Profile Shape (D/P/b/I → sesgo para el día siguiente) | Semana 2 Abril | market_profile_features.py | 🔲 |
| POC Migration (sesgo direccional del fair value) | Semana 2 Abril | market_profile_features.py | 🔲 |
| Single Prints (TPOs solitarios sin vol = imanes de precio) | Semana 2 Abril | profile_structure_map.py | 🔲 |
| Excess/Poor High-Low (agotamiento de extremos) | Semana 3 Abril | market_profile_features.py | 🔲 |

---

## LIBRO 15 — "Trading Order Flow" (Michael Valtos, 2022)
**Analizado:** 23/03/2026 | **Estado:** ✅ 7 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| CVD Divergence (precio nuevo máx/mín pero delta no confirma) | Semana 1 Abril | order_flow_monitor.py | 🔲 |
| Absorption/Exhaustion Detection (alto vol + precio quieto = iceberg) | Semana 2 Abril | order_flow_monitor.py | 🔲 |
| Volume Profile POC dinámico (VAH/VAL en tiempo real) | Semana 2 Abril | order_flow_monitor.py | 🔲 |
| Stop Raid Pattern / Liquidity Sweep (spike past swing + delta flip + reversal) | Semana 3 Abril | stop_raid_detector.py | 🔲 |
| Stacked Imbalances (footprint patterns, 3+ niveles) | Mayo | order_flow_monitor.py | 🔲 |
| of_score compuesto (CVD + Absorption + POC + Delta Rate) | Mayo | brain_v2.py | 🔲 |
| Large Trader Fingerprint (prints anomalos >500 contratos en tape) | Mayo | large_trader_detector.py | 🔲 |

---

## LIBRO 16 — "Mastering Financial Pattern Recognition" (2022)
**Analizado:** 23/03/2026 | **Estado:** ✅ 10 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Conditional Pattern Probability (CPP) P(éxito\|contexto) | **AHORA** | conditional_pattern_probability.py | 🔲 **URGENTE** |
| Pattern Quality Score (edge = hit_ratio - breakeven_hr) | Semana 1 Abril | pattern_quality.py | 🔲 |
| Forward-Walk Pattern Validator (degradation score por setup) | Semana 1 Abril | walkforward_pattern_validator.py | 🔲 |
| Trend Intensity Index (TII, % bricks sobre MA) | Semana 2 Abril | market_monitor_logger.py | 🔲 |
| ATR Quality Filter (señales válidas si rango > 1.5×ATR) | Semana 2 Abril | market_monitor_logger.py | 🔲 |
| Pattern Reliability Score (PRS: bootstrap rolling PF/winrate) | Semana 2 Abril | pattern_reliability_scorer.py | 🔲 |
| Pattern Decay Analysis (half-life del edge por estrategia) | Semana 2 Abril | pattern_decay_analyzer.py | 🔲 |
| Symmetrical Target + RR Filter (≥1.5 para ABCDHarmonic) | Semana 3 Abril | brain_v2.py | 🔲 |
| Renko Pattern Clusterer (DTW, familias de secuencias similares) | Semana 3 Abril | renko_pattern_clusterer.py | 🔲 |
| Dynamic Position Size (hit ratio reciente + half-Kelly) | Semana 4 Abril | monte_carlo_sizer.py | 🔲 |

---

---

## LIBRO 17 — "Machine Learning for Asset Managers" (López de Prado, 2020)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| CUSUM Filter (event-driven sampling, reemplaza barras fijas) | Semana 1 Abril | cusum_filter.py | 🔲 |
| Triple Barrier Method (etiquetado: PT/SL/timeout) | Semana 1 Abril | triple_barrier.py | 🔲 |
| Meta-Labeling (RF predice si trade primario gana, no dirección) | Semana 4 Abril | brain_v2.py | 🔲 **CRÍTICO** |
| Fractional Differentiation (d≈0.3 para estacionariedad con memoria) | Semana 2 Abril | wavelet_filter.py | 🔲 |
| MDI/MDA/SFI Feature Importance (SFI: modelo por feature individual) | Semana 4 Abril | brain_v2.py | 🔲 |
| Bet Sizing Kelly-ML (Kelly continuo desde prob RF) | Semana 4 Abril | monte_carlo_sizer.py | 🔲 |
| Clustering Regímenes sin supervisión (K-Means sobre features market) | Semana 1 Abril | regime_clusterer.py | 🔲 |
| Deflated Sharpe Ratio (DSR) | AHORA | deflated_sr.py | 🔲 (también Libro 1) |

**Pipeline integrado:** CUSUM → Frac.Diff → Triple Barrier → MDI/SFI → Meta-RF → Kelly-ML → HRP

---

## LIBRO 18 — "Algorithmic Trading and DMA" (Barry Johnson, 2010)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Momentum Ignition Detector (spike precio+vol → reversión 2-3 bricks, inhibe estrategias) | **AHORA** | anomaly_detector.py | 🔲 **URGENTE** |
| Almgren-Chriss Scheduler (escalonar entradas entre estrategias correlacionadas) | Semana 1 Abril | almgren_chriss_scheduler.py | 🔲 |
| TCA Pre-trade Estimator (costo estimado antes de ejecutar: spread+slippage+comms) | Semana 1 Abril | pre_trade_tca.py | 🔲 |
| POV Liquidity Filter (reducir sizing si volumen barra < P10 del día) | Semana 1 Abril | vol_regime_percentile.py | 🔲 |
| Spread Decomposition — Adverse Selection Component (fracción informada del spread) | Semana 2 Abril | spread_decomposition.py | 🔲 |

**Insight clave:** Momentum Ignition explica incidentes 06/03 (-$11,920) y 17/03 (-$8,906) — es el filtro más urgente del libro.

---

## LIBRO 19 — "Building Winning Algorithmic Trading Systems" (Kevin Davey, 2014)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| CAGR/MaxDD (Calmar Ratio) como métrica primaria de ranking | **AHORA** | strategies_portfolio.md update | 🔲 |
| Degradation Monitor Live (50%→reduce 50%; 75%→stop) con t-stat rolling | **AHORA** | autocritica_daily.py | 🔲 |
| WFO Efficiency Ratio (OOS PF / IS PF ≥ 0.50 → estrategia robusta) | Semana 2 Abril | wfo_validator.py | 🔲 |
| Portfolio MC Correlated (sampleo trades correlacionados, no independientes) | Semana 3 Abril | portfolio_mc_correlated.py | 🔲 |
| Multi-Config Consistency (≥70% vecinos param con PF>1 → no curve-fitted) | Semana 2 Abril | robustness_tester.py | 🔲 |

**Insight clave:** Davey advierte Sortino=38.73 en backtest es señal de curve fitting — Robustness Surface sobre StatMeanCross es prioritario antes de Apex.

---

## LIBRO 20 — "Probabilistic Machine Learning for Finance and Investing" (2023)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 4 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| BOCPD — Bayesian Online Changepoint Detection (P(cambio_régimen) en tiempo real) | Semana 1 Abril | bocpd_detector.py | 🔲 |
| Entropy Pooling (Meucci) — redistribución capital por escenarios con correlación adversa | Semana 3 Abril | entropy_pooling.py | 🔲 |
| Factor Graph / Probabilistic Graphical Model (P(estrategia_activa\|régimen)) | Semana 4 Abril | factor_graph_signals.py | 🔲 |
| Hierarchical Bayesian Models (priors compartidos entre estrategias cortas historia) | Mayo | hierarchical_bayes.py | 🔲 |

**Insight clave:** BOCPD detecta changepoint en los PRIMEROS minutos (vs HMM que necesita barras para confirmar) — complemento urgente al Markov.

---

## LIBRO 21 — "Deep Learning for Finance" (Sofien Kaabar, 2024)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 4 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Feature Autoencoder (compresión de vector features para RF, limpia ruido) | Semana 1 Abril | feature_autoencoder.py | 🔲 |
| CNN para patrones de precio (OHLC → imagen → capas convolucionales) | Semana 2 Abril | cnn_pattern_detector.py | 🔲 |
| VAE Regime Detector (espacio latente continuo de regímenes) | Semana 3 Abril | vae_regime_detector.py | 🔲 |
| Temporal Attention Layer (ponderación dinámica de features por barra) | Semana 4 Abril | temporal_attention_layer.py | 🔲 |

**Nota:** Feature Autoencoder + VAE comparten arquitectura encoder — implementar juntos en Semana 3.

---

## LIBRO 22 — "Machine Learning for Factor Investing" (Coqueret & Guida, 2020)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Factor Timing Conditional (predice CUÁNDO un factor funciona, no dirección) | Semana 1 Abril | factor_timing_conditional.py | 🔲 |
| Feature Crosses / Interaction Effects (RSI×ATR, EMA_slope×vol_ratio) | Semana 2 Abril | feature_crosses.py | 🔲 |
| Rolling Feature Importance SHAP temporal (qué factor domina AHORA) | Semana 3 Abril | rolling_feature_importance.py | 🔲 |
| Turnover-Penalized Loss (penaliza cambios frecuentes de señal en entrenamiento) | Semana 4 Abril | turnover_penalized_trainer.py | 🔲 |
| Error Decorrelation Ensemble Stacking (meta-learner entrena sobre residuos, no preds) | Mayo | error_decorrelation_ensemble.py | 🔲 |

---

## LIBRO 23 — "Time Series Analysis with Python Cookbook" (Tarek Atwan, 2022)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 5 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Johansen Cointegration (NQ/ES/YM/RTY, confirmar relación largo plazo) | Semana 1 Abril | johansen_cointegration.py | 🔲 |
| Rolling ACF + Ljung-Box (monitor degradación temporal P&L estrategia) | Semana 1 Abril | autocorr_drift_monitor.py | 🔲 |
| Granger Causality ES→MNQ (lag 1-5 min, feature predictivo directo para RF) | Semana 2 Abril | granger_causality_mnq.py | 🔲 |
| Ruptures Change Points (cambios estructurales en P&L intraday, más preciso que CUSUM) | Semana 2 Abril | ruptures_regime_detector.py | 🔲 |
| Periodograma Espectral FFT (ciclos dominantes MNQ intraday en minutos) | Semana 3 Abril | spectral_cycle_detector.py | 🔲 |

---

## LIBRO 24 — "Learn Algorithmic Trading" (Donadio & Ghosh, 2019, Packt)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 9 conceptos incorporados

**Enfoque único del libro:** Infraestructura de producción defensiva — el único libro de la biblioteca que trata heartbeat, state machine y latency como ciudadanos de primera clase. Asume que todo va a fallar y construye desde ahí. Para Apex funded, esta mentalidad vale más que cualquier modelo adicional.

| Concepto | Fase | Archivo | Urgencia |
|---|---|---|---|
| Heartbeat Monitor ZMQ con reconexión automática | **AHORA** | heartbeat_watchdog.py | CRITICO |
| Pre-Trade Risk Gate (firewall pre-orden) | **AHORA** | pre_trade_gate.py | CRITICO |
| Alert System Multicanal Telegram (4 niveles severidad) | **AHORA** | alert_system.py | CRITICO |
| Order State Machine + Audit Log (.jsonl) | **AHORA** | order_state_machine.py | ALTO |
| Priority Signal Queue (exits primero, por Sortino) | Semana 1 Abril | priority_signal_queue.py | ALTO |
| Latency Profiler P50/P95/P99 por etapa del pipeline | Semana 1 Abril | latency_profiler.py | MEDIO |
| Tick Data Normalizer (spikes, dupes, out-of-session) | Semana 1 Abril | tick_data_normalizer.py | MEDIO |
| Paper/Live Switch con Parity Check (pre-Apex) | Pre-Apex | paper_live_switch.py | ALTO |
| Execution Quality Report (slippage real vs backtest) | Pre-Apex | execution_quality_report.py | ALTO |

**Lo que el libro confirma como ya correcto en Midas:**
ZeroMQ para comunicación NT8↔Python, Random Forest para señales, paper trading antes de live, comisiones en backtest, Slippage=1 como estándar.

**Insight clave:** Pre-Trade Risk Gate + Alert System habrían limitado los incidentes 06/03 (-$11,920) y 17/03 (-$8,906). Son los 2 módulos de mayor ROI del libro.

---

---

## LIBRO 25 — "Decoding the Quant Market" (Gautier Marti, 2023)
**Ruta:** `E:\QUANTITATIVE FINANCE\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 9 conceptos incorporados
**Nota:** Contenido posiblemente AI-generated, pero temas basados en papers reales de Marti (arXiv).

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| CORT Similarity (correlación + orden temporal, detecta timing coincidente entre estrategias) | Semana 1 Abril | correlation_monitor.py | 🔲 **URGENTE** |
| Hayashi-Yoshida Correlation (correlación real entre barras Renko asíncronas) | Semana 1 Abril | correlation_monitor.py | 🔲 |
| GNPR Transform (representación no-paramétrica rolling, robusto a cambios de régimen) | Semana 1 Abril | wavelet_filter.py | 🔲 |
| Wasserstein Distance Regime (distancia continua al régimen "normal" — pre-alerta) | Semana 1 Abril | market_monitor_logger.py | 🔲 |
| MST Mantegna-Stanley (árbol de expansión mínima — visualiza hub de contagio EMA(21)) | Semana 2 Abril | hrp_optimizer.py | 🔲 |
| MI-Distance Clustering (distancia por información mutua para HRP no-lineal) | Semana 2 Abril | hrp_optimizer.py | 🔲 |
| Alpha-Stable Lévy (α≈1.65 NQ → Kelly corregido por fat tails reales) | Semana 2 Abril | monte_carlo_sizer.py | 🔲 |
| Copulas Clayton/Student-t (tail dependence λ_L entre estrategias) | Semana 3 Abril | monte_carlo_sizer.py | 🔲 |
| Vol-Weighted Similarity (correlación ponderada por liquidez en barra) | Semana 3 Abril | correlation_monitor.py | 🔲 |

**Insight clave:** CORT + Hayashi-Yoshida son los primeros 2 a implementar — la correlación Pearson estándar entre barras Renko asíncronas subestima sistemáticamente la correlación real.

---

## LIBRO 26 — "Machine Trading" (Ernie Chan, 2017)
**Ruta:** `E:\QUANTITATIVE FINANCE\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 9 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Optimal Rebalancing Frequency (math del fix tide_score: rebalancear cada ½ × half-life alpha) | **AHORA** | market_monitor_logger.py | 🔲 **FIX VENTANA CIEGA** |
| Signal Decay Rate (half-life intraday del alpha — calibra si latencia ZMQ destruye edge) | Semana 1 Abril | autocritica_daily.py | 🔲 |
| Regime-Conditional Stop (stop/target asimétrico por percentil de volatilidad) | Semana 1 Abril | monte_carlo_sizer.py | 🔲 |
| Intermarket Lagged Momentum (DXY/RTY/TLT con rezago 1-3 días predice NQ) | Semana 2 Abril | market_monitor_logger.py | 🔲 |
| Kalman Adaptive Exit (stop dinámico via velocidad Kalman — exit preventivo 2-3 bricks antes) | Semana 2 Abril | brain_v2.py | 🔲 |
| Stochastic DD Signal (DD extremo intraday → estadísticamente revierte; no pánico) | Semana 2 Abril | monte_carlo_sizer.py | 🔲 |
| Bar Magnification (techo real de escalado contratos antes de Apex) | Semana 3 Abril | deflated_sr.py | 🔲 |
| Walk-Forward Anchored (WFA: IS siempre desde mismo origen — más robusto en bull NQ) | Semana 3 Abril | wfo_validator.py | 🔲 |
| Options Tail Hedge (collar mensual ~$0 costo neto — para cuenta propia Darwin/X 2027) | Mayo/Junio | hedge_manager.py | 🔲 |

---

## LIBRO 27 — "ML for Financial Risk Management with Python" (2022)
**Ruta:** `E:\QUANTITATIVE FINANCE\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 9 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Network Contagio (grafo rolling estrategias: densidad→1 predice drawdown sistémico) | Semana 1 Abril | network_contagio.py | 🔲 **URGENTE** |
| CDaR — Conditional Drawdown at Risk (duración+magnitud episodios DD para Darwin/X) | Semana 1 Abril | monte_carlo_sizer.py | 🔲 |
| EVT/GPD Fat Tails (cola izquierda NQ real: VaR(99%) es 20-40% más grande que gaussiano) | Semana 2 Abril | monte_carlo_sizer.py | 🔲 |
| Copula Tail Dependence Clayton (λ_L entre estrategias → trata como 1 slot si λ_L>0.4) | Semana 2 Abril | correlation_monitor.py | 🔲 |
| MS-GARCH Regime Risk (GARCH por estado: low-vol / high-vol — VaR condicional al estado) | Semana 2 Abril | garch_vol.py | 🔲 |
| GBT Drawdown Predictor (LightGBM predice P(DD>$500) próximos 3 días con market_logs) | Semana 2 Abril | drawdown_predictor.py | 🔲 |
| Factor Stress Testing Sintético (shocks por dimensión: vol_spike × correlacion_crisis) | Semana 2 Abril | stress_tester.py | 🔲 |
| Liquidity-Adjusted VaR (VaR ajustado por spread en barras de bajo volumen) | Semana 3 Abril | vol_regime_percentile.py | 🔲 |
| Risk Attribution SHAP (SHAP sobre P&L negativo → ¿qué feature causó 06/03 y 17/03?) | Semana 3 Abril | risk_attribution.py | 🔲 |

---

## LIBRO 28 — "Implementing ML for Finance" (2021, Packt)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Feature Store lightweight con versionado (captura features en señal, no retroactivo) | Semana 3 Abril | feature_store.py | 🔲 **URGENTE** |
| Isotonic Calibration → Kelly (prob RF bien calibrada para Kelly-ML sizing) | Semana 4 Abril | monte_carlo_sizer.py | 🔲 |
| Financial Preprocessing Pipeline (RobustScaler + winsorización dentro de sklearn.Pipeline) | Semana 4 Abril | meta_brain_bbv5.py | 🔲 |
| XGBoost + Focal Loss (supera RF en N<5000 samples con class imbalance) | Semana 4 Abril | meta_brain_bbv5.py | 🔲 |
| EV + MCC Metrics (ev_lift: ¿el meta-model realmente añade valor? criterio go/no-go) | Semana 4 Abril | evaluate_meta_model.py | 🔲 |
| Champion/Challenger A/B (modelo challenger observa en silencio; promueve con Mann-Whitney) | Semana 4 Abril | champion_challenger.py | 🔲 |
| SMOTE-Tomek financiero (oversampling clase minoritaria con respeto al orden temporal) | Semana 4 Abril | meta_brain_bbv5.py | 🔲 |
| Online SGD Corrector híbrido (RF batch + SGD online: capta drift en 3-5 trades vs 20) | Semana 3 Abril | meta_brain_bbv5.py | 🔲 |

---

## LIBRO 29 — "ML and Data Sciences for Financial Markets" (Capponi & Lehalle, 2023)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 7 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| VPIN Flow Toxicity Score (fracción volumen informado en tiempo real — inhibe mean-reversion) | Semana 2 Abril | vpin_flow_toxicity.py | 🔲 **URGENTE** |
| Adversarial Validation (RF detecta drift multivariante train vs live — detecta rollover MNQ) | Semana 2 Abril | autocritica_daily.py | 🔲 |
| FinBERT Event Classifier (ventana inhibición variable por tipo de evento: Fed=30min, Geo=60min) | Semana 2 Abril | finbert_event_classifier.py | 🔲 |
| Causal Do-Calculus Feature Filter (ATE real del feature vs correlación espuria) | Semana 4 Abril | cv_financial.py | 🔲 |
| Contrastive Regime Embedder (K días similares históricos → prior para sizing) | Mayo | contrastive_regime_embedder.py | 🔲 |
| GNN Correlation Regime (grafo neural: firma de correlaciones que precede a crash) | Mayo | gnn_correlation_regime.py | 🔲 |
| Deep RL Execution Scheduler (PPO aprende curva de impacto dinámica) | Mayo | rl_execution_scheduler.py | 🔲 |

---

## LIBRO 30 — "Entry and Exit Confessions" (Kevin Davey, 2nd book)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 9 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Setup Quality Score Pre-Entrada (checklist 5 condiciones: tide+ATR+news+vol+VWAP) | Semana 1 Abril | pre_trade_checklist.py | 🔲 |
| Volatility Stop Percentil ATR (stop distancia ajustada por percentil vol histórica) | Semana 1 Abril | market_monitor_logger.py | 🔲 |
| Anti-Martingala Condicional (sizing +25% en racha 3 wins + equity peak; -50% en 2 losses) | Semana 1 Abril | portfolio_heat_monitor.py | 🔲 |
| Time Stop Régimen-Condicional (N barras para resolver según ADX: 6/12/18 bricks) | Semana 2 Abril | cada .cs de estrategia | 🔲 |
| Señal Contraria como Exit Primario (exit type: objetivo fijo en ranging, señal contraria en trend) | Semana 2 Abril | exit_regime_selector.py | 🔲 |
| Scale-Out Estructural 1R/Runner (50% sale en 1R, runner con trailing stop en BE) | Semana 2 Abril | ULTRA/MomentumZ .cs | 🔲 |
| Pullback Depth Gate (0.5×ATR retroceso post-breakout antes de entrar) | Semana 3 Abril | PivotTrend/Darvas .cs | 🔲 |
| Structural Trailing Stop Swing (trailing por swing de N bricks contrarios) | Semana 3 Abril | EMATrend/MomentumZ .cs | 🔲 |
| Failed Breakout Reversal (nueva estrategia: ruptura fallida con vol + delta flip → reversal) | Mayo | FailedBreakout_v1.cs | 🔲 |

---

## LIBRO 31 — "The Book of Back-Tests" (Sofien Kaabar, 2021)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| SSL Channel como `ssl_score` (+1/0/-1, sin ventana ciega, reemplaza tide_score) | **AHORA** | market_monitor_logger.py | 🔲 |
| Techo máximo señales/estrategia (5-8 trades/día = límite viabilidad con costos MNQ) | **AHORA** | strategies_portfolio.md (análisis) | 🔲 |
| Hurst Exponent rolling 100 bricks Renko (H>0.55=trending, H<0.45=mean-rev, feature HMM) | Semana 1 Abril | markov_regime.py | 🔲 |
| PCR (Put-Call Ratio) diario via yfinance `^PCALL`/`^PCPUT` — sesgo direccional pre-apertura | Semana 1 Abril | market_monitor_logger.py | 🔲 |
| Ichimoku Kumo régimen (+1=sobre cloud / 0=dentro / -1=bajo) — segunda capa de tendencia | Semana 1 Abril | markov_regime.py | 🔲 |
| GEX (Gamma Exposure Index) — GEX>0: mean-reverting; GEX<0: trending → pesos por estrategia | Semana 2 Abril | markov_regime.py | 🔲 |
| COT Variable Barrier NQ (Bollinger sobre COT CFTC → filtro semanal de sesgo largo/corto) | Semana 2 Abril | market_monitor_logger.py | 🔲 |
| MIC (Maximal Information Coefficient) para feature selection (captura no-linealidades) | Semana 4 Abril | brain_v2.py | 🔲 |

**Validación de backtests (segunda capa — metodología Kaabar):**

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| OSRT (Out-of-Sample Ratio Test): Sharpe_OOS/Sharpe_IS > 0.50 + DD_OOS/DD_IS < 2.5x | **AHORA** | osrt_validator.py | 🔲 **criterio admisión faltante** |
| Hit Ratio Stability Score (HRSS): std(HR_rolling) / mean < 0.20 — base empírica TfT | Semana 1 Abril | hit_ratio_stability.py | 🔲 |
| Consecutive Loss Cluster Analysis (CLCA): test KS vs distribución geométrica teórica | Semana 1 Abril | consecutive_loss_cluster.py | 🔲 |
| Parameter Sensitivity Heatmap 2D (PSH): interacciones entre parámetros — picos estrechos = overfitting | Semana 1 Abril | param_sensitivity_heatmap.py | 🔲 |
| Symmetrical Performance Matrix (SPM): válido si PF>1 en MNQ+MES+NQ con mismos params | Semana 1 Abril | symmetrical_perf_matrix.py | 🔲 |
| Noise-to-Signal Ratio Test (NSR): PF_con_ruido/PF_original > 0.75 — fragilidad por ejecución | Semana 2 Abril | nsr_backtest_test.py | 🔲 |
| Cross-Asset Regime Validation (CARV): edge válido si funciona en ES/YM/RTY con misma lógica | Semana 2 Abril | cross_asset_regime_val.py | 🔲 |
| Trade Duration Distribution Test (TDDT): Mann-Whitney U ganadores vs perdedores en barras Renko | Semana 2 Abril | trade_duration_dist_test.py | 🔲 |

**Hallazgos negativos críticos (confirmaciones de lo que NO implementar):**
RSI standalone, MACD cross-zero, Stochastic solo, CCI, Parabolic SAR señal, BB contrarian, candlestick patterns, Awesome Oscillator → todos con expectancy negativa en índices. Solo usar como features secundarios del RF, nunca como señales primarias.

---

## LIBRO 32 — "Algorithmic Trading: A Practitioner's Guide" (Jeffrey Bacidore, 2020)
**Ruta:** `E:\QUANTITATIVE FINANCE\ + E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| IMRT (Intraday Momentum Reversal Threshold: k≈2.3×σ_día → feature contrarian/trend weight) | Semana 1 Abril | imrt_score.py | 🔲 |
| FRQS (Fill Rate Quality Score por estrategia/hora/régimen → detecta slippage > Slippage=1) | Semana 1 Abril | fill_quality_monitor.py | 🔲 |
| Arrival Price Benchmark (vs Decision Price → mide costo real de latencia ZMQ) | Semana 1 Abril | arrival_price_tracker.py | 🔲 |
| Participation Rate Adaptive (PRA: sizing como %volumen del minuto — reduce slippage baja liquidez) | Semana 2 Abril | participation_rate_sizer.py | 🔲 |
| Shortfall Decomposition 4 componentes (Timing+Impact+Opportunity+Fees → opportunity cost al TfT) | Semana 2 Abril | shortfall_decomposer.py | 🔲 |
| Pre-Trade Cost Model Spread Elasticity (costo ∝ size^0.6 × vol × 1/ADV — no lineal) | Semana 2 Abril | pre_trade_cost_model.py | 🔲 |
| Alpha Capture vs Alpha Decay intraday (escala segundos: 50% alpha perdido en 2-3 min post-señal) | Semana 2 Abril | alpha_capture_tracker.py | 🔲 |
| Volume Clock (reescalar tiempo a unidades de volumen → retornos más estacionarios para HMM) | Semana 3 Abril | volume_clock_resampler.py | 🔲 |

**Confirmaciones del libro:** IS genérico (Narang), TCA lineal (Johnson), Almgren-Chriss, slippage en C#.
**Descartado:** TWAP/VWAP como benchmark para small retail futures → Arrival Price es superior (Bacidore argumento explícito).

---

## LIBRO 33 — "Developing High-Frequency Trading Systems" (Donadio, Ghosh, Rossier, 2022)
**Ruta:** `E:\QUANTITATIVE FINANCE\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Latency Budget Tracking (SLA por etapa: t_send+t_transit+t_process+t_return — detecta brain lento) | **AHORA** | latency_monitor.py | 🔲 **prerequisito infraestructura** |
| Position Reconciliation Loop (shadow book Python vs NT8 — detecta split de estado post 20/03) | **AHORA** | position_reconciler.py | 🔲 **bug infraestructura** |
| Adaptive Throttle Gate (ATG: máx N señales en 10min — previene burst correlacionado 06/03+17/03) | Semana 1 Abril | throttle_gate.py | 🔲 |
| Sequence Number Gap Detection (seq_id en ZMQ — detecta mensajes perdidos con conexión activa) | Semana 1 Abril | servidor_ia.py (modificar) | 🔲 |
| Correlation Monitor + Dynamic Slot Allocation (correlación rolling: si >0.7 → solo 1 slot activo) | Semana 1 Abril | correlation_monitor.py | 🔲 **PRIORIDAD ALTA** |
| Order Book Imbalance Ratio (OBIR=bid_qty/(bid+ask) via Level 2 NT8 — intención latente pre-move) | Semana 2 Abril | order_book_imbalance.py | 🔲 (requiere Level 2) |
| Session State Machine FSM (IDLE→ACTIVE→THROTTLED→SUSPENDED→EOD — estados explícitos y trazables) | Semana 2 Abril | session_state_machine.py | 🔲 |
| Execution Quality Score (EQS: p50/p90/p99 slippage real por estrategia/hora — detecta drift vs Slippage=1) | Semana 3 Abril | execution_quality.py | 🔲 |

**Nota de deduplicación:** EQS complementa B4-49 (Execution Quality Report) con distribución percentil en vivo. Correlation Slots formaliza el insight de MEMORY.md ("tratar StatMean+EMATrend como 1 slot") en código ejecutable.

---

## LIBRO 34 — "Artificial Intelligence for Financial Markets" (Capponi & Lehalle eds., Springer 2022)
**Ruta:** `E:\ALGO TRADING\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| Adversarial Regime Detector (LightGBM: AUC>0.70 entre datos recientes vs histórico → early warning) | Semana 1 Abril | adversarial_regime_detector.py | 🔲 **2h implementación, usa logs existentes** |
| Cascade Risk Score (eigenvalue matriz corr×size → Portfolio Stop si >0.70 — resuelve 17/03) | Semana 2 Abril | cascade_risk_score.py | 🔲 **15 líneas, ROI inmediato** |
| Mean-Field Game Portfolio Stop (N estrategias = campo medio → bloquea entrada cuando intensity>0.65) | Semana 2 Abril | mean_field_portfolio_stop.py | 🔲 |
| Almgren-Chriss Execution Scheduler (turno 2min entre N estrategias en apertura — reduce impact) | Semana 3 Abril | execution_scheduler.py | 🔲 (complementa B3-11) |
| Sparse Attention Regime Detection (2 attention heads: aprende qué días históricos son relevantes hoy) | Semana 4 Abril | sparse_attention_regime.py | 🔲 (complementa HMM) |
| Counterfactual Explanations (qué tan lejos estuvo un trade bloqueado de aprobarse — alibi library) | Semana 4 Abril | counterfactual_explainer.py | 🔲 |
| Nash Q-Learning Anti-Correlación (estrategias aprenden espontáneamente a no entrar juntas) | Mayo | nash_q_learning.py | 🔲 |
| Renko Path Signatures nivel 2 (25 features de geometría path — invariante a tiempo Renko variable) | Mayo | renko_signature_features.py | 🔲 (confirma Libro 5 Log-Sig) |

**Nota de deduplicación:** Adversarial Regime Detector ≠ B4-22 (Adversarial Validation Capponi). B4-22 detecta drift train vs live. Este detecta cuando el régimen actual difiere del histórico de entrenamiento → early-warning antes del primer fallo. Almgren-Chriss Execution Scheduler es extensión de B3-11: B3-11 escalonaba entradas correlacionadas; este escalonaba la queue de todas las N estrategias en apertura.

---

## LIBRO 35 — "Teoría de Juegos" (Ken Binmore, edición española)
**Ruta:** `C:\Users\Pablo\Downloads\...\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 6 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| ESS (Evolutionarily Stable Strategy): detecta que estrategias con mismo genotipo EMA(21) no co-existen establemente | Semana 2 Abril | ess_strategy_selector.py | 🔲 |
| Folk Theorem (cooperación con descuento δ): cuando δ cae en alta volatilidad → portfolio cooperativo se rompe → reducir tamaño | Semana 2 Abril | folk_theorem_cooperation.py | 🔲 |
| Correlated Equilibrium (brain como correlacionador central — Pareto-superior a Nash) | Semana 3 Abril | correlated_equilibrium_router.py | 🔲 **solución formal 17/03** |
| Revelation Principle + Mecanismo IC (sizing por Sharpe rolling = mecanismo que extrae tipo real de estrategia) | Semana 3 Abril | mechanism_design_incentives.py | 🔲 |
| Bayesian Game tipos ocultos (cada estrategia tiene tipo privado: sesgo en régimen actual) | Semana 4 Abril | bayesian_game_portfolio.py | 🔲 |
| Signaling Game + Separating Equilibrium (test Cho-Kreps: señal separadora real vs pooling/ruido) | Mayo | signaling_game_regime.py | 🔲 |

**Extiende:** TfT (ESS + Folk Theorem + Revelation Principle), Von Neumann (Bayesian Game), Nash Q-Learning (Correlated Equilibrium)

---

## LIBROS 36-40 — Cluster Market Profile / Auction Theory
**Dalton: Markets in Profile + Markets and Market Logic | Steidlmayer: Markets A New Approach + Steidlmayer on Markets | Value-Based Power Trading (Jones)**
**Ruta:** `C:\Users\Pablo\Downloads\...\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

> **Por qué es la capa más única de toda la biblioteca:** Market Profile responde WHO controls the price NOW basándose en distribución de participantes en tiempo real. Ningún oscilador, regresión ni ML responde esto — trabajan sobre qué pasó, MP trabaja sobre quién controla el precio ahora.

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| VAH/VAL Context (open dentro/fuera del VA previo → 80% prob de viaje al otro extremo del VA) | Semana 1 Abril | market_profile_features.py | 🔲 **imán estructural** |
| Initial Balance Expansion (IB range 9:30-10:30 ET: extensión >1.5x = día tendencia real) | Semana 1 Abril | market_profile_features.py | 🔲 |
| POC Migration (dirección migración del Point of Control hora a hora = sesgo institucional) | Semana 1 Abril | market_profile_features.py | 🔲 |
| Excess vs Poor High/Low (calidad del extremo: single prints = rechazo; múltiples TPOs = re-test inminente) | Semana 2 Abril | market_profile_features.py | 🔲 |
| Single Prints (agujeros en perfil = subasta pendiente → imán de retorno ~70% probabilidad) | Semana 2 Abril | market_profile_features.py | 🔲 |
| TFP Control Score (OTP institucional vs Local retail: +1=OTP bull / -1=OTP bear / 0=Local choppy) | Semana 2 Abril | tfp_control_detector.py | 🔲 **combate 17/03** |
| Profile Shape (D/P/b/B/trending: perfil B = doble distribución = chop destructor → size×0.25) | Semana 3 Abril | market_profile_features.py | 🔲 |
| Auction Rotation Factor (rotaciones aceptadas vs rechazadas por período → estado de subasta) | Semana 3 Abril | market_profile_features.py | 🔲 |

**Implementación requiere:** datos de TPO del día (NinjaTrader tiene Market Profile indicator nativo que puede exportar va_high, va_low, poc vía C# → ZMQ → Python)

---

## LIBRO 41 — "High-Frequency Trading: A Practical Guide" (Irene Aldridge, 2013) + "LIT Trap Trading"
**Ruta:** `C:\Users\Pablo\Downloads\...\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| HFT Participation Rate (cancellation_rate proxy: vol/tick↑ = flow genuino vs HFT noise) | Semana 1 Abril | order_flow_monitor.py (update) | 🔲 |
| FVG Quantifier (Fair Value Gap: gap 3-velas = imán retorno 50-70% — feature price action RF) | Semana 1 Abril | fvg_detector.py | 🔲 |
| CHoCH Detector (Change of Character: primer break swing + vol>P75 = cambio estructura intraday) | Semana 1 Abril | choch_detector.py | 🔲 |
| Adverse Selection Tracker (midprice drift post-entry: estrategias con drift↑ = operando contra flow) | Semana 2 Abril | adverse_selection_tracker.py | 🔲 |
| Cross-Asset Lead-Lag intraday (CCF ES→MNQ lag 2-30s — extensión intraday del breadth diario) | Semana 2 Abril | lead_lag_detector.py | 🔲 |
| Liquidity Pool Map (swing highs/lows + round numbers + wick extremos = zonas de stop hunt) | Semana 2 Abril | liquidity_pool_map.py | 🔲 |
| Inducement Score (minor swing + vol<P60 + cierre-en-3-bricks = pre-filtro Failed Breakout) | Semana 2 Abril | inducement_score.py | 🔲 |
| Intraday Liquidity Clock (volume-normalized time — confirma B5-28 Bacidore, misma idea) | Semana 2 Abril | volume_clock.py | 🔲 (confirma Bacidore) |

**Notas deduplicación:** Volume Clock confirma B5-27 (Bacidore), misma implementación. Lead-Lag es extensión intraday (segundos) de B3-19 Granger ES→MNQ (diario). CHoCH complementa B3-20 Ruptures (macro) con nivel intraday estructural.

## LIBROS 42-43 — FRM Exam Part 1 Book 2 (GARP, 2025) + CMT Level III (CMT Association, 2024)
**Ruta:** `C:\Users\Pablo\Downloads\...\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 6 conceptos incorporados

| Concepto | Fuente | Fase | Archivo | Estado |
|---|---|---|---|---|
| RRG (Relative Rotation Graph: JdK RS-Ratio + RS-Momentum — rotación cuadrante NQ vs índices) | CMT III | Semana 1 Abril | rrg_breadth_score.py | 🔲 **reemplaza market_breadth_score** |
| PAS (Portfolio Alignment Score: alineación estructural prospectiva vs régimen HMM — complementa TfT) | CMT III | Semana 2 Abril | portfolio_alignment_score.py | 🔲 **habría filtrado 17/03** |
| Intermarket Divergence Score (NQ vs SOX/HYG/VIX/DXY rolling corr < P20 = alerta régimen) | CMT III | Semana 2 Abril | intermarket_divergence_score.py | 🔲 |
| Basel Traffic Light Test (verde/amarillo/rojo: conteo excepciones VaR en 250 días rolling) | FRM Book 2 | Semana 3 Abril | var_model_validator.py | 🔲 |
| Kupiec POF Test + Christoffersen (chi-cuadrado LR: valida cobertura y clustering excepciones) | FRM Book 2 | Semana 3 Abril | var_model_validator.py | 🔲 |
| Spectral Risk Measures (φ(p) weighting: peor 1% pesa 10x > peor 5% — calibrado a Apex $7,500) | FRM Book 2 | Mayo | spectral_risk_measure.py | 🔲 |

## LIBROS 44-46 — Trader Dale: VWAP Trading + Order Flow Trading Setups + Volume Profile (2024)
**Ruta:** `C:\Users\Pablo\Downloads\...\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 8 conceptos incorporados

| Concepto | Fase | Archivo | Estado |
|---|---|---|---|
| CVD (Cumulative Volume Delta: ask_vol - bid_vol acumulado — señal divergencia precio/flujo) | Semana 1 Abril | cvd_monitor.py | 🔲 (proxy (C-O)×Vol hasta NT8 ZMQ) |
| VWAP SD Bands intraday (±1σ/2σ/3σ: régimen dinámico por sesión — fix ventana ciega tide_score) | Semana 1 Abril | vwap_regime_intraday.py | 🔲 **FIX DOCUMENTADO MEMORY.md** |
| Poor High / Poor Low (último 10% rango <20% vol promedio → subasta incompleta → retorno >60%) | Semana 1 Abril | market_profile_features.py | 🔲 |
| POC + Value Area S/R intraday (POC del día anterior: imán rechazo/breakout — confirma Dalton) | Semana 1 Abril | market_profile_features.py | 🔲 |
| Absorption Detection (delta en POC/VWAP: flujo agresivo absorbido → reversión alta probabilidad) | Semana 2 Abril | absorption_detector.py | 🔲 **mejora OFR_v1 de PF=2.20 a >3.0** |
| Initial Balance Classifier (initiative: IB<0.75×ATR5 + expansión unilateral → activar tendencia) | Semana 2 Abril | initial_balance_classifier.py | 🔲 **habría filtrado 06/03+17/03** |
| POC Migration intraday (POC sube durante sesión = distribución confirmada; oscila = chop) | Semana 2 Abril | market_profile_features.py | 🔲 |
| Footprint Imbalance (bid vs ask ejecutado por nivel: imbalance >3:1 = S/R persistente) | Mayo | footprint_imbalance.py | 🔲 (requiere tick data NT8) |

**Nota implementación:** VWAP SD Bands calculable 100% vía yfinance 1-min cada 5min durante sesión — sin infraestructura adicional. CVD usa proxy (Close-Open)×Vol hasta que NT8 exporte tick data via ZMQ. Los conceptos 3/4/6 van en `market_profile_features.py` (mismo módulo que Dalton).

## LIBROS 47-50 — Chan vol1 + Way of the Turtle + Trading No Predictivo + Survival Guide
**Ruta:** `C:\Users\Pablo\Downloads\...\` | **Analizado:** 23/03/2026 | **Estado:** ✅ 6 conceptos incorporados

| Concepto | Fuente | Fase | Archivo | Estado |
|---|---|---|---|---|
| Units Correlation Cap (límite duro C#: MaxCorrelatedUnits=6 — regla Turtle operativa sin ML) | Curtis Faith | **AHORA** | correlation_units_cap.cs | 🔴 **habría limitado 17/03** |
| Comeback Ratio DD Ladder (CR = 1/(1-loss)-1: sizing intraday por DD actual, determinista) | Survival Guide | **AHORA** | portfolio_heat_monitor.py (ext.) | 🔴 **habría limitado 06/03** |
| ADF+Hurst+OU gate binario (tres tests combinados: si falla uno → StatMeanCross no opera ese día) | Chan vol.1 | Semana 1 Abril | mean_reversion_gate.py | 🔲 **protege mejor estrategia** |
| Signal Staleness Filter (barras desde breakout sin retest > umbral → signal inválida) | Curtis Faith | Semana 1 Abril | signal_staleness_filter.py | 🔲 |
| Condition Map (árbol exhaustivo pre-mercado: si VIX+5%+news+bear → ALL size×0.25, sin ML) | Trading No Pred. | Semana 1 Abril | condition_map.py | 🔲 **cubre edge cases extremos** |
| Exit Signal Asymmetry (time decay: cuanto más tiempo abierto sin resolver → trailing más ajustado) | Chan vol.1 | Semana 2 Abril | trade_time_decay_exit.py | 🔲 |

## LIBRO 51 — Binmore (Teoría de Juegos) → ver Libro 35

---

## ANÁLISIS COMPLETO — Todos los libros procesados ✅

Todos los libros de `E:\QUANTITATIVE FINANCE\`, `E:\ALGO TRADING\` y `C:\Users\Pablo\Downloads\Telegram` han sido analizados:
- **Libros 1-16:** Batch 1+2 (23/03/2026) — fundamentos quant, volatilidad, momentum, ML
- **Libros 17-30:** Batch 3+4 (23/03/2026) — microestructura, gamma exposure, infraestructura
- **Libros 31-34:** Batch 5 (23/03/2026) — Kaabar BT, Bacidore, HFT Sys, AI for Financial Mkts
- **Libro 5 (Bouev):** Análisis actualizado capa 2 con options intelligence (23/03/2026)
- **Libros 35-50:** Batch 6 — Telegram folder (23/03/2026):
  - Libro 35: Ken Binmore (Game Theory) — ESS, Folk Theorem, Correlated Eq., Bayesian Game
  - Libros 36-40: Dalton/Steidlmayer Market Profile × 5 — VAH/VAL, IB, POC, Single Prints, TFP
  - Libro 41: Aldridge HFT + LIT Trap — FVG, CHoCH, Adverse Selection, Lead-Lag, Inducement
  - Libros 42-43: FRM Book 2 + CMT III — RRG, PAS, Intermarket, Basel TL, Spectral Risk
  - Libros 44-46: Trader Dale × 3 — VWAP SD Bands, CVD, Absorption, IB Classifier, Footprint
  - Libros 47-50: Chan vol1 + Turtle + Trading No Pred + Survival Guide — Units Cap, Comeback Ratio, ADF Gate

**Total conceptos incorporados:** ~120 conceptos únicos a través de 50+ libros
**AHORA (máxima urgencia):** VWAP SD Bands · CVD · Units Correlation Cap · Comeback Ratio DD Ladder
**Top impacto sobre resultados históricos:** Units Cap (17/03) · Comeback Ratio (06/03) · IB Classifier (06/03+17/03) · Correlated Equilibrium (17/03)

---

## REGLA DE INCORPORACIÓN

Antes de agregar un concepto de un libro a la arquitectura, verificar:
1. ¿Ya está planificado en brain_midas_arquitectura.md? → No agregar, solo confirmar
2. ¿Requiere datos que Midas no tiene? → Marcar fase correcta
3. ¿Añade una capa real de edge o es complejidad gratuita? → Solo incorporar si es edge real
4. ¿Cuánto esfuerzo de implementación? → Priorizar los de bajo esfuerzo / alto impacto primero
