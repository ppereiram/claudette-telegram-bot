# CLAUDE.md — Trader Bot "Midas" — Contexto de sesión

## Proyecto
- **Plataforma**: NinjaTrader 8 (NinjaScript / C#) + Python brain
- **Instrumento**: MNQ (Micro E-mini Nasdaq 100) — TickSize=0.25, PointValue=$2, TickValue=$0.50
- **Objetivo**: Bot 100% autónomo → Apex funded account → Darwin/X 2027
- **Idioma**: SIEMPRE en español
- **Directorio**: `c:\Users\Pablo\Documents\Obsidian Vault\Trader Bot`

## Reglas Críticas — NUNCA romper
1. `Slippage = 1` en TODAS las estrategias (estándar desde 26/02/2026)
2. **NUNCA corregir** el "Filtro Accidental" (bug `dailyPnL` en ULTRA/SCALPER) — ES el edge real
3. Longs+Shorts combinados SIEMPRE mejor que separados — nunca dividirlos
4. Backtests SIEMPRE con comisiones incluidas
5. R² > 0.85 mínimo para entrar al portafolio
6. MaxDD debe caber en Apex $7,500
7. Tiempos SIEMPRE en ET en el código (función `GetEtTime()` aplicada a todas las estrategias)
8. `market_monitor_logger.py` corre CADA DÍA — NO saltarse ningún día (combustible de Markov)

## Estado actual (Marzo 2026)
- **Fase**: Paper trading 15+ estrategias simultáneas en cuentas sim
- **Brain**: Fase heurística recolectando datos para RF + Markov
- **Roadmap**: Construcción del brain Abril 2026 (ver `memory/roadmap_abril2026.md`)
- **Mejor estrategia**: StatMeanCross_v1 (Renko 35, PF=2.56, Sortino=38.73)

## Contexto del usuario
- Trader independiente, construyendo track record para capital externo
- Prefiere respuestas directas, sin relleno
- Siempre quiere código completo listo para copiar-pegar
- Fecha formato: DD/MM/YYYY

## Archivos de memoria (leer para contexto completo)
- `memory/MEMORY.md` — índice principal (siempre cargado)
- `memory/strategies_portfolio.md` — params detallados de cada estrategia
- `memory/brain_midas_arquitectura.md` — arquitectura completa del brain Midas
- `memory/diario_lecciones.md` — diario de trading y lecciones para Midas
- `memory/roadmap_abril2026.md` — roadmap semana a semana
- `memory/quant_strategies.md` — matemáticas y quant docs
