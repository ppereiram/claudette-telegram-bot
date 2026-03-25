# SuperTrendWave v1.1
> Trend-following con piramidación | Paper trading activo desde 19/02/2026 | `Strategies/SuperTrendWave.cs`

---

## Resumen ejecutivo

| Métrica | Renko (principal) | 5-min (benchmark) |
|---|---|---|
| Profit Factor (con comm) | **1.41** | 1.18 |
| PF sin comisiones | 1.73 | — |
| Max Drawdown | **$3,074** | — |
| Trades/día | multi | — |
| Chart | Renko | 5-min |
| Estado | 📝 **Paper trading** | Referencia |

> Inicio paper trading: 19/02/2026, 1 contrato, AllowShort=OFF

---

## Concepto y edge

Sistema de **trend-following puro con piramidación al estilo Elliott**. A diferencia de las demás estrategias del portafolio que tienen un target fijo, SuperTrendWave **no tiene profit target** — deja correr la posición mientras el SuperTrend no flipee.

### Mecánica de entrada
1. SuperTrend define la dirección (alcista = solo longs)
2. Se detecta un pullback dentro de la tendencia
3. Cuando el precio rompe el high anterior al pullback → entrada
4. Si el precio hace otro pullback y rompe un nuevo high → pirámide (agrega contrato)
5. Sale cuando el SuperTrend cambia de dirección

### Piramidación
- Máximo `MaxLevels` contratos acumulados
- `StopTargetHandling.ByStrategyPosition` — UN stop para toda la posición piramidada
- El stop se mueve según el SuperTrend conforme avanza el precio

### Por qué Renko funciona mejor que 5-min
- Renko filtra el ruido intra-barra — solo forma bricks cuando hay movimiento real
- Los parámetros del SuperTrend (ATR=14, Mult=3.0) calibran la sensibilidad del trailing
- Resultado: **PF=1.41 en Renko vs PF=1.18 en 5-min** con los mismos parámetros

---

## Parámetros ganadores

| Parámetro | Valor | Notas |
|---|---|---|
| Chart | Renko | Mejor que time-based para trend-following |
| ATR Period | 14 | Para el SuperTrend |
| Multiplicador | 3.0 | Balance entre sensibilidad y ruido |
| AllowShort | **OFF** | MNQ es alcista estructuralmente |
| UsePrimeHoursOnly | ON | Evita sesiones de baja liquidez |
| MaxLevels | TBD | Define agresividad de la pirámide |

---

## El incidente del 20/02/2026

**Primer día de paper trading**: El mercado abrió con chop extremo — Renko formaba bricks en 5-20 segundos en lugar de minutos normales. El sistema entró múltiples veces en corto tiempo y acumuló -$730 en el primer día.

**Lección aprendida**: Los mercados muy choppy de madrugada/apertura pueden generar bricks Renko artificialmente rápidos. Esto motivó la propuesta del **Choppiness Index Filter** en el Roadmap.

**Acción pendiente**: Si el patrón se repite (días malos en mañanas volátiles), implementar CI > 61.8 como filtro de no-entrada.

---

## Plan de paper trading

| Período | Acción |
|---|---|
| 19/02 — 20/03/2026 | Paper trading 1ct, AllowShort=OFF, anotar días problemáticos |
| ~20/03/2026 | Revisión de métricas reales vs backtest |
| Si métricas OK | Evaluar escalar a cuenta real |
| Si hay patrón de días malos | Implementar Choppiness Index Filter |

---

## Fortalezas

- **MaxDD $3,074** — el más bajo del portafolio, perfecto para Apex
- **Sin profit target** — deja correr tendencias fuertes (alta MFE)
- **Piramidación** — único en el portafolio, captura impulsos de varios puntos
- **Descorrelacionado** — Renko chart en timeframe diferente a todas las demás

## Debilidades / Riesgos

- **Choppy markets** — sin el filtro CI, días con mucho ruido pueden generar muchas entradas rápidas
- **Confianza estadística** — el backtest en Renko puede ser más susceptible a condiciones específicas del período
- **Parámetros Renko** — el tamaño del brick afecta dramáticamente los resultados; necesita calibración con datos reales
- **PF=1.18 en 5-min** — el benchmark honesto sin el "efecto Renko" es moderado

---

## Sizing potencial para Apex

| Contratos | MaxDD estimado | Viable Apex $7,500 |
|---|---|---|
| 2 | ~$6,148 | ✅ |
| 3 | ~$9,222 | ❌ |

**Recomendación**: Esperar paper trading y operar máximo 2ct en Apex.
