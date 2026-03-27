# Trader Bot "Midas" — Memory Index

## Contexto rápido
- **Plataforma**: NinjaTrader 8 | **Instrumento**: MNQ | **Meta**: Darwin/X 2027
- **Usuario**: Pablo | **Idioma**: Español siempre | Totalmente automatizado
- **Fase actual** (03/2026): Paper trading 15+ estrategias + construcción brain Midas
- **Roadmap activo**: Abril 2026 — construcción del brain semana a semana

## Archivos de memoria (leer según contexto)
| Archivo | Contenido |
|---------|-----------|
| `strategies_portfolio.md` | Params completos de cada estrategia, rankings, descartadas |
| `brain_midas_arquitectura.md` | Stack matemático completo de Midas (Markov, Minimax, TfT, MC, RF, RL, GA + capas nuevas) |
| `diario_lecciones.md` | Diario de trading 02/03-26/03 — 8 lecciones con pérdidas reales documentadas |
| `manual_buenas_practicas.md` | **7 niveles de reglas operativas** derivadas del paper trading — el escudo para real money |
| `objetivos_competencias.md` | Darwin/X 2027 + USIC (después de Darwin) — contexto mercado 2026 atípico |
| `roadmap_abril2026.md` | Plan semana a semana desde 01/04/2026 hasta Darwin/X |
| `quant_strategies.md` | Kelly, ML Meta-Labeling, Kalman, Hurst, OU process |
| `libros_extraidos.md` | Conceptos extraídos de cada libro de la biblioteca de Pablo |

## Top 5 estrategias (por Sortino)
| Estrategia | PF | Sortino | MaxDD | Profit/mes |
|------------|-----|---------|-------|------------|
| StatMeanCross_v1 (Renko 35) | 2.56 | **38.73** | $2,668 | $4,092 |
| BreadButter_ULTRA (Renko 35) | 2.03 | **18.52** | $6,903 | $9,378 |
| PivotTrendBreak_v1 (Renko 25) | 1.92 | **8.50** | $2,730 | $2,305 |
| EMATrendRenko_v1 (Renko 35) | 2.29 | **6.75** | $7,460 | $4,825 |
| OrderFlowReversal_v1 (Renko 45) | 2.20 | **5.80** | $5,146 | $2,831 |

## Reglas críticas — NUNCA romper
1. `Slippage = 1` en TODAS las estrategias
2. **NUNCA corregir** el Filtro Accidental en ULTRA/SCALPER → ES el edge
3. Longs+Shorts combinados SIEMPRE mejor que separados
4. Backtests SIEMPRE con comisiones
5. R² > 0.85 mínimo para el portafolio
6. MaxDD dentro de Apex $7,500
7. Tiempos siempre en ET en el código (`GetEtTime()`)
8. `market_monitor_logger.py` CADA DÍA — NO saltarse (combustible de Markov)

## Estado del brain Midas
- **Módulo 1** (Market Monitor): ✅ ACTIVO desde 09/03/2026 — `Bot_Quant_IA/market_monitor_logger.py`
- **Módulo 1b** (Auto-Crítica Diaria): 🔲 IMPLEMENTAR AHORA — agregar a market_monitor_logger.py. Compara predicción de ayer vs realidad de hoy. Output: `autocritica_YYYY-MM-DD.json` + `midas_accuracy_historico.json`
- **Módulo 2** (Markov): 🔲 Semana 1 Abril — necesita 30+ días de logs + auto-críticas
- **Módulo 3** (News Filter): 🔲 Semana 2 Abril
- **Módulo 4** (Tit for Tat): 🔲 Semana 2 Abril
- **Módulo 5** (Von Neumann Regret): 🔲 Semana 3 Abril
- **Módulo 6** (Monte Carlo): 🔲 Semana 3 Abril
- **Módulo 7** (Brain v2 RF completo): 🔲 Semana 4 Abril

## Lecciones críticas del diario (ver `diario_lecciones.md` para detalle completo)
- **17/03 -$8,906**: StatMean+EMATrend+BBv5 Long simultáneos → correlación catastrófica
- **20/03 patrón**: mismo evento en shorts → correlación estructural (EMA(21))
- **06/03 -$11,920**: peor día — sin análisis forense, probable noticias + sin Portfolio Stop
- **13/03 +$7,191**: mejor día — portafolio alineado con mercado, sin correlación adversa
- **24/03 DIAGNÓSTICO COMPLETO**: Longs=+$7,248 (PF=1.17) / Shorts=-$9,095 (PF=0.80) — los SHORTS destruyen el portafolio. Sin filtro de tendencia diaria = ruina en bull market. MaxDD -$29K viene de shorts.
- **El edge existe**: +$7K en longs en 23 días es real. Problema = estrategias short sin filtro direccional
- **Bug infraestructura**: strategies_pnl JSON borrados por auto_push_pnl.bat → CSV de NT8 es la verdad

## Adiciones nuevas pendientes (de sesión 20/03/2026)
- **market_breadth_score** (Sem 1 Abril): ES=F + YM=F + RTY=F via yfinance → confirmar dirección NQ
- **multi_osc_score** (Sem 2 Abril): MFI + RSI + Stochastic consenso → feature para brain_v2
- **Arquitectura Elswee** (Sem 2 Abril): ConvictionScore secuencial Exhaustion→Realignment→Volume
- **OBOrderFlow_v1.cs** (Mayo): Bo$$ Order Block concept en 1-min chart (no Renko)

## Insights clave no obvios
- Filtro Accidental (ULTRA/SCALPER): `dailyPnL += Commission + AverageFillPrice * Quantity` suma nominal → dispara MaxLoss → 1 trade/día. NO tocar.
- BreadButterBALANCED: combined PF=1.31 — el edge viene de la competición long/short por el slot
- StatMean+EMATrend comparten EMA(21) → correlación estructural → tratar como 1 slot si coinciden
- tide_score 1x/día genera ventana ciega de 4-7h intraday → fix: calcular cada 60s
- EMA Touch es el setup dominante de ULTRA — los otros 3 setups no añaden PF
- Rollover MNQ cambia datos Renko → re-validar estrategias con nuevo contrato
- **NUEVO 24/03**: PivotReverse+DarvasBox+SuperTrendWave = 3 estrategias short sin filtro direccional → suspender shorts hasta implementar tide_score_intraday + VWAP SD Bands

## Métricas target Darwin/X 2027
| Métrica | Mínimo | Ideal | Darwin/X |
|---------|--------|-------|----------|
| Sharpe | >1.0 | >1.5 | >2.0 |
| Sortino | >2.0 | >3.0 | >4.0 |
| MaxDD | <$7,000 | <$5,000 | <$4,000 |
| Profit/mes | >$2,000 | >$5,000 | >$8,000 |
| P(ruin) | <10% | <5% | <2% |
| Correlación | <0.7 | <0.5 | <0.4 |
