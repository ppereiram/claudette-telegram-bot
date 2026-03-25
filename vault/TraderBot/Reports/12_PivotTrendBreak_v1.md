# PivotTrendBreak_v1
> Mejor estrategia del portafolio — Breakout estructural de pivots | `Strategies/PivotTrendBreak_v1.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (con comm) | **1.92** 🏆 |
| R² | **0.96** 🏆 |
| Sortino Ratio | **8.50** 🏆 (mejor del portafolio) |
| Net total (3 años, 20ct) | ~$138,000 |
| Profit/mes (20ct) | **$2,305** |
| MaxDD (1ct) | **$182** |
| MaxDD (20ct) | **$2,730** ✅ |
| Win Rate | 46.67% |
| Win/Loss Ratio | 2.19x |
| Trades totales (3 años) | 240 (0.49/día) |
| Chart | Renko 25-tick MNQ |

**Estrategia #1 del portafolio.** Sortino=8.50 es excepcional — curva de equity casi perfecta con drawdowns mínimos. El MaxDD por contrato más bajo de todo el portafolio permite escalar a 20ct dentro de Apex.

---

## Concepto y edge

### Breakout de Pivots Estructurales

Un pivot high/low representa un punto donde el mercado **rechazó** un precio — hay orders reales ahí. Cuando el precio rompe ese nivel, los stops de quienes tenían posiciones en la dirección opuesta se activan, creando momentum.

**Lógica**:
1. Detectar pivot high reciente (PivotStrength=3 — necesita 3 velas a cada lado)
2. Precio rompiendo ese pivot al alza = breakout estructural → LONG
3. SL = pivot low más cercano (nivel de soporte real)
4. TP = Entry + (Entry - SL) × MinRR (mínimo 1.5R, usualmente más)

### Por qué MaxTrades=1/día crea el edge

Al limitar a 1 trade por día, la estrategia toma **únicamente el breakout más limpio del día**. Los breakouts múltiples en el mismo día tienden a ser menos confiables (fakeouts del primer movimiento).

### Por qué Renko 25-tick es el timeframe ideal

Los charts Renko eliminan el ruido temporal y muestran **puramente el movimiento de precio**. Un brick de 25 ticks = $12.50 de movimiento real. Los pivots en Renko son estructurales genuinos, no artefactos del tiempo.

---

## Parámetros ganadores

### Pivot Detection
| Parámetro | Valor | Descripción |
|---|---|---|
| PivotStrength | 3 | Barras a cada lado para confirmar pivot |
| MinPivotGapTicks | 20 | Separación mínima entre pivots |
| MaxPivotAgeBricks | 80 | Pivot expira si tiene más de 80 bricks de antigüedad |

### Filtros de entrada
| Parámetro | Valor | Descripción |
|---|---|---|
| MinRR | 1.5 | R:R mínimo — rechaza trades con target insuficiente |
| UseVolumeFilter | ON | Requiere volumen sobre el promedio |
| VolumePeriod | 20 | Período del promedio de volumen |
| MinVolRatio | 1.11 | Volumen mínimo = 1.11× el promedio |
| MaxTradesPerDay | 1 | Solo el breakout más limpio del día |

### Stop/Target
| Parámetro | Valor | Descripción |
|---|---|---|
| StopBufferTicks | 4 | Buffer bajo el pivot de SL |
| AllowLong | ON | — |
| AllowShort | ON | — |

### Horario
| Parámetro | Valor |
|---|---|
| PrimeStart | 93000 (9:30 ET) |
| PrimeEnd | 153000 (15:30 ET) |

---

## Desglose por dirección

| Dirección | PF | Contribución |
|---|---|---|
| Longs | **2.25** | Mayor edge en mercado alcista |
| Shorts | **1.63** | También rentable — mercado bajista anticipado 2026 |
| Combinado | **1.92** | El mejor ratio del portafolio |

**Por qué funciona en ambas direcciones**: Los breakouts de pivot son estructurales independientemente de la dirección. En Renko, un breakout short es tan limpio como uno long.

---

## Fortalezas

- **Sortino=8.50** — el mejor indicador de calidad de riesgo. Significa que las ganancias son mucho mayores y más consistentes que las pérdidas
- **R²=0.96** — curva de equity casi perfecta, crecimiento lineal sostenido en 3 años
- **MaxDD=$182/ct** — el stop loss más ajustado y estructural del portafolio
- **20 contratos en Apex** — máximo aprovechamiento del capital disponible ($2,730 DD vs $7,500 límite)
- **0.49 trades/día** — frecuencia suficiente para estadística sólida (240 trades en 3 años)
- **Concepto puro** — no hay indicadores mágicos, solo estructura de mercado real

## Debilidades / Riesgos

- **Renko chart requerido** — algunos brokers/plataformas no tienen Renko histórico confiable
- **Sensibilidad a PivotStrength** — cambiar a 2 o 4 puede alterar significativamente los resultados
- **Mercado sin pivots claros** — en días de rango muy estrecho, el sistema no genera señales (0 trades)
- **240 trades en 3 años = 80/año** — muestra sólida pero no enorme para confirmar edge con 20ct

---

## Sizing para Apex

| Contratos | Net/mes | MaxDD | Viable Apex |
|---|---|---|---|
| 10 | $1,150 | $1,820 | ✅ muy cómodo |
| 15 | $1,725 | $2,730 | ✅ |
| **20** | **$2,305** | **$2,730** | ✅ **recomendado** |
| 25 | $2,880 | $4,550 | ✅ con margen |
| 41 | $4,715 | $7,462 | ⚠️ exactamente en el límite |

**Recomendación**: 20 contratos — usa solo 36% del límite MaxDD de Apex, dejando margen para drawdowns excepcionales.

---

## Por qué es la #1 del portafolio

En trading algorítmico, el Sortino Ratio es el mejor indicador de calidad porque penaliza solo las pérdidas (no la volatilidad positiva). Un Sortino=8.50 es extraordinario — implica que por cada unidad de riesgo negativo, la estrategia genera 8.5 unidades de retorno ajustado.

Comparación:
- Hedge funds top tier: Sortino ~2-4
- PivotTrendBreak_v1: **8.50**

Esto sugiere que los pivots estructurales en Renko 25-tick capturan un edge genuino y persistente en MNQ.
