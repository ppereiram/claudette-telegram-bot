# Trader Bot "Midas" — Memory Index

## Contexto rápido
- **Plataforma**: NinjaTrader 8 | **Instrumento**: MNQ | **Meta**: Darwin/X 2027
- **Usuario**: Pablo | **Idioma**: Español siempre | Totalmente automatizado
- **Fase actual** (03/2026): Paper trading 4 semanas completadas + construcción brain Midas
- **Roadmap activo**: Semana 0 Abril 2026 — análisis de marzo antes de construir

## Archivos de memoria (leer según contexto)
| Archivo | Contenido |
|---------|-----------|
| `strategies_portfolio.md` | Params backtest + **resultados reales 4 semanas (02/03-30/03)** — divergencia crítica |
| `brain_midas_arquitectura.md` | Stack matemático + **código Python ya deployado** (meta_brain.py etc.) |
| `diario_lecciones.md` | 10 lecciones documentadas 02/03-30/03 con pérdidas reales |
| `manual_buenas_practicas.md` | 7 niveles de reglas operativas — el escudo para real money |
| `objetivos_competencias.md` | Darwin/X 2027 + USIC — Pablo quiere ser el próximo Larry Williams |
| `roadmap_abril2026.md` | Plan semana a semana desde 01/04/2026 hasta Darwin/X |
| `quant_strategies.md` | Kelly, ML Meta-Labeling, Kalman, Hurst, OU process |
| `libros_extraidos.md` | Conceptos extraídos de cada libro de la biblioteca de Pablo |
| `feedback_ninza_pipeline.md` | Pipeline ninZa/RenkoKings — extraer ideas sin comprar |
| `feedback_session_continuity.md` | Al reanudar sesión interrumpida: retomar hilo activo, no ejecutar pending tasks |
| `project_apex_sizing.md` | Position sizing Apex: 1 micro base, Monte Carlo define escalado. Markov self-learning desde 07/04 |

## Resultados reales 4 semanas (02/03 – 30/03/2026)
| Estrategia | P&L Real | vs Backtest |
|---|---|---|
| BBv5_Apex | **+$21,238** | ↑↑↑ Backtest decía $873/mes |
| DarvasBox | **+$16,824** | ↑↑↑ Backtest decía $2,426/mes |
| PivotReverse | +$5,038 | ↑ |
| PivotTrendBreak | **-$6,287** | ↓↓↓ Backtest decía +$2,305/mes |
| SuperTrendWave | -$3,979 | ↓↓ |
| EMATrendRenko | -$3,697 | ↓↓ (inflado por AllEntries bug) |
| **Portfolio total** | **+$23,134** | BBv5 = 92% de las ganancias |

> Lección: BBv5 Filtro Accidental (1 trade/día) no aparece en backtest estándar → divergencia masiva.
> Riesgo de concentración: sin BBv5 el portafolio tiene +$1,896 en 4 semanas.

## Reglas críticas — NUNCA romper
1. `Slippage = 1` en TODAS las estrategias
2. **NUNCA corregir** el Filtro Accidental en ULTRA/SCALPER/BBv5 → ES el edge
3. Longs+Shorts combinados SIEMPRE mejor que separados
4. Backtests SIEMPRE con comisiones
5. R² > 0.85 mínimo para el portafolio
6. MaxDD dentro de Apex $7,500
7. Tiempos siempre en ET en el código (`GetEtTime()`)
8. `market_monitor_logger.py` CADA DÍA — NO saltarse (combustible de Markov)

## Estado del brain Midas
- **Módulo 1** (Market Monitor): ✅ ACTIVO desde 09/03/2026 — `Bot_Quant_IA/market_monitor_logger.py`
- **Módulo 1b** (Auto-Crítica Diaria): 🔲 PENDIENTE — agregar a market_monitor_logger.py
- **Módulo 2** (Markov): 🔲 Semana 1 Abril — necesita 30+ días de logs
- **Módulo 3** (News Filter): ✅ ACTIVO desde 27/03/2026 — VIX + Fear&Greed + Forex Factory calendar
- **meta_brain.py**: ✅ CÓDIGO EXISTE — ZMQ port 5556, heurístico→RF unificado por estrategia. Conectar a NT8 en Abril
- **Módulo 4** (Tit for Tat): 🔲 Semana 2 Abril
- **Módulo 5** (Von Neumann Regret): 🔲 Semana 3 Abril
- **Módulo 6** (Monte Carlo): 🔲 Semana 3 Abril
- **Módulo 7** (Brain v2 RF completo): 🔲 Semana 4 Abril

