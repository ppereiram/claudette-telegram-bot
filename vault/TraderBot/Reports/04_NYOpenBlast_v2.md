# NYOpenBlast_v2
> Momentum apertura NY | `Strategies/NYOpenBlast_v2.cs` (archivo: NYOpenBlast_v1.cs en NT8)

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (sin comm) | **1.55** |
| PF estimado con comm | ~1.42 |
| R² | 0.92 |
| Sortino Ratio | 0.89 |
| Total trades (3 años) | ~192 |
| Trades/día | 0.25 |
| Ventana activa | 9:29 — 10:00 AM |
| Chart | 1-min MNQ, ETH session |

> **Nota histórica**: Un PF=1.72 fue anotado en sesiones anteriores bajo "condiciones ideales". El número honesto con condiciones normales es **1.55 sin comisiones / ~1.42 con comisiones**.

---

## Concepto y edge

Captura el **impulso de la apertura de NY** (9:30 AM ET). En los primeros 15 minutos de sesión regular, MNQ suele establecer una dirección fuerte impulsada por noticias pre-mercado, earnings y posicionamiento institucional.

**La mecánica clave**: el sistema analiza el movimiento de precio en los minutos previos a la apertura y determina la dirección probable. Con `InvertDirection=ON`, el sistema actúa de manera contraria a la lectura directa — esto captura el fenómeno de "fade the gap" o corrección del over-enthusiasm matutino.

**Por qué AllowShort=OFF**: En la apertura NY, el sesgo estructural del mercado es alcista. Los shorts durante este período tienen menor edge estadístico para MNQ.

---

## Parámetros confirmados

### Timing
| Parámetro | Valor | Descripción |
|---|---|---|
| DirectionTime | 92900 | Evalúa dirección a las 9:29:00 |
| EntryDeadline | 94500 | No nuevas entradas después de 9:45:00 |
| ForceExit | 100000 | Cierra todo a las 10:00:00 AM |
| TrendLookback | 30 | Barras para calcular la tendencia |

### Direccionalidad
| Parámetro | Valor |
|---|---|
| InvertDirection | **ON** ← crítico |
| AllowLong | ON |
| AllowShort | **OFF** |

### Filtro MACD
| Parámetro | Valor |
|---|---|
| UseMACDFilter | ON |
| MACD Fast | 10 |
| MACD Slow | 22 |
| MACD Signal | 9 |

### Risk
| Parámetro | Valor |
|---|---|
| Target | 500 ticks ($250/ct) |
| Stop | 100 ticks ($50/ct) |
| Breakeven | OFF |
| R:R implícito | 5:1 |

---

## Comportamiento en vivo

**La salida principal NO es el profit target de 500 ticks** — es el `ForceExit` a las 10:00 AM. La mayoría de los trades que ganan, salen por tiempo (ForceExit) con una ganancia parcial menor a los 500 ticks. El target de 500 ticks actúa más como "techo de protección ante movimientos explosivos".

Esto es importante porque:
- El stop real efectivo es tiempo (no precio)
- Los 100 ticks de stop son la protección ante moves adversos fuertes en apertura
- La ventana de trading es de máximo 31 minutos (9:29-10:00)

---

## Fortalezas

- **R²=0.92** — segunda curva más lineal del portafolio
- **Muy pocas horas de riesgo** — posición solo 9:29-10:00 AM (~31 min máximo)
- **Completamente descorrelacionado** — solo opera durante la apertura, el resto del portafolio no tiene posición en esa ventana
- **0.25 trades/día** — baja frecuencia = baja comisión

## Debilidades / Riesgos

- **Datos económicos** — los primeros viernes del mes (NFP), FOMC days y CPI pueden generar moves de 200+ ticks en segundos. El stop de 100 ticks puede ser insuficiente en eventos extremos
- **Dependencia del contexto macro** — si hay un cambio estructural en cómo reacciona el mercado a la apertura de NY, la estrategia perdería edge
- **Sortino 0.89** — el más bajo del grupo (baja frecuencia implica que los pocos días malos pesan más)

---

## Nota sobre el nombre del archivo

El archivo en NT8 se llama `NYOpenBlast_v1.cs` pero la clase interna es `NYOpenBlast_v2`. El código es la versión v2 confirmada — no se debe renombrar o reemplazar sin verificar.

---

## Sizing para Apex

| Contratos | Net/mes | MaxDD estimado | Viable Apex |
|---|---|---|---|
| 7 | ~$350 | ~$7,000 | ✅ |
| 10 | ~$500 | ~$10,000 | ❌ |

**Cálculo**: Con SurvivalTrades=20 → ~7 contratos caben en MaxDD $7,500.