## Pendientes críticos — Semana 1 Abril (desde 31/03/2026)
1. **Bug AllEntries** → `EntryHandling.UniqueEntries` en: `EMATrendRenko_v1.cs`, `OrderFlowReversal_v1.cs`, `PivotTrendBreak_v1.cs`, **+ RE-VERIFICAR DarvasBox** (CSV 30/03 muestra patrón 20-contratos aún activo)
2. **Módulo 3 fix** → `avoid_shorts` cruzar con `tide_score`: si `tide_score <= -2.0`, no aplicar avoid_shorts
3. **Revisar/suspender** estrategias en MaxDD >$3K: EMATrendRenko, SuperTrendWave, PivotTrendBreak
4. **BBv5 re-entradas** → trades sin nombre de estrategia post-Filtro-Accidental
5. **Encoding UTF-8 BOM** → `auto_push_pnl.bat` genera archivos con BOM (`ï»¿` al inicio). El `→` en el archivo está correcto — el problema es el BOM que confunde la lectura en Windows. Fix: agregar `encoding='utf-8'` sin BOM en el script bat o en el Python que escribe el JSON.

## Insights clave no obvios
- **Filtro Accidental** (BBv5/ULTRA/SCALPER): `dailyPnL += Commission + AverageFillPrice * Quantity` → dispara MaxLoss → 1 trade/día. NUNCA corregir.
- **StatMean+EMATrend** comparten EMA(21) → correlación estructural → tratar como 1 slot si coinciden
- **avoid_shorts + tide_score**: si tide_score ≤ -2.0, la tendencia bajista domina sobre VIX EXTREME — no aplicar avoid_shorts (BBv5 short +$6,103 el 27/03 con VIX=31 lo confirma)
- **AllEntries bug**: qty inflado en 4 estrategias → pérdidas hasta 18x reales. Fix = UniqueEntries.
- **Intervención manual EOD** para take profit (cuando mercado llegó a objetivo) es correcta. Intervención mid-trade para "asegurar" es destructiva (costo documentado: -$633 el 26/03)
- **tide_score 1x/día** → ventana ciega 4-7h intraday. Fix pendiente: calcular cada 60s via ZMQ
- **BBv5 concentración**: 92% de las ganancias del portafolio en 4 semanas vienen de 1 estrategia

## Lecciones críticas (ver `diario_lecciones.md` para detalle)
- **06/03 -$11,920**: peor día — sin Portfolio Stop, probable noticias
- **13/03 +$7,191**: mejor día — portafolio alineado con mercado
- **17/03 -$8,906**: StatMean+EMATrend+BBv5 Long simultáneos → correlación EMA(21)
- **24/03 diagnóstico**: Longs +$7,248 / Shorts -$9,095 — shorts sin filtro direccional destruyen el PF
- **27/03 +$3,431**: Paradoja Módulo 3 — avoid_shorts=True pero tide=-3.0, BBv5 short ganó +$6,103
- **30/03 +$11,779**: BBv5 home run -451 pts. Portfolio total: +$23,134 en 4 semanas

## Métricas target Darwin/X 2027
| Métrica | Mínimo | Ideal | Darwin/X |
|---------|--------|-------|----------|
| Sharpe | >1.0 | >1.5 | >2.0 |
| Sortino | >2.0 | >3.0 | >4.0 |
| MaxDD | <$7,000 | <$5,000 | <$4,000 |
| Profit/mes | >$2,000 | >$5,000 | >$8,000 |
| P(ruin) | <10% | <5% | <2% |
| Correlación | <0.7 | <0.5 | <0.4 |
